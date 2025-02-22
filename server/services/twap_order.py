from datetime import datetime


class TWAPOrder:
    def __init__(
            self,
            subscription_manager,
            exchange: str,
            symbol: str,
            quantity: float,
            slices: int,
            duration_seconds: int
    ):
        self.subscription_manager = subscription_manager
        self.exchange = exchange.lower()
        self.symbol = symbol.upper()
        self.quantity = quantity
        self.slices = slices
        self.duration_seconds = duration_seconds

        # Calculer la quantité par slice
        self.quantity_per_slice = self.quantity / self.slices

        # Temps entre chaque slice
        self.interval_seconds = duration_seconds / slices

        # Statut et suivi
        self.executed_quantity = 0
        self.executions = []
        self.status = "active"  # active, completed, error

    async def start(self):
        """S'abonne au flux de données"""
        await self.subscription_manager.add_subscription(self.symbol)

    async def execute_slice(self):
        """Exécute une slice au prix du marché actuel"""
        try:
            # Récupérer l'orderbook actuel depuis les websockets
            order_book = self.subscription_manager.exchange_connectors[self.exchange].order_book.get(self.symbol)

            if order_book and order_book["asks"]:
                # Prendre le premier prix ask
                execution_price = order_book["asks"][0][0]

                # Enregistrer l'exécution
                self.executions.append({
                    "price": execution_price,
                    "quantity": self.quantity_per_slice,
                    "timestamp": datetime.now().isoformat()
                })
                self.executed_quantity += self.quantity_per_slice

                if self.executed_quantity >= self.quantity:
                    self.status = "completed"
                    # Se désabonner du flux
                    await self.subscription_manager.remove_subscription(self.symbol)
                return True

        except Exception as e:
            print(f"Erreur lors de l'exécution de la slice: {e}")
            self.status = "error"
            return False

        return False

    def get_status(self):
        """Retourne le statut actuel de l'ordre"""
        return {
            "status": self.status,
            "executed_quantity": self.executed_quantity,
            "total_quantity": self.quantity,
            "slices_executed": len(self.executions),
            "total_slices": self.slices,
            "executions": self.executions,
            "average_price": sum(ex["price"] * ex["quantity"] for ex in self.executions) /
                             self.executed_quantity if self.executed_quantity > 0 else None
        }