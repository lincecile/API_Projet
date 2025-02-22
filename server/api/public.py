from fastapi import FastAPI, HTTPException, WebSocket, Request
from typing import List, Dict, Any
import asyncio
from datetime import datetime  # Ajout de l'import manquant
from server.connectors import BinanceConnector, KrakenConnector
from server.auth.auth_manager import AuthenticationManager
from server.services.websocket_manager import ClientWebSocketManager
from server.services.subscription_manager import SubscriptionManager
from server.services.twap_order import TWAPOrder
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


# Routes TWAP
@app.post("/twap")
async def create_twap_order(
        exchange: str,
        symbol: str,
        quantity: float,
        slices: int,
        duration_seconds: int
):
    """Crée un nouvel ordre TWAP"""
    exchange = exchange.lower()
    if exchange not in EXCHANGES:
        raise HTTPException(status_code=400, detail="Exchange non supporté")

    # Créer l'ordre
    order_id = f"order_{len(app.state.active_orders) + 1}"
    order = TWAPOrder(
        subscription_manager=app.state.subscription_manager,
        exchange=exchange,
        symbol=symbol,
        quantity=quantity,
        slices=slices,
        duration_seconds=duration_seconds
    )
    app.state.active_orders[order_id] = order

    # Démarrer l'ordre
    await order.start()
    asyncio.create_task(execute_twap_order(app, order_id))

    return {"order_id": order_id}


@app.get("/twap/{order_id}")
async def get_twap_status(order_id: str) -> Dict[str, Any]:
    """Récupère le statut d'un ordre TWAP"""
    if order_id not in app.state.active_orders:
        raise HTTPException(status_code=404, detail="Ordre non trouvé")
    return app.state.active_orders[order_id].get_status()


async def execute_twap_order(app: FastAPI, order_id: str):
    """Exécute un ordre TWAP"""
    order = app.state.active_orders[order_id]

    try:
        while order.status == "active":
            await order.execute_slice()
            await asyncio.sleep(order.interval_seconds)

    except Exception as e:
        order.status = "error"
        print(f"Erreur lors de l'exécution TWAP: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("public:app", host="0.0.0.0", port=8000, reload=True)