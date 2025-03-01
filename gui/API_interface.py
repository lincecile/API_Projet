import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import asyncio
import threading
import pandas as pd
from client.client_side import ClientSide
from client.client_credentials import Credentials

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class APIGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading Platform")
        
        self.client = ClientSide()
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.start_loop, daemon=True).start()
        
        self.run_async(self.connect_and_listen_websocket())
        
        self.create_scrollable_frame()

        self.ws_subscribed_symbols = set()
        self.subscribed_symbol = None
        self.klines_data = {}

    def create_scrollable_frame(self):
        self.canvas = tk.Canvas(self.root, width=770, height=1000)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.create_widgets()

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_async(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    async def connect_and_listen_websocket(self):
        await self.client.connect_websocket()
        await self.client.listen_websocket_updates(self.on_websocket_update)
    
    def on_websocket_update(self, data):
        if data["type"]=="order_book":
            self.update_order_book(data)

    def create_widgets(self):
        self.scrollable_frame.columnconfigure(0, weight=1)
        self.scrollable_frame.rowconfigure(3, weight=1)

         # Initialiser toutes les variables de symbole
        self.symbol_var = tk.StringVar()  # Pour le menu principal
        self.twap_symbol_var = tk.StringVar()  # Pour les ordres TWAP

        self.frame_connexion()
        self.frame_exchange_and_symbol_selection()
        self.frame_order_book()
        self.frame_klines()
        self.frame_twap_order()
        self.frame_twap_sub_follow()
        
        self.update_exchanges()

    def frame_connexion(self):
        # Frame pour connexion
        login_frame = ttk.LabelFrame(self.scrollable_frame, text="Connexion API")
        login_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(login_frame, text="Username:").pack(side="left", padx=5)
        self.username_entry = ttk.Entry(login_frame)
        self.username_entry.pack(side="left", padx=5)
        
        ttk.Label(login_frame, text="Password:").pack(side="left", padx=5)
        self.password_entry = ttk.Entry(login_frame, show="*")
        self.password_entry.pack(side="left", padx=5)
        
        ttk.Button(login_frame, text="Login", command=self.login).pack(side="left", padx=5)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        creds = Credentials(username, password)
        self.run_async(self.async_login(creds))

    async def async_login(self, creds):
        success = await self.client.login(creds)
        await self.client.ws_authenticate()
        if success:
            messagebox.showinfo("Login", "Connexion réussie!")
        else:
            messagebox.showerror("Login", "Échec de la connexion!")

    def frame_exchange_and_symbol_selection(self):
        # Frame pour selection de l'exchange
        self.exchange_var = tk.StringVar()
        exchange_and_symbol_frame = ttk.LabelFrame(self.scrollable_frame, text="Exchanges and Symbols")
        exchange_and_symbol_frame.pack(fill="x", padx=5, pady=5)

        self.exchange_combo = ttk.Combobox(exchange_and_symbol_frame, textvariable=self.exchange_var, state="readonly")
        self.exchange_combo.bind("<<ComboboxSelected>>", lambda e: self.update_symbols())
        self.exchange_combo.pack(side="left", padx=5)
        
        self.symbol_var = tk.StringVar()
        self.symbol_combo = ttk.Combobox(exchange_and_symbol_frame, textvariable=self.symbol_var)
        self.symbol_combo.pack(side="left", padx=5)
        self.symbol_combo.bind("<<ComboboxSelected>>", lambda e: self.update_symbol())

    def update_exchanges(self):
        self.run_async(self.async_update_exchanges())

    async def async_update_exchanges(self):
        exchanges = await self.client.get_supported_exchanges()
        if exchanges:
            self.exchange_combo["values"] =  exchanges

    def update_symbols(self):
        self.run_async(self.async_update_symbols())

    async def async_update_symbols(self):
        exchanges = self.exchange_combo.get()
        if exchanges:
            pairs = await self.client.get_trading_pairs(exchanges)
            
            self.symbol_combo.delete(0, tk.END)
            self.symbol_combo.set("Sélectionner")
            self.symbol_combo['values'] = pairs
            self.twap_symbol_combo['values'] = pairs 
            
            # Si on a des pairs, mettre une valeur par défaut
            if pairs:
                self.symbol_var.set(pairs[0])
                self.twap_symbol_var.set(pairs[0])

    def update_symbol(self):
        symbol = self.symbol_var.get()
        exchange = self.exchange_var.get()
        self.fetch_and_display_klines(exchange, symbol)
        self.unsubscribe()
        self.subscribe_symbol(symbol)

    def frame_klines(self):
        klines_frame = ttk.LabelFrame(self.scrollable_frame, text="Klines")
        klines_frame.pack(fill="both", padx=5, pady=5, expand=True)
        self.klines_frame = klines_frame

    def fetch_and_display_klines(self, *args):
        self.run_async(self.async_fetch_and_display_klines(*args))

    async def async_fetch_and_display_klines(self, exchange, symbol):
        klines = await self.client.get_klines(exchange, symbol, "15m", 100)
        
        if not klines:
            messagebox.showerror("Erreur", "Aucune donnée de klines disponible pour ce symbole.")
            return

        df = pd.DataFrame(klines, columns=["timestamp", "open", "high", "low", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ns')
        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot()

        # Plot candlesticks
        for idx, row in df.iterrows():
            color = 'green' if row['close'] >= row['open'] else 'red'
            ax.plot([row['timestamp'], row['timestamp']], [row['low'], row['high']], color=color)
            ax.plot([row['timestamp'], row['timestamp']], [row['open'], row['close']], color=color, linewidth=5)

        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        ax.set_title(f"Candlestick chart for {symbol}")
        
        for widget in self.klines_frame.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=self.klines_frame) 
        canvas.draw()

        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)


    def frame_order_book(self):
        # Frame pour affichage des ordres et transactions (bids, asks et statistique sur une seule ligne)
        book_frame = ttk.LabelFrame(self.scrollable_frame, text="Order Book et Statistiques")
        book_frame.pack(fill="both", padx=5, pady=5)

        book_frame.columnconfigure(0, weight=1)
        book_frame.columnconfigure(1, weight=1)
        book_frame.columnconfigure(2, weight=1)
        book_frame.rowconfigure(1, weight=1)

        ttk.Label(book_frame, text="Bids").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(book_frame, text="Asks").grid(row=0, column=1, padx=5, pady=5)

        self.bids_text = scrolledtext.ScrolledText(book_frame, height=10, width=40)
        self.bids_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.asks_text = scrolledtext.ScrolledText(book_frame, height=10, width=40)
        self.asks_text.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
    
    def update_order_book(self, data):
        
        current_symbol = self.symbol_var.get()
        
        if data["symbol"] != current_symbol:
            return
        
        bids = data["bids"]
        asks = data["asks"]
        
        self.bids_text.delete("1.0", tk.END)
        self.asks_text.delete("1.0", tk.END)
        
        for i, (price, quantity) in enumerate(bids):
            self.bids_text.insert(tk.END, f"{i+1}. Price: {price}, Quantity: {quantity}\n")
            
        for i, (price, quantity) in enumerate(asks):
            self.asks_text.insert(tk.END, f"{i+1}. Price: {price}, Quantity: {quantity}\n")
   
   
    def subscribe_symbol(self, symbol): 
        if symbol in self.ws_subscribed_symbols:
            return
        
        self.run_async(self.async_subscribe_symbol(symbol))
        
    async def async_subscribe_symbol(self, symbol):
        await self.client.subscribe_symbol(symbol)
        self.ws_subscribed_symbols.add(symbol)
        print(f"Abonné à {symbol}")
        self.subscribed_symbol = symbol
        
    def unsubscribe(self): 
        if self.subscribed_symbol is not None: self.run_async(self.async_unsubscribe_symbol(self.subscribed_symbol))
        
    async def async_unsubscribe_symbol(self, symbol):
        await self.client.unsubscribe_symbol(symbol)
        self.ws_subscribed_symbols.remove(symbol)
        print(f"Désabonné de {symbol}")
        self.subscribed_symbol = None
   
    ####################################################################################################################################
    ####################################################################################################################################
    ################################################### TWAP ORDER ET SUBSCRIPTION #####################################################
    ####################################################################################################################################
    ####################################################################################################################################

    def frame_twap_order(self):
        # Frame pour créer TWAP Order
        twap_frame = ttk.LabelFrame(self.scrollable_frame, text="Créer TWAP Order")
        twap_frame.pack(fill="x", padx=5, pady=5)

        twap_frame.columnconfigure(0, weight=1)
        twap_frame.columnconfigure(1, weight=1)
        twap_frame.columnconfigure(2, weight=1)
        twap_frame.columnconfigure(3, weight=1)
        twap_frame.columnconfigure(4, weight=1)
        twap_frame.columnconfigure(5, weight=1)

        ttk.Label(twap_frame, text="Symbole:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.twap_symbol_var = tk.StringVar()
        self.twap_symbol_combo = ttk.Combobox(twap_frame, textvariable=self.twap_symbol_var)
        self.twap_symbol_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(twap_frame, text="Sens (buy/sell):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.twap_side_var = ttk.Entry(twap_frame)
        self.twap_side_var.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        ttk.Label(twap_frame, text="Quantité:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.twap_quantity_entry = ttk.Entry(twap_frame)
        self.twap_quantity_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(twap_frame, text="Durée (en seconde):").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.twap_duration_entry = ttk.Entry(twap_frame)
        self.twap_duration_entry.grid(row=1, column=3, padx=5, pady=5, sticky="ew")

        ttk.Label(twap_frame, text="Nb de slice:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.twap_slice_entry = ttk.Entry(twap_frame)
        self.twap_slice_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(twap_frame, text="Limite de prix:").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.twap_price_limit = ttk.Entry(twap_frame)
        self.twap_price_limit.grid(row=2, column=3, padx=5, pady=5, sticky="ew")

        ttk.Button(twap_frame, text="Créer TWAP", command=self.create_twap_order).grid(row=3, column=0, columnspan=6, padx=5, pady=5)

    def frame_twap_sub_follow(self):
        # Frame pour suivi TWAP et subscription (première ligne, 2 colonnes)
        suivi_frame = ttk.LabelFrame(self.scrollable_frame, text="Suivi et Subscription")
        suivi_frame.pack(fill="both", padx=5, pady=5, expand=True)

        suivi_frame.columnconfigure(0, weight=1)
        suivi_frame.columnconfigure(1, weight=1)
        suivi_frame.rowconfigure(1, weight=1)

        twap_header = ttk.Frame(suivi_frame)
        twap_header.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Label(twap_header, text="Suivi TWAP").grid(row=0, column=0, sticky="w", padx=5)
        
        sub_header = ttk.Frame(suivi_frame)
        sub_header.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.twap_status_text = scrolledtext.ScrolledText(suivi_frame, height=10)
        self.twap_status_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

    def create_twap_order(self):
        if self.client.token is None:
            messagebox.showerror("Erreur", "Veuillez vous connecter d'abord.")
            return
        
        exchange = self.exchange_var.get()
        symbol = self.twap_symbol_var.get()
        quantity = self.twap_quantity_entry.get()
        side = self.twap_side_var.get()
        limit_price = self.twap_price_limit.get()
        slices = self.twap_slice_entry.get()
        duration_seconds = self.twap_duration_entry.get()

        if not symbol or not quantity or not slices or not duration_seconds or not side:
            messagebox.showerror("Erreur", "Tous les champs doivent être remplis.")
            return
        
        try:
            quantity = float(quantity)
            slices = int(slices)
            duration_seconds = int(duration_seconds)
            limit_price = float(limit_price) if limit_price else None
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez entrer des valeurs numériques valides.")
            return
        
        self.twap_status_text.insert(tk.END, "Création de l'ordre TWAP en cours...\n")
        
        self.run_async(self.async_create_twap_order(exchange=exchange, symbol=symbol, 
                                                    quantity=quantity, side=side, slices=slices, 
                                                    duration_seconds=duration_seconds,token=self.client.token, limit_price=limit_price))

    async def async_create_twap_order(self, exchange, symbol, quantity, side, slices, duration_seconds, token, limit_price):
        order_id = await self.client.create_twap_order(
                exchange=exchange, 
                symbol=symbol, 
                quantity=quantity, 
                side=side, 
                slices=slices, 
                duration_seconds=duration_seconds, 
                limit_price=limit_price
            )
        if order_id:
            self.current_twap_order_id = order_id
            messagebox.showinfo("TWAP", f"TWAP Order créé avec succès : {order_id}")
            
            # Mise à jour immédiate du statut et démarrage d'une mise à jour régulière
            await self.async_update_twap_status()
            
            # Programmer une mise à jour régulière du statut toutes les 2 secondes
            await asyncio.sleep(2) 
            self.run_async(self.async_update_twap_status())
            
            return True
        else:
            messagebox.showerror("TWAP", "Échec de la création du TWAP Order.")
            return False
        
    async def async_update_twap_status(self):
        status = await self.client.get_order_status(self.current_twap_order_id)

        self.twap_status_text.delete("1.0", tk.END)

        self.twap_status_text.insert(tk.END, f"\nOrdre ID: {self.current_twap_order_id}\n")
        self.twap_status_text.insert(tk.END, f"Statut: {status.get('status', 'inconnu')}\n")
        filtered_status = {k: v for k, v in status.items() if k != "executions"}
        self.twap_status_text.insert(tk.END, f"Statut: {filtered_status}\n")
        for exec in status.get("executions", []):
            self.twap_status_text.insert(tk.END, f"Execution avancement: {exec}\n")

        if status.get("status") in ["completed", "error"]:
            self.current_twap_order_id = None
        
        await asyncio.sleep(2)
        self.run_async(self.async_update_twap_status())

if __name__ == "__main__":
    root = tk.Tk()
    app = APIGUI(root)
    root.mainloop()
