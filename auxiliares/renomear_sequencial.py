#!/usr/bin/env python3

import argparse
from pathlib import Path
from uuid import uuid4


IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"
}


def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def listar_arquivos(diretorio: Path, recursivo: bool = False):
    if recursivo:
        arquivos = [p for p in diretorio.rglob("*") if is_image_file(p)]
    else:
        arquivos = [p for p in diretorio.iterdir() if is_image_file(p)]

    return sorted(arquivos, key=lambda p: p.name.lower())


def renomear_sequencial(
    diretorio: Path,
    inicio: int = 1,
    digitos: int = 6,
    recursivo: bool = False,
    dry_run: bool = False
):
    if not diretorio.exists():
        raise FileNotFoundError(f"Diretório não existe: {diretorio}")

    if not diretorio.is_dir():
        raise NotADirectoryError(f"Não é um diretório: {diretorio}")

    arquivos = listar_arquivos(diretorio, recursivo=recursivo)

    if not arquivos:
        print("Nenhum arquivo de imagem encontrado.")
        return

    plano = []

    for idx, arquivo in enumerate(arquivos, start=inicio):
        novo_nome = f"{idx:0{digitos}d}{arquivo.suffix.lower()}"
        destino = arquivo.with_name(novo_nome)
        plano.append((arquivo, destino))

    print("Plano de renomeação:")
    for origem, destino in plano:
        print(f"{origem.name} -> {destino.name}")

    if dry_run:
        print("\nDry-run habilitado. Nenhum arquivo foi renomeado.")
        return

    temporarios = []

    try:
        for origem, _ in plano:
            temporario = origem.with_name(f".tmp_rename_{uuid4().hex}{origem.suffix}")
            origem.rename(temporario)
            temporarios.append(temporario)

        for temporario, (_, destino) in zip(temporarios, plano):
            temporario.rename(destino)

        print(f"\nConcluído. {len(plano)} arquivos de imagem renomeados.")

    except Exception as e:
        print(f"\nErro durante renomeação: {e}")
        print("Alguns arquivos podem ter ficado com nome temporário.")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Renomeia apenas arquivos de imagem para números sequenciais."
    )

    parser.add_argument(
        "diretorio",
        help="Diretório contendo os arquivos de imagem a renomear."
    )

    parser.add_argument(
        "--inicio",
        type=int,
        default=1,
        help="Número inicial da sequência. Padrão: 1."
    )

    parser.add_argument(
        "--digitos",
        type=int,
        default=6,
        help="Quantidade de dígitos no nome final. Padrão: 6."
    )

    parser.add_argument(
        "--recursivo",
        action="store_true",
        help="Renomeia imagens também em subdiretórios."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria feito, sem renomear arquivos."
    )

    args = parser.parse_args()

    renomear_sequencial(
        diretorio=Path(args.diretorio),
        inicio=args.inicio,
        digitos=args.digitos,
        recursivo=args.recursivo,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
