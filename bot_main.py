import json
import openai
import telebot
from telebot import types

# Читаем конфиг
with open('config.json', "r", encoding="utf-8") as file:
    config = json.load(file)

openai.api_key = config['gpt_api_key']

# Подключение к боту
bot = telebot.TeleBot(config['bot_api_key'])


# Функция для запроса GPT
def ask_gpt(income):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are helpful assistant in telegram chat for business and system analysts"},
            {"role": "user", "content": income}
        ]
    )
    return response.choices[0].message.content


def send_reply(chat_id, message, smart:bool):
    bot.send_chat_action(chat_id, action='typing')
    if smart:
        reply = ask_gpt(message)
    else:
        reply = message
    bot.send_message(chat_id, reply)


@bot.message_handler(func=lambda message: True)
def smart_reply(message):
    user_id = message.from_user.id
    msg = message.text
    reply: str
    names = ['Фёдор', 'Федя', 'Федор', '@AnalystsEduBot', 'бот', 'федор', 'федя', 'фёдор', 'Бот']
    for name in names:
        if name in msg:
            send_reply(message.chat.id, msg, smart=True)
    if message.chat.type == 'private':
        send_reply(user_id, msg, smart=True)


bot.infinity_polling()
