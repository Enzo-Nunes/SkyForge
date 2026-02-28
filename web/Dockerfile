# Stage 1: build Vue frontend
FROM node:slim AS frontend-build

WORKDIR /frontend
COPY web/frontend/package*.json ./
RUN npm install
COPY web/frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:slim

WORKDIR /app

COPY web/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=frontend-build /frontend/dist ./static
COPY web/main.py ./main.py

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
