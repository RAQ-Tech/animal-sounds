FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=3000 \
    CONFIG_PATH=/config \
    DATA_PATH=/data

WORKDIR /app

COPY app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY app /app

RUN mkdir -p /config /data

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3000/health', timeout=3).read()" || exit 1

# waitress, not app.run(): Flask's development server is single-threaded and
# not built for production traffic. main.py keeps app.run() under __main__ for
# local development.
CMD ["waitress-serve", "--host=0.0.0.0", "--port=3000", "main:app"]
