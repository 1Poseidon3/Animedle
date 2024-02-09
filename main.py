import logging
import random
import requests
import datetime
import hashlib

from flask import Flask, request, render_template, jsonify, Response
from jikan4snek import Jikan4SNEK, dump
from bs4 import BeautifulSoup
from pathlib import Path

app = Flask(__name__)

animes_list = []
global_anime_id_chosen = 0
global_anime_title_chosen = ""

@app.route('/')
@app.route('/index')
async def index():
    global global_anime_id_chosen
    global global_anime_title_chosen
    g = 0
    random.seed(get_todays_seed())
    jikan = Jikan4SNEK(debug=True)
    fp = Path('data/anime-id-list.txt')
    if not fp.exists():
        scrape_ids()
    with open('data/anime-id-list.txt', 'r') as file:
        animes = [int(line) for line in file.readlines()]
    animes = animes[:10]
    solution_anime_index_chosen = random.randint(0, len(animes) - 1)
    global_anime_id_chosen = animes[solution_anime_index_chosen]
    for i in animes:
        if g == 10:
            break
        anime = await jikan.get(i).anime()
        animes_list.append(anime['data']['titles'])
        g += 1
    global_anime_title_chosen = animes_list[solution_anime_index_chosen][0]['title']
    return render_template('index.html', Title='Welcome', Anime_ID=global_anime_id_chosen, Anime_Title=global_anime_title_chosen, Seed=get_todays_seed())


@app.route('/get_dropdown_options', methods=['POST'])
def get_dropdown_options():
    user_input = request.form.get('user_input', '').lower()
    options = list(set([anime2[0]['title'] for anime2 in animes_list for title_obj in anime2 if user_input in title_obj['title'].lower()]))
    if len(user_input) == 0:
        options = []
    return jsonify(sorted(options))


@app.route('/submit', methods=['POST'])
def submit():
    chosen = request.form.get('dropdown')
    if chosen.lower() == global_anime_title_chosen.lower():
        return jsonify(message="Yes!", won=True)
    else:
        return jsonify(message="Not yet...", won=False)


def scrape_ids():
    i = 0
    with open('data/anime-id-list.txt', 'w+') as file:
        while i != 1000:
            j = -1
            res = requests.get('https://myanimelist.net/topanime.php?type=bypopularity&limit={}'.format(i))
            soup = BeautifulSoup(res.content, 'html.parser')
            for row in soup.find_all('a', class_='hoverinfo_trigger'):
                j += 1
                if j % 2 != 0:
                    continue
                text = str(row)[79:]
                index2 = text.index('/')
                text = text[:index2]
                print(text, file=file)
            i += 50


def get_todays_seed():
    today = datetime.date.today().strftime('%Y%m%d')
    seed = int(hashlib.sha256(today.encode('utf-8')).hexdigest(), 16) % 10 ** 8
    return seed


app.run(host='0.0.0.0', port=81)
