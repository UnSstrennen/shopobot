from telebot import TeleBot
from urllib.parse import urlparse
from requests import get
from bs4 import BeautifulSoup
import schedule
from multiprocessing import Process
from os import makedirs
from os.path import exists
from time import sleep
import json


from config import *


bot = TeleBot(TOKEN)

if not exists('data.json'):
    with open('data.json', mode='w') as f:
        json.dump({}, f)


def parse_all():
    with open('data.json', mode='r') as f:
        data = json.load(f)
    for chat_id in data:
        for search_url in data[chat_id]:
            parse_avito(search_url, chat_id, data[chat_id][search_url])


schedule.every(FREQUENCY).minutes.do(parse_all)


@bot.message_handler(commands=['start'])
def start_message(message):
    users = get_users()
    if message.chat.id not in users:
        with open('data.json', mode='r') as f:
            data = json.load(f)
        if message.chat.id not in data:
            data[str(message.chat.id)] = {}
        with open('data.json', mode='w') as f:
            data = json.dump(data, f)
    bot.send_message(message.chat.id, 'Отправьте мне ссылки (одно сообщение - одна ссылка на поисковый запрос, за которым я должен следить).')


@bot.message_handler(content_types=['text'])
def new_link(message):
    link = message.text
    try:
        r = get(link)
        r.raise_for_status()
    except Exception as e:
        print(e)
        bot.send_message(message.chat.id, 'Ссылка не работает или произошла ошибка. Проверьте ссылку.')
        return
    with open('data.json', mode='r') as f:
        data = json.load(f)
    if link not in data[str(message.chat.id)]:
        data[str(message.chat.id)][link] = []
    with open('data.json', mode='w') as f:
        json.dump(data, f)
    bot.send_message(message.chat.id, 'Ссылка успешно добавлена.')
    domain = urlparse(link).netloc
    if 'avito' in domain:
        parse_avito(link, str(message.chat.id))


def update_was(chat_id, search_url, was):
    with open('data.json', mode='r') as f:
        data = json.load(f)
    data[chat_id][search_url] += was
    with open('data.json', mode='w') as f:
        json.dump(data, f)

def get_users():
    with open('data.json', mode='r') as f:
        return json.load(f).keys()


def routine():
    while True:
        schedule.run_pending()
        sleep(1)


def start_process():
    p1 = Process(target=routine, args=())
    p1.start()


def parse_avito(search_url, chat_id, *args):
    init = True
    new_links = []
    was = []
    if args:
        was = args[0]
        init = False
    r = get(search_url)
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    elements = soup.findAll('a', itemprop='url')
    for el in elements:
        url = 'https://www.avito.ru' + el['href']
        if url in was:
            continue
        if not init:
            r = get(url)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            name = soup.find('span', class_='title-info-title-text').text
            bot.send_message(int(chat_id), '{}\n{}'.format(name, url))
        new_links.append(url)
    update_was(chat_id, search_url, new_links)


if __name__ == '__main__':
    start_process()
    try:
        bot.polling(none_stop=True)
    except:
        pass
