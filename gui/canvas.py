import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QCheckBox, QGraphicsView, QGraphicsScene, QGraphicsPolygonItem,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsLineItem
)
from PyQt6.QtCore import Qt, QPointF, QTimer, QRectF
from PyQt6.QtGui import QPolygonF, QPen, QBrush, QColor, QFont, QPainterPath

from typing import Optional, List
import config
from models.floor_plan import FloorPlan
from models.violations import Violation


class InteractiveGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        from PyQt6.QtGui import QPainter
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("background-color: #070909; border: none;")

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
            
        self.scale(zoom_factor, zoom_factor)


class CanvasPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CanvasPanel")
        
        self.floor_plan: Optional[FloorPlan] = None
        self.violations: List[Violation] = []
        self.visible = False
        
        self.show_labels_var = True
        self.show_occupancy_var = True
        self.show_violations_var = True
        
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # ── Toggle / controls bar ───────────────────────────────
        self.toggle_frame = QFrame()
        self.toggle_frame.setFixedHeight(36)
        toggle_layout = QHBoxLayout(self.toggle_frame)
        toggle_layout.setContentsMargins(8, 4, 8, 0)
        
        self.toggle_btn = QPushButton("▼ Show Canvas")
        self.toggle_btn.clicked.connect(self.toggle)
        toggle_layout.addWidget(self.toggle_btn)
        
        self.labels_cb = QCheckBox("Labels")
        self.labels_cb.setChecked(True)
        self.labels_cb.stateChanged.connect(self._on_layer_toggle)
        toggle_layout.addWidget(self.labels_cb)
        
        self.occ_cb = QCheckBox("Occupancy")
        self.occ_cb.setChecked(True)
        self.occ_cb.stateChanged.connect(self._on_layer_toggle)
        toggle_layout.addWidget(self.occ_cb)
        
        self.viol_cb = QCheckBox("Violations")
        self.viol_cb.setChecked(True)
        self.viol_cb.stateChanged.connect(self._on_layer_toggle)
        toggle_layout.addWidget(self.viol_cb)
        
        toggle_layout.addStretch()
        
        fit_btn = QPushButton("Fit")
        fit_btn.clicked.connect(self.fit_to_window)
        toggle_layout.addWidget(fit_btn)
        
        main_layout.addWidget(self.toggle_frame)
        
        # ── Canvas panel (hidden initially) ─────────────────────
        self.panel_frame = QFrame()
        self.panel_frame.setProperty("class", "Card")
        panel_layout = QVBoxLayout(self.panel_frame)
        panel_layout.setContentsMargins(6, 6, 6, 6)
        
        self.scene = QGraphicsScene()
        self.view = InteractiveGraphicsView(self.scene)
        panel_layout.addWidget(self.view)
        
        main_layout.addWidget(self.panel_frame, 1)
        self.panel_frame.hide()

    def _on_layer_toggle(self):
        self.show_labels_var = self.labels_cb.isChecked()
        self.show_occupancy_var = self.occ_cb.isChecked()
        self.show_violations_var = self.viol_cb.isChecked()
        self._redraw()

    def toggle(self):
        if self.visible:
            self.panel_frame.hide()
            self.toggle_btn.setText("▼ Show Canvas")
            self.visible = False
        else:
            self.panel_frame.show()
            self.toggle_btn.setText("▲ Hide Canvas")
            self.visible = True
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
        
        # Calculate bounding rect of the scene
        rect = self.scene.itemsBoundingRect()
        if not rect.isNull():
            # Add some padding
            rect.adjust(-10, -10, 10, 10)
            self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def _redraw(self):
        self.scene.clear()
        if not self.floor_plan:
            return
            
        plan = self.floor_plan
        
        # Rooms
        for room in plan.rooms:
            if room.polygon:
                poly = QPolygonF([QPointF(p[0], p[1]) for p in room.polygon])
                item = self.scene.addPolygon(poly, QPen(QColor("#b3c7c1"), 0.2), QBrush(QColor("#070909")))
                
                if self.show_labels_var or self.show_occupancy_var:
                    cx = sum(p[0] for p in room.polygon) / len(room.polygon)
                    cy = sum(p[1] for p in room.polygon) / len(room.polygon)
                    
                    text_parts = []
                    if self.show_labels_var:
                        text_parts.append(room.name)
                    if self.show_occupancy_var and room.occupancy > 0:
                        text_parts.append(f"Occ: {room.occupancy}")
                        
                    if text_parts:
                        text_item = self.scene.addText("\n".join(text_parts), QFont("Segoe UI", 2))
                        text_item.setDefaultTextColor(QColor("#8899aa"))
                        # Center the text
                        br = text_item.boundingRect()
                        text_item.setPos(cx - br.width()/2, cy - br.height()/2)

        # Corridors
        for corridor in plan.corridors:
            if corridor.polygon:
                poly = QPolygonF([QPointF(p[0], p[1]) for p in corridor.polygon])
                pen = QPen(QColor("#3a5070"), 0.1)
                pen.setStyle(Qt.PenStyle.DashLine)
                self.scene.addPolygon(poly, pen, QBrush(QColor("#070909")))

        # Exits
        for exit_ in plan.exits:
            ex, ey = exit_.position[0], exit_.position[1]
            # Draw exit circle
            self.scene.addEllipse(ex - 0.8, ey - 0.8, 1.6, 1.6, QPen(QColor("#4c5767"), 0.2), QBrush(QColor("#b3c7c1")))
            
            if self.show_labels_var:
                text_item = self.scene.addText("EXIT", QFont("Segoe UI", 2, QFont.Weight.Bold))
                text_item.setDefaultTextColor(QColor("#b3c7c1"))
                text_item.setPos(ex - text_item.boundingRect().width()/2, ey - 2)

        # Doors
        for door in plan.doors:
            dx, dy = door.position[0], door.position[1]
            r = 0.6
            self.scene.addLine(dx - r/2, dy, dx + r/2, dy, QPen(QColor("#c47b2a"), 0.2))
            
            # Simplified arc (just a rect path for PyQt)
            path = QPainterPath()
            path.arcMoveTo(QRectF(dx - r, dy - r, r*2, r*2), 0)
            path.arcTo(QRectF(dx - r, dy - r, r*2, r*2), 0, 90)
            self.scene.addPath(path, QPen(QColor("#c47b2a"), 0.2))

        # Violations
        if self.show_violations_var and self.violations:
            fallback_x = 0
            fallback_y = 0
            
            for idx, v in enumerate(self.violations):
                target = plan.get_room(v.location) or plan.get_corridor(v.location)
                
                if target and target.polygon:
                    wx = sum(p[0] for p in target.polygon) / len(target.polygon)
                    wy = sum(p[1] for p in target.polygon) / len(target.polygon)
                else:
                    wx = fallback_x + idx * 2
                    wy = fallback_y
                    
                color = QColor("#f44336") if v.severity == "critical" else QColor("#c47b2a") if v.severity == "major" else QColor("#fdd835")
                
                item = QGraphicsEllipseItem(wx - 0.9, wy - 0.9, 1.8, 1.8)
                item.setPen(QPen(QColor("#ffffff"), 0.2))
                item.setBrush(QBrush(color))
                item.setToolTip(f"<b>{v.rule} | {v.severity.upper()}</b><br>{v.description}")
                self.scene.addItem(item)
                
        # Only fit to window initially or if requested
        # To avoid jumping on every toggle, don't auto-fit here if we already have a view.

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
        
        # Animation using QTimer
        ring = QGraphicsEllipseItem(cx - 2.2, cy - 2.2, 4.4, 4.4)
        pen = QPen(QColor("#ff6b6b"), 0.3)
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