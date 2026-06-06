"""
Zemberek LLM Reranker — Benchmark

Google Turkish Web Treebank (TWT) için doğrudan benchmark.

Kullanım:
  python Benchmark/benchmark.py benchmark_data/TWT/data/web.conllu
  python Benchmark/benchmark.py benchmark_data/TWT/data/web.conllu benchmark_data/TWT/data/wiki.conllu --limit 200
"""

import sys
import os
import argparse
import json
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
from dataset_loader import load_twt


def _tr_lower(text: str) -> str:
    return text.replace('I', 'ı').replace('İ', 'i').lower()


def _get_candidates(
    zemberek: ZemberekClient,
    word_analyses: dict[str, list[str]],
    word: str,
) -> list[str]:
    candidates = word_analyses.get(word)
    if candidates:
        return candidates
    lower_word = _tr_lower(word)
    for key, value in word_analyses.items():
        if _tr_lower(key) == lower_word:
            return value
    try:
        return zemberek.analyze_word(word)
    except Exception:
        return []


def _candidate_record(analysis: str) -> dict:
    return {
        'analysis': analysis,
        'surface_morphemes': normalize(analysis),
    }


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
    single_ig = pure.get('single_ig', 0)
    if single_ig:
        print(f'Tek-IG kelimeler (atlandı) : {single_ig}')
    print(f'Toplam kelime              : {total}')
    print(f'  Belirsiz (LLM gerekli)   : {amb}')
    print(f'  Tek adaylı               : {unamb}')
    if pure.get('no_analysis'):
        print(f'  Zemberek analizi yok     : {pure["no_analysis"]}')

    if amb > 0:
        base_acc  = pure.get('baseline_correct', 0) / amb * 100
        pure_acc  = pure.get('llm_correct', 0)      / amb * 100
        pure_gain = pure_acc - base_acc

        print(f'\nDisambiguation accuracy (belirsiz kelimeler):')
        print(f'  Baseline        : {pure.get("baseline_correct", 0)}/{amb} = {base_acc:.1f}%')
        print(f'  Pure LLM        : {pure.get("llm_correct", 0)}/{amb} = {pure_acc:.1f}%  ({pure_gain:+.1f}% vs baseline)')

        if has_judge:
            j_amb = judge.get('ambiguous', amb)
            judge_acc  = judge.get('llm_correct', 0) / j_amb * 100
            judge_gain = judge_acc - base_acc
            vs_pure    = judge_acc - pure_acc
            changed    = judge.get('changed', 0)
            improved   = judge.get('improved', 0)
            worsened   = judge.get('worsened', 0)

            print(f'  LLM + Judge     : {judge.get("llm_correct", 0)}/{j_amb} = {judge_acc:.1f}%  ({judge_gain:+.1f}% vs baseline  {vs_pure:+.1f}% vs pure)')
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


# ── TWT doğrudan karşılaştırma ───────────────────────────────────

def _seg_match(system_str: str, gold_igs: list[str]) -> bool:
    """
    Sistem morfem stringinin TWT IG'lerinin geçerli bir alt bölünmesi
    (refinement) olup olmadığını kontrol eder.

    Örnek:
      system="bit+ir+me+nin"  gold_igs=["bit","ir","menin"]  → True
      system="bitir+menin"    gold_igs=["bit","ir","menin"]  → False
    """
    sys_segs = _tr_lower(system_str).split('+')
    i, j, current = 0, 0, ''
    while i < len(gold_igs) and j < len(sys_segs):
        current += sys_segs[j]
        j += 1
        if current == gold_igs[i]:
            i += 1
            current = ''
        elif not gold_igs[i].startswith(current):
            return False
    return i == len(gold_igs) and current == ''


def evaluate_twt(
    twt_path: str,
    zemberek: ZemberekClient,
    step: bool,
    verbose: bool,
    limit: int,
    use_judge: bool,
    log_file=None,
) -> tuple[dict, dict]:
    """
    TWT CoNLL-U dosyasını doğrudan okur — .gold dosyasına gerek yok.
    Gold = TWT'nin insan-anotasyonlu IG yüzey formları (döngüsüz).
    Yalnızca birden fazla IG'li kelimeler değerlendirilir; tek-IG
    kelimeler (çekim ekleri) 'single_ig' sayacına eklenir.
    """
    pure:  dict = defaultdict(int)
    judge: dict = defaultdict(int)

    for sent_idx, sentence in enumerate(load_twt(twt_path)):
        if limit and sent_idx >= limit:
            break

        if step:
            print(f'\n{"─" * 60}')
            print(f'[{sent_idx + 1}] {sentence.text}')
            sys.stdout.flush()

        word_analyses = zemberek.analyze_sentence(sentence.text)
        if not word_analyses:
            continue

        pure_rankings = rank_sentence(sentence.text, word_analyses)

        if use_judge:
            judge_rankings = judge_and_rerank(sentence.text, word_analyses, pure_rankings)
        else:
            judge_rankings = {}

        sent_log = {
            'dataset': os.path.basename(twt_path),
            'sentence_index': sent_idx + 1,
            'sentence': sentence.text,
            'tokens': [],
        }

        for token in sentence.tokens:
            word = token.form.strip(".,!?;:\"'()[]{}…-")
            candidates = _get_candidates(zemberek, word_analyses, word)
            baseline_sel = candidates[0] if candidates else None
            pure_sel = pure_rankings.get(word, baseline_sel) if baseline_sel else None
            judge_sel = judge_rankings.get(word, pure_sel) if use_judge and pure_sel else None
            gold_igs = token.surface_igs
            baseline_str = normalize(baseline_sel) if baseline_sel else ''
            pure_str = normalize(pure_sel) if pure_sel else ''
            judge_str = normalize(judge_sel) if judge_sel else ''
            baseline_ok = _seg_match(baseline_str, gold_igs) if baseline_sel else False
            pure_ok = _seg_match(pure_str, gold_igs) if pure_sel else False
            judge_ok = _seg_match(judge_str, gold_igs) if judge_sel else False
            evaluated = len(gold_igs) >= 2 and bool(candidates)

            sent_log['tokens'].append({
                'form': token.form,
                'lookup_form': word,
                'upos': token.upos,
                'gold_surface_igs': gold_igs,
                'gold_surface': '+'.join(gold_igs),
                'evaluated': evaluated,
                'skip_reason': None if evaluated else ('single_ig' if len(gold_igs) < 2 else 'no_zemberek_analysis'),
                'zemberek_candidates': [_candidate_record(c) for c in candidates],
                'baseline': {
                    'candidate_index': 0 if baseline_sel else None,
                    'analysis': baseline_sel,
                    'surface_morphemes': baseline_str,
                    'correct': baseline_ok,
                },
                'llm': {
                    'candidate_index': candidates.index(pure_sel) if pure_sel in candidates else None,
                    'analysis': pure_sel,
                    'surface_morphemes': pure_str,
                    'correct': pure_ok,
                },
                'judge': {
                    'enabled': use_judge,
                    'candidate_index': candidates.index(judge_sel) if judge_sel in candidates else None,
                    'analysis': judge_sel,
                    'surface_morphemes': judge_str,
                    'correct': judge_ok,
                } if use_judge else None,
            })

            if len(token.surface_igs) < 2:
                pure['single_ig'] += 1
                continue

            if not candidates:
                pure['no_analysis'] += 1
                continue

            pure['total'] += 1

            if len(candidates) > 1:
                pure['ambiguous'] += 1

                if baseline_ok:
                    pure['baseline_correct'] += 1
                if pure_ok:
                    pure['llm_correct'] += 1

                if use_judge:
                    judge['ambiguous'] += 1
                    if judge_ok:
                        judge['llm_correct'] += 1
                    if judge_sel != pure_sel:
                        judge['changed'] += 1
                        if judge_ok and not pure_ok:
                            judge['improved'] += 1
                        elif not judge_ok and pure_ok:
                            judge['worsened'] += 1
                else:
                    judge_ok = pure_ok

                if step:
                    mark_p = '✓' if pure_ok  else '✗'
                    mark_j = ('✓' if judge_ok else '✗') if use_judge else ''
                    gold_str = '+'.join(gold_igs)
                    if use_judge:
                        print(f'  {mark_p}pure {mark_j}judge  {word:18s}  gold={gold_str}  pure={pure_str}  judge={normalize(judge_sel) if use_judge else ""}')
                    else:
                        print(f'  {mark_p} {word:20s}  gold={gold_str}  llm={pure_str}')
                elif verbose and not pure_ok:
                    print(f'\n  YANLIŞ → "{word}"')
                    print(f'    Gold (TWT) : {"+".join(gold_igs)}')
                    print(f'    Pure LLM   : {pure_str}')
                    if use_judge:
                        print(f'    Judge      : {normalize(judge_sel)}')
            else:
                pure['unambiguous'] += 1
                if pure_ok:
                    pure['unambiguous_correct'] += 1

        if log_file:
            log_file.write(json.dumps(sent_log, ensure_ascii=False) + '\n')
            log_file.flush()

    return dict(pure), dict(judge)


# ── Ana giriş ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Zemberek LLM Reranker TWT Benchmark')
    parser.add_argument('twt_files', nargs='+', help='Google TWT .conllu dosyaları')
    parser.add_argument('--step',    action='store_true', help='Kelime kelime canlı çıktı')
    parser.add_argument('--verbose', action='store_true', help='Sadece yanlış tahminleri göster')
    parser.add_argument('--judge',   action='store_true', help='LLM-as-Judge aşamasını etkinleştir')
    parser.add_argument('--limit',   type=int, default=0, help='Maks cümle sayısı (0=tümü)')
    parser.add_argument('--json-log', default='', help='Cümle bazlı JSONL karar logu yazılacak dosya')
    args = parser.parse_args()

    try:
        zemberek = ZemberekClient()
    except ConnectionError as e:
        print(f'Hata: {e}', file=sys.stderr)
        sys.exit(1)

    log_file = None
    if args.json_log:
        log_dir = os.path.dirname(os.path.abspath(args.json_log))
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        log_file = open(args.json_log, 'w', encoding='utf-8')

    try:
        for twt_file in args.twt_files:
            if not twt_file.endswith('.conllu'):
                print(f'Uyarı: TWT benchmark sadece .conllu dosyası bekler, atlandı: {twt_file}', file=sys.stderr)
                continue

            label = os.path.splitext(os.path.basename(twt_file))[0].upper()
            mode  = 'Pure LLM + Judge' if args.judge else 'Pure LLM'
            print(f'\n→ {twt_file} değerlendiriliyor...  [{mode}]  [TWT doğrudan]')
            pure, judge = evaluate_twt(
                twt_file, zemberek,
                step=args.step, verbose=args.verbose,
                limit=args.limit, use_judge=args.judge,
                log_file=log_file,
            )
            print_report(pure, judge, label)
    finally:
        if log_file:
            print(f'\nJSONL karar logu: {args.json_log}')
            log_file.close()
        zemberek.close()


if __name__ == '__main__':
    main()
