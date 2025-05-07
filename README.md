# Manusplit

A minimal, fast, purpose-built desktop app for splitting large documents (.docx and .txt) into smaller parts based on word count.

## Purpose

Manusplit helps you break down large text documents into smaller chunks for use with AI knowledge bases that have word count limits (e.g., OpenAI's Custom GPT). Simply drag and drop your files, and Manusplit automatically splits them into compliant parts.

## Key Features

- **Simple Interface**: Drag and drop files for immediate processing
- **Word-Based Splitting**: Intelligently splits on paragraph boundaries
- **Format Preservation**: Maintains basic text formatting
- **Multiple File Support**: Process batch files at once
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Requirements

- Python 3.9 or newer (3.13+ recommended for best performance)
- Dependencies: python-docx, PySimpleGUI, requests

## Installation

### Option 1: Download Pre-built Binaries

Download the latest release for your platform from the [Releases](https://github.com/yourname/manusplit/releases) page.

### Option 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/yourname/manusplit.git
cd manusplit

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Usage

1. Launch Manusplit
2. Drag and drop .docx or .txt files into the window (or use the Browse button)
3. Files are automatically processed using current settings
4. Split parts are saved to the configured output folder

## Settings

Access settings by clicking the gear icon:

- **Maximum words per file**: Target word count per output (1,000-100,000)
- **Output folder**: Where split files are saved
- **Preserve formatting**: Keep basic text formatting (bold, italic, etc.)
- **Skip files under limit**: Don't process files below the word limit
- **Theme**: Light, Dark, or System default
- **Check for updates**: Automatically check for new versions

## Development

### Setup Environment

```bash
# Install development dependencies
pip install -r requirements.txt pytest

# Run tests
pytest tests/
```

### Building Executables

```bash
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --windowed --onefile --icon=assets/icon.ico main.py
```

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Future Plans

- CLI version
- Section-aware splitting (by chapters/headings)
- Table of contents generation
- Merge tool for rejoining parts
- i18n support
