"""
Starlang (aday üretici) + Google (kök atomizasyonu) hibrit istemci.

hybrid_client.py ile aynı mantık — fark: Zemberek yerine Starlang kullanılır.
Starlang yeni formatta zaten kök+ek+ek döndürdüğünden '+'.split ile
(root, suffix_segs) çıkarılır, ardından her kök için Google çağrılır.
"""
from starlang_client import StarlangClient
from google_morphology_client import GoogleMorphologyClient
from google_morpheme_normalizer import normalize as google_normalize, dedupe_candidates

_SOFTEN = {'p': 'b', 'ç': 'c', 't': 'd', 'k': 'ğ'}
_VOWELS = set('aeıiouöü')


def _soften_boundary(root_norm: str, suffix_segs: list[str]) -> str:
    if not suffix_segs or not root_norm:
        return root_norm
    first_suf_char = suffix_segs[0][0] if suffix_segs[0] else ''
    if root_norm[-1] in _SOFTEN and first_suf_char in _VOWELS:
        return root_norm[:-1] + _SOFTEN[root_norm[-1]]
    return root_norm


class HybridStarlangClient:
    def __init__(self):
        try:
            self._starlang = StarlangClient()
        except ConnectionError as e:
            raise ConnectionError(f"Starlang başlatılamadı: {e}") from e
        try:
            self._google = GoogleMorphologyClient()
        except ConnectionError as e:
            raise ConnectionError(f"Google Gateway bağlantısı başarısız: {e}") from e

    def _starlang_pairs(self, word: str) -> list[tuple[str, list[str]]]:
        """Starlang kök+ek+ek adaylarını (root, suffix_segs) çiftlerine dönüştürür."""
        try:
            raw = self._starlang.analyze_word(word)
        except Exception:
            return []

        seen: dict[tuple, None] = {}
        results = []
        for candidate in raw:
            parts = candidate.split('+')
            if not parts:
                continue
            root = parts[0]
            suffix_segs = parts[1:]
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
            return [root]

    def analyze_word(self, word: str) -> list[str]:
        pairs = self._starlang_pairs(word)
        if not pairs:
            return []

        root_cache: dict[str, list[str]] = {}
        for root, _ in pairs:
            if root not in root_cache:
                root_cache[root] = self._google_roots(root)

        seen: dict[str, None] = {}
        for root, suffix_segs in pairs:
            suf = ('+' + '+'.join(suffix_segs)) if suffix_segs else ''
            seen.setdefault(root + suf, None)
            for g_root in root_cache[root]:
                seen.setdefault(g_root + suf, None)
                softened = _soften_boundary(g_root, suffix_segs)
                if softened != g_root:
                    seen.setdefault(softened + suf, None)

        return list(seen)

    def analyze_sentence(self, sentence: str) -> dict[str, list[str]]:
        try:
            raw = self._starlang.analyze_sentence(sentence)
        except Exception:
            raw = {}
        result = {}
        for word in raw:
            candidates = self.analyze_word(word)
            if candidates:
                result[word] = candidates
        return result

    def close(self):
        self._starlang.close()
        self._google.close()
