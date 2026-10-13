from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.analyzer import analyze
from ..core.exporter import export_all, export_category
from ..core.models import Analysis, DataError
from ..core.parser import load_export
from .home_page import HomePage
from .results_page import ResultsPage
from .theme import apply_theme


class Task(QThread):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, operation: Callable, parent=None) -> None:
        super().__init__(parent)
        self.operation = operation

    def run(self) -> None:
        try:
            self.completed.emit(self.operation(self.progress.emit))
        except DataError as exc:
            self.failed.emit(str(exc))
        except Exception:
            # Não registrar exceções que possam conter nomes ou conteúdo dos dados.
            self.failed.emit(
                "Não foi possível concluir a operação. Verifique o arquivo e tente novamente."
            )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("InstaFollow Analyzer")
        self.resize(1180, 820)
        self.setMinimumSize(640, 560)
        self.task: Task | None = None
        self.dark = True
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QHBoxLayout()
        header.setContentsMargins(30, 18, 30, 10)
        brand = QLabel("◈  InstaFollow Analyzer")
        brand.setObjectName("eyebrow")
        brand.setWordWrap(True)
        header.addWidget(brand, 1)
        about = QPushButton("Sobre e privacidade")
        about.clicked.connect(self.show_about)
        header.addWidget(about)
        self.theme_button = QPushButton("Tema claro")
        self.theme_button.clicked.connect(self.toggle_theme)
        header.addWidget(self.theme_button)
        layout.addLayout(header)
        self.pages = QStackedWidget()
        self.home = HomePage()
        self.results = ResultsPage()
        for page in (self.home, self.results):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setWidget(page)
            self.pages.addWidget(scroll)
        layout.addWidget(self.pages)
        self.setCentralWidget(root)
        self.home.selected.connect(self.import_source)
        self.results.back.connect(self.go_home)
        self.results.export_requested.connect(self.export_results)
        self.statusBar().showMessage("Pronto • Seus dados são processados neste dispositivo.")
        apply_theme(QApplication.instance(), self.dark)

    def toggle_theme(self) -> None:
        self.dark = not self.dark
        apply_theme(QApplication.instance(), self.dark)
        self.theme_button.setText("Tema claro" if self.dark else "Tema escuro")

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "Sobre o InstaFollow Analyzer",
            "InstaFollow Analyzer 0.1.0\n\n"
            "Análise de exportações oficiais, inteiramente neste dispositivo.\n"
            "Sem login, telemetria, scraping ou automação. Nenhum dado importado é salvo "
            "automaticamente. Exportações e cópias para a área de transferência dependem "
            "de sua ação. Abrir um perfil acessa o Instagram pelo navegador.\n\n"
            "Projeto independente, sem vínculo com a Meta ou o Instagram.\n"
            "Código: MIT. PySide6/Qt: licenças próprias, incluindo LGPLv3. "
            "Consulte THIRD_PARTY_NOTICES.md e as licenças incluídas na distribuição.",
        )

    def start_task(self, operation: Callable, completed: Callable) -> None:
        if self.task is not None:
            return
        self.home.set_busy(True)
        self.results.set_busy(True)
        task = Task(operation, self)
        self.task = task
        task.progress.connect(self.show_progress)
        task.completed.connect(completed)
        task.failed.connect(self.show_error)
        task.finished.connect(self.task_finished)
        task.start()

    def show_progress(self, message: str) -> None:
        self.home.activity.setText(message)
        self.statusBar().showMessage(message)

    def task_finished(self) -> None:
        task = self.task
        self.task = None
        self.home.set_busy(False)
        self.results.set_busy(False)
        if task:
            task.deleteLater()

    def show_error(self, message: str) -> None:
        self.statusBar().showMessage("A operação não foi concluída.")
        QMessageBox.warning(self, "Não foi possível concluir", message)

    def import_source(self, source: str) -> None:
        if self.task is not None:
            return
        self.start_task(
            lambda progress: analyze(load_export(source, progress=progress)), self.show_results
        )

    def show_results(self, analysis: Analysis) -> None:
        self.results.set_analysis(analysis)
        self.pages.setCurrentIndex(1)
        self.statusBar().showMessage("Análise concluída • Nenhum dado foi salvo automaticamente.")

    def go_home(self) -> None:
        if self.task is not None:
            return
        self.results.set_analysis(None)
        self.pages.setCurrentIndex(0)
        self.statusBar().showMessage("Sessão limpa. Selecione uma nova exportação.")

    def export_results(self, all_categories: bool) -> None:
        analysis = self.results.analysis
        if self.task is not None or analysis is None:
            return
        category = self.results.category
        stem = "todos_resultados" if all_categories else category
        destination, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Exportar resultados",
            stem + ".csv",
            "CSV (*.csv);;Texto (*.txt)",
        )
        if not destination:
            return
        if not Path(destination).suffix:
            destination += ".txt" if "*.txt" in selected_filter else ".csv"
        self.show_progress("Salvando resultados…")
        self.start_task(
            lambda _: (
                export_all(analysis, destination)
                if all_categories
                else export_category(analysis, category, destination)
            ),
            lambda count: self.statusBar().showMessage(
                f"Exportação concluída: {count} perfis salvos."
            ),
        )

    def closeEvent(self, event) -> None:
        if self.task is not None:
            event.ignore()
            self.statusBar().showMessage(
                "Aguarde a operação terminar antes de fechar o aplicativo."
            )
        else:
            event.accept()
