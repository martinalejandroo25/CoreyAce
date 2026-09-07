import json
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget,
                             QLabel, QLineEdit, QComboBox, QPushButton,
                             QFormLayout, QGroupBox, QMessageBox, QCheckBox,
                             QScrollArea, QSizePolicy)
from PyQt6.QtCore import Qt


class SettingsDialog(QDialog):

    def __init__(self, parent=None, config_path='config.json'):
        super().__init__(parent)
        self.config_path = config_path
        self.setWindowTitle("ACE — Panel de Configuración")
        self.setModal(True)
        self.setMinimumSize(480, 620)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.resize(480, 640)

        self.setStyleSheet("""
            QDialog {
                background-color: #12121a;
                color: #d8d8e8;
                font-family: 'Courier New', Courier, monospace;
            }

            /* ─── ScrollArea ─────────────────────────────────── */
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: #1a1a24;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #333348;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: #00c3ff; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

            /* ─── Labels ─────────────────────────────────────── */
            QLabel#SectionTitle {
                color: #39ff14;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 2px;
            }
            QLabel {
                color: #9090b8;
                font-size: 11px;
            }

            /* ─── GroupBox ───────────────────────────────────── */
            QGroupBox {
                background-color: #181824;
                border: 1px solid #2a2a3e;
                border-radius: 10px;
                margin-top: 14px;
                padding: 14px 14px 10px 14px;
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 14px;
                top: -1px;
                padding: 0 6px;
                background-color: #12121a;
                color: #00c3ff;
                font-weight: bold;
                font-size: 10px;
                letter-spacing: 1px;
            }

            /* ─── Inputs ─────────────────────────────────────── */
            QLineEdit {
                background-color: #0e0e18;
                border: 1px solid #2a2a3e;
                border-radius: 6px;
                color: #d8d8e8;
                padding: 7px 10px;
                font-size: 11px;
                min-height: 28px;
            }
            QLineEdit:focus {
                border-color: #00c3ff;
                background-color: #10101e;
            }
            QLineEdit:hover {
                border-color: #3a3a5e;
            }

            /* ─── ComboBox ───────────────────────────────────── */
            QComboBox {
                background-color: #0e0e18;
                border: 1px solid #2a2a3e;
                border-radius: 6px;
                color: #d8d8e8;
                padding: 6px 10px;
                font-size: 11px;
                min-height: 28px;
            }
            QComboBox:focus { border-color: #00c3ff; }
            QComboBox:hover { border-color: #3a3a5e; }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: right;
                width: 22px;
                border-left: 1px solid #2a2a3e;
            }
            QComboBox QAbstractItemView {
                background-color: #181824;
                border: 1px solid #2a2a3e;
                color: #d8d8e8;
                selection-background-color: #1e3c5a;
            }

            /* ─── CheckBox ───────────────────────────────────── */
            QCheckBox {
                color: #c0c0d8;
                font-size: 11px;
                spacing: 10px;
                padding: 2px 0;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #0e0e18;
                border: 1px solid #2a2a3e;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: #39ff14;
                border-color: #39ff14;
                image: none;
            }
            QCheckBox::indicator:hover {
                border-color: #00c3ff;
            }

            /* ─── Buttons ────────────────────────────────────── */
            QPushButton#SaveButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #1a3d28, stop:1 #0e2418);
                border: 1px solid #2d5a41;
                border-radius: 8px;
                color: #39ff14;
                font-weight: bold;
                font-size: 12px;
                letter-spacing: 1px;
                padding: 10px 28px;
                min-width: 120px;
            }
            QPushButton#SaveButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #22503a, stop:1 #142e1e);
                border-color: #39ff14;
            }
            QPushButton#SaveButton:pressed {
                background-color: #0a1a10;
                padding-top: 12px;
                padding-bottom: 8px;
            }

            QPushButton#CancelButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #3a1e1e, stop:1 #241010);
                border: 1px solid #5a2d2d;
                border-radius: 8px;
                color: #ff4444;
                font-weight: bold;
                font-size: 12px;
                letter-spacing: 1px;
                padding: 10px 28px;
                min-width: 120px;
            }
            QPushButton#CancelButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #4e2727, stop:1 #301515);
                border-color: #ff4444;
            }
            QPushButton#CancelButton:pressed {
                background-color: #1a0a0a;
                padding-top: 12px;
                padding-bottom: 8px;
            }
        """)

        self.config = self._load_current_config()
        self._init_ui()
        self._populate_fields()

    # ------------------------------------------------------------------
    # Config I/O
    # ------------------------------------------------------------------

    def _load_current_config(self):
        default_config = {
            "llm_mode": "online",
            "tts_mode": "online",
            "online_llm": "openai",
            "local_llm": "llama3",
            "online_voice": "elevenlabs",
            "local_voice": "piper",
            "camera_enabled": False,
            "mic_enabled": False,
            "apis": {
                "openai_key": "",
                "elevenlabs_key": "",
                "anthropic_key": "",
                "gemini_key": ""
            }
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                # Migración desde campo "mode" heredado
                if "mode" in config and "llm_mode" not in config:
                    config["llm_mode"] = config["mode"]
                    config["tts_mode"] = config["mode"]
                # Rellenar campos ausentes
                if 'apis' not in config:
                    config['apis'] = {}
                for key in default_config['apis']:
                    config['apis'].setdefault(key, "")
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
            except Exception as e:
                print(f"[SettingsDialog] Error cargando config: {e}")
        return default_config

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _init_ui(self):
        # Outer layout con márgenes generosos
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scroll area para soportar pantallas pequeñas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)

        # Widget interior
        inner_widget = QWidget()
        inner_widget.setStyleSheet("background: transparent;")
        scroll.setWidget(inner_widget)

        layout = QVBoxLayout(inner_widget)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(16)

        # ── Título ──────────────────────────────────────────────────
        title = QLabel("CONFIGURACIÓN DEL SISTEMA")
        title.setObjectName("SectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Todos los cambios se guardan en config.json")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #44445a; font-size: 10px; margin-bottom: 4px;")
        layout.addWidget(subtitle)

        # ── 1. MODO DE EJECUCIÓN ─────────────────────────────────────
        mode_group = QGroupBox("MODO DE EJECUCIÓN (INDEPENDIENTES)")
        mode_form = QFormLayout(mode_group)
        mode_form.setContentsMargins(10, 18, 10, 10)
        mode_form.setSpacing(12)
        mode_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.combo_llm_mode = QComboBox()
        self.combo_llm_mode.addItems(["Online (APIs de nube)", "Local (Ollama)"])

        self.combo_tts_mode = QComboBox()
        self.combo_tts_mode.addItems(["Online (API ElevenLabs)", "Local (ChatTTS / Piper)"])

        mode_form.addRow("Cerebro (LLM):", self.combo_llm_mode)
        mode_form.addRow("Voz (TTS):", self.combo_tts_mode)
        layout.addWidget(mode_group)

        # ── 2. APIS Y MODELOS CLOUD ──────────────────────────────────
        online_group = QGroupBox("APIS Y MODELOS CLOUD")
        online_form = QFormLayout(online_group)
        online_form.setContentsMargins(10, 18, 10, 10)
        online_form.setSpacing(12)
        online_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.combo_online_llm = QComboBox()
        self.combo_online_llm.addItems([
            "OpenAI — ChatGPT / GPT-4o",
            "Anthropic — Claude 3.5 Sonnet",
            "Google — Gemini 1.5 Flash"
        ])

        self.edit_openai_key = QLineEdit()
        self.edit_openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_openai_key.setPlaceholderText("sk-...")

        self.edit_anthropic_key = QLineEdit()
        self.edit_anthropic_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_anthropic_key.setPlaceholderText("sk-ant-...")

        self.edit_gemini_key = QLineEdit()
        self.edit_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_gemini_key.setPlaceholderText("AIzaSy...")

        self.combo_online_voice = QComboBox()
        self.combo_online_voice.addItems(["ElevenLabs (Premium TTS)"])

        self.edit_eleven_key = QLineEdit()
        self.edit_eleven_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_eleven_key.setPlaceholderText("API Key de ElevenLabs...")

        online_form.addRow("Proveedor LLM:", self.combo_online_llm)
        online_form.addRow("OpenAI Key:", self.edit_openai_key)
        online_form.addRow("Anthropic Key:", self.edit_anthropic_key)
        online_form.addRow("Gemini Key:", self.edit_gemini_key)
        online_form.addRow("TTS Online:", self.combo_online_voice)
        online_form.addRow("ElevenLabs Key:", self.edit_eleven_key)
        layout.addWidget(online_group)

        # ── 3. SERVICIOS LOCALES ─────────────────────────────────────
        local_group = QGroupBox("SERVICIOS LOCALES")
        local_form = QFormLayout(local_group)
        local_form.setContentsMargins(10, 18, 10, 10)
        local_form.setSpacing(12)
        local_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.edit_local_llm = QLineEdit()
        self.edit_local_llm.setPlaceholderText("Nombre del modelo Ollama (ej: llama3, mistral, phi3)")

        self.combo_local_voice = QComboBox()
        self.combo_local_voice.addItems([
            "Piper (TTS local rápido)",
            "ChatTTS (Voz natural local)"
        ])

        local_form.addRow("Modelo Ollama:", self.edit_local_llm)
        local_form.addRow("TTS Local:", self.combo_local_voice)
        layout.addWidget(local_group)

        # ── 4. PERIFÉRICOS ───────────────────────────────────────────
        hw_group = QGroupBox("PERIFÉRICOS Y CAPTURA")
        hw_layout = QVBoxLayout(hw_group)
        hw_layout.setContentsMargins(14, 20, 14, 14)
        hw_layout.setSpacing(10)

        self.check_camera = QCheckBox("Activar Cámara  (lectura de emociones faciales en tiempo real)")
        self.check_mic = QCheckBox("Activar Micrófono  (dictado de voz a texto — STT)")

        hw_layout.addWidget(self.check_camera)
        hw_layout.addWidget(self.check_mic)
        layout.addWidget(hw_group)

        layout.addStretch()

        # ── Botones ──────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)

        self.btn_cancel = QPushButton("CANCELAR")
        self.btn_cancel.setObjectName("CancelButton")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("GUARDAR")
        self.btn_save.setObjectName("SaveButton")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self._save_config)

        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)

        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Populate & Save
    # ------------------------------------------------------------------

    def _populate_fields(self):
        # LLM mode
        self.combo_llm_mode.setCurrentIndex(
            0 if self.config.get("llm_mode", "online") == "online" else 1
        )
        # TTS mode
        self.combo_tts_mode.setCurrentIndex(
            0 if self.config.get("tts_mode", "online") == "online" else 1
        )
        # Online LLM provider
        online_map = {"openai": 0, "anthropic": 1, "gemini": 2}
        self.combo_online_llm.setCurrentIndex(
            online_map.get(self.config.get("online_llm", "openai"), 0)
        )
        # API keys
        apis = self.config.get("apis", {})
        self.edit_openai_key.setText(apis.get("openai_key", ""))
        self.edit_anthropic_key.setText(apis.get("anthropic_key", ""))
        self.edit_gemini_key.setText(apis.get("gemini_key", ""))
        self.edit_eleven_key.setText(apis.get("elevenlabs_key", ""))
        # Local LLM
        self.edit_local_llm.setText(self.config.get("local_llm", "llama3"))
        # Local voice
        local_voice_map = {"piper": 0, "chattts": 1}
        self.combo_local_voice.setCurrentIndex(
            local_voice_map.get(self.config.get("local_voice", "piper"), 0)
        )
        # Hardware
        self.check_camera.setChecked(self.config.get("camera_enabled", False))
        self.check_mic.setChecked(self.config.get("mic_enabled", False))

    def _save_config(self):
        llm_mode = "online" if self.combo_llm_mode.currentIndex() == 0 else "local"
        tts_mode = "online" if self.combo_tts_mode.currentIndex() == 0 else "local"
        online_llm = ["openai", "anthropic", "gemini"][self.combo_online_llm.currentIndex()]
        local_llm = self.edit_local_llm.text().strip() or "llama3"
        local_voice = ["piper", "chattts"][self.combo_local_voice.currentIndex()]

        self.config.update({
            "llm_mode": llm_mode,
            "tts_mode": tts_mode,
            "mode": llm_mode,  # campo heredado
            "online_llm": online_llm,
            "local_llm": local_llm,
            "online_voice": "elevenlabs",
            "local_voice": local_voice,
            "camera_enabled": self.check_camera.isChecked(),
            "mic_enabled": self.check_mic.isChecked(),
        })
        self.config["apis"].update({
            "openai_key": self.edit_openai_key.text().strip(),
            "anthropic_key": self.edit_anthropic_key.text().strip(),
            "gemini_key": self.edit_gemini_key.text().strip(),
            "elevenlabs_key": self.edit_eleven_key.text().strip(),
        })

        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            QMessageBox.information(
                self, "✓ Configuración guardada",
                "Los cambios se han guardado correctamente.\n"
                "Reinicia ACE si cambias el modo de TTS local."
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar la configuración:\n{e}")
