# turkish-morphology paketi Linux x86-64 binary (pywrapfst) içerdiği için
# Apple Silicon Mac'te native çalışmıyor — bu image --platform linux/amd64
# ile build/run edilmeli (Docker Desktop emülasyonla çalıştırır).
FROM python:3.9

WORKDIR /app

RUN pip install --no-cache-dir turkish-morphology

# Build context proje köküdür (bkz. start_google_gateway.sh) — bu yüzden
# google_morpheme_normalizer.py'yi Benchmark/'tan kopyalayabiliyoruz.
COPY Benchmark/google_morpheme_normalizer.py /app/google_morpheme_normalizer.py
COPY ["Google Morfoloji/docker_server.py", "/app/docker_server.py"]

EXPOSE 8765

CMD ["python3", "docker_server.py"]
