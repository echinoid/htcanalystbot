import json
import openai
import telebot
from telebot import types
from atlassian import Confluence
import pymysql
from pymysql import cursors

# Читаем конфиг
with open('config.json', "r", encoding="utf-8") as file:
    config = json.load(file)

BOT_PERSONALITY = config['bot_personality']
SEARCH_QUERY = config['confluence_search_query']
CONFLUENCE_URL = config['confluence_url']
SPACE_KEY = "AN"
TAGS_ON_PAGE = 5
MYSQL_DATABASE = 'echinos$htcanalystbot'

openai.api_key = config['gpt_api_key']

# Подключение к Confluence
confluence = Confluence(
    url=CONFLUENCE_URL,
    username=config['confluence_user'],
    token=config['confluence_api_key']
)

# Подключение к боту
bot = telebot.TeleBot(config['bot_api_key'])


# Подключение к БД MySQL
connection = pymysql.connect(
    host=config['mysql_url'],
    user=config['mysql_login'],
    password=config['mysql_pass'],
    database=MYSQL_DATABASE,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)


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


def page_by_tags_result_parser(results):
    """Функция приведения результатов поиска по тэгу к нужному для отправки в чат формату"""
    page_list: str = ''
    for item in results:
        page: str = f"<b><a href=\"{CONFLUENCE_URL}{item['_links']['webui']}\">{item['title']}</a></b> \n\n"
        page_list += page

    return page_list


def send_tags(chat_id: str, tags: list, start: int):
    """Функция вывода в чат списка найденных тегов в виде кнопок с пэджинацией"""
    markup = types.InlineKeyboardMarkup(keyboard=None, row_width=2)
    message = 'Список найденных тегов (нажми на тег чтобы найти все страницы с ним):'
    if len(tags) <= 10:
        for tag in tags:
            button = types.InlineKeyboardButton(text=tag, callback_data=f'tag={tag}')
            markup.add(button)
    else:
        end: int = start + TAGS_ON_PAGE
        for tag in tags[start:end]:
            button = types.InlineKeyboardButton(text=tag, callback_data=f'tag={tag}')
            markup.add(button)
        if len(tags[end:] > 0):
            button_next = types.InlineKeyboardButton(text='Дальше', callback_data={"end": end, "tags": tags})
            markup.add(button_next)
        if start > 0:
            start = start - 5
            button_previous = types.InlineKeyboardButton(text='Назад', callback_data={"start": start, "tags": tags})
            markup.add(button_previous)

    bot.send_message(chat_id, message, reply_markup=markup)


def select_tags():
    """Получение списка тегов из базы"""
    with connection:
        with connection.cursor() as cursor:
            sql = "SELECT tag FROM confluence_tags"
            cursor.execute(sql)
            result = cursor.fetchall()
            result_list = [row['tag'] for row in result]
            result_list.sort()

    return result_list


# Триггеры на команды бота
@bot.message_handler(commands=['tags'])
def tags_list(message):
    """Вывод пользователю списка всех тегов пространства"""
    all_tags: list = select_tags()
    send_tags(message.chat.id, all_tags, 0)


# Триггеры на callback вызовы
@bot.callback_query_handler(func=lambda call: True)
def search_page_for_tag(call):
    chat_id = call.message.chat.id
    if call.data[:4] == 'tag=':
        tag = call.data[4:]
        result_pages = confluence.get_all_pages_by_label(tag)
        if result_pages:
            message = page_by_tags_result_parser(result_pages)
        else:
            message = 'Страницы не найдены'
        bot.send_message(chat_id, message, parse_mode="html")


def tags_pagination(call):
    chat_id = call.message.chat.id
    if call.data['end']:
        send_tags(chat_id, call.data['tags'], call.data['end'])
    if call.data['start']:
        send_tags(chat_id, call.data['tags'], call.data['start'])


# Триггеры на новые сообщения в чате
@bot.message_handler(func=lambda message: True)
def smart_reply(message):
    """Функция ответа через ChatGPT на сообщения с упоминанием бота или поиска в бз"""
    user_id = message.from_user.id
    msg: str = message.text
    names = ['Фёдор', 'Федя', 'Федор', '@AnalystsEduBot', ' бот', 'федор', 'федя', 'фёдор', ' Бот']

    if msg[:3] == 'бз!':
        query: str = SEARCH_QUERY + msg[4:]
        keywords: str = ask_gpt(query)
        results = cql_search(keywords, SPACE_KEY)
        pretty_results: str = cql_result_parser(results, keywords)
        bot.send_message(message.chat.id, pretty_results, parse_mode="html")

    else:
        for name in names:
            if name in msg:
                send_reply(message.chat.id, msg)
        if message.chat.type == 'private':
            send_reply(user_id, msg)


bot.infinity_polling()
