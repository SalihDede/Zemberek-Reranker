"""
ZemberekClient ile aynı arayüze sahip istemci — kaynak motor StarlangSoftware'in
NlpToolkit-MorphologicalDisambiguation / MorphologicalAnalysis kütüphanesi
(https://github.com/StarlangSoftware/TurkishMorphologicalDisambiguation).

Google/Zemberek'in aksine ayrı bir gateway süreci gerekmez: kütüphane saf
Python'dur ve sözlük verisini pip paketiyle birlikte getirir, bu yüzden
FsmMorphologicalAnalyzer doğrudan bu süreç içinde (in-process) çalışır.

Aday string formatı iki parçadan oluşur: "TAGS | suffixList". Sol taraf
transitionList() çıktısıdır (LLM'e gösterilen, ranker.py'deki tag legend ile
eşleşen sade gramer etiketleri: "koy+NOUN+A3SG+PNON+GEN"). Sağ taraf
suffixList() çıktısıdır (StateName(kümülatif yüzey biçim) adımları, örn.
"NominalRoot(koy)+Case1(koyun)") — starlang_morpheme_normalizer.py bu kısmı
ayrıştırarak gerçek yüzey morfemlerini çıkarır. Tek string olması, diğer
istemcilerle aynı sözleşmeyi (candidate = LLM'e gösterilecek VE normalize
edilecek tek kaynak) korur.
"""
from MorphologicalAnalysis.FsmMorphologicalAnalyzer import FsmMorphologicalAnalyzer
from starlang_morpheme_normalizer import normalize as _normalize


def _candidate_str(parse) -> str:
    full = f"{parse.transitionList()} | {parse.suffixList()}"
    return _normalize(full)


class StarlangClient:
    def __init__(self):
        try:
            self._fsm = FsmMorphologicalAnalyzer()
        except Exception as e:
            raise ConnectionError(
                f"Starlang FsmMorphologicalAnalyzer yüklenemedi: {e}"
            ) from e

    def analyze_word(self, word: str) -> list[str]:
        """Bir kelime için tüm morfolojik analiz ihtimallerini döndürür."""
        try:
            parse_list = self._fsm.robustMorphologicalAnalysis(word)
        except Exception:
            return []
        seen: dict[str, None] = {}
        for j in range(parse_list.size()):
            try:
                seen.setdefault(_candidate_str(parse_list.getFsmParse(j)), None)
            except Exception:
                continue
        return list(seen)

    def analyze_sentence(self, sentence: str) -> dict[str, list[str]]:
        """
        Cümledeki her kelime için analiz ihtimallerini döndürür. Starlang'in
        cümle bazlı Sentence() tokenizer'ı noktalamayı kelimeye yapıştırılmış
        bırakıyor (örn. "eve." tek token), bu yüzden Zemberek'in word-by-word
        fallback'ine benzer şekilde kendi noktalama temizliğimizi yapıp
        kelime kelime analiz ediyoruz.
        """
        analyses = {}
        for word in sentence.split():
            clean = word.strip(".,!?;:\"'()[]{}…-")
            if not clean or clean in analyses:
                continue
            candidates = self.analyze_word(clean)
            if candidates:
                analyses[clean] = candidates
        return analyses

    def close(self):
        pass  # in-process kütüphane, kapatılacak bir bağlantı yok
