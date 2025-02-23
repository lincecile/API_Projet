import asyncio
import aiohttp
import websockets
import json
from typing import Optional, List, Dict, Any, Callable
from client_credentials import Credentials
import datetime

class ClientSide:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = f"ws://{base_url.split('://')[-1]}/ws"
        self.token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.keep_ws: Optional[asyncio.Task] = None
        
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

    async def _keep_ws_connexion(self):
        """Maintien la connexion avec WebSocket"""
        try:
            while True:
                if self.ws and not self.ws.close:
                    await self.ws.ping()
                await asyncio.sleep(20)  # Ping toutes les 20 secondes
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Problème dans le ping vers WS : {e}")

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
        
    async def create_twap_order(self, exchange: str, symbol: str, quantity: float, slices: int, duration_seconds: int):
        """
        Crée un ordre TWAP
        
        Returns:
            id de l'ordre crée
        """
        await self._ensure_connexion()

        async with self.session.post(f"{self.base_url}/twap",
                                     params={
                                         "exchange": exchange, "symbol": symbol, "quantity": quantity, "slices": slices,
                                         "duration_seconds": duration_seconds, "token": self.token}
                                         ) as response:
            response.raise_for_status()
            data = await response.json()
            return data['order_id']

    async def get_twap_status(self, order_id: str) -> Dict[str, Any]:
        """
        Récupère le statut d'un ordre TWAP via son id

        Returns:
            Dict : {'status': str, 'executed_quantity': int, 
            'total_quantity': float, 'slices_executed': int, 
            'total_slices': int, 'executions': list, 'average_price': float}
        """
        await self._ensure_connexion()

        async with self.session.get(f"{self.base_url}/twap/{order_id}",params={"token": self.token}) as response:
            response.raise_for_status()
            return await response.json()
        
    async def connect_websocket(self):
        """Établit une connexion WebSocket et la maintien ouverte"""
        if self.ws is None or self.ws.close:
            self.ws = await websockets.connect(self.ws_url)
        
        if self.keep_ws is None or self.keep_ws.done():
            self.keep_ws = asyncio.create_task(self._keep_ws_connexion())
        
    async def subscribe_symbol(self, symbol: str):
        """S'abonne aux mises à jour d'un symbole"""
        if self.ws is None or self.ws.close:
            await self.connect_websocket()

        await self.ws.send(json.dumps({"action": "subscribe","symbol": symbol}))
        
    async def unsubscribe_symbol(self, symbol: str):
        """Se désabonne des mises à jour d'un symbole"""
        if self.ws is None or self.ws.close:
            await self.connect_websocket()
            
        await self.ws.send(json.dumps({"action": "unsubscribe","symbol": symbol}))

            
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
                
                # Connexion WS
                await client.connect_websocket()

                # Abonnement aux données temps réel
                await client.subscribe_symbol(symbol)
                print(f"Abonné de {symbol} via {exchange}")

                # Création d'un ordre TWAP
                order_id = await client.create_twap_order(exchange=exchange, symbol=symbol, quantity=1.0, slices=5, duration_seconds=300)
                print(f"Ordre TWAP créé: {order_id} sur {exchange}")

                # Suivi de l'ordre
                iteration = 0
                while True and iteration < 10:
                    iteration += 1
                    status = await client.get_twap_status(order_id)
                    print(f"Statut de l'ordre {iteration}: {status}")
                    if status["status"] in ["completed", "error"]:
                        break
                    await asyncio.sleep(10)

                # Désabonnement aux données temps réel
                await client.unsubscribe_symbol(symbol)
                print(f"Désabonné de {symbol} via {exchange}")


if __name__ == "__main__":
    asyncio.run(main())