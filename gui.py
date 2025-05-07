"""
Simplified GUI for Manusplit application.
Uses Tkinter directly to avoid PySimpleGUI issues.
"""
import os
import sys
import threading
import queue
from pathlib import Path
import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from settings import Settings
from splitter import DocumentSplitter


class ManusplitGUI:
    """Main GUI for the Manusplit application using Tkinter directly."""

    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.splitter = DocumentSplitter(settings)
        self.queue = queue.Queue()
        self.active_threads = []
        self._create_window()

    def _create_window(self):
        """Create the main application window using Tkinter directly."""
        # Create root window
        self.root = tk.Tk()
        self.root.title("Manusplit")
        self.root.geometry("500x200")
        self.root.resizable(True, True)

        # Configure basic layout with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create widgets
        label = ttk.Label(main_frame, text="Drop files here or click Browse", font=("Helvetica", 14))
        label.pack(pady=10)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=5, fill=tk.X)

        browse_button = ttk.Button(button_frame, text="Browse Files...", command=self._browse_files)
        browse_button.pack(side=tk.LEFT, padx=5)

        settings_button = ttk.Button(button_frame, text="Settings", command=self._show_settings)
        settings_button.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(main_frame, text=f"Ready. Max words per file: {self.settings.get('max_words'):,}")
        self.status_label.pack(pady=5, fill=tk.X)

        self.progress_bar = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(pady=5, fill=tk.X)

        # Set up a file drop handler (simplified, without complex drag-drop)
        self.root.bind("<KeyPress>", self._handle_key)

    def _handle_key(self, event):
        """Simple keyboard handler for testing."""
        if event.char == 'q':
            self.root.quit()

    def _browse_files(self):
        """Show file dialog to select files."""
        files = filedialog.askopenfilenames(
            title="Select files to split",
            filetypes=(("Documents", "*.docx *.txt"), ("All files", "*.*"))
        )
        if files:
            self._process_files(files)

    def run(self):
        """Run the main event loop."""
        try:
            # Set up a timer to check the queue periodically
            self._check_queue()

            # Start the main loop
            self.root.mainloop()

        except Exception as e:
            self.logger.exception(f"Error in main loop: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

        finally:
            # Wait for active threads to complete
            for thread in self.active_threads:
                if thread.is_alive():
                    thread.join(timeout=1.0)

    def _process_files(self, files):
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
                self.logger.warning(f"Skipping unsupported file: {file}")
                self.status_label.config(text=f"Skipping unsupported file: {os.path.basename(file)}")

        if not valid_files:
            self.status_label.config(text="No valid files selected.")
            return

        # Update status
        self.status_label.config(text=f"Processing {len(valid_files)} file(s)...")
        self.progress_bar['value'] = 0

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
        """Check the queue for thread updates and schedule next check."""
        try:
            while True:
                action, data = self.queue.get_nowait()

                if action == "status":
                    self.status_label.config(text=data)
                elif action == "progress":
                    self.progress_bar['value'] = data

                self.queue.task_done()
        except queue.Empty:
            pass

        # Schedule next check
        self.root.after(100, self._check_queue)

    def _show_settings(self):
        """Show the settings dialog."""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.grab_set()  # Make modal

        frame = ttk.Frame(settings_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        # Max words
        ttk.Label(frame, text="Maximum words per file:").grid(row=0, column=0, sticky=tk.W, pady=5)
        max_words_var = tk.StringVar(value=str(self.settings.get("max_words")))
        max_words_entry = ttk.Entry(frame, textvariable=max_words_var, width=10)
        max_words_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        ttk.Label(frame, text="(1,000 - 100,000)").grid(row=0, column=2, sticky=tk.W, pady=5)

        # Output folder
        ttk.Label(frame, text="Output folder:").grid(row=1, column=0, sticky=tk.W, pady=5)
        output_folder_var = tk.StringVar(value=self.settings.get("output_folder"))
        output_folder_entry = ttk.Entry(frame, textvariable=output_folder_var, width=30)
        output_folder_entry.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5)

        def browse_folder():
            folder = filedialog.askdirectory()
            if folder:
                output_folder_var.set(folder)

        ttk.Button(frame, text="Browse...", command=browse_folder).grid(row=1, column=3, pady=5)

        # Checkboxes
        preserve_formatting_var = tk.BooleanVar(value=self.settings.get("preserve_formatting"))
        ttk.Checkbutton(frame, text="Preserve formatting", variable=preserve_formatting_var).grid(
            row=2, column=0, columnspan=4, sticky=tk.W, pady=5)

        skip_under_limit_var = tk.BooleanVar(value=self.settings.get("skip_under_limit"))
        ttk.Checkbutton(frame, text="Skip files under word limit", variable=skip_under_limit_var).grid(
            row=3, column=0, columnspan=4, sticky=tk.W, pady=5)

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=4, pady=10)

        def save_settings():
            try:
                # Validate and update settings
                max_words = int(max_words_var.get())
                if max_words < 1000 or max_words > 100000:
                    messagebox.showerror("Error", "Maximum words must be between 1,000 and 100,000.")
                    return

                output_folder = output_folder_var.get()
                if not output_folder:
                    messagebox.showerror("Error", "Output folder cannot be empty.")
                    return

                # Update settings
                self.settings.set("max_words", max_words)
                self.settings.set("output_folder", output_folder)
                self.settings.set("preserve_formatting", preserve_formatting_var.get())
                self.settings.set("skip_under_limit", skip_under_limit_var.get())

                # Save settings
                self.settings.save()

                # Update status
                self.status_label.config(text=f"Settings saved. Max words per file: {max_words:,}")

                # Close settings window
                settings_window.destroy()

            except ValueError:
                messagebox.showerror("Error", "Invalid value for maximum words.")

        def reset_defaults():
            if messagebox.askyesno("Reset", "Reset all settings to defaults?"):
                self.settings.reset()
                settings_window.destroy()
                self._show_settings()

        ttk.Button(button_frame, text="Save", command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset to Defaults", command=reset_defaults).pack(side=tk.LEFT, padx=5)