FROM python:3.11-alpine

# Install system dependencies
RUN apk add --no-cache nodejs npm ffmpeg \
     && node -v \
     && ffmpeg -version

# Install yt-dlp
RUN wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/local/bin/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

# Install dependencies
RUN pip install Flask webvtt-py Flask-Cors

# Copy the web server code
COPY server.py /app/
COPY api_keys.json /app/
WORKDIR /app

# Expose a port
EXPOSE 5000

# Run the web server
CMD ["python", "server.py"]
