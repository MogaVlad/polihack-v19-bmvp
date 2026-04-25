import os

def get_stylesheet(dark_mode: bool = True) -> str:
    """Returns the QSS stylesheet for the application."""
    if dark_mode:
        main_bg = "#4c5767"
        card_bg = "#070909"
        text_color = "#e8edeb"
        text_muted = "#b3c7c1"
        btn_bg = "#384c46"
        btn_hover = "#2a3a34"
        btn_text = "#e8edeb"
        accent = "#8889a5"
        border = "#b3c7c1"
        input_bg = "#121715"
    else:
        main_bg = "#98a3b3"
        card_bg = "#f6f8f8"
        text_color = "#121715"
        text_muted = "#4c5767"
        btn_bg = "#384c46"
        btn_hover = "#2a3a34"
        btn_text = "#f6f8f8"
        accent = "#5a5b77"
        border = "#3a4854"
        input_bg = "#e8edeb"

    qss = f"""
    QMainWindow {{
        background-color: {main_bg};
    }}
    
    QWidget {{
        color: {text_color};
        font-family: "Segoe UI", sans-serif;
        font-size: 12px;
    }}

    QFrame.Card {{
        background-color: {card_bg};
        border-radius: 10px;
    }}
    
    QFrame.Header {{
        background-color: {card_bg};
        border-bottom: 1px solid {border};
    }}

    QFrame.Sidebar {{
        background-color: {main_bg};
        border-right: 1px solid {border};
    }}

    QPushButton {{
        background-color: {btn_bg};
        color: {btn_text};
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: bold;
    }}
    
    QPushButton:hover {{
        background-color: {btn_hover};
    }}
    
    QPushButton:disabled {{
        background-color: {text_muted};
        color: {card_bg};
    }}
    
    QPushButton.SidebarBtn {{
        background-color: {btn_bg};
        text-align: left;
        padding-left: 16px;
    }}

    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {input_bg};
        color: {text_color};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 6px;
    }}
    
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    
    QScrollBar:vertical {{
        border: none;
        background: {main_bg};
        width: 10px;
        margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {btn_bg};
        min-height: 20px;
        border-radius: 5px;
    }}
    
    QTabWidget::pane {{
        border: none;
        background: {card_bg};
        border-radius: 10px;
    }}
    
    QTabBar::tab {{
        background: {main_bg};
        color: {text_color};
        padding: 8px 16px;
        margin-right: 4px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }}
    
    QTabBar::tab:selected {{
        background: {btn_bg};
        color: {btn_text};
    }}
    
    QLabel.Title {{
        font-size: 18px;
        font-weight: bold;
    }}
    
    QLabel.Subtitle {{
        font-size: 12px;
        color: {text_muted};
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
        background-color: {btn_bg};
        border: 2px solid {btn_bg};
    }}
    """
    return qss
