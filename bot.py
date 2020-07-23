from telebot import TeleBot
from urllib.parse import urlparse
from requests import get
from bs4 import BeautifulSoup
import schedule
from multiprocessing import Process
from os import makedirs
from os.path import exists
from time import sleep


from config import *


if not exists('data'):
    makedirs('data')

bot = TeleBot(TOKEN)


def parse_all():
    for source in get_sources():
        domain = urlparse(source).netloc
        if 'avito' in domain:
            parse_avito(source)
        elif 'drom' in domain:
            parse_drom(source)
        elif 'auto' in domain:
            parse_auto(source)


schedule.every(FREQUENCY).minutes.do(parse_all)


@bot.message_handler(commands=['start'])
def start_message(message):
    users = get_users()
    if message.chat.id not in users:
        with open('data/users.txt', mode='a') as f:
            f.write(str(message.chat.id) + '\n')
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
    with open('data/sources.txt', mode='a') as f:
        f.write(link + '\n')
    bot.send_message(message.chat.id, 'Ссылка успешно добавлена.')
    domain = urlparse(link).netloc
    if 'avito' in domain:
        parse_avito(link, init=True)
    elif 'drom' in domain:
        parse_drom(link, init=True)
    elif 'auto' in domain:
        parse_auto(link, init=True)


def get_sources():
    if not exists('data/sources.txt'):
        open('data/sources.txt', mode='w').close()
    with open('data/sources.txt', mode='r') as f:
        return [i.rstrip('\n') for i in f.readlines()]


def get_was():
    if not exists('data/was.txt'):
        open('data/was.txt', mode='w').close()
    with open('data/was.txt', mode='r') as f:
        return [i.rstrip('\n') for i in f.readlines()]


def update_was(urls):
    with open('data/was.txt', mode='a') as f:
        f.write('\n'.join(urls))
        if urls:
            f.write('\n')

def get_users():
    if not exists('data/users.txt'):
        open('data/users.txt', mode='w').close()
    with open('data/users.txt', mode='r') as f:
        return [int(i.rstrip('\n')) for i in f.readlines()]


def routine():
    while True:
        schedule.run_pending()
        sleep(1)


def start_process():
    p1 = Process(target=routine, args=())
    p1.start()


def parse_avito(search_url, init=False):
    was = get_was()
    ALLOWED_OPTIONS = ['Модификация', 'Пробег', 'Год выпуска', 'Поколение', 'Владельцев по ПТС', 'Комплектация']
    r = get(search_url)
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    elements = soup.findAll('a', itemprop='url')
    urls = []
    res = []
    for el in elements:
        url = 'https://www.avito.ru' + el['href']
        if url in was:
            continue
        urls.append(url)
        if not init:
            r = get(url)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            name = soup.find('span', class_='title-info-title-text').text
            options = [option.text.strip().replace('\xa0', ' ') for option in filter(lambda x: ''.join(ALLOWED_OPTIONS).find(x.text.split()[0].rstrip(':')) != -1, soup.findAll('li', class_='item-params-list-item'))]
            for user in get_users():
                bot.send_message(user, '{}\n{}\n{}'.format(name, '\n'.join(options), url))
    update_was(urls)


def parse_drom(search_url, init=False):
    was = get_was()
    r = get(search_url)
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    elements = soup.findAll('span', attrs={'data-ftid': 'bull_title'})
    urls = []
    res = []
    for el in elements:
        url = el.findParent('a')['href']
        if url in was:
            continue
        urls.append(url)
        if not init:
            r = get(url)
            if r.status_code != 200:
                continue
            name = el.text
            soup = BeautifulSoup(r.text, 'html.parser')
            for user in get_users():
                bot.send_message(user, '{}\n{}'.format(name, url))
    update_was(urls)


def parse_auto(search_url, init=False):
    was = get_was()
    r = get(search_url)
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    elements = soup.findAll('a', class_='Link ListingItemTitle-module__link')
    urls = []
    res = []
    for el in elements:
        url = el['href']
        if url in was:
            continue
        urls.append(url)
        if not init:
            r = get(url)
            if r.status_code != 200:
                continue
            name = el.text
            soup = BeautifulSoup(r.text, 'html.parser')
            for user in get_users():
                bot.send_message(user, '{}\n{}'.format(name, url))
    update_was(urls)


if __name__ == '__main__':
    start_process()
    try:
        bot.polling(none_stop=True)
    except:
        pass
