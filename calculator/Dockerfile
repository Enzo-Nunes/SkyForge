FROM python:3.14-slim-bookworm

WORKDIR /app

COPY common/ ./common/
COPY calculator/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY calculator/*.py ./

CMD ["python", "main.py"]
