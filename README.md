# Sereleum-Core

The core engine powering the [Sereleum app](https://github.com/dev-diaries41/sereleum), providing the indexing, clustering, and labelling pipeline for document analysis. Built on top of [SmartScan](https://github.com/smartscanapp/smartscan-lib), it includes the API and Client packages.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/dev-diaries41/sereleum-core.git
   cd sereleum-core
   ```

2. Install dependencies:

   ```bash
   pip install .
   ```

## Local Development

The `run.sh` script provides commands to initialize the database and run the API and Dramatiq worker locally.

1. Configure the required environment variables in `.env.local`.
2. Initialize the database:

   ```bash
   ./run.sh create
   ```

3. Start the API:

   ```bash
   ./run.sh api
   ```

4. Start the worker in a separate terminal:

   ```bash
   ./run.sh worker
   ```

**Available commands:**

| Command | Description |
|---|---|
| `./run.sh create` | Create and initialize the PostgreSQL database |
| `./run.sh drop` | Drop the PostgreSQL database |
| `./run.sh api` | Start PostgreSQL, Redis, and the API |
| `./run.sh worker` | Start PostgreSQL, Redis, and the Dramatiq worker |

The script uses the Python virtual environment at `./venv` and requires PostgreSQL and Redis to be installed and managed through `systemctl`.

## Deployment

Docker Compose is used for deployment.

**Build the server:**

```bash
docker compose build
```

**Start the server:**

```bash
docker compose up
```

## Design Choices

### Orchestration

Docker Compose manages the services required by the application:

- **Dramatiq Workers** – Process asynchronous indexing and clustering tasks.
- **API** – Exposes the core engine functionality to the Sereleum application.
- **PostgreSQL** – Stores application data and supports vector operations through the `vector` extension.
- **Redis** – Acts as the Dramatiq message broker and provides Pub/Sub channels for broadcasting real-time indexing progress and clustering status updates to API clients via Server-Sent Events (SSE).