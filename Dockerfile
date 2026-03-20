# Use the official Python 3.9 image which is fully compatible with Coqui TTS (coqpit)
FROM python:3.9-slim

# Set system-level environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV COQUI_TOS_AGREED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
# Note: We install torch cpu version to drastically reduce build time and avoid timeouts
RUN pip3 install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Ensure generated directories exist with correct permissions
RUN mkdir -p voice_samples generated_audio static

# Expose the Hugging Face Spaces port
EXPOSE 7860

# Add a healthcheck to ensure the container is running correctly
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:7860/ || exit 1

# Command to run the application using uvicorn
CMD ["uvicorn", "app_api:app", "--host", "0.0.0.0", "--port", "7860"]
