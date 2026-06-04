#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
DATA="$ROOT/benchmark_data"
GOLD="$ROOT/benchmark_gold"
JAVA="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java"
JAVAC="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/javac"
PY4J_JAR="$ROOT/zemberekvenv/share/py4j/py4j0.10.9.9.jar"
ZEM_JAR="$ROOT/Zemberek Morfoloji/lib/zemberek-full.jar"
GW_DIR="$ROOT/Zemberek Morfoloji/java_gateway"
PYTHON="$ROOT/zemberekvenv/bin/python"
BENCH="$ROOT/benchmark"

GW_PID=""

cleanup() {
    [[ -n "$GW_PID" ]] && kill "$GW_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

mkdir -p "$DATA" "$GOLD"

# ── 1. Veri setlerini indir ──────────────────────────────────────
echo "┌─ [1/4] Veri setleri kontrol ediliyor..."
if [[ ! -d "$DATA/TrMor2018" ]]; then
    echo "│  TrMor2018 indiriliyor..."
    git clone --depth 1 https://github.com/ai-ku/TrMor2018 "$DATA/TrMor2018"
fi
if [[ ! -d "$DATA/BOUN-UD" ]]; then
    echo "│  BOUN-UD indiriliyor..."
    git clone --depth 1 https://github.com/UniversalDependencies/UD_Turkish-BOUN "$DATA/BOUN-UD"
fi
if [[ ! -d "$DATA/IMST-UD" ]]; then
    echo "│  IMST-UD indiriliyor..."
    git clone --depth 1 https://github.com/UniversalDependencies/UD_Turkish-IMST "$DATA/IMST-UD"
fi
echo "└─ Veri setleri hazır."

# ── 2. Java gateway derle ve başlat ─────────────────────────────
echo "┌─ [2/4] Java gateway derleniyor ve başlatılıyor..."
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

# ── 3. Gold dosyaları oluştur (varsa atla) ───────────────────────
echo "┌─ [3/4] Gold morfem dosyaları hazırlanıyor..."

TRMOR_TEST=$(find "$DATA/TrMor2018" -name "*.test" -o -name "*test*" 2>/dev/null | head -1)
if [[ -n "$TRMOR_TEST" && ! -f "$GOLD/trmor.gold" ]]; then
    echo "│  TrMor2018 → trmor.gold"
    "$PYTHON" "$BENCH/prepare_gold.py" "$TRMOR_TEST" "$GOLD/trmor.gold" --format trmor
fi

BOUN_TEST=$(find "$DATA/BOUN-UD" -name "*test*.conllu" 2>/dev/null | head -1)
if [[ -n "$BOUN_TEST" && ! -f "$GOLD/boun.gold" ]]; then
    echo "│  BOUN-UD → boun.gold"
    "$PYTHON" "$BENCH/prepare_gold.py" "$BOUN_TEST" "$GOLD/boun.gold" --format conllu
fi

IMST_TEST=$(find "$DATA/IMST-UD" -name "*test*.conllu" 2>/dev/null | head -1)
if [[ -n "$IMST_TEST" && ! -f "$GOLD/imst.gold" ]]; then
    echo "│  IMST-UD → imst.gold"
    "$PYTHON" "$BENCH/prepare_gold.py" "$IMST_TEST" "$GOLD/imst.gold" --format conllu
fi
echo "└─ Gold dosyaları hazır."

# ── 4. Benchmark ─────────────────────────────────────────────────
echo "┌─ [4/4] Benchmark çalıştırılıyor..."
GOLD_FILES=()
for f in "$GOLD"/*.gold; do
    [[ -f "$f" ]] && GOLD_FILES+=("$f")
done

if [[ ${#GOLD_FILES[@]} -eq 0 ]]; then
    echo "│  Uyarı: Hiç .gold dosyası bulunamadı." >&2
else
    "$PYTHON" "$BENCH/benchmark.py" "${GOLD_FILES[@]}" "$@"
fi
echo "└─ Tamamlandı."
