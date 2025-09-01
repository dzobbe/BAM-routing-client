# BAM Smart Routing Examples

This directory contains examples demonstrating how to use the BAM Smart Routing client and compare it with normal RPC sending. The example is meant to send funds from the signing wallet to another wallet.

## Examples Overview


### 1. BAM Smart Routing Example (`send_bam.py`)

The `send_bam.py` example demonstrates sending transactions via BAM Smart Routing:

1. **Transaction Creation**: Creates a simple Solana transfer transaction
2. **Transaction Signing**: Signs the transaction with a keypair
3. **Smart Routing**: Sends the transaction via BAM's fastest available region

### 2. Normal RPC Example (`send_normal.py`)

The `send_normal.py` example demonstrates sending transactions directly to a Solana RPC endpoint without BAM routing:

1. **Transaction Creation**: Creates a simple Solana transfer transaction
2. **Transaction Signing**: Signs the transaction with a keypair
3. **Direct RPC**: Sends the transaction directly to a Solana RPC endpoint

## Setup

1. Install the required dependencies:
   ```bash
   # From the examples directory
   pip install -r requirements.txt
   
   # Install bam-router in development mode from parent directory
   pip install -e ..
   ```

2. Run any of the examples:
   ```bash
   # BAM Smart Routing example
   python send_bam.py
   
   # Normal RPC example
   python send_normal.py   
   ```

## Customization

You can modify any example by changing these variables in the `main()` function:

- `to_address`: Destination address
- `amount`: Amount to transfer (in lamports)
- `rpc_url`: RPC endpoint for getting recent blockhash

