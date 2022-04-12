import os, asyncio, traceback
from pywinauto import Application
import pyautogui
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from client_keys import ClientKeys

os.environ["SPOTIPY_CLIENT_ID"] = ClientKeys.client_id
os.environ["SPOTIPY_CLIENT_SECRET"] = ClientKeys.client_secret
os.environ["SPOTIPY_REDIRECT_URI"] = "http://127.0.0.1:7777/"

spotify_path = ""
app = Application(backend = "uia")

class Program:
    # init spotify
    def __init__(self, app):
        self.scope = ["user-read-playback-state"]
        self.spotify = spotipy.Spotify(auth_manager = SpotifyOAuth(scope = self.scope))
        self.app = app

    # check the current playback to see if an ad is playing
    async def check_current_playback(self):
        # if the token is expired, refresh
        auth = self.spotify.auth_manager
        token = auth.get_cached_token()
        if token != None and auth.is_token_expired(token):
            auth.refresh_access_token(token["refresh_token"])

        playback = self.spotify.current_playback()
        if playback != None:
            current_state = playback.get("currently_playing_type")
            if current_state == "ad":
                print("Ad detected! Rebooting Spotify.")
                await self.reload_spotify()
                await asyncio.sleep(1)

                window = self.app.windows()[0]
                window.set_focus()
                pyautogui.press("playpause")
                pyautogui.press("nexttrack")
                window.minimize()
        
        await asyncio.sleep(3)

    async def reload_spotify(self):
        self.app.kill()
        await asyncio.sleep(2)
        self.app.start(spotify_path)

async def main(p):
    await p.check_current_playback()
        

if __name__ == "__main__":
    # get spotify.exe path
    spotify_path = os.path.expanduser("~") + "\\AppData\\Roaming\\Spotify\\Spotify.exe"
    print("INFO: Make sure Spotify was installed from spotify.com and not the Windows Store. Otherwise, this program will not open Spotify.")
    print("\nRunning...")

    program = Program(app)
    app.start(spotify_path)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            loop.run_until_complete(main(program))
    except:
        print(traceback.format_exc())
        input("Error detected. Press ENTER to close...")