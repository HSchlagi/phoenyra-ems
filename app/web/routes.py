"""
Phoenyra EMS - Web Routes
Flask Blueprint mit allen Web- und API-Endpunkten
"""

from flask import Blueprint, render_template, jsonify, request, current_app, Response, redirect, url_for, session, send_from_directory
from auth.security import login_required, role_required
import json
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('web', __name__)


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


# ============================================================================
# API - State & Real-time
# ============================================================================

@bp.route('/api/state')
@login_required
def api_state():
    """Gibt aktuellen Anlagenzustand zurück"""
    return jsonify(current_app.ems.to_dict())


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
