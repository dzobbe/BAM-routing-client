#!/usr/bin/env python3
"""
Simple example for sending Solana transactions normally (without BAM Smart Routing) using Phantom wallet.
This demonstrates the difference between using BAM routing and direct RPC calls.
"""

import anyio
import base64
import json
import base58
import getpass
from solana.rpc.async_api import AsyncClient
from solders.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.message import Message
from solders.hash import Hash
from solders.system_program import TransferParams, transfer

async def setup_wallet():
    """Setup wallet and get the public key."""
    private_key_input = getpass.getpass("Enter your wallet private key (base58 encoded): ").strip()
    
    if not private_key_input:
        raise ValueError("Private key is required")
    
    try:
        # Decode the base58 private key
        private_key_bytes = base58.b58decode(private_key_input)
        keypair = Keypair.from_bytes(private_key_bytes)
        return keypair
    except Exception as e:
        raise ValueError(f"Invalid private key: {e}")

async def create_transfer(from_keypair, to_address, amount_lamports):
    """Create a simple transfer transaction."""
    client = AsyncClient("https://api.testnet.solana.com")  
    
    blockhash_resp = await client.get_latest_blockhash()
    blockhash = blockhash_resp.value.blockhash
    
    transfer_ix = transfer(
        TransferParams(
            from_pubkey=from_keypair.pubkey(),
            to_pubkey=Pubkey.from_string(to_address),
            lamports=amount_lamports
        )
    )

    message = Message([transfer_ix], from_keypair.pubkey())
    
    tx = Transaction([from_keypair], message, blockhash)
    
    await client.close()
    return bytes(tx)

async def send_transaction_normal(signed_tx):
    """Send transaction directly to Solana RPC endpoint."""
    client = AsyncClient("https://api.testnet.solana.com")  
    
    try:
        # Send transaction directly to Solana RPC
        result = await client.send_raw_transaction(signed_tx)
        
        if result.value:
            return {"result": result.value}
        else:
            return {"error": "Transaction failed to send"}
            
    except Exception as e:
        return {"error": str(e)}
    finally:
        await client.close()

async def main():
    print("Setting up testnet wallet...")
    keypair = await setup_wallet()
    
    to_address = "2aDCackvygC59makgc7ndifFGft1ru35qJXsqbfVeiJr"
    amount = 100000000  # 0.1 SOL
    
    print("=== Normal Solana Transaction (without BAM) ===")
    print(f"From: {keypair.pubkey()}")
    print(f"To: {to_address}")
    print(f"Amount: {amount} lamports")
    print(f"RPC Endpoint: https://api.testnet.solana.com")  
     
    # Create transaction
    signed_tx = await create_transfer(keypair, to_address, amount)
    print(f"Transaction created: {len(signed_tx)} bytes")

    # Send transaction normally (without BAM)
    print("\nSending transaction directly to Solana RPC...")
    result = await send_transaction_normal(signed_tx)
    
    print(f"Result: {result}")
    
    if isinstance(result, dict) and 'result' in result:
        tx_sig = result['result']
        print(f"Signature: {tx_sig}")
        print(f"Explorer: https://explorer.solana.com/tx/{tx_sig}?cluster=testnet")  
    elif isinstance(result, dict) and 'error' in result:
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    anyio.run(main)
