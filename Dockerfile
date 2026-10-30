FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl git && \
    rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/daffi1238/GooFuzz_CaptchaBypass /opt/GooFuzz

WORKDIR /opt/GooFuzz

RUN chmod +x GooFuzz
ENTRYPOINT ["bash", "GooFuzz"]
