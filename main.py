import sys
import os
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app import App
from gui.theme import get_stylesheet


def main():
    qapp = QApplication(sys.argv)
    qapp.setStyleSheet(get_stylesheet(dark_mode=True))

    app_window = App()
    app_window.show()

    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()
