from fastapi import FastAPI, HTTPException, Depends, Request
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from server.connectors import BinanceConnector, KrakenConnector
from server.auth.auth_manager import AuthenticationManager
from server.auth.models import get_db

app = FastAPI()
auth_manager = AuthenticationManager()

# Initialisation des connecteurs d'exchanges
EXCHANGES = {
    "binance": BinanceConnector(),
    "kraken": KrakenConnector()
}

@app.post("/auth/login")
async def login(
    username: str,
    password: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login endpoint qui retourne un token."""
    token = auth_manager.authenticate_user(username, password, request.client.host, db)
    if not token:
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    return {"token": token}

# Route publique (pas d'authentification requise)
@app.get("/exchanges", response_model=List[str])
async def get_supported_exchanges():
    """Liste tous les exchanges supportés."""
    return list(EXCHANGES.keys())

# Routes protégées (authentification requise)
@app.get("/pairs/{exchange}", response_model=List[str])
async def get_trading_pairs(
    exchange: str,
    token: str,
    db: Session = Depends(get_db)
):
    """Obtient les paires de trading disponibles."""
    username = auth_manager.verify_token(token, db)

    exchange = exchange.lower()
    if exchange not in EXCHANGES:
        raise HTTPException(status_code=400, detail="Exchange non supporté")

    try:
        return await EXCHANGES[exchange].get_trading_pairs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/klines/{exchange}/{symbol}", response_model=List[Dict[str, Any]])
async def get_klines(
    exchange: str,
    symbol: str,
    token: str,
    db: Session = Depends(get_db),
    interval: str = "1m",
    limit: int = 10
):
    """Obtient les données klines."""
    username = auth_manager.verify_token(token, db)

    exchange = exchange.lower()
    if exchange not in EXCHANGES:
        raise HTTPException(status_code=400, detail="Exchange non supporté")

    try:
        return await EXCHANGES[exchange].get_klines(symbol, interval, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )