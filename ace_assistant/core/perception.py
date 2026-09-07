try:
    import cv2
    from deepface import DeepFace
    HAS_PERCEPTION = True
except ImportError:
    HAS_PERCEPTION = False

from PyQt6.QtCore import QThread, pyqtSignal

class PerceptionThread(QThread):
    emotion_detected = pyqtSignal(str) # Emite: 'happy', 'sad', 'neutral', etc.
    frame_captured = pyqtSignal(object) # Para enviar el frame al LLM de visión si es online

    def __init__(self):
        super().__init__()
        self.running = False

    def run(self):
        if not HAS_PERCEPTION:
            print("Módulo de percepción no disponible (deepface/opencv no instalados).")
            return
        
        self.running = True
        cap = cv2.VideoCapture(0)
        while self.running and not self.isInterruptionRequested():
            ret, frame = cap.read()
            if not ret: continue
            
            try:
                # Analizar emoción (cada X frames para no saturar CPU)
                result = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
                dominant_emotion = result[0]['dominant_emotion']
                self.emotion_detected.emit(dominant_emotion)
            except Exception as e:
                pass # A veces falla si no hay cara clara
            
            self.msleep(1000) # Analizar cada segundo
        cap.release()

    def stop(self):
        self.running = False

