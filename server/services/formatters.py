def format_kraken(symbol: str):
    symbol = symbol.upper().replace("BTC", "XBT")
    return symbol[0:3] + "/" + symbol[3:6]


def format_base(symbol: str):
    return symbol.upper().replace("/", "").replace("XBT", "BTC").replace("USD", "USDT")
