"""
Zemberek LLM Reranker — Benchmark

Gold dosyası formatı (prepare_gold.py çıktısı):
  Hazine Merkez'i rahatlattı
  1. Hazine --> hazine
  2. Merkez'i --> merkez+i
  3. rahatlattı --> rahatla+t+tı
  <boş satır>

Kullanım:
  python benchmark.py trmor.gold
  python benchmark.py boun.gold --verbose
  python benchmark.py imst.gold --limit 200
"""

import sys
import os
import argparse
from collections import defaultdict

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
_llm = os.path.join(_root, 'LLMBaseRanking')
for _p in (_here, _llm, _root):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from zemberek_client import ZemberekClient
from ranker import rank_sentence, judge_and_rerank
from morpheme_normalizer import normalize


# ── Gold dosyası okuyucu ─────────────────────────────────────────

def load_gold(path: str):
    """
    Yields: (sentence_text, [(word_form, gold_morpheme_seq), ...])

    Format:
      Hazine Merkez'i rahatlattı
      1. Hazine --> hazine
      2. Merkez'i --> merkez+i
      3. rahatlattı --> rahatla+t+tı
      <boş satır>
    """
    import re
    _row = re.compile(r'^\d+\.\s+(.+?)\s+-->\s+(.+)$')

    text = ''
    pairs: list[tuple[str, str]] = []

    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line:
                if pairs:
                    yield text, pairs
                    pairs = []
                    text = ''
                continue
            m = _row.match(line)
            if m:
                pairs.append((m.group(1), m.group(2)))
            else:
                text = line  # cümle başlık satırı

    if pairs:
        yield text, pairs


# ── Değerlendirme ────────────────────────────────────────────────

def evaluate(
    gold_path: str,
    zemberek: ZemberekClient,
    step: bool,
    verbose: bool,
    limit: int,
    use_judge: bool,
) -> tuple[dict, dict]:
    """
    Returns (pure_stats, judge_stats).
    judge_stats boş dict döner eğer use_judge=False.
    """
    pure:  dict = defaultdict(int)
    judge: dict = defaultdict(int)

    for sent_idx, (sentence, word_pairs) in enumerate(load_gold(gold_path)):
        if limit and sent_idx >= limit:
            break

        if step:
            print(f'\n{"─" * 60}')
            print(f'[{sent_idx + 1}] {sentence}')
            print(f'{"─" * 60}')
            print('  ① Zemberek analiz ediliyor...')
            sys.stdout.flush()

        word_analyses = zemberek.analyze_sentence(sentence)
        if not word_analyses:
            continue

        if step:
            amb_count = sum(1 for c in word_analyses.values() if len(c) > 1)
            print(f'     {len(word_analyses)} kelime analiz edildi, {amb_count} belirsiz')
            print('  ② LLM seçim yapıyor...')
            sys.stdout.flush()

        pure_rankings = rank_sentence(sentence, word_analyses)

        if use_judge:
            if step:
                print('  ③ Judge değerlendiriyor...')
                sys.stdout.flush()
            judge_rankings = judge_and_rerank(sentence, word_analyses, pure_rankings)
        else:
            judge_rankings = {}

        if step:
            label = '④' if use_judge else '③'
            print(f'  {label} Karşılaştırma:')

        for form, gold_seq in word_pairs:
            word = form.strip(".,!?;:\"'()[]{}…-")
            candidates = word_analyses.get(word, [])
            if not candidates:
                continue

            pure_sel   = pure_rankings.get(word, candidates[0])
            pure_seq   = normalize(pure_sel)
            pure['total'] += 1

            if len(candidates) > 1:
                pure['ambiguous'] += 1
                baseline_seq = normalize(candidates[0])
                pure_ok = pure_seq == gold_seq

                if pure_ok:
                    pure['llm_correct'] += 1
                if baseline_seq == gold_seq:
                    pure['baseline_correct'] += 1

                if use_judge:
                    judge_sel = judge_rankings.get(word, pure_sel)
                    judge_seq = normalize(judge_sel)
                    judge['ambiguous'] += 1
                    judge_ok = judge_seq == gold_seq
                    if judge_ok:
                        judge['llm_correct'] += 1
                    if judge_sel != pure_sel:
                        judge['changed'] += 1
                        if judge_ok and not pure_ok:
                            judge['improved'] += 1
                        elif not judge_ok and pure_ok:
                            judge['worsened'] += 1
                else:
                    judge_seq = pure_seq
                    judge_ok  = pure_ok

                if step:
                    mark_p = '✓' if pure_ok  else '✗'
                    mark_j = ('✓' if judge_ok else '✗') if use_judge else ''
                    changed = ' ← judge' if use_judge and judge_seq != pure_seq else ''
                    if use_judge:
                        print(f'     {mark_p}pure {mark_j}judge  {form:18s}  gold={gold_seq}  pure={pure_seq}  judge={judge_seq}{changed}  ({len(candidates)} aday)')
                    else:
                        print(f'     {mark_p} {form:20s}  gold={gold_seq}  llm={pure_seq}  ({len(candidates)} aday)')
                    sys.stdout.flush()

                elif verbose and not pure_ok:
                    print(f'\n  YANLIŞ → "{form}"')
                    print(f'    Gold  : {gold_seq}')
                    print(f'    Pure  : {pure_seq}')
                    if use_judge:
                        print(f'    Judge : {judge_seq}')
            else:
                pure['unambiguous'] += 1
                if pure_seq == gold_seq:
                    pure['unambiguous_correct'] += 1
                if step:
                    print(f'       {form:20s}  {pure_seq}  (tek aday)')
                    sys.stdout.flush()

    return dict(pure), dict(judge)


# ── Rapor ────────────────────────────────────────────────────────

def print_report(pure: dict, judge: dict, label: str = ''):
    total = pure.get('total', 0)
    amb   = pure.get('ambiguous', 0)
    unamb = pure.get('unambiguous', 0)
    has_judge = bool(judge)

    header = f'BENCHMARK — {label}' if label else 'BENCHMARK SONUÇLARI'
    print('\n' + '═' * 60)
    print(header)
    print('═' * 60)
    print(f'Toplam kelime              : {total}')
    print(f'  Belirsiz (LLM gerekli)   : {amb}')
    print(f'  Tek adaylı               : {unamb}')

    if amb > 0:
        base_acc  = pure.get('baseline_correct', 0) / amb * 100
        pure_acc  = pure.get('llm_correct', 0)      / amb * 100
        pure_gain = pure_acc - base_acc

        print(f'\nDisambiguation accuracy (belirsiz kelimeler):')
        print(f'  Baseline        : {pure["baseline_correct"]}/{amb} = {base_acc:.1f}%')
        print(f'  Pure LLM        : {pure["llm_correct"]}/{amb} = {pure_acc:.1f}%  ({pure_gain:+.1f}% vs baseline)')

        if has_judge:
            j_amb = judge.get('ambiguous', amb)
            judge_acc  = judge.get('llm_correct', 0) / j_amb * 100
            judge_gain = judge_acc - base_acc
            vs_pure    = judge_acc - pure_acc
            changed    = judge.get('changed', 0)
            improved   = judge.get('improved', 0)
            worsened   = judge.get('worsened', 0)

            print(f'  LLM + Judge     : {judge["llm_correct"]}/{j_amb} = {judge_acc:.1f}%  ({judge_gain:+.1f}% vs baseline  {vs_pure:+.1f}% vs pure)')
            print(f'\nJudge müdahalesi:')
            print(f'  Değiştirilen    : {changed}/{j_amb}')
            print(f'  İyileştirilen   : {improved}')
            print(f'  Kötüleştirilen  : {worsened}')

    if unamb > 0:
        unamb_acc = pure.get('unambiguous_correct', 0) / unamb * 100
        print(f'\nTek adaylı doğruluk        : {unamb_acc:.1f}%')

    if total > 0:
        pure_all  = pure.get('llm_correct', 0)  + pure.get('unambiguous_correct', 0)
        print(f'\nGenel doğruluk — Pure LLM  : {pure_all}/{total} = {pure_all/total*100:.1f}%')
        if has_judge:
            j_all = judge.get('llm_correct', 0) + pure.get('unambiguous_correct', 0)
            print(f'Genel doğruluk — +Judge    : {j_all}/{total} = {j_all/total*100:.1f}%')

    print('═' * 60)


# ── Ana giriş ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Zemberek LLM Reranker Benchmark')
    parser.add_argument('gold_files', nargs='+', help='.gold dosyaları (prepare_gold.py çıktısı)')
    parser.add_argument('--step',    action='store_true', help='Kelime kelime canlı çıktı')
    parser.add_argument('--verbose', action='store_true', help='Sadece yanlış tahminleri göster')
    parser.add_argument('--judge',   action='store_true', help='LLM-as-Judge aşamasını etkinleştir')
    parser.add_argument('--limit',   type=int, default=0, help='Maks cümle sayısı (0=tümü)')
    args = parser.parse_args()

    try:
        zemberek = ZemberekClient()
    except ConnectionError as e:
        print(f'Hata: {e}', file=sys.stderr)
        sys.exit(1)

    try:
        for gold_file in args.gold_files:
            label = os.path.splitext(os.path.basename(gold_file))[0].upper()
            mode  = 'Pure LLM + Judge' if args.judge else 'Pure LLM'
            print(f'\n→ {gold_file} değerlendiriliyor...  [{mode}]')
            pure, judge = evaluate(
                gold_file, zemberek,
                step=args.step, verbose=args.verbose,
                limit=args.limit, use_judge=args.judge,
            )
            print_report(pure, judge, label)
    finally:
        zemberek.close()


if __name__ == '__main__':
    main()
