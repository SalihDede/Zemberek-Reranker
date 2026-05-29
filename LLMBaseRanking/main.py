import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chunker import paragraph_chunks, sentence_chunks
from zemberek_client import ZemberekClient
from ranker import rank_sentence
from scrapWikipedia import main_body_cek


def load_urls(source_path: str) -> list[str]:
    with open(source_path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def process_url(url: str, zemberek: ZemberekClient, strategy: str = "sentence"):
    print(f"\n{'═' * 60}")
    print(f"Çekiliyor: {url}")

    text = main_body_cek(url)
    if not text:
        print("  ❌ Sayfa alınamadı, atlanıyor.")
        return

    chunks = sentence_chunks(text) if strategy == "sentence" else paragraph_chunks(text)
    print(f"  {len(chunks)} {strategy} bulundu.")

    for i, chunk in enumerate(chunks, 1):
        word_analyses = zemberek.analyze_sentence(chunk)
        if not word_analyses:
            continue

        rankings = rank_sentence(chunk, word_analyses)
        _print_result(i, chunk, word_analyses, rankings)


def _print_result(para_no: int, paragraph: str, word_analyses: dict, rankings: dict):
    print(f"\n{'─' * 60}")
    print(f"Paragraf {para_no}:")
    print(f"{paragraph}")
    print()
    for word, candidates in word_analyses.items():
        selected = rankings.get(word, candidates[0])
        print(f"\n  {word}:")
        for i, c in enumerate(candidates):
            marker = "→" if c == selected else " "
            print(f"    {marker} [{i}] {c}")


def main():
    parser = argparse.ArgumentParser(description="Zemberek morfoloji LLM ranker")
    parser.add_argument(
        "source",
        help="Wikipedia URL'lerini içeren .txt dosyası (satır satır)",
    )
    parser.add_argument(
        "--strategy",
        choices=["sentence", "paragraph"],
        default="sentence",
        help="Chunking stratejisi (varsayılan: sentence)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"Hata: '{args.source}' bulunamadı.", file=sys.stderr)
        sys.exit(1)

    urls = load_urls(args.source)
    if not urls:
        print("Hata: source dosyası boş.", file=sys.stderr)
        sys.exit(1)

    import config
    print(f"Model     : {config.LLM_MODEL}")
    print(f"Strateji  : {args.strategy}")
    print(f"URL sayısı: {len(urls)}")

    zemberek = ZemberekClient()
    try:
        for url in urls:
            process_url(url, zemberek, strategy=args.strategy)
    finally:
        zemberek.close()


if __name__ == "__main__":
    main()
