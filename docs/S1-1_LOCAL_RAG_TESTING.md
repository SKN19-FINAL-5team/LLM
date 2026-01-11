# S1-1 Local RAG Testing Guide

This guide describes how to run tests for the S1-1 Local RAG Baseline.

## Prerequisites

- Conda environment `dsr` must be active (`conda activate dsr`)
- Database must be running (`docker-compose up -d db`)
- Test data must be loaded

## Test Structure

Tests are organized into the following directories under `backend/scripts/testing/`:

- **`api/`**: Tests for API endpoints (`/search`, `/chat`), error handling, and concurrency.
- **`integration/`**: Integration tests across components and Docker environment checks.
- **`data/`**: Data validation and quality tests.

## Running Tests

We provide a unified test runner script: `backend/run_local_rag_tests.sh`.

### Usage

```bash
# Run ALL tests
./backend/run_local_rag_tests.sh all

# Run API tests only
./backend/run_local_rag_tests.sh api

# Run Integration tests only
./backend/run_local_rag_tests.sh integration

# Run Data tests only
./backend/run_local_rag_tests.sh data
```

### Manual Execution (Pytest)

If you prefer running pytest directly:

```bash
cd backend
export PYTHONPATH=$PYTHONPATH:$(pwd)
pytest scripts/testing/api/test_api_endpoints.py -v
```

## Troubleshooting

- **Import Errors**: Ensure `PYTHONPATH` includes the `backend` directory. The runner script handles this automatically.
- **DB Connection Errors**: Check if the database container is healthy: `docker ps | grep db`.
