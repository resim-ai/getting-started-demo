# Replays recorded episodes instead of simulating them. Runs on a CPU and needs no
# model weights; each experience's SEED selects a recording under recordings/.
FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    "mcap>=1.0.0,<2.0.0" \
    "mcap-protobuf-support>=0.5.3" \
    "foxglove-schemas-protobuf>=0.3.0" \
    "imageio>=2.34.0" \
    "resim-open-core>=0.15.2" \
    av \
    numpy

COPY src/aloha_honua/__init__.py src/aloha_honua/emissions.py src/aloha_honua/replay.py src/aloha_honua/
COPY .resim/ .resim/
COPY recordings/ recordings/

ENV PYTHONPATH=/app/src
ENTRYPOINT ["python", "-m", "aloha_honua.replay"]
