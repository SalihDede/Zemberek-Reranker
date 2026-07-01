"""
5 backend'in karşılaştırmalı analizi.
"""
import json
import os
from collections import defaultdict

FILES = {
    'Zemberek':          'twt_benchmark.jsonl',
    'Google':            'google_benchmark.jsonl',
    'Starlang':          'starlang_benchmark.jsonl',
    'Hybrid Zem+Google': 'hybrid_zemberek_benchmark.jsonl',
    'Hybrid Str+Google': 'hybrid_starlang_benchmark.jsonl',
}

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    records = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def analyse(records):
    total_sents = len(records)
    total_words = 0
    skipped = 0           # tek-IG atlandı (tek anlam, değerlendirme dışı)
    no_analysis = 0       # analiz yok (kapsam dışı)

    # Belirsizlik yok (tek aday)
    unambig_correct = 0
    unambig_wrong = 0

    # Belirsizlik var (LLM devreye girdi)
    ambig_correct = 0
    ambig_wrong = 0

    oracle_correct = 0    # gold aday havuzunda VAR olan token sayısı
    oracle_total = 0      # değerlendirilen (analiz üretilen) tüm tokenlar

    wrong_tokens = []     # hatalı token detayları

    label_counts = defaultdict(int)

    for sent in records:
        for tok in (sent.get('tokens') or []):
            if tok is None:
                continue
            total_words += 1
            label = tok.get('label', 'unknown')
            label_counts[label] += 1

            if label == 'tek_ig_atlandi':
                skipped += 1
                continue

            if label in ('analiz_yok', 'zemberek_kapsam_disi'):
                no_analysis += 1
                continue

            # Oracle coverage: bu token için gold aday havuzunda var mı?
            oracle_total += 1
            if _gold_in_candidates(tok) or label == 'tek_aday_dogru':
                oracle_correct += 1

            # Tek aday
            if label == 'tek_aday_dogru':
                unambig_correct += 1
                continue
            if label == 'tek_aday_yanlis':
                unambig_wrong += 1
                wrong_tokens.append({
                    'type': 'tek_aday_yanlis',
                    'form': tok.get('form'),
                    'gold': tok.get('gold_surface'),
                    'predicted': (tok.get('llm') or {}).get('surface_morphemes'),
                    'candidates': [c.get('analysis') if isinstance(c, dict) else c
                                   for c in (tok.get('zemberek_candidates') or [])],
                    'sentence': sent.get('sentence'),
                })
                continue

            # Belirsiz — LLM devreye girdi
            llm_ok = (tok.get('llm') or {}).get('correct', False)
            judge_ok = (tok.get('judge') or {}).get('correct', False)
            if llm_ok or judge_ok:
                ambig_correct += 1
            else:
                ambig_wrong += 1
                wrong_tokens.append({
                    'type': 'llm_yanlis',
                    'form': tok.get('form'),
                    'gold': tok.get('gold_surface'),
                    'predicted': (tok.get('llm') or {}).get('surface_morphemes'),
                    'candidates': [c.get('analysis') if isinstance(c, dict) else c
                                   for c in (tok.get('zemberek_candidates') or [])],
                    'gold_in_candidates': _gold_in_candidates(tok),
                    'sentence': sent.get('sentence'),
                })

    return {
        'oracle_correct': oracle_correct,
        'oracle_total': oracle_total,
        'total_sents': total_sents,
        'total_words': total_words,
        'skipped': skipped,
        'no_analysis': no_analysis,
        'unambig_correct': unambig_correct,
        'unambig_wrong': unambig_wrong,
        'ambig_correct': ambig_correct,
        'ambig_wrong': ambig_wrong,
        'label_counts': dict(label_counts),
        'wrong_tokens': wrong_tokens,
    }


def _gold_in_candidates(tok):
    gold = tok.get('gold_surface', '')
    candidates = tok.get('zemberek_candidates') or []
    for c in candidates:
        surface = c.get('surface_morphemes') if isinstance(c, dict) else c
        if surface and surface == gold:
            return True
    return False


def pct(a, b):
    return f'{100*a/b:.1f}%' if b else 'N/A'


def print_report():
    print('=' * 80)
    print('KARŞILAŞTIRMALI BENCHMARK RAPORU')
    print('=' * 80)

    all_stats = {}
    for name, fname in FILES.items():
        fpath = os.path.join(HERE, fname)
        if not os.path.exists(fpath):
            print(f'\n[{name}] — dosya bulunamadı: {fname}')
            continue
        records = load(fpath)
        stats = analyse(records)
        all_stats[name] = stats

    # ── 1. Dataset özeti ──────────────────────────────────────────────────────
    print('\n── 1. Dataset & Kapsam ─────────────────────────────────────────────')
    print(f'{"Backend":<20} {"Cümle":>7} {"Kelime":>8} {"Atlandı(1-IG)":>14} {"Analiz Yok":>11}')
    print('-' * 65)
    for name, s in all_stats.items():
        print(f'{name:<20} {s["total_sents"]:>7} {s["total_words"]:>8} '
              f'{s["skipped"]:>9} ({pct(s["skipped"],s["total_words"]):>6}) '
              f'{s["no_analysis"]:>5} ({pct(s["no_analysis"],s["total_words"]):>5})')

    # ── 2. Coverage ──────────────────────────────────────────────────────────
    print('\n── 2. Coverage ─────────────────────────────────────────────────────')
    print(f'{"Backend":<20} {"Sistem Kapsam":>14} {"Oracle Kapsam":>14} {"Oracle Acc":>11}')
    print('-' * 63)
    for name, s in all_stats.items():
        evaluated = s['total_words'] - s['skipped']
        covered = evaluated - s['no_analysis']
        sys_cov = pct(covered, evaluated)
        oracle_cov = pct(s['oracle_correct'], s['oracle_total'])
        # Oracle accuracy = if gold were always selected from pool, what accuracy?
        oracle_acc = pct(s['oracle_correct'], s['oracle_total'])
        print(f'{name:<20} {covered:>7} ({sys_cov:>6}) {s["oracle_correct"]:>7} ({oracle_cov:>6})')
    print('  Sistem Kapsam : analiz üretilen / değerlendirilen kelime')
    print('  Oracle Kapsam : gold\'un aday havuzunda bulunma oranı (teorik tavan)')

    # ── 3. Tek aday (belirsizlik yok) ────────────────────────────────────────
    print('\n── 2. Belirsizlik Yok (Tek Aday) ──────────────────────────────────')
    print(f'{"Backend":<20} {"Doğru":>12} {"Yanlış":>12} {"Tek Aday Acc":>13}')
    print('-' * 60)
    for name, s in all_stats.items():
        total_unambig = s['unambig_correct'] + s['unambig_wrong']
        print(f'{name:<20} {s["unambig_correct"]:>7} ({pct(s["unambig_correct"],total_unambig):>6}) '
              f'{s["unambig_wrong"]:>7} ({pct(s["unambig_wrong"],total_unambig):>6}) '
              f'{pct(s["unambig_correct"],total_unambig):>12}')

    # ── 3. Belirsizlik var (LLM disambiguate) ────────────────────────────────
    print('\n── 3. Belirsizlik Var (LLM Disambiguate) ──────────────────────────')
    print(f'{"Backend":<20} {"Doğru":>12} {"Yanlış":>12} {"Disambig Acc":>13}')
    print('-' * 60)
    for name, s in all_stats.items():
        total_ambig = s['ambig_correct'] + s['ambig_wrong']
        print(f'{name:<20} {s["ambig_correct"]:>7} ({pct(s["ambig_correct"],total_ambig):>6}) '
              f'{s["ambig_wrong"]:>7} ({pct(s["ambig_wrong"],total_ambig):>6}) '
              f'{pct(s["ambig_correct"],total_ambig):>12}')

    # ── 4. Genel doğruluk (tüm değerlendirilen kelimeler) ────────────────────
    print('\n── 4. Genel Doğruluk (Değerlendirilen Tüm Kelimeler) ──────────────')
    print(f'{"Backend":<20} {"Doğru":>8} {"Toplam":>8} {"Acc":>8}')
    print('-' * 48)
    for name, s in all_stats.items():
        correct = s['unambig_correct'] + s['ambig_correct']
        total = correct + s['unambig_wrong'] + s['ambig_wrong']
        print(f'{name:<20} {correct:>8} {total:>8} {pct(correct, total):>8}')

    # ── 5. Hata analizi ──────────────────────────────────────────────────────
    print('\n── 5. Hata Kategorileri ────────────────────────────────────────────')
    for name, s in all_stats.items():
        wrong = s['wrong_tokens']
        total_wrong = s['unambig_wrong'] + s['ambig_wrong']
        if not wrong:
            continue
        llm_wrong = [w for w in wrong if w['type'] == 'llm_yanlis']
        coverage_wrong = [w for w in wrong if w['type'] == 'tek_aday_yanlis']
        gold_missing = [w for w in llm_wrong if not w.get('gold_in_candidates')]
        gold_present = [w for w in llm_wrong if w.get('gold_in_candidates')]

        print(f'\n  [{name}] — {total_wrong} hatalı token')
        print(f'    Kapsam hatası (tek yanlış aday):  {len(coverage_wrong)}')
        print(f'    LLM hatası (toplam):               {len(llm_wrong)}')
        print(f'      ↳ Gold adayda YOK (kapsam açığı): {len(gold_missing)} '
              f'({pct(len(gold_missing),len(llm_wrong))})')
        print(f'      ↳ Gold adayda VAR (LLM yanıldı):  {len(gold_present)} '
              f'({pct(len(gold_present),len(llm_wrong))})')

        # En sık yanlış yapılan kelimeler
        from collections import Counter
        form_counts = Counter(w['form'] for w in wrong)
        print(f'    En sık hatalı kelimeler: {form_counts.most_common(10)}')

    # ── 6. Öneri: Başka metrikler ─────────────────────────────────────────────
    print('\n── 6. Önerilen Ek Metrikler ────────────────────────────────────────')
    print("""
  a) Oracle Accuracy  — Gold aday havuzunda varsa ne kadar kazanabiliriz?
     → "Teorik tavan" gösterir; LLM hatası mı yoksa kapsam açığı mı daha büyük?

  b) Coverage Rate    — En az 1 geçerli aday üretilen kelime oranı
     → Hangi backend daha geniş kapsar?

  c) Avg Candidates   — Belirsiz kelime başına ortalama aday sayısı
     → Az aday = kolay disambiguate; çok aday = LLM zorlanır

  d) Per-POS Accuracy — NOUN/VERB/ADJ bazında ayrı doğruluk
     → Hangi POS zor? (Fiil çekimleri mi, isim durumları mı?)

  e) Morpheme F1      — Token-bazlı değil morfem-bazlı precision/recall
     → +2/-1 gibi kısmi hatalar da ödüllendirilsin

  f) Error by Source  — Kapsam hatası / LLM hatası / Format hatası ayrımı
     → Neyi geliştirirsen ne kadar kazanırsın?
""")


if __name__ == '__main__':
    print_report()
