from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class Token:
    form: str
    gold_tags: list[str]
    upos: str
    surface_igs: list[str] = field(default_factory=list)


@dataclass
class Sentence:
    text: str
    tokens: list[Token]


def _tr_lower(text: str) -> str:
    """Turkish-aware lowercase for stable surface comparisons."""
    return text.replace('I', 'ı').replace('İ', 'i').lower()


def _igs_to_token(igs: list[tuple[str, list[str], str]]) -> Token:
    form = ''.join(ig[0] for ig in igs)
    gold_tags = [feature for ig in igs for feature in ig[1]]
    upos = igs[-1][2]
    surface_igs = [_tr_lower(ig[0]) for ig in igs]
    return Token(form=form, gold_tags=gold_tags, upos=upos, surface_igs=surface_igs)


def _append_token(tokens: list[Token], current_igs: list[tuple[str, list[str], str]]) -> None:
    if not current_igs:
        return
    token = _igs_to_token(current_igs)
    if token.upos != 'PUNCT':
        tokens.append(token)


def load_twt(path: str) -> Iterator[Sentence]:
    """
    Google Turkish Web Treebank CoNLL-U loader.

    TWT rows are inflectional groups (IGs), not ordinary whitespace tokens.
    Consecutive non-punctuation IG rows joined by SpaceAfter=No are folded
    into one surface token while preserving the IG surface forms as gold.
    """
    text = ''
    tokens: list[Token] = []
    current_igs: list[tuple[str, list[str], str]] = []

    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('# text'):
                text = line.split('=', 1)[-1].strip()
                continue
            if line.startswith('#'):
                continue
            if not line:
                if current_igs:
                    _append_token(tokens, current_igs)
                    current_igs = []
                if tokens:
                    yield Sentence(text, tokens)
                text = ''
                tokens = []
                continue

            parts = line.split('\t')
            if len(parts) < 10 or '-' in parts[0] or '.' in parts[0]:
                continue

            ig_form = parts[1]
            upos = parts[3]
            feats = [p for p in parts[5].split('|') if '=' in p] if parts[5] != '_' else []
            misc = parts[9]

            if upos == 'PUNCT':
                if current_igs:
                    _append_token(tokens, current_igs)
                    current_igs = []
                continue

            current_igs.append((ig_form, feats, upos))
            if 'SpaceAfter=No' not in misc:
                _append_token(tokens, current_igs)
                current_igs = []

    if current_igs:
        _append_token(tokens, current_igs)
    if tokens:
        yield Sentence(text, tokens)
