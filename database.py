# database.py

import sqlite3
import json
from pathlib import Path
from config import DB_FILENAME, SCHEMA_FILENAME

class Database:
    """
    🗄️ Clase para gestionar la base de datos SQLite de LeoMatch.
    Incluye creación de tablas, CRUD de usuarios, likes/matches y promo toggles.
    """

    def __init__(self, db_path: Path = None, schema_path: Path = None):
        """
        🚀 Inicializa conexión y crea tablas si no existen.
        - db_path: ruta al archivo SQLite (por defecto, DB_FILENAME junto a este archivo)
        - schema_path: ruta al .sql con la estructura (por defecto, SCHEMA_FILENAME junto a este archivo)
        """
        base = Path(__file__).parent
        self.db_path = db_path or (base / DB_FILENAME)
        self.schema_path = schema_path or (base / SCHEMA_FILENAME)

        # Conectar y asegurar que las tablas existan
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """📚 Ejecuta el SQL de SCHEMA_FILENAME para crear la estructura."""
        with open(self.schema_path, "r", encoding="utf-8") as f:
            script = f.read()
        self.conn.executescript(script)
        self.conn.commit()

    def add_user(self, telegram_id: int, name: str):
        """
        📥 Inserta un usuario nuevo si no existe.
        - telegram_id: ID único de Telegram
        - name: nombre o apodo
        """
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO users (telegram_id, name) VALUES (?, ?)",
            (telegram_id, name)
        )
        self.conn.commit()

    def get_user(self, telegram_id: int) -> dict:
        """
        🔍 Recupera todos los datos de un usuario por su telegram_id.
        Devuelve un dict con los campos o None si no existe.
        """
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def update_user(self, telegram_id: int, **fields):
        """
        ✏️ Actualiza campos arbitrarios de un usuario.
        Uso: update_user(12345, age=30, bio='Hola!')
        """
        if not fields:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [telegram_id]
        self.conn.execute(f"UPDATE users SET {cols} WHERE telegram_id = ?", vals)
        self.conn.commit()

    def like_user(self, user_id: int, target_id: int):
        """
        ❤️ Registra un “like” de user_id a target_id.
        Si target_id ya te había dado like, crea match.
        """
        me = self.get_user(user_id)
        likes = json.loads(me["liked_users"])
        if target_id not in likes:
            likes.append(target_id)
            self.update_user(user_id, liked_users=json.dumps(likes))

        other = self.get_user(target_id)
        other_likes = json.loads(other["liked_users"])
        if user_id in other_likes:
            self._add_match(user_id, target_id)

    def _add_match(self, u1: int, u2: int):
        """
        🤝 Registra el match mutuo entre u1 y u2.
        Añade en matched_users de ambos.
        """
        for a, b in ((u1, u2), (u2, u1)):
            usr = self.get_user(a)
            matches = json.loads(usr["matched_users"])
            if b not in matches:
                matches.append(b)
                self.update_user(a, matched_users=json.dumps(matches))

    def toggle_promo(self, telegram_id: int, state: bool):
        """
        🔔 Activa (state=True) o desactiva (state=False) recepción de promociones.
        Solo usuarios premium pueden desactivar.
        """
        self.update_user(telegram_id, receive_promos=1 if state else 0)

    def set_premium(self, telegram_id: int, is_premium: bool):
        """
        💎 Marca al usuario como premium (True) o gratuito (False).
        """
        self.update_user(telegram_id, is_premium=1 if is_premium else 0)
