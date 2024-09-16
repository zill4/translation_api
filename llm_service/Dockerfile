FROM nvidia/cuda:12.2.0-base-ubuntu22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -o ollama.sh https://ollama.ai/install.sh && \
    bash ollama.sh

# Install Llama3 model
RUN ollama pull llama3

# Set work directory
WORKDIR /app

# Copy service code
COPY . /app

# Install Python packages
RUN pip3 install -r requirements.txt

# Expose port (if necessary)
EXPOSE 6000

# Run the LLM service
CMD ["python3", "llm_service.py"]