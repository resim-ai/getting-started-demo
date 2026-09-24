FROM python:3.10-slim

LABEL maintainer="matthew@resim.ai"

# Create ReSim input directory structure
RUN mkdir -p /tmp/resim/inputs/

WORKDIR /app

# SignalFlag SDK, for emitting metrics data
RUN pip install --no-cache-dir signalflag==1.7.0

# Copy experiences folder and simulation script
COPY experiences/ /app/experiences/

COPY sim_run.py .

# Default command
CMD ["python", "sim_run.py"]