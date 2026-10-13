from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DropArea(QFrame):
    selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("drop")
        self.setAcceptDrops(True)
        self.setAccessibleName("Área para arrastar um ZIP ou uma pasta de exportação")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        self.title = QLabel("↓  Arraste sua exportação para cá")
        self.title.setObjectName("sectionTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setWordWrap(True)
        layout.addWidget(self.title)
        label = QLabel("Arquivo ZIP ou pasta com os JSON extraídos")
        label.setObjectName("subtitle")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)
        buttons = QHBoxLayout()
        buttons.addStretch()
        file_button = QPushButton("Selecionar arquivo ZIP")
        file_button.setObjectName("primary")
        file_button.clicked.connect(self.choose_file)
        folder_button = QPushButton("Selecionar pasta")
        folder_button.clicked.connect(self.choose_folder)
        buttons.addWidget(file_button)
        buttons.addWidget(folder_button)
        buttons.addStretch()
        layout.addLayout(buttons)

    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar exportação", "", "Arquivo ZIP (*.zip)"
        )
        if path:
            self.selected.emit(path)

    def choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Selecionar pasta com os JSON extraídos")
        if path:
            self.selected.emit(path)

    def _accepts(self, event) -> bool:
        urls = event.mimeData().urls()
        if len(urls) != 1 or not urls[0].isLocalFile():
            return False
        path = Path(urls[0].toLocalFile())
        return path.is_dir() or path.suffix.lower() == ".zip"

    def _highlight(self, active: bool) -> None:
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.title.setText("Solte para analisar" if active else "↓  Arraste sua exportação para cá")

    def dragEnterEvent(self, event) -> None:
        if self.isEnabled() and self._accepts(event):
            self._highlight(True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self._highlight(False)
        event.accept()

    def dropEvent(self, event) -> None:
        self._highlight(False)
        if self.isEnabled() and self._accepts(event):
            event.acceptProposedAction()
            self.selected.emit(event.mimeData().urls()[0].toLocalFile())


class HomePage(QWidget):
    selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        self.content = QWidget()
        self.content.setMaximumWidth(820)
        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        outer.addStretch()
        outer.addWidget(self.content, 1)
        outer.addStretch()
        label = QLabel("CONEXÕES COM CLAREZA")
        label.setObjectName("eyebrow")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        title = QLabel("Descubra quem não te segue de volta")
        title.setObjectName("title")
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        subtitle = QLabel(
            "Compare sua exportação oficial com privacidade. "
            "Tudo é processado neste dispositivo, sem login e sem envio de dados."
        )
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        self.drop = DropArea()
        self.drop.selected.connect(self.selected)
        layout.addWidget(self.drop)
        self.activity = QLabel()
        self.activity.setWordWrap(True)
        self.activity.hide()
        layout.addWidget(self.activity)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)
        instructions = QFrame()
        instructions.setObjectName("card")
        steps = QVBoxLayout(instructions)
        steps.setContentsMargins(20, 16, 20, 16)
        steps.setSpacing(10)
        heading = QLabel("Prepare sua exportação")
        heading.setObjectName("sectionTitle")
        steps.addWidget(heading)
        for number, text in enumerate(
            [
                "Na Central de Contas, abra Suas informações e permissões "
                "e escolha exportar dados.",
                "Selecione sua conta e inclua Seguidores e seguindo.",
                "Escolha formato JSON e período Todo o tempo. "
                "Baixe o ZIP quando estiver disponível.",
            ],
            1,
        ):
            row = QHBoxLayout()
            badge = QLabel(str(number))
            badge.setObjectName("stepNumber")
            badge.setFixedSize(26, 26)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
            description = QLabel(text)
            description.setWordWrap(True)
            row.addWidget(description, 1)
            steps.addLayout(row)
        note = QLabel("Os nomes dos menus podem variar conforme a versão do Instagram.")
        note.setObjectName("subtitle")
        note.setWordWrap(True)
        steps.addWidget(note)
        layout.addWidget(instructions)
        privacy = QLabel("100% local  •  Sem telemetria  •  Dados apenas nesta sessão")
        privacy.setWordWrap(True)
        privacy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        privacy.setObjectName("eyebrow")
        layout.addWidget(privacy)
        layout.addStretch(1)

    def set_busy(self, busy: bool) -> None:
        self.drop.setEnabled(not busy)
        self.progress.setVisible(busy)
        self.activity.setVisible(busy)
        if not busy:
            self.activity.clear()
