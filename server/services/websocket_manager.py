from fastapi import WebSocket, WebSocketDisconnect
from typing import Set
import json
import asyncio
from server.services.subscription_manager import SubscriptionManager
from server.auth.auth_manager import AuthenticationManager

class ClientWebSocketManager:
    
    def __init__(self, websocket: WebSocket, auth_manager:AuthenticationManager):
        self.websocket = websocket
        self.subscriptions: Set[str] = set()
        self.authenticated = False
        self.auth_manager = auth_manager
        

    async def handle(self, subscription_manager: SubscriptionManager):
        await self.websocket.accept()
        sender_task = asyncio.create_task(self.send_aggregated_data(subscription_manager))
        try:
            while True:
                msg = await self.websocket.receive_text()
                data = json.loads(msg)
                action = data.get("action")
                symbol = data.get("symbol", "").upper()
                
                if action =="authenticate": 
                    self.authenticated = True
                    token = data.get("token")
                    try: 
                        username = self.auth_manager.verify_token(token, raise_http=False)
                    except:
                        await self.websocket.send_text(json.dumps({"error": "Invalid token"}))
                        username = None
                        pass
                    if username is not None:
                        self.auth_manager = True    
                        await self.websocket.send_text(json.dumps({"authenticated": True}))
                    continue
                
                if not self.authenticated: 
                    continue
                
                if action == "subscribe":
                    self.subscriptions.add(symbol)
                    await subscription_manager.add_subscription(symbol)
                elif action == "unsubscribe":
                    if symbol in self.subscriptions:
                        self.subscriptions.remove(symbol)
                        await subscription_manager.remove_subscription(symbol)
        except WebSocketDisconnect:
            print("[Client] Disconnected")
        finally:
            sender_task.cancel()

    async def send_aggregated_data(self, subscription_manager: SubscriptionManager):
        while True:
            await asyncio.sleep(1)
            data_to_send = []
            for symbol in self.subscriptions: 
                order_books = []
                for exchange in subscription_manager.exchange_connectors:
                    order_book = subscription_manager.exchange_connectors[exchange].order_book
                    if not symbol in order_book:
                        continue
                    order_books.append(order_book[symbol])
                     
                merged_order_book = {"bids": [], "asks": []}
                for order_book in order_books:
                    merged_order_book["bids"].extend(order_book["bids"])
                    merged_order_book["asks"].extend(order_book["asks"])
                
                merged_order_book["bids"].sort(key=lambda x: x[0], reverse=True)
                merged_order_book["asks"].sort(key=lambda x: x[0])
                
                data_to_send.append({
                    "type":"order_book",
                    "symbol": symbol,
                    **merged_order_book
                })
                
            if len(data_to_send)>0:
                await self.websocket.send_text(json.dumps(data_to_send))