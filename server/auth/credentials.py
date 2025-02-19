from werkzeug.security import generate_password_hash

# Dictionnaire des credentials (utilisateurs et mots de passe hashés)
USERS = {
    "Tristan": generate_password_hash("Tristanmdp")
}

# Si besoin d'ajouter d'autres configurations liées aux credentials plus tard
TOKEN_EXPIRATION = 24  # heures