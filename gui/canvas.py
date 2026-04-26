import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsPolygonItem,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem, QSizePolicy,
    QGraphicsItem
)
from PyQt6.QtCore import Qt, QPointF, QTimer, QRectF, QSize, pyqtProperty, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPolygonF, QPen, QBrush, QColor, QFont, QPainterPath, QPainter, QPalette, QFontMetricsF

import re
from typing import Optional, List, Dict, Tuple
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


_SEV_ORDER: Dict[str, int] = {"critical": 3, "major": 2, "minor": 1, "info": 0}

_SEV_MARKER_COLORS: Dict[str, str] = {
    "critical": "#e05555",
    "major": "#d4943a",
    "minor": "#c0a040",
    "info": "#8b81a2",
}

_ROOM_TINTS_DARK: Dict[str, str] = {
    "critical": "#2a1818",
    "major": "#2a2218",
}

_ROOM_TINTS_LIGHT: Dict[str, str] = {
    "critical": "#fff0f0",
    "major": "#fff5e6",
}

_LOCATION_ID_RE = re.compile(r'\b([RCDE]\d+)\b')


class CanvasPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CanvasPanel")

        self.floor_plan: Optional[FloorPlan] = None
        self.violations: List[Violation] = []
        self.visible = False
        self._plan_rect: Optional[QRectF] = None
        self._dark_mode = True
        self._theme_colors = {}

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
        self.apply_theme(True)

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

    def apply_theme(self, dark_mode: bool):
        self._dark_mode = dark_mode
        if dark_mode:
            self._theme_colors = {
                "view_bg": "#0f1315",
                "room_fill": "#181c1f",
                "room_border": "#b3c0c7",
                "corridor_border": "#4f4c67",
                "exit_fill": "#8b81a2",
                "door_color": "#b3c0c7",
                "label_color": "#b3c0c7",
            }
        else:
            self._theme_colors = {
                "view_bg": "#f5f7f9",
                "room_fill": "#ffffff",
                "room_border": "#3b4a52",
                "corridor_border": "#8893a4",
                "exit_fill": "#5f7390",
                "door_color": "#3b4a52",
                "label_color": "#3b4a52",
            }
        self.view.setStyleSheet(f"background-color: {self._theme_colors['view_bg']}; border: none;")
        if self.visible:
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

    @staticmethod
    def _poly_centroid(polygon) -> Tuple[float, float]:
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def _violation_location_ids(self, location: str) -> List[str]:
        plan = self.floor_plan
        if not plan:
            return []
        if plan.get_room(location):
            return [location]
        if plan.get_corridor(location):
            return [location]

        result = []
        ids = _LOCATION_ID_RE.findall(location)
        for id_ in ids:
            if plan.get_room(id_) or plan.get_corridor(id_):
                result.append(id_)

        if not result:
            for door in plan.doors:
                if door.id in ids or location.startswith(door.id):
                    result.extend(c for c in door.connects
                                  if plan.get_room(c) or plan.get_corridor(c))
                    break

        if not result:
            for exit_ in plan.exits:
                if exit_.id in ids:
                    rid = exit_.room_id
                    if rid and (plan.get_room(rid) or plan.get_corridor(rid)):
                        result.append(rid)
                    break

        return result

    def _resolve_violation_pos(self, location: str) -> Optional[Tuple[float, float]]:
        plan = self.floor_plan
        if not plan:
            return None

        target = plan.get_room(location) or plan.get_corridor(location)
        if target and target.polygon:
            return self._poly_centroid(target.polygon)

        if location == "building":
            all_pts = [p for r in plan.rooms if r.polygon for p in r.polygon]
            if all_pts:
                return (sum(p[0] for p in all_pts) / len(all_pts),
                        sum(p[1] for p in all_pts) / len(all_pts))
            return None

        ids = _LOCATION_ID_RE.findall(location)
        for id_ in ids:
            room = plan.get_room(id_)
            if room and room.polygon:
                return self._poly_centroid(room.polygon)
            corr = plan.get_corridor(id_)
            if corr and corr.polygon:
                return self._poly_centroid(corr.polygon)
            for door in plan.doors:
                if door.id == id_:
                    return (door.position[0], door.position[1])
            for exit_ in plan.exits:
                if exit_.id == id_:
                    return (exit_.position[0], exit_.position[1])

        return None

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

        room_fill_base = QColor(self._theme_colors.get("room_fill", "#181c1f"))
        room_border_base = QColor(self._theme_colors.get("room_border", "#b3c0c7"))
        corridor_border = QColor(self._theme_colors.get("corridor_border", "#4f4c67"))
        exit_fill = QColor(self._theme_colors.get("exit_fill", "#8b81a2"))
        door_color = QColor(self._theme_colors.get("door_color", "#b3c0c7"))
        label_color = QColor(self._theme_colors.get("label_color", "#b3c0c7"))
        label_font = QFont("Segoe UI", 8)

        room_worst: Dict[str, str] = {}
        if self.show_violations_var and self.violations:
            for v in self.violations:
                sev = (v.severity or "").lower()
                sev_rank = _SEV_ORDER.get(sev, -1)
                for lid in self._violation_location_ids(v.location):
                    if sev_rank > _SEV_ORDER.get(room_worst.get(lid, ""), -1):
                        room_worst[lid] = sev

        tint_map = _ROOM_TINTS_DARK if self._dark_mode else _ROOM_TINTS_LIGHT

        for room in plan.rooms:
            if not room.polygon:
                continue
            poly = QPolygonF([QPointF(p[0], p[1]) for p in room.polygon])

            fill = QColor(room_fill_base)
            border = QColor(room_border_base)
            border_w = 0.2

            sev = room_worst.get(room.id)
            if sev and sev in tint_map:
                fill = QColor(tint_map[sev])
            if sev in ("critical", "major"):
                border = QColor(_SEV_MARKER_COLORS[sev])
                border_w = 0.4

            self.scene.addPolygon(poly, QPen(border, border_w), QBrush(fill))
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
            if not corridor.polygon:
                continue
            poly = QPolygonF([QPointF(p[0], p[1]) for p in corridor.polygon])

            corr_fill = QColor(room_fill_base)
            corr_border = QColor(corridor_border)
            border_w = 0.1

            sev = room_worst.get(corridor.id)
            if sev and sev in tint_map:
                corr_fill = QColor(tint_map[sev])
            if sev in ("critical", "major"):
                corr_border = QColor(_SEV_MARKER_COLORS[sev])
                border_w = 0.3

            pen = QPen(corr_border, border_w)
            pen.setStyle(Qt.PenStyle.DashLine)
            self.scene.addPolygon(poly, pen, QBrush(corr_fill))
            expand_rect(poly.boundingRect())

        wall_color = QColor(room_border_base)
        wall_color.setAlpha(180)
        for wall in plan.walls:
            sx, sy = wall.start[0], wall.start[1]
            ex_w, ey_w = wall.end[0], wall.end[1]
            self.scene.addLine(sx, sy, ex_w, ey_w, QPen(wall_color, 0.3))
            expand_rect(QRectF(
                QPointF(min(sx, ex_w), min(sy, ey_w)),
                QPointF(max(sx, ex_w), max(sy, ey_w)),
            ))

        for exit_ in plan.exits:
            ex, ey = exit_.position[0], exit_.position[1]
            self.scene.addEllipse(ex - 0.8, ey - 0.8, 1.6, 1.6, QPen(room_border_base, 0.2), QBrush(exit_fill))
            expand_rect(QRectF(ex - 0.8, ey - 0.8, 1.6, 1.6))

            arrow = QPainterPath()
            arrow.moveTo(ex - 0.5, ey + 1.4)
            arrow.lineTo(ex, ey + 2.4)
            arrow.lineTo(ex + 0.5, ey + 1.4)
            self.scene.addPath(arrow, QPen(exit_fill, 0.15), QBrush(exit_fill))

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
            loc_counts: Dict[str, int] = {}
            unresolved_idx = 0

            for v in self.violations:
                pos = self._resolve_violation_pos(v.location)
                if pos:
                    wx, wy = pos
                    key = f"{wx:.0f},{wy:.0f}"
                    loc_counts[key] = loc_counts.get(key, 0) + 1
                    count = loc_counts[key] - 1
                    col = count % 4
                    row = count // 4
                    wx += (col - 1.5) * 2.8
                    wy += 3.0 + row * 2.8
                else:
                    if self._plan_rect:
                        wx = self._plan_rect.left() + unresolved_idx * 3.5
                        wy = self._plan_rect.bottom() + 5
                    else:
                        wx = unresolved_idx * 3.5
                        wy = 30
                    unresolved_idx += 1

                sev = (v.severity or "").lower()
                color = QColor(_SEV_MARKER_COLORS.get(sev, "#8b81a2"))

                r = 1.1
                item = QGraphicsEllipseItem(wx - r, wy - r, r * 2, r * 2)
                item.setPen(QPen(QColor("#e8ecee"), 0.15))
                item.setBrush(QBrush(color))
                item.setToolTip(
                    f"<b style='color:{_SEV_MARKER_COLORS.get(sev, '#8b81a2')}'>"
                    f"{v.severity.upper()}</b> — {v.rule}<br>{v.description}"
                )
                item.setZValue(100)
                item.setAcceptHoverEvents(True)
                self.scene.addItem(item)

        if self._plan_rect:
            self._update_scene_rect(self._plan_rect)

    def highlight_location(self, location_id: str):
        if not self.floor_plan:
            return
        if not self.visible:
            self.toggle()

        pos = self._resolve_violation_pos(location_id)
        if not pos:
            return
        cx, cy = pos

        ring = QGraphicsEllipseItem(cx - 3.0, cy - 3.0, 6.0, 6.0)
        pen = QPen(QColor("#e05555"), 0.35)
        pen.setStyle(Qt.PenStyle.DashLine)
        ring.setPen(pen)
        ring.setZValue(200)
        self.scene.addItem(ring)

        self.view.centerOn(cx, cy)

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
