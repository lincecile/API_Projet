import threading
import time
import socket
import uvicorn
from server.api.public import app

import tkinter as tk
from gui.API_interface import APIGUI

def run_server():
    """Lance Uvicorn dans un thread séparé avec 0.0.0.0"""
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

def wait_for_server(host="127.0.0.1", port=8000):
    """Attend que le serveur FastAPI soit prêt"""
    while True:
        try:
            with socket.create_connection((host, port), timeout=2):
                print('Serveur prêt')
                time.sleep(1)
                return True  # Serveur prêt
        except (OSError, ConnectionRefusedError):
            time.sleep(0.5)  # Réessayer après 500ms

if __name__ == "__main__":
    # Démarrer le serveur FastAPI dans un thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Attendre que le serveur soit prêt
    wait_for_server()  # Vérifie en se connectant à 127.0.0.1

    # Lancer l'interface Tkinter après que le serveur soit bien lancé
    root = tk.Tk()
    app = APIGUI(root)
    root.mainloop()
