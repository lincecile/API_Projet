import asyncio
from client.client_credentials import Credentials
from client.client_side import ClientSide
import pandas as pd 
import matplotlib.pyplot as plt
import mplfinance as mpf


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
        if exchanges:
            # Trading paire de la plataforme 
            pairs = await client.get_trading_pairs(exchanges[0])
            symbol = pairs[0]
                
            if pairs:
                # klines des dernieres paires d'un symbole
                symbol = pairs[0]                    
                klines = await client.get_klines(exchanges[0], symbol, interval="1h", limit=100)
                print(f"100 dernieres klines pour {symbol} chez {exchanges[0]}:")
                for kline in klines:
                    time_str = pd.to_datetime(kline['timestamp'], unit='ns', errors='coerce')
                    print(f"  {time_str} - Open: {kline['open']}, High: {kline['high']}, Low: {kline['low']}, Close: {kline['close']}, Volume: {kline['volume']}")
            
        df = pd.DataFrame(klines, columns=["timestamp", "open", "high", "low", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ns')
        df.set_index("timestamp", inplace=True)

        # Graphique: courbe des prix
        plt.figure(figsize=(8, 5))
        plt.plot(df.index, df["close"], label=f'{symbol}', color='b')
        plt.title('Evolutions des prix')
        plt.xlabel('Dates')
        plt.legend()
        plt.grid()
        plt.show()

        # Graphique: chandeliers
        fig, axlist = mpf.plot(df, type='candle', style='charles', title='Graphique en Chandeliers', ylabel='Prix', returnfig=True)
        plt.show()

if __name__ == "__main__":
    print("Test sur les klines avec authentification:\n")
    asyncio.run(main())