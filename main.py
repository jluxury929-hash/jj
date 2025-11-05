# 10X HYPER EARNING BACKEND - Railway Ready
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web3 import Web3
import os
from datetime import datetime

app = FastAPI(title="Hyper Earning Backend", version="10.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY", "")
PRIVATE_KEY = os.getenv("ADMIN_PRIVATE_KEY", "")
REWARD_TOKEN_ADDRESS = os.getenv("REWARD_TOKEN_ADDRESS", "0x8502496d6739dd6e18ced318c4b5fc12a5fb2c2c")

if ALCHEMY_API_KEY:
    w3 = Web3(Web3.HTTPProvider(f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"))
    if PRIVATE_KEY:
        admin_account = w3.eth.account.from_key(PRIVATE_KEY)
    else:
        admin_account = None
else:
    w3 = None
    admin_account = None

TOKEN_ABI = [
    {"inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "mint", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"}
]

STRATEGIES = {
    "aave_lending": {"apy": 0.85, "weight": 0.15},
    "compound_lending": {"apy": 0.78, "weight": 0.12},
    "uniswap_v3_lp": {"apy": 2.45, "weight": 0.18},
    "curve_stable": {"apy": 1.25, "weight": 0.10},
    "yearn_vaults": {"apy": 1.98, "weight": 0.15},
    "convex_boosted": {"apy": 3.12, "weight": 0.10},
    "balancer_weighted": {"apy": 1.67, "weight": 0.08},
    "sushiswap_farms": {"apy": 2.89, "weight": 0.05},
    "mev_arbitrage": {"apy": 4.25, "weight": 0.03},
    "flashloan_arb": {"apy": 5.12, "weight": 0.02},
    "governance_rewards": {"apy": 0.95, "weight": 0.01},
    "staking_rewards": {"apy": 1.42, "weight": 0.01}
}

AI_BOOST_MULTIPLIER = 2.5
user_sessions = {}

class StartEngineRequest(BaseModel):
    walletAddress: str
    miningContract: str
    yieldAggregator: str
    strategies: list

def calculate_yield(principal: float, time_seconds: float):
    total_apy = sum(s["apy"] * s["weight"] for s in STRATEGIES.values()) * AI_BOOST_MULTIPLIER
    rate_per_second = total_apy / (365 * 24 * 3600)
    earnings = principal * rate_per_second * time_seconds
    return earnings, total_apy

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "10X Hyper Earning Backend",
        "version": "10.0.0",
        "strategies": len(STRATEGIES),
        "ai_boost": AI_BOOST_MULTIPLIER,
        "web3_connected": w3 is not None and w3.is_connected() if w3 else False
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/engine/start")
async def start_engine(request: StartEngineRequest):
    wallet = request.walletAddress.lower()
    user_sessions[wallet] = {
        "start_time": datetime.now().timestamp(),
        "total_earned": 0.0,
        "last_mint": datetime.now().timestamp()
    }
    return {"success": True, "message": "10X Engine started", "ai_boost": AI_BOOST_MULTIPLIER}

@app.get("/api/engine/metrics")
async def get_metrics(x_wallet_address: str = Header(None, alias="X-Wallet-Address")):
    if not x_wallet_address:
        raise HTTPException(status_code=400, detail="X-Wallet-Address required")
    
    wallet = x_wallet_address.lower()
    if wallet not in user_sessions:
        user_sessions[wallet] = {
            "start_time": datetime.now().timestamp(),
            "total_earned": 0.0,
            "last_mint": datetime.now().timestamp()
        }
    
    session = user_sessions[wallet]
    current_time = datetime.now().timestamp()
    time_running = current_time - session["start_time"]
    time_since_mint = current_time - session["last_mint"]
    
    principal = 100000.0
    earnings, total_apy = calculate_yield(principal, time_running)
    session["total_earned"] += earnings
    
    if time_since_mint >= 5 and w3 and admin_account:
        try:
            await mint_tokens_to_user(wallet, session["total_earned"])
            session["last_mint"] = current_time
            session["total_earned"] = 0
        except Exception as e:
            print(f"Mint error: {e}")
    
    hourly_rate = (earnings / time_running) * 3600 if time_running > 0 else 0
    return {
        "totalProfit": session["total_earned"],
        "hourlyRate": hourly_rate,
        "dailyProfit": hourly_rate * 24,
        "activePositions": len(STRATEGIES),
        "pendingRewards": session["total_earned"] * 0.1,
        "total_apy": f"{total_apy * 100:.2f}%"
    }

async def mint_tokens_to_user(wallet_address: str, amount_usd: float):
    if not w3 or not admin_account:
        return None
    
    try:
        token_amount = int(amount_usd * 10**18)
        if token_amount <= 0:
            return None
        
        print(f"🚀 MINTING {amount_usd:.4f} tokens to {wallet_address}")
        
        token_contract = w3.eth.contract(
            address=Web3.to_checksum_address(REWARD_TOKEN_ADDRESS),
            abi=TOKEN_ABI
        )
        
        gas_price = int(w3.eth.gas_price * 1.2)
        nonce = w3.eth.get_transaction_count(admin_account.address)
        
        mint_tx = token_contract.functions.mint(
            Web3.to_checksum_address(wallet_address),
            token_amount
        ).build_transaction({
            'from': admin_account.address,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': gas_price,
            'chainId': w3.eth.chain_id
        })
        
        signed_tx = admin_account.sign_transaction(mint_tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt['status'] == 1:
            print(f"✅ MINT CONFIRMED - Block: {receipt['blockNumber']}")
            print(f"🔗 https://etherscan.io/tx/{tx_hash.hex()}")
        
        return tx_hash.hex()
    except Exception as e:
        print(f"❌ Mint error: {e}")
        return None

@app.post("/api/engine/stop")
async def stop_engine(request: dict):
    wallet = request.get("walletAddress", "").lower()
    if wallet in user_sessions:
        del user_sessions[wallet]
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)main.py
