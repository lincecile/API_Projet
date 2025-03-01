import asyncio
import aiohttp
import websockets
import json
from typing import Optional, Dict, Any, Callable
from client.client_credentials import Credentials

class ClientSide:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = f"ws://{base_url.split('://')[-1]}/ws"
        self.token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.ws_connected: bool = False
        self.keep_ws: Optional[asyncio.Task] = None
        self.subscribed_symbols = set()
        
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
                if self.ws and not self.ws_connected:
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
        
    async def ws_authenticate(self):
        """Authentifie l'utilisateur sur WebSocket"""
        if self.token is None:
            raise ValueError("Vous devez être authentifié pour vous connecter à WebSocket")
        
        
        await self.ws.send(json.dumps({"action": "authenticate", "token": self.token}))
                 
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

        async with self.session.get(f"{self.base_url}/pairs/{exchange}") as response:
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
                                    params={"interval": interval, "limit": limit}) as response:
            response.raise_for_status()
            return await response.json()
        
    async def create_twap_order(self, exchange: str, symbol: str, side: str, quantity: float, slices: int, duration_seconds: int, limit_price: Optional[float] = None):
        """
        Crée un ordre TWAP

        Args:
            exchange: Nom de l'exchange (ex: 'binance', 'kraken')
            symbol: Symbole de la paire (ex: 'BTCUSDT')
            side: Type d'ordre ('buy' ou 'sell')
            quantity: Quantité totale à acheter/vendre
            slices: Nombre de tranches pour l'ordre TWAP
            duration_seconds: Durée totale de l'exécution en secondes
            limit_price: Prix limite optionnel
        
        Returns:
            id de l'ordre crée
        """
        await self._ensure_connexion()

        if self.token is None:
            raise ValueError("Vous devez être authentifié pour créer un ordre")

        params = {"exchange": exchange,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "slices": slices,
            "duration_seconds": duration_seconds,
            "token": self.token}

        if limit_price is not None:
            params["limit_price"] = limit_price
        
        async with self.session.post(f"{self.base_url}/orders/twap", params=params) as response:
            response.raise_for_status()
            data = await response.json()
            return data['order_id']

    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Récupère le statut d'un ordre TWAP via son id

        Args:
            order_id: ID de l'ordre

        Returns:
            Dict : Informations sur le statut de l'ordre
        """
        await self._ensure_connexion()

        async with self.session.get(f"{self.base_url}/orders/{order_id}", params={"token": self.token}) as response:
            response.raise_for_status()
            return await response.json()
        
    async def connect_websocket(self):
        """Établit une connexion WebSocket et la maintien ouverte"""
        self.ws = await websockets.connect(self.ws_url)
        self.ws_connected = True
        print("Connexion WebSocket établie")
        
        if self.keep_ws is None and self.ws_connected:
            print("Lancement du ping WS")
            self.keep_ws = asyncio.create_task(self._keep_ws_connexion())

    async def subscribe_symbol(self, symbol: str):
        """S'abonne aux mises à jour d'un symbole"""
        await self.ws.send(json.dumps({"action": "subscribe","symbol": symbol}))
        
    async def unsubscribe_symbol(self, symbol: str):
        """Se désabonne des mises à jour d'un symbole"""
        await self.ws.send(json.dumps({"action": "unsubscribe","symbol": symbol}))

    async def listen_websocket_updates(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Mises à jour WebSocket pendant une durée spécifiée et applique le callback à chaque message
        
        Args:
            callback: Fonction à appeler pour chaque message reçu
            duration_seconds: Durée d'écoute en secondes
        """

        try:
            while True: 
                message = await self.ws.recv()
                data = json.loads(message)
                for event in data:
                    try:
                        callback(event)
                    except Exception as e:
                        print("Error in callback", e)
        except Exception as e:
            print(f"Erreur lors de l'écoute WebSocket: {e}")
            
