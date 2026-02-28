FROM python:3.14-slim

WORKDIR /app

COPY common/ ./common/
COPY db-api/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY db-api/db.py ./db.py
COPY db-api/main.py ./main.py

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
