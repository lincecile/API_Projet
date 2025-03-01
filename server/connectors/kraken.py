import aiohttp
from typing import List, Dict, Any
from server.connectors.base_connector import BaseConnector, BaseExchangeWSConnection
from server.services.formatters import format_kraken, format_base
import pandas as pd
from fastapi import HTTPException
import json


class KrakenConnector(BaseConnector):

    def __init__(self):
        super().__init__(
            exchange_name="Kraken", rest_url="https://api.kraken.com/0/public"
        )

    async def get_klines(
        self, symbol: str, interval: str, limit: int
    ) -> List[Dict[str, Any]]:
        
        url = f"{self.rest_url}/OHLC"

        interval_in_minutes = pd.to_timedelta(interval).seconds // 60

        if not interval_in_minutes in [1, 5, 15, 30, 60, 240, 1440, 10080, 21600]:
            raise HTTPException(status_code=400, detail="Invalid interval")

        params = {
            "pair": symbol,
            "interval": interval_in_minutes,
            "count": min(limit, 720),
        }
        klines = []

        async with aiohttp.ClientSession() as session:
            while len(klines) < limit:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if not data or "error" in data and data["error"]:
                        raise HTTPException(status_code=400, detail=data["error"])
                    pair_data = data["result"][list(data["result"].keys())[0]]
                    klines = pair_data + klines
                    if len(pair_data) < 720:
                        break
                    params["since"] = pair_data[0][0]

        return self.standardize_klines(klines[:limit])

    async def get_trading_pairs(self) -> List[str]:
        url = f"{self.rest_url}/AssetPairs"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return data["result"].keys()

    def standardize_klines(self, raw_data):
        return [
            {
                "timestamp": entry[0] * 1000000000,
                "open": float(entry[1]),
                "high": float(entry[2]),
                "low": float(entry[3]),
                "close": float(entry[4]),
                "volume": float(entry[5]),
            }
            for entry in raw_data
        ]


class KrakenWSConnection(BaseExchangeWSConnection):
    def __init__(self):
        super().__init__("Kraken", "wss://ws.kraken.com")

    async def subscribe_symbol(self, symbol: str):
        if symbol in self.subscribed_symbols:
            return
        subscribe_msg = {
            "event": "subscribe",
            "pair": [format_kraken(symbol)],
            "subscription": {"name": "book", "depth": 10},
        }
        await self.ws.send(json.dumps(subscribe_msg))
        self.subscribed_symbols.add(symbol)
        print(f"[Kraken] Subscribed to {symbol}")

    async def unsubscribe_symbol(self, symbol: str):
        if symbol not in self.subscribed_symbols:
            return
        unsubscribe_msg = {
            "event": "unsubscribe",
            "pair": [format_kraken(symbol)],
            "subscription": {"name": "book"},
        }
        await self.ws.send(json.dumps(unsubscribe_msg))
        self.subscribed_symbols.remove(symbol)
        print(f"[Kraken] Unsubscribed from {symbol}")

    async def listen(self):
        message = await self.ws.recv()
        data = json.loads(message)
        if isinstance(data, list) and len(data) > 1:
            update = data[1]
            symbol = format_base(data[3])
            if "as" in update or "bs" in update:
                standardized = {
                    "exchange": "Kraken",
                    "symbol": symbol,
                    "bids": [
                        [float(price), float(quantity)]
                        for price, quantity, _ in update.get("bs", [])
                    ][:10],
                    "asks": [
                        [float(price), float(quantity)]
                        for price, quantity, _ in update.get("as", [])
                    ][:10],
                }
                self.order_book[symbol] = standardized