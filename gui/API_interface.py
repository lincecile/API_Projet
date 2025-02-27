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

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_async(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def create_widgets(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

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
        ttk.Button(symbol_frame, text="Obtenir Order Book", command=self.update_order_book).pack(side="left", padx=5)
        ttk.Button(symbol_frame, text="Analyser Order Book", command=self.show_order_book_stats).pack(side="left", padx=5)

    def update_symbols(self):
        self.run_async(self.async_update_symbols())

    async def async_update_symbols(self):
        exchanges = self.exchange_combo.get()
        if exchanges:
            pairs = await self.client.get_trading_pairs(exchanges)
            self.symbol_combo['values'] = pairs
            if pairs:
                self.symbol_var.set(pairs[0])

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

    def update_order_book(self):
        self.run_async(self.async_update_order_book())

    async def async_update_order_book(self):
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

    def show_order_book_stats(self):
        self.run_async(self.async_show_order_book_stats())

    async def async_show_order_book_stats(self):
        symbol = self.symbol_var.get()
        selected_exchange = self.exchange_var.get()
        print(selected_exchange)

        if not symbol or not selected_exchange:
            messagebox.showerror("Erreur", "Veuillez sélectionner un exchange spécifique et un symbole!")
            return
        
        # Récupération et analyse des statistiques
        stats = await self.analyze_order_book(selected_exchange, symbol)
        
        if "error" in stats:
            messagebox.showerror("Erreur", stats["error"])
            return
        
        # Mise à jour de la zone de statistiques
        self.stat_text.delete('1.0', tk.END)
        
        # Formatage des statistiques pour l'affichage
        stats_display = f"Statistiques carnet d'ordres {stats['symbol']} sur {stats['exchange']}\n"
        stats_display += f"Timestamp: {stats['timestamp']}\n"
        stats_display += f"\n--- BIDS (Acheteurs) ---\n"
        stats_display += f"Nombre d'ordres: {stats['bid_stats']['count']}\n"
        stats_display += f"Volume total: {stats['bid_stats']['volume_total']:.4f}\n"
        stats_display += f"Prix min/max: {stats['bid_stats']['price_min']:.2f} / {stats['bid_stats']['price_max']:.2f}\n"
        stats_display += f"Prix moyen: {stats['bid_stats']['price_avg']:.2f}\n"
        stats_display += f"Écart-type prix: {stats['bid_stats']['price_std']:.2f}\n"
        
        stats_display += f"\n--- ASKS (Vendeurs) ---\n"
        stats_display += f"Nombre d'ordres: {stats['ask_stats']['count']}\n"
        stats_display += f"Volume total: {stats['ask_stats']['volume_total']:.4f}\n"
        stats_display += f"Prix min/max: {stats['ask_stats']['price_min']:.2f} / {stats['ask_stats']['price_max']:.2f}\n"
        stats_display += f"Prix moyen: {stats['ask_stats']['price_avg']:.2f}\n"
        stats_display += f"Écart-type prix: {stats['ask_stats']['price_std']:.2f}\n"
        
        stats_display += f"\n--- MARCHÉ GLOBAL ---\n"
        stats_display += f"Spread: {stats['spread']:.2f} ({stats['spread_percentage']:.2f}%)\n"
        stats_display += f"Ratio déséquilibre: {stats['imbalance_ratio']:.2f}\n"
        stats_display += f"Pression du marché: {stats['market_pressure']}\n"
        stats_display += f"Score de liquidité: {stats['liquidity_score']:.2f}\n"
        
        self.stat_text.insert(tk.END, stats_display)

    async def analyze_order_book(self, exchange, symbol):
        """
        Récupère et analyse le carnet d'ordres pour fournir des statistiques
        sur les bids et les asks.
        
        Args:
            exchange (str): Nom de l'exchange
            symbol (str): Symbole de trading
            
        Returns:
            dict: Statistiques sur le carnet d'ordres
        """
        try:
            # Récupération du carnet d'ordres
            print(exchange, symbol)
            order_book = await self.client.get_klines(exchange, symbol)

            if not order_book:
                return {"error": "Impossible de récupérer le carnet d'ordres"}
            
            # Extraction des bids et asks
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return {"error": "Carnet d'ordres incomplet"}
            
            # Conversion en DataFrame pour faciliter l'analyse
            bids_df = pd.DataFrame(bids, columns=['price', 'amount'])
            asks_df = pd.DataFrame(asks, columns=['price', 'amount'])
            
            # Calcul des statistiques
            bid_stats = {
                "count": len(bids_df),
                "volume_total": bids_df['amount'].sum(),
                "price_min": bids_df['price'].min(),
                "price_max": bids_df['price'].max(),
                "price_avg": bids_df['price'].mean(),
                "price_median": bids_df['price'].median(),
                "price_std": bids_df['price'].std(),
                "spread_internal": bids_df['price'].max() - bids_df['price'].min()
            }
            
            ask_stats = {
                "count": len(asks_df),
                "volume_total": asks_df['amount'].sum(),
                "price_min": asks_df['price'].min(),
                "price_max": asks_df['price'].max(),
                "price_avg": asks_df['price'].mean(),
                "price_median": asks_df['price'].median(),
                "price_std": asks_df['price'].std(),
                "spread_internal": asks_df['price'].max() - asks_df['price'].min()
            }
            
            # Calcul du spread global (différence entre le prix minimum des asks et le prix maximum des bids)
            spread = asks_df['price'].min() - bids_df['price'].max()
            spread_percentage = (spread / asks_df['price'].min()) * 100
            
            # Calcul de la profondeur de marché (volume cumulé à différents niveaux)
            bids_df['cumulative_volume'] = bids_df['amount'].cumsum()
            asks_df['cumulative_volume'] = asks_df['amount'].cumsum()
            
            # Déséquilibre offre/demande
            imbalance_ratio = bid_stats["volume_total"] / ask_stats["volume_total"] if ask_stats["volume_total"] > 0 else float('inf')
            
            return {
                "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "exchange": exchange,
                "bid_stats": bid_stats,
                "ask_stats": ask_stats,
                "spread": spread,
                "spread_percentage": spread_percentage,
                "imbalance_ratio": imbalance_ratio,
                "market_pressure": "Buy" if imbalance_ratio > 1.2 else "Sell" if imbalance_ratio < 0.8 else "Neutral",
                "liquidity_score": (bid_stats["volume_total"] + ask_stats["volume_total"]) / 2
            }
        
        except Exception as e:
            return {"error": f"Erreur lors de l'analyse du carnet d'ordres: {str(e)}"}
    
    def frame_twap_order(self):
        # Frame pour créer TWAP Order
        twap_frame = ttk.LabelFrame(self.root, text="Créer TWAP Order")
        twap_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(twap_frame, text="Symbole:").pack(side="left", padx=5)
        self.twap_symbol_entry = ttk.Entry(twap_frame)
        self.twap_symbol_entry.pack(side="left", padx=5)

        ttk.Label(twap_frame, text="Quantité:").pack(side="left", padx=5)
        self.twap_quantity_entry = ttk.Entry(twap_frame)
        self.twap_quantity_entry.pack(side="left", padx=5)

        ttk.Label(twap_frame, text="Sens (buy/sell):").pack(side="left", padx=5)
        self.twap_price_limit = ttk.Entry(twap_frame)
        self.twap_price_limit.pack(side="left", padx=5)

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

        # Header frames pour titre + bouton
        twap_header = ttk.Frame(suivi_frame)
        twap_header.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        # Label et bouton dans twap_header
        ttk.Label(twap_header, text="Suivi TWAP").grid(row=0, column=0, sticky="w", padx=5)
        ttk.Button(twap_header, text="Actualiser", command=self.auto_update_twap_status).grid(row=0, column=1, padx=5, sticky="e")
        
        sub_header = ttk.Frame(suivi_frame)
        sub_header.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(sub_header, text="Subscription").pack(side="left")

        self.symbol_sub = tk.StringVar()        
        self.symbol_combo_sub = ttk.Combobox(sub_header, textvariable=self.symbol_sub)
        self.symbol_combo_sub.pack(side="left", padx=5)
        ttk.Button(sub_header, text="S'abonner", command=self.subscribe_to_symbol).pack(side="left", padx=5)
        ttk.Button(sub_header, text="Se désabonner", command=self.unsubscribe_from_symbol).pack(side="left", padx=5)

        # Création des zones de texte avec une hauteur de 15 (1.5x la hauteur originale de 10)
        self.twap_status_text = scrolledtext.ScrolledText(suivi_frame, height=10, width=60)
        self.twap_status_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.subscription_text = scrolledtext.ScrolledText(suivi_frame, height=10, width=60)
        self.subscription_text.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

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
  
    def subscribe_to_symbol(self):
        symbol = self.symbol_var.get()
        if not symbol:
            messagebox.showerror("Erreur", "Veuillez sélectionner un symbole!")
            return
            
        self.run_async(self.async_subscribe_to_symbol(symbol))
    
    async def async_subscribe_to_symbol(self, symbol):
        try:
            await self.client.subscribe_symbol(symbol)
            self.ws_subscribed_symbols.add(symbol)
            messagebox.showinfo("Abonnement", f"Abonné au symbole {symbol}")
            
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
            await self.client.unsubscribe_symbol(symbol)
            if symbol in self.ws_subscribed_symbols:
                self.ws_subscribed_symbols.remove(symbol)
            messagebox.showinfo("Désabonnement", f"Désabonné du symbole {symbol}")
            
            # Mettre à jour l'affichage des abonnements
            self.update_subscription_text()
        except Exception as e:
            messagebox.showerror("Erreur de désabonnement", str(e))
    
    def update_subscription_text(self):
        self.subscription_text.delete('1.0', tk.END)
        
        if not self.ws_subscribed_symbols:
            self.subscription_text.insert(tk.END, "Aucun abonnement actif")
            return
            
        self.subscription_text.insert(tk.END, "Abonnements actifs:\n")
        self.subscription_text.insert(tk.END, "-------------------------\n")
        
        for symbol in self.ws_subscribed_symbols:
            self.subscription_text.insert(tk.END, f"- {symbol}\n")

    def create_twap_order(self):
        exchange = self.exchange_var.get()
        symbol = self.twap_symbol_entry.get()
        quantity = self.twap_quantity_entry.get()
        slices = self.twap_interval_entry.get()
        duration_seconds = self.twap_duration_entry.get()

        if not (symbol and quantity and slices and duration_seconds):
            messagebox.showerror("Erreur", "Tous les champs doivent être remplis.")
            return
        
        self.run_async(self.async_create_twap_order(exchange=exchange, symbol=symbol, quantity=quantity, slices=slices, duration_seconds=duration_seconds))

    async def async_create_twap_order(self, exchange, symbol, quantity, slices, duration_seconds):
        print(exchange, symbol, quantity, slices, duration_seconds)
        success = await self.client.create_twap_order(exchange, symbol, float(quantity), int(slices), int(duration_seconds))
        if success:
            messagebox.showinfo("TWAP", "TWAP Order créé avec succès!")
        else:
            messagebox.showerror("TWAP", "Échec de la création du TWAP Order.")

    def auto_update_twap_status(self):
        self.run_async(self.async_update_twap_status())
        self.root.after(2000, self.auto_update_twap_status)  # Actualisation toutes les 2 secondes

    async def async_update_twap_status(self):
        status = await self.client.get_twap_status()
        self.twap_status_text.delete('1.0', tk.END)
        self.twap_status_text.insert(tk.END, status if status else "Aucun statut TWAP disponible.")

    def rien():
        pass

if __name__ == "__main__":
    root = tk.Tk()
    app = APIGUI(root)
    root.mainloop()
