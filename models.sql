-- models.sql
-- PRAGMA para asegurar integridad referencial
PRAGMA foreign_keys = ON;

-- 🗄️ Tabla de usuarios para LeoMatch
-- Campos:
-- id              -> clave primaria autoincremental
-- telegram_id     -> ID único de Telegram del usuario
-- name            -> nombre o apodo
-- age             -> edad
-- gender          -> género (hombre, mujer, otro)
-- looking_for     -> preferencia de emparejamiento ('todos' para free, 'hombres'/'mujeres' para premium)
-- bio             -> presentación breve
-- photo           -> file_id de la foto de perfil
-- location        -> ciudad o país
-- is_premium      -> 0 = free, 1 = premium
-- receive_promos  -> 1 = acepta promociones, 0 = no (solo premium puede cambiar)
-- liked_users     -> JSON array con IDs a los que dio “me gusta”
-- matched_users   -> JSON array con IDs con los que hizo match

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    gender TEXT NOT NULL,
    looking_for TEXT NOT NULL DEFAULT 'todos',
    bio TEXT,
    photo TEXT,
    location TEXT,
    is_premium INTEGER NOT NULL DEFAULT 0,
    receive_promos INTEGER NOT NULL DEFAULT 1,
    liked_users TEXT NOT NULL DEFAULT '[]',
    matched_users TEXT NOT NULL DEFAULT '[]'
);
