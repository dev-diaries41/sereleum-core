FROM python:3.12.3-slim-bookworm

RUN apt-get update && \
    apt-get install -y sqlite3 git build-essential cmake libgomp1 && \
    rm -rf /var/lib/apt/lists/* && \
    sqlite_version=$(sqlite3 --version | awk '{print $1}') && \
    echo "SQLite version installed: $sqlite_version" && \
    dpkg --compare-versions "$sqlite_version" "ge" "3.35" || { echo "SQLite < 3.35, aborting"; exit 1; }

RUN groupadd -r revelium_user && useradd -r -m -g revelium_user revelium_user

WORKDIR /home/revelium_user/app
COPY --chown=revelium_user:revelium_user . .

RUN pip install --no-cache-dir .[api]

RUN mkdir -p /data /data/uploads /data/models && \
    chown -R revelium_user:revelium_user /data

USER revelium_user

EXPOSE 8000
CMD ["python", "-m", "api.main"]
