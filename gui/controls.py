import customtkinter as ctk


class StatusBar:
    def __init__(self, parent):
        self.parent = parent

        self.frame = ctk.CTkFrame(
            parent,
            height=36,
            corner_radius=0,
            fg_color=("#e7d5a5", "#1a0e05"),
            border_width=0,
        )

        inner = ctk.CTkFrame(self.frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=4)

        self.status_label = ctk.CTkLabel(
            inner,
            text="● Ready",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#92817A", "#92817A"),
        )
        self.status_label.pack(side="left")

        sep1 = ctk.CTkLabel(inner, text="│", text_color=("#543520", "#92817A"), font=ctk.CTkFont(size=12))
        sep1.pack(side="left", padx=12)

        self.agents_label = ctk.CTkLabel(
            inner,
            text="Agents: 0 loaded",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#543520", "#92817A"),
        )
        self.agents_label.pack(side="left")

        sep2 = ctk.CTkLabel(inner, text="│", text_color=("#543520", "#92817A"), font=ctk.CTkFont(size=12))
        sep2.pack(side="left", padx=12)

        self.tools_label = ctk.CTkLabel(
            inner,
            text="Tools: 0 available",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#543520", "#92817A"),
        )
        self.tools_label.pack(side="left")

        # Dark / Light switch
        right_frame = ctk.CTkFrame(inner, fg_color="transparent")
        right_frame.pack(side="right")

        self.mode_label = ctk.CTkLabel(
            right_frame,
            text="☀",
            font=ctk.CTkFont(size=14),
            text_color=("#543520", "#92817A"),
        )
        self.mode_label.pack(side="left", padx=(0, 6))

        self.theme_switch = ctk.CTkSwitch(
            right_frame,
            text="",
            width=42,
            height=22,
            switch_width=38,
            switch_height=18,
            command=self._toggle_theme,
            onvalue=1,
            offvalue=0,
            progress_color="#92817A",
        )
        self.theme_switch.pack(side="left")
        self.theme_switch.select()  # Start with dark mode ON

        self.moon_label = ctk.CTkLabel(
            right_frame,
            text="🌙",
            font=ctk.CTkFont(size=14),
            text_color=("#543520", "#92817A"),
        )
        self.moon_label.pack(side="left", padx=(6, 0))

    def _toggle_theme(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")

    def set_status(self, text: str, color: str = "#92817A"):
        self.status_label.configure(text=f"● {text}", text_color=(color, color))

    def set_agent_count(self, count: int):
        self.agents_label.configure(text=f"Agents: {count} loaded")

    def set_tool_count(self, count: int):
        self.tools_label.configure(text=f"Tools: {count} available")