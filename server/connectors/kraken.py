import aiohttp
from typing import List, Dict, Any
from server.connectors.base_connector import BaseConnector
import datetime as dt
import pandas as pd
import asyncio
from fastapi import FastAPI, HTTPException

class KrakenConnector(BaseConnector):

    def __init__(self):
        super().__init__(
            exchange_name="Kraken",
            rest_url="https://api.kraken.com/0/public"
        )

    async def get_klines(self, symbol: str, interval: str, limit: int) -> List[Dict[str, Any]]:
        url = f"{self.rest_url}/OHLC"
        
        interval_in_minutes = pd.to_timedelta(interval).seconds // 60
        
        if not interval_in_minutes in [1, 5, 15, 30, 60, 240, 1440, 10080, 21600]:
            raise HTTPException(status_code=400, detail="Invalid interval")
        
        params = {
            "pair": symbol,
            "interval": interval_in_minutes,
            "count": min(limit, 720)
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
                return [symbol_info["altname"] for symbol_info in data["result"].values()]

    def standardize_klines(self, raw_data):
        return [
            {
                "timestamp": entry[0]*1000000000,
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
        connector = KrakenConnector()
        pairs = await connector.get_trading_pairs()
        print(pairs)
        klines = await connector.get_klines("XXBTZUSD", "15m", 2000)
        print(pd.to_datetime(pd.DataFrame(klines)["timestamp"]*1000000))

    asyncio.run(main())