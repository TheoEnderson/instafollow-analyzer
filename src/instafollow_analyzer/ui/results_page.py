from PySide6.QtCore import (
    QAbstractTableModel,
    QEvent,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    QUrl,
    Signal,
)
from PySide6.QtGui import QDesktopServices, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QBoxLayout,
    QFrame,
    QGridLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QLineEdit,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTabBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..core.exporter import CATEGORY_LABELS
from ..core.models import Analysis, profile_url


class UserModel(QAbstractTableModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.names: list[str] = []

    def set_names(self, names: frozenset[str]) -> None:
        self.beginResetModel()
        self.names = sorted(names)
        self.endResetModel()

    def rowCount(self, parent=None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self.names)

    def columnCount(self, parent=None) -> int:
        return 0 if parent is not None and parent.isValid() else 3

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        name = self.names[index.row()]
        if role == Qt.ItemDataRole.ToolTipRole:
            if name.startswith("_deleted_"):
                return (
                    "Identificador com prefixo _deleted_ preservado da exportação. "
                    "Isso não confirma exclusão nem atividade da conta.\n" + profile_url(name)
                )
            return profile_url(name)
        if role == Qt.ItemDataRole.DisplayRole:
            return (name, "Ver no Instagram ↗", "Copiar usuário")[index.column()]
        if role == Qt.ItemDataRole.ForegroundRole and index.column() == 1:
            return QApplication.palette().color(QPalette.ColorRole.Link)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return ("Nome de usuário", "Perfil", "Ações")[section]
        return None


class ResultsPage(QWidget):
    back = Signal()
    export_requested = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        self.analysis: Analysis | None = None
        self.keys = list(CATEGORY_LABELS)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(12)
        # O mínimo representa os controles reorganizados, não a soma de uma linha
        # larga. Isso permite reduzir a página e então recalcular as disposições.
        layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.top = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.title = QLabel("Suas conexões, em perspectiva")
        self.title.setWordWrap(True)
        self.title.setObjectName("title")
        self.top.addWidget(self.title, 1)
        self.back_button = QPushButton("Analisar outro arquivo")
        self.back_button.clicked.connect(self.back)
        self.top.addWidget(self.back_button)
        layout.addLayout(self.top)
        note = QLabel(
            "Retrato da exportação importada. Mudanças posteriores no Instagram não aparecem aqui."
        )
        note.setWordWrap(True)
        note.setObjectName("subtitle")
        layout.addWidget(note)
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(12)
        self.cards: list[QFrame] = []
        self.card_columns = 0
        self.counts: list[QLabel] = []
        for _i, label in enumerate(
            [
                "Seguidores",
                "Seguindo",
                "Não me seguem de volta",
                "Não sigo de volta",
                "Mútuos",
            ]
        ):
            card = QFrame()
            card.setObjectName("card")
            content = QVBoxLayout(card)
            content.setContentsMargins(16, 14, 16, 14)
            number = QLabel("0")
            number.setObjectName("number")
            description = QLabel(label)
            description.setWordWrap(True)
            description.setObjectName("subtitle")
            content.addWidget(number)
            content.addWidget(description)
            self.counts.append(number)
            self.cards.append(card)
        layout.addLayout(self.cards_layout)
        self.reflow_cards()
        self.reciprocity = QProgressBar()
        self.reciprocity.setObjectName("reciprocity")
        self.reciprocity.setRange(0, 1000)
        self.reciprocity.setTextVisible(False)
        self.reciprocity.setFixedHeight(8)
        self.reciprocity.setAccessibleName("Proporção de seguimentos mútuos entre quem você segue")
        self.reciprocity_label = QLabel()
        self.reciprocity_label.setObjectName("subtitle")
        self.reciprocity_label.setWordWrap(True)
        layout.addWidget(self.reciprocity_label)
        layout.addWidget(self.reciprocity)
        self.deleted_notice = QLabel()
        self.deleted_notice.setObjectName("notice")
        self.deleted_notice.setWordWrap(True)
        self.deleted_notice.hide()
        layout.addWidget(self.deleted_notice)
        self.tabs = QTabBar()
        self.tabs.setExpanding(False)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideNone)
        for label in CATEGORY_LABELS.values():
            self.tabs.addTab(label)
        self.tabs.currentChanged.connect(self.refresh_category)
        layout.addWidget(self.tabs)
        self.toolbar = QGridLayout()
        self.toolbar.setSpacing(12)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Pesquisar nome de usuário…")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Pesquisar usuários da categoria atual")

        self.export_button = QPushButton("Exportar categoria")
        self.export_button.clicked.connect(lambda: self.export_requested.emit(False))

        self.export_all_button = QPushButton("Exportar tudo")
        self.export_all_button.setObjectName("primary")
        self.export_all_button.clicked.connect(lambda: self.export_requested.emit(True))
        layout.addLayout(self.toolbar)
        self.model = UserModel(self)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterKeyColumn(0)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search.textChanged.connect(self.proxy.setFilterFixedString)
        self.search.textChanged.connect(self.update_count)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setAccessibleName("Usuários e links de perfis")
        self.table.setToolTip("Duplo clique no nome ou Enter para abrir o perfil selecionado.")
        self.open_shortcut = QShortcut(QKeySequence("Return"), self.table)
        self.open_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.open_shortcut.activated.connect(self.open_profile)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setMinimumSectionSize(110)
        self.table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.table.setMinimumHeight(180)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.clicked.connect(self.on_clicked)
        self.table.doubleClicked.connect(
            lambda index: self.open_profile() if index.column() == 0 else None
        )
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context_menu)
        self.empty_state = QFrame()
        self.empty_state.setObjectName("card")
        self.empty_state.setMinimumHeight(180)
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.addStretch()
        self.empty_title = QLabel()
        self.empty_title.setObjectName("sectionTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_title.setWordWrap(True)
        empty_layout.addWidget(self.empty_title)
        self.empty_description = QLabel()
        self.empty_description.setObjectName("subtitle")
        self.empty_description.setWordWrap(True)
        self.empty_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_description)
        self.clear_search = QPushButton("Limpar pesquisa")
        self.clear_search.clicked.connect(self.search.clear)
        empty_layout.addWidget(self.clear_search, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch()
        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty_state, 1)
        self.empty_state.hide()
        self.bottom = QGridLayout()
        self.bottom.setSpacing(10)
        self.visible_count = QLabel()
        self.visible_count.setObjectName("subtitle")

        self.copy_name = QPushButton("Copiar usuário")
        self.copy_link = QPushButton("Copiar link")
        self.open_button = QPushButton("Abrir perfil ↗")
        self.copy_name.clicked.connect(lambda: self.copy(False))
        self.copy_link.clicked.connect(lambda: self.copy(True))
        self.open_button.clicked.connect(self.open_profile)
        for button in (self.copy_name, self.copy_link, self.open_button):
            button.setEnabled(False)

        self.table.selectionModel().selectionChanged.connect(self.update_actions)
        layout.addLayout(self.bottom)
        self.compact = None
        self.reflow_controls()
        footer = QLabel(
            "A exportação inclui a categoria inteira, mesmo com busca. "
            "O JSON não confirma atividade da conta. Abrir perfil usa o navegador."
        )
        footer.setWordWrap(True)
        footer.setObjectName("subtitle")
        layout.addWidget(footer)
        for label in self.findChildren(QLabel):
            if label.wordWrap():
                policy = label.sizePolicy()
                policy.setHorizontalPolicy(QSizePolicy.Policy.Ignored)
                label.setSizePolicy(policy)

    @staticmethod
    def control_width(widget) -> int:
        return max(
            widget.minimumWidth(), widget.minimumSizeHint().width(), widget.sizeHint().width()
        )

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        if hasattr(self, "compact"):
            controls = (
                self.back_button,
                self.export_button,
                self.export_all_button,
                self.copy_name,
                self.copy_link,
                self.open_button,
                self.visible_count,
                self.search,
                self.tabs,
                self.table,
                self.empty_state,
                self.reciprocity,
                *self.cards,
            )
            width = max(
                max(widget.minimumWidth(), widget.minimumSizeHint().width()) for widget in controls
            )
            margins = self.layout().contentsMargins()
            hint.setWidth(width + margins.left() + margins.right())
        return hint

    def event(self, event) -> bool:
        result = super().event(event)
        if hasattr(self, "compact") and event.type() in (
            QEvent.Type.LayoutRequest,
            QEvent.Type.FontChange,
            QEvent.Type.StyleChange,
        ):
            self.reflow_cards()
            self.reflow_controls()
        return result

    @property
    def category(self) -> str:
        return self.keys[self.tabs.currentIndex()]

    def set_analysis(self, analysis: Analysis | None) -> None:
        self.analysis = analysis
        self.search.clear()
        if analysis:
            groups = [
                analysis.followers,
                analysis.following,
                analysis.not_following_back,
                analysis.not_followed_back,
                analysis.mutual,
            ]
            for label, group in zip(self.counts, groups, strict=True):
                label.setText(f"{len(group):,}".replace(",", "."))
            self.tabs.setCurrentIndex(0)
        following = len(analysis.following) if analysis else 0
        mutual = len(analysis.mutual) if analysis else 0
        self.reciprocity.setValue(round(mutual / following * 1000) if following else 0)
        self.reciprocity.setVisible(bool(following))
        if following:
            percent = f"{mutual / following:.0%}"
            self.reciprocity_label.setText(
                f"Entre quem você segue: {percent} mútuos ({mutual}) · "
                f"{following - mutual} não seguem de volta"
            )
        else:
            self.reciprocity_label.setText("Sem perfis seguidos para calcular a reciprocidade.")
        identifiers = analysis.followers | analysis.following if analysis else frozenset()
        deleted = sum(name.startswith("_deleted_") for name in identifiers)
        self.deleted_notice.setVisible(bool(deleted))
        self.deleted_notice.setText(
            f"{deleted} identificador(es) com prefixo _deleted_ na exportação. "
            "Eles foram preservados nos totais e resultados; o prefixo não comprova "
            "exclusão nem atividade da conta."
        )
        if not analysis:
            for label in self.counts:
                label.setText("0")
        self.refresh_category()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.reflow_cards()
        if hasattr(self, "compact"):
            self.reflow_controls()

    def reflow_controls(self) -> None:
        available = self.layout().contentsRect().width()
        exports = (self.export_button, self.export_all_button)
        actions = (self.copy_name, self.copy_link, self.open_button)
        export_width = (
            sum(self.control_width(button) for button in exports) + self.toolbar.spacing()
        )
        action_width = (
            sum(self.control_width(button) for button in actions) + 2 * self.bottom.spacing()
        )
        compact = (
            self.width() < 900
            or self.control_width(self.search) + export_width + self.toolbar.spacing() > available
            or self.control_width(self.visible_count) + action_width + self.bottom.spacing()
            > available
        )
        export_columns = 2 if export_width <= available else 1
        action_columns = 3 if action_width <= available else 1
        self.top.setDirection(
            QBoxLayout.Direction.LeftToRight
            if self.title.minimumSizeHint().width()
            + self.control_width(self.back_button)
            + self.top.spacing()
            <= available
            else QBoxLayout.Direction.TopToBottom
        )
        state = (compact, export_columns, action_columns)
        if state == self.compact:
            return
        self.compact = state
        for grid in (self.toolbar, self.bottom):
            while grid.count():
                grid.takeAt(0)
            for column in range(4):
                grid.setColumnStretch(column, 0)
        if compact:
            self.toolbar.addWidget(self.search, 0, 0, 1, export_columns)
            for index, button in enumerate(exports):
                self.toolbar.addWidget(button, 1 + index // export_columns, index % export_columns)
            self.bottom.addWidget(self.visible_count, 0, 0, 1, action_columns)
            for index, button in enumerate(actions):
                self.bottom.addWidget(button, 1 + index // action_columns, index % action_columns)
        else:
            self.toolbar.addWidget(self.search, 0, 0)
            self.toolbar.addWidget(self.export_button, 0, 1)
            self.toolbar.addWidget(self.export_all_button, 0, 2)
            self.toolbar.setColumnStretch(0, 1)
            self.bottom.addWidget(self.visible_count, 0, 0)
            self.bottom.setColumnStretch(0, 1)
            for column, button in enumerate((self.copy_name, self.copy_link, self.open_button), 1):
                self.bottom.addWidget(button, 0, column)
        self.updateGeometry()

    def reflow_cards(self) -> None:
        columns = 5 if self.width() >= 1050 else 3 if self.width() >= 760 else 2
        available = self.layout().contentsRect().width()
        minimum = max(
            max(card.minimumWidth(), card.minimumSizeHint().width()) for card in self.cards
        )
        spacing = self.cards_layout.spacing()
        columns = min(columns, max(1, (available + spacing) // (minimum + spacing)))
        if columns == self.card_columns:
            return
        for column in range(5):
            self.cards_layout.setColumnStretch(column, 1 if column < columns else 0)
        for index, card in enumerate(self.cards):
            self.cards_layout.addWidget(card, index // columns, index % columns)
        self.card_columns = columns
        self.updateGeometry()

    def refresh_category(self, *_args) -> None:
        names = self.analysis.categories()[self.category] if self.analysis else frozenset()
        self.model.set_names(names)
        self.update_count()
        self.update_actions()

    def update_count(self, *_args) -> None:
        count = self.proxy.rowCount()
        self.visible_count.setText(f"{count} de {self.model.rowCount()} perfis")
        self.table.setVisible(bool(count))
        self.empty_state.setVisible(not count)
        searching = bool(self.search.text())
        self.empty_title.setText(
            "Nenhum usuário encontrado" if searching else "Nenhum perfil nesta categoria"
        )
        self.empty_description.setText(
            "Tente parte do nome de usuário ou limpe a pesquisa."
            if searching
            else "A exportação importada não contém relações deste tipo."
        )
        self.clear_search.setVisible(searching)
        self.update_actions()

    def selected_name(self) -> str | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        return self.model.names[self.proxy.mapToSource(rows[0]).row()]

    def update_actions(self, *_args) -> None:
        enabled = self.selected_name() is not None
        for button in (self.copy_name, self.copy_link, self.open_button):
            button.setEnabled(enabled)

    def copy(self, link: bool) -> None:
        name = self.selected_name()
        if name:
            QApplication.clipboard().setText(profile_url(name) if link else name)
            self.visible_count.setText("Link copiado." if link else "Nome de usuário copiado.")

    def open_profile(self) -> None:
        name = self.selected_name()
        if name and not QDesktopServices.openUrl(QUrl(profile_url(name))):
            QMessageBox.warning(
                self, "Navegador indisponível", "Não foi possível abrir o navegador."
            )

    def on_clicked(self, index: QModelIndex) -> None:
        if index.column() == 1:
            self.open_profile()
        elif index.column() == 2:
            self.copy(False)

    def context_menu(self, position) -> None:
        index = self.table.indexAt(position)
        if not index.isValid():
            return
        self.table.selectRow(index.row())
        menu = QMenu(self)
        menu.addAction("Copiar usuário", lambda: self.copy(False))
        menu.addAction("Copiar link", lambda: self.copy(True))
        menu.addAction("Abrir perfil no navegador", self.open_profile)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def set_busy(self, busy: bool) -> None:
        for button in (self.back_button, self.export_button, self.export_all_button):
            button.setEnabled(not busy)
