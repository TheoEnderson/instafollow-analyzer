"""Integração Qt offscreen: sinais, importação assíncrona, filtros e exportação."""

import time
from pathlib import Path

import pytest
from PySide6.QtCore import QEventLoop, Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QPushButton

from instafollow_analyzer.ui.main_window import MainWindow


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    yield application


def wait_until(app, condition):
    deadline = time.monotonic() + 10
    while not condition():
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 20)
        time.sleep(0.005)
        assert time.monotonic() < deadline, "Operação Qt não terminou"
    app.processEvents()


def results_layout_diagnostics(scroll, results):
    components = {
        "page": results,
        "top": results.top,
        "title": results.title,
        "cards": results.cards_layout,
        "reciprocity": results.reciprocity,
        "reciprocity_label": results.reciprocity_label,
        "notice": results.deleted_notice,
        "tabs": results.tabs,
        "search": results.search,
        "toolbar": results.toolbar,
        "table": results.table,
        "empty_state": results.empty_state,
        "bottom": results.bottom,
        "back": results.back_button,
        "export": results.export_button,
        "export_all": results.export_all_button,
        "copy_name": results.copy_name,
        "copy_link": results.copy_link,
        "open": results.open_button,
        **{f"card_{index}": card for index, card in enumerate(results.cards)},
    }
    metrics = {}
    for name, item in components.items():
        metrics[name] = {
            "geometry": item.geometry().getRect(),
            "minimum_hint": (
                item.minimumSizeHint() if hasattr(item, "minimumSizeHint") else item.minimumSize()
            ).toTuple(),
            "hint": item.sizeHint().toTuple(),
        }
        if hasattr(item, "sizePolicy"):
            metrics[name]["minimum_width"] = item.minimumWidth()
            metrics[name]["policy"] = str(item.sizePolicy().horizontalPolicy())
    return str(
        {
            "viewport": scroll.viewport().size().toTuple(),
            "scroll": scroll.horizontalScrollBar().maximum(),
            "components": metrics,
        }
    )


def test_async_import_search_sort_copy_export_and_reset(
    app,
    make_export,
    export_data,
    tmp_path,
    monkeypatch,
):
    window = MainWindow()
    window.show()
    try:
        window.import_source(str(make_export(export_data)))
        assert window.task is not None
        assert not window.home.drop.isEnabled()
        wait_until(app, lambda: window.task is None)
        assert window.pages.currentIndex() == 1
        assert [label.text() for label in window.results.counts] == ["3", "2", "1", "2", "1"]
        results = window.results
        results.tabs.setCurrentIndex(1)
        assert results.proxy.rowCount() == 2
        results.search.setText("BO")
        assert results.proxy.rowCount() == 1
        results.table.selectRow(0)
        results.copy(False)
        assert app.clipboard().text() == "bob"
        results.copy(True)
        assert app.clipboard().text() == "https://www.instagram.com/bob/"
        results.search.clear()
        results.table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
        assert results.proxy.index(0, 0).data() == "carol"
        results.search.setText("no_match")
        assert results.proxy.rowCount() == 0
        assert not results.open_button.isEnabled()
        destination = tmp_path / "ui.csv"
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(destination), "CSV"))
        window.export_results(False)
        wait_until(app, lambda: window.task is None)
        assert "bob" in destination.read_text(encoding="utf-8-sig")
        assert "carol" in destination.read_text(encoding="utf-8-sig")
        window.toggle_theme()
        assert not window.dark
        window.go_home()
        assert window.pages.currentIndex() == 0
        assert window.results.analysis is None
        assert window.results.model.rowCount() == 0
    finally:
        if window.task:
            wait_until(app, lambda: window.task is None)
        window.close()


def test_invalid_import_shows_friendly_message(app, tmp_path, monkeypatch):
    errors = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: errors.append(args[-1]))
    window = MainWindow()
    try:
        window.import_source(str(tmp_path / "missing.zip"))
        wait_until(app, lambda: window.task is None)
        assert errors and "Selecione" in errors[0]
        assert window.pages.currentIndex() == 0
        assert window.home.drop.isEnabled()
    finally:
        window.close()


@pytest.mark.parametrize("size", [(640, 560), (820, 620), (1180, 820), (1920, 1080)])
@pytest.mark.parametrize("dark", [True, False])
def test_layouts_fit_viewport_and_controls_remain_reachable(app, size, dark):
    from instafollow_analyzer.core.analyzer import analyze
    from instafollow_analyzer.core.models import Relationships

    window = MainWindow()
    window.resize(*size)
    window.show()
    try:
        if window.dark != dark:
            window.toggle_theme()
        app.processEvents()
        assert window.home.content.width() <= 820
        home_scroll = window.pages.widget(0)
        assert home_scroll.horizontalScrollBar().maximum() == 0, (
            f"viewport={home_scroll.viewport().width()}, "
            f"page_min={window.home.minimumSizeHint().width()}, "
            f"content_min={window.home.content.minimumSizeHint().width()}, "
            f"drop_min={window.home.drop.minimumSizeHint().width()}"
        )
        for button in window.home.drop.findChildren(QPushButton):
            assert button.width() >= button.minimumSizeHint().width()
            point = button.mapTo(home_scroll.widget(), button.rect().topLeft())
            assert point.x() >= 0
            assert point.x() + button.width() <= home_scroll.viewport().width()
            home_scroll.ensureWidgetVisible(button)
            app.processEvents()
            assert button.visibleRegion().boundingRect().height() == button.height()
        window.show_results(
            analyze(
                Relationships(
                    frozenset({"_deleted_demo", "ana_demo"}),
                    frozenset({"_deleted_demo", "bruno_demo"}),
                )
            )
        )
        app.processEvents()
        results = window.results
        scroll = window.pages.widget(1)
        assert scroll.horizontalScrollBar().maximum() == 0, results_layout_diagnostics(
            scroll, results
        )
        for button in (
            results.back_button,
            results.export_button,
            results.export_all_button,
            results.copy_name,
            results.copy_link,
            results.open_button,
        ):
            assert button.width() >= button.minimumSizeHint().width()
            point = button.mapTo(scroll.widget(), button.rect().topLeft())
            assert point.x() >= 0
            assert point.x() + button.width() <= scroll.widget().width()
        # Cada parte da página é alcançável pela rolagem vertical, sem corte horizontal.
        scroll.ensureWidgetVisible(results.open_button)
        app.processEvents()
        assert results.open_button.visibleRegion().boundingRect().height() > 0
        window.resize(1180, 820)
        app.processEvents()
        window.resize(*size)
        app.processEvents()
        assert scroll.horizontalScrollBar().maximum() == 0, results_layout_diagnostics(
            scroll, results
        )
        assert results.cards_layout.count() == 5
    finally:
        window.close()


@pytest.mark.parametrize("dark", [True, False])
def test_results_reflow_wide_controls_without_outer_scroll(app, dark):
    from PySide6.QtTest import QTest

    from instafollow_analyzer.core.analyzer import analyze
    from instafollow_analyzer.core.models import Relationships

    window = MainWindow()
    if window.dark != dark:
        window.toggle_theme()
    results = window.results
    actions = (results.copy_name, results.copy_link, results.open_button)
    # Linha inferior antiga: 213 + 213 + 212 + 20 + 48 = 706 px,
    # ou 80 px além do viewport de 626. Exercitar também outros grupos largos.
    for button, width in zip(actions, (213, 213, 212), strict=True):
        button.setMinimumWidth(width)
    for button in (results.export_button, results.export_all_button):
        button.setMinimumWidth(300)
    for card in results.cards:
        card.setMinimumWidth(300)
    results.table.horizontalHeader().setMinimumSectionSize(240)
    window.show()
    window.show_results(
        analyze(
            Relationships(
                frozenset({"_deleted_demo", "ana_demo"}), frozenset({"_deleted_demo", "bruno_demo"})
            )
        )
    )
    try:
        for size in [(1920, 1080), (640, 560), (820, 620), (1180, 820), (1920, 1080), (640, 560)]:
            window.resize(*size)
            for _ in range(5):
                app.processEvents()
            scroll = window.pages.widget(1)
            diagnostic = results_layout_diagnostics(scroll, results)
            assert scroll.horizontalScrollBar().maximum() == 0, diagnostic
            assert results.minimumSizeHint().width() <= scroll.viewport().width(), diagnostic
            assert results.cards_layout.count() == 5
            bounds = results.layout().contentsRect()
            for card in results.cards:
                assert card.width() >= card.minimumWidth()
                assert bounds.contains(card.geometry()), diagnostic
            controls = (
                results.back_button,
                results.export_button,
                results.export_all_button,
                *actions,
            )
            for button in controls:
                assert button.width() >= max(
                    button.minimumWidth(), button.minimumSizeHint().width()
                ), diagnostic
                assert button.height() >= button.minimumSizeHint().height(), diagnostic
                assert bounds.contains(button.geometry()), diagnostic
                scroll.ensureWidgetVisible(button)
                app.processEvents()
                assert button.visibleRegion().boundingRect().height() == button.height(), diagnostic
            assert bounds.contains(results.search.geometry()), diagnostic
            if size[0] == 640:
                assert results.export_button.geometry().bottom() < results.export_all_button.y()
                assert results.copy_name.geometry().bottom() < results.copy_link.y()
                assert results.copy_link.geometry().bottom() < results.open_button.y()
                assert results.card_columns == 1
                assert results.table.horizontalScrollBar().maximum() > 0
            if size[0] == 1920:
                assert results.card_columns == 5
                assert results.export_button.y() == results.export_all_button.y()
                assert results.copy_name.y() == results.copy_link.y() == results.open_button.y()
            scroll.ensureWidgetVisible(results.tabs)
            results.tabs.setFocus()
            results.tabs.setCurrentIndex(0)
            for index in (1, 2):
                QTest.keyClick(results.tabs, Qt.Key.Key_Right)
                app.processEvents()
                assert results.tabs.currentIndex() == index
                assert results.tabs.rect().contains(results.tabs.tabRect(index)), diagnostic
    finally:
        window.close()


@pytest.mark.parametrize("dark", [True, False])
def test_import_buttons_reflow_with_wide_minima_and_back(app, dark):
    from PySide6.QtWidgets import QBoxLayout

    window = MainWindow()
    if window.dark != dark:
        window.toggle_theme()
    drop = window.home.drop
    # Reproduz no Linux os 656 px da linha observada no CI Windows:
    # 296 + 296 + 12 de espaçamento + 48 de margens + 4 de bordas.
    # Somente a fixture impõe larguras; a interface usa as métricas reais dos botões.
    for button in (drop.file_button, drop.folder_button):
        button.setMinimumWidth(296)
    window.show()
    try:
        for size in [(640, 560), (820, 620), (1180, 820), (1920, 1080), (640, 560)]:
            window.resize(*size)
            # A reorganização produz LayoutRequests também nos layouts ancestrais.
            for _ in range(5):
                app.processEvents()
            scroll = window.pages.widget(0)
            assert scroll.horizontalScrollBar().maximum() == 0
            assert window.home.minimumSizeHint().width() <= scroll.viewport().width()
            assert drop.minimumSizeHint().width() <= drop.width()
            assert window.home.content.width() <= 820
            content_center = window.home.content.mapTo(
                scroll.widget(), window.home.content.rect().center()
            )
            assert abs(content_center.x() - scroll.viewport().rect().center().x()) <= 1
            if size[0] == 640:
                assert drop.buttons.direction() == QBoxLayout.Direction.TopToBottom
                assert drop.file_button.geometry().bottom() < drop.folder_button.geometry().top()
            else:
                assert drop.buttons.direction() == QBoxLayout.Direction.LeftToRight
                assert drop.file_button.y() == drop.folder_button.y()
            for button in (drop.file_button, drop.folder_button):
                assert button.width() >= max(296, button.minimumSizeHint().width())
                assert button.height() >= button.minimumSizeHint().height()
                assert drop.layout().contentsRect().contains(button.geometry())
                scroll.ensureWidgetVisible(button)
                app.processEvents()
                assert button.visibleRegion().boundingRect().height() == button.height()
    finally:
        window.close()


def test_empty_state_selection_actions_and_double_click(app, make_export, export_data, monkeypatch):
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtTest import QTest

    opened = []
    monkeypatch.setattr(
        QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True
    )
    window = MainWindow()
    window.show()
    try:
        window.import_source(str(make_export(export_data)))
        wait_until(app, lambda: window.task is None)
        results = window.results
        buttons = (results.copy_name, results.copy_link, results.open_button)
        assert all(not button.isEnabled() for button in buttons)
        index = results.proxy.index(0, 0)
        position = results.table.visualRect(index).center()
        QTest.mouseClick(results.table.viewport(), Qt.MouseButton.LeftButton, pos=position)
        QTest.mouseDClick(results.table.viewport(), Qt.MouseButton.LeftButton, pos=position)
        assert opened == ["https://www.instagram.com/dave/"]
        results.table.setFocus()
        app.processEvents()
        QTest.keyClick(results.table, Qt.Key.Key_Return)
        assert opened == ["https://www.instagram.com/dave/"] * 2
        assert all(button.isEnabled() for button in buttons)
        results.search.setText("sem_correspondencia")
        app.processEvents()
        assert all(not button.isEnabled() for button in buttons)
        assert results.empty_state.isVisible()
        assert results.empty_title.text() == "Nenhum usuário encontrado"
        results.clear_search.click()
        assert results.table.isVisible()
        assert not results.empty_state.isVisible()
        results.table.clearSelection()
        assert all(not button.isEnabled() for button in buttons)
    finally:
        window.close()


def test_deleted_identifiers_preserved_with_cautious_explanation(app, make_export, tmp_path):
    from instafollow_analyzer.core.analyzer import analyze
    from instafollow_analyzer.core.exporter import export_all
    from instafollow_analyzer.core.parser import load_export

    from .conftest import records

    result = analyze(
        load_export(
            make_export(
                {
                    "followers_1.json": records("_deleted_demo", "ana_demo"),
                    "following.json": {
                        "relationships_following": records("_deleted_demo", "bruno_demo")
                    },
                }
            )
        )
    )
    assert "_deleted_demo" in result.mutual
    destination = tmp_path / "ficticio.csv"
    export_all(result, destination)
    assert "_deleted_demo" in destination.read_text(encoding="utf-8-sig")
    window = MainWindow()
    window.show()
    try:
        window.show_results(result)
        app.processEvents()
        results = window.results
        assert results.deleted_notice.isVisible()
        assert "não comprova" in results.deleted_notice.text()
        assert results.reciprocity.value() == 500
        assert "50%" in results.reciprocity_label.text()
        results.tabs.setCurrentIndex(2)
        assert results.proxy.index(0, 0).data() == "_deleted_demo"
        assert "não confirma" in results.proxy.index(0, 0).data(Qt.ItemDataRole.ToolTipRole)
        assert results.proxy.index(0, 1).data() == "Ver no Instagram ↗"
        assert "https://www.instagram.com/_deleted_demo/" in results.proxy.index(0, 1).data(
            Qt.ItemDataRole.ToolTipRole
        )
    finally:
        window.close()


def test_empty_category_has_no_meaningless_proportion(app):
    from instafollow_analyzer.core.analyzer import analyze
    from instafollow_analyzer.core.models import Relationships

    window = MainWindow()
    window.show()
    try:
        window.show_results(analyze(Relationships(frozenset(), frozenset())))
        assert not window.results.reciprocity.isVisible()
        assert window.results.empty_state.isVisible()
        assert not window.results.clear_search.isVisible()
        assert "categoria" in window.results.empty_title.text()
    finally:
        window.close()


@pytest.mark.parametrize("dark", [True, False])
def test_theme_text_contrast(app, dark):
    from PySide6.QtGui import QPalette

    from instafollow_analyzer.ui.theme import apply_theme

    def luminance(color):
        channels = [color.redF(), color.greenF(), color.blueF()]
        linear = [
            channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return sum(
            component * weight
            for component, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True)
        )

    apply_theme(app, dark)
    palette = app.palette()
    for foreground, background in [
        (QPalette.ColorRole.WindowText, QPalette.ColorRole.Window),
        (QPalette.ColorRole.Text, QPalette.ColorRole.Base),
        (QPalette.ColorRole.HighlightedText, QPalette.ColorRole.Highlight),
        (QPalette.ColorRole.PlaceholderText, QPalette.ColorRole.Base),
    ]:
        values = sorted(
            [luminance(palette.color(foreground)), luminance(palette.color(background))]
        )
        assert (values[1] + 0.05) / (values[0] + 0.05) >= 4.5


def test_drop_area_highlights_only_supported_local_inputs(app, tmp_path):
    from PySide6.QtCore import QMimeData, QPoint, QPointF, QUrl, qVersion
    from PySide6.QtGui import QDragEnterEvent, QDropEvent

    from instafollow_analyzer.ui.home_page import DropArea

    # Qt 6.12 usa QPointF; manter o construtor antigo para Qt 6.8–6.11.
    point_type = QPointF if tuple(map(int, qVersion().split("."))) >= (6, 12) else QPoint
    area = DropArea()
    selected = []
    area.selected.connect(selected.append)
    area.show()
    try:
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(tmp_path / "ficticio.zip"))])
        enter = QDragEnterEvent(
            point_type(10, 10),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        app.sendEvent(area, enter)
        assert enter.isAccepted()
        assert area.property("dragActive")
        drop = QDropEvent(
            QPointF(10, 10),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        app.sendEvent(area, drop)
        assert [Path(path) for path in selected] == [tmp_path / "ficticio.zip"]
        assert not area.property("dragActive")
        invalid = QMimeData()
        invalid.setUrls([QUrl("https://example.invalid/export.zip")])
        invalid_enter = QDragEnterEvent(
            point_type(10, 10),
            Qt.DropAction.CopyAction,
            invalid,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        app.sendEvent(area, invalid_enter)
        assert not invalid_enter.isAccepted()
        assert len(selected) == 1
    finally:
        area.close()
