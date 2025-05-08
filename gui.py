"""
Manusplit - Elegant, minimal interface for document splitting.
Horizontal layout with integrated design and darker theme.
"""
import sys
import os
import logging
import json
import traceback
from pathlib import Path

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLabel, QPushButton, QFileDialog,
                           QFrame, QScrollArea, QLineEdit, QSplitter)
from PyQt6.QtGui import (QFont, QFontMetrics, QDragEnterEvent, QDropEvent,
                       QCursor, QPainter, QColor, QIntValidator, QPixmap)
from PyQt6.QtCore import (Qt, QThread, pyqtSignal, QObject, QSize, QPoint,
                        QPropertyAnimation, QEasingCurve, QVariantAnimation,
                        pyqtProperty, QTimer)
from PyQt6.QtSvg import QSvgRenderer

# Import your existing components
from settings import Settings
from splitter import DocumentSplitter
from utils import setup_logging
import version


class ElegantFrame(QFrame):
    """A beautifully styled frame with subtle shadows and rounded corners."""

    def __init__(self, parent=None, radius=12, bg_color="#1a1a1a", shadow=True, border=False, border_color=None, border_style="solid"):
        super().__init__(parent)
        self.radius = radius
        self.bg_color = bg_color
        self.has_shadow = shadow
        self.has_border = border
        self.border_color = border_color or "#333333"
        self.border_style = border_style
        self.setStyleSheet(f"""
            background-color: transparent;
            border: none;
        """)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        """Custom paint event to draw rounded corners and shadows."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw shadow if enabled
        if self.has_shadow:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 20))
            painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), self.radius, self.radius)

        # Draw main background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.bg_color))
        painter.drawRoundedRect(self.rect(), self.radius, self.radius)

        # Draw border if enabled
        if self.has_border:
            if self.border_style == "dashed":
                pen = painter.pen()
                pen.setColor(QColor(self.border_color))
                pen.setStyle(Qt.PenStyle.DashLine)
                pen.setWidth(1)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), self.radius, self.radius)
            else:
                painter.setPen(QColor(self.border_color))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), self.radius, self.radius)


class DownArrowWidget(QWidget):
    """Widget that displays a down arrow."""
    def __init__(self, parent=None, color="#555555", size=48):
        super().__init__(parent)
        self.color = color
        self.size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        """Paint the down arrow."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Define arrow points
        width, height = self.width(), self.height()
        arrow_width = width * 0.5
        arrow_height = height * 0.3

        points = [
            QPoint(width / 2 - arrow_width / 2, height / 2 - arrow_height / 2),  # top-left
            QPoint(width / 2 + arrow_width / 2, height / 2 - arrow_height / 2),  # top-right
            QPoint(width / 2, height / 2 + arrow_height / 2)                     # bottom
        ]

        # Draw arrow
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.color))
        painter.drawPolygon(points)


class Worker(QObject):
    """Worker thread to process files in the background."""
    fileProgress = pyqtSignal(str, int)  # filepath, progress percentage
    fileComplete = pyqtSignal(str, int)  # filepath, parts created
    fileError = pyqtSignal(str, str)     # filepath, error message
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
            for file_path in self.files:
                try:
                    # Create an output folder for this file
                    self._prepare_output_folder(file_path)

                    # Process the file
                    result = self.splitter.process_file(
                        file_path,
                        callback=lambda status, progress, message:
                            self.fileProgress.emit(file_path, progress)
                    )

                    # Report completion
                    if result["success"]:
                        self.fileComplete.emit(file_path, result["parts_created"])
                    else:
                        self.fileError.emit(file_path, result["message"])
                except Exception as e:
                    self.logger.exception(f"Error processing file {file_path}: {str(e)}")
                    self.fileError.emit(file_path, str(e))

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

            # Create a clean folder name
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


class FileCard(QWidget):
    """An elegantly designed file card."""

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.basename = os.path.basename(file_path)
        self.extension = os.path.splitext(self.basename)[1][1:].upper()
        self.parts_count = 0
        self.is_processing = False
        self.progress = 0

        self.setup_ui()

    def setup_ui(self):
        """Set up the file card UI."""
        # Main layout with larger margins for cleaner look
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # Base widget is transparent
        self.setStyleSheet("""
            background-color: transparent;
            color: #ffffff;
        """)

        # Create background frame
        self.bg_frame = ElegantFrame(self, radius=8, bg_color="#1a1a1a")
        self.bg_frame.setGeometry(self.rect())

        # File type indicator
        type_container = QWidget()
        type_container.setFixedSize(34, 34)
        type_container.setStyleSheet("""
            background-color: #2a2a2a;
            border-radius: 17px;
        """)

        type_layout = QVBoxLayout(type_container)
        type_layout.setContentsMargins(0, 0, 0, 0)

        self.type_label = QLabel(self.extension[:3])  # Limit to 3 chars
        self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.type_label.setStyleSheet("""
            color: #ffffff;
            font-size: 11px;
            font-weight: 600;
            background-color: transparent;
        """)
        type_layout.addWidget(self.type_label)

        layout.addWidget(type_container)

        # File details container
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(2)

        # Filename
        self.filename_label = QLabel(self._truncate_filename(self.basename, 250))
        self.filename_label.setStyleSheet("""
            color: #ffffff;
            font-size: 13px;
            font-weight: 500;
            background-color: transparent;
        """)
        self.filename_label.setToolTip(self.basename)
        details_layout.addWidget(self.filename_label)

        # Status line
        self.status_label = QLabel("Waiting")
        self.status_label.setStyleSheet("""
            color: #888888;
            font-size: 12px;
            background-color: transparent;
        """)
        details_layout.addWidget(self.status_label)

        layout.addWidget(details_widget, 1)  # Stretch

        # Progress count/parts
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("""
            color: #0078d4;
            font-size: 14px;
            font-weight: 600;
            background-color: transparent;
            padding-right: 4px;
        """)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.progress_label.setFixedWidth(70)
        layout.addWidget(self.progress_label)

        # Update on resize
        self.resizeEvent = self._on_resize

    def _on_resize(self, event):
        """Handle resize events."""
        # Update frame size
        self.bg_frame.setGeometry(self.rect())

    def _truncate_filename(self, filename, max_width):
        """Truncate filename to fit in the available width."""
        metrics = QFontMetrics(self.font())
        if metrics.horizontalAdvance(filename) <= max_width:
            return filename

        # Truncate the middle
        base, ext = os.path.splitext(filename)
        while metrics.horizontalAdvance(f"{base[:-3]}...{ext}") > max_width and len(base) > 10:
            base = base[:-1]

        return f"{base[:-3]}...{ext}"

    def update_progress(self, progress):
        """Update processing progress."""
        self.progress = progress
        self.is_processing = True

        # Update labels
        self.status_label.setText("Processing")
        self.status_label.setStyleSheet("""
            color: #0078d4;
            font-size: 12px;
            background-color: transparent;
        """)

        self.progress_label.setText(f"{progress}%")

        # Progress-colored background - subtle gradient
        color = self._interpolate_color("#1a3a5a", "#1a1a1a", progress/100)
        self.bg_frame.bg_color = color
        self.bg_frame.update()

    def set_completed(self, parts_count):
        """Mark as completed with parts count."""
        self.parts_count = parts_count
        self.is_processing = False

        # Update labels
        self.status_label.setText("Completed")
        self.status_label.setStyleSheet("""
            color: #2fcc71;
            font-size: 12px;
            background-color: transparent;
        """)

        self.progress_label.setText(f"{parts_count} parts")
        self.progress_label.setStyleSheet("""
            color: #2fcc71;
            font-size: 14px;
            font-weight: 600;
            background-color: transparent;
            padding-right: 4px;
        """)

        # Reset background with slight green tint
        self.bg_frame.bg_color = "#1a291f"
        self.bg_frame.update()

    def set_error(self, error_message):
        """Mark as error with message."""
        self.is_processing = False

        # Update labels
        self.status_label.setText("Error")
        self.status_label.setStyleSheet("""
            color: #e74c3c;
            font-size: 12px;
            background-color: transparent;
        """)

        self.progress_label.setText("Failed")
        self.progress_label.setStyleSheet("""
            color: #e74c3c;
            font-size: 14px;
            font-weight: 600;
            background-color: transparent;
            padding-right: 4px;
        """)
        self.status_label.setToolTip(error_message)

        # Error background
        self.bg_frame.bg_color = "#2a1a1a"
        self.bg_frame.update()

    def _interpolate_color(self, color1, color2, factor):
        """Interpolate between two colors."""
        r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)

        r = int(r1 + factor * (r2 - r1))
        g = int(g1 + factor * (g2 - g1))
        b = int(b1 + factor * (b2 - b1))

        return f"#{r:02x}{g:02x}{b:02x}"


class AnimatedButton(QPushButton):
    """Base class for buttons with smooth macOS-like animation."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Animation properties
        self._animation_progress = 0.0
        self._animation = QVariantAnimation()
        self._animation.setDuration(75)  # 150ms animation
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)  # macOS-like easing
        self._animation.valueChanged.connect(self._update_animation)

        # Keep track of mouse state
        self._is_pressed = False
        self._is_hovered = False

        # Set transparent background so we can paint our own
        self.setStyleSheet("""
            QPushButton {
                color: #ffffff;
                background-color: transparent;
                border: none;
                padding: 6px 12px;
                font-size: 13px;
                text-align: center;
            }
        """)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _get_animation_progress(self):
        return self._animation_progress

    def _set_animation_progress(self, progress):
        self._animation_progress = progress
        self.update()  # Trigger repaint

    # Define animation property
    animation_progress = pyqtProperty(float, _get_animation_progress, _set_animation_progress)

    def _update_animation(self, value):
        """Update animation state."""
        self.animation_progress = value

    def enterEvent(self, event):
        """Handle mouse enter event."""
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave event."""
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press with animation start."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = True

            # Start animation from 0 to 1
            self._animation.stop()
            self._animation.setStartValue(0.0)
            self._animation.setEndValue(1.0)
            self._animation.start()

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release with animation back."""
        if event.button() == Qt.MouseButton.LeftButton and self._is_pressed:
            self._is_pressed = False

            # Start animation from current value back to 0
            self._animation.stop()
            self._animation.setStartValue(self._animation_progress)
            self._animation.setEndValue(0.0)
            self._animation.start()

        super().mouseReleaseEvent(event)


class ElegantButton(AnimatedButton):
    """Beautifully styled button with smooth macOS-like animations."""

    def __init__(self, text, parent=None, primary=False, icon=None):
        super().__init__(text, parent)
        self.is_primary = primary
        self.icon_path = icon

        # Set button styles based on primary status
        if primary:
            self.normal_color = "#0078d4"
            self.hover_color = "#0086f0"
            self.pressed_color = "#005a9e"  # Darker for press animation
        else:
            self.normal_color = "#1e1e1e"
            self.hover_color = "#2a2a2a"
            self.pressed_color = "#101010"  # Darker for press animation

        # Set font weight
        if primary:
            self.setStyleSheet("""
                QPushButton {
                    color: #ffffff;
                    background-color: transparent;
                    border: none;
                    padding: 6px 12px;
                    font-size: 13px;
                    font-weight: 600;
                    text-align: center;
                }
            """)

    def paintEvent(self, event):
        """Custom paint event to draw animated rounded button."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Determine background color based on state and animation
        if self._is_pressed or self._animation_progress > 0:
            # Animate between normal/hover color and pressed color based on animation progress
            if self._is_hovered and not self._is_pressed:
                base_color = self.hover_color
            else:
                base_color = self.normal_color

            # Mix colors based on animation progress
            color = self._mix_colors(base_color, self.pressed_color, self._animation_progress)
            painter.setBrush(QColor(color))
        elif self._is_hovered:
            painter.setBrush(QColor(self.hover_color))
        else:
            painter.setBrush(QColor(self.normal_color))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)

        # Pass to standard button painting for text/icon
        super(AnimatedButton, self).paintEvent(event)

    def _mix_colors(self, color1, color2, factor):
        """Mix two hex colors based on factor (0-1)."""
        r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)

        r = int(r1 + factor * (r2 - r1))
        g = int(g1 + factor * (g2 - g1))
        b = int(b1 + factor * (b2 - b1))

        return f"#{r:02x}{g:02x}{b:02x}"


class DestinationButton(AnimatedButton):
    """Button showing the current destination folder with animations."""

    def __init__(self, path, parent=None):
        # Just use an empty string for text, we'll set it in updateStyle
        super().__init__("", parent)
        self.full_path = path

        # Fixed size to match word limit input
        self.setFixedHeight(28)
        self.setFixedWidth(120)

        # Style the button
        self.normal_color = "#1e1e1e"
        self.hover_color = "#2a2a2a"
        self.pressed_color = "#101010"  # Darker for press animation

        # Set initial text
        self.update_path(path)

    def paintEvent(self, event):
        """Custom paint event to draw animated rounded button."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Determine background color based on state and animation
        if self._is_pressed or self._animation_progress > 0:
            # Animate between normal/hover color and pressed color based on animation progress
            if self._is_hovered and not self._is_pressed:
                base_color = self.hover_color
            else:
                base_color = self.normal_color

            # Mix colors based on animation progress
            color = self._mix_colors(base_color, self.pressed_color, self._animation_progress)
            painter.setBrush(QColor(color))
        elif self._is_hovered:
            painter.setBrush(QColor(self.hover_color))
        else:
            painter.setBrush(QColor(self.normal_color))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 6, 6)

        # Pass to standard button painting for text
        super(AnimatedButton, self).paintEvent(event)

    def _mix_colors(self, color1, color2, factor):
        """Mix two hex colors based on factor (0-1)."""
        r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)

        r = int(r1 + factor * (r2 - r1))
        g = int(g1 + factor * (g2 - g1))
        b = int(b1 + factor * (b2 - b1))

        return f"#{r:02x}{g:02x}{b:02x}"

    def _format_path(self, path):
        """Format path for display - shorten if needed."""
        if len(path) > 18:  # Shorter limit to fit button
            # Get last folder name
            parts = path.split(os.path.sep)
            last_part = parts[-1] if parts[-1] else parts[-2]  # Handle trailing slash
            if len(last_part) > 16:
                last_part = last_part[:14] + "..."
            return f".../{last_part}"
        return path

    def update_path(self, path):
        """Update the path."""
        self.full_path = path
        self.setText(self._format_path(path))
        self.setToolTip(path)


class WordLimitInput(QWidget):
    """Elegant word limit input with label."""

    valueChanged = pyqtSignal(int)

    def __init__(self, initial_value=50000, parent=None):
        super().__init__(parent)
        self.value = initial_value
        self.setup_ui()

    def setup_ui(self):
        """Set up the word limit input UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Label
        self.label = QLabel("Max words:")
        self.label.setStyleSheet("""
            color: #aaaaaa;
            font-size: 13px;
            background-color: transparent;
        """)
        layout.addWidget(self.label)

        # Spacer to push input to the right, aligned with Save To
        layout.addStretch(1)

        # Input field container with appropriate width
        input_container = QWidget()
        input_container.setFixedSize(120, 28)  # Appropriate width for content
        input_container.setStyleSheet("""
            background-color: #1e1e1e;
            border-radius: 6px;
        """)

        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(4, 0, 4, 0)
        input_layout.setSpacing(0)

        # Text input for words
        self.input = QLineEdit(str(self.value))
        self.input.setStyleSheet("""
            color: #ffffff;
            font-size: 13px;
            background-color: transparent;
            border: none;
            padding: 0;
        """)
        self.input.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Only allow integers
        validator = QIntValidator(1000, 1000000)
        self.input.setValidator(validator)

        self.input.textChanged.connect(self._value_changed)
        input_layout.addWidget(self.input)

        layout.addWidget(input_container)

    def _value_changed(self, text):
        """Handle value changes."""
        if text:
            try:
                value = int(text)
                self.value = value
                self.valueChanged.emit(value)
            except ValueError:
                pass

    def get_value(self):
        """Get the current value."""
        return self.value

    def set_value(self, value):
        """Set a new value."""
        self.value = value
        self.input.setText(str(value))


class ManusplitApp(QMainWindow):
    """Redesigned horizontal layout UI for Manusplit."""

    def __init__(self, settings):
        super().__init__()
        self.settings = settings

        # Default to always preserve formatting and process all files
        self.settings.set("preserve_formatting", True)
        self.settings.set("skip_under_limit", False)

        self.splitter = DocumentSplitter(settings)
        self.splitter.current_output_folder = settings.get("output_folder")

        self.logger = logging.getLogger(__name__)
        self.processed_files = {}  # Map filepath to FileCard widgets

        # Set up the UI
        self.setWindowTitle("Manusplit")
        self.setMinimumWidth(700)  # Wider minimum width
        self.setMinimumHeight(450)  # Taller minimum height

        # Start with larger size
        self.resize(800, 500)  # Wider default

        # Set app style - darker theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #121212;
                color: #ffffff;
                font-family: Arial, sans-serif;
            }
            QScrollBar:vertical {
                border: none;
                background: #1e1e1e;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QSplitter::handle {
                background-color: #2a2a2a;
                width: 1px;
            }
        """)

        self.setup_ui()

        # Enable drag and drop for main window
        self.setAcceptDrops(True)

        # Worker thread
        self.worker_thread = None

    def setup_ui(self):
        """Set up the UI with horizontal layout."""
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)  # Smaller margins
        main_layout.setSpacing(0)

        # Create horizontal splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        # Left side - Files panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 12, 0)  # Less right margin
        left_layout.setSpacing(10)  # Tighter spacing

        # Header for files
        files_header = QLabel("Files")
        files_header.setStyleSheet("""
            color: #ffffff;
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 4px;
        """)
        left_layout.addWidget(files_header)

        # Files list container with frame
        files_frame = ElegantFrame(radius=10, bg_color="#171717")
        files_frame_layout = QVBoxLayout(files_frame)
        files_frame_layout.setContentsMargins(10, 10, 10, 10)  # Smaller padding
        files_frame_layout.setSpacing(6)  # Tighter spacing

        # Files list with scroll
        self.files_list = QWidget()
        self.files_layout = QVBoxLayout(self.files_list)
        self.files_layout.setContentsMargins(0, 0, 0, 0)
        self.files_layout.setSpacing(4)  # Even tighter spacing
        self.files_layout.addStretch(1)  # Push content to top

        # Scroll area for files
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(self.files_list)
        files_frame_layout.addWidget(scroll_area)

        left_layout.addWidget(files_frame, 1)  # Stretch to fill

        # Right side - Drop zone and settings panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 0, 0, 0)  # Less left margin
        right_layout.setSpacing(10)  # Tighter spacing

        # Header for drop zone
        drop_header = QLabel("Add Files")
        drop_header.setStyleSheet("""
            color: #ffffff;
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 4px;
        """)
        right_layout.addWidget(drop_header)

        # Drop zone with dashed border and down arrow
        self.drop_zone = QWidget()
        # No fixed height to match files panel
        self.drop_zone.setAcceptDrops(True)

        drop_layout = QVBoxLayout(self.drop_zone)
        drop_layout.setContentsMargins(0, 0, 0, 0)  # No margins

        # Drop zone container with dashed border - STORE DIRECT REFERENCE
        self.drop_container = ElegantFrame(
            radius=10,
            bg_color="#171717",
            border=True,
            border_color="#444444",
            border_style="dashed"
        )

        # Content inside the dashed border
        drop_content_layout = QVBoxLayout(self.drop_container)
        drop_content_layout.setContentsMargins(16, 20, 16, 20)  # More top/bottom padding
        drop_content_layout.setSpacing(12)  # More space between elements
        drop_content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Down arrow - smaller and move closer to text
        self.arrow = DownArrowWidget(color="#666666", size=28)
        drop_content_layout.addWidget(self.arrow, 0, Qt.AlignmentFlag.AlignCenter)

        # Drop label - move closer to arrow
        self.drop_label = QLabel("Drop .docx or .txt files here")
        self.drop_label.setStyleSheet("""
            color: #888888;
            font-size: 14px;
            font-weight: 400;
            background-color: transparent;
            padding-top: 0;
        """)
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_content_layout.addWidget(self.drop_label)

        # More space before browse button
        drop_content_layout.addSpacing(12)

        # Browse button - now with animation
        self.browse_btn = ElegantButton("Browse Files", primary=False)
        self.browse_btn.clicked.connect(self.browse_files)
        drop_content_layout.addWidget(self.browse_btn, 0, Qt.AlignmentFlag.AlignCenter)

        # Add the framed container to the drop layout
        drop_layout.addWidget(self.drop_container)

        # Add drop zone to right panel
        right_layout.addWidget(self.drop_zone, 1)  # Stretch to fill

        # Settings section
        settings_header = QLabel("Settings")
        settings_header.setStyleSheet("""
            color: #ffffff;
            font-size: 15px;
            font-weight: 600;
            margin-top: 10px;
            margin-bottom: 4px;
        """)
        right_layout.addWidget(settings_header)

        # Settings container
        settings_panel = ElegantFrame(radius=10, bg_color="#171717")
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setContentsMargins(16, 16, 16, 16)
        settings_layout.setSpacing(12)

        # Word limit setting with right-aligned input
        self.word_limit = WordLimitInput(self.settings.get("max_words"))
        self.word_limit.valueChanged.connect(self.update_word_limit)
        settings_layout.addWidget(self.word_limit)

        # Save to location with matching right alignment
        save_to_container = QWidget()
        save_to_layout = QHBoxLayout(save_to_container)
        save_to_layout.setContentsMargins(0, 0, 0, 0)
        save_to_layout.setSpacing(8)

        # Label
        save_to_label = QLabel("Save to:")
        save_to_label.setStyleSheet("""
            color: #aaaaaa;
            font-size: 13px;
            background-color: transparent;
        """)
        save_to_layout.addWidget(save_to_label)

        # Add stretch to push button to the right, aligned with word input
        save_to_layout.addStretch(1)

        # Path button - entire button is clickable with animation
        self.destination_btn = DestinationButton(self.settings.get("output_folder"))
        self.destination_btn.clicked.connect(self.browse_destination)
        save_to_layout.addWidget(self.destination_btn)

        settings_layout.addWidget(save_to_container)

        # Add settings panel to right layout
        right_layout.addWidget(settings_panel)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        # Set initial sizes (left panel larger than right)
        splitter.setSizes([500, 300])  # 62.5/37.5 ratio

        # Add splitter to main layout
        main_layout.addWidget(splitter)

    def dragEnterEvent(self, event):
        """Enhanced drag enter handling."""
        if event.mimeData().hasUrls():
            # Now using direct reference to drop container
            self.drop_container.bg_color = "#1a2a3a"
            self.drop_container.border_color = "#0078d4"
            self.drop_container.update()

            self.drop_label.setStyleSheet("""
                color: #ffffff;
                font-size: 14px;
                font-weight: 400;
                background-color: transparent;
                padding-top: 0;
            """)
            self.arrow.color = "#0078d4"
            self.arrow.update()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """Enhanced drag leave handling."""
        # Now using direct reference to drop container
        self.drop_container.bg_color = "#171717"
        self.drop_container.border_color = "#444444"
        self.drop_container.update()

        self.drop_label.setStyleSheet("""
            color: #888888;
            font-size: 14px;
            font-weight: 400;
            background-color: transparent;
            padding-top: 0;
        """)
        self.arrow.color = "#666666"
        self.arrow.update()

    def dropEvent(self, event):
        """Enhanced drop handling."""
        if event.mimeData().hasUrls():
            # Now using direct reference to drop container
            self.drop_container.bg_color = "#171717"
            self.drop_container.border_color = "#444444"
            self.drop_container.update()

            self.drop_label.setStyleSheet("""
                color: #888888;
                font-size: 14px;
                font-weight: 400;
                background-color: transparent;
                padding-top: 0;
            """)
            self.arrow.color = "#666666"
            self.arrow.update()

            # Get valid files
            valid_files = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if not os.path.isfile(file_path):
                    continue

                _, ext = os.path.splitext(file_path.lower())
                if ext not in ['.docx', '.txt']:
                    continue

                # Only add if not already processed
                if file_path not in self.processed_files:
                    valid_files.append(file_path)

            # Process valid files
            if valid_files:
                self.process_files(valid_files)

            event.acceptProposedAction()

    def browse_files(self):
        """Browse for files via dialog."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files to Split",
            "",
            "Documents (*.docx *.txt)"
        )

        if files:
            # Filter already processed files
            new_files = [f for f in files if f not in self.processed_files]
            if new_files:
                self.process_files(new_files)

    def update_word_limit(self, value):
        """Update word limit setting."""
        self.settings.set("max_words", value)
        self.settings.save()

    def browse_destination(self):
        """Browse for destination folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Destination Folder",
            self.settings.get("output_folder")
        )

        if folder:
            self.settings.set("output_folder", folder)
            self.settings.save()
            self.splitter.current_output_folder = folder
            self.destination_btn.update_path(folder)

    def process_files(self, files):
        """Process files - maintains existing functionality."""
        # Prevent starting a new batch while a current processing thread is active
        if getattr(self, 'worker_thread', None) and self.worker_thread.isRunning():
            return
        try:
            # Add files to UI first
            for file_path in files:
                # Skip if already processed
                if file_path in self.processed_files:
                    continue

                # Create file card
                file_card = FileCard(file_path)

                # Add to map and UI
                self.processed_files[file_path] = file_card
                self.files_layout.insertWidget(self.files_layout.count() - 1, file_card)

            # Start worker thread if there are files to process
            if files:
                # Create thread and worker
                self.worker_thread = QThread()
                self.worker = Worker(self.splitter, files, self.settings)
                self.worker.moveToThread(self.worker_thread)

                # Connect signals
                self.worker_thread.started.connect(self.worker.process)
                self.worker.fileProgress.connect(self.update_file_progress)
                self.worker.fileComplete.connect(self.mark_file_complete)
                self.worker.fileError.connect(self.mark_file_error)
                self.worker.finished.connect(self.worker_thread.quit)
                self.worker_thread.finished.connect(self.worker.deleteLater)
                # Remove automatic thread deletion to prevent premature deletion
                # self.worker_thread.finished.connect(self.worker_thread.deleteLater)
                # Instead, clear the reference when finished
                self.worker_thread.finished.connect(lambda: setattr(self, 'worker_thread', None))

                # Start thread
                self.worker_thread.start()
        except Exception as e:
            self.logger.exception(f"Error processing files: {str(e)}")

    def update_file_progress(self, file_path, progress):
        """Update progress for a file."""
        if file_path in self.processed_files:
            self.processed_files[file_path].update_progress(progress)

    def mark_file_complete(self, file_path, parts_count):
        """Mark a file as completed."""
        if file_path in self.processed_files:
            self.processed_files[file_path].set_completed(parts_count)

    def mark_file_error(self, file_path, error_message):
        """Mark a file as errored."""
        if file_path in self.processed_files:
            self.processed_files[file_path].set_error(error_message)


class FirstRunScreen(QMainWindow):
    """Elegant first run welcome screen."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Welcome to Manusplit")
        self.resize(500, 280)
        self.output_path = os.path.join(os.path.expanduser("~"), "Documents", "Manusplit Files")
        self.result = False

        # Set app style - darker theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #121212;
                color: #ffffff;
                font-family: Arial, sans-serif;
            }
        """)

        self.setup_ui()

    def setup_ui(self):
        """Set up the welcome screen."""
        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Description - direct approach
        desc_label = QLabel("Select where you'd like to save split documents")
        desc_label.setStyleSheet("""
            color: #ffffff;
            font-size: 16px;
            font-weight: 500;
        """)
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)

        # Content frame
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        # Background frame
        self.content_bg = ElegantFrame(content_widget, radius=12, bg_color="#171717")
        self.content_bg.setGeometry(content_widget.rect())
        content_widget.resizeEvent = lambda e: self.content_bg.setGeometry(content_widget.rect())

        # Folder path display
        path_container = QWidget()
        path_layout = QHBoxLayout(path_container)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(10)

        self.path_label = QLabel(self.output_path)
        self.path_label.setStyleSheet("""
            color: #ffffff;
            font-size: 14px;
            background-color: #1a1a1a;
            border-radius: 6px;
            padding: 8px 12px;
        """)
        self.path_label.setFixedHeight(36)
        path_layout.addWidget(self.path_label, 1)

        # Use animated button
        browse_btn = ElegantButton("Browse", self)
        browse_btn.clicked.connect(self.browse_folder)
        path_layout.addWidget(browse_btn)

        content_layout.addWidget(path_container)

        # Add note
        note_label = QLabel("This folder will be created if it doesn't exist")
        note_label.setStyleSheet("""
            color: #888888;
            font-size: 13px;
            font-style: italic;
        """)
        content_layout.addWidget(note_label)

        # Add the content widget to main layout
        main_layout.addWidget(content_widget)

        # Add spacer
        main_layout.addStretch(1)

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(12)

        # Push to right
        buttons_layout.addStretch(1)

        # Continue button - with animation
        continue_btn = ElegantButton("Get Started", self, primary=True)
        continue_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(continue_btn)

        main_layout.addLayout(buttons_layout)

    def browse_folder(self):
        """Browse for output folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            self.output_path
        )

        if folder:
            self.output_path = folder
            self.path_label.setText(folder)

    def accept(self):
        """Accept and close."""
        self.result = True
        self.close()


# Utility functions
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

            # Default settings - always preserve formatting and process all files
            settings_dict = {
                "max_words": 100000,
                "output_folder": output_path,
                "preserve_formatting": True,
                "skip_under_limit": False
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

    # Use modern font
    font = QFont("Arial", 10)
    app.setFont(font)

    # Add exception hook to log uncaught exceptions
    def exception_hook(exctype, value, tb):
        logger.critical(f"Uncaught exception: {value}")
        logger.critical("".join(traceback.format_tb(tb)))
        sys.__excepthook__(exctype, value, tb)

    sys.excepthook = exception_hook

    try:
        # Show first run dialog if needed
        output_path = None
        if first_run := is_first_run():
            dialog = FirstRunScreen()
            dialog.show()

            # Run event loop until dialog is closed
            app.exec()

            if dialog.result:
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