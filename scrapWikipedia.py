import requests
from bs4 import BeautifulSoup
import re


def web_scraping_yap(url):
    """Wikipedia sayfasını indirir ve BeautifulSoup nesnesi döner."""
    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/91.0.4472.124 Safari/537.36'
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return None
    return BeautifulSoup(response.content, 'html.parser')



def main_body_cek(url):
    """Wikipedia sayfasının ana metin paragraflarını düz metin olarak döndürür."""
    soup = web_scraping_yap(url)
    if soup is None:
        return None

    paragraflar = soup.select('#mw-content-text p')
    temiz_paragraflar = []

    for p in paragraflar:
        metin = p.get_text(separator=" ", strip=True)
        metin = re.sub(r'\[\s*\d+\s*\]', '', metin)  # dipnotlar [1] veya [ 6 ]
        metin = re.sub(r"\s+'", "'", metin)           # "Ödülü 'ne" → "Ödülü'ne"
        metin = re.sub(r'\s+', ' ', metin).strip()
        if metin:
            temiz_paragraflar.append(metin)

    return "\n\n".join(temiz_paragraflar)


# Test veya dış çağrılar için örnek kullanım
if __name__ == "__main__":
    test_url = "https://tr.wikipedia.org/wiki/Recep_Tayyip_Erdo%C4%9Fan"
    metin = main_body_cek(test_url)
    if metin:
        with open("WikiOutput.txt", "w", encoding="utf-8") as f:
            f.write(metin)
        print("✅ WikiOutput.txt dosyası oluşturuldu.")
    else:
        print("❌ Sayfa alınamadı.")