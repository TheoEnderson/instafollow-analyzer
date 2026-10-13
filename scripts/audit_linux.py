"""Audita requisitos GLIBC dos ELF distribuídos, sem executar os binários."""

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


def version_tuple(value: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+(?:\.\d+)+", value):
        raise ValueError(f"Versão glibc inválida: {value}")
    return tuple(map(int, value.split(".")))


def required_versions(output: str) -> set[str]:
    # Definições exportadas não são requisitos. LC_ALL=C estabiliza os cabeçalhos.
    needs = output.partition("Version needs section")[2]
    needs = needs.split("Version definition section", 1)[0]
    return set(re.findall(r"Name: (GLIBC_[A-Za-z0-9_.]+)", needs))


def audit_bundle(bundle: Path, maximum: str = "2.35") -> dict:
    bundle = bundle.resolve()
    if not (bundle / "InstaFollowAnalyzer").is_file():
        raise RuntimeError("Executável Linux ausente.")
    if shutil.which("readelf") is None:
        raise RuntimeError("Instale binutils para auditar o pacote Linux.")
    ceiling = version_tuple(maximum)
    files = []
    for file in sorted(bundle.rglob("*")):
        if file.is_symlink() or not file.is_file():
            continue
        with file.open("rb") as stream:
            if stream.read(4) != b"\x7fELF":
                continue
        result = subprocess.run(
            ["readelf", "--version-info", "--wide", str(file)],
            env=dict(os.environ, LC_ALL="C"),
            capture_output=True,
            text=True,
            check=True,
        )
        requirements = required_versions(result.stdout)
        numeric = {name[6:] for name in requirements if re.fullmatch(r"GLIBC_\d+(?:\.\d+)+", name)}
        unknown = sorted(requirements - {f"GLIBC_{v}" for v in numeric})
        minimum = max(numeric, key=version_tuple, default=None)
        files.append(
            {
                "file": file.relative_to(bundle).as_posix(),
                "required_glibc": sorted(numeric, key=version_tuple),
                "minimum_glibc": minimum,
                "unclassified": unknown,
                "exceeds_baseline": bool(unknown or (minimum and version_tuple(minimum) > ceiling)),
            }
        )
    if not files or not any(item["file"] == "InstaFollowAnalyzer" for item in files):
        raise RuntimeError("Executável sem formato ELF; auditoria incompleta.")
    minima = [item["minimum_glibc"] for item in files if item["minimum_glibc"]]
    return {
        "baseline_glibc": maximum,
        "maximum_required_glibc": max(minima, key=version_tuple, default=None),
        "compatible_symbol_versions": not any(item["exceeds_baseline"] for item in files),
        "scope": "Requisitos de símbolos ELF; não comprova compatibilidade gráfica ou do sistema.",
        "files": files,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=root / "dist/InstaFollowAnalyzer")
    parser.add_argument("--maximum", default="2.35")
    parser.add_argument("--output", type=Path, default=root / "build/linux-abi.json")
    args = parser.parse_args()
    report = audit_bundle(args.bundle, args.maximum)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"ELF: {len(report['files'])}; GLIBC máxima requerida: {report['maximum_required_glibc']}"
    )
    if not report["compatible_symbol_versions"]:
        for item in report["files"]:
            if item["exceeds_baseline"]:
                print(f"  {item['file']}: {item['minimum_glibc']} {item['unclassified']}")
        raise SystemExit("Pacote acima da baseline glibc; refaça o build no Ubuntu 22.04.")
    print("Requisitos GLIBC dentro da baseline; testes de execução continuam necessários.")


if __name__ == "__main__":
    main()
