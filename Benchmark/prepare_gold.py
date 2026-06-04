"""
Veri setlerini benchmark için surface morfem formatına dönüştürür.

Çıktı formatı (cümle başlığı + numaralı kelimeler, etiket yok):

  Hazine Merkez'i rahatlattı
  1. Hazine --> hazine
  2. Merkez'i --> merkez+i
  3. rahatlattı --> rahatla+t+tı

  YILBAŞINDAN bu yana Merkez Bankası kaynaklarına yüklenen Hazine...
  1. YILBAŞINDAN --> yılbaş+ı+ndan
  2. bu --> bu
  ...
"""

import sys
import os
import argparse

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
_llm = os.path.join(_root, 'LLMBaseRanking')
for _p in (_here, _llm, _root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from zemberek_client import ZemberekClient
from morpheme_normalizer import extract_tags, normalize, extract_pos
from dataset_loader import load_trmor, load_conllu

_ZEM_TO_UPOS = {
    'Noun': 'NOUN', 'Verb': 'VERB', 'Adj': 'ADJ', 'Adv': 'ADV',
    'Pron': 'PRON', 'Det': 'DET', 'Postp': 'ADP', 'Conj': 'CCONJ',
    'Punc': 'PUNCT', 'Num': 'NUM', 'Interj': 'INTJ',
    'Prop': 'PROPN', 'Abbrv': 'NOUN', 'Ques': 'PART',
}


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _best_candidate(candidates: list[str], token, is_conllu: bool) -> str:
    if len(candidates) == 1:
        return candidates[0]
    best, best_score = candidates[0], -1.0
    for cand in candidates:
        zem_tags = extract_tags(cand)
        if is_conllu:
            pos = extract_pos(cand)
            upos_match = 1.0 if _ZEM_TO_UPOS.get(pos, '') == token.upos else 0.0
            score = upos_match * 0.6 + _jaccard(zem_tags, token.gold_tags) * 0.4
        else:
            score = _jaccard(zem_tags, token.gold_tags)
        if score > best_score:
            best_score = score
            best = cand
    return best


def generate(dataset_path: str, fmt: str, output_path: str, zemberek: ZemberekClient, limit: int = 0):
    loader = load_trmor if fmt == 'trmor' else load_conllu
    is_conllu = fmt == 'conllu'
    total = skipped = 0

    with open(output_path, 'w', encoding='utf-8') as out:
        for sent_idx, sent in enumerate(loader(dataset_path)):
            if limit and sent_idx >= limit:
                break

            pairs: list[tuple[str, str]] = []
            for token in sent.tokens:
                word = token.form.strip(".,!?;:\"'()[]{}…-")
                if not word:
                    continue

                candidates = zemberek.analyze_word(word)
                if not candidates:
                    skipped += 1
                    pairs.append((token.form, word))
                    continue

                best = _best_candidate(candidates, token, is_conllu)
                pairs.append((token.form, normalize(best)))
                total += 1

            if not pairs:
                continue

            # Cümle satırı
            out.write(sent.text + '\n')
            # Numaralı kelime satırları
            for i, (form, morpheme_seq) in enumerate(pairs, 1):
                out.write(f'{i}. {form} --> {morpheme_seq}\n')
            out.write('\n')

    print(f'  Yazılan: {total} kelime  |  Zemberek kaydı olmayan: {skipped}')


def main():
    parser = argparse.ArgumentParser(description='Gold morfem dosyası oluştur')
    parser.add_argument('dataset', help='Dataset dosyası')
    parser.add_argument('output', help='Çıktı .gold dosyası')
    parser.add_argument('--format', choices=['trmor', 'conllu'], default='trmor')
    parser.add_argument('--limit', type=int, default=0, help='Maks cümle sayısı (0=tümü)')
    args = parser.parse_args()

    try:
        zemberek = ZemberekClient()
    except ConnectionError as e:
        print(f'Hata: {e}', file=sys.stderr)
        sys.exit(1)

    print(f'→ Gold dosyası oluşturuluyor: {args.output}')
    try:
        generate(args.dataset, args.format, args.output, zemberek, args.limit)
    finally:
        zemberek.close()
    print('Tamamlandı.')


if __name__ == '__main__':
    main()
