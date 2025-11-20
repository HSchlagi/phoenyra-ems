from flask import Flask, jsonify, request
from .routes import bp
import yaml, os
from pathlib import Path
from ems.controller import EmsCore
from ems.multi_site_manager import MultiSiteManager
from services.database.user_db import UserDatabase

def create_app():
    app=Flask(__name__); app.secret_key=os.environ.get('FLASK_SECRET','dev')
    # Template-Reloading aktivieren (auch im Production-Modus für Development)
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    @app.after_request
    def csp(r): 
        r.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://cdnjs.cloudflare.com https://cdn.plot.ly; style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; img-src 'self' data:; font-src 'self' data: https://cdnjs.cloudflare.com; connect-src 'self';"
        return r
    
    @app.errorhandler(403)
    def handle_403(e):
        """Return JSON for API endpoints, HTML redirect for others"""
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Forbidden: Insufficient permissions'}), 403
        from flask import redirect, url_for
        return redirect(url_for('web.login'))
    
    cfg=yaml.safe_load(open(Path(__file__).resolve().parents[1]/'config'/'ems.yaml'))
    
    # User Database initialisieren
    user_db_path = cfg.get('database', {}).get('user_db_path', 'data/ems_users.db')
    app.user_db = UserDatabase(user_db_path)
    
    # Migration von YAML zu Datenbank (falls noch nicht geschehen)
    try:
        users_yaml = yaml.safe_load(open(Path(__file__).resolve().parents[1]/'config'/'users.yaml'))
        yaml_users = users_yaml.get('users', [])
        if yaml_users:
            migrated = app.user_db.migrate_from_yaml(yaml_users)
            if migrated > 0:
                print(f"✅ {migrated} Benutzer aus YAML migriert")
    except Exception as e:
        print(f"⚠️ YAML-Migration fehlgeschlagen: {e}")
    
    # Rückwärtskompatibilität: Falls DB leer, verwende YAML
    db_users = app.user_db.list_users(include_inactive=True)
    if not db_users:
        users_yaml = yaml.safe_load(open(Path(__file__).resolve().parents[1]/'config'/'users.yaml'))
        app.users = users_yaml.get('users', [])
    else:
        # Konvertiere DB-Users zu YAML-Format für Kompatibilität
        app.users = [{'username': u['username'], 'password': '***', 'role': u['role']} for u in db_users]
    
    # Multi-Site oder Single-Site Modus?
    sites_config = cfg.get('sites', {})
    if sites_config and 'sites' in sites_config and sites_config.get('sites'):
        # Multi-Site-Modus
        try:
            app.ems = MultiSiteManager(sites_config)
            app.multi_site = True
            print(f"✅ Multi-Site-Modus aktiviert: {len(app.ems.sites)} Standorte")
        except Exception as e:
            print(f"❌ Fehler beim Initialisieren von Multi-Site: {e}")
            print("⚠️ Fallback auf Single-Site-Modus")
            app.ems = EmsCore(cfg)
            app.ems.start()
            app.multi_site = False
    else:
        # Single-Site-Modus (Rückwärtskompatibilität)
        app.ems = EmsCore(cfg)
        app.ems.start()
        app.multi_site = False
        print("✅ Single-Site-Modus aktiviert")
    
    # Context-Processor: current_app und multi_site für Templates verfügbar machen
    @app.context_processor
    def inject_current_app():
        return {
            'current_app': app,
            'multi_site': app.multi_site if hasattr(app, 'multi_site') else False
        }
    
    app.register_blueprint(bp); return app
app=create_app()
