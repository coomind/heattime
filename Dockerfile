FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 MPLBACKEND=Agg
WORKDIR /app
COPY pyproject.toml ./
COPY backend/ ./backend/
COPY docs/licenses/ ./docs/licenses/
COPY data/mock/ ./data/mock/
COPY data/observations/ ./data/observations/
COPY docs/kma/asos-stations.json ./docs/kma/asos-stations.json
COPY docs/real-data/replay-results.json ./docs/real-data/replay-results.json
RUN pip install --no-cache-dir .
COPY --from=frontend /build/dist ./frontend/dist/
RUN mkdir -p data
EXPOSE 10000
CMD ["python", "-m", "backend.run", "--host", "0.0.0.0", "--port", "10000"]
