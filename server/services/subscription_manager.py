from typing import Dict, List
from server.connectors.kraken import KrakenWSConnection
from server.connectors.binance import BinanceWSConnection
from server.connectors.base_connector import BaseExchangeWSConnection
import asyncio

class SubscriptionManager:
    
    def __init__(self):
        
        self.exchange_connectors : Dict[str, BaseExchangeWSConnection] = {
            "kraken": KrakenWSConnection(),
            "binance": BinanceWSConnection()
        }
        self.subscriptions: Dict[str, Dict[str, int]] = {
            "kraken": {},
            "binance": {}
        }
    
    async def connect(self):
        print("Connecting")
        await asyncio.gather(*[exchange_connector.connect() for exchange_connector in self.exchange_connectors.values()])
        
    async def run(self):
        for exchange_connector in self.exchange_connectors.values():
            asyncio.create_task(exchange_connector.run())
        
    async def add_subscription(self, symbol: str):
        for exchange in self.subscriptions:   
            if self.subscriptions[exchange].get(symbol, 0) == 0:
                self.subscriptions[exchange][symbol] = 1
                await self.exchange_connectors[exchange].subscribe_symbol(symbol)
            else:
                self.subscriptions[exchange][symbol] += 1

    async def remove_subscription(self, symbol: str):
        for exchange in self.subscriptions:
            if symbol in self.subscriptions[exchange]:
                self.subscriptions[exchange][symbol] -= 1
                if self.subscriptions[exchange][symbol] <= 0:
                    del self.subscriptions[exchange][symbol]
                    await self.exchange_connectors[exchange].unsubscribe_symbol(symbol)