import aiohttp
from typing import List, Dict, Any
from server.connectors.base_connector import BaseConnector, BaseExchangeWSConnection
import datetime as dt
import pandas as pd
import json
import asyncio

class BinanceConnector(BaseConnector):

    def __init__(self):
        super().__init__(
            exchange_name="Binance",
            rest_url="https://api.binance.com/api/v3"
        )

    async def get_klines(self, symbol: str, interval: str, limit: int) -> List[Dict[str, Any]]:
        url = f"{self.rest_url}/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000)
        }
        
        klines = []

        async with aiohttp.ClientSession() as session:
            while len(klines) < limit:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if not data:
                        break
                    klines = data + klines
                    if len(data) < 1000:
                        break
                    params["endTime"] = data[0][0]-1
                    
        return self.standardize_klines(klines[:limit])

    async def get_trading_pairs(self) -> List[str]:
        url = f"{self.rest_url}/exchangeInfo"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return [symbol_info["symbol"] for symbol_info in data["symbols"]]
    
    def standardize_klines(self, raw_data):
        return [
            {
                "timestamp": entry[0]*1000000,
                "open": float(entry[1]),
                "high": float(entry[2]),
                "low": float(entry[3]),
                "close": float(entry[4]),
                "volume": float(entry[5]),
            }
            for entry in raw_data
        ]
    

class BinanceWSConnection(BaseExchangeWSConnection):
    def __init__(self):
        super().__init__("Binance", "wss://stream.binance.com/stream")

    async def subscribe_symbol(self, symbol: str):
        symbol = symbol.replace("/", "").lower()
        if symbol in self.subscribed_symbols:
            return
        # Binance expects lowercase symbol with stream name appended
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": [f"{symbol}@depth10@100ms"],
            "id": symbol
        }
        await self.ws.send(json.dumps(subscribe_msg))
        self.subscribed_symbols.add(symbol)
        print(f"[Binance] Subscribed to {symbol}")

    async def unsubscribe_symbol(self, symbol: str):
        symbol = symbol.replace("/", "").lower()
        if symbol not in self.subscribed_symbols:
            return
        unsubscribe_msg = {
            "method": "UNSUBSCRIBE",
            "params": [f"{symbol}@depth10@100ms"],
            "id": symbol
        }
        await self.ws.send(json.dumps(unsubscribe_msg))
        self.subscribed_symbols.remove(symbol)
        print(f"[Binance] Unsubscribed from {symbol}")

    async def listen(self):
        message = await self.ws.recv()
        parsed_message = json.loads(message)
        if not "depth10" in parsed_message.get("stream", ""): return
        symbol = parsed_message["stream"].split("@")[0].upper()
        data = parsed_message.get("data")
        standardized = {
            "exchange": "Binance",
            "symbol": symbol,
            "bids": [[float(price), float(quantity)] for price, quantity in data.get("bids", [])][:10],
            "asks": [[float(price), float(quantity)] for price, quantity in data.get("asks", [])][:10],
        }
        self.order_book[symbol] = standardized
