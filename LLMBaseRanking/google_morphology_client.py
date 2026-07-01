"""
ZemberekClient ile birebir aynı arayüze sahip istemci — sadece kaynak motor
Google'ın turkish-morphology kütüphanesi, taşıma katmanı py4j yerine HTTP
(Docker container'daki docker_server.py'ye bağlanır).

Bu arayüz eşitliği sayesinde benchmark.py / ranker.py hiçbir değişiklik
gerektirmeden iki motor arasında --backend flag'iyle geçiş yapabiliyor.
"""
import requests
from config import GOOGLE_MORPH_HOST, GOOGLE_MORPH_PORT

_BASE_URL = f"http://{GOOGLE_MORPH_HOST}:{GOOGLE_MORPH_PORT}"


class GoogleMorphologyClient:
    def __init__(self):
        try:
            resp = requests.get(f"{_BASE_URL}/health", timeout=5)
            resp.raise_for_status()
        except Exception as e:
            raise ConnectionError(
                f"Google Morphology Gateway'e bağlanılamadı ({_BASE_URL}): {e}"
            ) from e

    def analyze_word(self, word: str) -> list[str]:
        """Bir kelime için tüm morfolojik analiz ihtimallerini döndürür."""
        resp = requests.get(f"{_BASE_URL}/analyze_word", params={"word": word}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def analyze_sentence(self, sentence: str) -> dict[str, list[str]]:
        """
        Cümledeki her kelime için analiz ihtimallerini döndürür. Google
        motorunun kendi cümle-bazlı analiz API'si olmadığı için sunucu
        tarafında kelime kelime ayrıştırılır (Zemberek'in word-by-word
        fallback'ine benzer).
        """
        resp = requests.get(f"{_BASE_URL}/analyze_sentence", params={"text": sentence}, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def close(self):
        pass  # HTTP bağlantısı kalıcı bir oturum tutmuyor, kapatılacak bir şey yok
