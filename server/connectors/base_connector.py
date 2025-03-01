from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set
import websockets


class BaseConnector(ABC):
    
    def __init__(self, exchange_name: str, rest_url: str):
        self.exchange_name = exchange_name
        self.rest_url = rest_url

    @abstractmethod
    async def get_klines(self, symbol: str, interval: str, limit: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_trading_pairs(self) -> List[str]:
        pass

    def standardize_klines(self, raw_data: List[List[Any]]) -> List[Dict[str, Any]]:
        pass
    
    
class BaseExchangeWSConnection(ABC):
    def __init__(self, exchange: str, websocket_url: str):
        self.exchange = exchange
        self.websocket_url = websocket_url
        self.ws = None
        self.subscribed_symbols: Set[str] = set()
        self.order_book = {}
        print("Instanciating Exchange Connection")

    async def connect(self): 
        self.ws = await websockets.connect(self.websocket_url)
        print(f"[{self.exchange}] Connected to WebSocket.")

    async def subscribe_symbol(self, symbol: str):
        pass

    async def unsubscribe_symbol(self, symbol: str):
        pass

    async def listen(self):
        pass

    async def run(self):
        while True:
            await self.listen()