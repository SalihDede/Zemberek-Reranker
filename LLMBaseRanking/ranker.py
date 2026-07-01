import json
import re
import threading
from openai import OpenAI
from config import LLM_BASE_URL, LLM_MODEL, LLM_API_KEY

_client = None
_client_lock = threading.Lock()


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    return _client


_TAG_LEGEND = """
Zemberek morfoloji etiket sözlüğü:

# Sözcük türleri
Noun=isim  Verb=fiil  Adj=sıfat  Adv=zarf  Postp=edat  Conj=bağlaç  Pron=zamir
Num=sayı  Det=belirteç  Ques=soru  Interj=ünlem  Dup=ikileме  Punc=noktalama
Prop=özel isim  Abbrv=kısaltma  Time=zaman ismi  Card=asıl sayı  Ord=sıra sayısı  Dist=üleştirme sayısı  RomanNumeral=Roma rakamı

# İyelik ekleri (P = possessive)
Pnon=iyelik yok  P1sg=benim (-m)  P2sg=senin (-n)  P3sg=onun (-ı/sı)
P1pl=bizim (-mız)  P2pl=sizin (-nız)  P3pl=onların (-ları)

# Kişi uyumu (A = agreement)
A1sg=ben  A2sg=sen  A3sg=o  A1pl=biz  A2pl=siz  A3pl=onlar

# Hâl ekleri
Nom=yalın  Acc=belirtme (-ı)  Dat=yönelme (-a)  Loc=bulunma (-da)
Abl=ayrılma (-dan)  Gen=tamlayan (-ın)  Ins=vasıta (-la)  Equ=eşitlik (-ca)

# Zaman / kip
Pres=şimdiki  Prog1=şimdiki süreğen (-yor)  Prog2=şimdiki süreğen (-makta)
Aor=geniş zaman (-r)  Past=belirli geçmiş (-dı)  Narr=öğrenilen geçmiş (-mış)
Fut=gelecek (-acak)  Cond=şart (-sa)  Imp=emir  Opt=istek (-a)
Desr=dilek (-sa)  Neces=gereklilik (-malı)  Cop=ek fiil (-dır)

# Çatı
Pass=edilgen (-ıl/-ın)  Caus=ettirgen (-tır)  Recip=işteş (-ış)
Able=yeterlilik (-abil)  Reflex=dönüşlü (-ın)  Neg=olumsuzluk (-ma)

# Sıfat-fiil (participle)
PastPart=geçmiş sıfat-fiil (-dık)  NarrPart=öğrenilen sıfat-fiil (-mış)
PresPart=şimdiki sıfat-fiil (-an)  FutPart=gelecek sıfat-fiil (-acak)  AorPart=geniş sıfat-fiil (-r)

# Zarf-fiil (converb)
While=-ken  When=-ınca  ByDoingSo=-arak  SinceDoingSo=-alı  AsLongAs=-dıkça
AfterDoingSo=-ıp  WithoutHavingDoneSo=-madan  AsIf=-casına

# Mastar / isim-fiil
Inf1=mastar (-mak)  Inf2=isim-fiil (-ma)  Inf3=isim-fiil (-ış)  ActOf=eylem adı

# İsimden türetme
Ness=nitelik/durum (-lık)  Dim=küçültme (-cık)  With=-lı  Without=-sız
Related=-sal/-sel  JustLike=-vari  Rel=-ki  Agt=yapan (-cı)

# Fiilden türetme
Become=-laş  Acquire=-lan  Ly=zarflaştırma (-ca)

# Edat bağlama biçimleri (PC = Post Conjunction)
PCNom=yalın edat  PCDat=yönelme edat  PCLoc=bulunma edat
PCAbl=ayrılma edat  PCIns=vasıta edat  PCGen=tamlayan edat

# Diğer
Zero=sıfır türetme (ek olmadan tür değişimi)
""".strip()


# Google turkish-morphology'nin etiket şeması Zemberek'ten tamamen farklı
# (Category=Value çiftleri, örn. "Derivation=Make", "PersonNumber=A3sg").
_GOOGLE_TAG_LEGEND = """
# Sözcük türleri (IG başındaki köşeli parantez)
NN=isim  VB=fiil  ADJ=sıfat  ADV=zarf  NOMP=isim-fiil/mastar  VN=fiilden isim
CC=bağlaç/edat  DET=belirteç  NUM=sayı  PRON=zamir  INTJ=ünlem  PUNCT=noktalama

# Türetme (Derivation) değerleri
Make=isimden/sıfattan fiil yapma (-la/-le)  Bcm=olma (-laş/-leş)  Acq=kazanma (-lan/-len)
Rcp=işteş (-ş)  Pass=edilgen (-n/-ıl)  Caus=ettirgen (-t/-dır)  Able=yeterlilik (-abil)
Inf=mastar (-mak)  Nonf=isim-fiil (-ma)  PresNom=şimdiki ad-fiil (-an)  AorNom=geniş ad-fiil (-ır)
PresPart=şimdiki sıfat-fiil (-an)  PastNom=geçmiş ad-fiil (-dık)  FutPart=gelecek sıfat-fiil (-acak)
With=-lı  Without=-sız  Ness=-lık  Rel=ilgi (-ki)  Agt=yapan (-cı)

# Kişi/uyum (PersonNumber) ve iyelik (Possessive)
A1sg=ben(isim)  A2sg=sen(isim)  A3sg=o(isim)  A1pl=biz(isim)  A2pl=siz(isim)  A3pl=onlar(isim)
V1sg=ben(fiil)  V2sg=sen(fiil)  V3sg=o(fiil)  V1pl=biz(fiil)  V2pl=siz(fiil)  V3pl=onlar(fiil)
Pnon=iyelik yok  P1sg=benim(-m)  P2sg=senin(-n)  P3sg=onun(-ı/sı)  P1pl=bizim  P2pl=sizin  P3pl=onların

# Hâl (Case)
Bare=çekimsiz/yalın  Nom=yalın  Acc=belirtme(-ı)  Dat=yönelme(-a)  Loc=bulunma(-da)
Abl=ayrılma(-dan)  Gen=tamlayan(-ın)  Ins=vasıta(-la)

# Zaman / kip / olumsuzluk
Polarity=olumluluk(Pos=olumlu,Neg=olumsuz)  TenseAspectMood=zaman-kip
Imp=emir  Aor=geniş zaman  Opt=istek  Cond=şart  Past=geçmiş  Prog=şimdiki süreğen
Copula=ek fiil(PresCop=şimdiki zaman ek fiili)  Proper=özel isim mi
""".strip()


# Starlang (TurkishMorphologicalDisambiguation) transitionList() etiketleri
# büyük harf yazılır ama Zemberek ile aynı kavramsal şemayı (Oflazer geleneği)
# paylaşır — "koy+NOUN+A3SG+PNON+GEN" gibi. _filter_legend tam büyük harf
# isimleri de eşleştirdiği için bu ayrı legend yalnızca isimlendirme farkını
# (Noun→NOUN, Gen→GEN) ve Starlang'e özgü birkaç etiketi (INF, NARR, FUTPART...)
# yansıtır.
_STARLANG_TAG_LEGEND = """
# Sözcük türleri
NOUN=isim  VERB=fiil  ADJ=sıfat  ADV=zarf  POSTP=edat  CONJ=bağlaç  PRON=zamir
NUM=sayı  DET=belirteç  QUES=soru  INTERJ=ünlem  DUP=ikileme  PUNC=noktalama
PROP=özel isim  CARD=asıl sayı  ORD=sıra sayısı  DIST=üleştirme sayısı  TIME=zaman ismi

# İyelik ekleri (P = possessive)
PNON=iyelik yok  P1SG=benim (-m)  P2SG=senin (-n)  P3SG=onun (-ı/sı)
P1PL=bizim (-mız)  P2PL=sizin (-nız)  P3PL=onların (-ları)

# Kişi uyumu (A = agreement)
A1SG=ben  A2SG=sen  A3SG=o  A1PL=biz  A2PL=siz  A3PL=onlar

# Hâl ekleri
NOM=yalın  ACC=belirtme (-ı)  DAT=yönelme (-a)  LOC=bulunma (-da)
ABL=ayrılma (-dan)  GEN=tamlayan (-ın)  INS=vasıta (-la)  EQU=eşitlik (-ca)

# Zaman / kip
PRES=şimdiki  PROG1=şimdiki süreğen (-yor)  PROG2=şimdiki süreğen (-makta)
AOR=geniş zaman (-r)  PAST=belirli geçmiş (-dı)  NARR=öğrenilen geçmiş (-mış)
FUT=gelecek (-acak)  COND=şart (-sa)  IMP=emir  OPT=istek (-a)
DESR=dilek (-sa)  NECES=gereklilik (-malı)  COP=ek fiil (-dır)

# Çatı
PASS=edilgen (-ıl/-ın)  CAUS=ettirgen (-tır)  RECIP=işteş (-ış)
ABLE=yeterlilik (-abil)  REFLEX=dönüşlü (-ın)  NEG=olumsuzluk (-ma)  POS=olumlu

# Sıfat-fiil (participle)
PASTPART=geçmiş sıfat-fiil (-dık)  FUTPART=gelecek sıfat-fiil (-acak)  PRESPART=şimdiki sıfat-fiil (-an)

# Mastar / isim-fiil
INF=mastar (-mak)  ACTOF=eylem adı

# İsimden/fiilden türetme
NESS=nitelik/durum (-lık)  WITH=-lı  WITHOUT=-sız  REL=-ki  AGT=yapan (-cı)
BECOME=-laş  ACQUIRE=-lan  LY=zarflaştırma (-ca)  JUSTLIKE=-vari  RELATED=-sal/-sel

# Edat bağlama biçimleri (PC = Post Conjunction)
PCNOM=yalın edat  PCDAT=yönelme edat  PCABL=ayrılma edat  PCGEN=tamlayan edat  PCINS=vasıta edat

# Zarf-fiil (converb)
WHILE=-ken  WHEN=-ınca  BYDOINGSO=-arak  AFTERDOINGSO=-ıp  ASIF=-casına

# Diğer
ZERO=sıfır türetme (ek olmadan tür değişimi)
""".strip()


# Hybrid backend: adaylar zaten kök+ek+ek formatında, etiket yok.
# LLM'e formatı kısaca açıkla.
_HYBRID_LEGEND = """
Adaylar "kök+ek+ek" formatında gerçek yüzey morfemleridir (örn. "imza+la+n+an").
Starlang aday havuzu Google morphology ile kök seviyesinde zenginleştirilmiştir.
Cümle bağlamına göre en uygun morfem bölünmesini seç.
""".strip()


def _filter_legend(word_analyses: dict[str, list[str]], legend_text: str = _TAG_LEGEND) -> str:
    """Analizlerde geçen etiketleri bulup ilgili legend satırlarını döndürür."""
    all_text = " ".join(c for candidates in word_analyses.values() for c in candidates)
    relevant = []
    for line in legend_text.splitlines():
        if not line or line.startswith("#"):
            continue
        # Satırdaki kısaltmaları (büyük harf+küçük harf kombinasyonları) çek
        tags = re.findall(r'\b[A-Z][A-Za-z0-9]+\b', line)
        if any(tag in all_text for tag in tags):
            relevant.append(line)
    return "\n".join(relevant) if relevant else legend_text


def _build_prompt(sentence: str, ambiguous: dict[str, list[str]], legend: str) -> str:
    lines = []
    for word, candidates in ambiguous.items():
        numbered = "\n".join(f"  {i}: {c}" for i, c in enumerate(candidates))
        lines.append(f'"{word}":\n{numbered}')

    analyses_block = "\n\n".join(lines)
    word_list = ", ".join(f'"{w}"' for w in ambiguous)

    return f"""Türkçe morfoloji uzmanısın. Cümlenin bağlamına göre her kelime için doğru analiz indeksini seç.

Etiket sözlüğü:
{legend}

Cümle: "{sentence}"

Analizler:
{analyses_block}

Sadece JSON döndür, başka hiçbir şey yazma. Tüm kelimeler ({word_list}) için indeks ver:
{{"kelime": indeks}}"""


def _build_cot_prompt(
    sentence: str,
    ambiguous: dict[str, list[str]],
    initial_selections: dict[str, str],
    legend: str,
) -> str:
    """
    Chain-of-thought ikinci geçiş: İlk seçimi göster, bağımsız yeniden değerlendir.
    Model hem ilk seçimi hem de tüm adayları görür; kendi gerekçesiyle en iyisini seçer.
    """
    lines = []
    for word, candidates in ambiguous.items():
        if word not in initial_selections:
            continue
        prev = initial_selections[word]
        prev_idx = candidates.index(prev) if prev in candidates else 0
        numbered = "\n".join(f"  {i}: {c}" for i, c in enumerate(candidates))
        lines.append(
            f'"{word}" (ilk seçim: [{prev_idx}]):\n{numbered}'
        )

    block = "\n\n".join(lines)
    word_list = ", ".join(f'"{w}"' for w in ambiguous if w in initial_selections)

    return f"""Türkçe morfoloji uzmanısın. Bir önceki model bu cümle için aşağıdaki morfolojik seçimleri yaptı.
Sen bu seçimleri sıfırdan ve bağımsız olarak yeniden değerlendiriyorsun.

Değerlendirme adımları:
1. Cümledeki her kelimenin gramer rolünü belirle (özne/nesne/yüklem/zarf vs.)
2. Her kelime için hangi morfolojik analiz bu role en uygun?
3. Eğer ilk seçim mantıklıysa onu onayla, daha iyi bir aday varsa onu seç.

Etiket sözlüğü:
{legend}

Cümle: "{sentence}"

Kelimeler ve adaylar (ilk seçim parantez içinde):
{block}

Sadece JSON döndür, başka hiçbir şey yazma. Tüm kelimeler ({word_list}) için indeks ver:
{{"kelime": indeks}}"""


def judge_and_rerank(
    sentence: str,
    word_analyses: dict[str, list[str]],
    initial_selections: dict[str, str],
    legend_text: str = _TAG_LEGEND,
) -> dict[str, str]:
    """
    LLM-as-Judge (CoT ikinci geçiş):
    - İlk seçimi bağımsız olarak yeniden değerlendirir
    - Chain-of-thought ile gramer rolünü analiz eder
    - Döndürür: {kelime: seçilen_analiz_metni}

    legend_text: Zemberek dışı bir motor (örn. Google turkish-morphology,
    Starlang) kullanılıyorsa sırasıyla _GOOGLE_TAG_LEGEND / _STARLANG_TAG_LEGEND
    verilmeli — etiket şeması farklı.
    """
    ambiguous = {
        w: c for w, c in word_analyses.items()
        if len(c) > 1 and w in initial_selections
    }
    if not ambiguous:
        return initial_selections

    legend = _filter_legend(ambiguous, legend_text)
    client = _get_client()

    cot_prompt = _build_cot_prompt(sentence, ambiguous, initial_selections, legend)
    try:
        raw = _call_llm(cot_prompt, client, use_json_format=True, temperature=0.3)
    except Exception:
        try:
            raw = _call_llm(cot_prompt, client, use_json_format=False, temperature=0.3)
        except Exception:
            raw = None

    new_selections = _parse_raw(raw)

    # Retry: aynı prompt ile (aynı sistemle) tekrar dene
    if new_selections is None:
        try:
            raw = _call_llm(cot_prompt, client, use_json_format=False, temperature=0.3)
            new_selections = _parse_raw(raw)
        except Exception:
            new_selections = None

    if not new_selections:
        return initial_selections

    result = dict(initial_selections)
    for word, candidates in ambiguous.items():
        idx = new_selections.get(word, None)
        if not isinstance(idx, int) or not (0 <= idx < len(candidates)):
            continue
        result[word] = candidates[idx]

    return result


def _parse_raw(raw: "str | None") -> "dict | None":
    if not raw:
        return None
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if match:
        raw = match.group(1)
    raw = raw.strip()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, RecursionError, ValueError):
        return None


def _call_llm(prompt: str, client: OpenAI, use_json_format: bool, temperature: float = 0) -> str:
    kwargs = dict(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    if use_json_format:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    if not response.choices:
        raise ValueError(f"LLM boş/null choices döndürdü (model={LLM_MODEL})")
    content = response.choices[0].message.content
    if content is None:
        raise ValueError(f"LLM null içerik döndürdü (model={LLM_MODEL})")
    return content.strip()


def rank_sentence(
    sentence: str,
    word_analyses: dict[str, list[str]],
    legend_text: str = _TAG_LEGEND,
) -> dict[str, str]:
    """
    Bir cümle için LLM'den doğru morfolojik analizleri alır.
    Döndürür: {kelime: seçilen_analiz_metni}

    legend_text: Zemberek dışı bir motor (örn. Google turkish-morphology,
    Starlang) kullanılıyorsa sırasıyla _GOOGLE_TAG_LEGEND / _STARLANG_TAG_LEGEND
    verilmeli — etiket şeması farklı.
    """
    if not word_analyses:
        return {}

    # Tek adaylı kelimeler direkt seçilir, LLM'e gönderilmez
    result = {w: c[0] for w, c in word_analyses.items() if len(c) == 1}
    ambiguous = {w: c for w, c in word_analyses.items() if len(c) > 1}

    if not ambiguous:
        return result

    legend = _filter_legend(ambiguous, legend_text)
    prompt = _build_prompt(sentence, ambiguous, legend)
    client = _get_client()

    # İlk deneme: response_format ile
    use_json_format = True
    try:
        raw = _call_llm(prompt, client, use_json_format=True)
    except Exception:
        use_json_format = False
        try:
            raw = _call_llm(prompt, client, use_json_format=False)
        except Exception:
            raw = None

    selections = _parse_raw(raw)

    # Retry: JSON parse başarısızsa aynı prompt ile (aynı sistemle) tekrar dene
    if selections is None:
        try:
            raw = _call_llm(prompt, client, use_json_format=use_json_format)
            selections = _parse_raw(raw)
        except Exception:
            selections = None

    if selections is None:
        print(f"  [uyarı] JSON parse başarısız, ilk analiz kullanılıyor: {sentence[:60]}")
        result.update({w: c[0] for w, c in ambiguous.items()})
        return result

    for word, candidates in ambiguous.items():
        idx = selections.get(word, 0)
        if not isinstance(idx, int) or idx >= len(candidates):
            idx = 0
        result[word] = candidates[idx]

    return result
