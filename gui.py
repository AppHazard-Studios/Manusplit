"""
Simplified interface components for Manusplit application.
"""
import os
import sys
import PySimpleGUI as sg
import threading
import queue
from pathlib import Path
import logging

import version
from settings import Settings
from splitter import DocumentSplitter


class ManusplitGUI:
    """Main GUI for the Manusplit application."""

    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.splitter = DocumentSplitter(settings)
        self.queue = queue.Queue()
        self.active_threads = []
        self._create_window()

    def _create_window(self):
        """Create the main application window."""
        # Use a simple theme
        sg.theme('Default1')

        # Main layout - simplified with no icons or complex elements
        layout = [
            [sg.Text("Drop files here or click Browse", font=("Helvetica", 14))],
            [
                sg.Input(key="-FILES-", visible=False, enable_events=True),
                sg.FilesBrowse(
                    "Browse Files...",
                    file_types=(("Documents", "*.docx *.txt"),),
                    size=(15, 1)
                ),
                sg.Button("Settings", key="-SETTINGS-")
            ],
            [sg.Text("", size=(60, 1), key="-STATUS-")],
            [sg.ProgressBar(100, orientation='h', size=(40, 20), key='-PROGRESS-')]
        ]

        # Create window with drag and drop
        self.window = sg.Window(
            "Manusplit",
            layout,
            size=(500, 200),
            resizable=True
        )

        # Enable drag and drop
        self.window["-FILES-"].Widget.drop_target_register(7)
        self.window["-FILES-"].Widget.dnd_bind('<<Drop>>', self._drop)

        # Set initial status
        self.window["-STATUS-"].update(f"Ready. Max words per file: {self.settings.get('max_words'):,}")
        self.window["-PROGRESS-"].update(0)

    def run(self):
        """Run the main event loop."""
        try:
            while True:
                event, values = self.window.read(timeout=100)

                if event == sg.WINDOW_CLOSED:
                    break

                # Process events
                if event == "-FILES-":
                    self._process_files(values["-FILES-"].split(";"))

                elif event == "-SETTINGS-":
                    self._show_settings()

                # Check queue for thread updates
                self._check_queue()

        except Exception as e:
            self.logger.exception(f"Error in main loop: {str(e)}")
            sg.popup_error(f"An error occurred: {str(e)}")

        finally:
            # Wait for active threads to complete
            for thread in self.active_threads:
                if thread.is_alive():
                    thread.join(timeout=1.0)

            self.window.close()

    def _drop(self, event):
        """Handle drag and drop events."""
        try:
            # Get file paths from drop event
            files = event.data.decode().split('}')[0].split('{')[1].split('} {')
            self._process_files(files)
        except Exception as e:
            self.logger.exception(f"Error processing dropped files: {str(e)}")
            self.window["-STATUS-"].update(f"Error: {str(e)}")

    def _process_files(self, files):
        """Process a list of files."""
        # Filter valid files
        valid_files = []
        for file in files:
            file = file.strip()
            if not file:
                continue

            _, ext = os.path.splitext(file.lower())
            if ext in ['.docx', '.txt']:
                valid_files.append(file)
            else:
                self.logger.warning(f"Skipping unsupported file: {file}")
                self.window["-STATUS-"].update(f"Skipping unsupported file: {os.path.basename(file)}")

        if not valid_files:
            self.window["-STATUS-"].update("No valid files selected.")
            return

        # Update status
        self.window["-STATUS-"].update(f"Processing {len(valid_files)} file(s)...")
        self.window["-PROGRESS-"].update(0)

        # Start processing thread
        thread = threading.Thread(
            target=self._process_files_thread,
            args=(valid_files,),
            daemon=True
        )
        thread.start()

        # Add to active threads
        self.active_threads.append(thread)

        # Clean up completed threads
        self.active_threads = [t for t in self.active_threads if t.is_alive()]

    def _process_files_thread(self, files):
        """Thread function to process files."""
        try:
            for i, file in enumerate(files):
                # Update status
                progress = int((i / len(files)) * 100)
                self.queue.put(("status", f"Processing {os.path.basename(file)}..."))
                self.queue.put(("progress", progress))

                # Process the file
                self.splitter.process_file(file, callback=self._splitter_callback)

            # Complete
            self.queue.put(("status", f"Completed processing {len(files)} file(s)."))
            self.queue.put(("progress", 100))

        except Exception as e:
            self.logger.exception(f"Error in processing thread: {str(e)}")
            self.queue.put(("status", f"Error: {str(e)}"))

    def _splitter_callback(self, status, progress, message):
        """Callback for splitter progress updates."""
        self.queue.put(("status", message))
        self.queue.put(("progress", progress))

    def _check_queue(self):
        """Check the queue for thread updates."""
        try:
            while True:
                action, data = self.queue.get_nowait()

                if action == "status":
                    self.window["-STATUS-"].update(data)
                elif action == "progress":
                    self.window["-PROGRESS-"].update(data)

                self.queue.task_done()
        except queue.Empty:
            pass

    def _show_settings(self):
        """Show the settings dialog."""
        # Create settings layout
        layout = [
            [sg.Text("Maximum words per file:"),
             sg.Input(self.settings.get("max_words"), key="-MAX_WORDS-", size=(10, 1)),
             sg.Text("(1,000 - 100,000)")],

            [sg.Text("Output folder:"),
             sg.Input(self.settings.get("output_folder"), key="-OUTPUT_FOLDER-", size=(30, 1)),
             sg.FolderBrowse()],

            [sg.Checkbox("Preserve formatting", key="-PRESERVE_FORMATTING-",
                        default=self.settings.get("preserve_formatting"))],

            [sg.Checkbox("Skip files under word limit", key="-SKIP_UNDER_LIMIT-",
                        default=self.settings.get("skip_under_limit"))],

            [sg.Button("Save"), sg.Button("Cancel"), sg.Button("Reset to Defaults")]
        ]

        # Create dialog
        dialog = sg.Window("Settings", layout, modal=True, finalize=True)

        # Event loop
        while True:
            event, values = dialog.read()

            if event == sg.WINDOW_CLOSED or event == "Cancel":
                break

            if event == "Save":
                try:
                    # Validate and update settings
                    max_words = int(values["-MAX_WORDS-"])
                    if max_words < 1000 or max_words > 100000:
                        sg.popup_error("Maximum words must be between 1,000 and 100,000.")
                        continue

                    output_folder = values["-OUTPUT_FOLDER-"]
                    if not output_folder:
                        sg.popup_error("Output folder cannot be empty.")
                        continue

                    # Update settings
                    self.settings.set("max_words", max_words)
                    self.settings.set("output_folder", output_folder)
                    self.settings.set("preserve_formatting", values["-PRESERVE_FORMATTING-"])
                    self.settings.set("skip_under_limit", values["-SKIP_UNDER_LIMIT-"])

                    # Save settings
                    self.settings.save()

                    # Update status
                    self.window["-STATUS-"].update(f"Settings saved. Max words per file: {max_words:,}")

                    break

                except ValueError:
                    sg.popup_error("Invalid value for maximum words.")
                    continue

            if event == "Reset to Defaults":
                if sg.popup_yes_no("Reset all settings to defaults?") == "Yes":
                    self.settings.reset()
                    dialog.close()
                    self._show_settings()  # Reopen with defaults
                    return

        dialog.close()