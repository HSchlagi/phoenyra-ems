"""
Phoenyra EMS - Web Routes
Flask Blueprint mit allen Web- und API-Endpunkten
"""

from flask import Blueprint, render_template, jsonify, request, current_app, Response, redirect, url_for, session, send_from_directory
from auth.security import login_required, role_required
import json
import logging
import yaml
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from config import list_profiles, get_profile
from services.communication import ModbusConfig, ModbusClient

logger = logging.getLogger(__name__)

bp = Blueprint('web', __name__)

def load_config():
    """Load EMS configuration"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'ems.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_config(config):
    """Save EMS configuration"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'ems.yaml')
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

def get_site_config(config: Dict[str, Any], site_id: Optional[int] = None) -> Dict[str, Any]:
    """Get site-specific configuration or global config if site_id is None"""
    if site_id is None:
        return config
    
    sites_config = config.get('sites', {})
    if not sites_config:
        return config
    
    # Prüfe ob es die verschachtelte Struktur ist: sites.sites.{site_id}
    if isinstance(sites_config, dict) and 'sites' in sites_config:
        sites_dict = sites_config.get('sites', {})
        # Prüfe ob site_id als int oder str Key existiert
        if isinstance(sites_dict, dict):
            if site_id in sites_dict:
                return sites_dict[site_id]
            elif str(site_id) in sites_dict:
                return sites_dict[str(site_id)]
    
    # Wenn sites direkt ein Dict mit site_id als Keys ist (alte Struktur)
    if isinstance(sites_config, dict) and site_id in sites_config:
        return sites_config[site_id]
    elif isinstance(sites_config, dict) and str(site_id) in sites_config:
        return sites_config[str(site_id)]
    
    # Wenn sites eine Liste ist (z.B. aus YAML)
    if isinstance(sites_config, list):
        for site in sites_config:
            if site.get('id') == site_id:
                return site
    
    # Fallback: globale Config
    return config

def set_site_config(config: Dict[str, Any], site_id: Optional[int], section: str, value: Any):
    """Set site-specific configuration"""
    if site_id is None:
        config[section] = value
        return
    
    # Stelle sicher, dass 'sites' existiert
    if 'sites' not in config:
        config['sites'] = {'sites': {}, 'default_site_id': 1}
    
    sites_config = config['sites']
    
    # Prüfe ob es die verschachtelte Struktur ist: sites.sites.{site_id}
    if isinstance(sites_config, dict) and 'sites' in sites_config:
        sites_dict = sites_config.get('sites', {})
        # Stelle sicher, dass site_id existiert
        site_key = site_id if site_id in sites_dict else str(site_id) if str(site_id) in sites_dict else None
        if site_key is None:
            # Erstelle neuen Standort mit Standard-Konfiguration
            sites_dict[site_id] = {}
        else:
            site_id = int(site_key) if isinstance(site_key, str) else site_key
        
        if site_id not in sites_dict:
            sites_dict[site_id] = {}
        if str(site_id) not in sites_dict:
            sites_dict[str(site_id)] = sites_dict.get(site_id, {})
        
        # Verwende int-Key für Konsistenz
        if site_id not in sites_dict:
            sites_dict[site_id] = {}
        sites_dict[site_id][section] = value
        sites_dict[str(site_id)] = sites_dict[site_id]  # Auch als String-Key speichern für YAML-Kompatibilität
    # Wenn sites direkt ein Dict mit site_id als Keys ist (alte Struktur)
    elif isinstance(sites_config, dict):
        if site_id not in sites_config:
            sites_config[site_id] = {}
        sites_config[site_id][section] = value
    # Wenn sites eine Liste ist
    elif isinstance(sites_config, list):
        site_found = False
        for site in sites_config:
            if site.get('id') == site_id:
                site[section] = value
                site_found = True
                break
        if not site_found:
            sites_config.append({'id': site_id, section: value})


# ============================================================================
# Authentication Routes
# ============================================================================

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login-Seite"""
    if request.method == 'POST':
        u = request.form.get('username', '')
        p = request.form.get('password', '')
        
        # Versuche zuerst Datenbank-Authentifizierung
        if hasattr(current_app, 'user_db'):
            if current_app.user_db.verify_password(u, p):
                user = current_app.user_db.get_user_by_username_or_email(u)
                if user:
                    current_app.user_db.update_last_login(user['username'])
                    session['user'] = {
                        'name': user['username'],
                        'id': user['id'],
                        'role': user.get('role', 'viewer'),
                        'email': user.get('email')
                    }
                    logger.info(f"User logged in (DB): {user['username']} (via: {u})")
                    return redirect(request.args.get('next') or url_for('web.dashboard'))
        
        # Fallback: YAML-Authentifizierung (Rückwärtskompatibilität)
        for usr in current_app.users:
            if usr.get('username') == u and usr.get('password') == p:
                session['user'] = {
                    'name': u,
                    'role': usr.get('role', 'viewer')
                }
                logger.info(f"User logged in (YAML): {u}")
                return redirect(request.args.get('next') or url_for('web.dashboard'))
        
        logger.warning(f"Failed login attempt for user: {u}")
        return render_template('login.html', error='Ungültige Anmeldedaten')
    
    return render_template('login.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registrierungs-Seite"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        email = request.form.get('email', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        
        # Validierung
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Benutzername muss mindestens 3 Zeichen lang sein')
        
        if not password or len(password) < 6:
            errors.append('Passwort muss mindestens 6 Zeichen lang sein')
        
        if password != password_confirm:
            errors.append('Passwörter stimmen nicht überein')
        
        if email and '@' not in email:
            errors.append('Ungültige E-Mail-Adresse')
        
        # Prüfe ob Benutzername bereits existiert
        if hasattr(current_app, 'user_db'):
            existing = current_app.user_db.get_user_by_username(username)
            if existing:
                errors.append('Benutzername existiert bereits')
        
        if errors:
            return render_template('register.html', errors=errors, 
                                 username=username, email=email, 
                                 first_name=first_name, last_name=last_name)
        
        # Erstelle neuen Benutzer (Standard-Rolle: viewer)
        try:
            if hasattr(current_app, 'user_db'):
                user = current_app.user_db.create_user(
                    username=username,
                    password=password,
                    email=email if email else None,
                    role='viewer',  # Neue Benutzer erhalten Standard-Rolle
                    first_name=first_name if first_name else None,
                    last_name=last_name if last_name else None
                )
                
                logger.info(f"New user registered: {username}")
                
                # Automatisch einloggen nach Registrierung
                session['user'] = {
                    'name': username,
                    'id': user['id'],
                    'role': user.get('role', 'viewer'),
                    'email': user.get('email')
                }
                
                return redirect(url_for('web.dashboard'))
            else:
                return render_template('register.html', 
                                     errors=['Registrierung momentan nicht verfügbar'])
        except ValueError as e:
            return render_template('register.html', errors=[str(e)],
                                 username=username, email=email,
                                 first_name=first_name, last_name=last_name)
        except Exception as e:
            logger.error(f"Error during registration: {e}")
            return render_template('register.html', 
                                 errors=['Fehler bei der Registrierung. Bitte versuchen Sie es erneut.'],
                                 username=username, email=email,
                                 first_name=first_name, last_name=last_name)
    
    return render_template('register.html')


@bp.route('/logout')
def logout():
    """Logout"""
    user = session.get('user', {}).get('name', 'unknown')
    session.pop('user', None)
    logger.info(f"User logged out: {user}")
    return redirect(url_for('web.login'))


# ============================================================================
# Web Pages
# ============================================================================

@bp.route('/')
@login_required
def dashboard():
    """Haupt-Dashboard"""
    multi_site = hasattr(current_app, 'multi_site') and current_app.multi_site
    return render_template('dashboard.html', multi_site=multi_site)


@bp.route('/analytics')
@login_required
def analytics():
    """Analytics & Performance Dashboard"""
    multi_site = hasattr(current_app, 'multi_site') and current_app.multi_site
    return render_template('analytics.html', multi_site=multi_site)


@bp.route('/settings')
@login_required
def settings():
    """System Settings & Configuration"""
    multi_site = hasattr(current_app, 'multi_site') and current_app.multi_site
    return render_template('settings.html', multi_site=multi_site)


@bp.route('/forecasts')
@login_required
def forecasts():
    """Forecasts & Market Data"""
    multi_site = hasattr(current_app, 'multi_site') and current_app.multi_site
    return render_template('forecasts.html', multi_site=multi_site)


@bp.route('/users')
@login_required
@role_required('admin')
def users():
    """Benutzerverwaltung (nur für Admins)"""
    multi_site = hasattr(current_app, 'multi_site') and current_app.multi_site
    return render_template('users.html', multi_site=multi_site)


@bp.route('/help')
@login_required
def help():
    """Hilfe & Anleitungen"""
    multi_site = hasattr(current_app, 'multi_site') and current_app.multi_site
    return render_template('help.html', multi_site=multi_site)


@bp.route('/monitoring')
@login_required
def monitoring():
    """Live Monitoring & Telemetrie"""
    multi_site = hasattr(current_app, 'multi_site') and current_app.multi_site
    return render_template('monitoring.html', multi_site=multi_site)


@bp.route('/sites')
@login_required
def sites():
    """Multi-Site-Übersicht (nur wenn Multi-Site aktiviert)"""
    multi_site = hasattr(current_app, 'multi_site') and current_app.multi_site
    if not multi_site:
        return redirect(url_for('web.dashboard'))
    # Debug: Prüfe Session
    user_info = session.get('user', {})
    user_role = user_info.get('role', 'unknown')
    logger.info(f"User in sites route: {user_info}, role: {user_role}")
    return render_template('sites.html', multi_site=multi_site, user_role=user_role, user_info=user_info)


@bp.route('/mqtt-test')
@login_required
def mqtt_test():
    """MQTT Topic Configuration Test Page"""
    return render_template('mqtt_test.html')


# ============================================================================
# API - State & Real-time
# ============================================================================

def get_ems_for_site(site_id: int = None):
    """
    Helper-Funktion: Gibt EmsCore für einen Standort zurück
    Unterstützt sowohl Single-Site als auch Multi-Site-Modus
    """
    if not hasattr(current_app, 'ems') or current_app.ems is None:
        return None
    
    if hasattr(current_app, 'multi_site') and current_app.multi_site:
        # Multi-Site-Modus
        if site_id is None:
            if hasattr(current_app.ems, 'default_site_id'):
                site_id = current_app.ems.default_site_id
            else:
                return None
        if hasattr(current_app.ems, 'get_site'):
            return current_app.ems.get_site(site_id)
        return None
    else:
        # Single-Site-Modus
        return current_app.ems


@bp.route('/api/state')
@login_required
def api_state():
    """Gibt aktuellen Anlagenzustand zurück"""
    site_id = request.args.get('site_id', type=int)
    ems = get_ems_for_site(site_id)
    if ems:
        return jsonify(ems.to_dict())
    return jsonify({'error': 'Site not found'}), 404


@bp.route('/api/monitoring/telemetry')
@login_required
def api_monitoring_telemetry():
    """Gibt Telemetrieverlauf zurück"""
    site_id = request.args.get('site_id', type=int)
    minutes = request.args.get('minutes', 60, type=int)
    limit = request.args.get('limit', 900, type=int)
    
    ems = get_ems_for_site(site_id)
    if not ems:
        return jsonify({'error': 'Site not found'}), 404
    
    telemetry = ems.get_recent_telemetry(minutes=minutes, limit=limit)
    current_state = ems.to_dict()
    
    return jsonify({
        'data': telemetry,
        'current': current_state
    })


@bp.route('/api/monitoring/powerflow')
@login_required
def api_monitoring_powerflow():
    """Aggregierte Energieflüsse für Sankey-Diagramm"""
    site_id = request.args.get('site_id', type=int)
    minutes = request.args.get('minutes', 5, type=int)
    
    ems = get_ems_for_site(site_id)
    if not ems:
        return jsonify({'error': 'Site not found'}), 404
    
    power_flow = ems.get_power_flow(minutes=max(1, minutes))
    return jsonify(power_flow)


@bp.route('/api/events')
@login_required
def sse():
    """Server-Sent Events für Live-Updates"""
    q = current_app.ems.sse_register()
    
    def stream():
        try:
            while True:
                data = q.get()
                yield f"data: {json.dumps(data)}\n\n"
        finally:
            current_app.ems.sse_unregister(q)
    
    return Response(stream(), mimetype='text/event-stream')


# ============================================================================
# API - Optimization & Strategy
# ============================================================================

@bp.route('/api/plan')
@login_required
def api_plan():
    """Gibt aktuellen Optimierungsplan zurück"""
    site_id = request.args.get('site_id', type=int)
    ems = get_ems_for_site(site_id)
    if not ems:
        return jsonify({'error': 'Site not found'}), 404
    
    plan = ems.get_current_plan()
    
    if plan:
        return jsonify(plan)
    else:
        return jsonify({'error': 'No plan available'}), 404


@bp.route('/api/strategies')
@login_required
def api_strategies():
    """Gibt verfügbare Strategien zurück"""
    site_id = request.args.get('site_id', type=int)
    ems = get_ems_for_site(site_id)
    if not ems:
        return jsonify({'error': 'Site not found'}), 404
    
    strategies = ems.strategy_manager.get_available_strategies()
    current = ems.strategy_manager.get_current_strategy()
    
    return jsonify({
        'available': strategies,
        'current': current,
        'mode': ems.strategy_manager.selection_mode,
        'site_id': site_id
    })


@bp.route('/api/strategy', methods=['POST'])
@login_required
@role_required('admin')
def api_set_strategy():
    """Setzt manuelle Strategie"""
    data = request.get_json()
    strategy_name = data.get('strategy')
    site_id = data.get('site_id')
    
    if not strategy_name:
        return jsonify({'error': 'Missing strategy parameter'}), 400
    
    ems = get_ems_for_site(site_id)
    if not ems:
        return jsonify({'error': 'Site not found'}), 404
    
    success = ems.set_manual_strategy(strategy_name)
    
    if success:
        logger.info(f"Strategy manually set to: {strategy_name} for site {site_id}")
        return jsonify({'success': True, 'strategy': strategy_name, 'site_id': site_id})
    else:
        return jsonify({'error': 'Unknown strategy'}), 400


@bp.route('/api/strategy/auto', methods=['POST'])
@login_required
@role_required('admin')
def api_auto_strategy():
    """Aktiviert automatische Strategiewahl"""
    data = request.get_json() or {}
    site_id = data.get('site_id')
    
    ems = get_ems_for_site(site_id)
    if not ems:
        return jsonify({'error': 'Site not found'}), 404
    
    ems.strategy_manager.set_auto_mode()
    logger.info(f"Auto strategy mode activated for site {site_id}")
    return jsonify({'success': True, 'mode': 'auto', 'site_id': site_id})


# ============================================================================
# API - AI Strategy Selection
# ============================================================================

@bp.route('/api/ai/status')
@login_required
def api_ai_status():
    """Gibt AI-Status zurück"""
    try:
        site_id = request.args.get('site_id', type=int)
        
        # Prüfe ob EMS verfügbar ist
        if not hasattr(current_app, 'ems') or current_app.ems is None:
            return jsonify({
                'enabled': False,
                'is_trained': False,
                'training_samples': 0,
                'error': 'EMS not initialized'
            })
        
        ems = get_ems_for_site(site_id)
        if not ems:
            return jsonify({
                'enabled': False,
                'is_trained': False,
                'training_samples': 0,
                'error': 'Site not found'
            })
        
        # Prüfe ob strategy_manager existiert
        if not hasattr(ems, 'strategy_manager') or ems.strategy_manager is None:
            return jsonify({
                'enabled': False,
                'is_trained': False,
                'training_samples': 0
            })
        
        ai_selector = ems.strategy_manager.ai_selector if hasattr(ems.strategy_manager, 'ai_selector') else None
        
        # Lade Config direkt (ohne load_config() Helper)
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'ems.yaml')
        enabled = False
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            ai_config = config.get('strategies', {}).get('ai_selection', {})
            enabled = ai_config.get('enabled', False)
        except Exception as e:
            logger.warning(f"Could not load AI config: {e}")
        
        # Zähle Trainingsdaten
        training_samples = 0
        if hasattr(ems, 'history_db') and ems.history_db:
            try:
                opt_history = ems.history_db.get_optimization_history(days=30)
                training_samples = len(opt_history) if opt_history else 0
            except Exception as e:
                logger.warning(f"Could not count training samples: {e}")
        
        return jsonify({
            'enabled': enabled,
            'is_trained': ai_selector.is_trained if ai_selector and hasattr(ai_selector, 'is_trained') else False,
            'training_samples': training_samples
        })
    except Exception as e:
        logger.error(f"Error in api_ai_status: {e}", exc_info=True)
        return jsonify({
            'enabled': False,
            'is_trained': False,
            'training_samples': 0,
            'error': str(e)
        }), 500


@bp.route('/api/ai/config', methods=['POST'])
@login_required
@role_required('admin')
def api_ai_config():
    """Aktiviert/deaktiviert AI-Strategie-Auswahl"""
    try:
        data = request.get_json() or {}
        enabled = data.get('enabled', False)
        site_id = data.get('site_id')
        
        # Verwende current_app.config_path falls verfügbar, sonst Standard-Pfad
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'ems.yaml')
        
        # Prüfe ob Config-Datei existiert
        if not os.path.exists(config_path):
            logger.error(f"Config file not found: {config_path}")
            return jsonify({'success': False, 'error': 'Config file not found'}), 500
        
        # Lade Config
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error reading config file: {e}")
            return jsonify({'success': False, 'error': f'Error reading config: {str(e)}'}), 500
        
        # Update Config
        if 'strategies' not in config:
            config['strategies'] = {}
        if 'ai_selection' not in config['strategies']:
            config['strategies']['ai_selection'] = {}
        
        config['strategies']['ai_selection']['enabled'] = enabled
        
        # Speichere Config
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            logger.error(f"Error writing config file: {e}")
            return jsonify({'success': False, 'error': f'Error saving config: {str(e)}'}), 500
        
        logger.info(f"AI selection {'enabled' if enabled else 'disabled'} for site {site_id}")
        return jsonify({
            'success': True, 
            'enabled': enabled
        })
    except Exception as e:
        logger.error(f"Error updating AI config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/ai/train', methods=['POST'])
@login_required
@role_required('admin')
def api_ai_train():
    """Triggert manuelles AI-Training"""
    data = request.get_json() or {}
    site_id = data.get('site_id')
    
    ems = get_ems_for_site(site_id)
    if not ems:
        return jsonify({'error': 'Site not found'}), 404
    
    ai_selector = ems.strategy_manager.ai_selector
    if not ai_selector:
        return jsonify({'success': False, 'error': 'AI selector not initialized'}), 400
    
    try:
        # Triggere Training
        ems.strategy_manager._train_ai_selector()
        
        # Zähle Trainingsdaten
        training_samples = 0
        if ems.history_db:
            opt_history = ems.history_db.get_optimization_history(days=30)
            training_samples = len(opt_history)
        
        return jsonify({
            'success': True,
            'is_trained': ai_selector.is_trained,
            'training_samples': training_samples
        })
    except Exception as e:
        logger.error(f"Error training AI model: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/ai/features')
@login_required
def api_ai_features():
    """Gibt Feature-Importance zurück"""
    site_id = request.args.get('site_id', type=int)
    ems = get_ems_for_site(site_id)
    if not ems:
        return jsonify({'error': 'Site not found'}), 404
    
    ai_selector = ems.strategy_manager.ai_selector
    if not ai_selector or not ai_selector.is_trained:
        return jsonify({'success': False, 'error': 'AI model not trained'}), 400
    
    try:
        features = ai_selector.get_feature_importance()
        return jsonify({'success': True, 'features': features})
    except Exception as e:
        logger.error(f"Error getting feature importance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# API - Forecasts & Prices
# ============================================================================

@bp.route('/api/forecast')
@login_required
def api_forecast():
    """Gibt Prognosen zurück"""
    try:
        forecast_data = current_app.ems._get_forecast_data()
        
        # Konvertiere zu JSON-serialisierbarem Format
        result = {
            'prices': [(ts.isoformat(), price) for ts, price in forecast_data.get('prices', [])],
            'pv': [(ts.isoformat(), power) for ts, power in forecast_data.get('pv', [])],
            'load': [(ts.isoformat(), power) for ts, power in forecast_data.get('load', [])]
        }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting forecast: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# API - Analytics & History (Phase 2)
# ============================================================================

@bp.route('/api/history/state')
@login_required
def api_history_state():
    """Gibt State History zurück"""
    hours = request.args.get('hours', 24, type=int)
    
    try:
        history = current_app.ems.history_db.get_state_history(hours=hours)
        return jsonify({'history': history, 'count': len(history)})
    except Exception as e:
        logger.error(f"Error getting state history: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/history/optimization')
@login_required
def api_history_optimization():
    """Gibt Optimization History zurück"""
    days = request.args.get('days', 7, type=int)
    
    try:
        history = current_app.ems.history_db.get_optimization_history(days=days)
        return jsonify({'history': history, 'count': len(history)})
    except Exception as e:
        logger.error(f"Error getting optimization history: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/analytics/daily')
@login_required
def api_daily_metrics():
    """Gibt tägliche Metriken zurück"""
    days = request.args.get('days', 30, type=int)
    site_id = request.args.get('site_id', type=int)
    
    try:
        ems = get_ems_for_site(site_id)
        if not ems or not hasattr(ems, 'history_db') or not ems.history_db:
            return jsonify({'metrics': [], 'count': 0})
        
        metrics = ems.history_db.get_daily_metrics(days=days)
        # Wenn keine Metriken vorhanden, berechne sie für heute
        if not metrics:
            try:
                ems.history_db.calculate_daily_metrics()
                metrics = ems.history_db.get_daily_metrics(days=days)
            except Exception as calc_err:
                logger.warning(f"Could not calculate daily metrics: {calc_err}")
        return jsonify({'metrics': metrics or [], 'count': len(metrics) if metrics else 0})
    except Exception as e:
        logger.error(f"Error getting daily metrics: {e}", exc_info=True)
        return jsonify({'error': str(e), 'metrics': [], 'count': 0}), 500


@bp.route('/api/analytics/summary')
@login_required
def api_performance_summary():
    """Gibt Performance-Zusammenfassung zurück"""
    days = request.args.get('days', 30, type=int)
    site_id = request.args.get('site_id', type=int)
    
    try:
        ems = get_ems_for_site(site_id)
        if not ems or not hasattr(ems, 'history_db') or not ems.history_db:
            return jsonify({
                'total_profit': 0.0,
                'avg_daily_profit': 0.0,
                'total_cycles': 0.0,
                'avg_soc': 0.0,
                'period_days': days,
                'strategy_distribution': {}
            })
        
        summary = ems.history_db.get_performance_summary(days=days)
        # Wenn keine Zusammenfassung vorhanden, berechne Metriken für heute
        if not summary:
            try:
                ems.history_db.calculate_daily_metrics()
                summary = ems.history_db.get_performance_summary(days=days)
            except Exception as calc_err:
                logger.warning(f"Could not calculate daily metrics: {calc_err}")
        
        # Stelle sicher, dass alle erforderlichen Felder vorhanden sind
        if not summary:
            summary = {
                'total_profit': 0.0,
                'avg_daily_profit': 0.0,
                'total_cycles': 0.0,
                'avg_soc': 0.0,
                'period_days': days,
                'strategy_distribution': {}
            }
        
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'total_profit': 0.0,
            'avg_daily_profit': 0.0,
            'total_cycles': 0.0,
            'avg_soc': 0.0,
            'period_days': days,
            'strategy_distribution': {}
        }), 500


# ============================================================================
# API - Documentation
# ============================================================================

@bp.route('/api/openapi.yaml')
def openapi_spec():
    """OpenAPI Spezifikation"""
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / 'api' / 'openapi.yaml'
    return send_from_directory(p.parent, p.name, mimetype='text/yaml')

# ============================================================================
# MQTT Configuration API
# ============================================================================

@bp.route('/api/mqtt/config', methods=['GET'])
@login_required
def api_mqtt_config_get():
    """Get current MQTT configuration"""
    try:
        site_id = request.args.get('site_id', type=int)
        config = load_config()
        site_config = get_site_config(config, site_id)
        mqtt_config = site_config.get('mqtt', {})
        return jsonify({
            'success': True,
            'config': mqtt_config,
            'site_id': site_id
        })
    except Exception as e:
        logger.error(f"Error getting MQTT config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/mqtt/config', methods=['POST'])
@login_required
def api_mqtt_config_set():
    """Update MQTT configuration"""
    try:
        config_data = request.get_json()
        site_id = config_data.pop('site_id', None)
        
        # Load current config
        config = load_config()
        
        # Update MQTT section (site-specific or global)
        set_site_config(config, site_id, 'mqtt', config_data)
        
        # Save config
        save_config(config)
        
        return jsonify({'success': True, 'message': 'MQTT configuration updated', 'site_id': site_id})
        
    except Exception as e:
        logger.error(f"Error setting MQTT config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/mqtt/test', methods=['POST'])
def api_mqtt_test():
    """Test MQTT connection"""
    try:
        config_data = request.get_json()
        
        # Import MQTT client
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            return jsonify({'success': False, 'error': 'paho-mqtt not installed'}), 500
        
        # Test connection
        client = mqtt.Client(config_data.get('client_id', 'phoenyra_ems_test'))
        
        if config_data.get('username'):
            client.username_pw_set(config_data['username'], config_data.get('password'))
        
        try:
            client.connect(config_data['host'], config_data['port'], config_data.get('keepalive', 60))
            client.disconnect()
            return jsonify({'success': True, 'message': 'MQTT connection successful'})
        except Exception as conn_error:
            return jsonify({'success': False, 'error': f'Connection failed: {str(conn_error)}'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# Modbus Configuration API
# ============================================================================

@bp.route('/api/modbus/config', methods=['GET'])
@login_required
def api_modbus_config_get():
    """Get current Modbus configuration"""
    try:
        site_id = request.args.get('site_id', type=int)
        config = load_config()
        site_config = get_site_config(config, site_id)
        modbus_config = site_config.get('modbus', {})
        profile_key = modbus_config.get('profile')
        profile_details = get_profile(profile_key) if profile_key else None
        profiles = list_profiles()
        return jsonify({
            'success': True,
            'config': modbus_config,
            'profile': profile_details,
            'profiles': profiles,
            'site_id': site_id
        })
    except Exception as e:
        logger.error(f"Error getting Modbus config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/modbus/config', methods=['POST'])
@login_required
def api_modbus_config_set():
    """Update Modbus configuration"""
    try:
        config_data = request.get_json()
        site_id = config_data.pop('site_id', None)
        
        # Load current config
        config = load_config()
        
        # Get site-specific or global modbus section
        if site_id is None:
            if 'modbus' not in config:
                config['modbus'] = {}
            modbus_section: Dict[str, Any] = config['modbus']
        else:
            if 'sites' not in config:
                config['sites'] = {}
            if site_id not in config['sites']:
                config['sites'][site_id] = {}
            if 'modbus' not in config['sites'][site_id]:
                config['sites'][site_id]['modbus'] = {}
            modbus_section: Dict[str, Any] = config['sites'][site_id]['modbus']

        registers = config_data.pop('registers', None)
        if registers is not None:
            modbus_section['registers'] = registers

        status_codes = config_data.pop('status_codes', None)
        if status_codes is not None:
            # sicherstellen, dass Keys als Strings gespeichert werden
            modbus_section['status_codes'] = {str(k): v for k, v in status_codes.items()}

        # übrige Felder kopieren
        modbus_section.update(config_data)
        
        # Save config
        save_config(config)
        
        return jsonify({'success': True, 'message': 'Modbus configuration updated', 'site_id': site_id})
        
    except Exception as e:
        logger.error(f"Error setting Modbus config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/modbus/test', methods=['POST'])
def api_modbus_test():
    """Test Modbus connection"""
    try:
        config_data = request.get_json()

        modbus_config = ModbusConfig(
            enabled=True,
            connection_type=config_data.get('connection_type', 'tcp'),
            host=config_data.get('host', 'localhost'),
            port=config_data.get('port', 502),
            slave_id=config_data.get('slave_id', 1),
            timeout=config_data.get('timeout', 3.0),
            retries=config_data.get('retries', 3),
            profile=config_data.get('profile'),
            poll_interval_s=config_data.get('poll_interval_s', 2.0),
            status_codes={str(k): v for k, v in config_data.get('status_codes', {}).items()},
            registers=config_data.get('registers', {}),
            serial_port=config_data.get('serial_port', '/dev/ttyUSB0'),
            baudrate=config_data.get('baudrate', 115200),
            parity=config_data.get('parity', 'N'),
        )

        client = ModbusClient(modbus_config)
        if not client.config.enabled:
            return jsonify({'success': False, 'error': 'pymodbus not installed'}), 500

        if not client.connect():
            return jsonify({'success': False, 'error': 'Modbus connection failed'})

        try:
            if client.test_connection():
                return jsonify({'success': True, 'message': 'Modbus connection successful'})
            return jsonify({'success': False, 'error': 'No response from test register'})
        finally:
            client.disconnect()

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/modbus/profiles', methods=['GET'])
def api_modbus_profiles():
    """Liste oder Detail der verfügbaren Modbus-Profile"""
    try:
        profile_key = request.args.get('profile')
        if profile_key:
            profile = get_profile(profile_key)
            if not profile:
                return jsonify({'success': False, 'error': 'Profile not found'}), 404
            return jsonify({'success': True, 'profile': profile})
        else:
            profiles = list_profiles()
            return jsonify({'success': True, 'profiles': profiles})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/config/feedin_limitation', methods=['GET'])
@login_required
def api_feedin_limitation_get():
    """Get Feed-in Limitation configuration"""
    try:
        site_id = request.args.get('site_id', type=int)
        config = load_config()
        site_config = get_site_config(config, site_id)
        feedin_config = site_config.get('feedin_limitation', {})
        return jsonify({'success': True, 'config': feedin_config, 'site_id': site_id})
    except Exception as e:
        logger.error(f"Error getting feedin limitation config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/config/feedin_limitation', methods=['POST'])
@login_required
def api_feedin_limitation_set():
    """Update Feed-in Limitation configuration"""
    try:
        config_data = request.get_json()
        site_id = config_data.pop('site_id', None)
        config = load_config()
        set_site_config(config, site_id, 'feedin_limitation', config_data)
        save_config(config)
        return jsonify({'success': True, 'message': 'Feed-in limitation configuration updated', 'site_id': site_id})
    except Exception as e:
        logger.error(f"Error setting feedin limitation config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/config/grid_connection', methods=['GET'])
@login_required
def api_grid_connection_get():
    """Get Grid Connection configuration"""
    try:
        site_id = request.args.get('site_id', type=int)
        config = load_config()
        site_config = get_site_config(config, site_id)
        grid_config = site_config.get('grid_connection', {})
        return jsonify({'success': True, 'config': grid_config, 'site_id': site_id})
    except Exception as e:
        logger.error(f"Error getting grid connection config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/config/grid_connection', methods=['POST'])
@login_required
def api_grid_connection_set():
    """Update Grid Connection configuration"""
    try:
        config_data = request.get_json()
        site_id = config_data.pop('site_id', None)
        config = load_config()
        set_site_config(config, site_id, 'grid_connection', config_data)
        save_config(config)
        return jsonify({'success': True, 'message': 'Grid connection configuration updated', 'site_id': site_id})
    except Exception as e:
        logger.error(f"Error setting grid connection config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/config/bess', methods=['GET'])
@login_required
def api_bess_config_get():
    """Get BESS configuration"""
    try:
        site_id = request.args.get('site_id', type=int)
        config = load_config()
        site_config = get_site_config(config, site_id)
        bess_config = site_config.get('bess', {})
        return jsonify({'success': True, 'config': bess_config, 'site_id': site_id})
    except Exception as e:
        logger.error(f"Error getting BESS config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/config/bess', methods=['POST'])
@login_required
@role_required('admin')
def api_bess_config_set():
    """Update BESS configuration"""
    try:
        config_data = request.get_json()
        site_id = config_data.pop('site_id', None)
        config = load_config()
        set_site_config(config, site_id, 'bess', config_data)
        save_config(config)
        return jsonify({'success': True, 'message': 'BESS configuration updated', 'site_id': site_id})
    except Exception as e:
        logger.error(f"Error setting BESS config: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/config/grid_tariffs', methods=['GET'])
@login_required
def api_grid_tariffs_get():
    """Get Grid Tariffs configuration"""
    try:
        site_id = request.args.get('site_id', type=int)
        config = load_config()
        site_config = get_site_config(config, site_id)
        grid_tariffs_config = site_config.get('grid_tariffs', {})
        
        # Hole zusätzliche Info vom Service (falls verfügbar)
        tariff_info = {}
        ems = get_ems_for_site(site_id) if site_id else (current_app.ems if hasattr(current_app, 'ems') else None)
        if ems and hasattr(ems, 'grid_tariff_service'):
            tariff_info = ems.grid_tariff_service.get_tariff_info()
        
        return jsonify({
            'success': True, 
            'config': grid_tariffs_config,
            'info': tariff_info,
            'site_id': site_id
        })
    except Exception as e:
        logger.error(f"Error getting grid tariffs config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/config/grid_tariffs', methods=['POST'])
@login_required
@role_required('admin')
def api_grid_tariffs_set():
    """Update Grid Tariffs configuration"""
    try:
        config_data = request.get_json()
        site_id = config_data.pop('site_id', None)
        
        # Validiere Konfiguration
        if config_data.get('enabled'):
            if not config_data.get('tariff_structure'):
                return jsonify({'success': False, 'error': 'tariff_structure is required when enabled'}), 400
        
        config = load_config()
        set_site_config(config, site_id, 'grid_tariffs', config_data)
        save_config(config)
        
        # Aktualisiere Service (falls EMS bereits läuft)
        try:
            ems = get_ems_for_site(site_id) if site_id else (current_app.ems if hasattr(current_app, 'ems') else None)
            if ems and hasattr(ems, 'grid_tariff_service'):
                from services.grid_tariff import GridTariffService
                ems.grid_tariff_service = GridTariffService(config_data)
                logger.info(f"Grid tariff service updated for site {site_id}")
        except Exception as service_err:
            logger.warning(f"Could not update grid tariff service: {service_err}")
        
        return jsonify({'success': True, 'message': 'Grid tariffs configuration updated', 'site_id': site_id})
    except Exception as e:
        logger.error(f"Error updating grid tariffs config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# API - User Management
# ============================================================================

@bp.route('/api/users', methods=['GET'])
@login_required
@role_required('admin')
def api_users_list():
    """Liste aller Benutzer"""
    try:
        if not hasattr(current_app, 'user_db'):
            return jsonify({'success': False, 'error': 'User database not initialized'}), 500
        
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        users = current_app.user_db.list_users(include_inactive=include_inactive)
        
        # Entferne Passwort-Hashes aus der Antwort
        for user in users:
            user.pop('password_hash', None)
        
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/users', methods=['POST'])
@login_required
@role_required('admin')
def api_users_create():
    """Erstellt neuen Benutzer"""
    try:
        if not hasattr(current_app, 'user_db'):
            return jsonify({'success': False, 'error': 'User database not initialized'}), 500
        
        data = request.get_json()
        
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        role = data.get('role', 'viewer')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'username and password are required'}), 400
        
        if role not in ['admin', 'operator', 'viewer']:
            return jsonify({'success': False, 'error': 'Invalid role'}), 400
        
        user = current_app.user_db.create_user(
            username=username,
            password=password,
            email=email,
            role=role,
            first_name=first_name,
            last_name=last_name
        )
        
        # Entferne Passwort-Hash
        user.pop('password_hash', None)
        
        return jsonify({'success': True, 'user': user})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@role_required('admin')
def api_users_update(user_id):
    """Aktualisiert Benutzer"""
    try:
        if not hasattr(current_app, 'user_db'):
            return jsonify({'success': False, 'error': 'User database not initialized'}), 500
        
        data = request.get_json()
        
        # Prüfe ob Benutzer existiert
        existing = current_app.user_db.get_user_by_id(user_id)
        if not existing:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Validiere Rolle
        if 'role' in data and data['role'] not in ['admin', 'operator', 'viewer']:
            return jsonify({'success': False, 'error': 'Invalid role'}), 400
        
        # Konvertiere Boolean zu Integer für is_active und email_verified
        if 'is_active' in data:
            data['is_active'] = 1 if data['is_active'] else 0
        if 'email_verified' in data:
            data['email_verified'] = 1 if data['email_verified'] else 0
        
        user = current_app.user_db.update_user(user_id, **data)
        
        # Entferne Passwort-Hash
        user.pop('password_hash', None)
        
        return jsonify({'success': True, 'user': user})
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def api_users_delete(user_id):
    """Löscht Benutzer"""
    try:
        if not hasattr(current_app, 'user_db'):
            return jsonify({'success': False, 'error': 'User database not initialized'}), 500
        
        # Verhindere Löschung des eigenen Accounts
        current_user_id = session.get('user', {}).get('id')
        if current_user_id == user_id:
            return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
        
        # Prüfe ob Benutzer existiert
        existing = current_app.user_db.get_user_by_id(user_id)
        if not existing:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        deleted = current_app.user_db.delete_user(user_id)
        
        if deleted:
            return jsonify({'success': True, 'message': 'User deleted'})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete user'}), 500
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/users/<int:user_id>/password', methods=['POST'])
@login_required
@role_required('admin')
def api_users_change_password(user_id):
    """Ändert Passwort eines Benutzers"""
    try:
        if not hasattr(current_app, 'user_db'):
            return jsonify({'success': False, 'error': 'User database not initialized'}), 500
        
        data = request.get_json()
        new_password = data.get('password')
        
        if not new_password:
            return jsonify({'success': False, 'error': 'password is required'}), 400
        
        # Prüfe ob Benutzer existiert
        existing = current_app.user_db.get_user_by_id(user_id)
        if not existing:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        current_app.user_db.change_password(user_id, new_password)
        
        return jsonify({'success': True, 'message': 'Password changed'})
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# API - Notifications
# ============================================================================

@bp.route('/api/notifications', methods=['GET'])
@login_required
def api_notifications():
    """Gibt aktuelle Benachrichtigungen und Alarme zurück"""
    try:
        if not hasattr(current_app, 'ems') or current_app.ems is None:
            return jsonify({
                'success': True,
                'notifications': [],
                'count': 0,
                'message': 'EMS not initialized'
            })
        
        state = current_app.ems.to_dict()
        notifications = []
        
        # Modbus-Alarme
        if state.get('alarm') and state.get('active_alarms'):
            for alarm in state.get('active_alarms', []):
                notifications.append({
                    'severity': 'critical',
                    'title': 'Modbus Alarm',
                    'message': f'Alarm erkannt: {alarm}',
                    'source': 'Modbus/BMS',
                    'timestamp': state.get('timestamp', datetime.now(timezone.utc).isoformat())
                })
        
        # DSO-Trip
        if state.get('dso_trip'):
            notifications.append({
                'severity': 'critical',
                'title': 'DSO-Abschaltanweisung',
                'message': 'Netzbetreiber hat eine Abschaltanweisung erteilt. System wird in sicheren Zustand versetzt.',
                'source': 'DSO/Power Control',
                'timestamp': state.get('timestamp', datetime.now(timezone.utc).isoformat())
            })
        
        # Safety Alarm
        if state.get('safety_alarm'):
            notifications.append({
                'severity': 'critical',
                'title': 'Sicherheitsalarm',
                'message': 'Sicherheitsalarm erkannt. Bitte Systemzustand prüfen.',
                'source': 'Safety System',
                'timestamp': state.get('timestamp', datetime.now(timezone.utc).isoformat())
            })
        
        # Power Limit Warnung
        if state.get('power_limit_reason'):
            notifications.append({
                'severity': 'warning',
                'title': 'Leistungsbegrenzung aktiv',
                'message': f'Leistung begrenzt: {state.get("power_limit_reason", "Unbekannter Grund")}',
                'source': 'Power Control',
                'timestamp': state.get('timestamp', datetime.now(timezone.utc).isoformat())
            })
        
        # Feed-in Limitation Info
        if state.get('feedin_limit_pct') and state.get('feedin_limit_mode') != 'off':
            notifications.append({
                'severity': 'info',
                'title': 'Einspeisebegrenzung aktiv',
                'message': f'Einspeisung auf {state.get("feedin_limit_pct", 0)}% begrenzt (Modus: {state.get("feedin_limit_mode", "unknown")})',
                'source': 'Feed-in Limitation',
                'timestamp': state.get('timestamp', datetime.now(timezone.utc).isoformat())
            })
        
        # Grid Utilization Warnung
        if state.get('grid_utilization_pct') and state.get('grid_utilization_pct', 0) > 90:
            notifications.append({
                'severity': 'warning',
                'title': 'Hohe Netzanschlussauslastung',
                'message': f'Netzanschluss zu {state.get("grid_utilization_pct", 0):.1f}% ausgelastet',
                'source': 'Grid Connection',
                'timestamp': state.get('timestamp', datetime.now(timezone.utc).isoformat())
            })
        
        # Optimierungs-Status
        if state.get('optimization_status') == 'failed':
            notifications.append({
                'severity': 'warning',
                'title': 'Optimierung fehlgeschlagen',
                'message': 'Die letzte Optimierung konnte nicht durchgeführt werden. Fallback-Strategie aktiv.',
                'source': 'Optimization',
                'timestamp': state.get('timestamp', datetime.now(timezone.utc).isoformat())
            })
        
        # Sortiere nach Schweregrad (critical > warning > info > success)
        severity_order = {'critical': 0, 'warning': 1, 'info': 2, 'success': 3}
        notifications.sort(key=lambda x: severity_order.get(x.get('severity', 'info'), 3))
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'count': len(notifications)
        })
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# API - Multi-Site Management
# ============================================================================

@bp.route('/api/sites', methods=['GET'])
@login_required
def api_list_sites():
    """Liste aller Standorte"""
    try:
        if not (hasattr(current_app, 'multi_site') and current_app.multi_site):
            # Single-Site-Modus: Gibt Default-Site zurück
            try:
                state_dict = current_app.ems.to_dict() if hasattr(current_app.ems, 'to_dict') else {}
            except Exception as e:
                logger.warning(f"Error getting EMS state: {e}")
                state_dict = {}
            
            return jsonify({
                'success': True,
                'sites': [{
                    'id': 1,
                    'name': 'Default Site',
                    'state': state_dict
                }],
                'multi_site': False,
                'default_site_id': 1
            })
        
        # Multi-Site-Modus
        if not hasattr(current_app.ems, 'list_sites'):
            return jsonify({
                'sites': [],
                'multi_site': False,
                'error': 'Multi-Site not properly initialized'
            }), 500
        
        sites_list = current_app.ems.list_sites()
        return jsonify({
            'sites': sites_list,
            'multi_site': True,
            'default_site_id': getattr(current_app.ems, 'default_site_id', 1)
        })
    except Exception as e:
        logger.error(f"Error in api_list_sites: {e}", exc_info=True)
        return jsonify({
            'sites': [],
            'multi_site': False,
            'error': str(e)
        }), 500


@bp.route('/api/sites', methods=['POST'])
@login_required
@role_required('admin')
def api_create_site():
    """Erstellt einen neuen Standort"""
    try:
        if not (hasattr(current_app, 'multi_site') and current_app.multi_site):
            return jsonify({
                'success': False,
                'error': 'Multi-Site-Modus ist nicht aktiviert. Bitte aktivieren Sie Multi-Site in den Einstellungen.'
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Keine Daten erhalten'}), 400
        
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Standort-Name ist erforderlich'}), 400
        
        # Lade aktuelle Konfiguration
        config = load_config()
        
        if 'sites' not in config:
            config['sites'] = {'sites': {}, 'default_site_id': 1}
        
        sites_dict = config['sites'].get('sites', {})
        
        # Bestimme neue Site-ID
        requested_id = data.get('site_id')
        if requested_id:
            site_id = int(requested_id)
            if str(site_id) in sites_dict or site_id in sites_dict:
                return jsonify({
                    'success': False,
                    'error': f'Standort-ID {site_id} existiert bereits'
                }), 400
        else:
            # Auto-generiere nächste verfügbare ID
            existing_ids = []
            for k in sites_dict.keys():
                try:
                    existing_ids.append(int(k))
                except (ValueError, TypeError):
                    continue
            site_id = max(existing_ids) + 1 if existing_ids else 1
        
        # Hole Standard-Konfiguration (kopiere von Site 1 oder verwende globale Defaults)
        default_site = sites_dict.get(1) or sites_dict.get('1')
        
        # Erstelle neue Site-Konfiguration
        new_site_config = {
            'name': name,
            'location': {
                'city': data.get('city', 'Unbekannt'),
                'latitude': data.get('latitude', 48.2082),
                'longitude': data.get('longitude', 16.3738)
            },
            'database': {
                'history_path': f"data/ems_history_site_{site_id}.db"
            }
        }
        
        # Kopiere Konfigurationen von Default-Site oder globalen Defaults
        if default_site:
            # Kopiere alle Konfigurationen von Site 1
            for key in ['bess', 'ems', 'feedin_limitation', 'forecast', 'grid_connection', 
                       'grid_tariffs', 'modbus', 'mqtt', 'strategies']:
                if key in default_site:
                    new_site_config[key] = default_site[key]
        else:
            # Verwende globale Defaults
            for key in ['bess', 'ems', 'feedin_limitation', 'forecast', 'grid_connection',
                       'grid_tariffs', 'modbus', 'mqtt', 'strategies']:
                if key in config:
                    new_site_config[key] = config[key]
        
        # Füge neue Site zur Konfiguration hinzu
        sites_dict[site_id] = new_site_config
        config['sites']['sites'] = sites_dict
        
        # Speichere Konfiguration
        save_config(config)
        
        logger.info(f"✅ Neuer Standort erstellt: ID={site_id}, Name={name}")
        
        return jsonify({
            'success': True,
            'site_id': site_id,
            'message': f'Standort "{name}" (ID: {site_id}) erfolgreich erstellt. Bitte starten Sie den Container neu.'
        })
        
    except Exception as e:
        logger.error(f"Error creating site: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Fehler beim Erstellen des Standorts: {str(e)}'
        }), 500


@bp.route('/api/sites/<int:site_id>', methods=['GET'])
@login_required
def api_get_site(site_id: int):
    """Informationen über einen Standort"""
    if not (hasattr(current_app, 'multi_site') and current_app.multi_site):
        if site_id == 1:
            return jsonify({
                'id': 1,
                'name': 'Default Site',
                'state': current_app.ems.to_dict()
            })
        return jsonify({'error': 'Site not found'}), 404
    
    site_info = current_app.ems.get_site_info(site_id)
    if site_info:
        return jsonify(site_info)
    return jsonify({'error': 'Site not found'}), 404


@bp.route('/api/sites/<int:site_id>', methods=['PUT'])
@login_required
@role_required('admin')
def api_update_site(site_id: int):
    """Bearbeitet einen bestehenden Standort"""
    try:
        if not (hasattr(current_app, 'multi_site') and current_app.multi_site):
            return jsonify({
                'success': False,
                'error': 'Multi-Site-Modus ist nicht aktiviert.'
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Keine Daten erhalten'}), 400
        
        # Lade aktuelle Konfiguration
        config = load_config()
        
        if 'sites' not in config or 'sites' not in config['sites']:
            return jsonify({'success': False, 'error': 'Keine Standorte konfiguriert'}), 404
        
        sites_dict = config['sites'].get('sites', {})
        
        # Prüfe ob Standort existiert
        if str(site_id) not in sites_dict and site_id not in sites_dict:
            return jsonify({'success': False, 'error': f'Standort {site_id} nicht gefunden'}), 404
        
        # Hole bestehende Site-Konfiguration
        site_key = str(site_id) if str(site_id) in sites_dict else site_id
        existing_site = sites_dict[site_key]
        
        # Aktualisiere nur übergebene Felder
        if 'name' in data:
            existing_site['name'] = data['name'].strip()
        
        if 'city' in data or 'latitude' in data or 'longitude' in data:
            if 'location' not in existing_site:
                existing_site['location'] = {}
            if 'city' in data:
                existing_site['location']['city'] = data['city'].strip() if data['city'] else 'Unbekannt'
            if 'latitude' in data:
                existing_site['location']['latitude'] = data['latitude']
            if 'longitude' in data:
                existing_site['location']['longitude'] = data['longitude']
        
        # Speichere Konfiguration
        sites_dict[site_key] = existing_site
        config['sites']['sites'] = sites_dict
        save_config(config)
        
        logger.info(f"✅ Standort {site_id} aktualisiert")
        
        return jsonify({
            'success': True,
            'message': f'Standort {site_id} erfolgreich aktualisiert. Bitte starten Sie den Container neu.'
        })
        
    except Exception as e:
        logger.error(f"Error updating site {site_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Fehler beim Aktualisieren des Standorts: {str(e)}'
        }), 500


@bp.route('/api/sites/<int:site_id>/duplicate', methods=['POST'])
@login_required
@role_required('admin')
def api_duplicate_site(site_id: int):
    """Dupliziert einen Standort mit allen Konfigurationen"""
    try:
        if not (hasattr(current_app, 'multi_site') and current_app.multi_site):
            return jsonify({
                'success': False,
                'error': 'Multi-Site-Modus ist nicht aktiviert.'
            }), 400
        
        # Lade aktuelle Konfiguration
        config = load_config()
        
        if 'sites' not in config or 'sites' not in config['sites']:
            return jsonify({'success': False, 'error': 'Keine Standorte konfiguriert'}), 404
        
        sites_dict = config['sites'].get('sites', {})
        
        # Prüfe ob Standort existiert
        site_key = None
        if str(site_id) in sites_dict:
            site_key = str(site_id)
        elif site_id in sites_dict:
            site_key = site_id
        
        if site_key is None:
            return jsonify({'success': False, 'error': f'Standort {site_id} nicht gefunden'}), 404
        
        # Hole Original-Site-Konfiguration
        original_site = sites_dict[site_key].copy()
        
        # Generiere neue Site-ID
        existing_ids = []
        for k in sites_dict.keys():
            try:
                existing_ids.append(int(k))
            except (ValueError, TypeError):
                continue
        new_site_id = max(existing_ids) + 1 if existing_ids else 1
        
        # Erstelle Kopie mit neuem Namen
        original_name = original_site.get('name', f'Site {site_id}')
        new_name = f"{original_name} (Kopie)"
        original_site['name'] = new_name
        
        # Füge neue Site zur Konfiguration hinzu
        sites_dict[new_site_id] = original_site
        config['sites']['sites'] = sites_dict
        save_config(config)
        
        logger.info(f"✅ Standort {site_id} dupliziert zu {new_site_id}")
        
        return jsonify({
            'success': True,
            'site_id': new_site_id,
            'message': f'Standort erfolgreich kopiert. Neue ID: {new_site_id}. Bitte starten Sie den Container neu.'
        })
        
    except Exception as e:
        logger.error(f"Error duplicating site {site_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Fehler beim Duplizieren des Standorts: {str(e)}'
        }), 500


@bp.route('/api/sites/<int:site_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def api_delete_site(site_id: int):
    """Löscht einen Standort"""
    try:
        if not (hasattr(current_app, 'multi_site') and current_app.multi_site):
            return jsonify({
                'success': False,
                'error': 'Multi-Site-Modus ist nicht aktiviert.'
            }), 400
        
        # Lade aktuelle Konfiguration
        config = load_config()
        
        if 'sites' not in config or 'sites' not in config['sites']:
            return jsonify({'success': False, 'error': 'Keine Standorte konfiguriert'}), 404
        
        sites_dict = config['sites'].get('sites', {})
        
        # Prüfe ob Standort existiert
        site_key = None
        if str(site_id) in sites_dict:
            site_key = str(site_id)
        elif site_id in sites_dict:
            site_key = site_id
        
        if site_key is None:
            return jsonify({'success': False, 'error': f'Standort {site_id} nicht gefunden'}), 404
        
        # Prüfe ob es der letzte Standort ist
        if len(sites_dict) <= 1:
            return jsonify({
                'success': False,
                'error': 'Der letzte Standort kann nicht gelöscht werden. Mindestens ein Standort muss vorhanden sein.'
            }), 400
        
        # Prüfe ob es der Default-Site ist
        default_site_id = config['sites'].get('default_site_id', 1)
        if site_id == default_site_id:
            # Setze neuen Default (ersten anderen Standort)
            other_sites = [int(k) for k in sites_dict.keys() if int(k) != site_id]
            if other_sites:
                config['sites']['default_site_id'] = other_sites[0]
                logger.info(f"Default-Site geändert zu {other_sites[0]}")
        
        # Lösche Standort
        del sites_dict[site_key]
        config['sites']['sites'] = sites_dict
        save_config(config)
        
        logger.info(f"✅ Standort {site_id} gelöscht")
        
        return jsonify({
            'success': True,
            'message': f'Standort {site_id} erfolgreich gelöscht. Bitte starten Sie den Container neu.'
        })
        
    except Exception as e:
        logger.error(f"Error deleting site {site_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Fehler beim Löschen des Standorts: {str(e)}'
        }), 500


@bp.route('/api/sites/<int:site_id>/state', methods=['GET'])
@login_required
def api_get_site_state(site_id: int):
    """Zustand eines Standorts"""
    ems = get_ems_for_site(site_id)
    if ems:
        return jsonify(ems.to_dict())
    return jsonify({'error': 'Site not found'}), 404


@bp.route('/api/sites/aggregated', methods=['GET'])
@login_required
@role_required('admin')  # Nur Admins sehen aggregierte Ansicht
def api_get_aggregated_state():
    """Aggregierter Zustand aller Standorte"""
    if not (hasattr(current_app, 'multi_site') and current_app.multi_site):
        # Single-Site: Gibt normalen State zurück
        return jsonify(current_app.ems.to_dict())
    
    aggregated = current_app.ems.get_aggregated_state()
    return jsonify(aggregated)


@bp.route('/api/config/multisite', methods=['POST'])
@login_required
@role_required('admin')  # Nur Admins können Multi-Site aktivieren/deaktivieren
def api_multisite_config():
    """Aktiviert oder deaktiviert Multi-Site-Modus"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        
        # Lade aktuelle Konfiguration
        config = load_config()
        
        if enabled:
            # Aktivieren: Erstelle Standard-Konfiguration falls nicht vorhanden
            if 'sites' not in config or 'sites' not in config['sites'] or not config['sites'].get('sites'):
                # Erstelle Standard-Site-Konfiguration basierend auf aktueller Config
                current_bess = config.get('bess', {})
                current_modbus = config.get('modbus', {})
                current_mqtt = config.get('mqtt', {})
                current_forecast = config.get('forecast', {})
                current_grid = config.get('grid_connection', {})
                current_feedin = config.get('feedin_limitation', {})
                current_tariffs = config.get('grid_tariffs', {})
                current_ems = config.get('ems', {})
                current_strategies = config.get('strategies', {})
                
                config['sites'] = {
                    'default_site_id': 1,
                    'sites': {
                        1: {
                            'name': 'Standort 1',
                            'location': {
                                'city': 'Standard',
                                'latitude': current_forecast.get('latitude', 48.2082),
                                'longitude': current_forecast.get('longitude', 16.3738)
                            },
                            'bess': current_bess,
                            'modbus': current_modbus,
                            'mqtt': current_mqtt,
                            'forecast': current_forecast,
                            'grid_connection': current_grid,
                            'feedin_limitation': current_feedin,
                            'grid_tariffs': current_tariffs,
                            'ems': current_ems,
                            'strategies': current_strategies,
                            'database': {
                                'history_path': 'data/ems_history_site_1.db'
                            }
                        }
                    }
                }
                logger.info("Multi-Site aktiviert: Standard-Site-Konfiguration erstellt")
            else:
                # Multi-Site ist bereits konfiguriert
                logger.info("Multi-Site ist bereits konfiguriert")
        else:
            # Deaktivieren: Entferne sites.sites (behalte default_site_id für Rückwärtskompatibilität)
            if 'sites' in config:
                if 'sites' in config['sites']:
                    del config['sites']['sites']
                logger.info("Multi-Site deaktiviert: sites.sites entfernt")
        
        # Speichere Konfiguration
        save_config(config)
        
        # Versuche Config neu zu laden (ohne Container-Neustart)
        try:
            # Lade Config neu
            new_cfg = load_config()
            sites_config = new_cfg.get('sites', {})
            
            # Prüfe ob Multi-Site aktiviert werden sollte
            if sites_config and 'sites' in sites_config and sites_config.get('sites'):
                # Versuche Multi-Site neu zu initialisieren
                if hasattr(current_app, 'multi_site') and current_app.multi_site:
                    # Stoppe alte Instanzen (nur wenn MultiSiteManager)
                    if hasattr(current_app.ems, 'stop_all'):
                        current_app.ems.stop_all()
                    elif hasattr(current_app.ems, 'stop'):
                        current_app.ems.stop()
                
                # Initialisiere neu
                from ems.multi_site_manager import MultiSiteManager
                current_app.ems = MultiSiteManager(sites_config)
                current_app.multi_site = True
                logger.info("Multi-Site-Konfiguration neu geladen")
            else:
                # Single-Site-Modus
                if hasattr(current_app, 'multi_site') and current_app.multi_site:
                    # Stoppe alte Instanzen (nur wenn MultiSiteManager)
                    if hasattr(current_app.ems, 'stop_all'):
                        current_app.ems.stop_all()
                    elif hasattr(current_app.ems, 'stop'):
                        current_app.ems.stop()
                
                from ems.controller import EmsCore
                current_app.ems = EmsCore(new_cfg)
                current_app.ems.start()
                current_app.multi_site = False
                logger.info("Single-Site-Modus aktiviert")
        except Exception as reload_err:
            logger.warning(f"Konfiguration gespeichert, aber Neuladen fehlgeschlagen: {reload_err}. Container-Neustart empfohlen.", exc_info=True)
        
        return jsonify({
            'success': True,
            'message': f'Multi-Site {"aktiviert" if enabled else "deaktiviert"}.',
            'reloaded': True
        })
        
    except Exception as e:
        logger.error(f"Error saving multi-site config: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
