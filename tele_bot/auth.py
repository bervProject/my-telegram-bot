from flask import Blueprint, session, request, render_template, redirect, url_for
from flask_login import current_user, login_user, logout_user
from tele_bot.config import Config
from tele_bot.model import User
import uuid
import msal

auth = Blueprint('auth', __name__, static_folder='templates')

def _load_cache():
    cache = msal.SerializableTokenCache()
    if session.get('token_cache'):
        cache.deserialize(session['token_cache'])
    return cache


def _save_cache(cache):
    if cache.has_state_changed:
        session['token_cache'] = cache.serialize()


def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        Config.CLIENT_ID, authority=authority or Config.AUTHORITY,
        client_credential=Config.CLIENT_SECRET, token_cache=cache)


def _build_auth_url(authority=None, scopes=None, state=None):
    return _build_msal_app(authority=authority).get_authorization_request_url(
        scopes or [],
        state=state or str(uuid.uuid4()),
        redirect_uri=url_for('auth.authorized', _external=True, _scheme='https'))


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('/'))
    session['state'] = str(uuid.uuid4())
    # Note: Below will return None as an auth_url until you implement the function
    auth_url = _build_auth_url(scopes=Config.SCOPE, state=session['state'])
    return render_template('login.html', title='Sign In', auth_url=auth_url)


@auth.route('/logout')
def logout():
    logout_user()  # Log out of Flask session
    if session.get('user'):  # Used MS Login
        # Wipe out user and its token cache from session
        session.clear()
        return redirect(
            Config.AUTHORITY + '/oauth2/v2.0/logout' +
            '?post_logout_redirect_uri=' + url_for('auth.login', _external=True))
    return redirect(url_for('auth.login'))


@auth.route('/oauth-msal')
def authorized():
    if request.args.get('state') != session.get('state'):
        return redirect(url_for('/'))  # Failed, go back home
    if 'error' in request.args:  # Authentication/Authorization failure
        return render_template('auth_error.html', result=request.args)
    if request.args.get('code'):
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_authorization_code(
            request.args['code'],
            scopes=Config.SCOPE,
            redirect_uri=url_for('auth.authorized', _external=True, _scheme='https'))
        if 'error' in result:
            return render_template('auth_error.html', result=result)
        session['user'] = result.get('id_token_claims')
        # Note: In a real app, use the appropriate user's DB ID below,
        #   but here, we'll just log in with a fake user zero
        #   This is so flask login functionality works appropriately.
        user = User(0)
        login_user(user)
        _save_cache(cache)
        return redirect(url_for('home'))
