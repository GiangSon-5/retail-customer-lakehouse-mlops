FROM python:3.10-slim

WORKDIR /app

# Cai dat dependencies he thong
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Sao chep danh sach goi thu vien
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chep ma nguon ung dung
COPY src/ /app/src/
COPY api/ /app/api/
COPY configs/ /app/configs/
COPY models/ /app/models/

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
