# Zemberek LLM Reranker

A context-aware morphological disambiguation tool for Turkish text, powered by LLMs.

## What is it?

Turkish is a morphologically rich language where a single word can have multiple valid analyses depending on context. For example:

```
"koyun" →  [koyun:Noun] koyun:Noun+A3sg       (sheep)
           [koymak:Verb] koy:Verb+Imp+un:A2pl  (imperative: put it)
           [koy:Noun] koy:Noun+A3sg+un:Gen      (of the cove)
```

Choosing the correct analysis requires understanding the surrounding context. This project:

1. Uses **Zemberek** to generate all possible morphological analyses for each word
2. Fetches **Wikipedia** articles as source text
3. Uses an **LLM** (any OpenAI-compatible model) to select the correct analysis based on context

## Architecture

```
source.txt  (list of Wikipedia URLs)
        ↓
  Wikipedia Scraper
        ↓
  Paragraph Chunker
        ↓
  Zemberek Gateway  →  N candidate analyses per word
        ↓
  LLM Ranker        →  pick the best analysis given context
        ↓
  Disambiguated morphological output
```

## Usage

### 1. Start the Zemberek Gateway

```bash
cd "Zemberek Morfoloji"
./start_zemberek_gateway.sh
```

### 2. Create your `.env` file

```bash
cp LLMBaseRanking/.env.example LLMBaseRanking/.env
```

Any OpenAI-compatible provider is supported:

```env
# Ollama (local)
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=gemma4:26b
LLM_API_KEY=ollama

# OpenRouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=anthropic/claude-3-5-sonnet
LLM_API_KEY=sk-or-...
```

### 3. Add Wikipedia URLs to `source.txt`

```
https://tr.wikipedia.org/wiki/Aziz_Sancar
https://tr.wikipedia.org/wiki/Atatürk
```

### 4. Run

```bash
cd LLMBaseRanking
python3 main.py ../source.txt
```

### Sample Output

```
Paragraph 1: Koyun otluyordu.

  Koyun:
      [0] [koymak:Verb] koy:Verb+Imp+un:A2pl
      [1] [koy:Noun] koy:Noun+A3sg+un:Gen
    → [2] [koyun:Noun] koyun:Noun+A3sg        ✓ LLM selection
```

## Requirements

- Python 3.9+
- Java 17+
- Ollama or any OpenAI-compatible LLM API

```bash
pip install openai py4j python-dotenv beautifulsoup4 requests
```

## Project Structure

```
Zemberek Morfoloji/      ← Zemberek Java gateway
LLMBaseRanking/          ← LLM-based ranking engine
  ├── main.py            ← entry point
  ├── ranker.py          ← LLM call and analysis selection
  ├── chunker.py         ← text chunking strategies
  ├── zemberek_client.py
  └── config.py
scrapWikipedia.py        ← Wikipedia scraper
source.txt               ← list of Wikipedia URLs to process
```

## Credits

**[Zemberek NLP](https://github.com/ahmetaa/zemberek-nlp)** — An open-source Turkish NLP library developed by Ahmet Afşın Akın. This project uses Zemberek's `TurkishMorphology` module for generating morphological analysis candidates.

**[Wikipedia](https://tr.wikipedia.org)** — Turkish Wikipedia articles are used as source text. Wikipedia content is available under the [Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/) license.
