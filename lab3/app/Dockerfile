FROM python:3.13-slim

WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY log_config.py .

RUN mkdir -p logs

ENV LOG_LEVEL=INFO

EXPOSE 5500

CMD ["python", "main.py"]
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5500", "--no-access-log"]