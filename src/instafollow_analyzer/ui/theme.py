"""Paletas próprias, sem ativos ou marcas do Instagram."""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def apply_theme(app: QApplication, dark: bool) -> None:
    colors = (
        {
            "bg": "#10151f",
            "surface": "#1a2230",
            "text": "#edf2fa",
            "muted": "#aebcd0",
            "border": "#354258",
            "accent": "#89aaff",
            "hover": "#28364c",
            "selection": "#3d5785",
        }
        if dark
        else {
            "bg": "#f3f5fa",
            "surface": "#ffffff",
            "text": "#202b40",
            "muted": "#536079",
            "border": "#c4cede",
            "accent": "#325aca",
            "hover": "#e8edfa",
            "selection": "#d5e1ff",
        }
    )
    palette = QPalette()
    for role, color in [
        (QPalette.ColorRole.Window, "bg"),
        (QPalette.ColorRole.Link, "accent"),
        (QPalette.ColorRole.WindowText, "text"),
        (QPalette.ColorRole.Base, "surface"),
        (QPalette.ColorRole.AlternateBase, "bg"),
        (QPalette.ColorRole.Text, "text"),
        (QPalette.ColorRole.Button, "surface"),
        (QPalette.ColorRole.ButtonText, "text"),
        (QPalette.ColorRole.Highlight, "selection"),
        (QPalette.ColorRole.HighlightedText, "text"),
        (QPalette.ColorRole.ToolTipBase, "surface"),
        (QPalette.ColorRole.ToolTipText, "text"),
        (QPalette.ColorRole.PlaceholderText, "muted"),
    ]:
        palette.setColor(role, QColor(colors[color]))
    app.setPalette(palette)
    app.setStyleSheet(
        """
        QWidget {{ font-family: 'Segoe UI', 'Noto Sans', sans-serif; font-size: 14px;
                  color: {text}; }}
        QMainWindow, QScrollArea, QWidget#page {{ background: {bg}; }}
        QLabel {{ background: transparent; }}
        QLabel#title {{ font-size: 28px; font-weight: 700; }}
        QLabel#subtitle {{ color: {muted}; }}
        QLabel#eyebrow {{ color: {accent}; font-weight: 700; }}
        QLabel#sectionTitle {{ font-size: 18px; font-weight: 600; }}
        QLabel#stepNumber {{ background: {selection}; color: {text}; border-radius: 13px;
                            font-weight: 700; }}
        QLabel#notice {{ background: {surface}; border: 1px solid {border};
                        border-left: 3px solid {accent}; border-radius: 6px; padding: 12px; }}
        QLabel#number {{ font-size: 28px; font-weight: 700; }}
        QFrame#card, QFrame#drop {{ background: {surface}; border: 1px solid {border};
                                 border-radius: 12px; }}
        QFrame#drop {{ border: 2px dashed {accent}; }}
        QFrame#drop[dragActive="true"] {{ background: {selection}; border-style: solid; }}
        QFrame#drop:disabled {{ border-color: {border}; }}
        QPushButton {{ background: {surface}; border: 1px solid {border};
                      border-radius: 7px; padding: 10px 14px; font-weight: 600; }}
        QPushButton:hover {{ background: {hover}; border-color: {accent}; }}
        QPushButton:focus {{ border: 2px solid {accent}; padding: 9px 13px; }}
        QLineEdit:focus {{ border: 1px solid {accent}; }}
        QPushButton:disabled {{ color: {muted}; background: {bg}; }}
        QPushButton#primary {{ background: {accent}; color: {bg}; border: 1px solid {accent}; }}
        QPushButton#primary:hover {{ background: {text}; }}
        QPushButton#primary:focus {{ border: 2px solid {text}; padding: 9px 13px; }}
        QPushButton#primary:disabled {{ background: {bg}; color: {muted};
                                       border-color: {border}; }}
        QPushButton:pressed {{ background: {selection}; }}
        QLineEdit, QComboBox {{ background: {surface}; border: 1px solid {border};
                              border-radius: 7px; padding: 10px; }}
        QTableView {{ background: {surface}; alternate-background-color: {bg};
                     border: 1px solid {border}; border-radius: 8px;
                     selection-background-color: {selection}; gridline-color: {border}; }}
        QTableView::item {{ padding: 8px; }}
        QTableView::item:selected {{ background: {selection}; color: {text}; }}
        QTableView::item:focus {{ border: 1px solid {accent}; }}
        QTableView:focus {{ border: 1px solid {accent}; }}
        QHeaderView::section {{ background: {surface}; border: none;
                              border-bottom: 1px solid {border}; padding: 12px;
                              font-weight: 600; }}
        QTabWidget::pane {{ border: none; }}
        QTabBar::tab {{ background: {bg}; padding: 12px 14px; color: {muted};
                        border-bottom: 3px solid transparent; }}
        QTabBar::tab:selected {{ color: {accent}; border-bottom-color: {accent}; }}
        QProgressBar {{ background: {surface}; border: none; border-radius: 4px; height: 6px; }}
        QTabBar::tab:hover {{ color: {text}; background: {hover}; }}
        QTabBar::tab:focus {{ border: 1px solid {accent}; }}
        QProgressBar#reciprocity {{ background: {border}; }}
        QProgressBar::chunk {{ background: {accent}; border-radius: 4px; }}
        QStatusBar {{ background: {bg}; color: {muted}; }}
    """.format(**colors)
    )
