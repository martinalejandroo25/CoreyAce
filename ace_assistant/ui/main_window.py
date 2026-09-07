from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QLabel, QLineEdit, QTextEdit
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from ui.avatar import AceAvatar
import json
import os
import sys
import wave
import io
import ctypes
import pyaudio
import numpy as np


def _open_pyaudio_quietly():
    """Inicializa PyAudio suprimiendo los mensajes de error de ALSA/JACK
    que se imprimen directamente en el descriptor de fichero de stderr (fd=2)."""
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    old_stderr_fd = os.dup(2)          # guardar stderr real
    os.dup2(devnull_fd, 2)             # redirigir stderr → /dev/null
    os.close(devnull_fd)
    try:
        pa = pyaudio.PyAudio()
    finally:
        os.dup2(old_stderr_fd, 2)      # restaurar stderr real
        os.close(old_stderr_fd)
    return pa


# ---------------------------------------------------------------------------
# Estilos de botón reutilizables (exportados para main.py)
# ---------------------------------------------------------------------------
_BTN_STYLE = """
    QPushButton {{
        background-color: #1a1a24;
        border: 1px solid #333345;
        border-radius: 7px;
        color: #6e6e8a;
        font-family: 'Courier New', Courier, monospace;
        font-size: 11px;
        font-weight: bold;
        padding: 5px 10px;
    }}
    QPushButton:hover {{
        background-color: #22222e;
        border-color: #00c3ff;
        color: #00c3ff;
    }}
    QPushButton:pressed {{
        background-color: #111118;
        color: #aaaacc;
    }}
"""

_BTN_ACTIVE_STYLE = """
    QPushButton {{
        background-color: #0d2b1a;
        border: 1px solid #39ff14;
        border-radius: 7px;
        color: #39ff14;
        font-family: 'Courier New', Courier, monospace;
        font-size: 11px;
        font-weight: bold;
        padding: 5px 10px;
    }}
    QPushButton:hover {{
        background-color: #0e3320;
        border-color: #55ff33;
        color: #55ff33;
    }}
    QPushButton:pressed {{
        background-color: #081a0f;
    }}
"""


# ---------------------------------------------------------------------------
# Reproductor de audio con Lip-sync
# ---------------------------------------------------------------------------

class AudioPlayerThread(QThread):
    rms_signal = pyqtSignal(float)
    finished_signal = pyqtSignal()

    def __init__(self, audio_data):
        super().__init__()
        self.audio_data = audio_data
        self.running = False

    def run(self):
        self.running = True
        try:
            wav_file = wave.open(io.BytesIO(self.audio_data), 'rb')
            p = _open_pyaudio_quietly()
            stream = p.open(
                format=p.get_format_from_width(wav_file.getsampwidth()),
                channels=wav_file.getnchannels(),
                rate=wav_file.getframerate(),
                output=True
            )

            chunk_size = 512
            data = wav_file.readframes(chunk_size)
            max_volume_threshold = 2200.0

            while data and self.running:
                stream.write(data)
                try:
                    samples = np.frombuffer(data, dtype=np.int16)
                    if len(samples) > 0:
                        rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
                        norm_rms = min(1.0, rms / max_volume_threshold)
                        self.rms_signal.emit(norm_rms)
                    else:
                        self.rms_signal.emit(0.0)
                except Exception:
                    self.rms_signal.emit(0.0)

                data = wav_file.readframes(chunk_size)

            stream.stop_stream()
            stream.close()
            p.terminate()
            wav_file.close()
        except Exception as e:
            print(f"[AudioPlayer] Error al reproducir audio: {e}")

        self.rms_signal.emit(0.0)
        self.finished_signal.emit()

    def stop(self):
        self.running = False


# ---------------------------------------------------------------------------
# Ventana Principal
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    settings_saved = pyqtSignal()

    # Estilos accesibles desde AceApp para cambiar estado de botones
    BTN_STYLE = _BTN_STYLE
    BTN_ACTIVE_STYLE = _BTN_ACTIVE_STYLE

    def __init__(self, config_path=None):
        super().__init__()
        self.config_path = config_path or self._find_config()
        self.setWindowTitle("Corey Beepington — ACE CRT Companion")
        self.setFixedSize(500, 660)
        self.setStyleSheet("background-color: #1a1a22;")
        self.audio_player = None

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # ------------------------------------------------------------------
        # CHASIS EXTERIOR DEL TELEVISOR RETRO
        # ------------------------------------------------------------------
        crt_chassis = QWidget()
        crt_chassis.setObjectName("CrtChassis")
        crt_chassis.setStyleSheet("""
            QWidget#CrtChassis {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e2e1db, stop:0.05 #dad9d3,
                    stop:0.95 #c8c7c0, stop:1 #b5b4ad);
                border: 4px solid #a8a7a0;
                border-radius: 24px;
            }
        """)
        chassis_layout = QVBoxLayout(crt_chassis)
        chassis_layout.setContentsMargins(18, 18, 18, 12)
        chassis_layout.setSpacing(8)

        # BISEL INTERNO
        screen_bezel = QWidget()
        screen_bezel.setObjectName("ScreenBezel")
        screen_bezel.setStyleSheet("""
            QWidget#ScreenBezel {
                background-color: #1c1c1c;
                border: 5px solid #101010;
                border-top-color: #0c0c0c;
                border-left-color: #0c0c0c;
                border-right-color: #242424;
                border-bottom-color: #242424;
                border-radius: 18px;
            }
        """)
        bezel_layout = QVBoxLayout(screen_bezel)
        bezel_layout.setContentsMargins(10, 10, 10, 10)

        # AVATAR
        self.avatar = AceAvatar()
        bezel_layout.addWidget(self.avatar, alignment=Qt.AlignmentFlag.AlignCenter)
        chassis_layout.addWidget(screen_bezel)

        # PANEL DE CONTROL INFERIOR (botonera retro)
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(4, 4, 4, 4)
        control_layout.setSpacing(8)

        # Altavoz izquierdo
        speaker_left = QLabel("░░░░░░░░")
        speaker_left.setStyleSheet("color: #9e9d96; font-size: 10px; font-family: monospace;")

        # Marca
        brand_label = QLabel("PANASONIC")
        brand_label.setStyleSheet("""
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-weight: bold;
            font-size: 11px;
            color: #55544e;
            letter-spacing: 2px;
        """)

        # Botón Power
        btn_power = QPushButton()
        btn_power.setFixedSize(22, 22)
        btn_power.setToolTip("Apagar Ace")
        btn_power.setStyleSheet("""
            QPushButton {
                background-color: #a32626;
                border: 2px solid #6b1818;
                border-radius: 11px;
            }
            QPushButton:hover { background-color: #c22d2d; }
            QPushButton:pressed { background-color: #591414; border-style: inset; }
        """)

        # LED / botón de ajustes
        self.power_led = QPushButton()
        self.power_led.setFixedSize(10, 10)
        self.power_led.setCursor(Qt.CursorShape.PointingHandCursor)

        led_layout = QVBoxLayout()
        led_layout.setContentsMargins(0, 0, 0, 0)
        led_layout.addWidget(self.power_led, alignment=Qt.AlignmentFlag.AlignCenter)

        # Altavoz derecho
        speaker_right = QLabel("░░░░░░░░")
        speaker_right.setStyleSheet("color: #9e9d96; font-size: 10px; font-family: monospace;")

        control_layout.addWidget(btn_power)
        control_layout.addLayout(led_layout)
        control_layout.addWidget(speaker_left)
        control_layout.addStretch()
        control_layout.addWidget(brand_label, alignment=Qt.AlignmentFlag.AlignCenter)
        control_layout.addStretch()
        control_layout.addWidget(speaker_right)
        chassis_layout.addWidget(control_panel)

        main_layout.addWidget(crt_chassis)

        # ------------------------------------------------------------------
        # FILA DE BOTONES DE ACCIÓN (bajo el chasis)
        # ------------------------------------------------------------------
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        qss_channel_btn = """
            QPushButton {
                background-color: #dad9d3;
                border: 2px solid #a8a7a0;
                border-bottom: 3px solid #8e8d87;
                border-radius: 6px;
                color: #403f3a;
                font-family: 'Courier New', Courier, monospace;
                font-weight: bold;
                font-size: 10px;
                padding: 5px 8px;
            }
            QPushButton:hover { background-color: #e5e4de; color: #2b2a26; }
            QPushButton:pressed {
                background-color: #c8c7c0;
                border-bottom-width: 1px;
                padding-top: 7px;
                padding-bottom: 3px;
            }
        """
        self.btn_online = QPushButton("TV/VIDEO\n(ONLINE)")
        self.btn_online.setStyleSheet(qss_channel_btn)
        self.btn_local = QPushButton("CH.SELECT\n(LOCAL)")
        self.btn_local.setStyleSheet(qss_channel_btn)

        # Botones de periféricos (cámara y micrófono)
        self.btn_camera = QPushButton("📷 CAM")
        self.btn_camera.setStyleSheet(_BTN_STYLE)
        self.btn_camera.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_camera.setToolTip("Activar / desactivar cámara y detección de emociones")

        self.btn_mic = QPushButton("🎙 MIC")
        self.btn_mic.setStyleSheet(_BTN_STYLE)
        self.btn_mic.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mic.setToolTip("Activar / desactivar entrada por micrófono (STT)")

        action_row.addWidget(self.btn_online)
        action_row.addWidget(self.btn_local)
        action_row.addStretch()
        action_row.addWidget(self.btn_camera)
        action_row.addWidget(self.btn_mic)

        main_layout.addLayout(action_row)

        # ------------------------------------------------------------------
        # PANTALLA DE RESPUESTA DE ACE (texto en tiempo real, estilo terminal)
        # ------------------------------------------------------------------
        self.response_display = QTextEdit()
        self.response_display.setReadOnly(True)
        self.response_display.setFixedHeight(76)
        self.response_display.setPlaceholderText("ACE responderá aquí...")
        self.response_display.setStyleSheet("""
            QTextEdit {
                background-color: #080810;
                border: 1px solid #1e1e2e;
                border-radius: 8px;
                color: #00c3ff;
                font-family: 'Courier New', Courier, monospace;
                font-size: 11px;
                padding: 8px 12px;
            }
            QScrollBar:vertical {
                background: #0a0a14;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #1e3a5a;
                border-radius: 3px;
            }
        """)
        main_layout.addWidget(self.response_display)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Escribe una pregunta para ACE y pulsa Enter...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #101014;
                border: 2px solid #00c3ff;
                border-radius: 8px;
                color: #00c3ff;
                font-family: 'Courier New', Courier, monospace;
                font-weight: bold;
                font-size: 12px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border-color: #39ff14;
                color: #39ff14;
            }
            QLineEdit:disabled {
                border-color: #334455;
                color: #445566;
            }
        """)
        main_layout.addWidget(self.input_field)

        # ------------------------------------------------------------------
        # Conexiones
        # ------------------------------------------------------------------
        btn_power.clicked.connect(self.close)
        self.power_led.clicked.connect(self._open_settings)
        self.btn_online.clicked.connect(self._set_mode_online)
        self.btn_local.clicked.connect(self._set_mode_local)

        self._update_led_from_config()

    # ------------------------------------------------------------------
    # LED de estado
    # ------------------------------------------------------------------

    def _update_led_from_config(self):
        color = "#39ff14"
        border_color = "#1e850a"
        tooltip = "ACE: Cerebro (LLM): ONLINE | Voz (TTS): ONLINE (clic para configurar)"

        cfg_file = self.config_path
        if cfg_file and os.path.exists(cfg_file):
            try:
                with open(cfg_file, "r") as f:
                    cfg = json.load(f)
                llm_m = cfg.get("llm_mode", "online")
                tts_m = cfg.get("tts_mode", "online")

                if llm_m == "local" and tts_m == "local":
                    color = "#ffaa00"
                    border_color = "#b87b00"
                elif llm_m == "local" or tts_m == "local":
                    color = "#ff8800"
                    border_color = "#b06000"

                tooltip = f"ACE: LLM → {llm_m.upper()} | TTS → {tts_m.upper()} (clic para configurar)"
            except Exception:
                pass

        self.power_led.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border-radius: 5px;
                border: 1px solid {border_color};
            }}
            QPushButton:hover {{
                background-color: {color};
                border-color: #ffffff;
            }}
        """)
        self.power_led.setToolTip(tooltip)

    def _find_config(self):
        """Busca config.json en el directorio de trabajo actual."""
        candidates = ["config.json", os.path.join(os.path.dirname(__file__), "..", "config.json")]
        for c in candidates:
            if os.path.exists(c):
                return c
        return "config.json"

    # ------------------------------------------------------------------
    # Diálogos y acciones rápidas
    # ------------------------------------------------------------------

    def _open_settings(self):
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self, config_path=self.config_path)
        if dialog.exec():
            self._update_led_from_config()
            self.settings_saved.emit()

    def _set_mode_online(self):
        self._set_config_mode("online")

    def _set_mode_local(self):
        self._set_config_mode("local")

    def _set_config_mode(self, mode):
        cfg_file = self.config_path
        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, "r") as f:
                    cfg = json.load(f)
                cfg["llm_mode"] = mode
                cfg["tts_mode"] = mode
                cfg["mode"] = mode
                with open(cfg_file, "w") as f:
                    json.dump(cfg, f, indent=2)
                self._update_led_from_config()
                print(f"[MainWindow] Modo rápido cambiado a: {mode.upper()}")
                self.settings_saved.emit()
            except Exception as e:
                print(f"[MainWindow] Error al cambiar modo de forma rápida: {e}")

    # ------------------------------------------------------------------
    # Respuesta de ACE
    # ------------------------------------------------------------------

    def show_response(self, text):
        """Muestra el texto de respuesta de ACE en la pantalla de terminal
        de forma inmediata, antes de que el audio TTS haya terminado."""
        self.set_thinking_mode(False)
        self.response_display.setPlainText(text)
        # Scroll al final para respuestas largas
        scrollbar = self.response_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def set_thinking_mode(self, is_thinking):
        """Alterna entre estado 'pensando' (texto atenuado) y estado normal."""
        if is_thinking:
            self.response_display.setStyleSheet("""
                QTextEdit {
                    background-color: #080810;
                    border: 1px solid #1e1e2e;
                    border-radius: 8px;
                    color: #334455;
                    font-family: 'Courier New', Courier, monospace;
                    font-size: 11px;
                    padding: 8px 12px;
                }
                QScrollBar:vertical { background: #0a0a14; width: 6px; border-radius: 3px; }
                QScrollBar::handle:vertical { background: #1e3a5a; border-radius: 3px; }
            """)
            self.response_display.setPlainText("▌ procesando respuesta...")
        else:
            self.response_display.setStyleSheet("""
                QTextEdit {
                    background-color: #080810;
                    border: 1px solid #1e1e2e;
                    border-radius: 8px;
                    color: #00c3ff;
                    font-family: 'Courier New', Courier, monospace;
                    font-size: 11px;
                    padding: 8px 12px;
                }
                QScrollBar:vertical { background: #0a0a14; width: 6px; border-radius: 3px; }
                QScrollBar::handle:vertical { background: #1e3a5a; border-radius: 3px; }
            """)
