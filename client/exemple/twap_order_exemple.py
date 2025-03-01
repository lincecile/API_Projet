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
                
            # Création d'un ordre TWAP d'achat
            order_id = await client.create_twap_order(
                exchange=exchanges[0],
                symbol=symbol,
                side="buy",
                quantity=1.0,  
                slices=3,
                duration_seconds=60  
            )
            print(f"Ordre TWAP créé avec ID: {order_id} sur le symbole {symbol} de l'exchange {exchanges[0]}")

            # Suivi de l'ordre
            print("Suivi de l'exécution de l'ordre TWAP:")
            for i in range(5):  # Vérifier 5 fois, espacées de 15 secondes
                status = await client.get_order_status(order_id)
                print(f"  Statut après {i*15} secondes: {status}")
                
                if status.get("status") in ["completed", "error"]:
                    print("Ordre terminé!")
                    break
                    
                await asyncio.sleep(15)

if __name__ == "__main__":
    print("Test twap order avec authentification:\n")
    asyncio.run(main())