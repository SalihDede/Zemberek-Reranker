import os
from dotenv import load_dotenv

load_dotenv()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")

ZEMBEREK_HOST = os.getenv("ZEMBEREK_HOST", "localhost")
ZEMBEREK_PORT = int(os.getenv("ZEMBEREK_PORT", "25333"))

GOOGLE_MORPH_HOST = os.getenv("GOOGLE_MORPH_HOST", "localhost")
GOOGLE_MORPH_PORT = int(os.getenv("GOOGLE_MORPH_PORT", "8765"))
