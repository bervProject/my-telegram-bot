from pdf2image import convert_from_bytes
from telebot import types
import io
import os
import uuid
import zipfile
import errno
import telebot
import logging

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)
token = os.environ["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(token)

def test_pdf(message):
    return message.document.mime_type == 'application/pdf'

@bot.message_handler(commands=['start','help'])
def handle_start_help(message):
    bot.reply_to(message, 'Please upload .pdf file to use this bot')

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
    medias = [types.InputMediaPhoto(x) for x in medias_plain]
    bot.send_media_group(chat_id, medias, reply_to_message_id=message_id)
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

bot.polling()
