FROM python:3.10-slim

LABEL maintainer="matthew@resim.ai"

# Create ReSim input directory structure
RUN mkdir -p /tmp/resim/inputs/

WORKDIR /app

# Copy hello.py
COPY drone_flight.py .

# Default command
CMD ["python", "drone_flight.py"]