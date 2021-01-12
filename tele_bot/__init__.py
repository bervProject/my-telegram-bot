from pdf2image import convert_from_bytes
from telebot.types import InputMediaPhoto
from flask import Flask, request, redirect, session, render_template, url_for
from flask_login import current_user, login_user, logout_user, login_required, LoginManager
from flask_session import Session
from tele_bot.config import Config
from tele_bot.model import User
import io
import os
import uuid
import zipfile
import errno
import msal
import telebot
import logging

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)
token = os.environ.get("TELEGRAM_TOKEN", "")
public_url = os.environ.get("PUBLIC_URL", "http://localhost:5000")
bot = telebot.TeleBot(token)


def test_pdf(message):
    if message is None:
        return False
    if message.document is None:
        return False
    return message.document.mime_type == 'application/pdf'


@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    bot.reply_to(message, 'Please upload .pdf file to use this bot')


@bot.message_handler(content_types=['photo', 'audio', 'sticker'])
def not_supported_yet(message):
    bot.reply_to(message, 'Sorry, we not supported this yet')


@bot.message_handler(func=test_pdf, content_types=['document'])
def handle_message_doc(message):
    chat_id = message.chat.id
    message_id = message.message_id
    user_id = message.from_user.id
    file_id = message.document.file_id
    logger.info('get message {},{} from {} with file {}'.format(
        message_id, chat_id, user_id, file_id))
    file_info = bot.get_file(file_id)
    doc_downloaded = bot.download_file(file_info.file_path)
    medias_plain = convert_pdf(doc_downloaded, user_id)
    open_file_list = [open(x, 'rb') for x in medias_plain]
    medias = [InputMediaPhoto(x) for x in open_file_list]
    bot.send_media_group(chat_id, medias, reply_to_message_id=message_id)
    # close the files
    for file in open_file_list:
        file.close()
    # remove the files
    for media in medias_plain:
        os.remove(media)


def convert_pdf(pdf_byte, user_id):
    images = convert_from_bytes(pdf_byte, fmt="jpeg")
    print(len(images))
    current_uuid = uuid.uuid4()
    list_location = []
    for num, image in enumerate(images):
        image_name = 'temp/{}/{}/output-{}.jpg'.format(
            user_id, current_uuid, num)
        if not os.path.exists(os.path.dirname(image_name)):
            try:
                os.makedirs(os.path.dirname(image_name))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        image.save(image_name, format='JPEG')
        list_location.append(image_name)
    return list_location


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
        redirect_uri=url_for('authorized', _external=True, _scheme='https'))


def create_app(test_config=None):
    app = Flask(__name__)
    app.logger.setLevel(logging.DEBUG)
    app.config.from_object(Config)
    Session(app)
    login = LoginManager(app)
    login.login_view = 'login'

    @login.user_loader
    def load_user(id):
        # Normally, Flask would have you check your DB for the user ID
        # We're just allowing any authenticated user in for now
        return User(0)

    @app.route('/' + token, methods=['POST'])
    def getMessage():
        bot.process_new_updates(
            [telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
        return "!", 200

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('/'))
        session['state'] = str(uuid.uuid4())
        # Note: Below will return None as an auth_url until you implement the function
        auth_url = _build_auth_url(scopes=Config.SCOPE, state=session['state'])
        return render_template('login.html', title='Sign In', auth_url=auth_url)

    @app.route('/logout')
    def logout():
        logout_user()  # Log out of Flask session
        if session.get('user'):  # Used MS Login
            # Wipe out user and its token cache from session
            session.clear()
            return redirect(
                Config.AUTHORITY + '/oauth2/v2.0/logout' +
                '?post_logout_redirect_uri=' + url_for('login', _external=True))
        return redirect(url_for('login'))

    @app.route('/oauth-msal')
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
                redirect_uri=url_for('authorized', _external=True, _scheme='https'))
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

    @app.route("/reset-hook")
    @login_required
    def webhook():
        app.logger.debug('Someone call reset hook')
        app.logger.debug('Try to remove hook from bot')
        bot.remove_webhook()
        app.logger.debug('Setup new webhook to: ' + public_url)
        bot.set_webhook(url=public_url + token)
        app.logger.debug('Finished setup webhook to: ' + public_url)
        return render_template('success-reset.html')

    @app.route("/home", methods=['GET'])
    def home():
        return render_template('home.html')

    @app.route("/", methods=['GET'])
    def index():
        return render_template('index.html')

    return app
