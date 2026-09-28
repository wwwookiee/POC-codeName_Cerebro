FROM python:3.12-slim

# ffmpeg : découpage audio. deno : runtime JS requis par yt-dlp pour l'extraction YouTube.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl unzip ca-certificates \
    && case "$(uname -m)" in \
         x86_64) DENO_ARCH=x86_64-unknown-linux-gnu ;; \
         aarch64) DENO_ARCH=aarch64-unknown-linux-gnu ;; \
         *) echo "Architecture non supportée : $(uname -m)" && exit 1 ;; \
       esac \
    && curl -fsSL -o /tmp/deno.zip "https://github.com/denoland/deno/releases/latest/download/deno-${DENO_ARCH}.zip" \
    && unzip -q /tmp/deno.zip -d /usr/local/bin \
    && rm /tmp/deno.zip \
    && apt-get purge -y curl unzip \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
