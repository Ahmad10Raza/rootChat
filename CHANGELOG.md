# Changelog

All notable changes to this project will be documented in this file.

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
