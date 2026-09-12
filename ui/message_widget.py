import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QApplication, QMenu)
from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath
from PySide6.QtCore import Qt, Signal, QRectF
from utils.markdown_renderer import parse_markdown_blocks
from utils.resource_path import get_resource_path

class MessageWidget(QWidget):
    regenerate_requested = Signal()
    delete_requested = Signal(int)
    
    def __init__(self, role: str, content: str, msg_id: int = None):
        super().__init__()
        self.role = role
        self.content = content
        self.msg_id = msg_id
        
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        if role == "user":
            self.setObjectName("UserMessage")
        else:
            self.setObjectName("AssistantMessage")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 12, 16, 12)
        self.main_layout.setSpacing(6)
        
        # Header Row (Avatar Icon + Role Label)
        self.header_row = QWidget()
        self.header_row.setObjectName("MsgHeaderRow")
        header_layout = QHBoxLayout(self.header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.avatar_lbl = QLabel()
        self.avatar_lbl.setObjectName("MsgAvatar")
        self.avatar_lbl.setFixedSize(22, 22)
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if role == "user":
            self.avatar_lbl.setPixmap(self._get_user_avatar(22))
            title_text = "You"
        elif role == "system":
            self.avatar_lbl.setText("ℹ️")
            title_text = "System"
        else:
            self.avatar_lbl.setPixmap(self._get_bot_avatar(22))
            title_text = "rootChat"
            
        header_layout.addWidget(self.avatar_lbl)
        
        self.header = QLabel(title_text)
        self.header.setObjectName("MsgHeader")
        header_layout.addWidget(self.header)
        header_layout.addStretch()
        
        self.main_layout.addWidget(self.header_row)
        
        # Content area
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(8)
        self.main_layout.addLayout(self.content_layout)
        
        self.render_content(content)
        
        # Actions for assistant messages
        if role == "assistant":
            actions_layout = QHBoxLayout()
            actions_layout.addStretch()
            actions_layout.setSpacing(6)
            
            copy_btn = QPushButton("Copy")
            copy_btn.setObjectName("MsgActionBtn")
            copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_btn.clicked.connect(self._copy_content)
            
            self.regen_btn = QPushButton("Regenerate")
            self.regen_btn.setObjectName("MsgActionBtn")
            self.regen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.regen_btn.clicked.connect(self.regenerate_requested.emit)
            
            actions_layout.addWidget(copy_btn)
            actions_layout.addWidget(self.regen_btn)
            self.main_layout.addLayout(actions_layout)
            
    def render_content(self, text: str):
        self.content = text
        blocks = list(parse_markdown_blocks(text))
        if not blocks:
            if self.content_layout.count() == 0:
                text_lbl = QLabel()
                text_lbl.setObjectName("MsgContent")
                t_font = text_lbl.font()
                t_font.setPixelSize(15)
                text_lbl.setFont(t_font)
                self.content_layout.addWidget(text_lbl)
            return

        # Remove extra widgets if the number of blocks decreased (rare but possible during parsing shifts)
        while self.content_layout.count() > len(blocks):
            child = self.content_layout.takeAt(self.content_layout.count() - 1)
            if child.widget():
                child.widget().hide()
                child.widget().deleteLater()

        for i, (is_code, content, lang) in enumerate(blocks):
            item = self.content_layout.itemAt(i)
            widget = item.widget() if item else None
            
            is_existing_code = (widget.objectName() == "CodeBlock") if widget else False
            
            if widget and (is_code == is_existing_code):
                # Update existing widget to avoid UI flickering
                if is_code:
                    code_lbl = widget.findChild(QLabel, "CodeContent")
                    if code_lbl:
                        code_lbl.setText(content)
                    lang_lbl = widget.findChild(QLabel, "CodeLang")
                    if lang_lbl:
                        lang_lbl.setText(lang if lang else "Code")
                else:
                    widget.setText(content)
            else:
                # Type mismatch or doesn't exist, create a new one
                if widget:
                    child = self.content_layout.takeAt(i)
                    child.widget().hide()
                    child.widget().deleteLater()
                    
                if is_code:
                    code_container = QWidget()
                    code_container.setObjectName("CodeBlock")
                    code_layout = QVBoxLayout(code_container)
                    code_layout.setContentsMargins(12, 8, 12, 12)
                    code_layout.setSpacing(6)
                    
                    header_layout = QHBoxLayout()
                    header_layout.setContentsMargins(0, 0, 0, 0)
                    
                    lang_lbl = QLabel(lang if lang else "Code")
                    lang_lbl.setObjectName("CodeLang")
                    
                    copy_code_btn = QPushButton("Copy")
                    copy_code_btn.setObjectName("CopyCodeBtn")
                    copy_code_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    copy_code_btn.clicked.connect(lambda _, c=content: QApplication.clipboard().setText(c))
                    
                    header_layout.addWidget(lang_lbl)
                    header_layout.addStretch()
                    header_layout.addWidget(copy_code_btn)
                    code_layout.addLayout(header_layout)
                    
                    code_lbl = QLabel(content)
                    code_lbl.setObjectName("CodeContent")
                    c_font = code_lbl.font()
                    c_font.setPixelSize(13)
                    code_lbl.setFont(c_font)
                    code_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                    code_lbl.setWordWrap(True)
                    code_layout.addWidget(code_lbl)
                    
                    self.content_layout.insertWidget(i, code_container)
                else:
                    text_lbl = QLabel()
                    text_lbl.setObjectName("MsgContent")
                    t_font = text_lbl.font()
                    t_font.setPixelSize(15)
                    text_lbl.setFont(t_font)
                    text_lbl.setTextFormat(Qt.TextFormat.MarkdownText)
                    text_lbl.setText(content)
                    text_lbl.setTextInteractionFlags(
                        Qt.TextInteractionFlag.TextBrowserInteraction | Qt.TextInteractionFlag.TextSelectableByMouse
                    )
                    text_lbl.setOpenExternalLinks(True)
                    text_lbl.setWordWrap(True)
                    text_lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                    text_lbl.customContextMenuRequested.connect(lambda p, l=text_lbl: self._show_context_menu(self.mapFromGlobal(l.mapToGlobal(p))))
                    self.content_layout.insertWidget(i, text_lbl)
                
    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.Type.StyleChange:
            if self.role == "user" and hasattr(self, "avatar_lbl"):
                self.avatar_lbl.setPixmap(self._get_user_avatar(22))

    def _copy_content(self):
        QApplication.clipboard().setText(self.content)

    def contextMenuEvent(self, event):
        self._show_context_menu(event.pos())

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        copy_action = menu.addAction("📋  Copy Text")
        copy_md_action = menu.addAction("📄  Copy as Markdown")
        
        regen_action = None
        if self.role == "assistant":
            menu.addSeparator()
            regen_action = menu.addAction("🔄  Regenerate Response")
            
        menu.addSeparator()
        delete_action = menu.addAction("🗑️  Delete Message")
        
        action = menu.exec(self.mapToGlobal(pos))
        if action == copy_action:
            QApplication.clipboard().setText(self.content)
        elif action == copy_md_action:
            QApplication.clipboard().setText(self.content)
        elif regen_action and action == regen_action:
            self.regenerate_requested.emit()
        elif action == delete_action:
            if self.msg_id is not None:
                self.delete_requested.emit(self.msg_id)

    @staticmethod
    def _get_user_avatar(size: int = 22) -> QPixmap:
        try:
            from ui.theme.theme_manager import ThemeManager
            tm = ThemeManager.instance()
            is_light = (getattr(tm, "_mode", "dark") == "light")
        except Exception:
            is_light = False
            
        icon_name = "user_light.png" if is_light else "user.png"
        icon_path = get_resource_path(f"resources/icons/{icon_name}")
        if not os.path.exists(icon_path):
            svg_name = "user_light.svg" if is_light else "user.svg"
            icon_path = get_resource_path(f"resources/icons/{svg_name}")
            
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            if not pix.isNull():
                return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                
        # Draw fallback badge if file missing
        bg = "#EAEEF2" if is_light else "#21262D"
        fg = "#57606A" if is_light else "#C9D1D9"
        border = "#D0D7DE" if is_light else "#30363D"
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(border), 1))
        p.setBrush(QBrush(QColor(bg)))
        p.drawEllipse(QRectF(0.5, 0.5, size - 1, size - 1))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(fg)))
        head_r = size * 0.20
        p.drawEllipse(QRectF(size/2.0 - head_r, size * 0.35 - head_r, head_r * 2, head_r * 2))
        clip = QPainterPath()
        clip.addEllipse(QRectF(1, 1, size - 2, size - 2))
        p.setClipPath(clip)
        body = QPainterPath()
        w = size * 0.64
        h = size * 0.44
        body.addRoundedRect(QRectF((size - w)/2.0, size * 0.58, w, h), size * 0.20, size * 0.20)
        p.drawPath(body)
        p.end()
        return pix

    @staticmethod
    def _get_bot_avatar(size: int = 22) -> QPixmap:
        logo_path = get_resource_path("resources/icons/rootChat_32.png")
        if not os.path.exists(logo_path):
            logo_path = get_resource_path("resources/icons/rootChat.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            if not pix.isNull():
                return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return QPixmap()
