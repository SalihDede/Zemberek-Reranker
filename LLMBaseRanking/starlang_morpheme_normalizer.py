"""
Starlang (StarlangSoftware/TurkishMorphologicalDisambiguation) analiz
string'lerini yüzey morfemlere çevirir — morpheme_normalizer.py'nin Starlang
motoru karşılığı.

Starlang'in suffixList() çıktısı her adımda KÜMÜLATİF yüzey biçimini verir,
örn. "NominalRoot(kitap)+Possessive(kitabım)" → kitap, kitabım. Bu modül
ardışık adımlar arasındaki farktan eklenen morfemi çıkarır:

  - Sınır karakteri AYNI uzunlukta değişirse (örn. p→b: kitap→kitabım) bu kök
    ünsüz yumuşamasıdır (Starlang'in kendi sözlüğü hangi köklerin yumuşadığını
    zaten bilip kümülatif biçime yansıtıyor) — değişen harf önceki segmente
    eklenir, ek bu sınırdan SONRA başlar.
  - Sınır karakteri tamamen düşerse (örn. otla→otl, +uyor) bu ünlü düşmesidir
    (örn. "-lA" fiillerinde "-Iyor" öncesi) — düşen karakter atılır, yeni ek
    bu noktadan (kendi tampon ünlüsüyle) başlar.

Doğrulama (round-trip): segmentlerin birleşimi getSurfaceForm() ile birebir
eşleşmeli. koyun (3 farklı okuma), açıklayıcı, anlaşma, zayıflama, kitapçı,
kitabım, ağacın, çalışmalarımızdan, okutturdular gibi örneklerle test edilmiştir.
"""
import re

_FORM_RE = re.compile(r'\(([^()]*)\)')
_SOFTEN = {'p': 'b', 'ç': 'c', 't': 'd', 'k': 'ğ'}


def _surface_steps(suffix_list_str: str) -> list[str]:
    """'NominalRoot(koy)+Possessive(koyun)' -> ['koy', 'koyun']"""
    steps = []
    for chunk in suffix_list_str.split('+'):
        groups = _FORM_RE.findall(chunk)
        if groups:
            steps.append(groups[-1])
    return steps


def extract_morphemes(analysis: str) -> list[str]:
    """
    "TAGS | StateName(form)+StateName(form)+..." → yüzey morfem listesi.

    "koy+NOUN+A3SG+PNON+GEN | NominalRoot(koy)+Case1(koyun)" → ["koy", "un"]
    """
    _, _, rest = analysis.partition(' | ')
    if not rest:
        rest = analysis
    steps = _surface_steps(rest)
    if not steps:
        return []

    segments = [steps[0]]
    for i in range(1, len(steps)):
        old, new = steps[i - 1], steps[i]
        cp = 0
        while cp < len(old) and cp < len(new) and old[cp] == new[cp]:
            cp += 1
        if cp == len(old):
            segments.append(new[cp:])
        elif cp == len(old) - 1 and old[-1] in _SOFTEN and new[cp:cp + 1] == _SOFTEN[old[-1]]:
            segments[-1] = segments[-1][:-1] + new[cp]
            segments.append(new[len(old):])
        elif cp == len(old) - 1:
            segments[-1] = segments[-1][:-1]
            segments.append(new[cp:])
        else:
            # Beklenmedik büyük sapma (kök yinelemesi, sayı vb.) — güvenli geri dönüş
            segments.append(new[len(old):] if len(new) > len(old) else new)
    return [s for s in segments if s]


def normalize(analysis: str) -> str:
    """'koy+un' formatında string döndürür (morpheme_normalizer.normalize ile aynı sözleşme)."""
    return '+'.join(extract_morphemes(analysis))
