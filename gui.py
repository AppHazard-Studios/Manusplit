"""
Manusplit - Perfectly fixed GUI with consistent spacing and proper alignment.
"""
import sys
import os
import logging
import json
from pathlib import Path

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLabel, QPushButton, QFileDialog,
                           QSpinBox, QLineEdit, QCheckBox, QDialog, QFormLayout,
                           QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
                           QAbstractItemView, QSizePolicy)
from PyQt6.QtGui import (QFont, QIcon, QDragEnterEvent, QDropEvent, QColor, QPalette,
                       QCursor)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer, QSize, QEvent

# Import your existing components
from settings import Settings
from splitter import DocumentSplitter
from utils import setup_logging
import version


class Worker(QObject):
    """Worker thread to process files in the background."""

    # Define signals for communication with main thread
    statusUpdated = pyqtSignal(str)
    progressUpdated = pyqtSignal(int)
    resultReady = pyqtSignal(dict)
    finished = pyqtSignal()

    def __init__(self, splitter, files, settings):
        super().__init__()
        self.splitter = splitter
        self.files = files
        self.settings = settings
        self.logger = logging.getLogger(__name__)

    def process(self):
        """Process files with the document splitter."""
        try:
            total_files = len(self.files)

            for i, file in enumerate(self.files):
                # Calculate progress
                progress = int((i / total_files) * 100)
                self.progressUpdated.emit(progress)

                # Only emit minimal status updates
                self.statusUpdated.emit("...")

                # Create an output folder for this file
                self._prepare_output_folder(file)

                # Process the file using the splitter
                result = self.splitter.process_file(file, callback=self.splitter_callback)

                # Emit result
                self.resultReady.emit(result)

            # Complete - clear status
            self.statusUpdated.emit("")
            self.progressUpdated.emit(100)

        except Exception as e:
            self.logger.exception(f"Error in processing thread: {str(e)}")
            self.statusUpdated.emit(f"Error: {str(e)}")

        finally:
            self.finished.emit()

    def _prepare_output_folder(self, file_path):
        """Create a dedicated output folder for a file."""
        try:
            # Get base filename without extension
            basename = os.path.basename(file_path)
            filename, _ = os.path.splitext(basename)

            # Create a clean folder name (remove invalid chars)
            folder_name = "".join(c for c in filename if c.isalnum() or c in [' ', '-', '_']).strip()
            if not folder_name:
                folder_name = "Document"

            # Create the path within the main output folder
            base_output_dir = self.settings.get("output_folder")
            output_dir = os.path.join(base_output_dir, folder_name)

            # Handle duplicate folder names
            count = 1
            original_output_dir = output_dir
            while os.path.exists(output_dir):
                output_dir = f"{original_output_dir}_{count}"
                count += 1

            # Create the folder
            os.makedirs(output_dir, exist_ok=True)

            # Update the splitter to use this folder
            self.splitter.current_output_folder = output_dir

        except Exception as e:
            self.logger.error(f"Error creating output folder: {str(e)}")
            # Fall back to main output folder
            self.splitter.current_output_folder = self.settings.get("output_folder")

    def splitter_callback(self, status, progress, message):
        """Callback for the DocumentSplitter with minimal updates."""
        # Only send minimal status messages
        if status == "saving" or status == "complete":
            self.statusUpdated.emit("")
        else:
            self.statusUpdated.emit("...")
        self.progressUpdated.emit(progress)


class SettingsDialog(QDialog):
    """Settings dialog for Manusplit."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.setWindowTitle("Settings")
        self.resize(400, 250)
        self.setup_ui()

    def setup_ui(self):
        """Set up the settings dialog UI."""
        # Main layout with clean margins
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Form layout with proper proportions
        form = QFormLayout()
        form.setSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)

        # Word limit with proper sizing
        limit_label = QLabel("Maximum words per file:")
        limit_label.setStyleSheet("color: white; font-size: 14px;")

        self.max_words = QSpinBox()
        self.max_words.setRange(1000, 100000)
        self.max_words.setValue(self.settings.get("max_words"))
        self.max_words.setSingleStep(1000)
        self.max_words.setFixedWidth(100)  # Smaller fixed width
        self.max_words.setFixedHeight(28)  # Fixed height to match text
        self.max_words.setStyleSheet("""
            QSpinBox {
                background-color: #262626;
                color: white;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 4px;
                font-size: 14px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                subcontrol-origin: border;
                width: 16px;
                border-radius: 3px;
            }
        """)
        form.addRow(limit_label, self.max_words)

        # Output folder with proper sizing
        folder_label = QLabel("Output folder:")
        folder_label.setStyleSheet("color: white; font-size: 14px;")

        folder_widget = QWidget()
        folder_layout = QHBoxLayout(folder_widget)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(8)

        self.output_folder = QLineEdit()
        self.output_folder.setText(self.settings.get("output_folder"))
        self.output_folder.setFixedHeight(28)  # Fixed height to match text
        self.output_folder.setStyleSheet("""
            QLineEdit {
                background-color: #262626;
                color: white;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 14px;
            }
        """)
        folder_layout.addWidget(self.output_folder)

        browse_btn = QPushButton("Browse")
        browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        browse_btn.setFixedHeight(28)  # Fixed height to match text
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(browse_btn)

        form.addRow(folder_label, folder_widget)

        # Add form to main layout
        layout.addLayout(form)
        layout.addSpacing(8)

        # Checkboxes
        self.preserve_formatting = QCheckBox("Preserve document formatting")
        self.preserve_formatting.setChecked(self.settings.get("preserve_formatting"))
        self.preserve_formatting.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #262626;
                border: 1px solid #444444;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border: 1px solid #0078d4;
            }
        """)
        layout.addWidget(self.preserve_formatting)

        self.skip_under_limit = QCheckBox("Skip files under word limit")
        self.skip_under_limit.setChecked(self.settings.get("skip_under_limit"))
        self.skip_under_limit.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #262626;
                border: 1px solid #444444;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border: 1px solid #0078d4;
            }
        """)
        layout.addWidget(self.skip_under_limit)

        # Add spacer
        layout.addStretch(1)

        # Button row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.setFixedHeight(32)  # Consistent height
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_btn.setFixedHeight(32)  # Consistent height
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0086f0;
            }
            QPushButton:pressed {
                background-color: #006aba;
            }
        """)
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def browse_folder(self):
        """Show dialog to select output folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder.setText(folder)

    def save_settings(self):
        """Save settings from dialog to Settings object."""
        try:
            self.settings.set("max_words", self.max_words.value())
            self.settings.set("output_folder", self.output_folder.text())
            self.settings.set("preserve_formatting", self.preserve_formatting.isChecked())
            self.settings.set("skip_under_limit", self.skip_under_limit.isChecked())

            # Save settings to disk
            self.settings.save()
            return True

        except Exception as e:
            self.logger.error(f"Failed to save settings: {str(e)}")
            return False


class FirstRunDialog(QDialog):
    """Dialog shown on first run to select output location."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Manusplit")
        self.resize(500, 280)
        self.output_path = os.path.join(os.path.expanduser("~"), "Documents", "Manusplit Files")
        self.setup_ui()

    def setup_ui(self):
        """Set up the first run dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Welcome message
        welcome = QLabel("Welcome to Manusplit")
        welcome.setStyleSheet("""
            font-size: 24px;
            font-weight: 600;
            color: white;
        """)
        layout.addWidget(welcome)

        # Description
        desc = QLabel("A tool for splitting large documents into smaller parts.")
        desc.setStyleSheet("""
            font-size: 14px;
            color: #cccccc;
        """)
        layout.addWidget(desc)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #333333;")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        layout.addSpacing(10)

        # Output folder section
        folder_label = QLabel("Choose where to save your split documents:")
        folder_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 500;
            color: white;
        """)
        layout.addWidget(folder_label)

        # Folder selection widget
        folder_widget = QWidget()
        folder_layout = QHBoxLayout(folder_widget)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(8)

        self.folder_input = QLineEdit(self.output_path)
        self.folder_input.setStyleSheet("""
            QLineEdit {
                background-color: #262626;
                color: white;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
            }
        """)
        folder_layout.addWidget(self.folder_input)

        browse_btn = QPushButton("Browse")
        browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(browse_btn)

        layout.addWidget(folder_widget)

        # Note
        note = QLabel("This folder will contain the split documents organized by file.")
        note.setStyleSheet("""
            font-size: 13px;
            color: #aaaaaa;
            font-style: italic;
        """)
        layout.addWidget(note)

        # Add spacer
        layout.addStretch(1)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        get_started = QPushButton("Get Started")
        get_started.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        get_started.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0086f0;
            }
            QPushButton:pressed {
                background-color: #006aba;
            }
        """)
        get_started.clicked.connect(self.accept)
        button_layout.addWidget(get_started)

        layout.addLayout(button_layout)

    def browse_folder(self):
        """Allow user to select output folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.folder_input.setText(folder)
            self.output_path = self.folder_input.text()


class ManusplitApp(QMainWindow):
    """Modern UI for Manusplit with proper alignment and spacing."""

    # Maximum filename length to display
    MAX_FILENAME_LENGTH = 40

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.splitter = DocumentSplitter(settings)
        self.splitter.current_output_folder = settings.get("output_folder")

        self.logger = logging.getLogger(__name__)
        self.processed_files = set()  # Track which files have been processed

        # Set up the UI
        self.setWindowTitle("Manusplit")
        self.resize(700, 400)  # Compact height
        self.setup_ui()

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Worker thread
        self.worker_thread = None

    def setup_ui(self):
        """Set up the modern UI with improved layout."""
        # Set app style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
                color: white;
            }
        """)

        # Set up central widget with main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)  # Reduced spacing

        # Container widget for the file table and header
        self.table_container = QWidget()
        table_container_layout = QVBoxLayout(self.table_container)
        table_container_layout.setContentsMargins(0, 0, 0, 0)
        table_container_layout.setSpacing(0)

        # Custom table header
        header_widget = QWidget()
        header_widget.setFixedHeight(40)
        header_widget.setStyleSheet("""
            background-color: #232323;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border-bottom: 1px solid #333333;
        """)

        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(0)

        # Left-aligned "Selected files" header
        files_header = QLabel("Selected files")
        files_header.setStyleSheet("color: white; font-weight: 500; font-size: 13px;")
        files_header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Center-aligned "# Words" header
        words_header = QLabel("# Words")
        words_header.setStyleSheet("color: white; font-weight: 500; font-size: 13px;")
        words_header.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        # Center-aligned "# Parts" header
        parts_header = QLabel("# Parts")
        parts_header.setStyleSheet("color: white; font-weight: 500; font-size: 13px;")
        parts_header.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        # Add headers to layout with proper stretching
        header_layout.addWidget(files_header, 7)
        header_layout.addWidget(words_header, 2)
        header_layout.addWidget(parts_header, 1)

        table_container_layout.addWidget(header_widget)

        # Table for files
        self.file_table = QTableWidget(0, 3)
        self.file_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.file_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.file_table.setShowGrid(False)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.horizontalHeader().setVisible(False)

        # Set column resize modes and widths
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.file_table.setColumnWidth(1, 80)
        self.file_table.setColumnWidth(2, 60)

        # Set elegant styling
        self.file_table.setStyleSheet("""
            QTableWidget {
                background-color: #232323;
                alternate-background-color: #282828;
                border: none;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
                gridline-color: transparent;
                outline: none;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #232323;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        table_container_layout.addWidget(self.file_table)

        # Initially hide the table container
        self.table_container.setVisible(False)
        main_layout.addWidget(self.table_container)

        # Status bar for minimal processing messages
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #aaaaaa; font-size: 13px;")
        self.status_label.setFixedHeight(20)  # Minimal height
        main_layout.addWidget(self.status_label)

        # Drag zone with proper text display
        self.drop_zone = QLabel("Drop files here to process")
        self.drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_zone.setFixedHeight(50)  # Perfect height to fit text
        self.drop_zone.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 14px;
                background-color: #222222;
                border: 1px solid #333333;
                border-radius: 8px;
                margin-top: 4px;
                margin-bottom: 4px;
                padding-top: 14px;      /* Increased top padding */
                padding-bottom: 14px;   /* Increased bottom padding */
            }
        """)
        main_layout.addWidget(self.drop_zone)

        # Settings button directly below the drag zone with minimal spacing
        settings_container = QHBoxLayout()
        settings_container.setContentsMargins(0, 4, 0, 0)  # Minimal top margin

        # Add stretch to push settings button to the right
        settings_container.addStretch()

        # Modern settings button
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.settings_btn.setFixedHeight(30)  # Smaller height
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #222222;
                color: #aaaaaa;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
                color: white;
            }
            QPushButton:pressed {
                background-color: #333333;
            }
        """)
        self.settings_btn.clicked.connect(self.show_settings)
        settings_container.addWidget(self.settings_btn)

        main_layout.addLayout(settings_container)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            self.drop_zone.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 14px;
                    background-color: rgba(0, 120, 212, 0.15);
                    border: 1px solid #0078d4;
                    border-radius: 8px;
                    padding-top: 14px;
                    padding-bottom: 14px;
                }
            """)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """Handle drag leave events."""
        self.drop_zone.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 14px;
                background-color: #222222;
                border: 1px solid #333333;
                border-radius: 8px;
                padding-top: 14px;
                padding-bottom: 14px;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        """Handle drop events."""
        if event.mimeData().hasUrls():
            self.drop_zone.setStyleSheet("""
                QLabel {
                    color: #aaaaaa;
                    font-size: 14px;
                    background-color: #222222;
                    border: 1px solid #333333;
                    border-radius: 8px;
                    padding-top: 14px;
                    padding-bottom: 14px;
                }
            """)
            event.acceptProposedAction()

            files = []
            for url in event.mimeData().urls():
                filepath = url.toLocalFile()
                # Check for duplicates
                if filepath not in self.processed_files:
                    files.append(filepath)
                    self.processed_files.add(filepath)

            if files:
                self.process_files(files)
            else:
                self.status_label.setText("Files already processed or unsupported")
                QTimer.singleShot(2000, lambda: self.status_label.setText(""))

    def truncate_filename(self, filename):
        """Truncate long filenames for display."""
        if len(filename) > self.MAX_FILENAME_LENGTH:
            name, ext = os.path.splitext(filename)
            truncated = name[:self.MAX_FILENAME_LENGTH - 5 - len(ext)] + "..." + ext
            return truncated
        return filename

    def process_files(self, files):
        """Process files and update UI."""
        # Filter valid files
        valid_files = []
        for file in files:
            file = str(file).strip()
            if not file:
                continue

            _, ext = os.path.splitext(file.lower())
            if ext in ['.docx', '.txt']:
                valid_files.append(file)
            else:
                self.status_label.setText(f"Skipping unsupported file: {os.path.basename(file)}")
                continue

        if not valid_files:
            self.status_label.setText("No valid files selected")
            return

        # Show table container
        self.table_container.setVisible(True)

        # Make drop zone more compact
        self.drop_zone.setFixedHeight(36)  # Smaller when files present
        self.drop_zone.setText("Drag more files here to process")
        self.drop_zone.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 14px;
                background-color: #222222;
                border: 1px solid #333333;
                border-radius: 8px;
                padding-top: 8px;
                padding-bottom: 8px;
            }
        """)

        # Add files to table
        self.add_files_to_table(valid_files)

        # Update status - minimal
        self.status_label.setText("...")

        # Start worker thread
        self.worker_thread = QThread()
        self.worker = Worker(self.splitter, valid_files, self.settings)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.process)
        self.worker.statusUpdated.connect(self.status_label.setText)
        self.worker.resultReady.connect(self.update_file_result)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.processing_completed)

        # Cleanup
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        # Start processing
        self.worker_thread.start()

    def add_files_to_table(self, files):
        """Add files to the table with proper styling."""
        for file_path in files:
            # Get filename
            filename = os.path.basename(file_path)
            truncated_name = self.truncate_filename(filename)

            # Add new row
            row = self.file_table.rowCount()
            self.file_table.insertRow(row)

            # Set row height
            self.file_table.setRowHeight(row, 36)

            # Create row number and filename item (left-aligned)
            file_item = QTableWidgetItem(f"{row+1}  {truncated_name}")
            file_item.setData(Qt.ItemDataRole.UserRole, file_path)
            file_item.setToolTip(filename)
            file_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # Create word count placeholder (center-aligned)
            word_item = QTableWidgetItem("...")
            word_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

            # Create parts placeholder (center-aligned)
            parts_item = QTableWidgetItem("...")
            parts_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

            # Add items to table
            self.file_table.setItem(row, 0, file_item)
            self.file_table.setItem(row, 1, word_item)
            self.file_table.setItem(row, 2, parts_item)

    def update_file_result(self, result):
        """Update table with processing result."""
        if not result['success']:
            return

        file_path = result['original_path']

        # Find the row for this file
        for row in range(self.file_table.rowCount()):
            item = self.file_table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == file_path:
                # Update word count (center-aligned)
                word_item = self.file_table.item(row, 1)
                if word_item:
                    word_item.setText(f"{result['total_words']:,}")
                    word_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

                # Update parts count (center-aligned)
                parts_item = self.file_table.item(row, 2)
                if parts_item:
                    parts_item.setText(str(result['parts_created']))
                    parts_item.setForeground(QColor("#4CAF50"))  # Green text
                    parts_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

                break

    def processing_completed(self):
        """Handle completion of all processing."""
        self.status_label.setText("")

    def show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(self.settings, self)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
            }
        """)

        if dialog.exec():
            # Save settings
            if dialog.save_settings():
                self.status_label.setText("Settings saved")
                QTimer.singleShot(2000, lambda: self.status_label.setText(""))

                # Update splitter
                self.splitter.current_output_folder = self.settings.get("output_folder")


def force_first_run():
    """Force first run dialog by renaming settings file."""
    if os.path.exists("settings.json"):
        try:
            os.rename("settings.json", "settings.json.bak")
            return True
        except:
            return False
    return True


def create_default_settings(output_path=None):
    """Create default settings file."""
    logger = logging.getLogger(__name__)

    if not os.path.exists("settings.json"):
        try:
            # Set default path
            if not output_path:
                output_path = os.path.join(os.path.expanduser("~"), "Documents", "Manusplit Files")

            # Create folder if needed
            if not os.path.exists(output_path):
                os.makedirs(output_path)

            # Default settings
            settings_dict = {
                "max_words": 100000,
                "output_folder": output_path,
                "preserve_formatting": True,
                "skip_under_limit": True
            }

            # Write settings
            with open("settings.json", "w") as f:
                json.dump(settings_dict, f, indent=4)

            logger.info(f"Created settings with output folder: {output_path}")
            return True

        except Exception as e:
            logger.warning(f"Failed to create settings: {str(e)}")
            return False

    return True


def is_first_run():
    """Check if this is the first run."""
    return not os.path.exists("settings.json")


def main():
    """Application entry point."""
    # Set up logging
    logger = setup_logging()
    logger.info(f"Starting Manusplit v{version.get_version()}")

    # Force first run if requested
    force_first = "--first-run" in sys.argv
    if force_first:
        force_first_run()

    # Start application
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Use modern font
    font = QFont("SF Pro, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial", 9)
    app.setFont(font)

    # Check for first run
    first_run = is_first_run()

    try:
        # Show first run dialog if needed
        output_path = None
        if first_run:
            dialog = FirstRunDialog()
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #1a1a1a;
                }
            """)

            if dialog.exec():
                output_path = dialog.output_path
            else:
                # Use default path if canceled
                output_path = os.path.join(os.path.expanduser("~"), "Documents", "Manusplit Files")

        # Create default settings
        create_default_settings(output_path)

        # Load settings
        settings = Settings()
        logger.info("Settings loaded")

        # Ensure output directory exists
        output_dir = Path(settings.get("output_folder"))
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create and show main window
        window = ManusplitApp(settings)
        window.show()

        # Run application
        sys.exit(app.exec())

    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()