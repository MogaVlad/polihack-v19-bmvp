def get_stylesheet(dark_mode: bool = True) -> str:
    if dark_mode:
        text = "#e8ecee"
        bg = "#0f1315"
        primary = "#b3c0c7"
        secondary = "#4f4c67"
        accent = "#8b81a2"
    else:
        text = "#111517"
        bg = "#eaeef0"
        primary = "#38454c"
        secondary = "#9b98b3"
        accent = "#675d7e"

    surface = "#181c1f" if dark_mode else "#dde2e5"
    border = "#282e33" if dark_mode else "#c4cad0"
    input_bg = "#1e2327" if dark_mode else "#d5dade"
    hover = "#252b30" if dark_mode else "#cfd5da"
    muted = primary

    qss = f"""
    /* ── Base ──────────────────────────────────────── */

    QMainWindow {{
        background-color: {bg};
    }}

    QWidget {{
        color: {text};
        font-family: "Segoe UI", sans-serif;
        font-size: 12px;
    }}

    /* ── Cards ─────────────────────────────────────── */

    QFrame[class="Card"] {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 8px;
    }}

    /* ── Header ────────────────────────────────────── */

    QFrame[class="Header"] {{
        background-color: {bg};
        border-bottom: 1px solid {border};
    }}

    QPushButton[class="HeaderBtn"] {{
        background-color: transparent;
        color: {muted};
        border: none;
        border-radius: 6px;
        padding: 4px;
        font-size: 18px;
        font-weight: normal;
    }}
    QPushButton[class="HeaderBtn"]:hover {{
        background-color: {hover};
        color: {text};
    }}

    /* ── Sidebar ───────────────────────────────────── */

    QFrame[class="Sidebar"] {{
        background-color: {bg};
        border-right: 1px solid {border};
    }}

    QLabel[class="SidebarTitle"] {{
        font-size: 11px;
        font-weight: bold;
        color: {muted};
        letter-spacing: 1px;
    }}

    QLabel[class="CategoryLabel"] {{
        font-size: 10px;
        font-weight: bold;
        color: {muted};
        letter-spacing: 1px;
    }}

    QLineEdit[class="SidebarSearch"] {{
        background-color: {surface};
        color: {text};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 7px 10px;
        font-size: 12px;
    }}

    /* ── Agent Cards ───────────────────────────────── */

    QPushButton[class="AgentCard"] {{
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 8px;
        text-align: left;
        padding: 0;
    }}
    QPushButton[class="AgentCard"]:hover {{
        background-color: {hover};
        border: 1px solid {border};
    }}

    QLabel[class="AgentCardTitle"] {{
        font-size: 13px;
        font-weight: 600;
        color: {text};
        background: transparent;
    }}

    QPushButton[class="CreateBtn"] {{
        background-color: {secondary};
        color: {text};
        border: none;
        border-radius: 8px;
        padding: 10px 16px;
        font-weight: bold;
        font-size: 12px;
    }}
    QPushButton[class="CreateBtn"]:hover {{
        background-color: {accent};
    }}

    /* ── Sidebar Nav Buttons ───────────────────────── */

    QPushButton[class="SidebarBtn"] {{
        background-color: transparent;
        color: {muted};
        text-align: left;
        padding: 8px 14px;
        border: none;
        border-radius: 8px;
        font-weight: normal;
        font-size: 12px;
    }}
    QPushButton[class="SidebarBtn"]:hover {{
        background-color: {hover};
        color: {text};
    }}

    /* ── Buttons ───────────────────────────────────── */

    QPushButton {{
        background-color: {secondary};
        color: {text};
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {accent};
    }}
    QPushButton:disabled {{
        background-color: {border};
        color: {muted};
    }}

    /* ── Inputs ────────────────────────────────────── */

    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {input_bg};
        color: {text};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 6px;
    }}

    QComboBox {{
        background-color: {input_bg};
        color: {text};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 4px 8px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {input_bg};
        color: {text};
        selection-background-color: {secondary};
        border: 1px solid {border};
    }}

    /* ── Scroll ────────────────────────────────────── */

    QScrollArea {{
        border: none;
        background-color: transparent;
    }}

    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 6px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {border};
        min-height: 20px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {muted};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        border: none;
        background: transparent;
        height: 6px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {border};
        min-width: 20px;
        border-radius: 3px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ── Labels ────────────────────────────────────── */

    QLabel[class="Title"] {{
        font-size: 16px;
        font-weight: bold;
    }}

    QLabel[class="Subtitle"] {{
        font-size: 11px;
        color: {muted};
    }}

    QLabel[class="SectionHeader"] {{
        font-size: 11px;
        font-weight: bold;
        color: {muted};
    }}

    /* ── Checkboxes ────────────────────────────────── */

    QCheckBox {{
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {border};
        border-radius: 4px;
    }}
    QCheckBox::indicator:checked {{
        background-color: {accent};
        border: 2px solid {accent};
    }}

    /* ── Misc ──────────────────────────────────────── */

    QSplitter::handle {{
        background-color: {border};
        width: 2px;
    }}

    QMessageBox {{
        background-color: {surface};
    }}

    QDialog {{
        background-color: {bg};
    }}

    QToolTip {{
        background-color: {surface};
        color: {text};
        border: 1px solid {border};
        padding: 6px;
        border-radius: 4px;
    }}
    """
    return qss
