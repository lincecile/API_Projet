import asyncio
from client.client_side import ClientSide
import pandas as pd 

# Exemple sans authentification
async def main_no_auth():
    async with ClientSide() as client:
        exchanges = await client.get_supported_exchanges()
        print(f"Plateformes supportées (sans authentification): {exchanges}")

        symbols = await client.get_trading_pairs(exchanges[0])
        print(f"Premiere paire de trading de {exchanges[0]}: {symbols[:5]}")
        
        klines = await client.get_klines(exchanges[0], symbols[0], interval="1h", limit=5)
        print(f"5 dernieres klines pour {symbols[0]} chez {exchanges[0]}:")
        for kline in klines:
            time_str = pd.to_datetime(kline['timestamp'], unit='ns', errors='coerce')
            print(f"  {time_str} - Open: {kline['open']}, High: {kline['high']}, Low: {kline['low']}, Close: {kline['close']}, Volume: {kline['volume']}")


if __name__ == "__main__":
    print("Test sans authentification: \n")
    asyncio.run(main_no_auth())
    