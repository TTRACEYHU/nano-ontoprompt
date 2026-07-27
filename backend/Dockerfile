FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends postgresql-client && \
    rm -rf /var/lib/apt/lists/*
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir -r requirements.txt
COPY . .
