import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import asyncio
import threading
import pandas as pd
from client.client_side import ClientSide
from client.client_credentials import Credentials

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

    def create_widgets(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

         # Initialiser toutes les variables de symbole
        self.symbol_var = tk.StringVar()  # Pour le menu principal
        self.symbol_sub = tk.StringVar()  # Pour les abonnements
        self.twap_symbol_var = tk.StringVar()  # Pour les ordres TWAP

        self.frame_connexion()
        self.frame_exchange_selection()
        self.frame_symbol_selection()
        self.frame_order_book()
        self.frame_twap_order()
        self.frame_twap_sub_follow()
        self.frame_order_portfolio()

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

        ttk.Button(exchange_frame, text="Charger Exchanges", command=self.update_exchanges).pack(side="left", padx=5)
        ttk.Button(exchange_frame, text="Sélectionner", command=self.update_symbols).pack(side="left", padx=5)

    def update_exchanges(self):
        self.run_async(self.async_update_exchanges())

    async def async_update_exchanges(self):
        exchanges = await self.client.get_supported_exchanges()
        if exchanges:
            self.exchange_combo["values"] = ["Tous"] + exchanges
            self.exchange_var.set("Tous")  # Par défaut, on sélectionne "Tous"

    def frame_symbol_selection(self):
        # Frame pour selection de symboles
        self.symbol_var = tk.StringVar()
        symbol_frame = ttk.LabelFrame(self.root, text="Symboles")
        symbol_frame.pack(fill="x", padx=5, pady=5)
        
        self.symbol_combo = ttk.Combobox(symbol_frame, textvariable=self.symbol_var)
        self.symbol_combo.pack(side="left", padx=5)
        
        ttk.Button(symbol_frame, text="Charger Symbols", command=self.update_symbols).pack(side="left", padx=5)
        ttk.Button(symbol_frame, text="Obtenir Order Book", command=self.rien).pack(side="left", padx=5)
        ttk.Button(symbol_frame, text="Analyser Order Book", command=self.rien).pack(side="left", padx=5)

    def update_symbols(self):
        self.run_async(self.async_update_symbols())

    async def async_update_symbols(self):
        exchanges = self.exchange_combo.get()
        if exchanges:
            pairs = await self.client.get_trading_pairs(exchanges)
            
            self.symbol_combo['values'] = pairs
            self.symbol_combo_sub['values'] = pairs
            self.twap_symbol_combo['values'] = pairs 
            
            # Si on a des pairs, mettre une valeur par défaut
            if pairs:
                self.symbol_var.set(pairs[0])
                self.symbol_sub.set(pairs[0])
                self.twap_symbol_var.set(pairs[0])

    def frame_order_book(self):
        # Frame pour affichage des ordres et transactions (bids, asks et statistique sur une seule ligne)
        book_frame = ttk.LabelFrame(self.root, text="Order Book et Statistiques")
        book_frame.pack(fill="both", padx=5, pady=5)

        book_frame.columnconfigure(0, weight=1)
        book_frame.columnconfigure(1, weight=1)
        book_frame.columnconfigure(2, weight=1)
        book_frame.rowconfigure(1, weight=1)

        ttk.Label(book_frame, text="Bids").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(book_frame, text="Asks").grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(book_frame, text="Statistiques").grid(row=0, column=2, padx=5, pady=5)

        self.bids_text = scrolledtext.ScrolledText(book_frame, height=10, width=40)
        self.bids_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.asks_text = scrolledtext.ScrolledText(book_frame, height=10, width=40)
        self.asks_text.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        self.stat_text = scrolledtext.ScrolledText(book_frame, height=10, width=40)
        self.stat_text.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")
        
    def update_book(self):
        self.run_async(self.async_update_book())

    async def async_update_book(self):
        symbol = self.symbol_var.get()
        selected_exchange = self.exchange_var.get()
        exchanges = await self.client.get_supported_exchanges()

        if not symbol:
            messagebox.showerror("Erreur", "Veuillez sélectionner un symbole!")
            return

        # On récupère les données pour tous les exchanges si "Tous" est sélectionné
        if selected_exchange == 'Tous':
            all_data = []
            for exchange in exchanges:
                data = await self.client.get_klines(exchange, symbol)
                if data:
                    df = pd.DataFrame(data)
                    df.insert(0, "Exchange", exchange)  # Ajouter colonne "Exchange"
                    all_data.append(df)

            df = pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()
        else:
            data = await self.client.get_klines(selected_exchange, symbol)
            df = pd.DataFrame(data) if data else pd.DataFrame()

        # Vérification et affichage des résultats
        self.bids_text.delete('1.0', tk.END)
        self.asks_text.delete('1.0', tk.END)
        self.stat_text.delete('1.0', tk.END)
        if df.empty:
            self.bids_text.insert(tk.END, "Aucune donnée disponible.")
            self.asks_text.insert(tk.END, "Aucune donnée disponible.")
            self.stat_text.insert(tk.END, "Aucune donnée disponible.")
            return
        
        # Vérification que les colonnes existent
        if df.shape[1] < 5:
            messagebox.showerror("Erreur", "Données de l'order book incorrectes.")
            return

        df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0], unit='ns', errors='coerce')

        # Séparation des bids et asks (hypothèse : ordres triés par prix)
        bids = df.iloc[:5].to_string(index=False)  # Premières lignes (simulées comme "bids")
        asks = df.iloc[-5:].to_string(index=False)  # Dernières lignes (simulées comme "asks")

        self.bids_text.insert(tk.END, bids)
        self.asks_text.insert(tk.END, asks)

        # Affichage du portfolio fictif
        moyenne = df[4].mean() if not df.empty else 0
        stat = f"Total Assets: {len(df)}\nValeur Moyenne: {moyenne:.2f}"
        self.stat_text.insert(tk.END, stat)

    ####################################################################################################################################
    ####################################################################################################################################
    ################################################### TWAP ORDER ET SUBSCRIPTION #####################################################
    ####################################################################################################################################
    ####################################################################################################################################

    def frame_twap_order(self):
        # Frame pour créer TWAP Order
        twap_frame = ttk.LabelFrame(self.root, text="Créer TWAP Order")
        twap_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(twap_frame, text="Symbole:").pack(side="left", padx=5)
        self.twap_symbol_var = tk.StringVar()
        self.twap_symbol_combo = ttk.Combobox(twap_frame, textvariable=self.twap_symbol_var)
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
        suivi_frame = ttk.LabelFrame(self.root, text="Suivi et Subscription")
        suivi_frame.pack(fill="both", padx=5, pady=5, expand=True)

        suivi_frame.columnconfigure(0, weight=1)
        suivi_frame.columnconfigure(1, weight=1)
        suivi_frame.rowconfigure(1, weight=1)

        twap_header = ttk.Frame(suivi_frame)
        twap_header.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Label(twap_header, text="Suivi TWAP").grid(row=0, column=0, sticky="w", padx=5)
        
        sub_header = ttk.Frame(suivi_frame)
        sub_header.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(sub_header, text="Subscription : Klines").pack(side="left")

        self.symbol_sub = tk.StringVar()        
        self.symbol_combo_sub = ttk.Combobox(sub_header, textvariable=self.symbol_sub)
        self.symbol_combo_sub.pack(side="left", padx=5)
        ttk.Button(sub_header, text="S'abonner", command=self.subscribe_to_symbol).pack(side="left", padx=5)
        ttk.Button(sub_header, text="Se désabonner", command=self.unsubscribe_from_symbol).pack(side="left", padx=5)

        self.twap_status_text = scrolledtext.ScrolledText(suivi_frame, height=10, width=60)
        self.twap_status_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.subscription_text = scrolledtext.ScrolledText(suivi_frame, height=10, width=60)
        self.subscription_text.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

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
            self.root.after(5000, lambda: self.run_async(self.async_update_twap_status()))
            
            return True
        else:
            messagebox.showerror("TWAP", "Échec de la création du TWAP Order.")
            return False
        
    async def async_update_twap_status(self):
        status = await self.client.get_order_status(self.current_twap_order_id)

        if status.get("status") in ["completed", "error"]:
            print("Ordre terminé!")

        self.twap_status_text.insert(tk.END, f"Ordre ID: {self.current_twap_order_id}\n")
        self.twap_status_text.insert(tk.END, f"Statut: {status.get('status', 'inconnu')}\n")
        self.twap_status_text.insert(tk.END, f"Statut: {status}\n")
        
    def subscribe_to_symbol(self):
        symbol = self.symbol_sub.get()
        if not symbol:
            messagebox.showerror("Erreur", "Veuillez sélectionner un symbole!")
            return
            
        self.run_async(self.async_subscribe_to_symbol(symbol))
    
    async def async_subscribe_to_symbol(self, symbol):
        try:
            if not hasattr(self.client, 'ws') or not self.client.ws:
                await self.client.connect_websocket()

            await self.client.subscribe_symbol(symbol)
            self.ws_subscribed_symbols.add(symbol)
            messagebox.showinfo("Abonnement", f"Abonné au symbole {symbol}")
            
            # Récupérer les klines pour le symbole
            exchange = self.exchange_var.get()
            if exchange and exchange != "Tous":
                await self.fetch_klines_for_symbol(exchange, symbol)
            
            # Mettre à jour l'affichage des abonnements
            self.update_subscription_text()
        except Exception as e:
            messagebox.showerror("Erreur d'abonnement", str(e))
    
    def unsubscribe_from_symbol(self):
        symbol = self.symbol_var.get()
        if not symbol:
            messagebox.showerror("Erreur", "Veuillez sélectionner un symbole!")
            return
            
        self.run_async(self.async_unsubscribe_from_symbol(symbol))
    
    async def async_unsubscribe_from_symbol(self, symbol):
        try:
            if symbol in self.ws_subscribed_symbols:
                self.ws_subscribed_symbols.remove(symbol)
                
                # Supprimer les données klines pour ce symbole
                if symbol in self.klines_data:
                    del self.klines_data[symbol]
                
                messagebox.showinfo("Désabonnement", f"Désabonné du symbole {symbol}")
            
            # Mettre à jour l'affichage des abonnements
            self.update_subscription_text()
            
        except Exception as e:
            messagebox.showerror("Erreur de désabonnement", str(e))
    
    def update_subscription_text(self):
            
        self.subscription_text.insert(tk.END, "Abonnements actifs:\n")
        self.subscription_text.insert(tk.END, "-------------------------\n")

        if self.client.token is None:
            self.subscription_text.insert(tk.END, "Veuillez vous connecter d'abord.\n")
            return
        
        # Afficher les klines pour chaque symbole abonné
        for symbol in self.ws_subscribed_symbols:
            self.subscription_text.insert(tk.END, f"\n=== {symbol} ===\n", "heading")
            
            if symbol in self.klines_data and self.klines_data[symbol]:
                klines = self.klines_data[symbol]
                # En-tête des colonnes
                self.subscription_text.insert(tk.END, "Date/Heure          | Open    | High    | Low     | Close   | Volume\n")
                self.subscription_text.insert(tk.END, "-" * 75 + "\n")
                
                # Formater et afficher les données klines
                for kline in klines[:10]:  # Limiter à 10 klines pour chaque symbole
                    try:
                        timestamp = pd.to_datetime(kline['timestamp'], unit='ns', errors='coerce')
                        self.subscription_text.insert(tk.END, 
                            f"{timestamp:%Y-%m-%d %H:%M} | {kline['open']:<7.2f} | {kline['high']:<7.2f} | {kline['low']:<7.2f} | {kline['close']:<7.2f} | {kline['volume']:<7.2f}\n")
                    except (KeyError, TypeError):
                        self.subscription_text.insert(tk.END, f"Données incorrectes: {kline}\n")
            else:
                self.subscription_text.insert(tk.END, "  Aucune donnée disponible\n")

    def start_klines_auto_update(self):
        """Démarre la mise à jour automatique des klines toutes les 30 secondes"""
        self.run_async(self.async_update_all_klines())
        # Planifier la prochaine mise à jour
        self.root.after(10000, self.start_klines_auto_update)

    async def async_update_all_klines(self):
        """Met à jour les klines pour tous les symboles abonnés"""
        exchange = self.exchange_var.get()
        if exchange and exchange != "Tous":
            for symbol in self.ws_subscribed_symbols:
                await self.fetch_klines_for_symbol(exchange, symbol)
            # Mettre à jour l'affichage
            self.update_subscription_text()

    async def fetch_klines_for_symbol(self, exchange, symbol, interval="1m", limit=10):
        """Récupère les klines pour un symbole spécifique"""
        try:
            klines = await self.client.get_klines(exchange, symbol, interval=interval, limit=limit)
            if klines:
                self.klines_data[symbol] = klines
                return True
            return False
        except Exception as e:
            print(f"Erreur lors de la récupération des klines pour {symbol}: {e}")
            return False

    ####################################################################################################################################
    ####################################################################################################################################
    ####################################################### ORDER ET PORFOLIO ##########################################################
    ####################################################################################################################################
    ####################################################################################################################################

    def frame_order_portfolio(self):
        # Frame pour Order et Portfolio (deuxième ligne, 2 colonnes)
        order_portfolio_frame = ttk.LabelFrame(self.root, text="Order et Portfolio")
        order_portfolio_frame.pack(fill="both", padx=5, pady=5, expand=True)

        order_portfolio_frame.columnconfigure(0, weight=1)
        order_portfolio_frame.columnconfigure(1, weight=1)
        order_portfolio_frame.rowconfigure(1, weight=1)

        # Header frames pour titre + bouton
        order_header = ttk.Frame(order_portfolio_frame)
        order_header.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Label(order_header, text="Order").pack(side="left")

        self.order_i = tk.StringVar()        
        self.order_combo = ttk.Combobox(order_header, textvariable=self.order_i)
        self.order_combo.pack(side="left", padx=5)
        ttk.Button(order_header, text="Cancel Order", command=self.rien).pack(side="left", padx=5)

        portfolio_header = ttk.Frame(order_portfolio_frame)
        portfolio_header.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(portfolio_header, text="Portfolio").pack(side="left")
        ttk.Button(portfolio_header, text="Actualiser", command=self.rien).pack(side="left", padx=5)

        # Création des zones de texte avec une hauteur de 15 (1.5x la hauteur originale de 10)
        self.order_text = scrolledtext.ScrolledText(order_portfolio_frame, height=15, width=60)
        self.order_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.portfolio_text = scrolledtext.ScrolledText(order_portfolio_frame, height=15, width=60)
        self.portfolio_text.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
  


    def rien(self):
        pass

if __name__ == "__main__":
    root = tk.Tk()
    app = APIGUI(root)
    root.mainloop()
