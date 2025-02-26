import asyncio

async def execute_twap_order(app, order_id):
    """Exécute un ordre TWAP"""
    order = app.state.active_orders[order_id]

    try:
        while order.status == "active":
            await order.execute_slice()
            await asyncio.sleep(order.interval_seconds)
    except Exception as e:
        order.status = "error"
        print(f"Erreur lors de l'exécution TWAP: {e}")