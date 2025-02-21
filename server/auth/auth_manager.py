from fastapi import HTTPException
from werkzeug.security import check_password_hash
import secrets
from typing import Optional
from .credentials import USERS


class AuthenticationManager:
    def __init__(self):
        # Charge la config des users depuis le fichier credentials.py
        self.users = USERS
        # Dict pour stocker les tokens de chaque user
        self.tokens = {}
        # Set pour garder la trace des tokens qui ne sont plus valides
        self.revoked_tokens = set()

    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        # Check si l'user existe et si son mot de passe est bon
        if username in self.users and check_password_hash(self.users[username], password):
            # On regarde si l'user a déjà un token, sinon on en fait un nouveau
            if username not in self.tokens:
                self.tokens[username] = secrets.token_urlsafe(32)
            return self.tokens[username]
        return None

    def verify_token(self, token: str) -> str:
        # Première vérif basique
        if not token:
            raise HTTPException(status_code=401, detail="Token manquant")

        # On check si le token a pas été révoqué avant
        if token in self.revoked_tokens:
            raise HTTPException(status_code=401, detail="Ce token a été révoqué")

        # On parcourt les tokens actifs pour trouver l'user correspondant
        for username, stored_token in self.tokens.items():
            if stored_token == token:
                return username

        raise HTTPException(status_code=401, detail="Token invalide")

    def revoke_token(self, token: str) -> None:
        # Check si le token existe quelque part dans nos tokens actifs
        if token not in [t for t in self.tokens.values()]:
            raise HTTPException(status_code=400, detail="Token invalide")

        # On blacklist le token
        self.revoked_tokens.add(token)

        # Faut aussi l'exclure des token actifs
        for username, stored_token in self.tokens.items():
            if stored_token == token:
                del self.tokens[username]
                break

    def generate_api_key(self, username: str) -> str:
        # On vérifie d'abord que l'user existe
        if username not in self.users:
            raise HTTPException(status_code=400, detail="Utilisateur invalide")
        return secrets.token_urlsafe(32)