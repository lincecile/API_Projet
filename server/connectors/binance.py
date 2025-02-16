import aiohttp
from typing import List, Dict, Any
from server.connectors.base_connector import BaseConnector
import datetime as dt
import pandas as pd

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

if __name__ == "__main__":
    async def main():
        connector = BinanceConnector()
        pairs = await connector.get_trading_pairs()
        print(pairs)
        klines = await connector.get_klines("BTCUSDT", "1n", 2000)
        print(pd.to_datetime(pd.DataFrame(klines)["timestamp"]*1000000))

    import asyncio
    asyncio.run(main())