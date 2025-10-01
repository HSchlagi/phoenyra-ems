from flask import Flask
from .routes import bp
import yaml, os
from pathlib import Path
from ems.controller import EmsCore

def create_app():
    app=Flask(__name__); app.secret_key=os.environ.get('FLASK_SECRET','dev')
    @app.after_request
    def csp(r): 
        r.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; img-src 'self' data:; font-src 'self' data: https://cdnjs.cloudflare.com; connect-src 'self';"
        return r
    cfg=yaml.safe_load(open(Path(__file__).resolve().parents[1]/'config'/'ems.yaml'))
    users=yaml.safe_load(open(Path(__file__).resolve().parents[1]/'config'/'users.yaml'))
    app.ems=EmsCore(cfg); app.ems.start(); app.users=users.get('users',[])
    app.register_blueprint(bp); return app
app=create_app()
