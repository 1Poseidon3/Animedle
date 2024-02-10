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

anime_list = []
global_anime_id_chosen = 0
global_anime_title_chosen = ""

# Main page
@app.route('/')
@app.route('/index')
async def index():
    global global_anime_id_chosen
    global global_anime_title_chosen
    # This is a test variable to prevent it from actually trying to load the top 1000 anime during testing
    g = 0
    # This gets a new anime ID every day for a daily challenge
    random.seed(get_todays_seed())
    jikan = Jikan4SNEK(debug=True)
    fp = Path('data/anime-id-list.txt')
    # If the file containing the IDs doesn't exist, create it by scraping the web pages using BeautifulSoup
    if not fp.exists():
        scrape_ids()
    # Read all the IDs into a list
    with open('data/anime-id-list.txt', 'r') as file:
        anime_ids_from_file = [int(line) for line in file.readlines()]
    # This is for testing. We only want the first 10 for now
    anime_ids_from_file = anime_ids_from_file[:10]
    # Choose a random anime to be the answer
    solution_anime_index_chosen = random.randint(0, len(anime_ids_from_file) - 1)
    global_anime_id_chosen = anime_ids_from_file[solution_anime_index_chosen]
    # Hit the Jikan API to get the anime's title
    for i in anime_ids_from_file:
        if g == 10:
            break
        anime = await jikan.get(i).anime()
        anime_list.append(anime['data']['titles'])
        g += 1
    global_anime_title_chosen = anime_list[solution_anime_index_chosen][0]['title']
    return render_template('index.html', Title='Welcome', Anime_ID=global_anime_id_chosen, Anime_Title=global_anime_title_chosen, Seed=get_todays_seed())


# Runs when the user types anything in the search text box
@app.route('/get_dropdown_options', methods=['POST'])
def get_dropdown_options():
    # Get user input to a string
    user_input = request.form.get('user_input', '').lower()
    # Check to see if the user's input is contained in any of the titles listed for the anime
    # (including alternate titles and languages)
    options = list(set([anime2[0]['title'] for anime2 in anime_list for title_obj in anime2 if user_input in title_obj['title'].lower()]))
    # If nothing is typed, show no options
    if len(user_input) == 0:
        options = []
    # Return the options to display them
    return jsonify(sorted(options))


# Runs when the user submits an answer
@app.route('/submit', methods=['POST'])
async def submit():
    jikan = Jikan4SNEK()
    chosen = request.form.get('dropdown')
    answer_data = await jikan.search(chosen).anime()
    if chosen.lower() == global_anime_title_chosen.lower():
        return jsonify(message="Yes!", won=True)
    else:
        return jsonify(message="Not yet...", won=False)


# Runs when we need to scrap the IDs of the top 1000 anime. This # is hard coded but can be changed in the future
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


# This method chooses a seed for the anime of the day based on today's date
def get_todays_seed():
    today = datetime.date.today().strftime('%Y%m%d')
    seed = int(hashlib.sha256(today.encode('utf-8')).hexdigest(), 16) % 10 ** 8
    return seed


# Website IP and port. 0.0.0.0 = localhost. Type localhost:81 in web browser
app.run(host='0.0.0.0', port=81)
