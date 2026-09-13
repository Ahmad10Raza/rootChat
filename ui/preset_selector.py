from PySide6.QtWidgets import QWidget, QHBoxLayout, QComboBox, QLabel
from PySide6.QtCore import Signal, Slot, Qt
from core.presets import list_presets, get_preset
from utils.logger import logger

class PresetSelector(QWidget):
    """Dropdown control to select the active conversation persona/preset."""
    
    preset_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.preset_label = QLabel("Persona:")
        self.preset_label.setObjectName("TopBarLabel")
        self.preset_label.setFixedWidth(54)
        layout.addWidget(self.preset_label)

        self.combo_box = QComboBox()
        self.combo_box.setObjectName("PresetCombo")
        self.combo_box.setFixedWidth(165)
        self.combo_box.setFixedHeight(28)
        
        for p in list_presets():
            self.combo_box.addItem(f"{p['icon']} {p['name']}", userData=p["id"])
            # Set tooltip for each item if possible
            idx = self.combo_box.count() - 1
            self.combo_box.setItemData(idx, p["description"], Qt.ItemDataRole.ToolTipRole)
            
        self.combo_box.currentIndexChanged.connect(self._on_combo_changed)
        layout.addWidget(self.combo_box)

    def set_preset(self, preset_id: str):
        """Programmatically select a preset by ID without emitting duplicate signals."""
        idx = -1
        for i in range(self.combo_box.count()):
            if self.combo_box.itemData(i, Qt.ItemDataRole.UserRole) == preset_id:
                idx = i
                break
        
        if idx != -1 and self.combo_box.currentIndex() != idx:
            self.combo_box.blockSignals(True)
            self.combo_box.setCurrentIndex(idx)
            self.combo_box.blockSignals(False)
            logger.debug("PresetSelector set to %s", preset_id)

    def get_current_preset(self) -> str:
        data = self.combo_box.currentData(Qt.ItemDataRole.UserRole)
        return data if data else "general"

    def _on_combo_changed(self, index: int):
        preset_id = self.combo_box.itemData(index, Qt.ItemDataRole.UserRole)
        if preset_id:
            logger.info("PresetSelector selected: %s", preset_id)
            self.preset_changed.emit(preset_id)
