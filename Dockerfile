FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

EXPOSE 5002

CMD ["gunicorn", "-w", "1", "--threads", "50", "-b", "0.0.0.0:5002", "app:app"]
