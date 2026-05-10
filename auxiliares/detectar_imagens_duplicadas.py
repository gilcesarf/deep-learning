#!/usr/bin/env python3
"""
Detecta imagens potencialmente duplicadas usando hash perceptual (pHash).

Uso:
  python detectar_imagens_duplicadas.py /caminho/das/imagens
  python detectar_imagens_duplicadas.py /caminho/das/imagens --limiar 3
  python detectar_imagens_duplicadas.py /caminho/das/imagens --csv duplicadas.csv

Dependências:
  pip install pillow imagehash
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageFile
import imagehash

# Permite carregar algumas imagens parcialmente corrompidas/truncadas.
ImageFile.LOAD_TRUNCATED_IMAGES = True

EXTENSOES_PADRAO = {
    ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"
}


@dataclass(frozen=True)
class ImagemHash:
    caminho: Path
    hash: imagehash.ImageHash


@dataclass(frozen=True)
class ParDuplicado:
    arquivo_1: Path
    arquivo_2: Path
    distancia: int


def listar_imagens(diretorio: Path, extensoes: set[str], recursivo: bool) -> list[Path]:
    padrao = "**/*" if recursivo else "*"
    return sorted(
        p for p in diretorio.glob(padrao)
        if p.is_file() and p.suffix.lower() in extensoes
    )


def calcular_hash(caminho: Path, hash_size: int) -> imagehash.ImageHash | None:
    try:
        with Image.open(caminho) as img:
            img = img.convert("RGB")
            return imagehash.phash(img, hash_size=hash_size)
    except Exception as exc:
        print(f"[AVISO] Não foi possível ler '{caminho}': {exc}", file=sys.stderr)
        return None


def calcular_hashes(imagens: Iterable[Path], hash_size: int) -> list[ImagemHash]:
    resultado: list[ImagemHash] = []

    for caminho in imagens:
        h = calcular_hash(caminho, hash_size)
        if h is not None:
            resultado.append(ImagemHash(caminho=caminho, hash=h))

    return resultado


def detectar_pares(hashes: list[ImagemHash], limiar: int) -> list[ParDuplicado]:
    pares: list[ParDuplicado] = []

    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            distancia = hashes[i].hash - hashes[j].hash
            if distancia <= limiar:
                pares.append(
                    ParDuplicado(
                        arquivo_1=hashes[i].caminho,
                        arquivo_2=hashes[j].caminho,
                        distancia=distancia,
                    )
                )

    return sorted(pares, key=lambda p: (p.distancia, str(p.arquivo_1), str(p.arquivo_2)))


def agrupar_pares(pares: list[ParDuplicado]) -> list[list[Path]]:
    """
    Agrupa pares conectados.
    Exemplo: A parecido com B, B parecido com C => grupo [A, B, C].
    """
    grupos: list[set[Path]] = []

    for par in pares:
        a = par.arquivo_1
        b = par.arquivo_2

        indices = [idx for idx, grupo in enumerate(grupos) if a in grupo or b in grupo]

        if not indices:
            grupos.append({a, b})
            continue

        primeiro = indices[0]
        grupos[primeiro].update({a, b})

        for idx in reversed(indices[1:]):
            grupos[primeiro].update(grupos[idx])
            del grupos[idx]

    return [sorted(grupo) for grupo in grupos]


def salvar_csv(pares: list[ParDuplicado], destino: Path) -> None:
    with destino.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["arquivo_1", "arquivo_2", "distancia"])
        writer.writeheader()
        for par in pares:
            writer.writerow({
                "arquivo_1": str(par.arquivo_1),
                "arquivo_2": str(par.arquivo_2),
                "distancia": par.distancia,
            })


def imprimir_pares(pares: list[ParDuplicado]) -> None:
    if not pares:
        print("Nenhuma duplicata potencial encontrada.")
        return

    print("Pares potencialmente duplicados:\n")
    for par in pares:
        print(f"distância={par.distancia}")
        print(f"  1) {par.arquivo_1}")
        print(f"  2) {par.arquivo_2}")
        print()


def imprimir_grupos(grupos: list[list[Path]]) -> None:
    if not grupos:
        print("Nenhum grupo de duplicatas potencial encontrado.")
        return

    print("Grupos de duplicatas potenciais:\n")
    for idx, grupo in enumerate(grupos, start=1):
        print(f"Grupo {idx}:")
        for arquivo in grupo:
            print(f"  - {arquivo}")
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detecta imagens potencialmente duplicadas por hash perceptual."
    )
    parser.add_argument(
        "diretorio",
        type=Path,
        help="Diretório onde as imagens serão procuradas.",
    )
    parser.add_argument(
        "--limiar",
        type=int,
        default=5,
        help="Distância máxima entre hashes. 0 = idênticas; 1-5 = provável duplicata. Padrão: 5.",
    )
    parser.add_argument(
        "--hash-size",
        type=int,
        default=8,
        help="Tamanho do hash perceptual. Padrão: 8.",
    )
    parser.add_argument(
        "--nao-recursivo",
        action="store_true",
        help="Procura somente no diretório informado, sem subdiretórios.",
    )
    parser.add_argument(
        "--grupos",
        action="store_true",
        help="Exibe grupos conectados em vez de pares.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Salva os pares encontrados em um arquivo CSV.",
    )
    parser.add_argument(
        "--ext",
        nargs="+",
        default=sorted(EXTENSOES_PADRAO),
        help="Extensões consideradas. Exemplo: --ext .jpg .png .webp",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    diretorio: Path = args.diretorio.expanduser().resolve()

    if not diretorio.exists():
        print(f"[ERRO] Diretório não existe: {diretorio}", file=sys.stderr)
        return 1

    if not diretorio.is_dir():
        print(f"[ERRO] Caminho informado não é um diretório: {diretorio}", file=sys.stderr)
        return 1

    extensoes = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in args.ext}

    imagens = listar_imagens(
        diretorio=diretorio,
        extensoes=extensoes,
        recursivo=not args.nao_recursivo,
    )

    print(f"Imagens encontradas: {len(imagens)}")

    if not imagens:
        return 0

    hashes = calcular_hashes(imagens, hash_size=args.hash_size)
    print(f"Imagens lidas com sucesso: {len(hashes)}")

    pares = detectar_pares(hashes, limiar=args.limiar)
    print(f"Pares potencialmente duplicados: {len(pares)}")
    print()

    if args.grupos:
        imprimir_grupos(agrupar_pares(pares))
    else:
        imprimir_pares(pares)

    if args.csv:
        destino = args.csv.expanduser().resolve()
        salvar_csv(pares, destino)
        print(f"CSV salvo em: {destino}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
