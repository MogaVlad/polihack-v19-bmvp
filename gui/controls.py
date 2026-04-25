import tkinter as tk
from tkinter import ttk


class StatusBar:
    def __init__(self, parent: tk.Tk):
        self.frame = ttk.Frame(parent, relief=tk.SUNKEN)

        self.status_label = ttk.Label(
            self.frame,
            text="Status: Ready",
            font=("Segoe UI", 9),
            padding=(10, 3),
        )
        self.status_label.pack(side=tk.LEFT)

        self.agents_label = ttk.Label(
            self.frame,
            text="Agents: 0 loaded",
            font=("Segoe UI", 9),
            padding=(10, 3),
        )
        self.agents_label.pack(side=tk.LEFT, padx=20)

        self.tools_label = ttk.Label(
            self.frame,
            text="Tools: 0 available",
            font=("Segoe UI", 9),
            padding=(10, 3),
        )
        self.tools_label.pack(side=tk.LEFT)

    def set_status(self, text: str):
        self.status_label.configure(text=f"Status: {text}")

    def set_agent_count(self, count: int):
        self.agents_label.configure(text=f"Agents: {count} loaded")

    def set_tool_count(self, count: int):
        self.tools_label.configure(text=f"Tools: {count} available")
