from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel
from PySide6.QtCore import Signal, Slot, Qt
from utils.logger import logger

class ModelSelector(QWidget):
    """Dropdown and refresh controls to select active local Ollama model."""
    
    model_changed = Signal(str)
    refresh_requested = Signal()
    manage_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.setSizeConstraint(QHBoxLayout.SizeConstraint.SetMinimumSize)

        self.model_label = QLabel("Model:")
        self.model_label.setObjectName("TopBarLabel")
        layout.addWidget(self.model_label)

        self.combo_box = QComboBox()
        self.combo_box.setObjectName("ModelCombo")
        self.combo_box.setMinimumWidth(150)
        self.combo_box.setFixedHeight(30)
        self.combo_box.currentTextChanged.connect(self._on_model_changed)
        layout.addWidget(self.combo_box)

        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setObjectName("TopBarIconBtn")
        self.refresh_btn.setToolTip("Refresh model list")
        self.refresh_btn.setFixedSize(28, 28)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(self.refresh_btn)

        self.manage_btn = QPushButton("⚙")
        self.manage_btn.setObjectName("TopBarIconBtn")
        self.manage_btn.setFixedSize(28, 28)
        self.manage_btn.setToolTip("Manage Ollama models (pull, inspect, delete)")
        self.manage_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manage_btn.clicked.connect(self.manage_requested.emit)
        layout.addWidget(self.manage_btn)

        # Info label for loading/error
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 12px;")
        self.info_label.hide()
        layout.addWidget(self.info_label)

    def set_loading(self, is_loading: bool):
        """Sets the loading state of the selector."""
        if is_loading:
            self.combo_box.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.manage_btn.setEnabled(False)
            self.info_label.setText("Loading...")
            self.info_label.show()
            logger.debug("ModelSelector set to loading state.")
        else:
            self.combo_box.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.manage_btn.setEnabled(True)
            self.info_label.hide()
            logger.debug("ModelSelector loading state cleared.")

    def set_models(self, models: list[dict], selected_model: str = None):
        """Populates the model selector dropdown."""
        self.combo_box.blockSignals(True)
        self.combo_box.clear()
        
        if not models:
            self.info_label.setText("No models found. Run 'ollama pull llama3.2' and click ↻")
            self.info_label.show()
            self.combo_box.setEnabled(False)
            logger.warning("ModelSelector updated with empty list.")
        else:
            self.info_label.hide()
            self.combo_box.setEnabled(True)
            
            model_names = [m.get("name") for m in models]
            self.combo_box.addItems(model_names)
            
            if selected_model and selected_model in model_names:
                self.combo_box.setCurrentText(selected_model)
            else:
                self.combo_box.setCurrentIndex(0)
                selected_model = self.combo_box.currentText()
                
            logger.info("ModelSelector populated with %d models. Selected: %s", len(models), selected_model)

        self.combo_box.blockSignals(False)

        if self.combo_box.count() > 0:
            self.model_changed.emit(self.combo_box.currentText())

    def _on_model_changed(self, text):
        if text:
            logger.info("ModelSelector combobox selected: %s", text)
            self.model_changed.emit(text)
