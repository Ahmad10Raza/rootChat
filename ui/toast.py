"""Toast notification system for rootChat."""

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont


class Toast(QWidget):
    """A non-blocking notification that auto-dismisses."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setFixedHeight(40)
        self.setMinimumWidth(200)
        self.setMaximumWidth(400)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        
        self.icon_label = QLabel()
        self.icon_label.setFixedWidth(18)
        layout.addWidget(self.icon_label)
        
        self.text_label = QLabel()
        self.text_label.setObjectName("ToastText")
        layout.addWidget(self.text_label)
        
        self.hide()
        
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._dismiss)
    
    def show_message(self, text: str, kind: str = "success", duration: int = 3000):
        """Show a toast message. kind: 'success', 'warning', 'error', 'info'"""
        icons = {"success": "✓", "warning": "⚠", "error": "✕", "info": "ℹ"}
        self.icon_label.setText(icons.get(kind, "ℹ"))
        self.text_label.setText(text)
        
        # Position at top-center of parent
        if self.parent():
            pw = self.parent().width()
            self.adjustSize()
            x = (pw - self.width()) // 2
            self.move(x, 10)
        
        self.show()
        self.raise_()
        self._timer.start(duration)
    
    def _dismiss(self):
        self.hide()
