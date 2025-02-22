from fastapi import FastAPI, HTTPException, WebSocket, Request
from typing import List, Dict, Any
import asyncio

from server.connectors import BinanceConnector, KrakenConnector
from server.auth.auth_manager import AuthenticationManager
from server.services.websocket_manager import ClientWebSocketManager
from server.services.subscription_manager import SubscriptionManager
from contextlib import asynccontextmanager


@asynccontextmanager
async def startup(app):
    app.state.subscription_manager = SubscriptionManager()
    await app.state.subscription_manager.connect()
    asyncio.create_task(app.state.subscription_manager.run())
    yield


app = FastAPI(lifespan=startup)
auth_manager = AuthenticationManager()

# Initialisation des connecteurs d'exchanges
EXCHANGES = {"binance": BinanceConnector(), "kraken": KrakenConnector()}


@app.post("/auth/login")
async def login(username: str, password: str):
    """Endpoint de login qui retourne un token"""
    token = auth_manager.authenticate_user(username, password)
    if not token:
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    return {"token": token}


# Route publique (pas d'authentification requise)
@app.get("/exchanges", response_model=List[str])
async def get_supported_exchanges():
    """Liste tous les exchanges supportés"""
    return list(EXCHANGES.keys())


# Routes protégées (authentification requise)
@app.get("/pairs/{exchange}", response_model=List[str])
async def get_trading_pairs(exchange: str, token: str):
    """Obtient les paires de trading disponibles"""
    username = auth_manager.verify_token(token)

    exchange = exchange.lower()
    if exchange not in EXCHANGES:
        raise HTTPException(status_code=400, detail="Exchange non supporté")

    try:
        return await EXCHANGES[exchange].get_trading_pairs()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/klines/{exchange}/{symbol}", response_model=List[Dict[str, Any]])
async def get_klines(
    exchange: str, symbol: str, token: str, interval: str = "1m", limit: int = 10
):
    """Obtient les données klines"""
    username = auth_manager.verify_token(token)

    exchange = exchange.lower()
    if exchange not in EXCHANGES:
        raise HTTPException(status_code=400, detail="Exchange non supporté")

    try:
        return await EXCHANGES[exchange].get_klines(symbol, interval, limit)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    manager = ClientWebSocketManager(websocket)
    await manager.handle(subscription_manager=websocket.app.state.subscription_manager)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("public:app", host="0.0.0.0", port=8000, reload=True)