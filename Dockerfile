FROM mysterydemon/botcluster:ffmpeg-v7.0.2

WORKDIR /app

COPY requirements.txt ./

RUN apt-get update && apt-get install -y python3-venv \
    && python3 -m venv venv \
    && . venv/bin/activate \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . .

COPY start.sh /usr/local/bin/start.sh

RUN chmod +x run.sh /usr/local/bin/start.sh

RUN useradd -m botuser

RUN chown -R botuser:botuser /app

USER botuser

RUN bash run.sh

CMD ["/usr/local/bin/start.sh"]
