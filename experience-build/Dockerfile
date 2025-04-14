FROM python:3.10-slim

LABEL maintainer="matthew@resim.ai"

# Create ReSim input directory structure
RUN mkdir -p /tmp/resim/inputs/

WORKDIR /app

# Copy experiences folder and simulation script
COPY experiences/ /experiences/
COPY sim_run.py .

# Default command
CMD ["python", "sim_run.py"]