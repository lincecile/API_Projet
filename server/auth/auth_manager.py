from datetime import datetime, timedelta
import jwt
import secrets
from typing import Optional, Dict
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


class AuthenticationManager:
    def __init__(self):
        # Clé secrète pour signer les tokens JWT (à stocker de manière sécurisée en production)
        self.secret_key = "your-secret-key-here"
        # Durée de validité des tokens (24 heures par défaut)
        self.token_expiration = timedelta(hours=24)
        # Stockage des tokens révoqués (à remplacer par une base de données en production)
        self.revoked_tokens = set()
        # Stockage des API keys (à remplacer par une base de données en production)
        self.api_keys: Dict[str, str] = {}
        # Sécurité pour la vérification du token bearer
        self.security = HTTPBearer()

    def create_token(self, user_id: str) -> str:
        """
        Crée un nouveau token JWT pour un utilisateur.

        Args:
            user_id: Identifiant unique de l'utilisateur

        Returns:
            Le token JWT généré
        """
        expiration = datetime.utcnow() + self.token_expiration
        token_data = {
            "sub": user_id,
            "exp": expiration,
            "iat": datetime.utcnow()
        }
        token = jwt.encode(token_data, self.secret_key, algorithm="HS256")
        return token

    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())) -> str:
        """
        Vérifie la validité d'un token JWT.

        Args:
            credentials: Les credentials contenant le token

        Returns:
            L'ID de l'utilisateur si le token est valide

        Raises:
            HTTPException: Si le token est invalide ou révoqué
        """
        try:
            token = credentials.credentials
            if token in self.revoked_tokens:
                raise HTTPException(
                    status_code=401,
                    detail="Token has been revoked"
                )

            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            user_id = payload.get("sub")

            if not user_id:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token payload"
                )

            return user_id

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    def revoke_token(self, token: str) -> None:
        """
        Révoque un token JWT.

        Args:
            token: Le token à révoquer
        """
        self.revoked_tokens.add(token)

    def generate_api_key(self, user_id: str) -> str:
        """
        Génère une nouvelle API key pour un utilisateur.

        Args:
            user_id: Identifiant unique de l'utilisateur

        Returns:
            La nouvelle API key générée
        """
        api_key = secrets.token_urlsafe(32)
        self.api_keys[api_key] = user_id
        return api_key

    def verify_api_key(self, api_key: str) -> Optional[str]:
        """
        Vérifie la validité d'une API key.

        Args:
            api_key: L'API key à vérifier

        Returns:
            L'ID de l'utilisateur associé à l'API key si elle est valide, None sinon
        """
        return self.api_keys.get(api_key)

    def list_user_tokens(self, user_id: str) -> list:
        """
        Liste tous les tokens actifs d'un utilisateur.

        Args:
            user_id: Identifiant unique de l'utilisateur

        Returns:
            Liste des tokens actifs
        """
        active_tokens = []
        current_time = datetime.utcnow()

        # Pour chaque token, on vérifie s'il n'est pas révoqué et s'il appartient à l'utilisateur
        for token in [t for t in self.get_all_tokens() if t not in self.revoked_tokens]:
            try:
                payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
                token_expiration = datetime.fromtimestamp(payload["exp"])
                if (payload["sub"] == user_id and
                        token not in self.revoked_tokens and
                        token_expiration > current_time):
                    active_tokens.append(token)
            except jwt.InvalidTokenError:
                continue

        return active_tokens
"""
    def get_all_tokens(self) -> list:
        
        Méthode utilitaire pour obtenir tous les tokens.
        En production, ceci devrait être remplacé par une requête à la base de données.

        Returns:
            Liste de tous les tokens
        
        return []  
"""