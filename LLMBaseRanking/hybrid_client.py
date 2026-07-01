"""
Zemberek (aday üretici) + Google (kök atomizasyonu) hibrit istemci.

Her kelime için:
1. Zemberek → aday listesi (kendi analiz string formatında)
2. morpheme_normalizer ile her adaydan (kök, suffix_segs) çıkar
3. Her benzersiz kök için Google.analyze_word(kök) → atomik kök varyantları al
4. Tüm (google_kök_norm) × (zemberek_suffix_segs) kombinasyonlarını üret
5. Orijinal Zemberek adaylarını da normalize edip ekle
6. Unified kök+ek+ek formatında, yüzey bazlı deduplicated döndür

Örnek:
  imzalanan → Zemberek: "[imzalamak:Verb] imzala:Verb+n:Pass+an:PresNom"
               morpheme_normalizer → kök="imzala", suffix=["n","an"]
               Google("imzala") → ["imza+la"]
               Sentetik: "imza+la+n+an"  ← TWT gold

Neden Zemberek?
  Starlang yerine Zemberek kullanılıyor çünkü:
  - Starlang bazı kelimelerde IndexError fırlatıyor (kütüphane iç bug'ı)
  - Zemberek gateway zaten çalışıyor, TWT benchmark'ta ana motor olarak test edilmiş
  - morpheme_normalizer.py Zemberek formatını eksiksiz parse ediyor
"""
from zemberek_client import ZemberekClient
from google_morphology_client import GoogleMorphologyClient
from google_morpheme_normalizer import normalize as google_normalize, dedupe_candidates
from morpheme_normalizer import extract_morphemes

_SOFTEN = {'p': 'b', 'ç': 'c', 't': 'd', 'k': 'ğ'}
_VOWELS = set('aeıiouöü')


class HybridClient:
    def __init__(self):
        try:
            self._zemberek = ZemberekClient()
        except ConnectionError as e:
            raise ConnectionError(f"Zemberek Gateway bağlantısı başarısız: {e}") from e
        try:
            self._google = GoogleMorphologyClient()
        except ConnectionError as e:
            raise ConnectionError(f"Google Gateway bağlantısı başarısız: {e}") from e

    def _zemberek_pairs(self, word: str) -> list[tuple[str, list[str]]]:
        """
        Zemberek adaylarını (kök, suffix_segs) çiftlerine dönüştürür.
        Aynı yüzey segmentasyonuna sahip adaylar birleştirilir (dedup).
        """
        try:
            raw = self._zemberek.analyze_word(word)
        except Exception:
            return []

        seen: dict[tuple, None] = {}
        results = []
        for analysis in raw:
            segs = extract_morphemes(analysis)
            if not segs:
                continue
            root = segs[0]
            suffix_segs = segs[1:]
            key = (root, tuple(suffix_segs))
            if key not in seen:
                seen[key] = None
                results.append((root, suffix_segs))
        return results

    def _google_roots(self, root: str) -> list[str]:
        """Google'dan kök için normalize edilmiş tüm varyantları döndürür."""
        try:
            raw = self._google.analyze_word(root)
            deduped = dedupe_candidates(raw)
            norms = list(dict.fromkeys(
                google_normalize(c).lower() for c in deduped
            ))
            return [n for n in norms if n]
        except Exception:
            return [root]  # fallback: köke dokunma

    def analyze_word(self, word: str) -> list[str]:
        pairs = self._zemberek_pairs(word)
        if not pairs:
            return []

        # Her benzersiz kök için Google adaylarını önbellekle
        root_cache: dict[str, list[str]] = {}
        for root, _ in pairs:
            if root not in root_cache:
                root_cache[root] = self._google_roots(root)

        seen: dict[str, None] = {}
        for root, suffix_segs in pairs:
            suf = ('+' + '+'.join(suffix_segs)) if suffix_segs else ''
            # Orijinal Zemberek adayı (normalize edilmiş)
            seen.setdefault(root + suf, None)
            # Google kök varyantları × Zemberek ekleri
            for g_root in root_cache[root]:
                seen.setdefault(g_root + suf, None)
                softened = _soften_boundary(g_root, suffix_segs)
                if softened != g_root:
                    seen.setdefault(softened + suf, None)

        return list(seen)

    def analyze_sentence(self, sentence: str) -> dict[str, list[str]]:
        try:
            raw = self._zemberek.analyze_sentence(sentence)
        except Exception:
            raw = {}
        result = {}
        for word, _ in raw.items():
            candidates = self.analyze_word(word)
            if candidates:
                result[word] = candidates
        return result

    def close(self):
        self._zemberek.close()
        self._google.close()


def _soften_boundary(root_norm: str, suffix_segs: list[str]) -> str:
    """Kök-ek sınırında ünsüz yumuşaması: güven+lik + i → güven+liğ."""
    if not suffix_segs or not root_norm:
        return root_norm
    first_suf_char = suffix_segs[0][0] if suffix_segs[0] else ''
    if root_norm[-1] in _SOFTEN and first_suf_char in _VOWELS:
        return root_norm[:-1] + _SOFTEN[root_norm[-1]]
    return root_norm
