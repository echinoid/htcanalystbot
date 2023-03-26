from atlassian import Confluence
import json
import pymysql
from pymysql import cursors


# Читаем конфиг
with open('config.json', "r", encoding="utf-8") as file:
    config = json.load(file)

MYSQL_DATABASE = 'echinos$htcanalystbot'
CONFLUENCE_URL = config['confluence_url']
SPACE_KEY = "AN"

# Подключение к Confluence
confluence = Confluence(
    url=CONFLUENCE_URL,
    username=config['confluence_user'],
    token=config['confluence_api_key']
)


# Подключение к БД MySQL
connection = pymysql.connect(
    host=config['mysql_url'],
    user=config['mysql_login'],
    password=config['mysql_pass'],
    database=MYSQL_DATABASE,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)


def search_tags() -> list:
    """Поиск тегов в пространстве Analyst базы знаний"""
    tags: list = []
    space_pages = confluence.get_all_pages_from_space(SPACE_KEY, limit=1000)
    for page in space_pages:
        page_tags = confluence.get_page_labels(page['id'])
        if len(page_tags['results']) > 0:
            for page_tag in page_tags['results']:
                tags.append(page_tag['name'])

    unique_tags = list(set(tags))
    unique_tags.sort()
    return unique_tags


def db_tag_list_update(tags: list):
    """Обновление списка тегов в БД"""
    with connection:
        with connection.cursor() as cursor:
            sql = "SELECT tag FROM confluence_tags"
            cursor.execute(sql)
            result = cursor.fetchall()
            result_list = [row[0] for row in result]

        not_in_db_list = [tag for tag in tags if tag not in result_list]
        for tag in not_in_db_list:
            with connection.cursor() as cursor:
                sql = f"INSERT INTO confluence_tags (tag) VALUES ('{tag}')"
                cursor.execute(sql)

        connection.commit()

        not_in_confluence_list = [item for item in result_list if item not in tags]
        for item in not_in_confluence_list:
            if item not in tags:
                with connection.cursor() as cursor:
                    sql = f"DELETE FROM confluence_tags WHERE tag = '{item}'"
                    cursor.execute(sql)

        connection.commit()


def main():
    """Основной метод джобы"""
    tags: list = search_tags()
    db_tag_list_update(tags)


main()
