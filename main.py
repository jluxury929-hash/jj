// main.py - Production Backend for Ethereum Mainnet
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from web3 import Web3
import os
from pydantic import BaseModel

app = FastAPI()

# CORS setup for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ETHEREUM MAINNET ONLY - Chain ID 1
MAINNET_CHAIN_ID = 1
NETWORK = "mainnet"

# Your deployed contract addresses (MAINNET ONLY)
REWARD_TOKEN_ADDRESS = "0xe1edb9510e468c745ccad91238b83cf63bf7c7ad"
YIELD_AGGREGATOR_ADDRESS = "0x3fa8271e96a29d570f4766aaeabea3aa2df7a9ec"

# Connect to Ethereum Mainnet via Alchemy
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
RPC_URL = f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Admin private key for minting/transfers
ADMIN_PRIVATE_KEY = os.getenv("ADMIN_PRIVATE_KEY")

class WithdrawRequest(BaseModel):
    walletAddress: str
    amount: float
    tokenAddress: str

@app.get("/")
def health_check():
    chain_id = w3.eth.chain_id if w3.is_connected() else 0
    return {
        "status": "online",
        "service": "10X Hyper Earning Backend",
        "version": "1.0.0",
        "network": NETWORK,
        "chain_id": chain_id,
        "mainnet_only": True,
        "web3_ready": w3.is_connected()
    }

@app.post("/api/engine/start")
async def start_engine(data: dict):
    # Verify we're on Mainnet
    if not w3.is_connected():
        raise HTTPException(status_code=503, detail="Not connected to Ethereum Mainnet")
    
    chain_id = w3.eth.chain_id
    if chain_id != MAINNET_CHAIN_ID:
        raise HTTPException(
            status_code=400, 
            detail=f"Wrong network! Expected Mainnet (1), got {chain_id}"
        )
    
    return {
        "status": "started",
        "message": "Engine started on Ethereum Mainnet",
        "network": NETWORK,
        "chain_id": chain_id
    }

@app.get("/api/engine/metrics")
async def get_metrics():
    return {
        "totalProfit": 0,
        "hourlyRate": 0,
        "dailyProfit": 0,
        "activePositions": 7,
        "pendingRewards": 0
    }

@app.post("/api/engine/withdraw")
async def withdraw(request: WithdrawRequest):
    if not w3.is_connected():
        raise HTTPException(status_code=503, detail="Not connected to Ethereum Mainnet")
    
    # Verify Mainnet
    chain_id = w3.eth.chain_id
    if chain_id != MAINNET_CHAIN_ID:
        raise HTTPException(
            status_code=400,
            detail=f"Wrong network! Mainnet only. Current: {chain_id}"
        )
    
    try:
        # Load admin account
        admin_account = w3.eth.account.from_key(ADMIN_PRIVATE_KEY)
        
        # ERC20 ABI for transfer
        ERC20_ABI = [
            {
                "inputs": [
                    {"name": "recipient", "type": "address"},
                    {"name": "amount", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        
        # Connect to token contract
        token_contract = w3.eth.contract(
            address=Web3.to_checksum_address(request.tokenAddress),
            abi=ERC20_ABI
        )
        
        # Convert amount to Wei (18 decimals)
        amount_wei = w3.to_wei(request.amount, 'ether')
        
        # Build transaction
        nonce = w3.eth.get_transaction_count(admin_account.address)
        
        transaction = token_contract.functions.transfer(
            Web3.to_checksum_address(request.walletAddress),
            amount_wei
        ).build_transaction({
            'chainId': MAINNET_CHAIN_ID,
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
        })
        
        # Sign and send transaction
        signed_txn = admin_account.sign_transaction(transaction)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Wait for confirmation
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return {
            "status": "success",
            "txHash": receipt['transactionHash'].hex(),
            "blockNumber": receipt['blockNumber'],
            "network": "mainnet"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
