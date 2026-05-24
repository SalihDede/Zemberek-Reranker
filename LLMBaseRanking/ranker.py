import json
from openai import OpenAI
from config import LLM_BASE_URL, LLM_MODEL, LLM_API_KEY

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    return _client


def _build_prompt(sentence: str, word_analyses: dict[str, list[str]]) -> str:
    lines = []
    for word, candidates in word_analyses.items():
        numbered = "\n".join(f"  {i}: {c}" for i, c in enumerate(candidates))
        lines.append(f'"{word}":\n{numbered}')

    analyses_block = "\n\n".join(lines)

    return f"""Sen bir Türkçe dil bilgisi uzmanısın. Verilen cümlede her kelimenin Zemberek morfoloji analizleri listelendi.
Cümle bağlamına göre her kelime için en uygun analizi seç.

Cümle: "{sentence}"

Analizler (0-indexed):
{analyses_block}

Sadece JSON formatında cevap ver. Her kelime için seçilen analizin indeksini yaz:
{{"kelime": indeks, ...}}

Örnek: {{"koyun": 1, "gitti": 0}}"""


def rank_sentence(sentence: str, word_analyses: dict[str, list[str]]) -> dict[str, str]:
    """
    Bir cümle için LLM'den doğru morfolojik analizleri alır.
    Döndürür: {kelime: seçilen_analiz_metni}
    """
    if not word_analyses:
        return {}

    prompt = _build_prompt(sentence, word_analyses)
    client = _get_client()

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()

    # JSON bloğunu çıkar (```json ... ``` sarmalı olabilir)
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        selections: dict = json.loads(raw)
    except json.JSONDecodeError:
        # Parse edilemezse tüm kelimeleri ilk analizle döndür
        return {word: candidates[0] for word, candidates in word_analyses.items()}

    result = {}
    for word, candidates in word_analyses.items():
        idx = selections.get(word, 0)
        if not isinstance(idx, int) or idx >= len(candidates):
            idx = 0
        result[word] = candidates[idx]

    return result
