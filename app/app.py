import os
import sys
import sqlite3
import logging
import configparser

import flask
import spotipy
import sqlparse
import waitress

# SETUP
config = configparser.ConfigParser()
config.read("config.ini")

## LOGGING
FORMAT = "%(asctime)s : %(levelname)s - %(message)s"
logging.basicConfig(filename="../music-stats-api.log", encoding="utf-8", level=logging.INFO, format=FORMAT)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

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
PORT = int(config['NETWORK']['PORT'])
DEV = int(config['NETWORK']['DEV'])

class Opener():
    def __init__(self):
        self.con = sqlite3.connect(DATABASE_PATH)

    def __enter__(self):
        return self.con, self.con.cursor()

    def __exit__(self, type, value, traceback):
        self.con.commit()
        self.con.close()

logging.info(f"<{'-'*10}> APP STARTING <{'-'*10}>")
logging.info(f"Database Path: {DATABASE_PATH}")
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

    response = { "top" : [] }
    for artist in results:
        artist_name: str = artist[0].replace('-', ' ').title()
        spotify_id: str = artist[2]
        listen_time: int = int(artist[1])

        # Check for album art in DB
        artist_icon_url: str | None = artist[4]

        if not artist_icon_url:
            artist_id: int = artist[3]
            artist_icon_url = get_spotify_artist_image_url(spotify_id)

            with Opener() as (con, cur):
                cur.execute(queries["update_artist_icon_url"], [artist_icon_url, artist_id])

        response["top"].append({
            "artist_name" : artist_name,
            "spotify_id" : spotify_id,
            "listen_time" : listen_time,
            "artist_icon" : artist_icon_url
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
    logging.debug(results)

    response = { "top" : [] }
    for album in results:
        artist_name: str = album[0].replace('-', ' ').title()
        album_name: str = album[2]
        spotify_id: str = album[4]
        listen_time = int(album[3])

         # Check for album art in DB
        album_cover_url: str | None = album[5]

        if not album_cover_url:
            logging.debug(f'Fetching album art for {album_name}')
            album_id: int = album[1]
            album_cover_url = get_spotify_album_image_url(spotify_id)


            with Opener() as (con, cur):
                cur.execute(queries["update_album_art"], [album_cover_url, album_id])

        response["top"].append({
            "artist_name" : artist_name,
            "album_name" : album_name,
            "spotify_id" : spotify_id,
            "listen_time" : listen_time,
            "album_cover" : album_cover_url
        })

    return flask.jsonify(response)

if __name__ == "__main__":
    if DEV:
        app.run(port=PORT)
    else:
        waitress.serve(app, host='0.0.0.0', port=PORT)
