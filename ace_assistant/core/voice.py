import requests
import json
import tempfile
import subprocess
import os
import io
import wave
import unicodedata
import re

class VoiceRouter:
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self._reload_config()
        self.chattts_engine = None

    def _reload_config(self):
        """Carga la configuración más reciente desde el disco"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error recargando config.json en VoiceRouter: {e}")
                self.config = {"tts_mode": "online", "apis": {}}
        else:
            self.config = {"tts_mode": "online", "apis": {}}

    def speak(self, text, audio_callback):
        """Genera audio y llama al callback con los datos en bytes.
        Si falla la síntesis, llama igualmente al callback con audio vacío
        para que el flujo de la aplicación no se rompa."""
        self._reload_config()
        audio_data = None
        try:
            tts_mode = self.config.get('tts_mode', 'online')
            local_voice = self.config.get('local_voice', 'piper')

            if tts_mode == 'online':
                audio_data = self._elevenlabs_tts(text)
            else:
                if local_voice == 'chattts':
                    audio_data = self._chattts_tts(text)
                else:
                    audio_data = self._piper_tts(text)

        except Exception as e:
            print(f"[VoiceRouter] Error de TTS: {e}")
            # Generar silencio WAV de 0.5 s para no romper el pipeline de audio
            audio_data = self._generate_silence(duration_ms=500)

        if audio_data:
            audio_callback(audio_data)

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    def _elevenlabs_tts(self, text):
        url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
        apis = self.config.get('apis', {})
        key = apis.get('elevenlabs_key', '')
        if not key:
            raise Exception("ElevenLabs API key no configurada. Ve a Ajustes → APIS Y MODELOS CLOUD.")
        headers = {"xi-api-key": key, "Content-Type": "application/json"}
        data = {"text": text, "model_id": "eleven_monolingual_v1"}
        response = requests.post(url, json=data, headers=headers, timeout=20)
        if response.status_code == 200:
            return response.content
        raise Exception(f"ElevenLabs API falló con código {response.status_code}: {response.text[:200]}")

    def _piper_tts(self, text):
        """Requiere 'piper' instalado en el sistema."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = tmp.name
        try:
            subprocess.run(
                ['piper', '--model', 'es_ES-sharvard-medium', '--output_file', tmp_path],
                input=text.encode('utf-8'),
                check=True,
                timeout=30
            )
            with open(tmp_path, 'rb') as f:
                return f.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _normalize_for_chattts(self, text, max_chars=220):
        """Preprocesa el texto para que ChatTTS lo acepte sin errores.
        - Elimina tildes y convierte caracteres especiales del español a ASCII
        - Elimina o sustituye caracteres que ChatTTS marca como inválidos
        - Trunca a max_chars para evitar inferencias interminables en CPU
        """
        # Normalizar unicode: descomponer tildes (NFD) y descartar marcas diacríticas
        nfkd = unicodedata.normalize('NFKD', text)
        ascii_text = ''.join(c for c in nfkd if not unicodedata.category(c).startswith('M'))

        # Sustituciones manuales para retener legibilidad
        replacements = {
            '¿': '', '¡': '',          # signos de apertura españoles
            ':': ',',  ';': ',',       # dos puntos → coma (pausa natural)
            '_': ' ',  '`': '',        # subrayado y backtick
            '"': '',   "'": '',        # comillas
            '(': ',',  ')': ',',
            '[': '',   ']': '',
            '{': '',   '}': '',
            '\n': ' ', '\r': ' ',
            '\t': ' ',
        }
        for src, dst in replacements.items():
            ascii_text = ascii_text.replace(src, dst)

        # Colapsar espacios múltiples
        ascii_text = re.sub(r' {2,}', ' ', ascii_text).strip()

        # Truncar en frontera de palabra para no cortar a mitad de oración
        if len(ascii_text) > max_chars:
            truncated = ascii_text[:max_chars]
            last_space = truncated.rfind(' ')
            ascii_text = truncated[:last_space] if last_space > 0 else truncated
            ascii_text += '...'

        return ascii_text

    def _chattts_tts(self, text):
        """Genera audio utilizando ChatTTS local en CPU.
        Usa la API actualizada: chat.load() en lugar del antiguo chat.load_models()"""
        try:
            import ChatTTS
            import numpy as np
        except ImportError as e:
            raise Exception(
                f"ChatTTS no está instalado ({e}). "
                "Instálalo con: pip install ChatTTS torch torchaudio"
            )

        if self.chattts_engine is None:
            print("[VoiceRouter] Inicializando ChatTTS por primera vez...")
            self.chattts_engine = ChatTTS.Chat()
            print("[VoiceRouter] Cargando pesos del modelo ChatTTS en CPU "
                  "(esto puede tardar la primera vez)...")
            success = self.chattts_engine.load(
                source='huggingface',
                compile=False
            )
            if not success:
                self.chattts_engine = None
                raise Exception("ChatTTS no pudo cargar los modelos. "
                                "Comprueba tu conexión o los pesos descargados.")
            print("[VoiceRouter] Modelos de ChatTTS cargados correctamente.")

        # Normalizar texto: eliminar acentos y caracteres problemáticos,
        # y limitar longitud para que la inferencia en CPU sea ágil
        clean_text = self._normalize_for_chattts(text)
        print(f"[ChatTTS] Texto normalizado ({len(clean_text)} chars): {clean_text[:60]}...")

        # Inferencia — ChatTTS espera una lista de strings
        wavs = self.chattts_engine.infer([clean_text], use_decoder=True)

        import numpy as np
        audio_data = wavs[0]
        if audio_data is None or len(audio_data) == 0:
            raise Exception("ChatTTS devolvió un array de audio vacío.")

        # Aplanar en caso de ser 2D (por ejemplo, (1, N))
        if audio_data.ndim > 1:
            audio_data = audio_data.flatten()

        # Convertir a PCM int16
        audio_int16 = (audio_data * 32767).clip(-32768, 32767).astype('int16')

        # Empaquetar como WAV en memoria (ChatTTS opera a 24 000 Hz)
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(audio_int16.tobytes())

        return buffer.getvalue()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _generate_silence(self, duration_ms=500, sample_rate=24000):
        """Genera un WAV de silencio para que el pipeline de audio no se rompa."""
        import struct
        n_samples = int(sample_rate * duration_ms / 1000)
        silent_pcm = b'\x00\x00' * n_samples  # int16 zeros
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(silent_pcm)
        return buffer.getvalue()
