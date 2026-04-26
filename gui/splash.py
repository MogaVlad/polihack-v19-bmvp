from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QRect, pyqtSignal, QVariantAnimation

class SplashOverlay(QWidget):
    finished = pyqtSignal()

    def __init__(self, parent, target_widget):
        super().__init__(parent)
        self.target_widget = target_widget
        self.setObjectName("SplashOverlay")
        self.setProperty("class", "SplashOverlay")
        
        # Hide original target to avoid overlapping duplicate names, but preserve its layout footprint
        self.target_effect = QGraphicsOpacityEffect()
        self.target_effect.setOpacity(0.0)
        self.target_widget.setGraphicsEffect(self.target_effect)
        
        # Background widget (to fade independently of the title)
        self.bg_widget = QWidget(self)
        self.bg_widget.setProperty("class", "SplashBg")
        
        # Opacity effect for the background
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(1.0)
        self.bg_widget.setGraphicsEffect(self.opacity_effect)
        
        bg_layout = QVBoxLayout(self.bg_widget)
        bg_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Spacer for where the title visually sits
        self.spacer = QLabel("")
        self.spacer.setFixedHeight(120)
        bg_layout.addWidget(self.spacer)
        
        self.proceed_btn = QPushButton("Proceed to AgentArchitect")
        self.proceed_btn.setProperty("class", "SplashProceedBtn")
        self.proceed_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.proceed_btn.clicked.connect(self._start_transition)
        bg_layout.addWidget(self.proceed_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        
        # Floating title label
        self.title_lbl = QLabel("AgentArchitect", self)
        self.title_lbl.setProperty("class", "SplashTitle")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._animating = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.bg_widget.resize(self.size())
        
        # Center the floating title if it hasn't animated yet
        if not self._animating:
            lbl_width = 800
            lbl_height = 100
            x = (self.width() - lbl_width) // 2
            y = (self.height() - lbl_height) // 2 - 80
            self.title_lbl.setGeometry(x, y, lbl_width, lbl_height)

    def _start_transition(self):
        self._animating = True
        self.proceed_btn.setEnabled(False)
        
        # Instantly hide the button so the transition looks cleaner
        self.proceed_btn.hide()
        
        self.anim_group = QParallelAnimationGroup(self)
        
        # 1. Fade out background
        fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_anim.setDuration(900)
        fade_anim.setStartValue(1.0)
        fade_anim.setEndValue(0.0)
        fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim_group.addAnimation(fade_anim)
        
        # 2. Move title
        target_global = self.target_widget.parentWidget().mapToGlobal(self.target_widget.geometry().topLeft())
        target_local = self.mapFromGlobal(target_global)
        
        # Ensure we match the target width and height to complete the illusion
        target_rect = QRect(target_local, self.target_widget.size())
        
        move_anim = QPropertyAnimation(self.title_lbl, b"geometry")
        move_anim.setDuration(900)
        move_anim.setStartValue(self.title_lbl.geometry())
        move_anim.setEndValue(target_rect)
        move_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.anim_group.addAnimation(move_anim)
        
        # 3. Shrink font size
        font_anim = QVariantAnimation(self)
        font_anim.setDuration(900)
        font_anim.setStartValue(48.0)
        font_anim.setEndValue(16.0) # size of class="Title" in theme
        font_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        def update_font(val):
            font = self.title_lbl.font()
            font.setPixelSize(int(val))
            # Also keep it bold to match target
            font.setBold(True)
            self.title_lbl.setFont(font)
            
        font_anim.valueChanged.connect(update_font)
        self.anim_group.addAnimation(font_anim)
        
        self.anim_group.finished.connect(self._on_finished)
        self.anim_group.start()
        
    def _on_finished(self):
        # Reveal the original target title underneath exactly where the animated title landed
        self.target_effect.setOpacity(1.0)
        self.target_widget.setGraphicsEffect(None)
        self.finished.emit()
        self.deleteLater()
