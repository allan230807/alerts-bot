import json
import os

DB_FILE = "users.json"

def cargar_usuarios():
    """Carga la lista de usuarios desde el archivo JSON."""
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def registrar_usuario(chat_id):
    """Guarda un nuevo usuario si no existe en la base de datos."""
    usuarios = cargar_usuarios()
    if chat_id not in usuarios:
        usuarios.append(chat_id)
        with open(DB_FILE, "w") as f:
            json.dump(usuarios, f)
        return True # Usuario nuevo registrado
    return False # El usuario ya existía

def obtener_todos_los_usuarios():
    """Devuelve la lista completa de chat IDs."""
    return cargar_usuarios()