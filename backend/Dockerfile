FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8000 \
    DATA_DIR=/app/data

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY config /app/config
COPY mock_data /app/mock_data

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python", "-m", "backend.main"]
