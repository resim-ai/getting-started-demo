FROM python:3.10-slim

LABEL maintainer="matthew@resim.ai"

# Create ReSim input directory structure
RUN mkdir -p /tmp/resim/inputs/

WORKDIR /app

# Copy experiences folder
COPY experiences/ /experiences/

# Default command
CMD ["python", "sim_run.py"]