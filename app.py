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

class Sleep:
    def __init__(self):
        self.tasks = set()
        self.is_complete = False
    
    async def sleep(self, delay, result = None, set_is_complete = False):
        task = asyncio.create_task(asyncio.sleep(delay, result))
        self.is_complete = False
        self.tasks.add(task)

        try:
            await task
            if set_is_complete:
                self.is_complete = True
                self.cancel_all()
                print("reached end of song")
        except asyncio.CancelledError:
            return result
        finally:
            self.tasks.remove(task)
    
    def cancel_all(self):
        for task in self.tasks:
            task.cancel()

class Program:
    # init spotify
    def __init__(self, app):
        self.scope = ["user-read-playback-state", "user-read-recently-played"]
        self.spotify = spotipy.Spotify(auth_manager = SpotifyOAuth(scope = self.scope))
        self.app = app
        self.previous_song_id = ""
        self.sleep = Sleep()

    # check the current playback to see if an ad is playing
    async def check_current_playback(self):
        # if the token is expired, refresh
        auth = self.spotify.auth_manager
        token = auth.get_cached_token()
        if token != None and auth.is_token_expired(token):
            auth.refresh_access_token(token["refresh_token"])

        # check playback state
        playback = self.spotify.current_playback()
        if playback != None and playback["is_playing"]:
            if self.previous_song_id == "":
                self.previous_song_id = self.spotify.current_user_recently_played(1)["items"][0]["track"]["id"]
            
            # wait for the song to end or if the song has been changed before continuing
            self.sleep.sleep(((playback["item"]["duration_ms"] - playback["progress_ms"]) + 100) / 1000, set_is_complete = True)
            self.previous_song_id = playback["item"]["id"]
            
            current_state = self.spotify.current_playback()["currently_playing_type"]
            if current_state == "track":
                print("Ad detected! Rebooting Spotify.")
                await self.reload_spotify()

        await asyncio.sleep(5)

    # async def check_if_song_changed(self):
    #     while True:
    #         recently_played = self.spotify.current_user_recently_played(1)["items"][0]["track"]["id"]
    #         print("Recently played: " + recently_played)
    #         print("Previous song: " + self.previous_song_id)
    #         if recently_played != self.previous_song_id or self.sleep.is_complete:
    #             self.sleep.cancel_all()
    #             break
            
    #         await self.sleep.sleep(10)

    # reopen spotify and play the next song
    async def reload_spotify(self):
        self.app.kill()
        await asyncio.sleep(2)
        self.app.start(spotify_path)

        await asyncio.sleep(1)
        window = self.app.windows()[0]
        window.set_focus()
        pyautogui.press("playpause")
        pyautogui.press("nexttrack")
        window.minimize()

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