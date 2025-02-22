from client_credentials import Credentials
from client_side import ClientSide
import asyncio
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