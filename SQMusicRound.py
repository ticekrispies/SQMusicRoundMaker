import json
import os
import pathlib
import spotipy
import random

from datetime import datetime
import xml.etree.cElementTree as ET
from spotipy.oauth2 import SpotifyClientCredentials


class MusicRoundManager:
    def __init__(self):
        self.b64_encoded_image = ""
        self.env_consts = self.get_env_consts()
        self.spotify = self.establish_spotify_connection()
        self.output_location = os.path.join(os.getcwd(), "output")

        self.create_output_directory()
        self.load_default_image()

    @staticmethod
    def get_env_var(env_var: str) -> str:
        """Return environment variable of key ``env_var``. Will stop application if not found."""
        try:
            return os.environ[env_var]
        except KeyError:
            print(f"Missing environment variable: {env_var}")
            raise

    def get_env_consts(self) -> dict:
        """Return dict containing all required environment variables at application launch."""
        env_const_dict = {
            "SPOTIFY_CLIENT_ID": "",
            "SPOTIFY_CLIENT_SECRET": "",
        }

        for key in env_const_dict:
            env_const_dict[key] = self.get_env_var(key)

        return env_const_dict

    def create_output_directory(self):
        pathlib.Path(self.output_location).mkdir(parents=True, exist_ok=True)

    def load_default_image(self):
        with open("assets/default_image.b64", encoding="UTF-8") as b64_file:
            self.b64_encoded_image = b64_file.read()

    def establish_spotify_connection(self) -> spotipy.Spotify:
        client_credentials_manager = SpotifyClientCredentials(
            client_id=self.env_consts["SPOTIFY_CLIENT_ID"],
            client_secret=self.env_consts["SPOTIFY_CLIENT_SECRET"])
        return spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    def get_playlist_from_url(self, playlist_url: str) -> list[dict]:
        playlist_id = playlist_url.split('/')[-1].split('?')[0]
        playlist_tracks = self.spotify.playlist_items(playlist_id)['items']

        return playlist_tracks

    @staticmethod
    def get_thumbnail_url(track: dict) -> str:
        images = track["album"]["images"]
        for image in images:
            if image["height"] == 64:
                return image["url"]

        return ""

    @staticmethod
    def handle_article_words(answer: str) -> str:
        split_answer = answer.split()
        if split_answer[0].upper() in ['THE', 'A', 'AN']:
            article = split_answer.pop(0)
            answer = " ".join(split_answer) + f", {article}"

        return answer

    @staticmethod
    def is_valid_as_answer(answer: str) -> bool:
        valid_characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if answer[0] in valid_characters:
            return True
        else:
            return False

    def parse_tracks(self, track_list: list[dict]) -> list[dict]:
        parsed_tracks = []

        for track in track_list:
            track_dict = track["track"]
            parsed_track = {
                "artists": [],
                "title": "",
                "valid_title": False,
                "thumbnail_image": "",
            }

            for artist in track_dict["artists"]:
                name = self.handle_article_words(artist["name"])
                is_valid = self.is_valid_as_answer(name)
                parsed_track["artists"].append(
                    {
                        "name": name,
                        "display": artist["name"],
                        "is_valid": is_valid,
                    }
                )
            track_title = self.handle_article_words(track_dict["name"])
            parsed_track["title"] = track_title
            parsed_track["display"] = track_dict["name"]
            parsed_track["valid_title"] = self.is_valid_as_answer(track_title)
            parsed_track["thumbnail_image"] = self.get_thumbnail_url(track_dict)

            parsed_tracks.append(parsed_track)

        return parsed_tracks

    @staticmethod
    def randomized_selection(track_list: list[dict]) -> list[dict]:
        for i, track in enumerate(track_list):
            artist_name = track["artists"][0]["name"]
            valid_artist = track["artists"][0]["is_valid"]

            track_name = track["title"]
            valid_track = track["valid_title"]

            if not valid_artist and not valid_track:
                raise ValueError(
                    f'SONG #{i} INVALID: Both artist_name ({artist_name}, first char {artist_name[0]}) and track_name ({track_name}, first char {track_name[0]}) start with illegal characters. Please swap out this entry for a valid one.'
                )

            question_target = random.choice(['ARTIST', 'SONG'])

            # Flip target if invalid target selected
            if question_target == "ARTIST" and not valid_artist:
                print(f"Artist {artist_name} invalid, switching target to song: {track_name}.")
                question_target = "SONG"
            elif question_target == "SONG" and not valid_track:
                print(f"Song {track_name} invalid, switching target to artist: {artist_name}.")
                question_target = "ARTIST"

            track_list[i]["target"] = question_target

        return track_list

    def generate_xml_from_parsed(self, parsed_tracks: list[dict]):
        now = datetime.now()  # current date and time
        date_time = now.strftime('%d %m %Y')

        new_round = ET.Element('round')
        ET.SubElement(new_round, 'game').text = 'Quizsentials'
        ET.SubElement(new_round, 'title').text = f'SQ Music Round {date_time}'
        ET.SubElement(new_round, 'points_per_question').text = '10'
        ET.SubElement(new_round, 'go_wide').text = 'true'
        ET.SubElement(new_round, 'speed_bonus').text = 'true'

        questions = ET.SubElement(new_round, 'questions')

        for i, track in enumerate(parsed_tracks, start=1):
            artist_display = track["artists"][0]["display"]
            artist_name = track["artists"][0]["name"]

            track_display = track["display"]
            track_name = track["title"]

            question_target = track["target"]

            song_number = f"{i}"
            q_text = ''

            if question_target == 'ARTIST':
                q_text = f'MUSIC ROUND #{song_number} - Tap on the first letter of the ARTIST name'
                s_answer = artist_name[0].upper()
                l_answer = f'{artist_display} with "{track_display}"'
                print(
                    f'XML Question element #{i} successfully added: answer set to "{s_answer}" as target is ARTIST for entry {artist_name} with"{track_name}" by ')

            if question_target == 'SONG':
                q_text = f'MUSIC ROUND #{song_number} - Tap on the first letter of the SONG TITLE'
                s_answer = track_name[0].upper()
                l_answer = f'"{track_display}" by {artist_display}'
                print(
                    f'XML Question element #{i} successfully added: answer set to "{s_answer}" as target is SONG for entry "{track_name}" by {artist_name}.')

            question = ET.SubElement(questions, 'question')
            ET.SubElement(question, 'user_view').text = 'letters'
            ET.SubElement(question, 'q').text = q_text
            ET.SubElement(question, 'short_answer').text = s_answer
            ET.SubElement(question, 'long_answer').text = l_answer
            ET.SubElement(question, 'picture').text = self.b64_encoded_image
            ET.SubElement(question, 'id').text = str(i)

        tree = ET.ElementTree(new_round)
        print('Generating XML file...')
        file_path = os.path.join(self.output_location, f"SQ Music Round {date_time}.sqq")
        tree.write(file_path, encoding='utf-8')
        print('XML file generated!')
        print('DONE: SpeedQuizzing music round successfully generated!')

    def generate_xml(self, playlist_tracks):
        now = datetime.now()  # current date and time
        date_time = now.strftime('%d %m %Y')

        # Uncomment to see complete playlist contents
        # for i, track in sp.playlist_tracks(playlist_id)['items']:
        #    i = i + 1
        #    #Track name
        #    track_name = track['track']['name']
        #    #Name, popularity, genre
        #    artist_name = track['track']['artists'][0]['name']
        #    print(i, '- ' + artist_name + ', ' + track_name)

        # Initial XML structure
        print('Setting up XML file structure...')
        new_round = ET.Element('round')
        ET.SubElement(new_round, 'game').text = 'Quizsentials'
        ET.SubElement(new_round, 'title').text = f'SQ Music Round {date_time}'
        ET.SubElement(new_round, 'points_per_question').text = '10'
        ET.SubElement(new_round, 'go_wide').text = 'true'
        ET.SubElement(new_round, 'speed_bonus').text = 'true'

        questions = ET.SubElement(new_round, 'questions')

        # Generate question XML structure for every item in playlist
        for i, track in enumerate(playlist_tracks, start=1):
            track_name = track['track']['name']
            artist_name = track['track']['artists'][0]['name']
            song_number = f"{i}"
            q_text = ''

            question_target = random.choice(['ARTIST', 'SONG'])

            # Check if the question target is 'ARTIST'
            if question_target == 'ARTIST':
                # Handle exception of both inputs being invalid
                split_artist_name = artist_name.split()
                if split_artist_name[0].upper() in ['THE', 'A', 'AN']:
                    article = split_artist_name.pop(0)
                    short_artist_name = " ".join(split_artist_name)
                if artist_name[0].isdigit():
                    split_track_name = track_name.split()
                    if split_track_name[0].upper() in ['THE', 'A', 'AN']:
                        article = split_track_name.pop(0)
                        short_track_name = " ".join(split_track_name)
                    if short_track_name[0].isdigit():
                        raise ValueError(
                            f'SONG #{i} INVALID: Both artist_name ({artist_name}, first char {artist_name[0]}) and track_name ({track_name}, first char {track_name[0]}) start with articles or numbers. Target was {question_target}, ({artist_name} with "{track_name})". Please swap out this entry for a valid one.')
                    else:
                        q_text = f'MUSIC ROUND #{song_number} - Tap on the first letter of the SONG TITLE'
                        s_answer = short_track_name[0].upper()
                        l_answer = f'"{track_name}" by {artist_name}'
                        print(
                            f'XML Question element #{i} successfully added: answer set to "{s_answer}" as target is SONG for entry "{track_name}" by {artist_name}.')
                else:
                    q_text = f'MUSIC ROUND #{song_number} - Tap on the first letter of the ARTIST name'
                    s_answer = artist_name[0].upper()
                    l_answer = f'{artist_name} with "{track_name}"'
                    print(
                        f'XML Question element #{i} successfully added: answer set to "{s_answer}" as target is ARTIST for entry {artist_name} with "{track_name}"')

            # Check if the question target is 'SONG'
            if question_target == 'SONG':
                # Handle exception of both inputs being invalid
                split_track_name = track_name.split()
                if split_track_name[0].upper() in ['THE', 'A', 'AN']:
                    article = split_track_name.pop(0)
                    short_track_name = " ".join(split_track_name)
                if track_name[0].isdigit():
                    split_artist_name = artist_name.split()
                    if split_artist_name[0].upper() in ['THE', 'A', 'AN']:
                        article = split_artist_name.pop(0)
                        short_artist_name = " ".join(split_artist_name)
                    if short_artist_name[0].isdigit():
                        raise ValueError(
                            f'SONG #{i} INVALID: Both artist_name ({artist_name}, first char {artist_name[0]}) and track_name ({track_name}, first char {track_name[0]}) start with articles or numbers. Target was {question_target}, ({artist_name} with "{track_name})". Please swap out this entry for a valid one.')
                    else:
                        q_text = f'MUSIC ROUND #{song_number} - Tap on the first letter of the ARTIST name'
                        s_answer = short_artist_name[0].upper()
                        l_answer = f'{artist_name} with "{track_name}"'
                        print(
                            f'XML Question element #{i} successfully added: answer set to "{s_answer}" as target is ARTIST for entry {artist_name} with "{track_name}"')
                else:
                    q_text = f'MUSIC ROUND #{song_number} - Tap on the first letter of the SONG TITLE'
                    s_answer = track_name[0].upper()
                    l_answer = f'"{track_name}" by {artist_name}'
                    print(
                        f'XML Question element #{i} successfully added: answer set to "{s_answer}" as target is SONG for entry "{track_name}" by {artist_name}.')

            question = ET.SubElement(questions, 'question')
            ET.SubElement(question, 'user_view').text = 'letters'
            ET.SubElement(question, 'q').text = q_text
            ET.SubElement(question, 'short_answer').text = s_answer
            ET.SubElement(question, 'long_answer').text = l_answer
            ET.SubElement(question, 'picture').text = self.b64_encoded_image
            ET.SubElement(question, 'id').text = str(i)

        tree = ET.ElementTree(new_round)
        print('Generating XML file...')
        file_path = os.path.join(self.output_location, f"SQ Music Round {date_time}.sqq")
        tree.write(file_path, encoding='utf-8')
        print('XML file generated!')
        print('DONE: SpeedQuizzing music round successfully generated!')


if __name__ == "__main__":
    round_manager = MusicRoundManager()
    new_track_list = round_manager.get_playlist_from_url("https://open.spotify.com/playlist/5uUyfOzZtZPxUkFCAUTNE2?si=ff7b076234c14038")

    use_parsed_list = False  # Set True for experimental parser and generation

    if use_parsed_list:
        parsed_list = round_manager.parse_tracks(new_track_list)
        selected_list = round_manager.randomized_selection(parsed_list)

        with open("parsed_list.json", mode="w+", encoding="UTF-8") as f:
            json.dump(selected_list, f, indent=4)

        round_manager.generate_xml_from_parsed(selected_list)
    else:
        round_manager.generate_xml(new_track_list)

