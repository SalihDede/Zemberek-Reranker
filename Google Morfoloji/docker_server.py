"""
Google turkish-morphology için minimal HTTP köprü servisi.

Bu paket (pywrapfst Linux-only binary içerdiği için) sadece Linux x86-64'te
çalışabiliyor; bu yüzden Docker container içinde çalıştırılıp host'tan
(macOS) HTTP üzerinden erişiliyor — Zemberek'in py4j gateway'ine paralel bir
mimari, sadece taşıma katmanı (py4j yerine HTTP) farklı.

Uç noktalar:
  GET /analyze_word?word=...      -> JSON: ["raw_analysis_1", "raw_analysis_2", ...]
  GET /analyze_sentence?text=...  -> JSON: {"kelime": ["raw_analysis_1", ...], ...}

Adaylar dönmeden önce dedupe_candidates() ile tekilleştirilir (Proper=True/False
gibi segmentasyonu değiştirmeyen varyantlar elenir) — bu adım da decompose
(protobuf tabanlı, binary bağımsız) kullandığı için container içinde de
host'takiyle birebir aynı kod çalışır.
"""
from __future__ import annotations

import json
import sys
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from turkish_morphology import analyze
from google_morpheme_normalizer import dedupe_candidates

PORT = int(os.environ.get('GOOGLE_MORPH_PORT', '8765'))


def _analyze_word(word: str) -> list[str]:
    try:
        results = analyze.surface_form(word)
    except Exception:
        return []
    return dedupe_candidates(results) if results else []


def _analyze_sentence(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for raw_word in text.split():
        word = raw_word.strip(".,!?;:\"'()[]{}…-")
        if not word:
            continue
        candidates = _analyze_word(word)
        if candidates:
            out[word] = candidates
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # sessiz — Zemberek gateway'i gibi sadece hazır mesajı basılır

    def _send_json(self, payload: dict | list) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == '/analyze_word':
            word = (params.get('word') or [''])[0]
            self._send_json(_analyze_word(word))
        elif parsed.path == '/analyze_sentence':
            text = (params.get('text') or [''])[0]
            self._send_json(_analyze_sentence(text))
        elif parsed.path == '/health':
            self._send_json({'status': 'ok'})
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print(f'Google Morphology Gateway başlatıldı (port {PORT}).')
    server.serve_forever()
