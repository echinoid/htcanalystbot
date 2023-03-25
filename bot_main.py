import json
import openai
import telebot

# Читаем конфиг
with open('config.json', "r", encoding="utf-8") as file:
    config = json.load(file)

BOT_CHARACTER = config['bot_character']
SEARCH_QUERY = config['confluence_search_query']

openai.api_key = config['gpt_api_key']

# Подключение к боту
bot = telebot.TeleBot(config['bot_api_key'])


def ask_gpt(income):
    """Функция получения ответа от ChatGPT с учетом характера бота"""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": BOT_CHARACTER},
            {"role": "user", "content": income}
        ]
    )
    return response.choices[0].message.content


def send_reply(chat_id, message):
    """Функция отправки ответа от ChatGPT в чат с эффектом 'бот пишет'"""
    bot.send_chat_action(chat_id, action='typing')
    ask_gpt(message)
    bot.send_message(chat_id, message)


# Триггер на новые сообщения в чате
@bot.message_handler(func=lambda message: True)
def smart_reply(message):
    """Функция ответа через ChatGPT на сообщения с упоминанием бота"""
    user_id = message.from_user.id
    msg: str = message.text
    names = ['Фёдор', 'Федя', 'Федор', '@AnalystsEduBot', ' бот', 'федор', 'федя', 'фёдор', ' Бот']
    for name in names:
        if name in msg:
            send_reply(message.chat.id, msg)

    if message.chat.type == 'private':
        send_reply(user_id, msg)


bot.infinity_polling()
