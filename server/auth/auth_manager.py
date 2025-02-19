from fastapi import HTTPException
from werkzeug.security import check_password_hash
from .credentials import USERS


class AuthenticationManager:
    def __init__(self):
        # Utilisateurs importés depuis credentials.py
        self.users = USERS
        # Stockage des tokens
        self.tokens = {}

    def authenticate_user(self, username: str, password: str) -> str:
        """Authentifie un utilisateur et retourne un token"""
        # Vérifie si l'utilisateur existe et si le mot de passe correspond
        if username in self.users and check_password_hash(self.users[username], password):
            # Crée un token s'il n'existe pas
            if username not in self.tokens:
                self.tokens[username] = f"token_for_{username}"
            return self.tokens[username]
        return None

    def verify_token(self, token: str) -> str:
        """Vérifie si le token est valide"""
        if not token:
            raise HTTPException(status_code=401, detail="Token manquant")

        for username, stored_token in self.tokens.items():
            if stored_token == token:
                return username

        raise HTTPException(status_code=401, detail="Token invalide")