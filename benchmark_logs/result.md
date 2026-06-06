
(zemberekvenv) salih@Salih-MacBook-Pro Zemberek Reranker % bash benchmark.sh
┌─ [1/3] Google TWT veri seti kontrol ediliyor...
└─ Google TWT hazır.
┌─ [2/3] Java gateway derleniyor ve başlatılıyor...
I|19:02:03.534|Root lexicon created in 85 ms.                                                                      | DictionarySerializer#getDictionaryItems
I|19:02:03.534|Dictionary generated in 106 ms                                                                      | RootLexicon#defaultBinaryLexicon
I|19:02:03.620|Initialized in 213 ms.                                                                              | TurkishMorphology#createWithDefaults
Zemberek Gateway başlatıldı.
└─ Gateway hazır (PID 95373).
┌─ [3/3] TWT benchmark çalıştırılıyor...
│  TWT dosyaları: 2 adet (doğrudan karşılaştırma)

→ /Users/salih/Desktop/Zemberek Reranker/benchmark_data/TWT/data/web.conllu değerlendiriliyor...  [Pure LLM]  [TWT doğrudan]

════════════════════════════════════════════════════════════
BENCHMARK — WEB
════════════════════════════════════════════════════════════
Tek-IG kelimeler (atlandı) : 17977
Toplam kelime              : 4522
  Belirsiz (LLM gerekli)   : 2745
  Tek adaylı               : 1777
  Zemberek analizi yok     : 190

Disambiguation accuracy (belirsiz kelimeler):
  Baseline        : 1545/2745 = 56.3%
  Pure LLM        : 2202/2745 = 80.2%  (+23.9% vs baseline)

Tek adaylı doğruluk        : 88.2%

Genel doğruluk — Pure LLM  : 3769/4522 = 83.3%
════════════════════════════════════════════════════════════

→ /Users/salih/Desktop/Zemberek Reranker/benchmark_data/TWT/data/wiki.conllu değerlendiriliyor...  [Pure LLM]  [TWT doğrudan]

════════════════════════════════════════════════════════════
BENCHMARK — WIKI
════════════════════════════════════════════════════════════
Tek-IG kelimeler (atlandı) : 27427
Toplam kelime              : 6886
  Belirsiz (LLM gerekli)   : 4334
  Tek adaylı               : 2552
  Zemberek analizi yok     : 183

Disambiguation accuracy (belirsiz kelimeler):
  Baseline        : 2487/4334 = 57.4%
  Pure LLM        : 3591/4334 = 82.9%  (+25.5% vs baseline)

Tek adaylı doğruluk        : 86.6%

Genel doğruluk — Pure LLM  : 5800/6886 = 84.2%
════════════════════════════════════════════════════════════

JSONL karar logu: /Users/salih/Desktop/Zemberek Reranker/benchmark_logs/twt_benchmark.jsonl
└─ Tamamlandı.
(zemberekvenv) salih@Salih-MacBook-Pro Zemberek Reranker % 