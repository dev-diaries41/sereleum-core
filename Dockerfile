FROM python:3.12.3-slim-bookworm

RUN apt-get update && \
    apt-get install -y sqlite3 git && \
    rm -rf /var/lib/apt/lists/* && \
    sqlite_version=$(sqlite3 --version | awk '{print $1}') && \
    echo "SQLite version installed: $sqlite_version" && \
    dpkg --compare-versions "$sqlite_version" "ge" "3.35" || { echo "SQLite < 3.35, aborting"; exit 1; }


# Create a new user with a specific UID and GID
RUN groupadd -r revelium_user && useradd -r -m -g revelium_user revelium_user

# Set the working directory inside the container
WORKDIR /home/revelium_user/app

COPY . .

# Install dependencies
RUN pip install --no-cache-dir .[api]

# Copy the remaining application code and set ownership
COPY --chown=revelium_user:revelium_user . .

USER root
RUN mkdir -p /data/uploads && chown -R revelium_user:revelium_user /data/uploads
RUN chown -R revelium_user:revelium_user /home/revelium_user/app

USER revelium_user

# Expose the port your app runs on
EXPOSE 8000

# Command to run your application
CMD ["python", "-m", "api.main"]
