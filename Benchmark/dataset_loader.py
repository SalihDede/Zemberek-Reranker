from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class Token:
    form: str
    gold_tags: list[str]   # eşleştirme için kaynak dataset etiketleri
    upos: str = ""         # sadece CoNLL-U için


@dataclass
class Sentence:
    text: str
    tokens: list[Token]


# ── TRMOR / Oflazer ──────────────────────────────────────────────

def _trmor_tags(analysis: str) -> list[str]:
    """
    "yap+Verb+Prog2+A3sg+Cop"             → ["Verb","Prog2","A3sg","Cop"]
    "ver+Verb^DB+Noun+Inf2+A3sg+Pnon+Acc" → ["Verb","Noun","Inf2","A3sg","Pnon","Acc"]
    """
    parts = analysis.replace('^DB', '').split('+')
    return [p.strip() for p in parts[1:] if p.strip()]


def _is_xml(form: str) -> bool:
    return form.startswith('<')


def load_trmor(path: str) -> Iterator[Sentence]:
    """
    TrMor2018: word<TAB>doğru_analiz[<TAB>alt1...]
    <S>…</S> etiketlerini cümle sınırı olarak kullanır,
    diğer XML etiketlerini (<DOC>, <TITLE>…) atlar.
    """
    tokens: list[Token] = []
    in_sentence = False

    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line.strip():
                continue

            parts = line.split('\t')
            form = parts[0].strip()
            gold_analysis = parts[1].strip() if len(parts) > 1 else ''

            if form == '<S>':
                in_sentence = True
                tokens = []
                continue
            if form == '</S>':
                if tokens:
                    yield Sentence(' '.join(t.form for t in tokens), tokens)
                tokens = []
                in_sentence = False
                continue

            # Diğer XML etiketlerini atla
            if _is_xml(form):
                continue

            if in_sentence:
                tokens.append(Token(form=form, gold_tags=_trmor_tags(gold_analysis)))

    if tokens:
        yield Sentence(' '.join(t.form for t in tokens), tokens)


# ── CoNLL-U (BOUN-UD, IMST-UD) ───────────────────────────────────

def load_conllu(path: str) -> Iterator[Sentence]:
    """CoNLL-U formatı — BOUN-UD ve IMST-UD için."""
    text = ''
    tokens: list[Token] = []

    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('# text'):
                text = line.split('=', 1)[-1].strip()
            elif line.startswith('#') or not line:
                if tokens:
                    yield Sentence(text, tokens)
                    text = ''
                    tokens = []
            else:
                parts = line.split('\t')
                if len(parts) < 10 or '-' in parts[0] or '.' in parts[0]:
                    continue
                feats = [p for p in parts[5].split('|') if '=' in p] if parts[5] != '_' else []
                tokens.append(Token(form=parts[1], gold_tags=feats, upos=parts[3]))

    if tokens:
        yield Sentence(text, tokens)
