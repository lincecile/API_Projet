from fastapi import FastAPI, HTTPException, WebSocket
from typing import List, Dict, Any
import asyncio
from server.connectors import BaseConnector, BinanceConnector, KrakenConnector
from server.auth.auth_manager import AuthenticationManager
from server.services.websocket_manager import ClientWebSocketManager
from server.services.subscription_manager import SubscriptionManager
from server.services.twap_order import TWAPOrder
from server.services.execute_twap_order import execute_twap_order
from contextlib import asynccontextmanager


@asynccontextmanager
async def startup(app):
    app.state.subscription_manager = SubscriptionManager()
    app.state.active_orders = {}  # Pour stocker les ordres TWAP
    await app.state.subscription_manager.connect()
    asyncio.create_task(app.state.subscription_manager.run())
    yield


app = FastAPI(lifespan=startup)
auth_manager = AuthenticationManager()

# Initialisation des connecteurs d'exchanges
EXCHANGES: Dict[str, BaseConnector] = {"binance": BinanceConnector(), "kraken": KrakenConnector()}


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
async def get_trading_pairs(exchange: str):
    """Obtient les paires de trading disponibles"""
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
        exchange: str, symbol: str, interval: str = "1m", limit: int = 10
):
    """Obtient les données klines"""
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
    manager = ClientWebSocketManager(websocket, auth_manager)
    await manager.handle(subscription_manager=websocket.app.state.subscription_manager)


@app.post("/orders/twap")
async def create_twap_order(
        exchange: str,
        symbol: str,
        side: str,
        quantity: float,
        slices: int,
        duration_seconds: int,
        token: str,  # Token d'authentification obligatoire
        limit_price: float = None,
        token_id: str = None  # ID d'ordre optionnel
):
    """Crée un nouvel ordre TWAP"""
    # Vérifier l'authentification
    username = auth_manager.verify_token(token)

    exchange = exchange.lower()
    if exchange not in EXCHANGES:
        raise HTTPException(status_code=400, detail="Exchange non supporté")

    if side.lower() not in ["buy", "sell"]:
        raise HTTPException(status_code=400, detail="Side doit être 'buy' ou 'sell'")

    # Générer un ID d'ordre
    order_id = token_id or f"order_{len(app.state.active_orders) + 1}"

    # Créer l'ordre
    order = TWAPOrder(
        subscription_manager=app.state.subscription_manager,
        exchange=exchange,
        symbol=symbol,
        side=side,
        quantity=quantity,
        slices=slices,
        duration_seconds=duration_seconds,
        limit_price=limit_price
    )

    # Stocker l'ordre
    app.state.active_orders[order_id] = order

    # Démarrer l'ordre
    await order.start()
    asyncio.create_task(execute_twap_order(app, order_id))

    return {"order_id": order_id, "status": "accepted"}


@app.get("/orders/{token_id}")
async def get_order_status(token_id: str, token: str):
    """Récupère le statut d'un ordre TWAP"""
    # Vérifier l'authentification
    username = auth_manager.verify_token(token)

    if token_id not in app.state.active_orders:
        raise HTTPException(status_code=404, detail="Ordre non trouvé")

    return app.state.active_orders[token_id].get_status()


async def execute_twap_order(app, order_id: str):
    """Exécute un ordre TWAP"""
    order = app.state.active_orders[order_id]

    try:
        while order.status == "active":
            await order.execute_slice()
            await asyncio.sleep(order.interval_seconds)
    except Exception as e:
        order.status = "error"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("public:app", host="0.0.0.0", port=8000, reload=True)