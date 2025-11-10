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
        
        for usr in current_app.users:
            if usr.get('username') == u and usr.get('password') == p:
                session['user'] = {
                    'name': u,
                    'role': usr.get('role', 'viewer')
                }
                logger.info(f"User logged in: {u}")
                return redirect(request.args.get('next') or url_for('web.dashboard'))
        
        logger.warning(f"Failed login attempt for user: {u}")
        return render_template('login.html', error='Ungültige Anmeldedaten')
    
    return render_template('login.html')


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

        return jsonify({
            'success': True,
            'profiles': list_profiles()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
