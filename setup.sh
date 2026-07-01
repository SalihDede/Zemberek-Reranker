#!/bin/bash
# setup.sh — Tek seferlik kurulum
#
# Kullanım: ./setup.sh [--skip-docker]
#
# Yapılanlar:
#   1. Python venv oluşturur ve bağımlılıkları yükler
#   2. .env dosyası yoksa .env.example'dan kopyalar
#   3. Zemberek Java Gateway'i derler (Java 17 gerekli)
#   4. Google Morphology Docker image'ını build eder (Docker gerekli)
#      --skip-docker ile atlanabilir (yalnızca zemberek/starlang kullanacaksan)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SKIP_DOCKER=0
for arg in "$@"; do
    [[ "$arg" == "--skip-docker" ]] && SKIP_DOCKER=1
done

OK="✓"
FAIL="✗"
INFO="·"

# ── 1. Python venv ────────────────────────────────────────────────────
echo ""
echo "── [1/4] Python ortamı ─────────────────────────────────────────"
if [[ ! -d "$ROOT/zemberekvenv" ]]; then
    echo "$INFO  venv oluşturuluyor..."
    python3 -m venv "$ROOT/zemberekvenv"
fi
PYTHON="$ROOT/zemberekvenv/bin/python"
PIP="$ROOT/zemberekvenv/bin/pip"
echo "$INFO  Bağımlılıklar yükleniyor..."
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet -r "$ROOT/requirements.txt"
echo "$OK  Python venv hazır ($("$PYTHON" --version))"

# ── 2. .env dosyası ───────────────────────────────────────────────────
echo ""
echo "── [2/4] Ortam değişkenleri ────────────────────────────────────"
if [[ ! -f "$ROOT/.env" ]]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
    echo "$OK  .env oluşturuldu — LLM_API_KEY değerini düzenle: $ROOT/.env"
else
    echo "$OK  .env zaten mevcut."
fi

# ── 3. Zemberek Java Gateway derleme ─────────────────────────────────
echo ""
echo "── [3/4] Zemberek Java Gateway ─────────────────────────────────"
JAVA="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java"
JAVAC="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/javac"

if [[ ! -f "$JAVAC" ]]; then
    # Alternatif konumları dene
    JAVAC="$(which javac 2>/dev/null || true)"
    JAVA="$(which java 2>/dev/null || true)"
fi

if [[ -z "$JAVAC" || ! -f "$JAVAC" ]]; then
    echo "$FAIL  Java 17 bulunamadı."
    echo "      macOS: brew install openjdk@17"
    echo "      Ubuntu: sudo apt install openjdk-17-jdk"
    echo "      (Sadece --backend starlang/google kullanacaksan gerekli değil)"
else
    PY4J_JAR="$ROOT/zemberekvenv/share/py4j/py4j0.10.9.9.jar"
    ZEM_JAR="$ROOT/Zemberek Morfoloji/lib/zemberek-full.jar"
    GW_DIR="$ROOT/Zemberek Morfoloji/java_gateway"
    echo "$INFO  Derleniyor..."
    "$JAVAC" -cp "$PY4J_JAR:$ZEM_JAR" -d "$GW_DIR" "$GW_DIR/ZemberekGateway.java"
    echo "$OK  Zemberek Gateway derlendi ($("$JAVA" -version 2>&1 | head -1))"
fi

# ── 4. Google Morphology Docker image ─────────────────────────────────
echo ""
echo "── [4/4] Google Morphology Gateway (Docker) ────────────────────"
if [[ "$SKIP_DOCKER" -eq 1 ]]; then
    echo "$INFO  --skip-docker ile atlandı."
elif ! command -v docker &>/dev/null; then
    echo "$FAIL  Docker bulunamadı — https://docs.docker.com/get-docker/"
    echo "      (Sadece --backend zemberek/starlang kullanacaksan gerekli değil)"
else
    if docker image inspect google-morphology-gateway &>/dev/null; then
        echo "$OK  google-morphology-gateway image zaten mevcut."
    else
        echo "$INFO  Image build ediliyor (linux/amd64, birkaç dakika sürebilir)..."
        docker build --platform linux/amd64 \
            -f "$ROOT/Google Morfoloji/Dockerfile" \
            -t google-morphology-gateway \
            "$ROOT" \
            --quiet
        echo "$OK  google-morphology-gateway image hazır."
    fi
fi

# ── Özet ──────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════"
echo "  Kurulum tamamlandı."
echo ""
echo "  .env dosyasında LLM_API_KEY değerini doldur,"
echo "  ardından benchmark çalıştır:"
echo ""
echo "    ./benchmark.sh --backend zemberek"
echo "    ./benchmark.sh --backend google"
echo "    ./benchmark.sh --backend starlang"
echo "    ./benchmark.sh --backend hybrid_zemberek   ← önerilen"
echo "    ./benchmark.sh --backend hybrid_starlang"
echo ""
echo "  Ek seçenekler: --limit N  --judge  --step"
echo "════════════════════════════════════════════════════════"
