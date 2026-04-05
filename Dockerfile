FROM python:3.11-slim

WORKDIR /app

# Install git for the modbusReader dependency
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ api/
COPY collector/ collector/
COPY config/ config/
COPY db/ db/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
