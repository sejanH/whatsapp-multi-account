# WhatsApp Multi-Account Client

A PyQt5-based desktop application that allows you to run multiple WhatsApp Web accounts simultaneously in a single window using tabs. Each account maintains its own separate profile and storage, enabling you to use personal and business accounts simultaneously.

## Features

- **Multi-Account Support**: Run multiple WhatsApp accounts simultaneously
- **Tabbed Interface**: Easy switching between different accounts
- **Persistent Sessions**: Each account maintains its own login session and cookies
- **Separate Storage**: Unique storage path for each account profile
- **Custom User-Agent**: Optimized user agent to avoid "Browser not supported" messages

## Requirements

- Python 3.6 or higher
- PyQt5
- PyQtWebEngine
- PyInstaller (for building the executable)

## Required Python Scripts

- `main.py` — application entry point (multi-account UI and web views).

## Installation

### Prerequisites

**Install system dependencies**:
    ```bash
    # Ubuntu/Debian
    sudo apt-get install python3-pyqt5 python3-pyqt5.qtwebengine

    # Fedora/RHEL
    sudo dnf install python3-qt5 python3-qtwebengine
    ```
