"""Exportações atômicas em UTF-8: só persistem por solicitação explícita."""

import csv
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

from .models import Analysis, DataError, profile_url
from .parser import normalize_username

CATEGORY_LABELS = {
    "nao_me_seguem_de_volta": "Não me seguem de volta",
    "nao_sigo_de_volta": "Não sigo de volta",
    "seguimento_mutuo": "Seguimento mútuo",
}


def export_rows(rows: Iterable[tuple[str, str]], destination: str | Path) -> int:
    """Grava categoria, usuário e URL; substitui o destino só após concluir a escrita."""
    path = Path(destination)
    extension = path.suffix.lower()
    if extension not in {".txt", ".csv"}:
        raise DataError("Escolha um nome de arquivo terminado em .txt ou .csv.")
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig" if extension == ".csv" else "utf-8",
            newline="",
            dir=path.parent,
            prefix=".instafollow-",
            delete=False,
        ) as stream:
            temporary = stream.name
            writer = csv.writer(stream) if extension == ".csv" else None
            if writer:
                writer.writerow(["categoria", "usuario", "perfil"])
            else:
                stream.write("Categoria\tUsuário\tPerfil\n")
            count = 0
            for category, username in rows:
                # Não permitir fórmulas de planilha ou quebras de linha no resultado.
                if category not in CATEGORY_LABELS or normalize_username(username) != username:
                    raise DataError(
                        "Resultado inválido para exportação. Analise o arquivo novamente."
                    )
                columns = [CATEGORY_LABELS[category], username, profile_url(username)]
                if writer:
                    writer.writerow(columns)
                else:
                    stream.write("\t".join(columns) + "\n")
                count += 1
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        return count
    except DataError:
        raise
    except (OSError, UnicodeError) as exc:
        raise DataError(
            "Não foi possível salvar o resultado. Verifique o espaço disponível e "
            "a permissão de escrita na pasta de destino."
        ) from exc
    finally:
        if temporary is not None:
            try:
                Path(temporary).unlink(missing_ok=True)
            except OSError:
                pass


def export_category(analysis: Analysis, category: str, destination: str | Path) -> int:
    if category not in CATEGORY_LABELS:
        raise DataError("Selecione uma categoria válida para exportar.")
    return export_rows(
        ((category, name) for name in sorted(analysis.categories()[category])),
        destination,
    )


def export_all(analysis: Analysis, destination: str | Path) -> int:
    return export_rows(
        (
            (category, name)
            for category, names in analysis.categories().items()
            for name in sorted(names)
        ),
        destination,
    )
