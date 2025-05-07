"""
Manusplit - GUI with properly aligned columns and improved layout.
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
                           QAbstractItemView, QSizePolicy, QGridLayout)
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
    progressUpdated = pyqtSignal(int)
    resultReady = pyqtSignal(dict)
    fileProcessingStarted = pyqtSignal(int)  # Signal with row index
    fileProcessingComplete = pyqtSignal(int, dict)  # Row index and result
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
                # Calculate overall progress
                progress = int((i / total_files) * 100)
                self.progressUpdated.emit(progress)

                # Emit signal that we're starting to process this file
                row = i  # Assuming files are added to table in same order
                self.fileProcessingStarted.emit(row)

                # Create an output folder for this file
                self._prepare_output_folder(file)

                # Process the file using the splitter
                result = self.splitter.process_file(file, callback=self.splitter_callback)

                # Emit result for this specific file
                self.fileProcessingComplete.emit(row, result)

            # Complete processing
            self.progressUpdated.emit(100)

        except Exception as e:
            self.logger.exception(f"Error in processing thread: {str(e)}")

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
        # We don't update status anymore - the table cells will show progress
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
        self.has_files = False  # Track if we have files loaded
        self.dot_timers = {}  # For animation timers

        # Set up the UI
        self.setWindowTitle("Manusplit")
        self.setMinimumWidth(450)  # Slightly larger minimum width
        self.setMinimumHeight(280)  # Slightly reduced minimum height
        self.resize(450, 280)  # Initial window size matching updated dimensions
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

        # Main layout with minimal margins
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(8)

        # Container widget for the file table and header
        self.table_container = QWidget()
        table_container_layout = QVBoxLayout(self.table_container)
        table_container_layout.setContentsMargins(0, 0, 0, 0)
        table_container_layout.setSpacing(0)

        # Custom table header
        header_widget = QWidget()
        header_widget.setFixedHeight(44)  # Slightly taller header
        header_widget.setStyleSheet("""
            background-color: #232323;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border-bottom: 1px solid #333333;
        """)

        # Use grid layout for precise positioning
        header_layout = QGridLayout(header_widget)
        header_layout.setContentsMargins(20, 0, 20, 0)
        header_layout.setSpacing(0)

        # Left-aligned "Files to split" header
        files_header = QLabel("Files")
        files_header.setStyleSheet("color: white; font-weight: 600; font-size: 14px;")
        files_header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(files_header, 0, 0)

        # Right-aligned "# Parts" in a container
        right_container = QWidget()
        right_container.setStyleSheet("background-color: transparent;")
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)  # Smaller spacing since only one widget remains

        # "# Parts" header - center-aligned (first and only right-hand header)
        parts_header = QLabel("# Parts")
        parts_header.setStyleSheet("color: white; font-weight: 600; font-size: 14px;")
        parts_header.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        parts_header.setFixedWidth(80)
        right_layout.addWidget(parts_header)

        # Add right container at column 1
        header_layout.addWidget(right_container, 0, 1, 1, 1, Qt.AlignmentFlag.AlignRight)

        # Set column stretch factors for proper alignment
        header_layout.setColumnStretch(0, 1)  # Files column stretches
        header_layout.setColumnStretch(1, 0)  # Fixed width for right columns

        table_container_layout.addWidget(header_widget)

        # Table for files
        self.file_table = QTableWidget(0, 2)
        self.file_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.file_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.file_table.setShowGrid(False)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.horizontalHeader().setVisible(False)

        # Set fixed column widths to match header
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.file_table.setColumnWidth(1, 80)   # Match header width

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
                padding: 8px 20px;  /* More padding for better readability */
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
        self.main_layout.addWidget(self.table_container)

        # Create a container for the drop zone with the settings cog
        self.drop_container = QWidget()
        drop_container_layout = QVBoxLayout(self.drop_container)
        drop_container_layout.setContentsMargins(0, 0, 0, 0)
        drop_container_layout.setSpacing(0)

        # Taller drop zone with settings icon
        self.drop_zone = QWidget()
        # let height size to content
        self.drop_zone.setMinimumHeight(0)
        self.drop_zone.setStyleSheet(
            """
            background-color: #222222;
            border: 0px dashed #555555;
            border-radius: 8px;
            """
        )

        # Use relative positioning layout
        drop_layout = QVBoxLayout(self.drop_zone)
        drop_layout.setContentsMargins(20, 12, 20, 12)

        # Center container for text - ensures perfect vertical centering
        center_container = QWidget()
        center_container.setStyleSheet("border: none; background-color: transparent;")
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)

        # Specific text with proper size
        self.drop_text = QLabel("Drop .docx or .txt files here to split.")
        self.drop_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_text.setStyleSheet("""
            color: #aaaaaa;
            font-size: 14px;
            background-color: transparent;
            padding: 4px 12px;
            border: none;
        """)
        center_layout.addWidget(self.drop_text)

        # Add center container in the middle of the drop zone
        drop_layout.addStretch(1)
        drop_layout.addWidget(center_container)
        drop_layout.addStretch(1)

        # Settings icon overlay - positioned in top right corner
        self.settings_btn = QPushButton()
        self.settings_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.settings_btn.setFixedSize(36, 36)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666666;
                border: none;
                font-size: 20px;
                text-align: center;
                padding: 0;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        self.settings_btn.setText("⚙")
        self.settings_btn.clicked.connect(self.show_settings)

        # Position settings button absolutely in top right
        self.settings_btn.setParent(self.drop_zone)
        drop_layout.addWidget(self.settings_btn, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        drop_container_layout.addWidget(self.drop_zone)
        self.main_layout.addWidget(self.drop_container)

    def dragEnterEvent(self, event):
        """Handle drag enter events safely."""
        try:
            if event.mimeData().hasUrls():
                self.drop_zone.setStyleSheet("""
                    background-color: rgba(0, 120, 212, 0.15);
                    border: 0px dashed #555555;
                    border-radius: 8px;
                """)
                self.drop_text.setStyleSheet("""
                    color: #ffffff;
                    font-size: 14px;
                    background-color: transparent;
                    padding: 4px 12px;
                    border: none;
                """)
                event.acceptProposedAction()
        except Exception as e:
            self.logger.error(f"Error in dragEnterEvent: {str(e)}")

    def dragLeaveEvent(self, event):
        """Handle drag leave events safely."""
        try:
            self.drop_zone.setStyleSheet("""
                background-color: #222222;
                border: 0px dashed #555555;
                border-radius: 8px;
            """)
            self.drop_text.setStyleSheet("""
                color: #aaaaaa;
                font-size: 14px;
                background-color: transparent;
                padding: 4px 12px;
                border: none;
            """)
        except Exception as e:
            self.logger.error(f"Error in dragLeaveEvent: {str(e)}")

    def dropEvent(self, event):
        """Handle drop events safely."""
        try:
            if event.mimeData().hasUrls():
                # Reset styles
                self.drop_zone.setStyleSheet("""
                    background-color: #222222;
                    border: 0px dashed #555555;
                    border-radius: 8px;
                """)
                self.drop_text.setStyleSheet("""
                    color: #aaaaaa;
                    font-size: 14px;
                    background-color: transparent;
                    padding: 4px 12px;
                    border: none;
                """)
                event.acceptProposedAction()

                # Process files with delay to ensure UI updates first
                files = []
                for url in event.mimeData().urls():
                    filepath = url.toLocalFile()
                    if filepath and os.path.isfile(filepath):
                        # Check for duplicates
                        if filepath not in self.processed_files:
                            files.append(filepath)
                            self.processed_files.add(filepath)

                if files:
                    # Use a short timer to process files after the event completes
                    QTimer.singleShot(50, lambda: self.process_files(files))
        except Exception as e:
            self.logger.error(f"Error in dropEvent: {str(e)}")

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
                continue

        if not valid_files:
            return

        # Show table container if not already visible
        if not self.has_files:
            self.has_files = True
            self.table_container.setVisible(True)

            # Make drop zone more compact when we have files
            self.drop_zone.setFixedHeight(100)  # Increased height to prevent text cropping

            # Restore drop-zone outline after first file is loaded
            self.drop_zone.setStyleSheet("""
                background-color: #222222;
                border: 0px dashed #555555;
                border-radius: 8px;
            """)

            # Keep the same text as before
            self.drop_text.setText("Drop .docx or .txt files here to split.")

        # Cancel any existing animation timers
        for timer in self.dot_timers.values():
            timer.stop()
        self.dot_timers.clear()

        # Add files to table
        self.add_files_to_table(valid_files)

        # Start worker thread
        self.worker_thread = QThread()
        self.worker = Worker(self.splitter, valid_files, self.settings)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.process)
        self.worker.fileProcessingStarted.connect(self.mark_file_processing)
        self.worker.fileProcessingComplete.connect(self.update_file_result)
        self.worker.finished.connect(self.on_processing_finished)

        # Cleanup
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        # Start processing
        self.worker_thread.start()

    def on_processing_finished(self):
        """Handle processing completion."""
        # Stop all animation timers
        for timer in self.dot_timers.values():
            timer.stop()
        self.dot_timers.clear()

        # Let worker thread quit
        self.worker_thread.quit()

    def mark_file_processing(self, row):
        """Mark a file as currently processing."""
        # Update parts count with processing indicator
        parts_item = self.file_table.item(row, 1)
        if parts_item:
            parts_item.setText("...")
            parts_item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            # Ensure font size matches settings UI (14px)
            font = parts_item.font()
            font.setPointSize(14)
            parts_item.setFont(font)

            # Create timer for this cell
            timer = QTimer(self)
            timer.timeout.connect(lambda: self._animate_dots(row, 1))
            timer.start(500)  # Update every 500ms
            self.dot_timers[(row, 1)] = timer

    def _animate_dots(self, row, col):
        """Animate the loading dots."""
        item = self.file_table.item(row, col)
        if not item:
            return

        text = item.text()
        if text == "...":
            item.setText(".")
        elif text == ".":
            item.setText("..")
        elif text == "..":
            item.setText("...")
        else:
            item.setText("...")

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
            self.file_table.setRowHeight(row, 38)  # Slightly taller for better readability

            # Create filename item (left-aligned with proper padding)
            file_item = QTableWidgetItem(f"{truncated_name}")
            file_item.setData(Qt.ItemDataRole.UserRole, file_path)
            file_item.setToolTip(filename)
            file_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            # Create parts placeholder (center-aligned to match header)
            parts_item = QTableWidgetItem("...")
            parts_item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

            # Apply larger font sizes (14px to match settings UI)
            for item in [file_item, parts_item]:
                font = item.font()
                font.setPointSize(14)
                item.setFont(font)

            # Add items to table
            self.file_table.setItem(row, 0, file_item)
            self.file_table.setItem(row, 1, parts_item)

    def update_file_result(self, row, result):
        """Update table with processing result."""
        if not result['success']:
            return

        # Stop animation timers for this row
        if (row, 1) in self.dot_timers:
            self.dot_timers[(row, 1)].stop()
            del self.dot_timers[(row, 1)]

        # Update parts count (center-aligned to match header)
        parts_item = self.file_table.item(row, 1)
        if parts_item:
            parts_item.setText(str(result['parts_created']))
            # No special color - keep it white like the other text
            parts_item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            # Ensure font size matches settings UI (14px)
            font = parts_item.font()
            font.setPointSize(14)
            parts_item.setFont(font)

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