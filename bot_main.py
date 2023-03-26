import json
import openai
import telebot
from atlassian import Confluence

# Читаем конфиг
with open('config.json', "r", encoding="utf-8") as file:
    config = json.load(file)

BOT_PERSONALITY = config['bot_personality']
SEARCH_QUERY = config['confluence_search_query']
CONFLUENCE_URL = config['confluence_url']

openai.api_key = config['gpt_api_key']

# Подключение к Confluence
confluence = Confluence(
    url=CONFLUENCE_URL,
    username=config['confluence_user'],
    token=config['confluence_api_key']
)

# Подключение к боту
bot = telebot.TeleBot(config['bot_api_key'])


def ask_gpt(income):
    """Функция получения ответа от ChatGPT с учетом заданной в конфиге личности бота"""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": BOT_PERSONALITY},
            {"role": "user", "content": income}
        ]
    )
    reply = response.choices[0].message.content
    return reply


def send_reply(chat_id, message):
    """Функция отправки ответа от ChatGPT в чат с эффектом 'бот пишет'"""
    bot.send_chat_action(chat_id, action='typing')
    reply: str = ask_gpt(message)
    bot.send_message(chat_id, reply)


def cql_search(query, space=None, label=None):
    """Функция поиска по базе знаний с помощью CQL"""
    params = {
        'cql': f'siteSearch ~ "{query}"'
    }
    params['cql'] += f' AND space="{space}"'
    params['cql'] += ' AND type="page"'

    if label:
        params['cql'] += f' AND label="{label}"'

    results = confluence.cql(params['cql'], limit=10)

    return results


def cql_result_parser(results, keywords):
    """Функция приведения результатов поиска CQL к нужному для отправки в чат формату"""
    page_list: str = f'Несколько страниц в тексте которых есть что-то из слов <i>"{keywords}"</i>: \n\n '
    for item in results['results']:
        page: str = f"<b><a href=\"{CONFLUENCE_URL}{item['url']}\">{item['title']}</a></b> \n\n"
        page_list += page

    return page_list


# Триггер на новые сообщения в чате
@bot.message_handler(func=lambda message: True)
def smart_reply(message):
    """Функция ответа через ChatGPT на сообщения с упоминанием бота или поиска в бз"""
    user_id = message.from_user.id
    msg: str = message.text
    space = "AN"
    names = ['Фёдор', 'Федя', 'Федор', '@AnalystsEduBot', ' бот', 'федор', 'федя', 'фёдор', ' Бот']

    if msg[:3] == 'бз!':
        query: str = SEARCH_QUERY + msg[4:]
        keywords: str = ask_gpt(query)
        results = cql_search(keywords, space)
        pretty_results: str = cql_result_parser(results, keywords)
        bot.send_message(message.chat.id, pretty_results, parse_mode="html")

    else:
        for name in names:
            if name in msg:
                send_reply(message.chat.id, msg)
        if message.chat.type == 'private':
            send_reply(user_id, msg)


bot.infinity_polling()
