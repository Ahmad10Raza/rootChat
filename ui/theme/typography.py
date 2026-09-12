"""Typography system for rootChat."""

from PySide6.QtGui import QFont, QFontDatabase


def get_preferred_font_family() -> str:
    """Returns the best available font family on this system."""
    available = QFontDatabase.families()
    
    preferences = ["Inter", "Noto Sans", "Ubuntu", "Cantarell", "DejaVu Sans", "Segoe UI"]
    for font in preferences:
        if font in available:
            return font
    
    # Fallback to system default sans-serif
    return "sans-serif"


def get_mono_font_family() -> str:
    """Returns the best available monospace font family."""
    available = QFontDatabase.families()
    
    preferences = ["JetBrains Mono", "Fira Code", "Source Code Pro", "Ubuntu Mono", "DejaVu Sans Mono", "Consolas"]
    for font in preferences:
        if font in available:
            return font
    
    return "monospace"


class FontSizes:
    """Standardized font sizes in pixels."""
    TITLE = 20
    HEADING = 16
    BODY = 14
    CHAT_BODY = 15
    CHAT_SIDEBAR = 13
    SMALL = 12
    CAPTION = 11
    CODE = 13
