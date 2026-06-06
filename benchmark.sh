#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
DATA="$ROOT/benchmark_data"
JAVA="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java"
JAVAC="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/javac"
PY4J_JAR="$ROOT/zemberekvenv/share/py4j/py4j0.10.9.9.jar"
ZEM_JAR="$ROOT/Zemberek Morfoloji/lib/zemberek-full.jar"
GW_DIR="$ROOT/Zemberek Morfoloji/java_gateway"
PYTHON="$ROOT/zemberekvenv/bin/python"
BENCH="$ROOT/Benchmark"
LOG_DIR="$ROOT/benchmark_logs"
DEFAULT_JSON_LOG="$LOG_DIR/twt_benchmark.jsonl"

GW_PID=""

cleanup() {
    [[ -n "$GW_PID" ]] && kill "$GW_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

BENCH_ARGS=()
HAS_JSON_LOG=0
for arg in "$@"; do
    case "$arg" in
        --twt-only)
            # Backward-compatible no-op: this script is TWT-only now.
            ;;
        --json-log)
            HAS_JSON_LOG=1
            BENCH_ARGS+=("$arg")
            ;;
        --json-log=*)
            HAS_JSON_LOG=1
            BENCH_ARGS+=("$arg")
            ;;
        *)
            BENCH_ARGS+=("$arg")
            ;;
    esac
done

mkdir -p "$DATA"
mkdir -p "$LOG_DIR"
if [[ "$HAS_JSON_LOG" -eq 0 ]]; then
    BENCH_ARGS+=(--json-log "$DEFAULT_JSON_LOG")
fi

# ── 1. Veri setini indir ─────────────────────────────────────────
echo "┌─ [1/3] Google TWT veri seti kontrol ediliyor..."
if [[ ! -d "$DATA/TWT" ]]; then
    echo "│  Google Turkish Web Treebank indiriliyor..."
    git clone --depth 1 https://github.com/google-research-datasets/turkish-treebanks "$DATA/TWT"
fi
echo "└─ Google TWT hazır."

# ── 2. Java gateway derle ve başlat ─────────────────────────────
echo "┌─ [2/3] Java gateway derleniyor ve başlatılıyor..."
"$JAVAC" -cp "$PY4J_JAR:$ZEM_JAR" -d "$GW_DIR" "$GW_DIR/ZemberekGateway.java"
"$JAVA" -cp "$PY4J_JAR:$ZEM_JAR:$GW_DIR" ZemberekGateway &
GW_PID=$!
for i in $(seq 1 20); do
    nc -z localhost 25333 2>/dev/null && break
    ! kill -0 "$GW_PID" 2>/dev/null && { echo "Hata: Gateway kapandı." >&2; exit 1; }
    sleep 1
done
nc -z localhost 25333 2>/dev/null || { echo "Hata: Gateway 20s içinde başlamadı." >&2; exit 1; }
echo "└─ Gateway hazır (PID $GW_PID)."

# ── 3. Benchmark ─────────────────────────────────────────────────
echo "┌─ [3/3] TWT benchmark çalıştırılıyor..."
TWT_FILES=()
for f in "$DATA/TWT/data/web.conllu" "$DATA/TWT/data/wiki.conllu"; do
    [[ -f "$f" ]] && TWT_FILES+=("$f")
done

ALL_FILES=("${TWT_FILES[@]}")

if [[ ${#ALL_FILES[@]} -eq 0 ]]; then
    echo "│  Uyarı: Hiç değerlendirme dosyası bulunamadı." >&2
else
    if [[ ${#TWT_FILES[@]} -gt 0 ]]; then
        echo "│  TWT dosyaları: ${#TWT_FILES[@]} adet (doğrudan karşılaştırma)"
    fi
    if [[ ${#BENCH_ARGS[@]} -gt 0 ]]; then
        "$PYTHON" "$BENCH/benchmark.py" "${ALL_FILES[@]}" "${BENCH_ARGS[@]}"
    else
        "$PYTHON" "$BENCH/benchmark.py" "${ALL_FILES[@]}"
    fi
fi
echo "└─ Tamamlandı."
