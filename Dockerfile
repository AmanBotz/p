FROM python:3.9-slim

# Install latest FFmpeg
RUN apt-get update && \
    apt-get install -y curl && \
    curl -s https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz | tar xJ && \
    mv ffmpeg-git-*-amd64-static/ff* /usr/local/bin/ && \
    apt-get remove -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python bot.py"]
