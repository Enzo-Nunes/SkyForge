FROM python:3.14-slim-bookworm

WORKDIR /app

COPY common/ ./common/
COPY db-api/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY db-api/*.py ./
COPY db-api/forge_data.json ./forge_data.json

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
