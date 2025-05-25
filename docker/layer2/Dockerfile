FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY layer2_realtime/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY layer2_realtime/ .

EXPOSE 8000

CMD ["uvicorn", "api.prediction_api:app", "--host", "0.0.0.0", "--port", "8000"]
