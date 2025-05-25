FROM python:3.9-slim

WORKDIR /app

COPY layer3_visualization/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY layer3_visualization/ .

EXPOSE 8050

CMD ["python", "main.py"]
