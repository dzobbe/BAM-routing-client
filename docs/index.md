# BAM Smart Routing Client

A small Python client that discovers BAM testnet regions, measures latency, chooses the fastest, and submits signed Solana transactions to the closest Jito Block Engine **testnet** TX endpoint.

- Regions and BAM URLs are from the official validators page.  
- TX submission uses Jito JSON-RPC `sendTransaction`.

