from py4j.java_gateway import JavaGateway, GatewayParameters
from config import ZEMBEREK_HOST, ZEMBEREK_PORT


class ZemberekClient:
    def __init__(self):
        try:
            self._gateway = JavaGateway(
                gateway_parameters=GatewayParameters(
                    address=ZEMBEREK_HOST,
                    port=ZEMBEREK_PORT,
                )
            )
            self._zemberek = self._gateway.entry_point
        except Exception as e:
            raise ConnectionError(
                f"Zemberek Gateway'e bağlanılamadı ({ZEMBEREK_HOST}:{ZEMBEREK_PORT}): {e}"
            ) from e

    def analyze_word(self, word: str) -> list[str]:
        """Bir kelime için tüm morfolojik analiz ihtimallerini döndürür."""
        results = self._zemberek.getAnalysisResults(word)
        return list(results)

    def analyze_sentence(self, sentence: str) -> dict[str, list[str]]:
        """
        Cümledeki her kelime için analiz ihtimallerini döndürür.
        Zemberek'in cümle düzeyindeki analizini kullanır; hata durumunda
        kelime bazlı analize geri döner. Tüm kelimeler (tek adaylılar dahil)
        sözlükte yer alır.
        """
        try:
            raw = self._zemberek.getSentenceAnalyses(sentence)
            return {word: list(candidates) for word, candidates in raw.items()}
        except Exception:
            return self._analyze_word_by_word(sentence)

    def _analyze_word_by_word(self, sentence: str) -> dict[str, list[str]]:
        words = sentence.split()
        analyses = {}
        for word in words:
            clean = word.strip(".,!?;:\"'()[]{}…-")
            if not clean:
                continue
            candidates = self.analyze_word(clean)
            if candidates:
                analyses[clean] = candidates
        return analyses

    def close(self):
        self._gateway.close()
