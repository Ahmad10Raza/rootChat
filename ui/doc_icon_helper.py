"""
doc_icon_helper.py - Dynamic vector icon generator for document types in rootChat.
Provides crisp, modern, high-DPI document icons without relying on system emojis.
"""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath, QFont


def create_document_icon(ext: str, size: int = 38, dark: bool = True, with_container: bool = True) -> QPixmap:
    """
    Renders a modern, vector document icon with folded corner flap and color-coded badge.
    
    :param ext: File extension (e.g. '.pdf', 'docx', 'csv')
    :param size: Dimension in pixels (width == height)
    :param dark: Whether the active theme is dark mode
    :param with_container: If True, draws a subtle rounded container box around the icon
    :return: QPixmap with transparent background
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    ext = ext.lower().lstrip(".")
    if ext == "pdf":
        base_col = QColor("#EF4444")
        bg_subtle = QColor(239, 68, 68, 32 if dark else 22)
        border_col = QColor(239, 68, 68, 80 if dark else 50)
        label = "PDF"
    elif ext in ["docx", "doc"]:
        base_col = QColor("#3B82F6")
        bg_subtle = QColor(59, 130, 246, 32 if dark else 22)
        border_col = QColor(59, 130, 246, 80 if dark else 50)
        label = "DOC"
    elif ext in ["csv", "xlsx", "xls"]:
        base_col = QColor("#10B981")
        bg_subtle = QColor(16, 185, 129, 32 if dark else 22)
        border_col = QColor(16, 185, 129, 80 if dark else 50)
        label = "CSV"
    elif ext in ["json", "xml", "yaml", "yml"]:
        base_col = QColor("#F59E0B")
        bg_subtle = QColor(245, 158, 11, 32 if dark else 22)
        border_col = QColor(245, 158, 11, 80 if dark else 50)
        label = "DATA"
    else:
        base_col = QColor("#94A3B8")
        bg_subtle = QColor(148, 163, 184, 32 if dark else 22)
        border_col = QColor(148, 163, 184, 80 if dark else 50)
        label = "TXT"

    if with_container:
        painter.setPen(QPen(border_col, 1))
        painter.setBrush(QBrush(bg_subtle))
        painter.drawRoundedRect(QRectF(1, 1, size - 2, size - 2), 8, 8)
        
        # Proportional document silhouette inside container
        dw = size * 0.46
        dh = size * 0.58
        dx = (size - dw) / 2.0
        dy = (size - dh) / 2.0
    else:
        dw = size * 0.76
        dh = size * 0.90
        dx = (size - dw) / 2.0
        dy = (size - dh) / 2.0

    fold = dw * 0.32
    
    # Base sheet path with cut top-right corner
    path = QPainterPath()
    path.moveTo(dx, dy)
    path.lineTo(dx + dw - fold, dy)
    path.lineTo(dx + dw, dy + fold)
    path.lineTo(dx + dw, dy + dh)
    path.lineTo(dx, dy + dh)
    path.closeSubpath()
    
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(base_col))
    painter.drawPath(path)
    
    # Folded flap path
    flap = QPainterPath()
    flap.moveTo(dx + dw - fold, dy)
    flap.lineTo(dx + dw - fold, dy + fold)
    flap.lineTo(dx + dw, dy + fold)
    flap.closeSubpath()
    painter.setBrush(QBrush(QColor("#FFFFFF") if not dark else base_col.lighter(135)))
    painter.drawPath(flap)
    
    # Badge text or stylized document lines
    if size >= 28:
        painter.setPen(QColor("#FFFFFF"))
        font_size = max(5, int(dw * 0.28))
        f = QFont("Sans Serif", font_size)
        f.setBold(True)
        painter.setFont(f)
        text_rect = QRectF(dx, dy + (dh * 0.32), dw, dh * 0.6)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)
    else:
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1.2))
        line_x1 = dx + (dw * 0.2)
        line_x2 = dx + (dw * 0.8)
        y1 = dy + (dh * 0.42)
        y2 = dy + (dh * 0.62)
        y3 = dy + (dh * 0.82)
        painter.drawLine(line_x1, y1, line_x2, y1)
        painter.drawLine(line_x1, y2, line_x2, y2)
        painter.drawLine(line_x1, y3, dx + (dw * 0.55), y3)
    
    painter.end()
    return pix
