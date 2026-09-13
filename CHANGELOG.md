# Changelog

All notable changes to this project will be documented in this file.

## [0.7.1] - 2026-09-13

### Added
- **Comprehensive Settings Audit & Expansion**:
  - **Default Model**: Select preferred default model from installed Ollama models to auto-select on launch.
  - **Default Persona**: Preselect starting assistant persona (`🤖 General Assistant`, `💻 Coding Assistant`, etc.) for new conversations.
  - **Generation Temperature**: Smooth slider control (0.00 – 1.00) with live value badge, directly wired to Ollama generation parameters.
  - **Context History Limit**: Configurable chat history depth (4 – 100 messages) passed into LLM context window.
  - **Max Recalled Memories**: Configurable limit for remembered facts injected into prompts (1 – 20 items).
  - **RAG Fine-Tuning**: In-app controls for retrieved chunks (Top-K) and cosine similarity threshold.
  - **Manage Knowledge Library Button**: Direct access to the Knowledge Base document manager from Settings.
  - **Data & Storage Card**: Dedicated maintenance section displaying live SQLite database path, file size, safe `VACUUM` defragmentation, and "Clear All Chats" action.
- **Top-Bar Context Controls**:
  - Added dedicated `🧠 Memory: On / Off ▾` selector alongside `📚 Knowledge: Off / All / N Docs ▾` with full scoping modal.
- **High-Performance PDF Parsing**: Ingest complex PDF documents with page tracking using PyMuPDF / Fitz.

### Fixed
- **Persona Truncation**: Expanded top-bar label width and combobox width to 165px, ensuring persona names like `🤖 General Assistant` display in full without clipping.
- **Collapsed Sidebar Archive Icon**: Restored the missing `📦` Archive View icon in the 56px collapsed sidebar navigation rail.
- **Light Theme Dropdown Popups**: Added global stylesheet rules for `QComboBox QAbstractItemView` ensuring clean card background (`#FFFFFF`), crisp dark text (`#1F2328`), and safety orange selection highlights instead of dark Linux system palette fallback.
- **Settings Dialog X-Axis Lock**: Fixed horizontal scrolling overflow in settings dialog cards.

## [0.7.0] - 2026-09-12

### Added
- **In-App Model Management**: Pull new models with real-time download progress, delete models, and view model parameter details (<kbd>Ctrl+M</kbd>).
- **Prompt Presets / Personas**: 6 specialized personas (General Assistant, Senior Software Engineer, Linux System Administrator, SQL Database Expert, Technical Writer, Executive Summarizer) selectable from the top bar.
- **Spotlight-style Quick Mini-Chat**: Lightweight floating HUD popup for rapid queries (<kbd>Ctrl+Space</kbd> / <kbd>Ctrl+Shift+Space</kbd>) with "Open in Full Chat" promotion.
- **System Tray & Desktop Notifications**: Background tray icon with quick actions and native desktop notifications when generation finishes in the background.
- **Collapsible Sidebar**: Compact 56px icon-rail mode vs 260px expanded mode (<kbd>Ctrl+B</kbd>).
- **Status Bar Statistics & Token Speed Meter**: Real-time generation speed indicator (tokens/sec), active conversation message counter, and memory/RAG source indicators.
- **Conversation Context Menu**: Right-click menu on sidebar chats with Pin to Top, Archive, Rename, Export (Markdown, Text, JSON), and Delete.
- **Message Context Menu & Actions**: Right-click menu on message bubbles for Copy Text, Copy Markdown, Regenerate, and Delete Message.
- **Keyboard Shortcuts Help Modal**: Searchable, categorized modal showcasing all registered shortcuts (<kbd>Ctrl+/</kbd>, <kbd>?</kbd>, <kbd>F1</kbd>, TopBar <kbd>⌨️</kbd>).
- **Conversation Export**: Export chat sessions to Markdown (`.md`), Plain Text (`.txt`), and JSON (`.json`).

### Fixed
- Fixed SQLite RAG document chunk commit transaction bug in `document_repository.py`.
- Fixed UI message duplication bug when regenerating responses.
- Fixed `on_message_removed` scope issue in `chat_window.py`.

## [0.6.0] - 2026-08-17

### Added
- Modern Linux desktop packaging.
- Ubuntu `.deb` package generation script.
- Portable `AppImage` generation script.
- Desktop launcher (`localchat.desktop`) and application icon integration.
- Production PyInstaller build configuration.
- Unified resource path management for PyInstaller bundles.
- Standardized Linux data paths (`~/.config/rootChat`, `~/.local/share/rootChat`, `~/.local/state/rootChat`).
- Automatic database path migration for legacy installations.
- Centralized version tracking (`version.py`).

### Changed
- Refactored `AppConfig`, `DatabaseManager`, and `Logger` to strictly use Linux standard XDG directories instead of hardcoded paths.
- Completely removed inline CSS in favor of a global token-based Design System.
- Modernized all UI components including sidebar grouping, chat windows, message styling, and settings.

### Limitations
- Ollama must be installed separately (not bundled).
