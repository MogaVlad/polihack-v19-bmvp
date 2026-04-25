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
            fg_color=("gray78", "#0f3460"),
            hover_color=("gray68", "#1e4a8a"),
            text_color=("gray10", "#c0d0e0"),
            command=self.toggle,
        )
        self.toggle_btn.pack(side="left", padx=(0, 12))

        # Example plan dropdown
        ctk.CTkLabel(
            self.toggle_frame, text="Load Example:",
            font=ctk.CTkFont(size=11), text_color=("gray40", "#8899aa"),
        ).pack(side="left", padx=(0, 4))

        self.example_combo = ctk.CTkComboBox(
            self.toggle_frame,
            values=self._get_example_names(),
            width=180, height=28, corner_radius=6,
            state="readonly",
            fg_color=("gray96", "#0e1117"),
            border_color=("gray75", "#2a3f60"),
            button_color=("gray75", "#1e4a8a"),
            button_hover_color=("gray60", "#3a5f90"),
            text_color=("gray10", "#e0e0e0"),
            dropdown_fg_color=("gray96", "#162d50"),
            font=ctk.CTkFont(size=11),
            command=self._on_example_selected,
        )
        self.example_combo.pack(side="left", padx=(0, 12))

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
                text_color=("gray30", "#8899aa"),
                fg_color="#4a9eff", hover_color="#3a89dd",
                border_color=("gray60", "#3a5070"),
                command=self._redraw,
            ).pack(side="left", padx=6)

        ctk.CTkButton(
            self.toggle_frame, text="Fit", width=50, height=28, corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=("gray78", "#0f3460"), hover_color=("gray68", "#1e4a8a"),
            text_color=("gray10", "#c0d0e0"), command=self.fit_to_window,
        ).pack(side="right", padx=4)

        # ── Canvas panel (hidden initially) ─────────────────────
        self.panel_frame = ctk.CTkFrame(
            self.parent,
            fg_color=("gray92", "#162d50"),
            corner_radius=10,
        )

        # The tk.Canvas itself (no CTk equivalent)
        self.canvas = tk.Canvas(
            self.panel_frame,
            bg="#0e1117",
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

    # ── Examples ─────────────────────────────────────────────────
    def _get_example_names(self):
        if os.path.exists(config.FLOOR_PLANS_DIR):
            return [f for f in os.listdir(config.FLOOR_PLANS_DIR) if f.endswith(".json")]
        return []

    def _on_example_selected(self, selection):
        if selection:
            path = os.path.join(config.FLOOR_PLANS_DIR, selection)
            plan = FloorPlan.load_from_json(path)
            self.load_plan(plan)
            self.fit_to_window()
            if not self.visible:
                self.toggle()

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
                    coords, fill="#1a2744", outline="#4a9eff",
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
                    coords, fill="#111827", outline="#3a5070",
                    width=1, dash=(4, 2), tags="corridor",
                )

        # Exits
        for exit_ in plan.exits:
            ex, ey = exit_.position[0] * s + ox, exit_.position[1] * s + oy
            self.canvas.create_oval(
                ex - 7, ey - 7, ex + 7, ey + 7,
                fill="#4caf50", outline="#2e7d32", width=2, tags="exit",
            )
            if self.show_labels_var.get():
                self.canvas.create_text(
                    ex, ey - 14, text="EXIT",
                    font=("Segoe UI", 7, "bold"), fill="#4caf50",
                )

        # Doors
        for door in plan.doors:
            dx, dy = door.position[0] * s + ox, door.position[1] * s + oy
            self.canvas.create_rectangle(
                dx - 4, dy - 4, dx + 4, dy + 4,
                fill="#ff9800", outline="#e65100", tags="door",
            )

        # Violations
        if self.show_violations_var.get() and self.violations:
            for idx, v in enumerate(self.violations):
                vx, vy = None, None
                target = plan.get_room(v.location) or plan.get_corridor(v.location)

                if target and target.polygon:
                    vx = sum(p[0] for p in target.polygon) / len(target.polygon) * s + ox
                    vy = sum(p[1] for p in target.polygon) / len(target.polygon) * s + oy
                else:
                    vx, vy = ox + 30 + (idx * 20), oy + 30

                color = "#f44336" if v.severity == "critical" else "#ff9800" if v.severity == "major" else "#fdd835"
                tag_id = f"violation_{idx}"

                item = self.canvas.create_oval(
                    vx - 9, vy - 9, vx + 9, vy + 9,
                    fill=color, outline="#ffffff", width=2,
                    tags=("violation", tag_id),
                )
                self.canvas.itemconfig(
                    item,
                    tags=("violation", tag_id, f"data:{v.rule} | {v.severity.upper()}\n{v.description}"),
                )

    # ── Tooltips ─────────────────────────────────────────────────
    def _on_violation_hover(self, event):
        item = self.canvas.find_withtag("current")[0]
        tags = self.canvas.gettags(item)
        text = "Violation Details"

        for t in tags:
            if t.startswith("data:"):
                text = t[5:]
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
        if self._tooltip_window:
            self._tooltip_window.destroy()
            self._tooltip_window = None

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