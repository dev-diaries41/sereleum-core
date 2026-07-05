import os 

POSTGRES_HOST=os.environ.get("POSTGRES_HOST")
POSTGRES_USER=os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD=os.environ.get("POSTGRES_PASSWORD")
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
POSTGRES_DB=os.environ.get("POSTGRES_DB")
POSTGRES_DSN=os.environ.get("POSTGRES_DSN")