"""
Phoenyra EMS - User Database
SQLite-basierte Benutzerverwaltung
"""

import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)


class UserDatabase:
    """
    Benutzer-Datenbank für EMS
    
    Speichert:
    - Benutzer (username, email, password_hash, role, is_active)
    - Benutzer-Site-Zuordnungen (user_id, site_id, permission_level)
    """
    
    def __init__(self, db_path: str = "data/ems_users.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        logger.info(f"User database initialized: {self.db_path}")
    
    def _init_database(self):
        """Erstellt Datenbank-Schema"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    first_name TEXT,
                    last_name TEXT,
                    company TEXT,
                    phone TEXT,
                    email_verified INTEGER NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    last_login DATETIME
                )
            """)
            
            # Migration: Füge neue Spalten hinzu, falls sie nicht existieren
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN company TEXT")
            except sqlite3.OperationalError:
                pass  # Spalte existiert bereits
            
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
            except sqlite3.OperationalError:
                pass  # Spalte existiert bereits
            
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Spalte existiert bereits
            
            # User Sites Table (für Site-basierte Zugriffskontrolle)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    site_id INTEGER NOT NULL DEFAULT 1,
                    permission_level TEXT NOT NULL DEFAULT 'read',
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, site_id)
                )
            """)
            
            # Indices
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username 
                ON users(username)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_email 
                ON users(email)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_sites_user 
                ON user_sites(user_id)
            """)
            
            conn.commit()
    
    def create_user(self, username: str, password: str, email: Optional[str] = None,
                   role: str = 'viewer', first_name: Optional[str] = None,
                   last_name: Optional[str] = None, site_id: int = 1) -> Dict[str, Any]:
        """Erstellt neuen Benutzer"""
        
        password_hash = generate_password_hash(password)
        now = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO users 
                    (username, email, password_hash, role, is_active, 
                     first_name, last_name, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (username, email, password_hash, role, 1, 
                      first_name, last_name, now, now))
                
                user_id = cursor.lastrowid
                
                # Erstelle Site-Zuordnung
                cursor.execute("""
                    INSERT INTO user_sites (user_id, site_id, permission_level, created_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, site_id, 'admin' if role == 'admin' else 'read', now))
                
                conn.commit()
                
                return self.get_user_by_id(user_id)
            except sqlite3.IntegrityError as e:
                if 'username' in str(e):
                    raise ValueError(f"Benutzername '{username}' existiert bereits")
                elif 'email' in str(e):
                    raise ValueError(f"E-Mail '{email}' existiert bereits")
                raise
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Holt Benutzer nach Benutzername"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM users WHERE username = ?
            """, (username,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Holt Benutzer nach ID"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM users WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_user_by_username_or_email(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Holt Benutzer nach Benutzername oder E-Mail-Adresse"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM users WHERE username = ? OR email = ?
            """, (identifier, identifier))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def verify_password(self, identifier: str, password: str) -> bool:
        """Prüft Passwort (unterstützt sowohl Benutzername als auch E-Mail)"""
        
        user = self.get_user_by_username_or_email(identifier)
        if not user or not user.get('is_active'):
            return False
        
        return check_password_hash(user['password_hash'], password)
    
    def update_last_login(self, username: str):
        """Aktualisiert letzten Login-Zeitpunkt"""
        
        now = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users SET last_login = ? WHERE username = ?
            """, (now, username))
            
            conn.commit()
    
    def update_user(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Aktualisiert Benutzer"""
        
        allowed_fields = ['email', 'role', 'is_active', 'first_name', 'last_name', 'company', 'phone', 'email_verified']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return self.get_user_by_id(user_id)
        
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [user_id]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"""
                UPDATE users SET {set_clause} WHERE id = ?
            """, values)
            
            conn.commit()
        
        return self.get_user_by_id(user_id)
    
    def change_password(self, user_id: int, new_password: str):
        """Ändert Passwort"""
        
        password_hash = generate_password_hash(new_password)
        now = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users 
                SET password_hash = ?, updated_at = ? 
                WHERE id = ?
            """, (password_hash, now, user_id))
            
            conn.commit()
    
    def delete_user(self, user_id: int) -> bool:
        """Löscht Benutzer"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            
            return cursor.rowcount > 0
    
    def list_users(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Listet alle Benutzer"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if include_inactive:
                cursor.execute("SELECT * FROM users ORDER BY username")
            else:
                cursor.execute("SELECT * FROM users WHERE is_active = 1 ORDER BY username")
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def migrate_from_yaml(self, yaml_users: List[Dict[str, Any]]) -> int:
        """Migriert Benutzer aus YAML-Datei"""
        
        migrated = 0
        
        for user_data in yaml_users:
            username = user_data.get('username')
            if not username:
                continue
            
            # Prüfe ob Benutzer bereits existiert
            existing = self.get_user_by_username(username)
            if existing:
                logger.info(f"User {username} already exists, skipping migration")
                continue
            
            try:
                password = user_data.get('password', 'changeme123')
                role = user_data.get('role', 'viewer')
                email = user_data.get('email')
                
                self.create_user(
                    username=username,
                    password=password,
                    email=email,
                    role=role
                )
                migrated += 1
                logger.info(f"Migrated user: {username}")
            except Exception as e:
                logger.error(f"Failed to migrate user {username}: {e}")
        
        return migrated

