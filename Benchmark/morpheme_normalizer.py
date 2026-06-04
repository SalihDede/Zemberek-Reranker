import re

_DERIV_RE = re.compile(r'\|([^|+]+?)→[A-Za-z,]+')


def extract_morphemes(analysis: str) -> list[str]:
    """
    Zemberek uzun format → yüzey morfem listesi (etiket yok).

    "[yapmak:Verb] yap:Verb+makta:Prog2+A3sg+dır:Cop"            → ["yap","makta","dır"]
    "[görmek:Verb] gör:Verb|ül:Pass→Verb+müş:Narr+A3sg+tür:Cop" → ["gör","ül","müş","tür"]
    "[çalışmak:Verb] çalış:Verb|ma:Inf2→Noun+lar:A3pl+ı:P3pl"   → ["çalış","ma","lar","ı"]
    "[bir:Adj] bir:Adj|lik:Ness→Noun+A3sg+te:Loc"               → ["bir","lik","te"]
    """
    _, _, rest = analysis.partition('] ')
    if not rest:
        rest = analysis

    # "|yüzey:Etiket→YeniPOS" → "+yüzey:Etiket"
    rest = _DERIV_RE.sub(r'+\1', rest)

    morphemes = []
    for token in rest.split('+'):
        token = token.strip()
        if ':' in token:
            surface = token.split(':', 1)[0]
            if surface and surface.lower() != 'zero':
                morphemes.append(surface)
        # "A3sg", "Imp", "Pres" gibi sıfır morfemli etiketler → atla

    return morphemes


def normalize(analysis: str) -> str:
    """'yap+makta+dır' formatında string döndürür."""
    return '+'.join(extract_morphemes(analysis))


def extract_tags(analysis: str) -> list[str]:
    """Etiket listesi — dataset eşleştirmesi için (gold dosyasına yazılmaz)."""
    _, _, rest = analysis.partition('] ')
    if not rest:
        rest = analysis
    rest = _DERIV_RE.sub(r'+\1', rest)

    tags = []
    for token in rest.split('+'):
        token = token.strip()
        if ':' in token:
            tag = token.split(':', 1)[1]
            if tag and tag.lower() != 'zero':
                tags.append(tag)
        elif token and token[0].isupper() and token.lower() != 'zero':
            tags.append(token)
    return tags


def extract_pos(analysis: str) -> str:
    """Ana sözcük türü: Verb, Noun, Adj..."""
    m = re.match(r'\[.*?:([A-Za-z]+)', analysis)
    return m.group(1) if m else ''
