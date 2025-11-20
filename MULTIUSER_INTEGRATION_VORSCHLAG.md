# Multiuser-Integration für Phoenyra EMS

## Übersicht

Erweiterung des EMS-Systems um eine vollständige Multiuser-Funktionalität mit:
- Datenbank-basierte Benutzerverwaltung (SQLite)
- Rollen und Berechtigungen
- Benutzerverwaltung über UI
- Optional: Site/Anlagen-basierte Zugriffskontrolle

## Implementierungsplan

### Phase 1: Datenbank-Modell
- `users` Tabelle: username, email, password_hash, role, is_active, created_at
- `user_sites` Tabelle: user_id, site_id, permission_level (read/write/admin)
- Migration von `users.yaml` zu Datenbank

### Phase 2: Authentifizierung erweitern
- Passwort-Hashing (werkzeug.security)
- Session-Management verbessern
- Login/Logout/Registrierung

### Phase 3: UI für Benutzerverwaltung
- Benutzerliste in Settings
- Benutzer hinzufügen/bearbeiten/löschen
- Rollen zuweisen
- Passwort zurücksetzen

### Phase 4: Berechtigungen
- Site-basierte Zugriffskontrolle (optional)
- API-Endpunkte mit Berechtigungsprüfung
- UI-Elemente basierend auf Rollen

## Vorteile gegenüber Supabase
- ✅ Keine externe Abhängigkeit
- ✅ Lokale Datenhaltung
- ✅ Einfache Integration in bestehendes System
- ✅ Konsistent mit History-DB (SQLite)

## Migration
- Bestehende `users.yaml` wird automatisch in Datenbank importiert
- Rückwärtskompatibel: Falls DB nicht existiert, verwendet YAML

