def get_stylesheet(dark_mode: bool = True) -> str:
    if dark_mode:
        text = "#e8edf0"
        bg = "#171d22"              # app shell
        sidebar_bg = "#11171c"      # darker sidebar for visual hierarchy
        content_bg = "#1d252b"      # lighter content surface
        card_bg = "#222b32"
        primary = "#b7c4cb"
        secondary = "#4f5a6b"
        accent = "#6f88a8"
        success = "#4caf8d"
        warning = "#d4a24c"
        danger = "#d86a6a"
    else:
        text = "#12171a"
        bg = "#edf1f3"
        sidebar_bg = "#dfe6ea"
        content_bg = "#f5f7f9"
        card_bg = "#ffffff"
        primary = "#3b4a52"
        secondary = "#8893a4"
        accent = "#5f7390"
        success = "#2f8d70"
        warning = "#b6802e"
        danger = "#b85454"

    border = "#303a42" if dark_mode else "#ccd4da"
    input_bg = "#1a2127" if dark_mode else "#f2f5f7"
    hover = "#2a333a" if dark_mode else "#e6edf2"
    muted = primary
    subtle = "#9aa7ae" if dark_mode else "#5f6f78"

    qss = f"""
    QMainWindow {{
        background-color: {bg};
    }}

    QWidget {{
        color: {text};
        font-family: "Segoe UI", sans-serif;
        font-size: 12px;
    }}

    /* Header */
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
    }}
    QPushButton[class="HeaderBtn"]:hover {{
        background-color: {hover};
        color: {text};
    }}

    /* Sidebar */
    QFrame[class="Sidebar"] {{
        background-color: {sidebar_bg};
        border-right: 1px solid {border};
    }}

    QLabel[class="SidebarTitle"] {{
        font-size: 11px;
        font-weight: 700;
        color: {muted};
        letter-spacing: 1px;
    }}

    QLabel[class="CategoryLabel"] {{
        font-size: 10px;
        font-weight: 700;
        color: {subtle};
        letter-spacing: 1px;
        padding-left: 2px;
    }}

    QLineEdit[class="SidebarSearch"] {{
        background-color: {card_bg};
        color: {text};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 7px 10px;
        font-size: 12px;
    }}

    /* Main cards */
    QFrame[class="Card"] {{
        background-color: {card_bg};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 8px;
    }}

    /* L2 intentionally plain */
    QFrame[class="L2Plain"] {{
        background-color: {content_bg};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 6px;
    }}

    QPushButton[class="L2PlainBtn"] {{
        background-color: {secondary};
        color: {text};
        border: none;
        border-radius: 5px;
        padding: 7px 12px;
        font-weight: 500;
    }}
    QPushButton[class="L2PlainBtn"]:hover {{
        background-color: {accent};
    }}

    /* Agent cards */
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

    QLabel[class="AgentCardSubtitle"] {{
        font-size: 11px;
        color: {subtle};
        background: transparent;
    }}

    QLabel[class="StatusDotBuiltIn"] {{
        color: {success};
        font-size: 14px;
    }}
    QLabel[class="StatusDotCustom"] {{
        color: {accent};
        font-size: 14px;
    }}
    QLabel[class="StatusDotUnknown"] {{
        color: {warning};
        font-size: 14px;
    }}

    QPushButton[class="CreateBtn"] {{
        background-color: {secondary};
        color: {text};
        border: none;
        border-radius: 8px;
        padding: 10px 16px;
        font-weight: 700;
        font-size: 12px;
    }}
    QPushButton[class="CreateBtn"]:hover {{
        background-color: {accent};
    }}

    QPushButton[class="SidebarBtn"] {{
        background-color: transparent;
        color: {muted};
        text-align: left;
        padding: 8px 14px;
        border: none;
        border-radius: 8px;
        font-size: 12px;
    }}
    QPushButton[class="SidebarBtn"]:hover {{
        background-color: {hover};
        color: {text};
    }}

    QPushButton {{
        background-color: {secondary};
        color: {text};
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 700;
    }}
    QPushButton:hover {{
        background-color: {accent};
    }}
    QPushButton:disabled {{
        background-color: {border};
        color: {muted};
    }}

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

    QLabel[class="Title"] {{
        font-size: 16px;
        font-weight: 700;
    }}

    QLabel[class="Subtitle"] {{
        font-size: 11px;
        color: {muted};
    }}

    QLabel[class="SectionHeader"] {{
        font-size: 11px;
        font-weight: 700;
        color: {muted};
    }}

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

    QProgressBar {{
        border: 1px solid {border};
        border-radius: 6px;
        background: {input_bg};
        text-align: center;
        min-height: 16px;
    }}
    QProgressBar::chunk {{
        background-color: {accent};
        border-radius: 6px;
    }}

    QDialog {{
        background-color: {bg};
    }}

    QToolTip {{
        background-color: {card_bg};
        color: {text};
        border: 1px solid {border};
        padding: 6px;
        border-radius: 4px;
    }}
    """
    return qss
