import random
import requests
import datetime
import hashlib

from flask import Flask, request, render_template, jsonify
from jikan4snek import Jikan4SNEK
from bs4 import BeautifulSoup
from pathlib import Path

app = Flask(__name__)

anime_list = []
global_anime_id_chosen = 0
global_anime_title_chosen = ""
global_info_boxes_data = ""

RANK_TOLERANCE = 25
SCORE_TOLERANCE = 0.50
POPULARITY_TOLERANCE = 10
MEMBERS_TOLERANCE = 100000
CACHE_LIFETIME = 43830
LIMIT_ANIME = 25  # For debugging

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
    jikan = Jikan4SNEK(
        debug=True,
        expire_cache=CACHE_LIFETIME
    )
    fp = Path('data/anime-id-list.txt')
    # If the file containing the IDs doesn't exist, create it by scraping the web pages using BeautifulSoup
    if not fp.exists():
        scrape_ids()
    # Read all the IDs into a list
    with open('data/anime-id-list.txt', 'r') as file:
        anime_ids_from_file = [int(line) for line in file.readlines()]
    # This is for testing. We only want the first 10 for now
    anime_ids_from_file = anime_ids_from_file[:LIMIT_ANIME]
    # Choose a random anime to be the answer
    solution_anime_index_chosen = random.randint(0, len(anime_ids_from_file) - 1)
    global_anime_id_chosen = anime_ids_from_file[solution_anime_index_chosen]
    # Hit the Jikan API to get the anime's title
    for i in anime_ids_from_file:
        if g == LIMIT_ANIME:
            break
        anime = await jikan.get(i).anime()
        anime_list.append(anime['data']['titles'])
        g += 1
    global_anime_title_chosen = anime_list[solution_anime_index_chosen][0]['title']
    return render_template('index.html',
                           Title='Welcome',
                           Anime_ID=global_anime_id_chosen,
                           Anime_Title=global_anime_title_chosen,
                           Seed=get_todays_seed())


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
    global global_info_boxes_data
    jikan = Jikan4SNEK()
    chosen = request.form.get('dropdown')
    answer_data = extract_from_data(await jikan.search(chosen, limit=1).anime())
    answer_rank = answer_data[0]
    answer_score = answer_data[1]
    answer_popularity = answer_data[2]
    answer_members = answer_data[3]
    answer_year = answer_data[4]
    answer_season = answer_data[5]
    answer_studios = []
    for studio in answer_data[6]:
        answer_studios.append(studio)
    answer_genres = []
    for genre in answer_data[7]:
        answer_genres.append(genre)
    answer_themes = []
    for theme in answer_data[8]:
        answer_themes.append(theme)
    answer_rating = answer_data[9]
    answer_source = answer_data[10]
    answer_id = answer_data[11]
    correct_data = extract_from_data(await jikan.search(global_anime_title_chosen, limit=1).anime())
    color_data = []
    if answer_id == global_anime_id_chosen:
        color_data = ["green", "green", "green", "green", "green", "green", "green", "green"]
    else:
        color_data = check_answer_data_closeness(answer_data, correct_data)
    global_info_boxes_data = render_template('addBoxesOnAnswer.html',
                                             answer_data=answer_data,
                                             answer_rank=answer_rank,
                                             answer_score=answer_score,
                                             answer_popularity=answer_popularity,
                                             answer_members=answer_members,
                                             answer_year=answer_year,
                                             answer_season=answer_season,
                                             answer_studios=answer_studios,
                                             answer_genres=answer_genres,
                                             answer_themes=answer_themes,
                                             answer_rating=answer_rating,
                                             answer_source=answer_source,
                                             score_color=color_data[0],
                                             members_color=color_data[1],
                                             air_color=color_data[2],
                                             studios_color=color_data[3],
                                             genres_color=color_data[4],
                                             themes_color=color_data[5],
                                             rating_color=color_data[6],
                                             source_color=color_data[7])
    if chosen.lower() == global_anime_title_chosen.lower():
        return jsonify(message="Yes!")
    else:
        return jsonify(message="Not yet...")


# This method is called to add the boxes to the page
@app.route('/append_boxes', methods=['GET'])
def append_boxes():
    global global_info_boxes_data
    return jsonify(info_boxes=global_info_boxes_data)


def extract_from_data(answer_data):
    answer_data_extracted = []
    answer_data_extracted.append(answer_data['data'][0]['rank'])
    answer_data_extracted.append(answer_data['data'][0]['score'])
    answer_data_extracted.append(answer_data['data'][0]['popularity'])
    answer_data_extracted.append(answer_data['data'][0]['members'])
    answer_data_extracted.append(answer_data['data'][0]['aired']['prop']['from']['year'])
    answer_data_extracted.append(answer_data['data'][0]['season'].capitalize())
    answer_studios = []
    for studio in answer_data['data'][0]['studios']:
        answer_studios.append(studio['name'])
    answer_data_extracted.append(answer_studios)
    answer_genres = []
    for genre in answer_data['data'][0]['genres']:
        answer_genres.append(genre['name'])
    answer_data_extracted.append(answer_genres)
    answer_themes = []
    for theme in answer_data['data'][0]['themes']:
        answer_themes.append(theme['name'])
    answer_data_extracted.append(answer_themes)
    answer_data_extracted.append(answer_data['data'][0]['rating'])
    answer_data_extracted.append(answer_data['data'][0]['source'])
    answer_data_extracted.append(answer_data['data'][0]['mal_id'])
    return answer_data_extracted


def check_answer_data_closeness(answer_data, correct_data):
    color_data = []
    if abs(answer_data[1] - correct_data[1]) <= SCORE_TOLERANCE or abs(answer_data[0] - correct_data[0]) <= RANK_TOLERANCE:
        color_data.append("yellow")
    elif answer_data[1] == correct_data[1]:
        color_data.append("green")
    else:
        color_data.append("red")
    if abs(answer_data[3] - correct_data[3]) <= MEMBERS_TOLERANCE or abs(answer_data[2] - correct_data[2]) <= POPULARITY_TOLERANCE:
        color_data.append("yellow")
    elif answer_data[3] == correct_data[3]:
        color_data.append("green")
    else:
        color_data.append("red")
    if answer_data[4] == correct_data[4]:
        if answer_data[5] == correct_data[5]:
            color_data.append("green")
        else:
            color_data.append("yellow")
    else:
        color_data.append("red")
    at_least_one_studio = False
    for studio in answer_data[6]:
        if studio in correct_data[6]:
            at_least_one_studio = True
    if at_least_one_studio:
        if answer_data[6] == correct_data[6]:
            color_data.append("green")
        else:
            color_data.append("yellow")
    else:
        color_data.append("red")
    at_least_one_genre = False
    for genre in answer_data[7]:
        if genre in correct_data[7]:
            at_least_one_genre = True
    if at_least_one_genre:
        if answer_data[7] == correct_data[7]:
            color_data.append("green")
        else:
            color_data.append("yellow")
    else:
        color_data.append("red")
    at_least_one_theme = False
    for theme in answer_data[8]:
        if theme in correct_data[8]:
            at_least_one_theme = True
    if at_least_one_theme:
        if answer_data[8] == correct_data[8]:
            color_data.append("green")
        else:
            color_data.append("yellow")
    else:
        color_data.append("red")
    if answer_data[9] == correct_data[9]:
        color_data.append("green")
    else:
        color_data.append("red")
    if answer_data[10] == correct_data[10]:
        color_data.append("green")
    else:
        color_data.append("red")
    return color_data


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
