import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsPolygonItem,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem, QSizePolicy,
    QGraphicsItem
)
from PyQt6.QtCore import Qt, QPointF, QTimer, QRectF, QSize, pyqtProperty, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPolygonF, QPen, QBrush, QColor, QFont, QPainterPath, QPainter, QPalette, QFontMetricsF

from typing import Optional, List
import config
from models.floor_plan import FloorPlan
from models.violations import Violation


class InteractiveGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #0f1315; border: none;")
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)


class ToggleSwitch(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(36, 18)
        self._knob_pos = 1.0 if self.isChecked() else 0.0
        self._anim = QPropertyAnimation(self, b"knobPos", self)
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._on_toggled)

    def sizeHint(self):
        return QSize(36, 18)

    def _on_toggled(self, checked: bool):
        self._anim.stop()
        self._anim.setStartValue(self._knob_pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def get_knob_pos(self) -> float:
        return self._knob_pos

    def set_knob_pos(self, value: float):
        self._knob_pos = max(0.0, min(1.0, float(value)))
        self.update()

    knobPos = pyqtProperty(float, fget=get_knob_pos, fset=set_knob_pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        radius = rect.height() / 2
        palette = self.palette()

        if self.isEnabled():
            track_color = palette.color(
                QPalette.ColorRole.Highlight if self.isChecked() else QPalette.ColorRole.Mid
            )
            knob_color = palette.color(QPalette.ColorRole.Base)
            border_color = palette.color(QPalette.ColorRole.Dark)
        else:
            track_color = palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Mid)
            knob_color = palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base)
            border_color = palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Dark)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)

        knob_size = rect.height() - 4
        knob_min = 2
        knob_max = rect.width() - knob_size - 2
        knob_x = knob_min + (knob_max - knob_min) * self._knob_pos
        knob_rect = QRectF(knob_x, 2, knob_size, knob_size)
        painter.setBrush(knob_color)
        painter.setPen(QPen(border_color, 1))
        painter.drawEllipse(knob_rect)


class CenteredTextItem(QGraphicsItem):
    def __init__(self, text: str, font: QFont, color: QColor, parent=None):
        super().__init__(parent)
        self._text = text
        self._font = font
        self._color = color
        self._rect = QRectF()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self._update_rect()

    def _update_rect(self):
        metrics = QFontMetricsF(self._font)
        lines = self._text.splitlines() or [""]
        width = max(metrics.horizontalAdvance(line) for line in lines)
        height = metrics.height() * len(lines)
        self._rect = QRectF(-width / 2, -height / 2, width, height)

    def boundingRect(self) -> QRectF:
        return self._rect

    def paint(self, painter: QPainter, option, widget=None):
        painter.setFont(self._font)
        painter.setPen(self._color)
        painter.drawText(self._rect, Qt.AlignmentFlag.AlignCenter, self._text)


class CanvasPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CanvasPanel")

        self.floor_plan: Optional[FloorPlan] = None
        self.violations: List[Violation] = []
        self.visible = False
        self._plan_rect: Optional[QRectF] = None

        self.show_labels_var = True
        self.show_occupancy_var = True
        self.show_violations_var = True

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout = main_layout

        self.toggle_frame = QFrame()
        self.toggle_frame.setFixedHeight(36)
        toggle_layout = QHBoxLayout(self.toggle_frame)
        toggle_layout.setContentsMargins(8, 4, 8, 0)
        toggle_layout.setSpacing(8)

        self.toggle_btn = QPushButton("Show Canvas")
        self.toggle_btn.clicked.connect(self.toggle)
        toggle_layout.addWidget(self.toggle_btn)

        def make_toggle(label_text: str, default_on: bool = True) -> ToggleSwitch:
            label = QLabel(label_text)
            toggle_layout.addWidget(label)
            toggle = ToggleSwitch()
            toggle.setChecked(default_on)
            toggle.toggled.connect(self._on_layer_toggle)
            toggle_layout.addWidget(toggle)
            return toggle

        self.labels_toggle = make_toggle("Labels", True)
        self.occ_toggle = make_toggle("Occupancy", True)
        self.viol_toggle = make_toggle("Violations", True)

        toggle_layout.addStretch()

        fit_btn = QPushButton("Fit")
        fit_btn.clicked.connect(self.fit_to_window)
        toggle_layout.addWidget(fit_btn)

        main_layout.addWidget(self.toggle_frame)

        self.panel_frame = QFrame()
        self.panel_frame.setProperty("class", "Card")
        panel_layout = QVBoxLayout(self.panel_frame)
        panel_layout.setContentsMargins(6, 6, 6, 6)

        self.scene = QGraphicsScene()
        self.view = InteractiveGraphicsView(self.scene)
        panel_layout.addWidget(self.view)

        main_layout.addWidget(self.panel_frame, 1)
        self.panel_frame.hide()
        self._set_collapsed(True)

    def _set_collapsed(self, collapsed: bool):
        if collapsed:
            header_height = self.toggle_frame.sizeHint().height()
            margins = self._main_layout.contentsMargins()
            total_height = header_height + margins.top() + margins.bottom()
            self.setMinimumHeight(total_height)
            self.setMaximumHeight(total_height)
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        else:
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    def _on_layer_toggle(self):
        self.show_labels_var = self.labels_toggle.isChecked()
        self.show_occupancy_var = self.occ_toggle.isChecked()
        self.show_violations_var = self.viol_toggle.isChecked()
        self._redraw()

    def toggle(self):
        if self.visible:
            self.panel_frame.hide()
            self.toggle_btn.setText("Show Canvas")
            self.visible = False
            self._set_collapsed(True)
        else:
            self.panel_frame.show()
            self.toggle_btn.setText("Hide Canvas")
            self.visible = True
            self._set_collapsed(False)
            self._redraw()

    def load_plan(self, plan: FloorPlan):
        self.floor_plan = plan
        self.violations = []
        if self.visible:
            self._redraw()

    def show_violations(self, violations: List[Violation]):
        self.violations = violations
        if self.visible:
            self._redraw()

    def fit_to_window(self):
        if not self.floor_plan:
            return
        rect = self._plan_rect or self.scene.itemsBoundingRect()
        if not rect.isNull():
            self._update_scene_rect(rect)
            self.view.resetTransform()
            rect.adjust(-10, -10, 10, 10)
            self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
            self.view.centerOn(rect.center())

    def _redraw(self):
        self.scene.clear()
        if not self.floor_plan:
            return

        plan = self.floor_plan
        self._plan_rect = None

        def expand_rect(rect: QRectF):
            if rect.isNull():
                return
            if self._plan_rect is None:
                self._plan_rect = QRectF(rect)
            else:
                self._plan_rect = self._plan_rect.united(rect)

        room_fill = QColor("#181c1f")
        room_border = QColor("#b3c0c7")
        corridor_border = QColor("#4f4c67")
        exit_fill = QColor("#8b81a2")
        door_color = QColor("#b3c0c7")
        label_color = QColor("#b3c0c7")
        label_font = QFont("Segoe UI", 8)

        for room in plan.rooms:
            if room.polygon:
                poly = QPolygonF([QPointF(p[0], p[1]) for p in room.polygon])
                self.scene.addPolygon(poly, QPen(room_border, 0.2), QBrush(room_fill))
                expand_rect(poly.boundingRect())

                if self.show_labels_var or self.show_occupancy_var:
                    cx = sum(p[0] for p in room.polygon) / len(room.polygon)
                    cy = sum(p[1] for p in room.polygon) / len(room.polygon)

                    parts = []
                    if self.show_labels_var:
                        parts.append(room.name)
                    if self.show_occupancy_var and room.occupancy > 0:
                        parts.append(f"Occ: {room.occupancy}")

                    if parts:
                        text_item = CenteredTextItem("\n".join(parts), label_font, label_color)
                        text_item.setPos(cx, cy)
                        self.scene.addItem(text_item)

        for corridor in plan.corridors:
            if corridor.polygon:
                poly = QPolygonF([QPointF(p[0], p[1]) for p in corridor.polygon])
                pen = QPen(corridor_border, 0.1)
                pen.setStyle(Qt.PenStyle.DashLine)
                self.scene.addPolygon(poly, pen, QBrush(room_fill))
                expand_rect(poly.boundingRect())

        for exit_ in plan.exits:
            ex, ey = exit_.position[0], exit_.position[1]
            self.scene.addEllipse(ex - 0.8, ey - 0.8, 1.6, 1.6, QPen(room_border, 0.2), QBrush(exit_fill))
            expand_rect(QRectF(ex - 0.8, ey - 0.8, 1.6, 1.6))

            if self.show_labels_var:
                exit_font = QFont(label_font)
                exit_font.setBold(True)
                text_item = CenteredTextItem("EXIT", exit_font, exit_fill)
                text_item.setPos(ex, ey - 2)
                self.scene.addItem(text_item)

        for door in plan.doors:
            dx, dy = door.position[0], door.position[1]
            r = 0.6
            self.scene.addLine(dx - r / 2, dy, dx + r / 2, dy, QPen(door_color, 0.2))

            path = QPainterPath()
            path.arcMoveTo(QRectF(dx - r, dy - r, r * 2, r * 2), 0)
            path.arcTo(QRectF(dx - r, dy - r, r * 2, r * 2), 0, 90)
            self.scene.addPath(path, QPen(door_color, 0.2))
            expand_rect(QRectF(dx - r, dy - r, r * 2, r * 2))

        if self.show_violations_var and self.violations:
            for idx, v in enumerate(self.violations):
                target = plan.get_room(v.location) or plan.get_corridor(v.location)

                if target and target.polygon:
                    wx = sum(p[0] for p in target.polygon) / len(target.polygon)
                    wy = sum(p[1] for p in target.polygon) / len(target.polygon)
                else:
                    wx = idx * 2
                    wy = 0

                if v.severity == "critical":
                    color = QColor("#e05555")
                elif v.severity == "major":
                    color = QColor("#c4883a")
                else:
                    color = QColor("#8b81a2")

                item = QGraphicsEllipseItem(wx - 0.9, wy - 0.9, 1.8, 1.8)
                item.setPen(QPen(QColor("#e8ecee"), 0.2))
                item.setBrush(QBrush(color))
                item.setToolTip(f"<b>{v.rule} | {v.severity.upper()}</b><br>{v.description}")
                self.scene.addItem(item)

        if self._plan_rect:
            self._update_scene_rect(self._plan_rect)

    def highlight_location(self, location_id: str):
        if not self.floor_plan:
            return
        if not self.visible:
            self.toggle()

        target = self.floor_plan.get_room(location_id) or self.floor_plan.get_corridor(location_id)
        if not target or not target.polygon:
            return

        cx = sum(p[0] for p in target.polygon) / len(target.polygon)
        cy = sum(p[1] for p in target.polygon) / len(target.polygon)

        ring = QGraphicsEllipseItem(cx - 2.2, cy - 2.2, 4.4, 4.4)
        pen = QPen(QColor("#e05555"), 0.3)
        pen.setStyle(Qt.PenStyle.DashLine)
        ring.setPen(pen)
        self.scene.addItem(ring)

        self._flash_count = 0

        def flash():
            if self._flash_count >= 8:
                self.scene.removeItem(ring)
                return
            ring.setVisible(self._flash_count % 2 == 0)
            self._flash_count += 1
            QTimer.singleShot(300, flash)

        flash()

    def clear(self):
        self.scene.clear()
        self.floor_plan = None
        self.violations = []
        self._plan_rect = None

    def _update_scene_rect(self, rect: QRectF):
        padded = QRectF(rect)
        pad = max(40.0, max(padded.width(), padded.height()) * 0.75)
        padded.adjust(-pad, -pad, pad, pad)
        self.scene.setSceneRect(padded)
