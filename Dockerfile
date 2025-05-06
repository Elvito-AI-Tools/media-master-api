FROM python:3.10-slim

WORKDIR /app

# Install FFmpeg and other dependencies - removed espeak since we're no longer using Piper TTS
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    wget \
    git \
    fontconfig \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create font directory in the system fonts location
RUN mkdir -p /usr/share/fonts/truetype/custom

# Copy fonts to the container
COPY fonts/*.ttf /usr/share/fonts/truetype/custom/

# Update font cache
RUN fc-cache -f -v

# Create temp directories
RUN mkdir -p /app/temp/output

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 