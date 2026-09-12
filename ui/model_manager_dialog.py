"""Ollama Model Manager Dialog for rootChat.

Provides inspection of local and cloud models, real-time search filtering,
switching the active model, deleting models, and pulling new LLMs from Ollama.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QLineEdit,
    QMessageBox, QProgressBar, QFrame, QWidget, QSplitter,
    QGridLayout
)
from PySide6.QtCore import Qt, Signal, Slot
from core.ollama_client import OllamaClient
from core.app_state import AppState
from core.ollama_worker import (
    OllamaModelsWorker, OllamaPullWorker,
    OllamaDeleteWorker, OllamaShowWorker
)
from ui.theme.theme_manager import ThemeManager
from utils.logger import logger


def format_size(size_bytes: int) -> str:
    """Formats bytes into human readable string (KB, MB, GB)."""
    if not size_bytes or size_bytes <= 0:
        return "Unknown"
    val = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if val < 1024.0:
            return f"{val:.1f} {unit}"
        val /= 1024.0
    return f"{val:.1f} PB"


class ModelManagerDialog(QDialog):
    """Dialog for inspecting, pulling, and deleting Ollama models."""
    
    models_updated = Signal()

    def __init__(self, client: OllamaClient, app_state: AppState, parent=None):
        super().__init__(parent)
        self.client = client
        self.app_state = app_state
        self.workers = []
        self.current_pull_worker = None
        self._all_models = []
        self._filter_text = ""

        self.setWindowTitle("Ollama Model Manager")
        self.setMinimumSize(820, 600)
        self.resize(880, 640)

        self.init_ui()
        self._apply_styling()
        self.refresh_models()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # ============ HEADER ============
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(3)

        title = QLabel("📦  Ollama Model Manager")
        title.setObjectName("ModelHeaderTitle")

        subtitle = QLabel("Inspect model architecture, switch active chat LLM, pull new models, or free up disk space.")
        subtitle.setObjectName("ModelHeaderSubtitle")

        header_text_layout.addWidget(title)
        header_text_layout.addWidget(subtitle)
        header_layout.addLayout(header_text_layout, 1)

        self.model_count_badge = QLabel("0 Models")
        self.model_count_badge.setObjectName("ModelCountBadge")
        header_layout.addWidget(self.model_count_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        main_layout.addLayout(header_layout)

        # ============ SPLITTER ============
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ============ LEFT PANEL (BROWSER) ============
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)

        # Top Bar: Label + Refresh
        models_header_layout = QHBoxLayout()
        models_label = QLabel("Installed Models")
        models_label.setObjectName("SectionHeading")
        models_header_layout.addWidget(models_label)
        models_header_layout.addStretch()

        self.refresh_btn = QPushButton("↻ Refresh")
        self.refresh_btn.setObjectName("ActionSecondaryBtn")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_models)
        models_header_layout.addWidget(self.refresh_btn)
        left_layout.addLayout(models_header_layout)

        # Search Filter Bar
        self.search_input = QLineEdit()
        self.search_input.setObjectName("ModelSearchInput")
        self.search_input.setPlaceholderText("🔍  Search models...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        left_layout.addWidget(self.search_input)

        # Models List Widget
        self.model_list = QListWidget()
        self.model_list.setObjectName("ModelList")
        self.model_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.model_list.currentItemChanged.connect(self._on_model_selection_changed)
        left_layout.addWidget(self.model_list, 1)

        # Left Action Buttons
        left_btn_layout = QHBoxLayout()
        left_btn_layout.setSpacing(8)

        self.use_active_btn = QPushButton("✓ Use as Active")
        self.use_active_btn.setObjectName("ActionPrimaryBtn")
        self.use_active_btn.setToolTip("Set the selected model as active chat model")
        self.use_active_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.use_active_btn.clicked.connect(self._on_use_active_clicked)
        left_btn_layout.addWidget(self.use_active_btn, 1)

        self.delete_btn = QPushButton("🗑 Delete")
        self.delete_btn.setObjectName("ActionDangerBtn")
        self.delete_btn.setToolTip("Delete selected model weights from disk")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        left_btn_layout.addWidget(self.delete_btn)

        left_layout.addLayout(left_btn_layout)
        splitter.addWidget(left_widget)

        # ============ RIGHT PANEL (DETAILS & PULL) ============
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(14)

        # 1. Model Details Card
        details_card = QFrame()
        details_card.setObjectName("ModelDetailsCard")
        details_layout = QVBoxLayout(details_card)
        details_layout.setContentsMargins(16, 16, 16, 16)
        details_layout.setSpacing(10)

        # Card Header: Title + Badges
        details_top_row = QHBoxLayout()
        details_sec_title = QLabel("MODEL SPECIFICATIONS")
        details_sec_title.setObjectName("CardSectionTitle")
        details_top_row.addWidget(details_sec_title)
        details_top_row.addStretch()

        self.details_type_badge = QLabel("💾 Local")
        self.details_type_badge.setObjectName("TypeBadgeLocal")
        self.details_type_badge.setVisible(False)
        details_top_row.addWidget(self.details_type_badge)

        self.details_active_badge = QLabel("⭐ Active")
        self.details_active_badge.setObjectName("ActiveBadge")
        self.details_active_badge.setVisible(False)
        details_top_row.addWidget(self.details_active_badge)

        details_layout.addLayout(details_top_row)

        # Selected Model Name
        self.details_name_lbl = QLabel("Select a model to view details.")
        self.details_name_lbl.setObjectName("ModelNameHeader")
        details_layout.addWidget(self.details_name_lbl)

        # Notice Banner (Local vs Cloud)
        self.details_notice_lbl = QLabel("")
        self.details_notice_lbl.setObjectName("NoticeBanner")
        self.details_notice_lbl.setVisible(False)
        details_layout.addWidget(self.details_notice_lbl)

        # Specifications Grid Box
        spec_box = QFrame()
        spec_box.setObjectName("SpecBox")
        spec_grid = QGridLayout(spec_box)
        spec_grid.setContentsMargins(0, 4, 0, 4)
        spec_grid.setHorizontalSpacing(10)
        spec_grid.setVerticalSpacing(8)

        self.details_params_lbl = QLabel("Parameters: —")
        self.details_quant_lbl = QLabel("Quantization: —")
        self.details_family_lbl = QLabel("Family: —")
        self.details_size_lbl = QLabel("Disk Size: —")
        self.details_context_lbl = QLabel("Context Length: —")
        self.details_caps_lbl = QLabel("Capabilities: —")
        self.details_host_lbl = QLabel("Remote Host: —")
        self.details_host_lbl.setVisible(False)

        spec_grid.addWidget(self.details_params_lbl, 0, 0)
        spec_grid.addWidget(self.details_quant_lbl, 0, 1)
        spec_grid.addWidget(self.details_family_lbl, 1, 0)
        spec_grid.addWidget(self.details_size_lbl, 1, 1)
        spec_grid.addWidget(self.details_context_lbl, 2, 0, 1, 2)
        spec_grid.addWidget(self.details_caps_lbl, 3, 0, 1, 2)
        spec_grid.addWidget(self.details_host_lbl, 4, 0, 1, 2)

        details_layout.addWidget(spec_box)
        right_layout.addWidget(details_card)

        # 2. Pull New Model Card
        pull_card = QFrame()
        pull_card.setObjectName("ModelPullCard")
        pull_layout = QVBoxLayout(pull_card)
        pull_layout.setContentsMargins(16, 16, 16, 16)
        pull_layout.setSpacing(10)

        pull_sec_title = QLabel("PULL NEW MODEL")
        pull_sec_title.setObjectName("CardSectionTitle")
        pull_layout.addWidget(pull_sec_title)

        pull_desc = QLabel("Download models directly from the official Ollama library:")
        pull_desc.setObjectName("CardSectionDesc")
        pull_layout.addWidget(pull_desc)

        # Quick Pick Recommendations
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(6)
        quick_models = ["llama3.2", "qwen2.5:3b", "deepseek-r1:1.5b", "mistral"]
        for qm in quick_models:
            qbtn = QPushButton(qm)
            qbtn.setObjectName("QuickChip")
            qbtn.setCursor(Qt.CursorShape.PointingHandCursor)
            qbtn.clicked.connect(lambda _, m=qm: self._set_pull_input(m))
            quick_layout.addWidget(qbtn)
        quick_layout.addStretch()
        pull_layout.addLayout(quick_layout)

        # Input & Pull Button
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.pull_input = QLineEdit()
        self.pull_input.setObjectName("ModelPullInput")
        self.pull_input.setPlaceholderText("Enter model tag, e.g. llama3.2, deepseek-r1:8b, mistral...")
        self.pull_input.returnPressed.connect(self._on_pull_clicked)
        input_layout.addWidget(self.pull_input, 1)

        self.pull_btn = QPushButton("⬇ Pull Model")
        self.pull_btn.setObjectName("ActionPrimaryBtn")
        self.pull_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pull_btn.clicked.connect(self._on_pull_clicked)
        input_layout.addWidget(self.pull_btn)
        pull_layout.addLayout(input_layout)

        # Pull Progress Elements
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        pull_layout.addWidget(self.progress_bar)

        progress_info_layout = QHBoxLayout()
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("font-size: 11px; color: #A6ACB8;")
        self.progress_label.setVisible(False)
        progress_info_layout.addWidget(self.progress_label, 1)

        self.cancel_pull_btn = QPushButton("Cancel")
        self.cancel_pull_btn.setObjectName("ActionSecondaryBtn")
        self.cancel_pull_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_pull_btn.setVisible(False)
        self.cancel_pull_btn.clicked.connect(self._on_cancel_pull_clicked)
        progress_info_layout.addWidget(self.cancel_pull_btn)

        pull_layout.addLayout(progress_info_layout)
        right_layout.addWidget(pull_card)
        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([330, 490])
        main_layout.addWidget(splitter, 1)

        # ============ BOTTOM BAR ============
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 4, 0, 0)

        endpoint_text = getattr(self.client, "endpoint", "http://localhost:11434")
        self.endpoint_status_lbl = QLabel(f"● Connected to {endpoint_text}")
        self.endpoint_status_lbl.setStyleSheet("color: #35C759; font-size: 11px; font-weight: 500;")
        bottom_layout.addWidget(self.endpoint_status_lbl)
        bottom_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setObjectName("ActionSecondaryBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(close_btn)

        main_layout.addLayout(bottom_layout)

    def _apply_styling(self):
        c = ThemeManager.instance().colors
        ff = ThemeManager.instance().font_family
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c.BG_PRIMARY};
                color: {c.TEXT_PRIMARY};
                font-family: '{ff}';
            }}
            #ModelHeaderTitle {{
                font-size: 18px;
                font-weight: 700;
                color: {c.TEXT_PRIMARY};
            }}
            #ModelHeaderSubtitle {{
                font-size: 12px;
                color: {c.TEXT_SECONDARY};
            }}
            #SectionHeading {{
                font-size: 13px;
                font-weight: 600;
                color: {c.TEXT_PRIMARY};
            }}
            #ModelCountBadge {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_SECONDARY};
                border: 1px solid {c.BORDER};
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            #ModelSearchInput {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 8px;
                padding: 7px 12px;
                font-size: 12px;
            }}
            #ModelSearchInput:focus {{
                border: 1px solid {c.ACCENT};
            }}
            #ModelList {{
                background-color: {c.BG_SECONDARY};
                border: 1px solid {c.BORDER};
                border-radius: 8px;
                padding: 4px;
                outline: none;
                font-size: 12px;
            }}
            #ModelList::item {{
                background-color: transparent;
                color: {c.TEXT_PRIMARY};
                border-radius: 6px;
                padding: 7px 8px;
                margin-bottom: 2px;
            }}
            #ModelList::item:hover {{
                background-color: {c.BG_HOVER};
            }}
            #ModelList::item:selected {{
                background-color: {c.BG_SELECTED};
                color: #FFFFFF;
                border-left: 3px solid {c.ACCENT};
            }}
            #ModelDetailsCard, #ModelPullCard {{
                background-color: {c.BG_CARD};
                border: 1px solid {c.BORDER};
                border-radius: 10px;
            }}
            #CardSectionTitle {{
                font-size: 11px;
                font-weight: 700;
                color: {c.TEXT_ACCENT};
                letter-spacing: 0.5px;
            }}
            #CardSectionDesc {{
                font-size: 12px;
                color: {c.TEXT_SECONDARY};
            }}
            #ModelNameHeader {{
                font-size: 16px;
                font-weight: 700;
                color: {c.TEXT_PRIMARY};
            }}
            #ActiveBadge {{
                background-color: rgba(53, 199, 89, 0.15);
                color: {c.SUCCESS};
                border: 1px solid rgba(53, 199, 89, 0.35);
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            #TypeBadgeCloud {{
                background-color: rgba(91, 157, 240, 0.15);
                color: {c.INFO};
                border: 1px solid rgba(91, 157, 240, 0.35);
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            #TypeBadgeLocal {{
                background-color: rgba(255, 95, 21, 0.15);
                color: {c.TEXT_ACCENT};
                border: 1px solid rgba(255, 95, 21, 0.35);
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            }}
            #NoticeBanner {{
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid {c.BORDER_SUBTLE};
                border-radius: 6px;
                padding: 8px 12px;
                color: {c.TEXT_SECONDARY};
                font-size: 11px;
            }}
            #SpecBox QLabel {{
                background-color: {c.BG_SECONDARY};
                border: 1px solid {c.BORDER_SUBTLE};
                border-radius: 6px;
                padding: 6px 10px;
                min-height: 20px;
                color: {c.TEXT_PRIMARY};
                font-size: 12px;
            }}
            #ModelPullInput {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
            }}
            #ModelPullInput:focus {{
                border: 1px solid {c.ACCENT};
            }}
            #QuickChip {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_SECONDARY};
                border: 1px solid {c.BORDER};
                border-radius: 11px;
                padding: 4px 10px;
                font-size: 11px;
            }}
            #QuickChip:hover {{
                background-color: {c.BG_HOVER};
                color: {c.TEXT_PRIMARY};
                border-color: {c.ACCENT};
            }}
            #ActionPrimaryBtn {{
                background-color: {c.ACCENT};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 7px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            #ActionPrimaryBtn:hover {{
                background-color: {c.ACCENT_HOVER};
            }}
            #ActionPrimaryBtn:pressed {{
                background-color: {c.ACCENT_PRESSED};
            }}
            #ActionPrimaryBtn:disabled {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_MUTED};
            }}
            #ActionSecondaryBtn {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_PRIMARY};
                border: 1px solid {c.BORDER};
                border-radius: 8px;
                padding: 7px 14px;
                font-size: 12px;
            }}
            #ActionSecondaryBtn:hover {{
                background-color: {c.BG_HOVER};
                border-color: {c.BORDER_FOCUS};
            }}
            #ActionDangerBtn {{
                background-color: rgba(255, 85, 85, 0.08);
                color: {c.ERROR};
                border: 1px solid rgba(255, 85, 85, 0.25);
                border-radius: 8px;
                padding: 7px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            #ActionDangerBtn:hover {{
                background-color: rgba(255, 85, 85, 0.18);
                border-color: {c.ERROR};
            }}
            #ActionDangerBtn:disabled {{
                background-color: {c.BG_INPUT};
                color: {c.TEXT_MUTED};
                border-color: {c.BORDER};
            }}
            QProgressBar {{
                background-color: {c.BG_SECONDARY};
                border: 1px solid {c.BORDER};
                border-radius: 5px;
                height: 8px;
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background-color: {c.ACCENT};
                border-radius: 4px;
            }}
        """)

    def _set_pull_input(self, model_name: str):
        self.pull_input.setText(model_name)
        self.pull_input.setFocus()

    def _on_search_text_changed(self, text: str):
        self._filter_text = text.strip().lower()
        self._populate_model_list()

    def refresh_models(self):
        """Fetches the latest installed models list from Ollama."""
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Loading...")
        
        worker = OllamaModelsWorker(self.client)
        worker.finished.connect(self._on_models_fetched)
        worker.error.connect(self._on_models_error)
        self.workers.append(worker)
        worker.start()

    @Slot(list)
    def _on_models_fetched(self, models: list):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("↻ Refresh")
        self._all_models = models or []
        self.model_count_badge.setText(f"{len(self._all_models)} Models")
        self._populate_model_list()

    def _populate_model_list(self):
        self.model_list.clear()

        if not self._all_models:
            item = QListWidgetItem("No installed models found.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.model_list.addItem(item)
            self._reset_details_panel()
            self.details_name_lbl.setText("No models available.")
            self.use_active_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return

        filtered = [
            m for m in self._all_models
            if not self._filter_text 
            or self._filter_text in m.get("name", "").lower()
            or self._filter_text in m.get("family", "").lower()
            or self._filter_text in str(m.get("details", {}).get("family", "")).lower()
        ]

        if not filtered:
            item = QListWidgetItem(f"No models matching '{self._filter_text}'")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.model_list.addItem(item)
            self._reset_details_panel()
            self.details_name_lbl.setText("No search results.")
            self.use_active_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return

        active_model = self.app_state.get("selected_model")
        selected_row = 0

        for idx, m in enumerate(filtered):
            name = m.get("name", "unknown")
            size_str = format_size(m.get("size", 0))
            is_cloud = bool(
                m.get("remote_model") 
                or m.get("remote_host") 
                or ":cloud" in name 
                or (m.get("details", {}).get("family") == "" and m.get("size", 0) < 1000)
            )
            is_active = (name == active_model)
            prefix = "⭐ " if is_active else "  "
            cloud_indicator = " ☁" if is_cloud else ""

            item = QListWidgetItem(f"{prefix}{name}{cloud_indicator}  ({size_str})")
            item.setData(Qt.ItemDataRole.UserRole, m)
            if is_active:
                selected_row = idx
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                
            self.model_list.addItem(item)

        if self.model_list.count() > 0:
            self.model_list.setCurrentRow(selected_row)

    @Slot(str)
    def _on_models_error(self, err_msg: str):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("↻ Refresh")
        self.model_list.clear()
        self._all_models = []
        self.model_count_badge.setText("0 Models")
        item = QListWidgetItem(f"Error fetching models: {err_msg}")
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.model_list.addItem(item)
        self._reset_details_panel()
        self.details_name_lbl.setText("Connection Error")
        self.use_active_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

    def _reset_details_panel(self):
        self.details_active_badge.setVisible(False)
        self.details_type_badge.setVisible(False)
        self.details_notice_lbl.setVisible(False)
        self.details_params_lbl.setText("Parameters: —")
        self.details_family_lbl.setText("Family: —")
        self.details_quant_lbl.setText("Quantization: —")
        self.details_size_lbl.setText("Disk Size: —")
        self.details_context_lbl.setText("Context Length: —")
        self.details_caps_lbl.setText("Capabilities: —")
        self.details_host_lbl.setText("Remote Host: —")
        self.details_host_lbl.setVisible(False)

    @Slot(QListWidgetItem, QListWidgetItem)
    def _on_model_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if not current:
            return
        model_data = current.data(Qt.ItemDataRole.UserRole)
        if not model_data:
            self.use_active_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return

        model_name = model_data.get("name", "unknown")
        active_model = self.app_state.get("selected_model")
        is_active = (model_name == active_model)
        size_val = model_data.get("size", 0)

        is_cloud = bool(
            model_data.get("remote_model") 
            or model_data.get("remote_host") 
            or ":cloud" in model_name
            or (model_data.get("details", {}).get("family") == "" and size_val < 1000)
        )

        # Update action buttons
        self.use_active_btn.setEnabled(not is_active)
        self.use_active_btn.setText("✓ Active Model" if is_active else "✓ Use as Active")
        self.delete_btn.setEnabled(True)

        # Update Card Header
        self.details_name_lbl.setText(model_name)
        self.details_active_badge.setVisible(is_active)
        
        if is_cloud:
            self.details_type_badge.setText("🌐 Cloud Proxy")
            self.details_type_badge.setObjectName("TypeBadgeCloud")
            self.details_type_badge.setVisible(True)
            self.details_notice_lbl.setText("⚡ Cloud proxy model executed on remote Ollama servers.")
            self.details_notice_lbl.setVisible(True)
            self.details_size_lbl.setText(f"Disk Size: {format_size(size_val)} (Proxy)")
            self.details_params_lbl.setText("Parameters: Cloud Managed")
            self.details_quant_lbl.setText("Quantization: Cloud API")
            self.details_family_lbl.setText(f"Family: {model_data.get('family') or 'Cloud'}")
            self.details_context_lbl.setText("Context Length: Cloud Managed")
            self.details_host_lbl.setText(f"Remote Host: {model_data.get('remote_host') or 'https://ollama.com:443'}")
            self.details_host_lbl.setVisible(True)
        else:
            self.details_type_badge.setText("💾 Local GGUF")
            self.details_type_badge.setObjectName("TypeBadgeLocal")
            self.details_type_badge.setVisible(True)
            self.details_notice_lbl.setText("💾 Weights stored locally on this machine.")
            self.details_notice_lbl.setVisible(True)
            self.details_size_lbl.setText(f"Disk Size: {format_size(size_val)}")
            self.details_params_lbl.setText("Parameters: Loading...")
            self.details_quant_lbl.setText("Quantization: Loading...")
            self.details_family_lbl.setText(f"Family: {model_data.get('family', '—')}")
            self.details_context_lbl.setText("Context Length: Loading...")
            self.details_host_lbl.setVisible(False)

        # Re-apply styles on type badge to ensure correct theme color
        self.details_type_badge.style().unpolish(self.details_type_badge)
        self.details_type_badge.style().polish(self.details_type_badge)

        # Fetch detailed specifications via OllamaShowWorker
        show_worker = OllamaShowWorker(self.client, model_name)
        show_worker.finished.connect(self._on_model_info_fetched)
        self.workers.append(show_worker)
        show_worker.start()

    @Slot(str, dict)
    def _on_model_info_fetched(self, model_name: str, info: dict):
        current_item = self.model_list.currentItem()
        if not current_item:
            return
        curr_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not curr_data or curr_data.get("name") != model_name:
            return

        details = info.get("details", {}) or {}
        model_info = info.get("model_info", {}) or {}
        remote_model = info.get("remote_model") or curr_data.get("remote_model")
        remote_host = info.get("remote_host") or curr_data.get("remote_host")
        caps = info.get("capabilities", []) or []

        is_cloud = bool(
            remote_model 
            or remote_host 
            or ":cloud" in model_name 
            or (details.get("family") == "" and curr_data.get("size", 0) < 1000)
        )

        if is_cloud:
            params = details.get("parameter_size") or "Cloud Managed"
            quant = details.get("quantization_level") or "Cloud API"
            family = details.get("family") or remote_model or "Cloud"
            context_len = "Cloud Managed"
            host_str = remote_host or "https://ollama.com:443"
        else:
            params = details.get("parameter_size") or "Unknown"
            quant = details.get("quantization_level") or "Unknown"
            family = details.get("family") or curr_data.get("family", "Unknown")
            context_len = "Default"
            host_str = ""

        for k, v in model_info.items():
            if "context_length" in k:
                context_len = f"{v:,} tokens"
                break

        self.details_params_lbl.setText(f"Parameters: {params}")
        self.details_quant_lbl.setText(f"Quantization: {quant}")
        self.details_family_lbl.setText(f"Family: {family}")
        self.details_context_lbl.setText(f"Context Length: {context_len}")
        self.details_size_lbl.setText(f"Disk Size: {format_size(curr_data.get('size', 0))}")

        if host_str:
            self.details_host_lbl.setText(f"Remote Host: {host_str}")
            self.details_host_lbl.setVisible(True)
        else:
            self.details_host_lbl.setVisible(False)

        if caps:
            caps_str = ", ".join(caps)
            self.details_caps_lbl.setText(f"Capabilities: {caps_str}")
            self.details_caps_lbl.setVisible(True)
        else:
            self.details_caps_lbl.setText("Capabilities: completion")
            self.details_caps_lbl.setVisible(True)

    def _on_use_active_clicked(self):
        item = self.model_list.currentItem()
        if not item:
            return
        model_data = item.data(Qt.ItemDataRole.UserRole)
        if not model_data:
            return

        model_name = model_data.get("name")
        self.app_state.set("selected_model", model_name)
        logger.info("Active model switched to %s via ModelManagerDialog", model_name)
        self.refresh_models()
        self.models_updated.emit()

    def _on_delete_clicked(self):
        item = self.model_list.currentItem()
        if not item:
            return
        model_data = item.data(Qt.ItemDataRole.UserRole)
        if not model_data:
            return

        model_name = model_data.get("name")
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete model '{model_name}'?\nThis will remove the model weights from disk to free space.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.delete_btn.setEnabled(False)
        self.delete_btn.setText("Deleting...")

        worker = OllamaDeleteWorker(self.client, model_name)
        worker.finished.connect(self._on_delete_finished)
        self.workers.append(worker)
        worker.start()

    @Slot(bool, str)
    def _on_delete_finished(self, success: bool, message: str):
        self.delete_btn.setEnabled(True)
        self.delete_btn.setText("🗑 Delete")
        if success:
            QMessageBox.information(self, "Model Deleted", message)
            self.refresh_models()
            self.models_updated.emit()
        else:
            QMessageBox.critical(self, "Delete Failed", f"Could not delete model:\n{message}")

    def _on_pull_clicked(self):
        model_name = self.pull_input.text().strip()
        if not model_name:
            QMessageBox.warning(self, "Input Required", "Please enter an Ollama model name or tag.")
            return

        if self.current_pull_worker and self.current_pull_worker.isRunning():
            QMessageBox.warning(self, "Download In Progress", "Another model download is currently running.")
            return

        self.pull_btn.setEnabled(False)
        self.pull_input.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText(f"Initiating download for '{model_name}'...")
        self.cancel_pull_btn.setVisible(True)

        self.current_pull_worker = OllamaPullWorker(self.client, model_name)
        self.current_pull_worker.progress.connect(self._on_pull_progress)
        self.current_pull_worker.finished.connect(self._on_pull_finished)
        self.current_pull_worker.error.connect(self._on_pull_error)
        self.workers.append(self.current_pull_worker)
        self.current_pull_worker.start()

    @Slot(dict)
    def _on_pull_progress(self, progress_data: dict):
        status = progress_data.get("status", "")
        completed = progress_data.get("completed", 0)
        total = progress_data.get("total", 0)
        percent = progress_data.get("percent", 0.0)

        if total and total > 0:
            self.progress_bar.setValue(int(percent))
            comp_str = format_size(completed)
            tot_str = format_size(total)
            self.progress_label.setText(f"{status}: {comp_str} / {tot_str} ({percent:.1f}%)")
        else:
            self.progress_bar.setValue(0)
            self.progress_label.setText(f"{status}")

    @Slot(str)
    def _on_pull_finished(self, model_name: str):
        self._reset_pull_ui()
        QMessageBox.information(self, "Pull Complete", f"Model '{model_name}' was downloaded successfully!")
        self.refresh_models()
        self.models_updated.emit()

    @Slot(str)
    def _on_pull_error(self, err_msg: str):
        self._reset_pull_ui()
        QMessageBox.critical(self, "Pull Failed", f"Failed to download model:\n{err_msg}")

    def _on_cancel_pull_clicked(self):
        if self.current_pull_worker and self.current_pull_worker.isRunning():
            self.progress_label.setText("Cancelling download...")
            self.current_pull_worker.stop()

    def _reset_pull_ui(self):
        self.pull_btn.setEnabled(True)
        self.pull_input.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(False)
        self.cancel_pull_btn.setVisible(False)
        self.current_pull_worker = None

    def closeEvent(self, event):
        if self.current_pull_worker and self.current_pull_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Download Active",
                "A model download is currently in progress. Closing this window will cancel it. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.current_pull_worker.stop()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
