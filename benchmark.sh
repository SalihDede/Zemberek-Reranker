#!/bin/bash
# benchmark.sh — Türkçe Morfolojik Disambiguasyon Benchmark
#
# Kullanım:
#   ./benchmark.sh --backend zemberek        # Sadece Zemberek
#   ./benchmark.sh --backend google          # Sadece Google
#   ./benchmark.sh --backend starlang        # Sadece Starlang
#   ./benchmark.sh --backend hybrid_zemberek # Zemberek + Google (en iyi)
#   ./benchmark.sh --backend hybrid_starlang # Starlang + Google
#
# Ek flagler:
#   --limit N    Sadece ilk N cümle
#   --judge      LLM-as-Judge aşamasını etkinleştir
#   --step       Cümle cümle canlı çıktı
#
# Gereksinimler:
#   - Python venv: python3 -m venv zemberekvenv && pip install -r requirements.txt
#   - .env dosyası: cp .env.example .env  (API key'i doldur)
#   - Java 17: yalnızca zemberek/hybrid için
#   - Docker:  yalnızca google/hybrid/hybrid_starlang için
#              (image: docker build --platform linux/amd64 \
#                        -f "Google Morfoloji/Dockerfile" \
#                        -t google-morphology-gateway .)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
DATA="$ROOT/benchmark_data"
PYTHON="$ROOT/zemberekvenv/bin/python"
LOG_DIR="$ROOT/benchmark_logs"

# ── Argümanları ayrıştır ──────────────────────────────────────────────
BACKEND="zemberek"
PASS_ARGS=()
i=1
while [[ $i -le $# ]]; do
    arg="${!i}"
    case "$arg" in
        --backend)
            i=$((i+1)); BACKEND="${!i}" ;;
        --backend=*)
            BACKEND="${arg#--backend=}" ;;
        *)
            PASS_ARGS+=("$arg") ;;
    esac
    i=$((i+1))
done

# Backend → log dosyası adı
case "$BACKEND" in
    zemberek)        LOG_FILE="twt_benchmark.jsonl" ;;
    google)          LOG_FILE="google_benchmark.jsonl" ;;
    starlang)        LOG_FILE="starlang_benchmark.jsonl" ;;
    hybrid_zemberek) LOG_FILE="hybrid_zemberek_benchmark.jsonl" ;;
    hybrid_starlang) LOG_FILE="hybrid_starlang_benchmark.jsonl" ;;
    *) echo "Hata: Geçersiz backend '$BACKEND'" >&2
       echo "      Seçenekler: zemberek, google, starlang, hybrid_zemberek, hybrid_starlang" >&2
       exit 1 ;;
esac

# Gateway PID ve container takibi
GW_PID=""
GOOGLE_CONTAINER=""
cleanup() {
    [[ -n "$GW_PID" ]] && kill "$GW_PID" 2>/dev/null || true
    [[ -n "$GOOGLE_CONTAINER" ]] && docker stop "$GOOGLE_CONTAINER" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

mkdir -p "$DATA" "$LOG_DIR"

# ── 1. Veri seti ─────────────────────────────────────────────────────
echo "┌─ [1] Google TWT veri seti kontrol ediliyor..."
if [[ ! -d "$DATA/TWT" ]]; then
    echo "│  İndiriliyor..."
    git clone --depth 1 https://github.com/google-research-datasets/turkish-treebanks "$DATA/TWT"
fi
echo "└─ Hazır."

# ── 2. Zemberek Java Gateway (gerekiyorsa) ────────────────────────────
if [[ "$BACKEND" == "zemberek" || "$BACKEND" == "hybrid_zemberek" ]]; then
    JAVA="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java"
    JAVAC="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/javac"
    PY4J_JAR="$ROOT/zemberekvenv/share/py4j/py4j0.10.9.9.jar"
    ZEM_JAR="$ROOT/Zemberek Morfoloji/lib/zemberek-full.jar"
    GW_DIR="$ROOT/Zemberek Morfoloji/java_gateway"

    if nc -z localhost 25333 2>/dev/null; then
        echo "┌─ [2] Zemberek Gateway zaten çalışıyor (port 25333)."
        echo "└─ Mevcut instance kullanılıyor."
    else
        echo "┌─ [2] Zemberek Gateway derleniyor ve başlatılıyor..."
        "$JAVAC" -cp "$PY4J_JAR:$ZEM_JAR" -d "$GW_DIR" "$GW_DIR/ZemberekGateway.java"
        "$JAVA" -cp "$PY4J_JAR:$ZEM_JAR:$GW_DIR" ZemberekGateway &
        GW_PID=$!
        for i in $(seq 1 20); do
            nc -z localhost 25333 2>/dev/null && break
            ! kill -0 "$GW_PID" 2>/dev/null && { echo "Hata: Gateway kapandı." >&2; exit 1; }
            sleep 1
        done
        nc -z localhost 25333 2>/dev/null || { echo "Hata: Gateway 20s içinde başlamadı." >&2; exit 1; }
        echo "└─ Zemberek Gateway hazır (PID $GW_PID)."
    fi
fi

# ── 3. Google Morphology Gateway (gerekiyorsa) ────────────────────────
if [[ "$BACKEND" == "google" || "$BACKEND" == "hybrid_zemberek" || "$BACKEND" == "hybrid_starlang" ]]; then
    GOOGLE_PORT="${GOOGLE_MORPH_PORT:-8765}"

    if curl -sf "http://localhost:$GOOGLE_PORT/health" > /dev/null 2>&1; then
        echo "┌─ [3] Google Gateway zaten çalışıyor (port $GOOGLE_PORT)."
        echo "└─ Mevcut instance kullanılıyor."
    else
        echo "┌─ [3] Google Morphology Gateway başlatılıyor (port $GOOGLE_PORT)..."
        GOOGLE_CONTAINER="google-morphology-gw-$$"
        docker run --rm -d --platform linux/amd64 \
            -p "$GOOGLE_PORT:8765" \
            --name "$GOOGLE_CONTAINER" \
            google-morphology-gateway
        for i in $(seq 1 30); do
            curl -sf "http://localhost:$GOOGLE_PORT/health" > /dev/null 2>&1 && break
            sleep 1
        done
        curl -sf "http://localhost:$GOOGLE_PORT/health" > /dev/null || { echo "Hata: Google Gateway başlamadı." >&2; exit 1; }
        echo "└─ Google Gateway hazır."
    fi
fi

# ── 4. Benchmark ─────────────────────────────────────────────────────
echo "┌─ [4] Benchmark başlatılıyor (backend=$BACKEND)..."
"$PYTHON" "$ROOT/Benchmark/benchmark.py" \
    "$DATA/TWT/data/web.conllu" "$DATA/TWT/data/wiki.conllu" \
    --backend "$BACKEND" \
    --json-log "$LOG_DIR/$LOG_FILE" \
    "${PASS_ARGS[@]+"${PASS_ARGS[@]}"}"
echo "└─ Tamamlandı. Log: benchmark_logs/$LOG_FILE"
