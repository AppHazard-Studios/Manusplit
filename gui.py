"""
Manusplit - Final UI that perfectly matches ExifCleaner's clean design.
Creates output folders for each document and handles duplicates intelligently.
"""
import sys
import os
import threading
import logging
import json
import shutil
from pathlib import Path
import time

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLabel, QPushButton, QFileDialog,
                           QSpinBox, QLineEdit, QCheckBox, QTableWidget,
                           QTableWidgetItem, QHeaderView, QDialog, QFormLayout)
from PyQt6.QtGui import QFont, QIcon, QDragEnterEvent, QDropEvent, QColor, QPixmap
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer

# Import your existing components
from settings import Settings
from splitter import DocumentSplitter
from utils import setup_logging
import version


# Worker thread to handle file processing without freezing the UI
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
                self.statusUpdated.emit(f"Processing {os.path.basename(file)}...")

                # Create an output folder for this file
                self._prepare_output_folder(file)

                # Process the file using the splitter
                result = self.splitter.process_file(file, callback=self.splitter_callback)

                # Emit result
                self.resultReady.emit(result)

            # Complete
            self.statusUpdated.emit(f"Completed processing {total_files} file(s).")
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
        """Callback for the DocumentSplitter."""
        self.statusUpdated.emit(message)
        self.progressUpdated.emit(progress)


class SettingsDialog(QDialog):
    """Settings dialog for Manusplit."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")
        self.resize(400, 200)  # More compact size
        self.setup_ui()

    def setup_ui(self):
        """Set up the settings dialog UI."""
        # Main layout with smaller margins
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Form layout for settings
        form = QFormLayout()
        form.setSpacing(10)

        # Max words setting
        self.max_words = QSpinBox()
        self.max_words.setRange(1000, 100000)
        self.max_words.setValue(self.settings.get("max_words"))
        self.max_words.setSingleStep(1000)
        self.max_words.setFixedWidth(100)
        self.max_words.setStyleSheet("""
            QSpinBox {
                background-color: #262626;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 4px;
            }
        """)
        form.addRow("Maximum words per file:", self.max_words)

        # Output folder setting with browse button
        folder_widget = QWidget()
        folder_layout = QHBoxLayout(folder_widget)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.setSpacing(5)

        self.output_folder = QLineEdit()
        self.output_folder.setText(self.settings.get("output_folder"))
        self.output_folder.setStyleSheet("""
            QLineEdit {
                background-color: #262626;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 4px;
            }
        """)
        folder_layout.addWidget(self.output_folder)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_folder)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
            }
        """)
        folder_layout.addWidget(browse_btn)

        form.addRow("Output folder:", folder_widget)

        layout.addLayout(form)

        # Checkboxes with proper spacing
        options_layout = QVBoxLayout()
        options_layout.setSpacing(8)

        self.preserve_formatting = QCheckBox("Preserve formatting")
        self.preserve_formatting.setChecked(self.settings.get("preserve_formatting"))
        self.preserve_formatting.setStyleSheet("""
            QCheckBox {
                color: white;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #262626;
                border: 1px solid #3d3d3d;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border: 1px solid #0078d4;
            }
        """)
        options_layout.addWidget(self.preserve_formatting)

        self.skip_under_limit = QCheckBox("Skip files under word limit")
        self.skip_under_limit.setChecked(self.settings.get("skip_under_limit"))
        self.skip_under_limit.setStyleSheet("""
            QCheckBox {
                color: white;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #262626;
                border: 1px solid #3d3d3d;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border: 1px solid #0078d4;
            }
        """)
        options_layout.addWidget(self.skip_under_limit)

        layout.addLayout(options_layout)

        # Add spacer
        layout.addStretch(1)

        # Button row
        button_layout = QHBoxLayout()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 3px;
            }
        """)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                padding: 6px 16px;
                border-radius: 3px;
            }
        """)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)

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
        self.resize(450, 250)
        self.output_path = os.path.join(os.path.expanduser("~"), "Documents", "Manusplit Files")
        self.setup_ui()

    def setup_ui(self):
        """Set up the first run dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Welcome message
        welcome = QLabel("Welcome to Manusplit")
        welcome.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
        """)
        layout.addWidget(welcome)

        desc = QLabel("Choose where to save your split documents:")
        desc.setStyleSheet("""
            font-size: 14px;
            color: #cccccc;
        """)
        layout.addWidget(desc)

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
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 6px;
            }
        """)
        folder_layout.addWidget(self.folder_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_folder)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
            }
        """)
        folder_layout.addWidget(browse_btn)

        layout.addWidget(folder_widget)

        # Note
        note = QLabel("This folder will contain the split documents organized by file.")
        note.setStyleSheet("""
            font-size: 12px;
            color: #aaaaaa;
        """)
        layout.addWidget(note)

        # Add spacer
        layout.addStretch(1)

        # Buttons
        button_layout = QHBoxLayout()

        get_started = QPushButton("Get Started")
        get_started.clicked.connect(self.accept)
        get_started.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 3px;
            }
        """)
        button_layout.addWidget(get_started)

        layout.addLayout(button_layout)

    def browse_folder(self):
        """Allow user to select output folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.folder_input.setText(folder)
            self.output_path = self.folder_input.text()


class ManusplitApp(QMainWindow):
    """Clean, ExifCleaner-style UI for Manusplit."""

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.splitter = DocumentSplitter(settings)

        # Add current_output_folder attribute to splitter
        self.splitter.current_output_folder = settings.get("output_folder")

        self.logger = logging.getLogger(__name__)
        self.processed_files = set()  # Track which files have been processed

        self.setWindowTitle("Manusplit")
        self.resize(550, 350)

        # Apply styling
        self.setup_ui()

        # Set up thread handler
        self.thread = None
        self.worker = None

        # Make the entire window a drop target
        self.setAcceptDrops(True)

    def setup_ui(self):
        """Set up UI that perfectly matches ExifCleaner."""
        # Set the main window style (flat, no borders)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: white;
                border: none;
            }
        """)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 10, 20, 20)
        main_layout.setSpacing(0)  # Important for exact spacing

        # Header with title and settings icon
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)

        title_label = QLabel("Manusplit")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
        """)
        header_layout.addWidget(title_label)

        # Settings cog (transparent background)
        self.settings_btn = QPushButton()
        self.settings_btn.setIcon(QIcon("settings_icon.png"))  # Fall back to Unicode if not found
        self.settings_btn.setText("⚙")
        self.settings_btn.setStyleSheet("""
            QPushButton {
                color: #aaaaaa;
                font-size: 24px;
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                color: white;
            }
        """)
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.clicked.connect(self.show_settings)
        header_layout.addWidget(self.settings_btn, alignment=Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(header_layout)

        # Thin separator line
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #333333;")
        main_layout.addWidget(separator)
        main_layout.addSpacing(10)  # Space after separator

        # Content area (either drop zone or results table)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # Empty state - drop zone
        self.drop_container = QWidget()
        drop_container_layout = QVBoxLayout(self.drop_container)
        drop_container_layout.setContentsMargins(0, 0, 0, 0)
        drop_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        drop_label = QLabel("Drop files here to process")
        drop_label.setStyleSheet("""
            color: #aaaaaa;
            font-size: 14px;
        """)
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_container_layout.addWidget(drop_label)

        self.content_layout.addWidget(self.drop_container)

        # Results table (initially hidden)
        self.table_header = QWidget()
        table_header_layout = QHBoxLayout(self.table_header)
        table_header_layout.setContentsMargins(10, 10, 10, 10)
        table_header_layout.setSpacing(0)

        # Column headers
        files_label = QLabel("Selected files")
        files_label.setStyleSheet("color: white; font-size: 14px;")
        table_header_layout.addWidget(files_label, 7)

        words_label = QLabel("# Words")
        words_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        words_label.setStyleSheet("color: white; font-size: 14px;")
        table_header_layout.addWidget(words_label, 2)

        parts_label = QLabel("# Parts")
        parts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        parts_label.setStyleSheet("color: white; font-size: 14px;")
        table_header_layout.addWidget(parts_label, 1)

        self.table_header.setVisible(False)
        self.content_layout.addWidget(self.table_header)

        # The actual table for results
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(0)

        # We'll add rows to this dynamically
        self.results_container.setVisible(False)
        self.content_layout.addWidget(self.results_container)

        main_layout.addWidget(self.content_widget, 1)

        # Status bar at bottom
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #aaaaaa; font-size: 14px;")
        main_layout.addWidget(self.status_label)

        # Drag more files hint (initially hidden)
        self.drag_hint = QLabel("Drag more files here to process")
        self.drag_hint.setStyleSheet("color: #666666; font-size: 14px; font-style: italic;")
        self.drag_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_hint.setVisible(False)
        main_layout.addWidget(self.drag_hint)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

            files = []
            for url in event.mimeData().urls():
                files.append(url.toLocalFile())

            self.process_files(files)

    def show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(self.settings, self)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
        """)

        if dialog.exec():
            # Save settings
            if dialog.save_settings():
                self.status_label.setText("Settings saved")
                # Use a timer to clear the status after 2 seconds
                QTimer.singleShot(2000, lambda: self.status_label.setText(""))

    def process_files(self, files):
        """Process a list of files."""
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

        # Hide drop container, show table
        self.drop_container.setVisible(False)
        self.table_header.setVisible(True)
        self.results_container.setVisible(True)

        # Clear any existing rows and add new ones for these files
        self.add_file_rows(valid_files)

        # Update status
        self.status_label.setText(f"Processing {len(valid_files)} file(s)...")

        # Set up thread and worker
        self.thread = QThread()
        self.worker = Worker(self.splitter, valid_files, self.settings)
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.thread.started.connect(self.worker.process)
        self.worker.statusUpdated.connect(self.status_label.setText)
        self.worker.resultReady.connect(self._handle_result)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self._processing_complete)

        # Clean up when done
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Start processing
        self.thread.start()

    def add_file_rows(self, files):
        """Add rows to the results table for new files."""
        # Clear previous results layout if starting fresh
        if len(files) > 0 and self.results_layout.count() == 0:
            # First time adding files
            for i, file in enumerate(files):
                self._add_row(i+1, file)
        else:
            # Adding more files to existing list
            current_count = self.results_layout.count()
            for i, file in enumerate(files):
                self._add_row(current_count+i+1, file)

    def _add_row(self, row_num, file_path):
        """Add a single row to the results table."""
        # Create row container
        row = QWidget()

        # Alternate row background color
        if row_num % 2 == 0:
            row.setStyleSheet("background-color: #262626;")
        else:
            row.setStyleSheet("background-color: #1e1e1e;")

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(0)

        # File cell with row number
        file_cell = QHBoxLayout()
        file_cell.setSpacing(10)

        # Row number
        row_label = QLabel(f"{row_num}")
        row_label.setStyleSheet("color: #aaaaaa; min-width: 15px;")
        file_cell.addWidget(row_label)

        # Filename
        filename = os.path.basename(file_path)
        file_label = QLabel(filename)
        file_label.setStyleSheet("color: white;")
        file_cell.addWidget(file_label)

        row_layout.addLayout(file_cell, 7)

        # Word count (processing indicator)
        words_label = QLabel("...")
        words_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        words_label.setStyleSheet("color: #aaaaaa;")
        row_layout.addWidget(words_label, 2)

        # Parts count (processing indicator)
        parts_label = QLabel("...")
        parts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        parts_label.setStyleSheet("color: #aaaaaa;")
        row_layout.addWidget(parts_label, 1)

        # Store file path and labels in the widget for later lookup
        row.setProperty("file_path", file_path)
        row.setProperty("words_label", words_label)
        row.setProperty("parts_label", parts_label)

        # Add to results
        self.results_layout.addWidget(row)

    def _handle_result(self, result):
        """Handle processing result and update UI."""
        if not result['success']:
            return

        # Find the row for this file
        file_path = result['original_path']

        for i in range(self.results_layout.count()):
            row_widget = self.results_layout.itemAt(i).widget()
            if row_widget and row_widget.property("file_path") == file_path:
                # Update word count
                words_label = row_widget.property("words_label")
                if words_label:
                    words_label.setText(f"{result['total_words']:,}")
                    words_label.setStyleSheet("color: white;")

                # Update parts count
                parts_label = row_widget.property("parts_label")
                if parts_label:
                    parts_value = str(result['parts_created'])
                    parts_label.setText(parts_value)
                    parts_label.setStyleSheet("color: #4CAF50;")  # Green text

                break

    def _processing_complete(self):
        """Called when processing is complete."""
        self.status_label.setText(f"Completed processing {self.results_layout.count()} file(s).")

        # Show hint about dragging more files
        self.drag_hint.setVisible(True)


# Create a dummy settings.json file to force first run dialog
def force_first_run():
    """Delete settings.json to force first run experience."""
    if os.path.exists("settings.json"):
        try:
            os.rename("settings.json", "settings.json.bak")
            return True
        except:
            return False
    return True


# Create default settings with user-specified folder
def create_default_settings(output_path=None):
    logger = logging.getLogger(__name__)

    if not os.path.exists("settings.json"):
        try:
            # Set default path if not provided
            if not output_path:
                output_path = os.path.join(os.path.expanduser("~"), "Documents", "Manusplit Files")

            # Create the folder if it doesn't exist
            if not os.path.exists(output_path):
                os.makedirs(output_path)

            # Create settings dictionary with 100k word limit
            settings_dict = {
                "max_words": 100000,  # Exactly 100k limit
                "output_folder": output_path,
                "preserve_formatting": True,
                "skip_under_limit": True
            }

            # Write settings to file
            with open("settings.json", "w") as f:
                json.dump(settings_dict, f, indent=4)

            logger.info(f"Created settings with output folder: {output_path}")
            return True

        except Exception as e:
            logger.warning(f"Failed to create settings: {str(e)}")
            return False

    return True


def is_first_run():
    """Check if this is the first time running the application."""
    return not os.path.exists("settings.json")


def main():
    """Application entry point."""
    # Set up logging
    logger = setup_logging()
    logger.info(f"Starting Manusplit v{version.get_version()}")

    # Force first run if requested via command line
    force_first = "--first-run" in sys.argv
    if force_first:
        force_first_run()

    # Start application
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Check if this is the first run
    first_run = is_first_run()

    try:
        # Show first run dialog if needed
        output_path = None
        if first_run:
            dialog = FirstRunDialog()
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #1e1e1e;
                }
            """)

            if dialog.exec():
                output_path = dialog.output_path
            else:
                # User canceled first run dialog, use default path
                output_path = os.path.join(os.path.expanduser("~"), "Documents", "Manusplit Files")

        # Create default settings
        create_default_settings(output_path)

        # Load settings
        settings = Settings()
        logger.info("Settings loaded")

        # Ensure output directory exists
        output_dir = Path(settings.get("output_folder"))
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create and show the main window
        window = ManusplitApp(settings)
        window.show()

        # Run event loop
        sys.exit(app.exec())

    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()