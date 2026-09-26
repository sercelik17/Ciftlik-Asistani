from __future__ import annotations

import argparse
from pathlib import Path

from .index_builder import build_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Hayvancılık RAG bilgi tabanı indeksini oluşturur.")
    parser.add_argument("--source", type=Path, default=None, help="PDF/TXT/MD kaynak klasörü")
    parser.add_argument("--index", type=Path, default=None, help="FAISS indeks klasörü")
    args = parser.parse_args()

    manifest = build_index(args.source, args.index)
    print("RAG indeksi başarıyla oluşturuldu:")
    for key, value in manifest.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
