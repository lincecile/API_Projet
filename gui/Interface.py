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

        self.create_widgets()

        self.ws_subscribed_symbols = set()
        self.klines_data = {}

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
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

         # Initialiser toutes les variables de symbole
        self.symbol_var = tk.StringVar()  # Pour le menu principal
        self.symbol_graph = tk.StringVar()  # Pour le graphique
        self.twap_symbol_var = tk.StringVar()  # Pour les ordres TWAP

        self.frame_connexion()
        self.frame_exchange_selection()
        self.frame_symbol_selection()
        self.frame_order_book()
        self.frame_twap_order()
        self.frame_twap_sub_follow()

    def frame_connexion(self):
        # Frame pour connexion
        login_frame = ttk.LabelFrame(self.root, text="Connexion API")
        login_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(login_frame, text="Username:").pack(side="left", padx=5)
        self.username_entry = ttk.Entry(login_frame)
        self.username_entry.pack(side="left", padx=5)

        ttk.Label(login_frame, text="Password:").pack(side="left", padx=5)
        self.password_entry = ttk.Entry(login_frame, show="*")
        self.password_entry.pack(side="left", padx=5)

        ttk.Button(login_frame, text="Login", command=self.login).pack(side="left", padx=5)

    ####################################################################################################################################
    ###################################### INTERFACE CONNEXION + ORDER BOOK + KLINES ###################################################
    ####################################################################################################################################

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        creds = Credentials(username, password)
        self.run_async(self.async_login(creds))

    async def async_login(self, creds):
        success = await self.client.login(creds)
        if success:
            messagebox.showinfo("Login", "Connexion réussie!")
            # Démarrer la mise à jour automatique des klines
            self.start_klines_auto_update()
        else:
            messagebox.showerror("Login", "Échec de la connexion!")

    def frame_exchange_selection(self):
        # Frame pour selection de l'exchange
        self.exchange_var = tk.StringVar()
        exchange_frame = ttk.LabelFrame(self.root, text="Exchanges")
        exchange_frame.pack(fill="x", padx=5, pady=5)

        self.exchange_combo = ttk.Combobox(exchange_frame, textvariable=self.exchange_var, state="readonly")
        self.exchange_combo.pack(side="left", padx=5)
        self.exchange_var.set("  --- Sélectionner ---") # Par défaut

        ttk.Button(exchange_frame, text="Charger Exchanges", command=self.update_exchanges).pack(side="left", padx=5)
        ttk.Button(exchange_frame, text="Sélectionner", command=self.update_symbols).pack(side="left", padx=5)

    def update_exchanges(self):
        self.run_async(self.async_update_exchanges())

    async def async_update_exchanges(self):
        exchanges = await self.client.get_supported_exchanges()
        if exchanges:
            self.exchange_combo["values"] = exchanges

    def update_symbols(self):
        self.run_async(self.async_update_symbols())

    async def async_update_symbols(self):
        exchanges = self.exchange_combo.get()
        if exchanges:
            pairs = await self.client.get_trading_pairs(exchanges)

            self.symbol_combo['values'] = pairs
            self.symbol_combo_graph['values'] = pairs
            self.twap_symbol_combo['values'] = pairs 
            
            # Si on a des pairs, mettre une valeur par défaut
            if pairs:
                self.symbol_var.set(pairs[0])
                self.symbol_graph.set(pairs[0])
                self.twap_symbol_var.set(pairs[0])

    def frame_symbol_selection(self):
        # Frame pour selection de symboles
        self.symbol_var = tk.StringVar()
        symbol_frame = ttk.LabelFrame(self.root, text="Symboles")
        symbol_frame.pack(fill="x", padx=5, pady=5)

        self.symbol_combo = ttk.Combobox(symbol_frame, textvariable=self.symbol_var)
        self.symbol_combo.pack(side="left", padx=5)
        self.symbol_var.set("  --- Sélectionner ---") # Par défaut

        ttk.Button(symbol_frame, text="Get Symbols", command=self.update_symbols).pack(side="left", padx=5)
        ttk.Button(symbol_frame, text="Subscribe Order Book and Klines", command=self.update_symbol_kline_ws).pack(side="left", padx=5)
        ttk.Button(symbol_frame, text="Klines Only", command=self.klines_update).pack(side="left", padx=5)

    def frame_order_book(self):
        # Frame pour affichage des ordres et transactions (bids, asks et statistique sur une seule ligne)
        book_frame = ttk.LabelFrame(self.root, text="Order Book et Klines")
        book_frame.pack(fill="both", padx=5, pady=5, expand=True)

        book_frame.columnconfigure(0, weight=1)
        book_frame.columnconfigure(1, weight=1)
        book_frame.columnconfigure(2, weight=1)
        book_frame.rowconfigure(1, weight=1)

        ttk.Label(book_frame, text="Bids").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(book_frame, text="Asks").grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(book_frame, text="Klines").grid(row=0, column=2, padx=5, pady=5)

        self.bids_text = scrolledtext.ScrolledText(book_frame, height=10, width=30)
        self.bids_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.asks_text = scrolledtext.ScrolledText(book_frame, height=10, width=30)
        self.asks_text.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        self.klines_text = scrolledtext.ScrolledText(book_frame, height=10, width=50)
        self.klines_text.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")

    def update_symbol_kline_ws(self):
        self.subscribe_symbol()
        self.klines_update()

    def subscribe_symbol(self):

        if self.client.token is None:
            messagebox.showerror("Erreur", "Veuillez vous connecter d'abord.")
            return
        
        symbol = self.symbol_var.get()
        if not symbol:
            messagebox.showerror("Erreur", "Veuillez sélectionner un symbole!")
            return
        self.run_async(self.async_subscribe_symbol(symbol))
        
    async def async_subscribe_symbol(self, symbol):
        await self.client.subscribe_symbol(symbol)
        print('start')
        self.ws_subscribed_symbols.add(symbol)
        print(f"Abonné à {symbol}")
        self.klines_text.insert(tk.END, f"Abonné à {symbol}\n")

        # Récupérer les klines pour le symbole
        exchange = self.exchange_var.get()
        if exchange:
            await self.fetch_klines_for_symbol(exchange, symbol)
    
    def update_order_book(self, data):
        
        current_symbol = self.symbol_var.get()
        
        if data["symbol"] != current_symbol:
            print('symbol nn')
            return
        
        bids = data["bids"]
        asks = data["asks"]
        
        self.bids_text.delete("1.0", tk.END)
        self.asks_text.delete("1.0", tk.END)
        
        for i, (price, quantity) in enumerate(bids):
            self.bids_text.insert(tk.END, f"{i+1}. Price: {price}, Quantity: {quantity}\n")
            
        for i, (price, quantity) in enumerate(asks):
            self.asks_text.insert(tk.END, f"{i+1}. Price: {price}, Quantity: {quantity}\n")

        print('done')

    def klines_update(self):
        """Démarre la mise à jour automatique des klines toutes les 30 secondes"""
        self.run_async(self.async_update_all_klines())
        # self.root.after(10000, self.start_klines_auto_update)

    async def async_update_all_klines(self):
        """Met à jour les klines pour tous les symboles abonnés"""
        exchange = self.exchange_var.get()
        symbol = self.symbol_var.get()
        if exchange:
            await self.fetch_klines_for_symbol(exchange, symbol)

    async def fetch_klines_for_symbol(self, exchange, symbol, interval="1m", limit=10):
        """Récupère les klines pour un symbole spécifique"""
        klines = await self.client.get_klines(exchange, symbol, interval=interval, limit=limit)
        if klines:
            self.klines_text.delete('1.0', tk.END)
            self.klines_data[symbol] = klines
            for kline in klines[:10]:  # Limiter à 10 klines pour chaque symbole
                try:
                    timestamp = pd.to_datetime(kline['timestamp'], unit='ns', errors='coerce')
                    self.klines_text.insert(tk.END, "   timestamp   | open | high | low | close | volume\n")
                    self.klines_text.insert(tk.END, 
                        f"{timestamp:%Y-%m-%d %H:%M} | {kline['open']:<7.2f} | {kline['high']:<7.2f} | {kline['low']:<7.2f} | {kline['close']:<7.2f} | {kline['volume']:<7.2f}\n")
                except (KeyError, TypeError):
                    self.klines_text.insert(tk.END, f"Données incorrectes: {kline}\n")
        else:
            messagebox.showinfo("Info", "Aucune donnée disponible")


    ####################################################################################################################################
    ################################################### TWAP ORDER ET KLINES GRAPH #####################################################
    ####################################################################################################################################

    def frame_twap_order(self):
        # Frame pour créer TWAP Order
        twap_frame = ttk.LabelFrame(self.root, text="Créer TWAP Order")
        twap_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(twap_frame, text="Symbole:").pack(side="left", padx=5)
        self.twap_symbol_var = tk.StringVar()
        self.twap_symbol_combo = ttk.Combobox(twap_frame, textvariable=self.twap_symbol_var)
        self.twap_symbol_var.set("  --- Sélectionner ---")
        self.twap_symbol_combo.pack(side="left", padx=5)

        ttk.Label(twap_frame, text="Sens (buy/sell):").pack(side="left", padx=5)
        self.twap_side_var = ttk.Entry(twap_frame)
        self.twap_side_var.pack(side="left", padx=5)

        ttk.Label(twap_frame, text="Quantité:").pack(side="left", padx=5)
        self.twap_quantity_entry = ttk.Entry(twap_frame)
        self.twap_quantity_entry.pack(side="left", padx=5)

        ttk.Label(twap_frame, text="Durée (en seconde):").pack(side="left", padx=5)
        self.twap_duration_entry = ttk.Entry(twap_frame)
        self.twap_duration_entry.pack(side="left", padx=5)

        ttk.Label(twap_frame, text="Intervalle (s):").pack(side="left", padx=5)
        self.twap_interval_entry = ttk.Entry(twap_frame)
        self.twap_interval_entry.pack(side="left", padx=5)

        ttk.Label(twap_frame, text="Limite de prix:").pack(side="left", padx=5)
        self.twap_price_limit = ttk.Entry(twap_frame)
        self.twap_price_limit.pack(side="left", padx=5)

        ttk.Button(twap_frame, text="Créer TWAP", command=self.create_twap_order).pack(side="left", padx=5)

    def frame_twap_sub_follow(self):
        # Frame pour suivi TWAP et subscription (première ligne, 2 colonnes)
        suivi_frame = ttk.LabelFrame(self.root, text="Suivi et Graphique")
        suivi_frame.pack(fill="both", padx=5, pady=5, expand=True)

        suivi_frame.columnconfigure(0, weight=1)
        suivi_frame.columnconfigure(1, weight=1)
        suivi_frame.rowconfigure(1, weight=1)

        twap_header = ttk.Frame(suivi_frame)
        twap_header.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Label(twap_header, text="Suivi TWAP").grid(row=0, column=0, sticky="w", padx=5)

        sub_header = ttk.Frame(suivi_frame)
        sub_header.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(sub_header, text="Graphique").pack(side="left")

        self.symbol_graph = tk.StringVar()        
        self.symbol_combo_graph = ttk.Combobox(sub_header, textvariable=self.symbol_graph)
        self.symbol_combo_graph.set("  --- Sélectionner ---")
        self.symbol_combo_graph.pack(side="left", padx=5)
        ttk.Button(sub_header, text="Get Historical Graph", command=self.fetch_and_display_klines).pack(side="left", padx=5)

        self.twap_status_text = scrolledtext.ScrolledText(suivi_frame, height=10, width=74)
        self.twap_status_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.symbol_graph_frame = scrolledtext.ScrolledText(suivi_frame, height=10, width=40)
        self.symbol_graph_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

    def create_twap_order(self):
        if self.client.token is None:
            messagebox.showerror("Erreur", "Veuillez vous connecter d'abord.")
            return

        exchange = self.exchange_var.get()
        symbol = self.twap_symbol_var.get()
        quantity = self.twap_quantity_entry.get()
        side = self.twap_side_var.get()
        limit_price = self.twap_price_limit.get()
        slices = self.twap_interval_entry.get()
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

        self.twap_status_text.delete('1.0', tk.END)
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
            self.root.after(2000, lambda: self.run_async(self.async_update_twap_status()))

            return True
        else:
            messagebox.showerror("TWAP", "Échec de la création du TWAP Order.")
            return False

    async def async_update_twap_status(self):
        status = await self.client.get_order_status(self.current_twap_order_id)

        if status.get("status") in ["completed", "error"]:
            print("Ordre terminé!")

        self.twap_status_text.insert(tk.END, f"\nOrdre ID: {self.current_twap_order_id}\n")
        filtered_status = {k: v for k, v in status.items() if k not in ["executions",'status']}
        self.twap_status_text.insert(tk.END, f"Statut: {status.get("status", 'inconnu')}\n")
        self.twap_status_text.insert(tk.END, f"Info: {filtered_status}\n")
        for exec in status.get("executions", []):
            self.twap_status_text.insert(tk.END, f"Execution avancement: {exec}\n")

        if status.get("status") in ["completed", "error"]:
            self.current_twap_order_id = None


    def fetch_and_display_klines(self):
        self.run_async(self.async_fetch_and_display_klines())

    async def async_fetch_and_display_klines(self):
        exchange = self.exchange_var.get()
        symbol = self.symbol_graph.get()
        klines = await self.client.get_klines(exchange, symbol, "15m", 100)
        
        if not klines:
            messagebox.showerror("Erreur", "Aucune donnée de klines disponible pour ce symbole.")
            return

        df = pd.DataFrame(klines, columns=["timestamp", "open", "high", "low", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ns')
        fig = Figure(figsize=(3, 3),dpi=100)
        ax = fig.add_subplot()
        (line,) = ax.plot(df["timestamp"], df["close"])
        ax.set_xlabel("time [s]")
        ax.set_ylabel(f"kline : {symbol}")
        
        for widget in self.symbol_graph_frame.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=self.symbol_graph_frame) 
        canvas.draw()

        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = APIGUI(root)
    root.mainloop()