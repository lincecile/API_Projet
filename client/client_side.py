import asyncio
import aiohttp
import websockets
import json
from typing import Optional, List, Dict, Any
from client_credentials import Credentials
import datetime

class ClientSide:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = f"ws://{base_url.split('://')[-1]}/ws"
        self.token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        
    async def __aenter__(self):
        """Permet l'utilisation du client"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ferme la session HTTP"""
        if self.session:
            await self.session.close()
        if self.ws:
            await self.ws.close()
    
    async def _ensure_connexion(self):
        """S'assure qu'une session HTTP est active."""
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def login(self, credentials: Credentials):
        """
        Authentifie l'utilisateur et stock le token
        
        Args:
            credentials: Nom d'utilisateur, Mot de passe
            
        Returns:
            bool: True si l'authentification a réussi, False sinon
        """
        await self._ensure_connexion()

        async with self.session.post(f"{self.base_url}/auth/login", 
                                     params={"username": credentials.username, 
                                             "password": credentials.password}) as response:
            if response.status == 401:
                return False
            response.raise_for_status()
            data = await response.json()
            self.token = data["token"]
            return True
        
            
    async def get_supported_exchanges(self):
        """
        Récupère la liste des exchanges supportés.
        Cette route est publique et ne nécessite pas d'authentification.
        
        Returns:
            List[str]: Liste des noms d'exchanges
        """
        await self._ensure_connexion()

        async with self.session.get(f"{self.base_url}/exchanges") as response:
            response.raise_for_status()
            return await response.json()
            
    async def get_trading_pairs(self, exchange: str):
        """
        Récupère les paires de trading disponibles pour un exchange précis.
        
        Args:
            exchange: Nom de l'exchange (ex: 'binance', 'kraken')
            
        Returns:
            List[str]: Liste des paires de trading
        """
        await self._ensure_connexion()

        async with self.session.get(f"{self.base_url}/pairs/{exchange}",
                                    params={"token": self.token}) as response:
            response.raise_for_status()
            return await response.json()
            
    async def get_klines(self, exchange: str, symbol: str, interval: str = "1m", limit: int = 10):
        """
        Récupère les données klines pour une paire de trading.
        
        Args:
            exchange: Nom de l'exchange (ex: 'binance', 'kraken')
            symbol: Symbole de la paire (ex: 'BTCUSDT')
            interval: Intervalle de temps (ex: '1m', '15m', '1h')
            limit: Nombre de klines à récupérer
            
        Returns:
            List[Dict[str, Any]]: Liste des klines avec timestamp, open, high, low, close, volume
        """
        await self._ensure_connexion()

        async with self.session.get(f"{self.base_url}/klines/{exchange}/{symbol}",
                                    params={"token": self.token, "interval": interval, "limit": limit}) as response:
            response.raise_for_status()
            return await response.json()
            
# Exemple
async def main():
    credentials = Credentials(username="Tristan", password="Tristan")
    
    async with ClientSide() as client:
        # Login
        logged_in = await client.login(credentials)
        if not logged_in:
            print("Erreur login")
            return
        
        # Liste des plateformes d'exchange
        exchanges = await client.get_supported_exchanges()
        print(f"Plateformes: {exchanges}")
        
        if exchanges:

            # Pour chaque plateforme
            for exchange in exchanges[:1]:
                # Trading paire de la plataforme 
                pairs = await client.get_trading_pairs(exchange)
                print(f"Premiere paire de trading de {exchange}: {pairs[:5]}")
            
                if pairs:
                    # klines des dernieres paires d'un symbole
                    symbol = pairs[0]
                    klines = await client.get_klines(exchange, symbol)
                    print(f"2 dernieres klines pour {symbol} chez {exchange}: {klines[:2]}")
                print()

if __name__ == "__main__":
    asyncio.run(main())