from functools import wraps
from flask import session, redirect, url_for, request, abort

def login_required(f):
    @wraps(f)
    def wrapper(*a,**k):
        if not session.get('user'):
            return redirect(url_for('web.login', next=request.path))
        return f(*a,**k)
    return wrapper

def role_required(*roles):
    def deco(f):
        @wraps(f)
        def w(*a,**k):
            user=session.get('user');
            if not user or user.get('role') not in roles: return abort(403)
            return f(*a,**k)
        return w
    return deco
