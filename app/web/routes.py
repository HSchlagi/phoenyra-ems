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
from typing import Dict, Any
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
    return render_template('dashboard.html')


@bp.route('/analytics')
@login_required
def analytics():
    """Analytics & Performance Dashboard"""
    return render_template('analytics.html')


@bp.route('/settings')
@login_required
def settings():
    """System Settings & Configuration"""
    return render_template('settings.html')


@bp.route('/forecasts')
@login_required
def forecasts():
    """Forecasts & Market Data"""
    return render_template('forecasts.html')


@bp.route('/users')
@login_required
@role_required('admin')
def users():
    """Benutzerverwaltung (nur für Admins)"""
    return render_template('users.html')


@bp.route('/help')
@login_required
def help():
    """Hilfe & Anleitungen"""
    return render_template('help.html')


@bp.route('/monitoring')
@login_required
def monitoring():
    """Live Monitoring & Telemetrie"""
    return render_template('monitoring.html')


@bp.route('/mqtt-test')
@login_required
def mqtt_test():
    """MQTT Topic Configuration Test Page"""
    return render_template('mqtt_test.html')


# ============================================================================
# API - State & Real-time
# ============================================================================

@bp.route('/api/state')
@login_required
def api_state():
    """Gibt aktuellen Anlagenzustand zurück"""
    return jsonify(current_app.ems.to_dict())


@bp.route('/api/monitoring/telemetry')
@login_required
def api_monitoring_telemetry():
    """Gibt Telemetrieverlauf zurück"""
    minutes = request.args.get('minutes', 60, type=int)
    limit = request.args.get('limit', 900, type=int)
    
    telemetry = current_app.ems.get_recent_telemetry(minutes=minutes, limit=limit)
    current_state = current_app.ems.to_dict()
    
    return jsonify({
        'data': telemetry,
        'current': current_state
    })


@bp.route('/api/monitoring/powerflow')
@login_required
def api_monitoring_powerflow():
    """Aggregierte Energieflüsse für Sankey-Diagramm"""
    minutes = request.args.get('minutes', 5, type=int)
    power_flow = current_app.ems.get_power_flow(minutes=max(1, minutes))
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
    plan = current_app.ems.get_current_plan()
    
    if plan:
        return jsonify(plan)
    else:
        return jsonify({'error': 'No plan available'}), 404


@bp.route('/api/strategies')
@login_required
def api_strategies():
    """Gibt verfügbare Strategien zurück"""
    strategies = current_app.ems.strategy_manager.get_available_strategies()
    current = current_app.ems.strategy_manager.get_current_strategy()
    
    return jsonify({
        'available': strategies,
        'current': current,
        'mode': current_app.ems.strategy_manager.selection_mode
    })


@bp.route('/api/strategy', methods=['POST'])
@login_required
@role_required('admin')
def api_set_strategy():
    """Setzt manuelle Strategie"""
    data = request.get_json()
    strategy_name = data.get('strategy')
    
    if not strategy_name:
        return jsonify({'error': 'Missing strategy parameter'}), 400
    
    success = current_app.ems.set_manual_strategy(strategy_name)
    
    if success:
        logger.info(f"Strategy manually set to: {strategy_name}")
        return jsonify({'success': True, 'strategy': strategy_name})
    else:
        return jsonify({'error': 'Unknown strategy'}), 400


@bp.route('/api/strategy/auto', methods=['POST'])
@login_required
@role_required('admin')
def api_auto_strategy():
    """Aktiviert automatische Strategiewahl"""
    current_app.ems.strategy_manager.set_auto_mode()
    logger.info("Auto strategy mode activated")
    return jsonify({'success': True, 'mode': 'auto'})


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
    
    try:
        metrics = current_app.ems.history_db.get_daily_metrics(days=days)
        # Wenn keine Metriken vorhanden, berechne sie für heute
        if not metrics:
            try:
                current_app.ems.history_db.calculate_daily_metrics()
                metrics = current_app.ems.history_db.get_daily_metrics(days=days)
            except Exception as calc_err:
                logger.warning(f"Could not calculate daily metrics: {calc_err}")
        return jsonify({'metrics': metrics, 'count': len(metrics)})
    except Exception as e:
        logger.error(f"Error getting daily metrics: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/api/analytics/summary')
@login_required
def api_performance_summary():
    """Gibt Performance-Zusammenfassung zurück"""
    days = request.args.get('days', 30, type=int)
    
    try:
        summary = current_app.ems.history_db.get_performance_summary(days=days)
        # Wenn keine Zusammenfassung vorhanden, berechne Metriken für heute
        if not summary:
            try:
                current_app.ems.history_db.calculate_daily_metrics()
                summary = current_app.ems.history_db.get_performance_summary(days=days)
            except Exception as calc_err:
                logger.warning(f"Could not calculate daily metrics: {calc_err}")
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        return jsonify({'error': str(e)}), 500


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
def api_mqtt_config_get():
    """Get current MQTT configuration"""
    try:
        config = load_config()
        mqtt_config = config.get('mqtt', {})
        return jsonify({
            'success': True,
            'config': mqtt_config
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/mqtt/config', methods=['POST'])
def api_mqtt_config_set():
    """Update MQTT configuration"""
    try:
        config_data = request.get_json()
        
        # Load current config
        config = load_config()
        
        # Update MQTT section
        if 'mqtt' not in config:
            config['mqtt'] = {}
        
        config['mqtt'].update(config_data)
        
        # Save config
        save_config(config)
        
        return jsonify({'success': True, 'message': 'MQTT configuration updated'})
        
    except Exception as e:
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
def api_modbus_config_get():
    """Get current Modbus configuration"""
    try:
        config = load_config()
        modbus_config = config.get('modbus', {})
        profile_key = modbus_config.get('profile')
        profile_details = get_profile(profile_key) if profile_key else None
        profiles = list_profiles()
        return jsonify({
            'success': True,
            'config': modbus_config,
            'profile': profile_details,
            'profiles': profiles
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/modbus/config', methods=['POST'])
def api_modbus_config_set():
    """Update Modbus configuration"""
    try:
        config_data = request.get_json()
        
        # Load current config
        config = load_config()
        
        # Update Modbus section
        if 'modbus' not in config:
            config['modbus'] = {}

        modbus_section: Dict[str, Any] = config['modbus']

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
        
        return jsonify({'success': True, 'message': 'Modbus configuration updated'})
        
    except Exception as e:
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
def api_feedin_limitation_get():
    """Get Feed-in Limitation configuration"""
    try:
        config = load_config()
        feedin_config = config.get('feedin_limitation', {})
        return jsonify({'success': True, 'config': feedin_config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/config/feedin_limitation', methods=['POST'])
def api_feedin_limitation_set():
    """Update Feed-in Limitation configuration"""
    try:
        config_data = request.get_json()
        config = load_config()
        config['feedin_limitation'] = config_data
        save_config(config)
        return jsonify({'success': True, 'message': 'Feed-in limitation configuration updated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/config/grid_connection', methods=['GET'])
def api_grid_connection_get():
    """Get Grid Connection configuration"""
    try:
        config = load_config()
        grid_config = config.get('grid_connection', {})
        return jsonify({'success': True, 'config': grid_config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/config/grid_connection', methods=['POST'])
def api_grid_connection_set():
    """Update Grid Connection configuration"""
    try:
        config_data = request.get_json()
        config = load_config()
        config['grid_connection'] = config_data
        save_config(config)
        return jsonify({'success': True, 'message': 'Grid connection configuration updated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/config/grid_tariffs', methods=['GET'])
@login_required
def api_grid_tariffs_get():
    """Get Grid Tariffs configuration"""
    try:
        config = load_config()
        grid_tariffs_config = config.get('grid_tariffs', {})
        
        # Hole zusätzliche Info vom Service (falls verfügbar)
        tariff_info = {}
        if hasattr(current_app, 'ems') and hasattr(current_app.ems, 'grid_tariff_service'):
            tariff_info = current_app.ems.grid_tariff_service.get_tariff_info()
        
        return jsonify({
            'success': True, 
            'config': grid_tariffs_config,
            'info': tariff_info
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
        config = load_config()
        config['grid_tariffs'] = config_data
        
        # Validiere Konfiguration
        if config_data.get('enabled'):
            if not config_data.get('tariff_structure'):
                return jsonify({'success': False, 'error': 'tariff_structure is required when enabled'}), 400
        
        save_config(config)
        
        # Aktualisiere Service (falls EMS bereits läuft)
        try:
            if hasattr(current_app, 'ems') and hasattr(current_app.ems, 'grid_tariff_service'):
                from services.grid_tariff import GridTariffService
                current_app.ems.grid_tariff_service = GridTariffService(config_data)
                logger.info("Grid tariff service updated")
        except Exception as service_err:
            logger.warning(f"Could not update grid tariff service: {service_err}")
        
        return jsonify({'success': True, 'message': 'Grid tariffs configuration updated'})
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
