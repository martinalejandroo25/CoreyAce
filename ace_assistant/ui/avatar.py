from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QRadialGradient, QLinearGradient, QPainterPath, QPolygonF
import math
import random

class AceAvatar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 300)
        
        # Estado de Animación
        self.mouth_open = 0.0  # 0.0 a 1.0 (Lip-sync)
        self.blink_state = 0.0 # 0.0 (abierto) a 1.0 (cerrado)
        self.emotion = "neutral" # neutral, happy, sad, thinking
        self.eye_offset_x = 0.0
        self.eye_offset_y = 0.0
        
        # Parámetros para efectos analógicos CRT y Vectores
        self.time_counter = 0.0
        self.jitter_amount = 0.7  # Ruido analógico analógico (jitter)
        self.flicker_brightness = 255  # Variación rápida del brillo del fósforo
        self.tilt_angle = -7.0  # Ladeo base
        self.face_scale = 1.0
        
        # Temporizador rápido para refresco y animación analógica (60 FPS aprox)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animations)
        self.anim_timer.start(16) # ~60 FPS
        
        # Temporizador para parpadeos aleatorios y cambios de mirada
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self._handle_blink)
        self.blink_timer.start(4000)
        
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self._handle_idle_eyes)
        self.idle_timer.start(3000)

    def _update_animations(self):
        self.time_counter += 0.04
        
        # 1. Efecto de flotación / respiración (inclinación base tierna de -7 grados con leve balanceo)
        self.tilt_angle = -7.0 + math.sin(self.time_counter * 0.4) * 2.0
        self.face_scale = 1.0 + math.sin(self.time_counter * 0.7) * 0.012
        
        # 2. Flicker de fósforo (parpadeo de alta frecuencia de la pantalla CRT)
        self.flicker_brightness = random.randint(235, 255)
        
        self.update()

    def update_lip_sync(self, amplitude):
        """Actualiza la apertura de la boca basado en la amplitud del audio (0.0 - 1.0)"""
        self.mouth_open = min(1.0, amplitude)
        self.update()

    def set_emotion(self, emotion):
        self.emotion = emotion
        self.update()

    def _handle_blink(self):
        self.blink_state = 1.0
        self.update()
        # Duración rápida del parpadeo (100ms)
        QTimer.singleShot(100, lambda: setattr(self, 'blink_state', 0.0) or self.update())

    def _handle_idle_eyes(self):
        # Desviación analógica sutil de mirada
        self.eye_offset_x = random.uniform(-2.0, 2.0)
        self.eye_offset_y = random.uniform(-1.0, 1.0)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Fondo CRT profundo (Tubo negro con viñeta y fósforo residual)
        self._draw_crt_background(painter)
        
        # Guardar estado del pintor para aplicar transformaciones de la cara (flotación/respiración)
        painter.save()
        
        # Desplazar al centro para realizar rotación y escala relativas
        center_x, center_y = self.width() / 2, self.height() / 2
        # Desplazamos la cara ligeramente más arriba para compactar el encuadre general
        painter.translate(center_x, center_y - 12)
        painter.rotate(self.tilt_angle)
        painter.scale(self.face_scale, self.face_scale)
        
        # Dibujar elementos del rostro en coordenadas locales (relativas al centro 0,0)
        self._draw_face_elements(painter)
        
        # Restaurar estado original del pintor
        painter.restore()
        
        # 2. Efectos estáticos de la pantalla CRT (Scanlines, Rejilla, Halación y Glare)
        self._draw_crt_screen_overlays(painter)

    def _draw_crt_background(self, painter):
        gradient = QRadialGradient(200, 150, 250)
        gradient.setColorAt(0, QColor(6, 12, 22))   # Azul oscuro profundo
        gradient.setColorAt(0.7, QColor(2, 4, 8))    # Más oscuro hacia los bordes
        gradient.setColorAt(1.0, QColor(0, 0, 0))    # Negro absoluto
        painter.fillRect(self.rect(), gradient)

    def _apply_jitter(self, points):
        """Aplica una pequeña distorsión aleatoria a cada punto para emular el ruido de un oscilador analógico"""
        jittered = []
        for pt in points:
            jx = pt.x() + random.uniform(-self.jitter_amount, self.jitter_amount)
            jy = pt.y() + random.uniform(-self.jitter_amount, self.jitter_amount)
            jittered.append(QPointF(jx, jy))
        return jittered

    def _draw_neon_path(self, painter, path):
        """Dibuja un path con múltiples pasadas de color y grosores para emular el resplandor de fósforo difuminado (Bloom)"""
        base_color = QColor(0, 195, 255)
        
        # Pasada 1: Bloom extremadamente amplio y difuso (dispersión de luz en el vidrio)
        pen_bloom_ext = QPen(QColor(base_color.red(), base_color.green(), base_color.blue(), int(self.flicker_brightness * 0.08)), 42)
        pen_bloom_ext.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen_bloom_ext.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen_bloom_ext)
        painter.drawPath(path)
        
        # Pasada 2: Glow medio-ancho (fósforo difuso)
        pen_glow_wide = QPen(QColor(base_color.red(), base_color.green(), base_color.blue(), int(self.flicker_brightness * 0.18)), 22)
        pen_glow_wide.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen_glow_wide.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen_glow_wide)
        painter.drawPath(path)
        
        # Pasada 3: Foco del haz de electrones
        pen_glow_mid = QPen(QColor(base_color.red(), base_color.green(), base_color.blue(), int(self.flicker_brightness * 0.40)), 10)
        pen_glow_mid.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen_glow_mid.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen_glow_mid)
        painter.drawPath(path)
        
        # Pasada 4: Núcleo incandescente del vector (Cian claro/blanco)
        pen_core = QPen(QColor(215, 245, 255, int(self.flicker_brightness * 0.90)), 2.2)
        pen_core.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen_core.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen_core)
        painter.drawPath(path)

    def _draw_face_elements(self, painter):
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # ----------------------------------------------------
        # 1. OJO IZQUIERDO (Ubicación central bajada de -15 a -6 para acercar a la boca)
        # ----------------------------------------------------
        eye_l_center_x = -58 + self.eye_offset_x
        eye_l_center_y = -6 + self.eye_offset_y
        
        if self.blink_state > 0.5:
            # Ojo cerrado: Una simple línea vectorial horizontal
            pts_blink_l = [
                QPointF(eye_l_center_x - 22, eye_l_center_y),
                QPointF(eye_l_center_x + 18, eye_l_center_y)
            ]
            path = QPainterPath()
            jittered_pts = self._apply_jitter(pts_blink_l)
            path.moveTo(jittered_pts[0])
            path.lineTo(jittered_pts[1])
            self._draw_neon_path(painter, path)
        else:
            # Ojo abierto: Trapezoide exterior con inclinación superior / y más compacto verticalmente (alto 28px)
            pts_eye_l = [
                QPointF(eye_l_center_x - 22, eye_l_center_y - 20), # Superior Izquierdo
                QPointF(eye_l_center_x + 20, eye_l_center_y - 32), # Superior Derecho (más arriba en Y para hacer /)
                QPointF(eye_l_center_x + 14, eye_l_center_y + 18), # Inferior Derecho
                QPointF(eye_l_center_x - 16, eye_l_center_y + 24), # Inferior Izquierdo
            ]
            path_eye_l = QPainterPath()
            j_pts = self._apply_jitter(pts_eye_l)
            path_eye_l.moveTo(j_pts[0])
            path_eye_l.lineTo(j_pts[1])
            path_eye_l.lineTo(j_pts[2])
            path_eye_l.lineTo(j_pts[3])
            path_eye_l.closeSubpath()
            self._draw_neon_path(painter, path_eye_l)

        # ----------------------------------------------------
        # 2. OJO DERECHO (Ubicación central bajada de -12 a -3 para acercar a la boca)
        # ----------------------------------------------------
        eye_r_center_x = 58 + self.eye_offset_x
        eye_r_center_y = -3 + self.eye_offset_y
        
        if self.blink_state > 0.5:
            # Ojo cerrado
            pts_blink_r = [
                QPointF(eye_r_center_x - 18, eye_r_center_y),
                QPointF(eye_r_center_x + 22, eye_r_center_y)
            ]
            path = QPainterPath()
            jittered_pts = self._apply_jitter(pts_blink_r)
            path.moveTo(jittered_pts[0])
            path.lineTo(jittered_pts[1])
            self._draw_neon_path(painter, path)
        else:
            # Ojo abierto: Trapezoide exterior con inclinación superior / y más compacto
            pts_eye_r = [
                QPointF(eye_r_center_x - 20, eye_r_center_y - 20), # Superior Izquierdo
                QPointF(eye_r_center_x + 22, eye_r_center_y - 32), # Superior Derecho (más arriba en Y para hacer /)
                QPointF(eye_r_center_x + 16, eye_r_center_y + 18), # Inferior Derecho
                QPointF(eye_r_center_x - 14, eye_r_center_y + 24), # Inferior Izquierdo
            ]
            path_eye_r = QPainterPath()
            j_pts = self._apply_jitter(pts_eye_r)
            path_eye_r.moveTo(j_pts[0])
            path_eye_r.lineTo(j_pts[1])
            path_eye_r.lineTo(j_pts[2])
            path_eye_r.lineTo(j_pts[3])
            path_eye_r.closeSubpath()
            self._draw_neon_path(painter, path_eye_r)

        # ----------------------------------------------------
        # 3. CEJAS (Expresión Empática: /  \, reubicadas sobre los nuevos ojos)
        # ----------------------------------------------------
        offset_sad = 6 if self.emotion == "sad" else 0
        offset_happy = -4 if self.emotion == "happy" else 0

        # Ceja Izquierda
        pts_brow_l = [
            QPointF(-82, -48 + offset_happy),       # Extremo Exterior
            QPointF(-32, -62 - offset_sad + offset_happy) # Extremo Interior (más arriba en Y)
        ]
        path_brow_l = QPainterPath()
        jb_l = self._apply_jitter(pts_brow_l)
        path_brow_l.moveTo(jb_l[0])
        path_brow_l.lineTo(jb_l[1])
        self._draw_neon_path(painter, path_brow_l)

        # Ceja Derecha
        pts_brow_r = [
            QPointF(32, -62 - offset_sad + offset_happy), # Extremo Interior (más arriba en Y)
            QPointF(82, -48 + offset_happy)        # Extremo Exterior
        ]
        path_brow_r = QPainterPath()
        jb_r = self._apply_jitter(pts_brow_r)
        path_brow_r.moveTo(jb_r[0])
        path_brow_r.lineTo(jb_r[1])
        self._draw_neon_path(painter, path_brow_r)

        # ----------------------------------------------------
        # 4. BOCA (Subida de Y = 46 a Y = 30 para acercarla estrechamente a los ojos)
        # ----------------------------------------------------
        path_mouth = QPainterPath()
        has_mouth_to_draw = False
        
        if self.emotion == "happy":
            # Sonrisa tierna de vector (Y = 32)
            pts_mouth = [
                QPointF(-20, 25),
                QPointF(-8, 40),
                QPointF(8, 40),
                QPointF(20, 31)
            ]
            jm = self._apply_jitter(pts_mouth)
            path_mouth.moveTo(jm[0])
            path_mouth.lineTo(jm[1])
            path_mouth.lineTo(jm[2])
            path_mouth.lineTo(jm[3])
            has_mouth_to_draw = True
            
        elif self.mouth_open > 0.1:
            # Hablando: Se abre como un trapezoide compacto y pegado a los ojos (Y = 28)
            depth = 28 + (14 * self.mouth_open)
            pts_mouth = [
                QPointF(-18, 28),
                QPointF(-10, depth),
                QPointF(10, depth),
                QPointF(18, 27)
            ]
            jm = self._apply_jitter(pts_mouth)
            path_mouth.moveTo(jm[0])
            path_mouth.lineTo(jm[1])
            path_mouth.lineTo(jm[2])
            path_mouth.lineTo(jm[3])
            path_mouth.closeSubpath()
            has_mouth_to_draw = True
            
        if has_mouth_to_draw:
            self._draw_neon_path(painter, path_mouth)

        # ----------------------------------------------------
        # 5. MARCO DE SOPORTE / FLECHAS (Decorativo inferior)
        # ----------------------------------------------------
        path_frame = QPainterPath()
        base_y = 108
        
        # Línea base inferior
        pts_base = [
            QPointF(-135, base_y),
            QPointF(135, base_y - 4)
        ]
        jb = self._apply_jitter(pts_base)
        path_frame.moveTo(jb[0])
        path_frame.lineTo(jb[1])
        
        # Flecha izquierda
        pts_arrow_l = [
            QPointF(-135, base_y),
            QPointF(-148, base_y - 25),
            QPointF(-146, base_y - 25),
            QPointF(-153, base_y - 22),
            QPointF(-148, base_y - 36),
            QPointF(-141, base_y - 23),
            QPointF(-146, base_y - 25)
        ]
        jal = self._apply_jitter(pts_arrow_l)
        path_frame.moveTo(jal[0])
        path_frame.lineTo(jal[1])
        path_frame.moveTo(jal[2])
        path_frame.lineTo(jal[3])
        path_frame.lineTo(jal[4])
        path_frame.lineTo(jal[5])
        path_frame.lineTo(jal[6])

        # Flecha derecha
        pts_arrow_r = [
            QPointF(135, base_y - 4),
            QPointF(148, base_y - 29),
            QPointF(146, base_y - 29),
            QPointF(140, base_y - 27),
            QPointF(148, base_y - 40),
            QPointF(154, base_y - 26),
            QPointF(146, base_y - 29)
        ]
        jar = self._apply_jitter(pts_arrow_r)
        path_frame.moveTo(jar[0])
        path_frame.lineTo(jar[1])
        path_frame.moveTo(jar[2])
        path_frame.lineTo(jar[3])
        path_frame.lineTo(jar[4])
        path_frame.lineTo(jar[5])
        path_frame.lineTo(jar[6])
        
        self._draw_neon_path(painter, path_frame)

    def _draw_crt_screen_overlays(self, painter):
        # 1. Halo de brillo de fósforo difuso ambiental central (Halation Glow retro)
        halation = QRadialGradient(200, 135, 180)
        halation.setColorAt(0, QColor(0, 195, 255, 24))  # Aura cian difusa en el centro
        halation.setColorAt(0.6, QColor(0, 195, 255, 6))
        halation.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(halation)
        painter.drawRect(self.rect())
        
        # 2. Líneas de escaneo oscuras horizontales (Scanlines)
        scanline_pen = QPen(QColor(0, 0, 0, 32), 1)
        painter.setPen(scanline_pen)
        for y in range(0, self.height(), 3):
            painter.drawLine(0, y, self.width(), y)
            
        # 3. Rejilla de fósforo vertical
        grille_pen = QPen(QColor(0, 0, 0, 14), 1)
        painter.setPen(grille_pen)
        for x in range(0, self.width(), 4):
            painter.drawLine(x, 0, x, self.height())
            
        # 4. Reflejo del cristal curvado
        glare_gradient = QLinearGradient(0, 0, 180, 180)
        glare_gradient.setColorAt(0, QColor(255, 255, 255, 16))
        glare_gradient.setColorAt(0.3, QColor(255, 255, 255, 6))
        glare_gradient.setColorAt(0.8, QColor(0, 0, 0, 0))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glare_gradient)
        painter.drawRect(self.rect())
        
        # 5. Sombreado de borde de pantalla (Viñeta exterior)
        vignette = QRadialGradient(200, 150, 240)
        vignette.setColorAt(0, QColor(0, 0, 0, 0))
        vignette.setColorAt(0.85, QColor(0, 0, 0, 45))
        vignette.setColorAt(1.0, QColor(0, 0, 0, 225))
        painter.setBrush(vignette)
        painter.drawRect(self.rect())
