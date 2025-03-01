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
            if pairs:
                # klines des dernieres paires d'un symbole
                symbol = pairs[0]                    
                klines = await client.get_klines(exchanges[0], symbol, interval="1m", limit=10)
                print(f"10 dernieres klines pour {symbol} chez {exchanges[0]}:")
                up = 0
                temp = klines[0]['close']
                for kline in klines:
                    time_str = pd.to_datetime(kline['timestamp'], unit='ns', errors='coerce')
                    print(f"  {time_str} - Open: {kline['open']}, High: {kline['high']}, Low: {kline['low']}, Close: {kline['close']}, Volume: {kline['volume']}")
                    
                    if kline['close'] > temp:
                        up += 1
                        temp = kline['close']
                
                if up >= 7:
                    print("Tendance haussière, création d'un ordre TWAP d'achat:")
                    user_side = "buy"
                elif up <= 3:
                    print("Tendance baissière, pas de création d'ordre.")
                    user_side = "sell"

            # Création d'un ordre TWAP d'achat
            order_id = await client.create_twap_order(
                exchange=exchanges[0],
                symbol=symbol,
                side=user_side,
                quantity=1.0,  
                slices=3,
                duration_seconds=120  
            )
            print(f"Ordre TWAP créé avec ID: {order_id}")

            # Suivi de l'ordre
            print("Suivi de l'exécution de l'ordre TWAP:")
            change = False
            for i in range(int(120/15)+1):  
                status = await client.get_order_status(order_id)
                print(f"  Statut après {i*15} secondes: {status}")
                
                if status.get("status") in ["completed", "error"]:
                    change = True
                    print("Ordre terminé!")
                    break
                
                if change:
                    print("Ordre désactivé, non completé")
                    break
                    
                await asyncio.sleep(15)

if __name__ == "__main__":
    print("Strategy avec authentification:\n")
    asyncio.run(main())