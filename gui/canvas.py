import os
import tkinter as tk
import customtkinter as ctk
from typing import Optional, List

import config
from models.floor_plan import FloorPlan
from models.violations import Violation


class CanvasPanel:
    def __init__(self, parent: ctk.CTkFrame):
        self.parent = parent
        self.floor_plan: Optional[FloorPlan] = None
        self.violations: List[Violation] = []
        self.visible = False

        # Viewport state
        self.scale = 10.0
        self.offset_x = 50.0
        self.offset_y = 50.0
        self._drag_data = {"x": 0, "y": 0}

        # Layer toggles
        self.show_labels_var = ctk.BooleanVar(value=True)
        self.show_occupancy_var = ctk.BooleanVar(value=True)
        self.show_violations_var = ctk.BooleanVar(value=True)

        self._build_ui()
        self._tooltip_window = None
        self._violation_data: dict = {}  # tag_id -> tooltip text

    def _build_ui(self):
        # ── Toggle / controls bar ───────────────────────────────
        self.toggle_frame = ctk.CTkFrame(
            self.parent,
            height=36,
            fg_color="transparent",
        )
        self.toggle_frame.pack(fill="x", padx=8, pady=(4, 0))

        self.toggle_btn = ctk.CTkButton(
            self.toggle_frame,
            text="▼ Show Canvas",
            width=130,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=("#384c46", "#4c5767"),
            hover_color=("#2a3a34", "#3a4854"),
            text_color=("#f6f8f8", "#e8edeb"),
            command=self.toggle,
        )
        self.toggle_btn.pack(side="left", padx=(0, 12))

        # Layer checkboxes
        for text, var in [
            ("Labels", self.show_labels_var),
            ("Occupancy", self.show_occupancy_var),
            ("Violations", self.show_violations_var),
        ]:
            ctk.CTkCheckBox(
                self.toggle_frame, text=text, variable=var,
                width=24, height=24,
                font=ctk.CTkFont(size=11),
                text_color=("#121715", "#b3c7c1"),
                fg_color="#384c46", hover_color="#2a3a34",
                border_color=("#384c46", "#b3c7c1"),
                command=self._redraw,
            ).pack(side="left", padx=6)

        ctk.CTkButton(
            self.toggle_frame, text="Fit", width=50, height=28, corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=("#384c46", "#4c5767"), hover_color=("#2a3a34", "#3a4854"),
            text_color=("#f6f8f8", "#e8edeb"), command=self.fit_to_window,
        ).pack(side="right", padx=4)

        # ── Canvas panel (hidden initially) ─────────────────────
        self.panel_frame = ctk.CTkFrame(
            self.parent,
            fg_color=("#f6f8f8", "#070909"),
            corner_radius=10,
        )

        # The tk.Canvas itself (no CTk equivalent)
        self.canvas = tk.Canvas(
            self.panel_frame,
            bg="#070909",
            height=280,
            highlightthickness=0,
            cursor="crosshair",
            relief="flat",
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True, padx=6, pady=6)

        # Pan and zoom
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<MouseWheel>", self._on_zoom)
        self.canvas.bind("<Button-4>", self._on_zoom)
        self.canvas.bind("<Button-5>", self._on_zoom)

        # Tooltip bindings
        self.canvas.tag_bind("violation", "<Enter>", self._on_violation_hover)
        self.canvas.tag_bind("violation", "<Leave>", self._on_violation_leave)

    # ── Toggle ───────────────────────────────────────────────────
    def toggle(self):
        if self.visible:
            self.panel_frame.pack_forget()
            self.toggle_btn.configure(text="▼ Show Canvas")
            self.visible = False
        else:
            self.panel_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))
            self.toggle_btn.configure(text="▲ Hide Canvas")
            self.visible = True
            self._redraw()

    # ── Load / show ──────────────────────────────────────────────
    def load_plan(self, plan: FloorPlan):
        self.floor_plan = plan
        self.violations = []
        self._violation_data.clear()
        if self.visible:
            self._redraw()

    def show_violations(self, violations: List[Violation]):
        self.violations = violations
        if self.visible:
            self._redraw()

    # ── Fit to window ────────────────────────────────────────────
    def fit_to_window(self):
        if not self.floor_plan:
            return

        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        for r in self.floor_plan.rooms:
            for x, y in r.polygon:
                min_x, min_y = min(min_x, x), min(min_y, y)
                max_x, max_y = max(max_x, x), max(max_y, y)

        if min_x == float('inf'):
            return

        w = max_x - min_x
        h = max_y - min_y

        canvas_w = self.canvas.winfo_width() or 800
        canvas_h = self.canvas.winfo_height() or 280

        scale_x = (canvas_w - 60) / w if w > 0 else 10
        scale_y = (canvas_h - 60) / h if h > 0 else 10

        self.scale = min(scale_x, scale_y)
        self.offset_x = (canvas_w - w * self.scale) / 2 - min_x * self.scale
        self.offset_y = (canvas_h - h * self.scale) / 2 - min_y * self.scale

        self._redraw()

    # ── Pan & Zoom ───────────────────────────────────────────────
    def _on_drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag_motion(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self.offset_x += dx
        self.offset_y += dy
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self._redraw()

    def _on_zoom(self, event):
        factor = 1.1 if event.num == 4 or getattr(event, 'delta', 0) > 0 else 0.9
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        self.offset_x = x - (x - self.offset_x) * factor
        self.offset_y = y - (y - self.offset_y) * factor
        self.scale *= factor
        self._redraw()

    # ── Draw ─────────────────────────────────────────────────────
    def _redraw(self):
        # Bug fix: destroy any open tooltip before wiping canvas items.
        # When canvas.delete("all") removes violation ovals, tkinter does NOT
        # fire the tag <Leave> binding, so the tooltip would stay on screen.
        self._destroy_tooltip()

        self.canvas.delete("all")
        if not self.floor_plan:
            return

        plan = self.floor_plan
        s, ox, oy = self.scale, self.offset_x, self.offset_y

        # Rooms
        for room in plan.rooms:
            if room.polygon:
                coords = [coord for pt in room.polygon for coord in (pt[0] * s + ox, pt[1] * s + oy)]
                self.canvas.create_polygon(
                    coords, fill="#070909", outline="#b3c7c1",
                    width=2, tags="room",
                )

                if self.show_labels_var.get() or self.show_occupancy_var.get():
                    cx = sum(p[0] for p in room.polygon) / len(room.polygon) * s + ox
                    cy = sum(p[1] for p in room.polygon) / len(room.polygon) * s + oy

                    text_parts = []
                    if self.show_labels_var.get():
                        text_parts.append(room.name)
                    if self.show_occupancy_var.get() and room.occupancy > 0:
                        text_parts.append(f"Occ: {room.occupancy}")

                    if text_parts:
                        self.canvas.create_text(
                            cx, cy, text="\n".join(text_parts),
                            font=("Segoe UI", 8), fill="#8899aa",
                            justify="center",
                        )

        # Corridors
        for corridor in plan.corridors:
            if corridor.polygon:
                coords = [coord for pt in corridor.polygon for coord in (pt[0] * s + ox, pt[1] * s + oy)]
                self.canvas.create_polygon(
                    coords, fill="#070909", outline="#3a5070",
                    width=1, dash=(4, 2), tags="corridor",
                )

        # Exits — draw as directional arrow marker
        for exit_ in plan.exits:
            ex, ey = exit_.position[0] * s + ox, exit_.position[1] * s + oy
            # Background circle
            self.canvas.create_oval(
                ex - 8, ey - 8, ex + 8, ey + 8,
                fill="#b3c7c1", outline="#4c5767", width=2, tags="exit",
            )
            # Arrow pointing up (exit direction)
            self.canvas.create_line(
                ex, ey + 5, ex, ey - 5,
                fill="#ffffff", width=2, arrow="last",
                arrowshape=(6, 8, 3), tags="exit",
            )
            if self.show_labels_var.get():
                self.canvas.create_text(
                    ex, ey - 18, text="EXIT",
                    font=("Segoe UI", 7, "bold"), fill="#b3c7c1",
                )

        # Doors — draw as arc (door swing)
        for door in plan.doors:
            dx, dy = door.position[0] * s + ox, door.position[1] * s + oy
            r = max(6, s * 0.4)
            # Door frame line
            self.canvas.create_line(
                dx - r * 0.5, dy, dx + r * 0.5, dy,
                fill="#c47b2a", width=2, tags="door",
            )
            # Door swing arc
            self.canvas.create_arc(
                dx - r, dy - r, dx + r, dy + r,
                start=0, extent=90,
                style="arc", outline="#c47b2a", width=2, tags="door",
            )

        # Violations
        if self.show_violations_var.get() and self.violations:
            # Compute world-space bounds for fallback positioning.
            # Unmatched dots get placed in world coords so they pan/zoom
            # with the drawing instead of floating at fixed screen offsets.
            all_wx = [p[0] for room in plan.rooms if room.polygon for p in room.polygon]
            all_wy = [p[1] for room in plan.rooms if room.polygon for p in room.polygon]
            fallback_wx = (min(all_wx) if all_wx else 0) - 3
            fallback_wy = (min(all_wy) if all_wy else 0) - 3

            for idx, v in enumerate(self.violations):
                target = plan.get_room(v.location) or plan.get_corridor(v.location)

                if target and target.polygon:
                    # World-space centroid → screen coords
                    wx = sum(p[0] for p in target.polygon) / len(target.polygon)
                    wy = sum(p[1] for p in target.polygon) / len(target.polygon)
                else:
                    # Bug fix: use world-space coords for fallback so dots
                    # pan and zoom together with the floor plan geometry.
                    wx = fallback_wx + idx * 2
                    wy = fallback_wy

                vx = wx * s + ox
                vy = wy * s + oy

                color = "#f44336" if v.severity == "critical" else "#c47b2a" if v.severity == "major" else "#fdd835"
                tag_id = f"violation_{idx}"
                # Store tooltip data in a separate dict keyed by tag_id —
                # embedding it inside a tag string is unreliable across tkinter versions.
                self._violation_data[tag_id] = f"{v.rule} | {v.severity.upper()}\n{v.description}"

                self.canvas.create_oval(
                    vx - 9, vy - 9, vx + 9, vy + 9,
                    fill=color, outline="#ffffff", width=2,
                    tags=("violation", tag_id),
                )

        # Re-bind tooltip events after every redraw (tag_bind survives
        # delete("all") on the tag name but items are new objects).
        self.canvas.tag_bind("violation", "<Enter>", self._on_violation_hover)
        self.canvas.tag_bind("violation", "<Leave>", self._on_violation_leave)

    # ── Tooltips ─────────────────────────────────────────────────
    def _destroy_tooltip(self):
        if self._tooltip_window:
            try:
                self._tooltip_window.destroy()
            except Exception:
                pass
            self._tooltip_window = None

    def _on_violation_hover(self, event):
        self._destroy_tooltip()
        item = self.canvas.find_withtag("current")[0]
        tags = self.canvas.gettags(item)

        text = "Violation Details"
        for t in tags:
            if t.startswith("violation_"):
                text = self._violation_data.get(t, text)
                break

        x = self.canvas.winfo_rootx() + event.x + 15
        y = self.canvas.winfo_rooty() + event.y + 10

        self._tooltip_window = tk.Toplevel(self.canvas)
        self._tooltip_window.wm_overrideredirect(True)
        self._tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self._tooltip_window, text=text, justify="left",
            background="#1a1a2e", foreground="#e0e0e0",
            relief="solid", borderwidth=1,
            font=("Segoe UI", 9), padx=8, pady=6,
        )
        label.pack()

    def _on_violation_leave(self, event):
        self._destroy_tooltip()

    def highlight_location(self, location_id: str):
        if not self.floor_plan:
            return
        if not self.visible:
            self.toggle()

        target = self.floor_plan.get_room(location_id) or self.floor_plan.get_corridor(location_id)
        if not target or not target.polygon:
            return

        s, ox, oy = self.scale, self.offset_x, self.offset_y
        cx = sum(p[0] for p in target.polygon) / len(target.polygon) * s + ox
        cy = sum(p[1] for p in target.polygon) / len(target.polygon) * s + oy

        tag = "_highlight"
        self.canvas.delete(tag)
        ring = self.canvas.create_oval(
            cx - 22, cy - 22, cx + 22, cy + 22,
            outline="#ff6b6b", width=3, dash=(6, 3), tags=tag,
        )
        self._flash_highlight(tag, ring, 0)

    def _flash_highlight(self, tag: str, item_id: int, count: int):
        if count >= 8:
            self.canvas.delete(tag)
            return
        state = "hidden" if count % 2 else "normal"
        try:
            self.canvas.itemconfigure(item_id, state=state)
        except tk.TclError:
            return
        self.canvas.after(300, lambda: self._flash_highlight(tag, item_id, count + 1))

    def clear(self):
        self.canvas.delete("all")
        self.floor_plan = None
        self.violations = []
        self._drag_data = {"x": 0, "y": 0}