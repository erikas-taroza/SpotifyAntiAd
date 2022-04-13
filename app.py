import os, traceback, time, pyautogui, spotipy
from pywinauto import Application
from spotipy.oauth2 import SpotifyOAuth
from client_keys import ClientKeys
from window_handler import WindowHandler
from threading import Event

os.environ["SPOTIPY_CLIENT_ID"] = ClientKeys.client_id
os.environ["SPOTIPY_CLIENT_SECRET"] = ClientKeys.client_secret
os.environ["SPOTIPY_REDIRECT_URI"] = "http://127.0.0.1:7777/"

spotify_path = ""
app = Application(backend = "uia")

class Program:
    # init spotify
    def __init__(self, app, evnt, window_handler):
        self.scope = ["user-read-playback-state"]
        self.spotify = spotipy.Spotify(auth_manager = SpotifyOAuth(scope = self.scope))
        self.app = app
        self.evnt = evnt
        self.window_handler = window_handler
        self.current_playback = None
        self.restarting = False

    # check the current playback to see if an ad is playing
    def check_for_ads(self):
        self.refresh_token()
        self.current_playback = self.spotify.current_playback()

        if self.current_playback != None and self.current_playback["is_playing"]:
            # wait for the song to end
            evnt.wait((self.current_playback["item"]["duration_ms"] - self.current_playback["progress_ms"]) / 1000)

            # if we dont wait some time here, we get a TypeError when main() calls this method again
            # ads dont provide the time needed in the calculation above
            time.sleep(0.5)
            current_state = self.spotify.current_playback()["currently_playing_type"]
            if current_state == "ad":
                print("Ad detected! Rebooting Spotify.")
                self.reload_spotify()

    # refresh the cached token if it is expired. expires in about 1 hour
    def refresh_token(self):
        auth = self.spotify.auth_manager
        token = auth.get_cached_token()
        if token != None and auth.is_token_expired(token):
            auth.refresh_access_token(token["refresh_token"])

    # reopen spotify and play the next song
    def reload_spotify(self):
        self.restarting = True
        self.app.kill()
        time.sleep(2)
        self.app.start(spotify_path)

        time.sleep(1)
        window = self.app.windows()[0]
        self.window_handler.window = window
        self.restarting = False
        
        window.set_focus()
        pyautogui.press("playpause")
        pyautogui.press("nexttrack")
        window.minimize()

def main(program, window_handler):
    if window_handler.can_check_ads:
        program.check_for_ads()

if __name__ == "__main__":
    # get spotify.exe path
    spotify_path = os.path.expanduser("~") + "\\AppData\\Roaming\\Spotify\\Spotify.exe"
    print("INFO: Make sure Spotify was installed from spotify.com and not the Windows Store. Otherwise, this program will not open Spotify.")
    print("\nRunning...")

    app.start(spotify_path)
    time.sleep(2)

    evnt = Event()
    window_handler = WindowHandler(evnt, app.windows()[0])
    program = Program(app, evnt, window_handler)
    window_handler.program = program
    window_handler.start()

    try:
        while True:
            main(program, window_handler)
    except:
        print(traceback.format_exc())
        input("Error detected. Press ENTER to close...")