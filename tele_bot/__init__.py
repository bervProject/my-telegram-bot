from pdf2image import convert_from_bytes
from telebot.types import InputMediaPhoto
from flask import Flask, request, render_template
import io
import os
import uuid
import zipfile
import errno
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

@bot.message_handler(commands=['start','help'])
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
    logger.info('get message {},{} from {} with file {}'.format(message_id, chat_id, user_id, file_id))
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
        image_name = 'temp/{}/{}/output-{}.jpg'.format(user_id, current_uuid, num)
        if not os.path.exists(os.path.dirname(image_name)):
            try:
                os.makedirs(os.path.dirname(image_name))
            except OSError as exc: # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        image.save(image_name, format='JPEG')
        list_location.append(image_name)
    return list_location

def create_app(test_config = None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key')
    )

    @app.route('/' + token, methods=['POST'])
    def getMessage():
        bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
        return "!", 200

    @app.route("/reset-hook")
    def webhook():
        bot.remove_webhook()
        bot.set_webhook(url=public_url + token)
        return render_template('success-reset.html')

    @app.route("/", methods=['GET'])
    def home():
        return render_template('index.html')

    return app