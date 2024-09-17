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

# Set work directory
WORKDIR /app

# Copy service code
COPY . /app

# Install Python packages
RUN pip3 install -r requirements.txt

# Ensure python3 is in PATH
ENV PATH="/usr/bin:${PATH}"

# Expose port (if necessary)
EXPOSE 6000

# Create a startup script
RUN echo '#!/bin/bash\n\
ollama serve &\n\
sleep 20\n\
ollama pull dolphin-llama3\n\
python3 llm_service.py' > /app/start.sh && \
    chmod +x /app/start.sh

# Run the startup script
CMD ["/app/start.sh"]