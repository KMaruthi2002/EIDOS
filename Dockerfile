# EIDOS Studio in one container.
#   docker build -t eidos .
#   docker run -p 8000:8000 --env-file .env -e EIDOS_TOKEN=choose-a-token eidos
# then open http://localhost:8000/?token=choose-a-token
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && python -m playwright install --with-deps chromium
COPY eidos eidos
COPY apps apps
COPY web/studio web/studio
COPY web/world web/world
COPY samples samples
COPY runs/tutorial_totals runs/tutorial_totals
COPY runs/ui_skill_mail runs/ui_skill_mail
COPY runs/ui_skill_calendar runs/ui_skill_calendar
COPY runs/ui_skill_expense runs/ui_skill_expense
COPY runs/ui_skill_settings runs/ui_skill_settings
COPY videos videos

ENV EIDOS_HOST=0.0.0.0 \
    EIDOS_MAX_LIVE=4 \
    EIDOS_DAILY_CALL_LIMIT=20000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
CMD ["python", "-m", "eidos", "studio", "8000"]
