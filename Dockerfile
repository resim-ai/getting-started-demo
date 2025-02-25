FROM python:3.10-slim

LABEL maintainer="matthew@resim.ai"

# Create ReSim input directory structure
RUN mkdir -p /tmp/resim/inputs/

# Copy hello.py
COPY hello.py .

# Expose the port
EXPOSE 5000

# Default command
CMD ["python", "hello.py"]