from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any
import asyncio

from server.connectors import BinanceConnector, KrakenConnector

app = FastAPI()

# Initialize exchange connectors
EXCHANGES = {
    "binance": BinanceConnector(),
    "kraken": KrakenConnector()
}


@app.get("/exchanges", response_model=List[str])
async def get_supported_exchanges():
    return list(EXCHANGES.keys())


@app.get("/pairs/{exchange}", response_model=List[str])
async def get_trading_pairs(exchange: str):
    exchange = exchange.lower()
    if exchange not in EXCHANGES:
        raise HTTPException(status_code=400, detail="Unsupported exchange")

    try:
        return await EXCHANGES[exchange].get_trading_pairs()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/klines/{exchange}/{symbol}", response_model=List[Dict[str, Any]])
async def get_klines(exchange: str, symbol: str, interval: str = "1m", limit: int = 10):
    exchange = exchange.lower()
    if exchange not in EXCHANGES:
        raise HTTPException(status_code=400, detail="Unsupported exchange")

    try:
        return await EXCHANGES[exchange].get_klines(symbol, interval, limit)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Run the FastAPI server using Uvicorn when executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
