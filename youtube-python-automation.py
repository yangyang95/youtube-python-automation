import json
import requests
import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import youtube_dl

from exceptions import ResponseException
from secrets import spotify_token, spotify_user_id

class CreatePlaylist:

    def __init__(self):
        self.youtube_client = self.get_youtube_client()
        self.all_song_info = {}

    # Step 1: Login to youtube
    def get_youtube_client(self):
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret.json"

        # Get credentials and create an API client
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
        credentials = flow.run_console()
        youtube_client = googleapiclient.discovery.build(api_service_name, api_version, credentials=credentials)

        return youtube_client

    # Step 2: Grab playlist from youtube
    def get_liked_video(self):
        
        request = youtube.playlists().list(
            part="snippet",
            maxResults=25,
            mine=True
        )

        response = request.execute()

        # Collect videos and get important information
        for item in response["items"]:
            video_title = item["snippet"]["title"]
            youtube_url = "https://www.youtube.com/watch?v={}".format(item["id"])

            # Use youtube_dl to collect the song name and artist name
            video = youtube_dl.YoutubeDL({}).extract_info(youtube_url, download=False)
            song_name = video["track"]
            artist = video["artist"]

            # Save all important info
            if song_name is not None and artist is not None:
                self.all_song_info[video_title] = {
                    "youtube_url": youtube_url,
                    "song_name": song_name,
                    "artist": artist,

                    # Add the url, easy to get song to put into playlist
                    "spotify_uri": self.get_spotify_uri(song_name, artist)
                }

    # Step 3: Crete spotify playlist if not exist
    def create_playlist(self):
        
        request_body = json.dumps({
            "name": "Youtube playlist",
            "description": "Liked video in youtube",
            "public": False
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format(spotify_user_id)
        
        response = requests.post(
            query,
            data = request_body,
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )

        response_json = response.json()

        # Return playlist id
        return response_json["id"]

    def get_spotify_uri(self, song_name, artist):
        
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20".format(
            song_name,
            artist
        )
        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        songs = response_json["tracks"]["items"]

        # only use the first song
        uri = songs[0]["uri"]

        return uri

    # Step 5: Add searched song to playlist
    def add_song_to_playlist(self):
        
        # Populate song dictionary
        self.get_liked_video()

        # Collect all of uri
        uris = []
        for song, info in self.all_song_info.items():
            uris.append(info["spotify_uri"])

        # Create a new playlist
        playlist_id = self.create_playlist()

        # Add all songs into new playlist
        request_data = json.dumps(uris)

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id)

        response = requests.post(
            query,
            data = request_data,
            headers = 
            {
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )

        # check for valid response status
        if response.status_code != 200:
            raise ResponseException(response.status_code)

        response_json = response.json()
        return response


if __name__ == '__main__':
    cp = CreatePlaylist()
    cp.add_song_to_playlist()