#!/bin/bash
JAVA=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java
DIR="$(cd "$(dirname "$0")" && pwd)"
PY4J_JAR="$DIR/zemberekvenv/share/py4j/py4j0.10.9.9.jar"
ZEM_JAR="$DIR/lib/zemberek-full.jar"
GW_DIR="$DIR/java_gateway"

$JAVA -cp "$PY4J_JAR:$ZEM_JAR:$GW_DIR" ZemberekGateway
