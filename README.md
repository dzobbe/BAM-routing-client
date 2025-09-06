# BAM Routing Client

This is a simple Python client for BAM (Block Assembly Marketplace) smart routing. 

## Features

- **Region Selection**: Automatically selects the fastest region based on latency
- **Transaction Submission**: Submit signed transactions to the selected endpoint
- **CLI Interface**: Command-line interface for basic operations

## Installation
 
```bash
pip install -e .
```

## Usage

### CLI Commands

#### List Regions
Show latency to all regions:

```bash
bam-router list-regions
```

#### Send Transaction
Submit a signed transaction:

```bash
bam-router send-raw transaction.bin
```

Options:
- `--region`: Force specific region (ny|dallas|slc)
- `--encoding`: Specify encoding (auto|base64|raw)

### Python API

```python
from bam_router.client import BamSmartClient

# Auto-select fastest region
client = BamSmartClient()

# Or specify a region
client = BamSmartClient(region_code="ny")

# Get region information
regions = await client.list_regions()

# Submit transaction
result = await client.send_transaction(signed_tx_bytes)
```

## Examples

For more detailed usage examples, including complete transaction creation and comparison with normal RPC sending, see the [examples directory](examples/README.md).

## Development

### Testing

Run tests with:

```bash
pytest
```

### Code Quality

Install development dependencies:

```bash
pip install -e ".[dev]"
```

```bash
# Linting
pylint bam_router/ tests/

# Security scanning (requires gitleaks)
gitleaks detect --source . --config .gitleaks.toml
```

### CI/CD

This project uses GitHub Actions for continuous integration:

- **Testing**: Runs the unit tests
- **Linting**: Checks code style with pylint, black, isort, and mypy
- **Security**: Scans for secrets and sensitive data with Gitleaks
- **Build**: Creates and validates package builds

## Project Structure

- **`regions.py`**: Region configuration
- **`latency.py`**: TCP ping measurements
- **`router.py`**: Region selection logic
- **`client.py`**: Main client API
- **`cli.py`**: Command-line interface

## License

MIT License
