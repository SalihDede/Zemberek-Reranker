"""
Google turkish-morphology (Thrax/Oflazer tabanlı) analiz string'lerini
yüzey morfemlere çevirir — morpheme_normalizer.py'nin Google motoru karşılığı.

Google motorunun "human-readable analysis" formatı, soyut arşifonemler
(büyük harfler: A, H, D, C, Y, S, N, Ş) içerir — gerçek harf değil:

    "(açık[NN]+...)([VB]-lA[Derivation=Make]+...)([NOMP]-mAk[Derivation=Inf]+...)"

Bu modül, Oflazer (1994) / Çakıcı (2012) iki-seviyeli morfoloji kurallarına
göre bu arşifonemleri gerçek yüzey harflerine çözümler (ünlü uyumu, ünsüz
benzeşmesi, tampon ünsüz düşmesi) — Docker'a/FST'ye ihtiyaç duymadan, sadece
`turkish_morphology.decompose` (protobuf tabanlı, binary bağımsız) kullanır.

Doğrulama (round-trip): çözümlenmiş segmentlerin birleşimi, orijinal kelimeyle
birebir eşleşmeli. açıklamak, anlaşma, koyun (3 farklı okuma), kitapçı, uçakta,
arabası, okuyacak, gidecek örnekleriyle test edilmiştir.
"""
import re
from turkish_morphology import decompose

_BACK_VOWELS = set('aıou')
_FRONT_VOWELS = set('eiöü')
_VOWELS = _BACK_VOWELS | _FRONT_VOWELS
_VOICELESS_CONSONANTS = set('çfhkpsşt')  # "Fıstıkçı Şahap"
_SOFTEN = {'p': 'b', 'ç': 'c', 't': 'd', 'k': 'ğ'}  # ünsüz yumuşaması (kitap+ı -> kitabı)


def _last_vowel(text: str) -> "str | None":
    for ch in reversed(text):
        if ch in _VOWELS:
            return ch
    return None


def _resolve_high_vowel(prev_vowel: "str | None") -> str:
    if prev_vowel in ('a', 'ı'):
        return 'ı'
    if prev_vowel in ('e', 'i'):
        return 'i'
    if prev_vowel in ('o', 'u'):
        return 'u'
    if prev_vowel in ('ö', 'ü'):
        return 'ü'
    return 'ı'


def resolve_meta_morpheme(meta: str, preceding_surface: str) -> str:
    """
    Bir meta-morfem string'ini (örn. "lA", "mAk", "Hn", "NDA"), kendisinden
    önce gelen yüzey metnine göre gerçek harflere çözümler. Karakter karakter
    işlenir; her arşifonem kendi pozisyonundaki (o ana kadar çözümlenmiş)
    önceki harfe göre karar verir — bu sayede "DH" gibi art arda gelen iki
    arşifonemde D önce ünsüze dönüşüp H'nin düşmesini otomatik engelliyor.
    """
    out = []
    cur = preceding_surface
    for ch in meta:
        if ch == 'A':
            v = _last_vowel(cur)
            resolved = 'a' if (v is None or v in _BACK_VOWELS) else 'e'
        elif ch == 'H':
            if cur and cur[-1] in _VOWELS:
                continue  # ünlüyle bitiyorsa H düşer (örn. masa+Hm -> masam)
            resolved = _resolve_high_vowel(_last_vowel(cur))
        elif ch == 'D':
            prev_char = cur[-1] if cur else ''
            resolved = 't' if prev_char in _VOICELESS_CONSONANTS else 'd'
        elif ch == 'C':
            prev_char = cur[-1] if cur else ''
            resolved = 'ç' if prev_char in _VOICELESS_CONSONANTS else 'c'
        elif ch in 'YSNŞ':
            prev_char = cur[-1] if cur else ''
            if prev_char not in _VOWELS:
                continue  # tampon ünsüz, ünsüzden sonra düşer
            resolved = ch.lower()
        else:
            resolved = ch
        out.append(resolved)
        cur += resolved
    return ''.join(out)


def extract_morphemes(analysis: str) -> list[str]:
    """
    Google insan-okunur analiz string'ini gerçek yüzey morfem listesine çevirir.

    "(açık[NN]+...)([VB]-lA[Derivation=Make]+...)([NOMP]-mAk[Derivation=Inf]+...)"
        → ["açık", "la", "mak"]
    """
    parsed = decompose.human_readable_analysis(analysis)
    segments: list[str] = []
    surface = ''
    prev_is_root = False

    def _append(seg: str, is_root: bool = False) -> None:
        nonlocal surface, prev_is_root
        if not seg:
            return
        # Ünsüz yumuşaması (p/ç/t/k -> b/c/d/ğ) SADECE ek-ek sınırında uygulanır
        # (örn. dHk+SH -> dığı — bu kategorik/düzenli bir ek-içi değişim).
        # Kök-ek sınırında UYGULANMAZ: kök sonu yumuşaması sözlüksel bir özellik
        # (kitap+ı -> kitabı yumuşar ama yap+an -> yapan yumuşamaz) ve decompose
        # API'si bu bilgiyi (hangi köklerin yumuşadığını) hiç vermiyor; gerçek
        # TWT verisinde gözlenen hatalar hep kök sınırında yanlış yumuşatmadan
        # kaynaklandığı için varsayılan olarak kök sınırında yumuşatma kapalı.
        if not prev_is_root and surface and surface[-1] in _SOFTEN and seg[0] in _VOWELS:
            softened = _SOFTEN[surface[-1]]
            surface = surface[:-1] + softened
            for i in range(len(segments) - 1, -1, -1):
                if segments[i]:
                    segments[i] = segments[i][:-1] + softened
                    break
        segments.append(seg)
        surface += seg
        prev_is_root = is_root

    for ig in parsed.ig:
        if ig.root.morpheme:
            _append(ig.root.morpheme, is_root=True)
        if ig.HasField('derivation') and ig.derivation.meta_morpheme:
            _append(resolve_meta_morpheme(ig.derivation.meta_morpheme, surface))
        for infl in ig.inflection:
            if infl.meta_morpheme:
                _append(resolve_meta_morpheme(infl.meta_morpheme, surface))

    return segments


def normalize(analysis: str) -> str:
    """'açık+la+mak' formatında string döndürür (morpheme_normalizer.normalize ile aynı sözleşme)."""
    return '+'.join(extract_morphemes(analysis))


_FEATURE_RE = re.compile(r'\+\[Proper=(?:True|False)\]$')


def _segmentation_key(analysis: str) -> str:
    """Proper=True/False gibi segmentasyonu etkilemeyen varyantları elemek için anahtar."""
    return _FEATURE_RE.sub('', analysis)


def dedupe_candidates(candidates: list[str]) -> list[str]:
    """
    Google motoru aynı segmentasyon için Proper=True/False, Case=Bare/Nom,
    PersonNumber=V3sg/V3pl gibi işlevsel olarak segmentasyonu değiştirmeyen
    onlarca varyant üretebiliyor (örn. "açıklamak" için 12 aday, hepsi
    açık+la+mak). Bu fonksiyon, normalize() çıktısı aynı olan adayları
    tekilleştirir — ilk görüleni temsilci olarak tutar.
    """
    seen: dict[str, str] = {}
    for c in candidates:
        key = normalize(c)
        if key not in seen:
            seen[key] = c
    return list(seen.values())
