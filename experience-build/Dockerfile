FROM python:3.10-slim

LABEL maintainer="matthew@resim.ai"

# Create ReSim input directory structure
RUN mkdir -p /tmp/resim/inputs/

# Copy over metrics config to container and make directory

WORKDIR /app

# Copy experiences folder and simulation script
COPY experiences/ /app/experiences/

COPY sim_run.py .

# Default command
CMD ["python", "sim_run.py"]
