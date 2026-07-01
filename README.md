# Türkçe Morfolojik Disambiguasyon — LLM Reranker

LLM destekli Türkçe morfolojik belirsizlik giderme (morphological disambiguation) aracı.  
5 farklı morfoloji backend'i, Google TWT gold standard'ı üzerinde karşılaştırmalı olarak değerlendirilmiştir.

---

## Neden bu proje?

Türkçe, aglütinatif yapısı nedeniyle bir kelimenin onlarca farklı morfolojik analizi olabilir:

```
"koyun" →  [koyun:Noun]  koyun:Noun+A3sg        → koyun (hayvan)
           [koy:Noun]    koy:Noun+A3sg+un:Gen    → koyun (koyun-un, tamlayan)
           [koymak:Verb] koy:Verb+Imp+un:A2pl    → koyun (emir: koyunuz)
```

Hangi analizin doğru olduğu yalnızca **bağlam** incelenerek anlaşılabilir. Bu proje:

1. Morfoloji motorundan **tüm olası aday analizleri** üretir
2. Google'ın morfem atomizasyonuyla adayları **zenginleştirir** (hybrid modlar)
3. LLM'in bağlam anlayışını kullanarak **doğru analizi** seçer

---

## Morfoloji Backend'leri

Sistem 5 farklı aday üretme stratejisini destekler:

| Backend | Açıklama |
|---|---|
| `zemberek` | Zemberek Java kütüphanesi — Türkçe NLP'nin fiili standardı |
| `google` | Google `turkish-morphology` — derin morfem atomizasyonu |
| `starlang` | StarlangSoftware NlpToolkit — saf Python, gateway yok |
| `hybrid_zemberek` | Zemberek adayları + Google kök atomizasyonu **(önerilen)** |
| `hybrid_starlang` | Starlang adayları + Google kök atomizasyonu |

### Hybrid Mantığı

Türkçe `-la/-le` yapım eki, tüm motorlarda sözlükte **bütünleşik kök** olarak kayıtlıdır.  
Oysa TWT gold, her zaman **en derin türetme sınırını** bekler:

```
"imzalandı"
  Zemberek        → imzala+n+dı          (imzala: atomik kök)
  Google(imzala)  → imza+la              (atomize eder)
  Hybrid çıktısı  → imzala+n+dı          (Zemberek orijinali)
                  → imza+la+n+dı         (Google atomize + Zemberek ekler)  ← TWT gold ✓
```

Her benzersiz Zemberek/Starlang kökü için Google çağrılır; Google'ın tüm varyantları  
Zemberek/Starlang'ın ek segmentasyonuyla çapraz ürün (cross-product) oluşturur.

---

## Kurulum

```bash
git clone <repo-url>
cd <repo>
./setup.sh
```

`setup.sh` şunları yapar:
- Python sanal ortamı oluşturur ve bağımlılıkları yükler
- `.env` dosyasını `.env.example`'dan kopyalar
- Zemberek Java Gateway'i derler (Java 17 gerekli)
- Google Morphology Docker image'ını build eder (Docker gerekli)

Google ve hybrid backend'leri **kullanmayacaksan** Docker'ı atlayabilirsin:

```bash
./setup.sh --skip-docker
```

### Gereksinimler

| Bileşen | Gerekli Olduğu Backend |
|---|---|
| Python 3.9+ | Hepsi |
| Java 17 | `zemberek`, `hybrid_zemberek` |
| Docker | `google`, `hybrid_zemberek`, `hybrid_starlang` |

### `.env` Dosyası

`setup.sh` sonrası `.env` oluşturulur. `LLM_API_KEY` değerini doldur:

```env
# OpenRouter (önerilen)
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=google/gemma-3-27b-it
LLM_API_KEY=sk-or-...

# Ollama (yerel)
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=gemma3:27b
LLM_API_KEY=ollama
```

---

## Benchmark

### Çalıştırma

```bash
./benchmark.sh --backend hybrid_zemberek   # önerilen
./benchmark.sh --backend zemberek
./benchmark.sh --backend google
./benchmark.sh --backend starlang
./benchmark.sh --backend hybrid_starlang
```

Ek seçenekler:

```bash
--limit 100    # İlk N cümleyle sınırla (hızlı test)
--judge        # LLM-as-Judge ikinci geçişini etkinleştir
--step         # Cümle cümle canlı çıktı
```

Veri seti (`benchmark_data/TWT`) yoksa otomatik indirilir.  
Sonuçlar `benchmark_logs/<backend>_benchmark.jsonl` dosyasına yazılır.

### Değerlendirme Yöntemi

**Değerlendirme dışı bırakılan kelimeler:**
- Tek-IG (inflectional group) kelimeler: morfolojik belirsizlik yok, atlandı
- Tek analizli kelimeler: LLM'e sunulmadan otomatik seçilir (doğru/yanlış olarak işaretlenir)

**Değerlendirilen kelimeler:**
- Birden fazla morfolojik adayı olan belirsiz kelimeler
- LLM bağlam kullanarak doğru adayı seçer
- Seçilen morfem dizisi, TWT gold morfem dizisiyle karşılaştırılır

**Karşılaştırma:** `açık+la+n+ma+yan` = `açıklanmayan` gold'u, nokta karşılaştırması ile eşleşmeli.

---

## Benchmark Sonuçları

Tüm koşular: `google/gemma-3-27b-it`, TWT tam veri seti (4.851 cümle, web + wiki).  
`hybrid_zemberek` dışındakilerde `--judge` kapalı; Zemberek orijinal koşusunda `--judge` aktifti.

### Genel Doğruluk

| Backend | Doğru | Toplam | **Genel Acc** |
|---|---|---|---|
| **Hybrid Zemberek+Google** | **10.605** | **11.408** | **%93.0** |
| Google | 10.253 | 11.282 | %90.9 |
| Zemberek (+Judge) | 9.637 | 10.635 | %90.6 |
| Hybrid Starlang+Google | 10.113 | 11.778 | %85.9 |
| Starlang | 9.549 | 11.778 | %81.1 |

### Kapsam Metrikleri

**Sistem Kapsamı** — Aday üretilen kelime oranı (analiz_yok hariç):

| Backend | Kapsam |
|---|---|
| Starlang | **%100.0** |
| Hybrid Starlang+Google | **%100.0** |
| Hybrid Zemberek+Google | %96.8 |
| Google | %95.8 |
| Zemberek | %90.3 |

**Oracle Kapsamı** — Gold'un aday havuzunda bulunma oranı (teorik tavan):

| Backend | Oracle |
|---|---|
| Google | **%63.4** |
| Hybrid Zemberek+Google | %62.8 |
| Zemberek | %60.1 |
| Starlang | %54.8 |
| Hybrid Starlang+Google | %54.4 |

> Oracle, "aday havuzunda gold varsa bile %100 doğruluk mümkün değil" gerçeğini gösterir.  
> Zemberek %90.3 sistem kapsamıyla %60.1 oracle üretiyor;  
> Starlang %100 kapsamına rağmen yalnızca %54.8 oracle — ürettiği adayların kalitesi düşük.

### Tek Aday Doğruluğu (Belirsizlik Yok)

| Backend | Tek Aday Acc |
|---|---|
| **Hybrid Zemberek+Google** | **%94.4** |
| Google | %92.1 |
| Zemberek | %87.2 |
| Hybrid Starlang+Google | %85.3 |
| Starlang | %77.1 |

### Disambiguasyon Doğruluğu (Belirsizlik Var, LLM Devreye Giriyor)

| Backend | Disambig Acc |
|---|---|
| **Zemberek** | **%92.9** |
| Hybrid Zemberek+Google | %92.2 |
| Google | %90.1 |
| Starlang | %83.0 |
| Hybrid Starlang+Google | %86.0 |

> Zemberek disambiguasyonda en iyi — az aday üretir, LLM'e kolay seçim sunar.  
> Hybrid Zemberek+Google çok daha geniş aday havuzuyla %92.2'ye ulaşıyor.

---

## Metrik Açıklamaları

| Metrik | Tanım |
|---|---|
| **Genel Doğruluk** | Doğru seçilen / değerlendirilen tüm kelimeler |
| **Sistem Kapsamı** | Aday üretilen kelimeler / değerlendirilen tüm kelimeler |
| **Oracle Kapsamı** | Gold'un aday havuzunda bulunduğu kelimeler / değerlendirilen tüm kelimeler |
| **Tek Aday Acc** | Tek aday durumunda o adayın gold ile eşleşme oranı |
| **Disambig Acc** | Birden fazla aday olan durumlarda LLM'in gold'u seçme oranı |
| **Kapsam Açığı** | LLM hatalarının gold'un hiç aday havuzuna girmediği kısım |
| **LLM Seçim Hatası** | Gold adayda VAR ama LLM yanlış seçti |

### Token Etiketleri (`label` alanı)

Her token `benchmark_logs/*.jsonl` dosyasında şu etiketlerden birini alır:

| Etiket | Anlamı |
|---|---|
| `tek_ig_atlandi` | Tek-IG kelime, değerlendirme dışı |
| `analiz_yok` | Motor hiç aday üretemedi |
| `tek_aday_dogru` | Tek aday, gold ile eşleşiyor |
| `tek_aday_yanlis` | Tek aday, gold ile eşleşmiyor (düzeltilemez) |
| `llm_dogruladi` | LLM belirsizliği doğru çözdü |
| `llm_yanlis` | LLM yanlış seçti (gold adayda vardı) |
| `llm_judge_dogruladi` | LLM yanlıştı, judge kurtardı |
| `judge_basarisiz` | LLM + judge ikisi de yanlış, gold adayda var |
| `zemberek_kapsam_disi` | Gold hiçbir adayda yok, kazanılamaz |

---

## Her Yaklaşımın Sorunları

### Zemberek

**Temel sorun — `-la/-le` yapım eki köke yapışık:**  
Zemberek, `-la/-le` ile türetilmiş fiilleri atomik kök olarak kaydeder.  
TWT bu kökleri daima ayrı morfem olarak bekler:

```
ekle+mek    → ek+le+mek    (ek: isim kök, le: yapım eki)
açıkla+dı   → açık+la+dı   (açık: sıfat kök, la: yapım eki)
tamamla+dı  → tamam+la+dı
```

**Sistem kapsamı %90.3** — her 10 kelimeden 1'i hiç analiz edilemiyor.

---

### Google

**Temel sorun — `ed`/`et` konvansiyonu çelişkisi (138 sistematik hata):**  
TWT, fonetik yüzey formunu kullanır: `etmek → ed` (ünsüz yumuşaması).  
Google, lemma kökünü kullanır: `etmek → et`.  
`ed` hiçbir zaman aday havuzuna girmiyor:

```
eden    → gold='ed+en'      pred='et+en'      (41 kez)
edildi  → gold='ed+ildi'    pred='et+il+di'   (20 kez)
edilir  → gold='ed+ilir'    pred='et+il+ir'   (19 kez)
```

**Aşırı bölümleme:**
```
tıklatın  → gold='tık+la+tın'  pred='tık+la+d+ın'  (7 kez)
```

LLM hatalarının **%83.4'ünde** gold zaten aday havuzunda yok — kapsam açığı baskın.

---

### Starlang

**Temel sorun — Sözlük-TWT uyumsuzluğu (874 tek-yanlış-aday tokeni):**  
Starlang'ın sözlüğündeki kök atamaları TWT gold'undan yapısal olarak farklı:

| Starlang üretiyor | TWT gold | Sıklık |
|---|---|---|
| `imparatorluğ+u` | `imparator+luğu` | 29× |
| `yeterli` | `yeter+li` | 15× |
| `görün+en` | `gör+ün+en` | 15× |
| `oyuncu+su` | `oyun+cusu` | 11× |

Sistem kapsamı **%100** ama oracle yalnızca **%54.8** — aday üretiyor ama doğru aday çoğu kez yok.  
LLM hatalarının **%85.8'inde** gold adayda hiç yok.

---

### Hybrid Zemberek+Google

**Temel sorun — Google'dan miras kalan kapsam açıkları:**  
`anla`, `ayr`, `karşıla`, `pay` kökleri ne Zemberek'te ne Google'da doğru atomize ediliyor.  
LLM hatalarının **%67.4'ünde** gold adayda yok.

**`ed`/`et` problemi kısmen miras:** Google kökler üretirken `et` üretiyor, `ed` üretmiyor.

**En az sorun yaşayan backend — %93.0 genel doğruluk.**

---

### Hybrid Starlang+Google

**Temel sorun — `olan`/`alan` zamir-fiil belirsizliği (83 sistematik hata):**  
Starlang `ol+an` ve `o+lan` üretiyor, Google da `o+lan`'ı güçlendiriyor.  
LLM 73 kez `o+lan` seçiyor, gold daima `ol+an`:

```
"Dizide yer alan mekânlardan biri olan..."
   olan → adaylar: ['o+lan', 'ol+an']
          LLM seçti: 'o+lan'   ← her seferinde yanlış
          gold:      'ol+an'
```

**Çok sayıda aday → LLM zorlanıyor:**  
Starlang+Google cross-product fazla aday üretiyor.  
LLM hatalarının **%34.5'inde** gold adayda var ama LLM yanlış seçiyor  
(Hybrid Zem+Google'da bu oran %32.6, Starlang tek başına %14.2).

---

## Evrensel Başarısızlıklar

**170 kelime formu** hiçbir backend'de çözülemiyor:

| Kategori | Örnekler | Sebep |
|---|---|---|
| Apostroflu özel isim | `İmparatorluğu'nun`, `ABD'li`, `Türkçe'de` | Apostrofu ek-gövde sınırı olarak işlemiyor |
| Noktalı kısaltma | `M.Ö.`, `L/100` | Morfolojik analiz dışı |
| Yüzde/sayı | `%100`, `%90` | Sayısal token |
| Zor fiil | `görüntülüyorsa`, `konabilmesi` | Zincir ekler + kip kombinasyonları |

---

## Öneri ve Sonraki Adımlar

**Kullan: `--backend hybrid_zemberek`** (%93.0)

Zemberek'in kaliteli kök ataması + Google'ın atomizasyon gücü en iyi dengeyi kuruyor.

**%95+ için 3 somut iyileştirme:**

1. **Apostrofu ön-işlemde böl**  
   `İmparatorluğu'nun` → `imparatorluğu` + `nun` → 45+ evrensel hata tek adımda çözülür

2. **`ed`/`et` normalizasyonu**  
   Google çıktısında `et` → `ed` mapping ekle → 138 sistematik hata gider

3. **`olan`/`alan` için prompt ipucu**  
   `ol-` fiili zamir `o`'dan bağlamla ayrışıyor → 83 Hybrid Starlang hatası kurtarılabilir

---

## Proje Yapısı

```
.
├── setup.sh                           ← Tek seferlik kurulum (venv + Docker + Java)
├── benchmark.sh                       ← Benchmark çalıştırıcı (--backend flag)
├── run.sh                             ← Metin analizi (Wikipedia URL → disambiguasyon)
├── requirements.txt
├── .env.example
├── source.txt                         ← Analiz edilecek Wikipedia URL listesi
├── scrapWikipedia.py
│
├── Zemberek Morfoloji/                ← Java katmanı
│   ├── java_gateway/ZemberekGateway.java
│   └── lib/zemberek-full.jar
│
├── Google Morfoloji/                  ← Docker gateway
│   ├── Dockerfile
│   ├── docker_server.py
│   └── start_google_gateway.sh
│
├── LLMBaseRanking/                    ← Python analiz motoru
│   ├── ranker.py                      ← LLM prompt + JSON parse + rerank
│   ├── zemberek_client.py
│   ├── google_morphology_client.py
│   ├── starlang_client.py
│   ├── hybrid_client.py               ← Zemberek + Google
│   ├── hybrid_starlang_client.py      ← Starlang + Google
│   ├── starlang_morpheme_normalizer.py
│   └── config.py
│
├── Benchmark/                         ← Değerlendirme modülü
│   ├── benchmark.py                   ← TWT CoNLL-U değerlendirme motoru
│   ├── dataset_loader.py
│   ├── morpheme_normalizer.py         ← Zemberek format → kök+ek+ek
│   ├── google_morpheme_normalizer.py
│   ├── hybrid_morpheme_normalizer.py
│   └── starlang_morpheme_normalizer.py
│
└── benchmark_logs/
    ├── analyze_results.py             ← Karşılaştırmalı analiz scripti
    ├── extract_wrong.py               ← Yanlış tahminleri çeker
    └── llm_jury.py                    ← 5 modelli bağımsız denetim (opsiyonel)
```

---

## Referanslar

**[Zemberek NLP](https://github.com/ahmetaa/zemberek-nlp)** — Ahmet Afşın Akın tarafından geliştirilen açık kaynaklı Türkçe NLP kütüphanesi.

**[Google Turkish Morphology](https://github.com/google-research/turkish-morphology)** — Google'ın Türkçe morfoloji kütüphanesi.

**[StarlangSoftware NlpToolkit](https://github.com/StarlangSoftware/TurkishMorphologicalDisambiguation)** — StarlangSoftware'in Türkçe morfolojik analiz ve disambiguasyon kütüphanesi.

**[Google Turkish Web Treebank](https://github.com/google-research-datasets/turkish-treebanks)** — Benchmark değerlendirmesinde kullanılan insan-anotasyonlu Türkçe ağaçbankası.

**[Wikipedia TR](https://tr.wikipedia.org)** — Kaynak metin. İçerik [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) lisansı altındadır.
