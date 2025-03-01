import asyncio
from client.client_credentials import Credentials
from client.client_side import ClientSide
import pandas as pd 

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
            # Trading paire de la plataforme 
            pairs = await client.get_trading_pairs(exchanges[0])
            symbol = pairs[0]

            # Connexion WS
            await client.connect_websocket()

            # Abonnement aux données temps réel
            await client.subscribe_symbol(symbol)
            print(f"Abonné à {symbol}")

            # Fonction pour traiter les mises à jour WS
            def on_websocket_update(data):
                if data["type"]=="order_book":

                    bids = data["bids"]
                    asks = data["asks"]
                    
                    for i, (price, quantity) in enumerate(bids):
                        print(f"{i+1}. Bids: {price}, Quantity: {quantity}\n")
                        
                    for i, (price, quantity) in enumerate(asks):
                        print(f"{i+1}. Asks: {price}, Quantity: {quantity}\n")
            
            print("Ecoute des mises à jour WS")
            await client.listen_websocket_updates(on_websocket_update)

if __name__ == "__main__":
    print("Test avec authentification pour obtenir les bids asks:\n")
    asyncio.run(main())