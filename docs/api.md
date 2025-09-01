
`docs/api.md`
```md
# API

## `BamSmartClient`

### `send_transaction(signed_tx: bytes) -> dict`
Submit a pre-signed transaction. Returns JSON-RPC result from the region's TX endpoint.

### `ping_matrix() -> list[dict]`
Measure latencies to all known regions and mark the fastest.
