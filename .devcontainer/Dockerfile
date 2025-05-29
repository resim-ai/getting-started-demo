FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Download and install resim CLI
RUN curl -L https://github.com/resim-ai/api-client/releases/latest/download/resim-linux-amd64 -o /usr/local/bin/resim \
    && chmod +x /usr/local/bin/resim

# Create workspace directory
WORKDIR /workspace

# Create a non-root user
RUN useradd -m -s /bin/bash vscode \
    && chown -R vscode:vscode /workspace

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONPATH=/workspace
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER vscode

# Command to keep container running
CMD ["bash"] 