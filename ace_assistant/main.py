import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal
from ui.main_window import MainWindow, AudioPlayerThread
from core.perception import PerceptionThread
from core.brain import BrainRouter
from core.voice import VoiceRouter


class AceQueryThread(QThread):
    """Hilo secundario que gestiona la llamada al LLM + síntesis de voz
    sin bloquear el hilo principal (animación CRT).

    Emite dos señales:
    - text_ready : str  → El texto de respuesta del LLM (llega rápido)
    - audio_ready: bytes → Los bytes WAV generados por TTS (puede tardar más)
    - error_signal: str → Descripción del error si falla el LLM
    """
    text_ready   = pyqtSignal(str)
    audio_ready  = pyqtSignal(bytes)
    error_signal = pyqtSignal(str)

    def __init__(self, brain_router, voice_router, user_text, message_history):
        super().__init__()
        self.brain = brain_router
        self.voice = voice_router
        self.user_text = user_text
        self.history = message_history

    def run(self):
        # ── Paso 1: Llamada al LLM ─────────────────────────────────────
        try:
            messages = self.history + [{"role": "user", "content": self.user_text}]
            ai_message = self.brain.generate_response(messages)

            if hasattr(ai_message, 'content'):
                response_text = ai_message.content
            else:
                response_text = str(ai_message)

            if not response_text:
                raise Exception("La IA no devolvió texto de respuesta.")

        except Exception as e:
            self.error_signal.emit(str(e))
            return

        # ── Paso 2: Emitir texto inmediatamente (UI ya puede mostrarlo) ─
        self.text_ready.emit(response_text)

        # ── Paso 3: Síntesis de voz (puede tardar en ChatTTS/CPU) ──────
        audio_bytes = []
        def store_audio(data):
            audio_bytes.append(data)

        self.voice.speak(response_text, store_audio)

        # VoiceRouter ya incluye fallback de silencio, nunca debería estar vacío
        if not audio_bytes:
            audio_bytes.append(self.voice._generate_silence(300))

        self.audio_ready.emit(audio_bytes[0])


class AceApp:
    def __init__(self):
        self.app = QApplication(sys.argv)

        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(base_dir, "config.json")

        self.window = MainWindow(config_path=self.config_path)

        self.brain = BrainRouter(config_path=self.config_path)
        self.voice = VoiceRouter(config_path=self.config_path)
        self.history = []
        self._pending_text = ""  # guarda el texto mientras TTS procesa

        # Hilo de percepción (cámara + emociones)
        self.perception = PerceptionThread()
        self.perception.emotion_detected.connect(self.handle_emotion)

        # Conexiones UI
        self.window.input_field.returnPressed.connect(self.on_submit)
        self.window.btn_camera.clicked.connect(self._toggle_camera)
        self.window.btn_mic.clicked.connect(self._toggle_mic)
        self.window.settings_saved.connect(self.on_settings_saved)

        self._camera_active = False
        self._mic_active = False

        # Sincronizar periféricos con la configuración inicial
        self._init_peripherals_from_config()

    # ------------------------------------------------------------------
    # Periféricos
    # ------------------------------------------------------------------

    def _init_peripherals_from_config(self):
        camera_enabled = self.brain.config.get("camera_enabled", False)
        mic_enabled = self.brain.config.get("mic_enabled", False)
        self._toggle_camera(force_state=camera_enabled)
        self._toggle_mic(force_state=mic_enabled)

    def on_settings_saved(self):
        print("[AceApp] Configuración guardada detectada. Sincronizando...")
        self.brain._reload_config()
        self.voice._reload_config()

        camera_enabled = self.brain.config.get("camera_enabled", False)
        mic_enabled = self.brain.config.get("mic_enabled", False)

        if camera_enabled != self._camera_active:
            self._toggle_camera(force_state=camera_enabled)
        if mic_enabled != self._mic_active:
            self._toggle_mic(force_state=mic_enabled)

    def _toggle_camera(self, force_state=None):
        if force_state is not None:
            self._camera_active = force_state
        else:
            self._camera_active = not self._camera_active

        if self._camera_active:
            self.perception.start()
            self.window.btn_camera.setText("📷 CAM ON")
            self.window.btn_camera.setStyleSheet(self.window.BTN_ACTIVE_STYLE)
        else:
            self.perception.stop()
            self.perception.requestInterruption()
            self.perception.wait(2000)
            self.window.btn_camera.setText("📷 CAM")
            self.window.btn_camera.setStyleSheet(self.window.BTN_STYLE)

    def _toggle_mic(self, force_state=None):
        if force_state is not None:
            self._mic_active = force_state
        else:
            self._mic_active = not self._mic_active

        if self._mic_active:
            self.window.btn_mic.setText("🎙 MIC ON")
            self.window.btn_mic.setStyleSheet(self.window.BTN_ACTIVE_STYLE)
        else:
            self.window.btn_mic.setText("🎙 MIC")
            self.window.btn_mic.setStyleSheet(self.window.BTN_STYLE)

    # ------------------------------------------------------------------
    # Emociones
    # ------------------------------------------------------------------

    def handle_emotion(self, emotion):
        if emotion == "happy":
            self.window.avatar.set_emotion("happy")
        elif emotion == "sad":
            self.window.avatar.set_emotion("sad")
        else:
            self.window.avatar.set_emotion("neutral")

    # ------------------------------------------------------------------
    # Ciclo de pregunta / respuesta
    # ------------------------------------------------------------------

    def on_submit(self):
        text = self.window.input_field.text().strip()
        if not text:
            return

        self.window.input_field.setEnabled(False)
        self.window.input_field.setPlaceholderText("ACE está pensando...")
        self.window.set_thinking_mode(True)

        # Detener reproducción anterior si la hay
        if self.window.audio_player and self.window.audio_player.isRunning():
            self.window.audio_player.stop()
            self.window.audio_player.wait()

        self.window.avatar.set_emotion("thinking")

        self.query_thread = AceQueryThread(self.brain, self.voice, text, self.history)
        self.query_thread.text_ready.connect(self.on_text_received)
        self.query_thread.audio_ready.connect(self.on_audio_received)
        self.query_thread.error_signal.connect(self.on_response_error)
        self.query_thread.start()

        self.history.append({"role": "user", "content": text})

    def on_text_received(self, response_text):
        """Se llama en cuanto el LLM responde — antes de que el TTS termine.
        Mostramos el texto inmediatamente para que el usuario no espere sin feedback."""
        self._pending_text = response_text
        self.history.append({"role": "assistant", "content": response_text})

        # Mostrar texto de forma instantánea
        self.window.set_thinking_mode(False)
        self.window.show_response(response_text)
        self.window.avatar.set_emotion("neutral")

        # Rehabilitar campo de texto: el usuario ya puede leer/escribir
        # aunque el audio todavía se esté sintetizando
        self.window.input_field.setEnabled(True)
        self._reset_input()

        print(f"[ACE → texto] {response_text}")

    def on_audio_received(self, audio_bytes):
        """Se llama cuando el TTS termina de sintetizar (puede ser varios segundos después)."""
        self.window.audio_player = AudioPlayerThread(audio_bytes)
        self.window.audio_player.rms_signal.connect(self.window.avatar.update_lip_sync)
        self.window.audio_player.finished_signal.connect(self.on_audio_finished)
        self.window.audio_player.start()

    def on_response_error(self, error_msg):
        print(f"[AceApp] Error: {error_msg}")
        self.window.set_thinking_mode(False)
        self.window.show_response(f"[Error] {error_msg}")
        self.window.input_field.setEnabled(True)
        self._reset_input()
        self.window.avatar.set_emotion("sad")

    def on_audio_finished(self):
        self.window.avatar.update_lip_sync(0.0)

    def _reset_input(self):
        self.window.input_field.clear()
        self.window.input_field.setPlaceholderText("Escribe una pregunta para ACE y pulsa Enter...")

    # ------------------------------------------------------------------
    # Arranque
    # ------------------------------------------------------------------

    def run(self):
        self.window.show()
        sys.exit(self.app.exec())


if __name__ == "__main__":
    ace = AceApp()
    ace.run()
