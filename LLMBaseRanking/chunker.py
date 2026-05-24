import re


def sentence_chunks(text: str) -> list[str]:
    """Metni cümlelere böler."""
    sentences = re.split(r'(?<=[.!?…])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def paragraph_chunks(text: str) -> list[str]:
    """Metni paragraflara böler."""
    paragraphs = re.split(r'\n\s*\n', text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


CHUNK_STRATEGIES = {
    "sentence": sentence_chunks,
    "paragraph": paragraph_chunks,
}
