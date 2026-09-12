# Contributing to rootChat

Thank you for your interest in contributing to **rootChat**! rootChat is an open-source, privacy-first local AI desktop assistant for Linux.

---

## Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free environment for everyone. Please be respectful, constructive, and kind in all issues, pull requests, and discussions.

---

## How Can I Contribute?

### 1. Reporting Bugs
- Search existing [Issues](https://github.com/Ahmad10Raza/rootChat/issues) to verify the bug hasn't already been reported.
- If not, open a new issue using the **Bug Report** template.
- Include clear reproduction steps, your OS/Desktop Environment, rootChat version, and terminal logs if applicable.

### 2. Suggesting Enhancements
- Check [Discussions](https://github.com/Ahmad10Raza/rootChat/discussions) and [Issues](https://github.com/Ahmad10Raza/rootChat/issues) to see if it has already been requested.
- Submit a new issue using the **Feature Request** template explaining the use case and proposed UX.

### 3. Code Contributions
- Pick an existing open issue or open a new issue to discuss significant changes before writing code.
- Follow the development setup below.

---

## Development Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Linux (Ubuntu 22.04 / 24.04 LTS recommended)
- Git
- Local [Ollama](https://ollama.ai) instance running on `http://localhost:11434`

### Steps

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/Ahmad10Raza/rootChat.git
   cd rootChat
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

---

## Running Tests

All code changes should pass the automated test suite before submitting a pull request.

Run the tests using `unittest`:
```bash
python -m unittest discover -s tests
```

> **Note on Test Isolation:**  
> Tests use isolated temporary databases and configuration files. Running tests will never overwrite your live `~/.config/rootChat/config.json` or personal chat database.

---

## Project Structure

```
rootChat/
├── app.py                     # Application entry point & process initialization
├── version.py                 # Central version declaration (e.g. 0.7.0)
├── core/                      # Business logic, Ollama API client, threads, state
│   ├── app_config.py          # Persistent configuration manager
│   ├── app_state.py           # Reactive application state
│   ├── chat_manager.py        # Chat orchestration & message streaming
│   ├── ollama_client.py       # REST client for Ollama API
│   ├── memory_manager.py      # Local memory recall engine
│   └── document_manager.py    # Local document ingestion & RAG
├── database/                  # SQLite schema and repositories
│   ├── database.py            # SQLite connection pool & migrations
│   ├── schema.py              # DDL schema definitions
│   └── repositories/          # Conversation, Message, and Memory data access
├── ui/                        # PySide6 desktop interface components
│   ├── main_window.py         # Main application window & action routing
│   ├── chat_window.py         # Message list viewport & composer
│   ├── message_widget.py      # Individual message card & markdown/code blocks
│   ├── sidebar.py             # Chat history, search, and archive controls
│   ├── settings_dialog.py     # Modern scrollable settings modal
│   ├── model_manager_dialog.py# Pull/delete Ollama models dialog
│   ├── mini_chat_dialog.py    # Spotlight HUD overlay (Ctrl+Space)
│   └── theme/                 # Centralized design tokens (Safety Orange palette)
├── resources/                 # Icons, desktop launchers, and SVG assets
│   ├── icons/                 # Multi-resolution PNG and SVG icons
│   └── desktop/               # FreeDesktop .desktop specification
├── packaging/                 # PyInstaller spec and Debian/AppImage build scripts
│   ├── rootChat.spec          # PyInstaller bundle specification
│   └── scripts/build_linux.sh # Automated .deb and .AppImage build pipeline
└── tests/                     # Unit tests
```

---

## Building Linux Release Packages

To test packaging changes:

```bash
bash packaging/scripts/build_linux.sh
```

Ensure that:
1. `dist/rootChat_*.deb` installs cleanly on a standard Ubuntu system.
2. `dist/rootChat-*.AppImage` executes directly without missing dynamic library dependencies.

---

## Pull Request Guidelines

1. Create a descriptive feature branch:
   ```bash
   git checkout -b feat/my-new-feature
   ```
2. Make your changes adhering to PEP 8 styling.
3. Add unit tests for any new logic or bug fixes.
4. Verify all tests pass (`python -m unittest discover -s tests`).
5. Commit with a clear message following [Conventional Commits](https://www.conventionalcommits.org/):
   ```bash
   git commit -m "feat(ui): add new keyboard shortcut for model switching"
   ```
6. Push to your fork and submit a Pull Request to `main`.
