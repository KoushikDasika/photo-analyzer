FROM python:3.13-slim

WORKDIR /app

# Install deps first so Docker layer-caches them between code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: run main.py. Override with `docker compose run app python -c "..."`
CMD ["python", "main.py"]
