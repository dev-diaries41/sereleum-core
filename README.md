# Sereleum-Core

This is the core engine that powers the [Sereleum app](https://github.com/dev-diaries41/sereleum), providing the indexing, clustering and labelling pipeline to enable prompts analysis. It includes the API and Client packages.

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

## Benchmarking

You can benchmark **indexing** and **clustering** processes using a simple CLI.

---

### Indexing Benchmarks

Supports **stress tests** with dummy data or indexing from a **prompts JSON file**.

**CLI Options:**

* `-n` → Number of items to generate (default: 100)
* `-o` → Dummy data offset (default: 0)
* `--stress` → Run stress test with dummy data
* `-f` → Path to prompts file

**Usage Examples:**

Run stress test with 10,000 items:

```bash
python -m benchmarks.index -n 10000 --stress
```

Run benchmark using a prompts file:

```bash
python -m benchmarks.index -f path/to/prompts.json
```

---

### Clustering Benchmarks

Supports **simulated benchmarks** or **real clustering** using indexed prompts.

**CLI Options:**

* `-s` → Run simulated benchmark
* `-r` → Run benchmark with real prompts
* `-i` → Number of items (simulated only, default: 10000)
* `-d` → Embedding dimension (simulated only, default: 384)

**Usage Examples:**

Run simulated clustering:

```bash
python -m benchmarks.cluster -s -i 1000 -d 384
```

Run real clustering:

```bash
python -m benchmarks.cluster -r
```

> Real clustering requires prompts to be indexed first.

---

## Design Choices

### Orchestration

Docker Compose manages four services:

* **Sereleum** – the FastAPI application
* **ChromaDB** – ChromaDB server required by both the API and Dramatiq workers
* **Dramatiq Workers** – task queue for indexing and clustering tasks
* **Redis** – required by Dramatiq

### Model

* Embedding model: **MiniLM-L6 quantized (onnxruntime)**
* **Max token length**: MiniLM-L6 tokenizer uses a maximum of **512 tokens** instead of 128. Using the higher limit increases indexing time but improves clustering accuracy by avoiding context loss when embedding large prompts.

---
