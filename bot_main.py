#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from openai import OpenAI
import telebot
import re

# Читаем конфиг
with open('config.json', "r", encoding="utf-8") as file:
    config = json.load(file)

client = OpenAI(api_key=config['gpt_api_key'])
bot = telebot.TeleBot(config['bot_api_key'])

BOT_PERSONALITY = config['bot_personality']


def escape_markdown_v2(text):
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)


def ask_gpt(income):
    """Функция получения ответа от ChatGPT с учетом заданной в конфиге личности бота"""
    response = client.chat.completions.create(model="gpt-4o",
                                              messages=[
                                                  {"role": "system", "content": BOT_PERSONALITY},
                                                  {"role": "user", "content": income}
                                              ])
    reply = response.choices[0].message.content
    return reply


def send_reply(chat_id, message, noreply: False):
    """Функция отправки ответа от ChatGPT в чат с эффектом 'бот пишет'"""
    if noreply:
        return
    bot.send_chat_action(chat_id, action='typing')
    reply: str = ask_gpt(message)
    bot.send_message(chat_id, escape_markdown_v2(reply), parse_mode='MarkdownV2')


def generate_image(chat_id, prompt):
    """Функция генерации изображения по запросу пользователя"""
    bot.send_chat_action(chat_id, action='typing')
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size='1024x1024',
        quality='standard',
        n=1
    )
    image_url = response.data[0].url
    return image_url


def handle_image(message):
    """Функция для обработки изображений, отправленных пользователем"""
    file_id = message.photo[-1].file_id
    prompt = message.caption
    file_info = bot.get_file(file_id)
    file_path = file_info.file_path
    file_url = f"https://api.telegram.org/file/bot{config['bot_api_key']}/{file_path}"

    content = [
        {
            "type": "text",
            "text": prompt
        },
        {
            "type": "image_url",
            "image_url": {
                "url": file_url
            }
        }
    ]

    return content


# Триггеры на новые сообщения в чате
@bot.message_handler(func=lambda message: True, content_types=['photo', 'text'])
def smart_reply(message):
    """Функция ответа через ChatGPT"""
    user_id = message.from_user.id
    noreply: bool = False

    if message.content_type == 'photo':
        # Обрабатываем полученное изображение
        content = handle_image(message)
    else:
        # Обрабатываем текстовое сообщение
        content = message.text

        if message.from_user.username:
            with open("log.log", "a") as f:
                print(message.from_user.username + ' - ' + content + '\n', file=f)

        if content.startswith("/generate"):
            noreply = True
            # Генерация изображения по запросу
            prompt = content.replace("/generate", "").strip()
            if prompt:
                image_url = generate_image(user_id, prompt)
                bot.send_photo(user_id, image_url)
            else:
                bot.send_message(user_id,
                                 "Пожалуйста, укажите запрос для генерации изображения после команды /generate")

    send_reply(user_id, content, noreply)


bot.infinity_polling()
