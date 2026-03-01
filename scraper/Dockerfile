FROM python:3.14-slim

WORKDIR /app

COPY common/ ./common/
COPY scraper/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY scraper/main.py ./main.py

CMD ["python", "main.py"]
