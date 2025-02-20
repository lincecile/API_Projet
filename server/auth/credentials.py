from werkzeug.security import generate_password_hash

# Dictionnaire des credentials (utilisateurs et mots de passe hashés)
# Dictionnaire des credentials avec des mots de passe cryptés
USERS = {
    "Tristan": "scrypt:32768:8:1$3gkJm6mo11zxtkof$3a1ce3a2849661d4de744620688f2f504e741851357655a5929941543637b36e90f1309d9b5c790f699713597f79d8609df751d9e77449c30f938ade268a67a7"
}

# Hash de "Tristan"


TOKEN_EXPIRATION = 24  # heures