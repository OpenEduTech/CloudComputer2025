FROM python:3.11-slim

WORKDIR /app

# System deps (build essentials for some wheels)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python", "main.py"]