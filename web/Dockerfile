# Stage 1: build Vue frontend
FROM node:25-slim AS frontend-build

WORKDIR /frontend
COPY VERSION /tmp/VERSION
COPY web/frontend/package*.json ./
RUN npm install
COPY web/frontend/ ./
RUN VITE_APP_VERSION=$(cat /tmp/VERSION) npm run build

# Stage 2: Python backend
FROM python:3.14-slim-bookworm

WORKDIR /app

COPY web/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=frontend-build /frontend/dist ./static
COPY web/main.py ./main.py

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
