"""Centralized theme manager for rootChat. Generates and applies QSS from design tokens."""

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from ui.theme.colors import DarkColors, LightColors
from ui.theme.typography import get_preferred_font_family, get_mono_font_family, FontSizes
from ui.theme.spacing import Spacing, Radius, Dimensions
from utils.resource_path import get_resource_path


class ThemeManager:
    """Manages application-wide theming. Generates QSS from centralized tokens."""
    
    _instance = None
    
    def __init__(self):
        self._mode = "dark"  # dark, light, system
        self._colors = DarkColors
        self._font_family = None
        self._mono_family = None
    
    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @property
    def colors(self):
        return self._colors
    
    @property
    def font_family(self):
        if self._font_family is None:
            self._font_family = get_preferred_font_family()
        return self._font_family
    
    @property
    def mono_family(self):
        if self._mono_family is None:
            self._mono_family = get_mono_font_family()
        return self._mono_family
    
    def set_mode(self, mode: str):
        """Set theme mode: 'dark', 'light', or 'system'."""
        self._mode = mode
        if mode == "dark":
            self._colors = DarkColors
        elif mode == "light":
            self._colors = LightColors
        else:
            # System: default to dark for now
            self._colors = DarkColors
    
    def apply(self, app: QApplication):
        """Apply the full application stylesheet."""
        app.setFont(QFont(self.font_family, FontSizes.BODY))
        app.setStyleSheet(self._generate_global_qss())
    
    def _generate_global_qss(self) -> str:
        c = self._colors
        ff = self.font_family
        mf = self.mono_family
        
        return f"""
        /* ==================== GLOBAL ==================== */
        QMainWindow {{
            background-color: {c.BG_PRIMARY};
            font-family: '{ff}';
        }}
        QWidget {{
            font-family: '{ff}';
            color: {c.TEXT_PRIMARY};
        }}
        QToolTip {{
            background-color: {c.BG_CARD};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.SM}px;
            padding: {Spacing.SM}px;
            font-size: {FontSizes.SMALL}px;
        }}
        
        /* ==================== SCROLLBARS ==================== */
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {c.SCROLLBAR};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c.SCROLLBAR_HOVER};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {c.SCROLLBAR};
            border-radius: 4px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {c.SCROLLBAR_HOVER};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: transparent;
        }}
        
        /* ==================== SIDEBAR ==================== */
        QWidget#Sidebar {{
            background-color: {c.BG_SIDEBAR};
            border-right: 1px solid {c.BORDER_SUBTLE};
        }}
        QPushButton#NewChatBtn {{
            background-color: {c.ACCENT};
            color: white;
            border: none;
            border-radius: {Radius.MD}px;
            padding: 10px 16px;
            font-size: {FontSizes.BODY}px;
            font-weight: 600;
            text-align: left;
        }}
        QPushButton#NewChatBtn:hover {{
            background-color: {c.ACCENT_HOVER};
        }}
        QPushButton#NewChatBtn:pressed {{
            background-color: {c.ACCENT_PRESSED};
        }}
        QLineEdit#SearchInput {{
            background-color: {c.BG_INPUT};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.MD}px;
            padding: 8px 12px 8px 32px;
            font-size: {FontSizes.BODY}px;
        }}
        QLineEdit#SearchInput:focus {{
            border-color: {c.ACCENT};
        }}
        QLabel#SectionLabel {{
            color: {c.TEXT_MUTED};
            font-size: {FontSizes.CAPTION}px;
            font-weight: 700;
            padding: 8px 4px 4px 4px;
            text-transform: uppercase;
        }}
        QListWidget#ChatList {{
            background-color: transparent;
            border: none;
            outline: none;
            font-size: {FontSizes.CHAT_SIDEBAR}px;
        }}
        QListWidget#ChatList::item {{
            color: {c.TEXT_SECONDARY};
            padding: 6px 10px;
            border-radius: {Radius.MD}px;
            margin: 1px 4px;
            font-size: {FontSizes.CHAT_SIDEBAR}px;
            min-height: 28px;
        }}
        QListWidget#ChatList::item:selected {{
            background-color: {c.BG_SELECTED};
            color: {c.TEXT_PRIMARY};
            font-weight: 500;
        }}
        QListWidget#ChatList::item:hover {{
            background-color: {c.BG_HOVER};
            color: {c.TEXT_PRIMARY};
        }}
        QPushButton#SidebarActionBtn {{
            background-color: transparent;
            color: {c.TEXT_SECONDARY};
            border: none;
            border-radius: {Radius.MD}px;
            padding: 8px 10px;
            font-size: {FontSizes.CHAT_SIDEBAR}px;
            text-align: left;
        }}
        QPushButton#SidebarActionBtn:hover {{
            background-color: {c.BG_HOVER};
            color: {c.TEXT_PRIMARY};
        }}
        
        /* ==================== ARCHIVE VIEW ROW ==================== */
        QFrame#ArchiveRow {{
            background-color: transparent;
            border-radius: {Radius.MD}px;
            padding: 2px 4px;
        }}
        QFrame#ArchiveRow:hover {{
            background-color: {c.BG_HOVER};
        }}
        QLabel#ArchiveIcon {{
            font-size: 13px;
        }}
        QLabel#ArchiveTitle {{
            color: {c.TEXT_SECONDARY};
            font-size: {FontSizes.CHAT_SIDEBAR}px;
            font-weight: 500;
        }}
        QPushButton#ArchiveToggleBtn {{
            background-color: {c.BG_INPUT};
            color: {c.TEXT_MUTED};
            border: 1px solid {c.BORDER};
            border-radius: 10px;
            font-size: 11px;
            font-weight: 700;
            padding: 0;
            text-align: center;
        }}
        QPushButton#ArchiveToggleBtn:hover {{
            background-color: {c.BG_HOVER};
            border-color: {c.BORDER_FOCUS};
            color: {c.TEXT_PRIMARY};
        }}
        QPushButton#ArchiveToggleBtn[active="true"] {{
            background-color: {c.ACCENT};
            color: #FFFFFF;
            border: 1px solid {c.ACCENT};
        }}
        QPushButton#ArchiveToggleBtn[active="true"]:hover {{
            background-color: {c.ACCENT_HOVER};
            border-color: {c.ACCENT_HOVER};
        }}
        
        /* ==================== TOP BAR ==================== */
        QWidget#TopBar {{
            background-color: {c.BG_SIDEBAR};
            border-bottom: 1px solid {c.BORDER_SUBTLE};
        }}
        QLabel#TopBarLabel {{
            color: {c.TEXT_SECONDARY};
            font-size: {FontSizes.SMALL}px;
            font-weight: 600;
        }}
        QFrame#TopBarSeparator {{
            background-color: {c.BORDER};
            border: none;
            width: 1px;
            max-width: 1px;
            min-height: 18px;
            max-height: 20px;
        }}
        QComboBox#ModelCombo, QComboBox#PresetCombo {{
            background-color: {c.BG_INPUT};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.MD}px;
            color: {c.TEXT_PRIMARY};
            padding: 4px 22px 4px 8px;
            font-size: 12px;
            min-height: 24px;
            max-height: 30px;
        }}
        QComboBox#ModelCombo:hover, QComboBox#PresetCombo:hover {{
            border-color: {c.BORDER_FOCUS};
            background-color: {c.BG_HOVER};
        }}
        QComboBox#ModelCombo:focus, QComboBox#PresetCombo:focus {{
            border-color: {c.ACCENT};
        }}
        QComboBox#ModelCombo::drop-down, QComboBox#PresetCombo::drop-down {{
            border: none;
            width: 18px;
        }}
        QComboBox#ModelCombo QAbstractItemView, QComboBox#PresetCombo QAbstractItemView {{
            background-color: {c.BG_CARD};
            color: {c.TEXT_PRIMARY};
            selection-background-color: {c.BG_SELECTED};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.SM}px;
            padding: {Spacing.XS}px;
            outline: none;
        }}
        QPushButton#TopBarBtn {{
            background-color: {c.BG_INPUT};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.MD}px;
            padding: 4px 9px;
            font-size: 11px;
            font-weight: 500;
            min-height: 20px;
        }}
        QPushButton#TopBarBtn:hover {{
            background-color: {c.BG_HOVER};
            border-color: {c.BORDER_FOCUS};
            color: #FFFFFF;
        }}
        QPushButton#TopBarBtn:pressed {{
            background-color: {c.BG_SELECTED};
        }}
        QPushButton#TopBarIconBtn {{
            background-color: {c.BG_INPUT};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.MD}px;
            font-size: 13px;
            font-weight: 600;
            min-width: 28px;
            max-width: 28px;
            min-height: 28px;
            max-height: 28px;
        }}
        QPushButton#TopBarIconBtn:hover {{
            background-color: {c.BG_HOVER};
            border-color: {c.BORDER_FOCUS};
            color: #FFFFFF;
        }}
        QPushButton#TopBarMiniChatBtn {{
            background-color: rgba(255, 95, 21, 0.12);
            color: {c.TEXT_ACCENT};
            border: 1px solid rgba(255, 95, 21, 0.35);
            border-radius: {Radius.MD}px;
            padding: 4px 9px;
            font-size: 11px;
            font-weight: 600;
            min-height: 20px;
        }}
        QPushButton#TopBarMiniChatBtn:hover {{
            background-color: rgba(255, 95, 21, 0.22);
            border-color: {c.ACCENT};
            color: #FFFFFF;
        }}
        QPushButton#TopBarMiniChatBtn:pressed {{
            background-color: {c.ACCENT_PRESSED};
            color: #FFFFFF;
        }}
        QFrame#ConnectionPill {{
            background-color: rgba(53, 199, 89, 0.12);
            border: 1px solid rgba(53, 199, 89, 0.28);
            border-radius: 13px;
        }}
        QPushButton#RefreshBtn {{
            background-color: transparent;
            color: {c.TEXT_MUTED};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.MD}px;
            padding: 6px 12px;
            font-size: {FontSizes.SMALL}px;
        }}
        QPushButton#RefreshBtn:hover {{
            background-color: {c.BG_HOVER};
            color: {c.TEXT_PRIMARY};
        }}
        
        /* ==================== CHAT AREA ==================== */
        QWidget#ChatArea {{
            background-color: {c.BG_PRIMARY};
        }}
        QScrollArea#ChatScroll {{
            background-color: {c.BG_PRIMARY};
            border: none;
        }}
        QScrollArea#ChatScroll > QWidget > QWidget {{
            background-color: {c.BG_PRIMARY};
        }}
        
        /* ==================== MESSAGE WIDGET ==================== */
        QWidget#UserMessage {{
            background-color: {c.USER_MSG_BG};
            border-radius: {Radius.LG}px;
            border: 1px solid {c.BORDER_SUBTLE};
        }}
        QWidget#AssistantMessage {{
            background-color: {c.ASSISTANT_MSG_BG};
        }}
        QWidget#MsgHeaderRow {{
            background-color: transparent;
        }}
        QLabel#MsgAvatar {{
            background-color: transparent;
        }}
        QLabel#MsgHeader {{
            color: {c.TEXT_SECONDARY};
            font-size: {FontSizes.CHAT_SIDEBAR}px;
            font-weight: 600;
        }}
        QLabel#MsgContent {{
            color: {c.TEXT_PRIMARY};
            font-size: {FontSizes.CHAT_BODY}px;
            line-height: 1.6;
        }}
        QPushButton#MsgActionBtn {{
            background-color: transparent;
            color: {c.TEXT_MUTED};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.SM}px;
            padding: 4px 10px;
            font-size: {FontSizes.SMALL}px;
        }}
        QPushButton#MsgActionBtn:hover {{
            background-color: {c.BG_HOVER};
            color: {c.TEXT_PRIMARY};
            border-color: {c.TEXT_MUTED};
        }}
        
        /* ==================== CODE BLOCKS ==================== */
        QWidget#CodeBlock {{
            background-color: {c.BG_CODE};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.MD}px;
        }}
        QLabel#CodeLang {{
            color: {c.TEXT_MUTED};
            font-size: {FontSizes.SMALL}px;
            font-weight: 600;
        }}
        QLabel#CodeContent {{
            color: {c.TEXT_PRIMARY};
            font-family: '{mf}';
            font-size: {FontSizes.CODE}px;
        }}
        QPushButton#CopyCodeBtn {{
            background-color: transparent;
            color: {c.TEXT_MUTED};
            border: none;
            padding: 2px 8px;
            font-size: {FontSizes.SMALL}px;
        }}
        QPushButton#CopyCodeBtn:hover {{
            color: {c.TEXT_PRIMARY};
        }}
        
        /* ==================== MESSAGE INPUT ==================== */
        QWidget#ComposerContainer {{
            background-color: {c.BG_PRIMARY};
        }}
        QTextEdit#MessageInput {{
            background-color: {c.BG_INPUT};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.LG}px;
            padding: 12px 16px;
            font-size: {FontSizes.BODY}px;
            font-family: '{ff}';
        }}
        QTextEdit#MessageInput:focus {{
            border-color: {c.ACCENT};
        }}
        QPushButton#SendBtn {{
            background-color: {c.ACCENT};
            color: white;
            border: none;
            border-radius: {Radius.MD}px;
            padding: 10px 18px;
            font-size: {FontSizes.BODY}px;
            font-weight: 700;
        }}
        QPushButton#SendBtn:hover {{
            background-color: {c.ACCENT_HOVER};
        }}
        QPushButton#SendBtn:disabled {{
            background-color: {c.BG_INPUT};
            color: {c.TEXT_MUTED};
        }}
        QPushButton#StopBtn {{
            background-color: {c.ERROR};
            color: white;
            border: none;
            border-radius: {Radius.MD}px;
            padding: 10px 18px;
            font-size: {FontSizes.BODY}px;
            font-weight: 700;
        }}
        QPushButton#StopBtn:hover {{
            background-color: #E04444;
        }}
        
        /* ==================== STATUS BAR ==================== */
        QWidget#StatusBar {{
            background-color: {c.BG_SECONDARY};
            border-top: 1px solid {c.BORDER_SUBTLE};
        }}
        QLabel#StatusDot {{
            font-size: 10px;
        }}
        QLabel#StatusText {{
            color: {c.TEXT_MUTED};
            font-size: {FontSizes.SMALL}px;
        }}
        QLabel#StatusModel {{
            color: {c.TEXT_SECONDARY};
            font-size: {FontSizes.SMALL}px;
            font-weight: 500;
        }}
        QLabel#StatusMessages,
        QLabel#StatusSpeed,
        QLabel#StatusContext {{
            color: {c.TEXT_MUTED};
            font-size: {FontSizes.SMALL}px;
        }}
        QLabel#StatusSpeed {{
            color: {c.ACCENT};
            font-weight: 500;
        }}
        QLabel#StatusSeparator {{
            color: {c.BORDER};
            font-size: {FontSizes.SMALL}px;
            padding: 0 4px;
        }}
        
        /* ==================== DIALOGS ==================== */
        QDialog {{
            background-color: {c.BG_PRIMARY};
            color: {c.TEXT_PRIMARY};
        }}
        QDialog QLabel#DialogHeader {{
            color: {c.TEXT_PRIMARY};
            font-size: {FontSizes.HEADING}px;
            font-weight: 700;
        }}
        QDialog QListWidget {{
            background-color: {c.BG_SECONDARY};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.MD}px;
            outline: none;
        }}
        QDialog QListWidget::item {{
            padding: 10px 12px;
            border-bottom: 1px solid {c.BORDER_SUBTLE};
            color: {c.TEXT_PRIMARY};
        }}
        QDialog QListWidget::item:selected {{
            background-color: {c.BG_SELECTED};
        }}
        QDialog QListWidget::item:hover {{
            background-color: {c.BG_HOVER};
        }}
        QDialog QPushButton {{
            background-color: {c.BG_INPUT};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.MD}px;
            padding: 8px 16px;
            font-size: {FontSizes.BODY}px;
        }}
        QDialog QPushButton:hover {{
            background-color: {c.BG_HOVER};
        }}
        QDialog QCheckBox {{
            color: {c.TEXT_SECONDARY};
            font-size: {FontSizes.BODY}px;
            spacing: 8px;
        }}
        QDialog QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: {Radius.SM}px;
            border: 2px solid {c.BORDER};
            background-color: {c.BG_INPUT};
        }}
        QDialog QCheckBox::indicator:hover {{
            border-color: {c.BORDER_FOCUS};
        }}
        QDialog QCheckBox::indicator:checked {{
            background-color: {c.ACCENT};
            border-color: {c.ACCENT};
            image: url("{get_resource_path('resources/icons/check.svg')}");
        }}
        QDialog QProgressBar {{
            background-color: {c.BG_INPUT};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.SM}px;
            height: 6px;
            text-align: center;
        }}
        QDialog QProgressBar::chunk {{
            background-color: {c.ACCENT};
            border-radius: {Radius.SM}px;
        }}
        
        /* ==================== OFFLINE PAGE ==================== */
        QWidget#OfflinePage {{
            background-color: {c.BG_PRIMARY};
        }}
        QLabel#OfflineTitle {{
            color: {c.ERROR};
            font-size: {FontSizes.TITLE}px;
            font-weight: 700;
        }}
        QLabel#OfflineBody {{
            color: {c.TEXT_SECONDARY};
            font-size: {FontSizes.BODY}px;
        }}
        QPushButton#RetryBtn {{
            background-color: {c.ACCENT};
            color: white;
            border: none;
            border-radius: {Radius.MD}px;
            padding: 10px 24px;
            font-size: {FontSizes.BODY}px;
            font-weight: 700;
        }}
        QPushButton#RetryBtn:hover {{
            background-color: {c.ACCENT_HOVER};
        }}
        QPushButton#RetryBtn:pressed {{
            background-color: {c.ACCENT_PRESSED};
        }}
        QPushButton#RetryBtn:disabled {{
            background-color: {c.BG_INPUT};
            color: {c.TEXT_MUTED};
        }}
        QPushButton#StartOllamaBtn {{
            background-color: {c.INFO};
            color: white;
            border: none;
            border-radius: {Radius.MD}px;
            padding: 10px 24px;
            font-size: {FontSizes.BODY}px;
            font-weight: 700;
            margin-top: 8px;
        }}
        QPushButton#StartOllamaBtn:hover {{
            background-color: #4A8AE0;
        }}
        QPushButton#StartOllamaBtn:pressed {{
            background-color: #3A7AD0;
        }}
        QPushButton#StartOllamaBtn:disabled {{
            background-color: {c.BG_INPUT};
            color: {c.TEXT_MUTED};
        }}
        QPushButton#OfflineSettingsBtn {{
            background-color: {c.BG_INPUT};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.MD}px;
            padding: 8px 20px;
            font-size: {FontSizes.BODY}px;
            font-weight: 500;
            margin-top: 4px;
        }}
        QPushButton#OfflineSettingsBtn:hover {{
            background-color: {c.BG_HOVER};
            border-color: {c.BORDER_FOCUS};
            color: #FFFFFF;
        }}
        
        /* ==================== CONTEXT MENUS ==================== */
        QMenu {{
            background-color: {c.BG_CARD};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.MD}px;
            padding: {Spacing.XS}px;
        }}
        QMenu::item {{
            padding: 6px 24px 6px 12px;
            border-radius: {Radius.SM}px;
            color: {c.TEXT_PRIMARY};
        }}
        QMenu::item:selected {{
            background-color: {c.BG_SELECTED};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {c.BORDER};
            margin: {Spacing.XS}px 8px;
        }}
        
        /* ==================== WELCOME SCREEN ==================== */
        QWidget#WelcomeScreen {{
            background-color: {c.BG_PRIMARY};
        }}
        QLabel#WelcomeIcon {{
            color: {c.ACCENT};
            font-size: 48px;
        }}
        QLabel#WelcomeTitle {{
            color: {c.TEXT_PRIMARY};
            font-size: {FontSizes.TITLE + 4}px;
            font-weight: 700;
        }}
        QLabel#WelcomeSubtitle {{
            color: {c.TEXT_SECONDARY};
            font-size: {FontSizes.BODY}px;
        }}
        QPushButton#QuickAction {{
            background-color: {c.BG_CARD};
            color: {c.TEXT_SECONDARY};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.LG}px;
            padding: 14px 20px;
            font-size: {FontSizes.BODY}px;
            text-align: left;
        }}
        QPushButton#QuickAction:hover {{
            background-color: {c.BG_HOVER};
            color: {c.TEXT_PRIMARY};
            border-color: {c.TEXT_MUTED};
        }}
        
        /* ==================== TOAST ==================== */
        QWidget#Toast {{
            background-color: {c.BG_CARD};
            border: 1px solid {c.BORDER};
            border-radius: {Radius.MD}px;
        }}
        QLabel#ToastText {{
            color: {c.TEXT_PRIMARY};
            font-size: {FontSizes.SMALL}px;
        }}
        """
