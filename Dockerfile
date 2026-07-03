FROM python:3.12.3-slim-bookworm

# Install build tools and PostgreSQL client libraries
RUN apt-get update && \
    apt-get install -y git build-essential libgomp1 libpq-dev python3-dev && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -r sereleum_user && useradd -r -m -g sereleum_user sereleum_user

WORKDIR /home/sereleum_user/app
COPY --chown=sereleum_user:sereleum_user . .

RUN pip install --no-cache-dir .[api]

RUN mkdir -p /data /data/uploads /data/models && \
    chown -R sereleum_user:sereleum_user /data

    
USER sereleum_user

EXPOSE 8000
CMD ["python", "-m", "api.main"]
