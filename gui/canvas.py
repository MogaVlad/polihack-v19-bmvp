import tkinter as tk
from tkinter import ttk
from typing import Optional

from models.floor_plan import FloorPlan


class CanvasPanel:
    def __init__(self, parent: ttk.Frame):
        self.parent = parent
        self.floor_plan: Optional[FloorPlan] = None
        self.visible = False
        self._build_ui()

    def _build_ui(self):
        self.toggle_frame = ttk.Frame(self.parent)
        self.toggle_frame.pack(fill=tk.X, padx=5)

        self.toggle_btn = ttk.Button(
            self.toggle_frame,
            text="Show Canvas",
            command=self.toggle,
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=5, pady=2)

        self.panel_frame = ttk.LabelFrame(self.parent, text="FLOOR PLAN CANVAS")
        self.canvas = tk.Canvas(
            self.panel_frame,
            bg="#ffffff",
            height=250,
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def toggle(self):
        if self.visible:
            self.panel_frame.pack_forget()
            self.toggle_btn.configure(text="Show Canvas")
            self.visible = False
        else:
            self.panel_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
            self.toggle_btn.configure(text="Hide Canvas")
            self.visible = True
            if self.floor_plan:
                self.render(self.floor_plan)

    def load_plan(self, plan: FloorPlan):
        self.floor_plan = plan
        if self.visible:
            self.render(plan)

    def render(self, plan: FloorPlan):
        self.canvas.delete("all")
        if not plan.rooms and not plan.corridors:
            self.canvas.create_text(
                self.canvas.winfo_width() // 2 or 400,
                self.canvas.winfo_height() // 2 or 125,
                text="No floor plan data to render",
                fill="#999999",
                font=("Segoe UI", 12),
            )
            return

        scale = 10
        offset_x, offset_y = 50, 50

        for room in plan.rooms:
            if room.polygon:
                coords = []
                for x, y in room.polygon:
                    coords.extend([x * scale + offset_x, y * scale + offset_y])
                self.canvas.create_polygon(
                    coords,
                    fill="#e3f2fd",
                    outline="#1565c0",
                    width=2,
                    tags="room",
                )
                cx = sum(p[0] for p in room.polygon) / len(room.polygon) * scale + offset_x
                cy = sum(p[1] for p in room.polygon) / len(room.polygon) * scale + offset_y
                self.canvas.create_text(cx, cy, text=room.name, font=("Segoe UI", 8), fill="#333")

        for corridor in plan.corridors:
            if corridor.polygon:
                coords = []
                for x, y in corridor.polygon:
                    coords.extend([x * scale + offset_x, y * scale + offset_y])
                self.canvas.create_polygon(
                    coords,
                    fill="#f5f5f5",
                    outline="#757575",
                    width=1,
                    dash=(4, 2),
                    tags="corridor",
                )

        for exit_ in plan.exits:
            ex = exit_.position[0] * scale + offset_x
            ey = exit_.position[1] * scale + offset_y
            self.canvas.create_oval(
                ex - 6, ey - 6, ex + 6, ey + 6,
                fill="#4caf50",
                outline="#2e7d32",
                width=2,
                tags="exit",
            )
            self.canvas.create_text(ex, ey - 12, text="EXIT", font=("Segoe UI", 7, "bold"), fill="#2e7d32")

    def show_violations(self, violations):
        for v in violations:
            pass

    def clear(self):
        self.canvas.delete("all")
        self.floor_plan = None
