# Zemberek LLM Reranker

LLM destekli Türkçe morfolojik belirsizlik giderme (morphological disambiguation) aracı.

---

## Neden bu proje?

Türkçe, aglütinatif yapısı nedeniyle bir kelimenin onlarca farklı analizi olabilir. Hangi analizin doğru olduğu yalnızca bağlam incelenerek anlaşılabilir.

```
"koyun" →  [koyun:Noun]  koyun:Noun+A3sg        → koyun (hayvan)
           [koy:Noun]    koy:Noun+A3sg+un:Gen    → koyun (koyun-un, tamlayan)
           [koymak:Verb] koy:Verb+Imp+un:A2pl    → koyun (emir: koyunuz)
```

**Zemberek** tüm olası analizleri üretir. Bu proje, doğru analizin hangisi olduğuna **LLM'in bağlam anlayışını** kullanarak karar verir.

---

## Proje Akışı

```
Wikipedia URL listesi (source.txt)
        │
        ▼
  Wikipedia Scraper          (scrapWikipedia.py)
        │  — Makale metni çeker
        ▼
  Paragraph Chunker          (LLMBaseRanking/chunker.py)
        │  — Metni cümle / paragraf parçalarına böler
        ▼
  Zemberek Java Gateway      (Zemberek Morfoloji/)
        │  — Her kelime için N aday morfolojik analiz üretir
        │  — py4j köprüsü üzerinden Python'a iletir
        ▼
  LLM Ranker                 (LLMBaseRanking/ranker.py)
        │  — Aday analizleri cümle bağlamıyla birlikte LLM'e gönderir
        │  — LLM her kelime için doğru indeksi JSON olarak döndürür
        │
        ├─► [isteğe bağlı] LLM-as-Judge (CoT ikinci geçiş)
        │     — İlk seçimi bağımsız olarak yeniden değerlendirir
        │     — Gramer rolünü (özne/nesne/yüklem) analiz eder
        │
        ▼
  Disambiguation çıktısı
        — Her kelime için seçilen morfolojik analiz
```

### İki Çalışma Modu

| Mod | Açıklama |
|-----|----------|
| **Pure LLM** | Tek geçişte tüm belirsiz kelimeleri çözer |
| **LLM + Judge** | İlk seçimi CoT (chain-of-thought) ile ikinci bir LLM geçişiyle doğrular |

---

## Kurulum

### Gereksinimler

- Python 3.9+
- Java 17+
- OpenAI-uyumlu herhangi bir LLM API'si (Ollama, OpenRouter, vb.)

### Paketler

```bash
pip install openai py4j python-dotenv beautifulsoup4 requests
```

### `.env` Dosyası

```bash
cp LLMBaseRanking/.env.example LLMBaseRanking/.env
```

`LLMBaseRanking/.env` dosyasını aşağıdaki şablonlardan biriyle doldurun:

```env
# Ollama (yerel)
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=gemma3:27b
LLM_API_KEY=ollama

# OpenRouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=anthropic/claude-3-5-sonnet
LLM_API_KEY=sk-or-...

# OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
LLM_API_KEY=sk-...
```

---

## Çalıştırma

### Metin Analizi (Ana Kullanım)

**1.** `source.txt` dosyasına Wikipedia URL'lerini ekleyin:

```
https://tr.wikipedia.org/wiki/Aziz_Sancar
https://tr.wikipedia.org/wiki/Atatürk
```

**2.** Tek komutla çalıştırın:

```bash
./run.sh
```

> `run.sh`, Java gateway'i derler, başlatır ve Python analiz motorunu çalıştırır.  
> İşlem bitince gateway otomatik kapatılır.

İsteğe bağlı argümanlar:

```bash
./run.sh source.txt paragraph   # kaynak ve chunk stratejisi
./run.sh source.txt sentence    # cümle bazlı chunk (varsayılan)
```

### Örnek Çıktı

```
Paragraph 1: Koyun otluyordu.

  koyun:
      [0] [koymak:Verb] koy:Verb+Imp+un:A2pl
      [1] [koy:Noun]    koy:Noun+A3sg+un:Gen
    → [2] [koyun:Noun]  koyun:Noun+A3sg         ✓ LLM seçimi
```

---

## Benchmark

Sistem, Google **Turkish Web Treebank (TWT)** veri setiyle değerlendirilir.  
TWT, insan-anotasyonlu CoNLL-U formatında Türkçe cümleler içerir.

### Değerlendirme Yöntemi

- Sadece **birden fazla Zemberek adayı olan kelimeler** değerlendirilir (gerçek belirsizlik)
- Baseline: Zemberek'in ilk adayı (kural-tabanlı)
- LLM: Bu projenin seçimi
- Karşılaştırma: Seçilen morfem dizisi, TWT'nin gold morfem dizisiyle eşleşiyor mu?

### Benchmark'ı Çalıştırma

```bash
./benchmark.sh
```

> Veri seti yoksa otomatik indirilir, gateway başlatılır, benchmark çalışır.

Ek seçenekler:

```bash
# Adım adım canlı çıktı
./benchmark.sh --step

# Yalnızca yanlış tahminleri göster
./benchmark.sh --verbose

# LLM-as-Judge ikinci geçişini etkinleştir
./benchmark.sh --judge

# İlk N cümleyle sınırla (hızlı test)
./benchmark.sh --limit 100

# Karar logunu farklı dosyaya yaz
./benchmark.sh --json-log benchmark_logs/my_run.jsonl
```

### Benchmark Çıktısı

```
══════════════════════════════════════════════════════════
BENCHMARK — WEB
══════════════════════════════════════════════════════════
Toplam kelime              : 3842
  Belirsiz (LLM gerekli)   : 1205
  Tek adaylı               : 2637

Disambiguation accuracy (belirsiz kelimeler):
  Baseline        : 891/1205 = 74.0%
  Pure LLM        : 963/1205 = 79.9%  (+5.9% vs baseline)
  LLM + Judge     : 971/1205 = 80.6%  (+6.6% vs baseline  +0.7% vs pure)

Genel doğruluk — Pure LLM  : 3200/3842 = 83.3%
Genel doğruluk — +Judge    : 3208/3842 = 83.5%
══════════════════════════════════════════════════════════
```

Karar detayları `benchmark_logs/twt_benchmark.jsonl` dosyasına JSONL formatında yazılır.  
Her satır bir cümleyi; her cümle içindeki her token için baseline, LLM ve judge seçimlerini içerir.

---

## Proje Yapısı

```
.
├── run.sh                        ← Ana çalıştırma betiği (derle + gateway + analiz)
├── benchmark.sh                  ← Benchmark betiği (derle + gateway + TWT değerlendirmesi)
├── source.txt                    ← Analiz edilecek Wikipedia URL listesi
├── scrapWikipedia.py             ← Wikipedia makale scraper'ı
│
├── Zemberek Morfoloji/           ← Java katmanı
│   ├── java_gateway/
│   │   └── ZemberekGateway.java  ← py4j köprüsü, Zemberek'i Python'a açar
│   ├── lib/
│   │   └── zemberek-full.jar     ← Zemberek NLP kütüphanesi
│   └── start_zemberek_gateway.sh ← Gateway'i ayrıca başlatmak için
│
├── LLMBaseRanking/               ← Python analiz motoru
│   ├── main.py                   ← Giriş noktası
│   ├── ranker.py                 ← LLM prompt + JSON parse + yeniden sıralama
│   ├── chunker.py                ← Metin parçalama stratejileri
│   ├── zemberek_client.py        ← py4j üzerinden Zemberek istemcisi
│   └── config.py                 ← .env okuyucu
│
├── Benchmark/                    ← Değerlendirme modülü
│   ├── benchmark.py              ← TWT CoNLL-U değerlendirme motoru
│   ├── dataset_loader.py         ← CoNLL-U dosya okuyucu
│   └── morpheme_normalizer.py    ← Morfem string normalleştirici
│
└── benchmark_logs/
    └── twt_benchmark.jsonl       ← Benchmark karar logu (JSONL)
```

---

## Referanslar

**[Zemberek NLP](https://github.com/ahmetaa/zemberek-nlp)** — Ahmet Afşın Akın tarafından geliştirilen açık kaynaklı Türkçe NLP kütüphanesi. Bu proje, morfolojik aday üretimi için Zemberek'in `TurkishMorphology` modülünü kullanmaktadır.

**[Google Turkish Web Treebank](https://github.com/google-research-datasets/turkish-treebanks)** — Google tarafından yayımlanan, insan-anotasyonlu Türkçe bağımlılık ağacı bankası. Benchmark değerlendirmesinde kullanılmaktadır.

**[Wikipedia TR](https://tr.wikipedia.org)** — Kaynak metin olarak Türkçe Wikipedia makaleleri kullanılmaktadır. İçerik [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) lisansı altındadır.
