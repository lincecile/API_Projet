from fastapi import HTTPException
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
import secrets
import re
import logging
import html
from typing import Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from .models import Token
from .credentials import USERS


class AuthenticationManager:
    def __init__(self):
        self.token_expiration = timedelta(hours=1)
        self.login_attempts: Dict[str, Tuple[int, datetime]] = {}
        self.max_attempts = 5
        self.block_duration = timedelta(minutes=15)

        # Configuration du logging améliorée
        logging.basicConfig(
            filename='security.log',
            level=logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def _sanitize_input(self, value: str) -> str:
        """Nettoie les entrées pour prévenir XSS et injection SQL."""
        if not isinstance(value, str):
            return ""

        # Liste des motifs dangereux à supprimer
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # Balises script
            r'javascript:',  # Protocole javascript
            r'data:',  # Protocole data
            r'vbscript:',  # Protocole vbscript
            r'on\w+\s*=',  # Événements on*
            r'fetch\s*\(',  # Appels fetch
            r'eval\s*\(',  # Appels eval
            r'setTimeout\s*\(',  # setTimeout
            r'setInterval\s*\(',  # setInterval
            r'new\s+Function',  # Function constructor
            r'\[\s*][^\]]*\]',  # Array literals
            r'\{\s*}',  # Object literals
        ]

        # Conversion en string et échappement HTML initial
        sanitized = html.escape(str(value))

        # Suppression des motifs dangereux
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)

        # Retrait des caractères spéciaux dangereux
        sanitized = re.sub(r'[\'";`]', '', sanitized)

        # Suppression des mots-clés SQL dangereux
        sql_keywords = r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|AND|OR|WHERE|FROM|JOIN)\b'
        sanitized = re.sub(sql_keywords, '', sanitized, flags=re.IGNORECASE)

        return sanitized

    def authenticate_user(self, username: str, password: str, ip: str, db: Session) -> Optional[str]:
        """Authentifie un utilisateur et retourne un token."""
        try:
            # Validation initiale
            self._validate_credentials(username, password)
            self._check_rate_limit(ip)

            # Clean input
            username = self._sanitize_input(username)

            # Vérification du password avec protection timing attack
            valid_password = False
            if username in USERS:
                try:
                    valid_password = check_password_hash(USERS[username], password)
                except Exception:
                    self._log_security_event("PASSWORD_CHECK_ERROR", username, ip)
                    raise HTTPException(status_code=500, detail="Erreur serveur")

            secrets.compare_digest('dummy', 'dummy')

            if not valid_password:
                self._log_security_event("LOGIN_FAILED", username, ip)
                raise HTTPException(status_code=401, detail="Identifiants invalides")

            token_str = None
            try:
                self._revoke_old_tokens(username, db)
                token_str = secrets.token_urlsafe(32)

                token = Token(
                    token=token_str,
                    username=username,
                    expires_at=datetime.utcnow() + self.token_expiration
                )

                db.add(token)
                db.commit()

            except SQLAlchemyError as e:
                db.rollback()
                self._log_security_event("DB_ERROR", username, ip)
                raise HTTPException(status_code=500, detail="Erreur serveur")

            self._log_security_event("LOGIN_SUCCESS", username, ip)
            return token_str

        except HTTPException as he:
            raise he
        except Exception as e:
            self._log_security_event("SYSTEM_ERROR", username, ip)
            raise HTTPException(status_code=500, detail="Erreur système")

    def _validate_credentials(self, username: str, password: str) -> None:
        """Valide et nettoie les credentials."""
        if not username or not password or not isinstance(username, str) or not isinstance(password, str):
            raise HTTPException(status_code=400, detail="Username et password requis")

        # Vérifie la longueur
        if len(username) > 100 or len(password) > 100:
            raise HTTPException(status_code=400, detail="Username ou password trop long")

        # Vérifie les caractères autorisés
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise HTTPException(status_code=400, detail="Username contient des caractères non autorisés")

    def verify_token(self, token: str, db: Session) -> str:
        """Vérifie si le token est valide."""
        if not token or not isinstance(token, str):
            raise HTTPException(status_code=401, detail="Token invalide")

        token = self._sanitize_input(token)

        try:
            db_token = db.query(Token).filter(Token.token == token).first()

            if not db_token:
                raise HTTPException(status_code=401, detail="Token invalide")

            if db_token.is_revoked:
                raise HTTPException(status_code=401, detail="Token révoqué")

            if db_token.expires_at < datetime.utcnow():
                raise HTTPException(status_code=401, detail="Token expiré")

            return db_token.username

        except SQLAlchemyError:
            self._log_security_event("DB_ERROR", "", "")
            raise HTTPException(status_code=500, detail="Erreur serveur")
        except HTTPException:
            raise
        except Exception:
            self._log_security_event("TOKEN_VERIFICATION_ERROR", "", "")
            raise HTTPException(status_code=500, detail="Erreur serveur")

    def _check_rate_limit(self, ip: str) -> None:
        """Vérifie le rate limiting."""
        now = datetime.utcnow()

        if ip in self.login_attempts:
            attempts, last_attempt = self.login_attempts[ip]

            if now - last_attempt > self.block_duration:
                self.login_attempts[ip] = (1, now)
                return

            if attempts >= self.max_attempts:
                wait_minutes = (self.block_duration - (now - last_attempt)).seconds // 60
                raise HTTPException(
                    status_code=429,
                    detail=f"Trop de tentatives. Réessayez dans {wait_minutes} minutes"
                )

            self.login_attempts[ip] = (attempts + 1, now)
        else:
            self.login_attempts[ip] = (1, now)

    def _log_security_event(self, event_type: str, username: str, ip: str) -> None:
        """Log les événements de sécurité."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "username": self._sanitize_input(username),
            "ip": self._sanitize_input(ip)
        }
        logging.warning(str(log_data))

    def _revoke_old_tokens(self, username: str, db: Session) -> None:
        """Révoque les anciens tokens."""
        try:
            db.query(Token).filter(
                (Token.username == username) |
                (Token.expires_at < datetime.utcnow())
            ).delete()
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            self._log_security_event("TOKEN_REVOCATION_ERROR", username, "")
            raise HTTPException(status_code=500, detail="Erreur lors de la révocation des tokens")