import asyncio
from client_credentials import Credentials
from client_side import ClientSide

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