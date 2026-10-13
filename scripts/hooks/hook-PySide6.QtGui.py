"""Exclui plugins PDF/teclado virtual desnecessários antes de resolver bibliotecas."""

from pathlib import Path

from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
excluded = {"qpdf", "libqpdf", "qtvirtualkeyboardplugin", "libqtvirtualkeyboardplugin"}
binaries = [
    (source, target) for source, target in binaries if Path(source).stem.lower() not in excluded
]
