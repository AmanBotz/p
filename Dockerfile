FROM python:3.9-slim

# Install FFmpeg with proper dependencies
RUN apt-get update && \
    apt-get install -y \
    xz-utils \
    curl \
    && curl -L https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz | tar xJ --strip-components=1 -C /usr/local/bin/ \
    && apt-get remove -y curl xz-utils \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
