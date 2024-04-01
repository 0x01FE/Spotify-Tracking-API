import os
import sqlite3
import configparser

import flask
import sqlparse
import spotipy

# SETUP
config = configparser.ConfigParser()
config.read("config.ini")

## SPOTIPY
CLIENT_ID = config["SPOTIFY"]["CLIENT_ID"]
CLIENT_SECRET = config["SPOTIFY"]["CLIENT_SECRET"]
REDIRECT_URI = config["SPOTIFY"]["REDIRECT_URI"]

os.environ["SPOTIPY_CLIENT_ID"] = CLIENT_ID
os.environ["SPOTIPY_CLIENT_SECRET"] = CLIENT_SECRET
os.environ["SPOTIPY_REDIRECT_URI"] = REDIRECT_URI

spotify = spotipy.Spotify(client_credentials_manager=spotipy.oauth2.SpotifyClientCredentials())


## DATABASE
SQL_DIR = "./sql/"
DATABASE_PATH = config["DATABASE"]["PATH"]

queries = {}

# Get SQL Files
for sql_file in os.listdir(SQL_DIR):
    file_name = sql_file.split('.')[0]

    with open(SQL_DIR + sql_file, 'r') as file:
        raw_data = file.read()

    statements = sqlparse.split(raw_data)
    if len(statements) == 1:
        queries[file_name] = statements[0]
    else:
        queries[file_name] = statements

## AUTH
AUTH_FILE = config["AUTH"]["PATH"]
AUTH = bool(int(config["AUTH"]["AUTH"]))

with open(AUTH_FILE, 'r') as file:
    authorized = file.readlines()

def is_authorized(token : str) -> bool:
    if not AUTH or token in authorized:
        return True
    else:
        return False

## MISC

class Opener():
    def __init__(self):
        self.con = sqlite3.connect(DATABASE_PATH)

    def __enter__(self):
        return self.con, self.con.cursor()

    def __exit__(self, type, value, traceback):
        self.con.commit()
        self.con.close()

app = flask.Flask(__name__)




def get_spotify_artist_image_url(id: str) -> str | None:
    spotify_response = spotify.artist(id)

    if spotify_response["images"]:
        image_url = spotify_response["images"][0]["url"]
    else:
        image_url = None

    return image_url

def get_spotify_album_image_url(id: str) -> str | None:
    spotify_response = spotify.album(id)

    if spotify_response["images"]:
        image_url = spotify_response["images"][0]["url"]
    else:
        image_url = None

    return image_url




@app.before_request
def check_auth():
    token = None
    if "token" in flask.request.headers:
        token = flask.request.headers["token"]

    if not is_authorized(token):
        flask.abort(400)

"""
Headers:
    user_id: int (required)
    limit: int (default 10) - Limits the number of artists in the response

Response:
    JSON
    {
        "top" : [
            "artist_name" : {
                "listen_time" : int (in ms),
                "spotify_id" : str
            }
        ]
    }
"""
@app.route("/top/artists", methods=["GET"])
def get_top_artists() -> flask.Response:

    # Check for user in request
    if "user" not in flask.request.headers:
        return flask.Response(status=400)

    user_id = flask.request.headers["user"]

    limit = 10
    if "limit" in flask.request.headers:
        limit = flask.request.headers["limit"]

    dated = False

    args = [user_id, limit]

    with Opener() as (con, cur):
        cur.execute(queries["top_artists"][dated], args)

        results = cur.fetchall()
    print(results)

    response = { "top" : [] }
    for artist in results:
        artist_name: str = artist[0].replace('-', ' ').title()
        spotify_id: str = artist[2]
        listen_time: int = int(artist[1])

        image_url = get_spotify_artist_image_url(spotify_id)

        response["top"].append({
            "artist_name" : artist_name,
            "spotify_id" : spotify_id,
            "listen_time" : listen_time,
            "artist_icon" : image_url
        })

    return flask.jsonify(response)

@app.route("/top/albums", methods=["GET"])
def get_top_albums() -> flask.Response:

    # Check for user in request
    if "user" not in flask.request.headers:
        return flask.Response(status=400)

    user_id = flask.request.headers["user"]

    limit = 10
    if "limit" in flask.request.headers:
        limit = flask.request.headers["limit"]

    dated = False

    args = [user_id, limit]

    with Opener() as (con, cur):
        cur.execute(queries["top_albums"][dated], args)

        results = cur.fetchall()
    print(results)

    response = { "top" : [] }
    for album in results:
        artist_name: str = album[0].replace('-', ' ').title()
        album_name: str = album[2]
        spotify_id: str = album[4]
        listen_time: int = int(album[3])

        image_url = get_spotify_album_image_url(spotify_id)

        response["top"].append({
            "artist_name" : artist_name,
            "album_name" : album_name,
            "spotify_id" : spotify_id,
            "listen_time" : listen_time,
            "album_cover" : image_url
        })

    return flask.jsonify(response)

app.run()
