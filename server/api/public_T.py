from fastapi import FastAPI, HTTPException, Depends
from typing import List, Dict, Any
from server.connectors import BinanceConnector, KrakenConnector
from server.auth.auth_manager import AuthenticationManager

app = FastAPI()

# Initialize authentication manager
auth_manager = AuthenticationManager()

# Initialize exchange connectors
EXCHANGES = {
    "binance": BinanceConnector(),
    "kraken": KrakenConnector()
}

# Authentication routes
@app.post("/auth/token")
async def create_access_token(user_id: str):
    """Create a new JWT token."""
    token = auth_manager.create_token(user_id)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/auth/token/revoke")
async def revoke_token(credentials: str = Depends(auth_manager.verify_token)):
    """Revoke a JWT token."""
    auth_manager.revoke_token(credentials)
    return {"message": "Token revoked successfully"}

@app.post("/auth/api-key")
async def create_api_key(user_id: str = Depends(auth_manager.verify_token)):
    """Create a new API key."""
    api_key = auth_manager.generate_api_key(user_id)
    return {"api_key": api_key}

# Public routes (no authentication required)
@app.get("/exchanges", response_model=List[str])
async def get_supported_exchanges():
    """List all supported exchanges."""
    return list(EXCHANGES.keys())

# Protected routes (authentication required)
@app.get("/pairs/{exchange}", response_model=List[str])
async def get_trading_pairs(
    exchange: str,
    user_id: str = Depends(auth_manager.verify_token)
):
    """Get available trading pairs for an exchange."""
    exchange = exchange.lower()
    if exchange not in EXCHANGES:
        raise HTTPException(status_code=400, detail="Unsupported exchange")

    try:
        return await EXCHANGES[exchange].get_trading_pairs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/klines/{exchange}/{symbol}", response_model=List[Dict[str, Any]])
async def get_klines(
    exchange: str,
    symbol: str,
    interval: str = "1m",
    limit: int = 10,
    user_id: str = Depends(auth_manager.verify_token)
):
    """Get klines (candlestick) data for a trading pair."""
    exchange = exchange.lower()
    if exchange not in EXCHANGES:
        raise HTTPException(status_code=400, detail="Unsupported exchange")

    try:
        return await EXCHANGES[exchange].get_klines(symbol, interval, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)