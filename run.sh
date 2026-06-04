#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
JAVA="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java"
JAVAC="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/javac"
PY4J_JAR="$ROOT/zemberekvenv/share/py4j/py4j0.10.9.9.jar"
ZEM_JAR="$ROOT/Zemberek Morfoloji/lib/zemberek-full.jar"
GW_DIR="$ROOT/Zemberek Morfoloji/java_gateway"
SOURCE="${1:-$ROOT/source.txt}"
STRATEGY="${2:-sentence}"
GW_PID=""

cleanup() {
    if [[ -n "$GW_PID" ]]; then
        echo ""
        echo "→ Gateway kapatılıyor (PID $GW_PID)..."
        kill "$GW_PID" 2>/dev/null || true
        wait "$GW_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

# ── 1. Derle ────────────────────────────────────────────────────
echo "┌─ [1/3] Java gateway derleniyor..."
"$JAVAC" -cp "$PY4J_JAR:$ZEM_JAR" -d "$GW_DIR" "$GW_DIR/ZemberekGateway.java"
echo "└─ Derleme tamamlandı."

# ── 2. Gateway'i başlat ──────────────────────────────────────────
echo "┌─ [2/3] Zemberek Gateway başlatılıyor..."
"$JAVA" -cp "$PY4J_JAR:$ZEM_JAR:$GW_DIR" ZemberekGateway &
GW_PID=$!

for i in $(seq 1 20); do
    if nc -z localhost 25333 2>/dev/null; then
        echo "└─ Gateway hazır (PID $GW_PID)."
        break
    fi
    if ! kill -0 "$GW_PID" 2>/dev/null; then
        echo "Hata: Gateway süreci beklenmedik şekilde kapandı." >&2
        exit 1
    fi
    sleep 1
done

if ! nc -z localhost 25333 2>/dev/null; then
    echo "Hata: Gateway 20 saniye içinde başlamadı." >&2
    exit 1
fi

# ── 3. Python çalıştır ───────────────────────────────────────────
echo "┌─ [3/3] Sistem çalıştırılıyor..."
echo "│  Kaynak  : $SOURCE"
echo "│  Strateji: $STRATEGY"
echo "│"
cd "$ROOT/LLMBaseRanking"
"$ROOT/zemberekvenv/bin/python" main.py "$SOURCE" --strategy "$STRATEGY"
echo "└─ Tamamlandı."
