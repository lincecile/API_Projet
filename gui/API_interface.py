import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import pandas as pd
from copy import deepcopy

from client.client_side import ClientSide

class APIGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading Platform")
        self.client = ClientSide()
        self.create_widgets()
        self.update_symbols()

    def create_widgets(self):
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=5, pady=5)

        # Top frame for symbol selection and buttons
        top_frame = ttk.LabelFrame(main_container, text="Stock Controls", padding="5")
        top_frame.pack(fill="x", padx=5, pady=5)
        
        self.symbol_var = tk.StringVar()
        self.symbol_combo = ttk.Combobox(top_frame, textvariable=self.symbol_var)
        self.symbol_combo.pack(side="left", padx=5)
        
        ttk.Button(top_frame, text="Refresh Data", command=self.update_order_book).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Refresh Symbols", command=self.update_symbols).pack(side="left", padx=5)
        
        # Middle frame containing order books and portfolio
        middle_frame = ttk.Frame(main_container)
        middle_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Bids frame with quantity input
        bids_frame = ttk.LabelFrame(middle_frame, text="Bids (Buy Orders)", padding="5")
        bids_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        self.bids_text = scrolledtext.ScrolledText(bids_frame, height=15, width=40)
        self.bids_text.pack(fill="both", expand=True)
        
        # Buy controls frame
        buy_controls = ttk.Frame(bids_frame)
        buy_controls.pack(fill="x", pady=5)
        
        ttk.Label(buy_controls, text="Quantity:").pack(side="left", padx=2)
        self.buy_quantity = ttk.Entry(buy_controls, width=10)
        self.buy_quantity.pack(side="left", padx=2)
        self.buy_quantity.insert(0, "100")  # Default value
        
        ttk.Button(buy_controls, text="Buy", command=self.buy_stock).pack(side="left", padx=5)
        
        # Asks frame with quantity input
        asks_frame = ttk.LabelFrame(middle_frame, text="Asks (Sell Orders)", padding="5")
        asks_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        self.asks_text = scrolledtext.ScrolledText(asks_frame, height=15, width=40)
        self.asks_text.pack(fill="both", expand=True)
        
        # Sell controls frame
        sell_controls = ttk.Frame(asks_frame)
        sell_controls.pack(fill="x", pady=5)
        
        ttk.Label(sell_controls, text="Quantity:").pack(side="left", padx=2)
        self.sell_quantity = ttk.Entry(sell_controls, width=10)
        self.sell_quantity.pack(side="left", padx=2)
        self.sell_quantity.insert(0, "100")  # Default value
        
        ttk.Button(sell_controls, text="Sell", command=self.sell_stock).pack(side="left", padx=5)
        
        # Portfolio frame
        portfolio_frame = ttk.LabelFrame(middle_frame, text="Portfolio", padding="5")
        portfolio_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        self.portfolio_text = scrolledtext.ScrolledText(portfolio_frame, height=15, width=40)
        self.portfolio_text.pack(fill="both", expand=True)
        ttk.Button(portfolio_frame, text="Refresh Portfolio", command=self.refresh_portfolio).pack(pady=5)

    def validate_quantity(self, quantity_str: str):
        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                messagebox.showerror("Invalid Quantity", "Quantity must be positive")
                return None
            return quantity
        except ValueError:
            messagebox.showerror("Invalid Quantity", "Please enter a valid number")
            return None

    def update_symbols(self):
        symbols = self.client.get_available_symbols()
        self.symbol_combo['values'] = symbols
        if symbols:
            self.symbol_combo.set(symbols[0])
            self.update_order_book()

    def update_order_book(self):
        symbol = self.symbol_var.get()
        if not symbol:
            return

        data = self.client.get_stock(symbol)
        if data:
            # Update the textboxes with current data
            self.update_order_displays(data)
            self.refresh_portfolio()
            data['order_book']['bids'].sort(key=lambda x: x['price'], reverse=True)
            data['order_book']['asks'].sort(key=lambda x: x['price'])
            return data
        
        
        return None

    def update_order_displays(self, data):
        # Convert and format data
        bids_df = pd.DataFrame(data['order_book']['bids'])
        asks_df = pd.DataFrame(data['order_book']['asks'])
        
        # Clear current displays
        self.bids_text.delete('1.0', tk.END)
        self.asks_text.delete('1.0', tk.END)
        
        if not bids_df.empty:
            bids_df = bids_df.sort_values('price', ascending=False).reset_index(drop=True)
            bids_df['timestamp'] = pd.to_datetime(bids_df['timestamp']).dt.strftime('%H:%M:%S')
            self.bids_text.insert(tk.END, f"Current Price: {data['last_price']}\n\n")
            self.bids_text.insert(tk.END, bids_df.to_string())
            
        if not asks_df.empty:
            asks_df = asks_df.sort_values('price', ascending=True).reset_index(drop=True)
            asks_df['timestamp'] = pd.to_datetime(asks_df['timestamp']).dt.strftime('%H:%M:%S')
            self.asks_text.insert(tk.END, f"Timestamp: {data['timestamp']}\n\n")
            self.asks_text.insert(tk.END, asks_df.to_string())

    def buy_stock(self):
        symbol = self.symbol_var.get()
        if not symbol:
            return
            
        initial_quantity = self.validate_quantity(self.buy_quantity.get())
        if initial_quantity is None:
            return
            
        data = self.update_order_book()  # Get fresh data
        if not data:
            return
            
        success, price, message = self.client.execute_buy_order(symbol, initial_quantity, data)
        
        if success:
            # Mettre à jour l'affichage avec les données modifiées
            self.update_order_displays(data)
            
            # Calculer la quantité exécutée à partir du message
            executed_quantities = [int(x.split()[0]) for x in message.replace("Executed: ", "").split(";")]
            total_executed = sum(executed_quantities)
            
            # Mettre à jour le champ de quantité avec la quantité restante
            remaining_quantity = initial_quantity - total_executed
            if remaining_quantity > 0:
                self.buy_quantity.delete(0, tk.END)
                self.buy_quantity.insert(0, str(remaining_quantity))
            else:
                self.buy_quantity.delete(0, tk.END)
                self.buy_quantity.insert(0, "100")  # Reset to default value
            
            self.refresh_portfolio()
            messagebox.showinfo("Trade Executed", message)
        else:
            messagebox.showerror("Trade Failed", message)

    def sell_stock(self):
        symbol = self.symbol_var.get()
        if not symbol:
            return
            
        initial_quantity = self.validate_quantity(self.sell_quantity.get())
        if initial_quantity is None:
            return
            
        data = self.update_order_book()  # Get fresh data
        if not data:
            return
            
        success, price, message = self.client.execute_sell_order(symbol, initial_quantity, data)
        
        if success:
            # Mettre à jour l'affichage avec les données modifiées
            self.update_order_displays(data)
            
            # Calculer la quantité exécutée à partir du message
            executed_quantities = [int(x.split()[0]) for x in message.replace("Executed: ", "").split(";")]
            total_executed = sum(executed_quantities)
            
            # Mettre à jour le champ de quantité avec la quantité restante
            remaining_quantity = initial_quantity - total_executed
            if remaining_quantity > 0:
                self.sell_quantity.delete(0, tk.END)
                self.sell_quantity.insert(0, str(remaining_quantity))
            else:
                self.sell_quantity.delete(0, tk.END)
                self.sell_quantity.insert(0, "100")  # Reset to default value
            
            self.refresh_portfolio()
            messagebox.showinfo("Trade Executed", message)
        else:
            messagebox.showerror("Trade Failed", message)

    def refresh_portfolio(self):
        self.portfolio_text.delete('1.0', tk.END)
        
        portfolio_valuation = self.client.get_portfolio_valuation()
        if not portfolio_valuation:
            self.portfolio_text.insert(tk.END, "No positions")
            return
        
        # Display total value at the top
        total_value = portfolio_valuation.pop('TOTAL')
        self.portfolio_text.insert(tk.END, f"Total Portfolio Value: ${total_value['market_value']:,.2f}\n\n")
        
        # Display positions
        if portfolio_valuation:
            df = pd.DataFrame.from_dict(portfolio_valuation, orient='index')
            df = df.round(2)
            self.portfolio_text.insert(tk.END, "Current Portfolio:\n\n")
            self.portfolio_text.insert(tk.END, df.to_string())



def main():
    root = tk.Tk()
    app = APIGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()