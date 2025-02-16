from abc import ABC, abstractmethod
from typing import List, Dict, Any


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