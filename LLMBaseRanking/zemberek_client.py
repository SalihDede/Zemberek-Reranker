from py4j.java_gateway import JavaGateway, GatewayParameters
from config import ZEMBEREK_HOST, ZEMBEREK_PORT


class ZemberekClient:
    def __init__(self):
        self._gateway = JavaGateway(
            gateway_parameters=GatewayParameters(
                address=ZEMBEREK_HOST,
                port=ZEMBEREK_PORT,
            )
        )
        self._zemberek = self._gateway.entry_point

    def analyze_word(self, word: str) -> list[str]:
        """Bir kelime için tüm morfolojik analiz ihtimallerini döndürür."""
        results = self._zemberek.getAnalysisResults(word)
        return list(results)

    def analyze_sentence(self, sentence: str) -> dict[str, list[str]]:
        """
        Cümledeki her kelime için analiz ihtimallerini döndürür.
        Birden fazla ihtimal olan kelimeler sözlükte yer alır.
        """
        words = sentence.split()
        analyses = {}
        for word in words:
            clean = word.strip(".,!?;:\"'()[]{}…-")
            if not clean:
                continue
            candidates = self.analyze_word(clean)
            if len(candidates) > 1:
                analyses[clean] = candidates
        return analyses

    def close(self):
        self._gateway.close()
