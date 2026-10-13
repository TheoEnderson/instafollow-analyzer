"""Captura a interface real com dados fictícios, sem usar exportações pessoais."""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from instafollow_analyzer.core.analyzer import analyze  # noqa: E402
from instafollow_analyzer.core.models import Relationships  # noqa: E402
from instafollow_analyzer.ui.main_window import MainWindow  # noqa: E402


def main() -> None:
    app = QApplication([])
    window = MainWindow()
    window.show()
    destination = Path(__file__).resolve().parents[1] / "assets"
    destination.mkdir(exist_ok=True)
    app.processEvents()
    window.grab().save(str(destination / "home-dark.png"))
    window.show_results(
        analyze(
            Relationships(
                frozenset({"ana.exemplo", "bruno_demo", "clara.demo", "daniel_demo"}),
                frozenset(
                    {"ana.exemplo", "clara.demo", "estudio_demo", "fotografia_demo", "jardim_demo"}
                ),
            )
        )
    )
    window.results.table.selectRow(0)
    app.processEvents()
    window.grab().save(str(destination / "results-dark.png"))
    window.toggle_theme()
    app.processEvents()
    window.grab().save(str(destination / "results-light.png"))
    window.close()


if __name__ == "__main__":
    main()
