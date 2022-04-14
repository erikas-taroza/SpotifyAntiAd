import os, traceback, time, pyautogui, tekore, asyncio
from client_keys import ClientKeys
from auth_helper import AuthHelper
from pywinauto import Application
from process_handler import ProcessHandler
from threading import Event

spotify_path = ""
app = Application(backend = "uia")
token = None

class Program:
    def __init__(self, app, evnt, process_handler):
        self.app = app
        self.evnt = evnt
        self.process_handler: ProcessHandler = process_handler
        self.spotify = tekore.Spotify(token, asynchronous = True)
        self.current_playback = None
        self.old_song = None

    # Check the current playback to see if an ad is playing.
    async def check_for_ads(self):
        self.current_playback: tekore.model.CurrentlyPlaying = await self.spotify.playback_currently_playing()
        print("Current Playback")

        if self.current_playback != None:
            # Check for ads or set the wait duration.
            if self.current_playback.currently_playing_type == "ad" or self.current_playback.currently_playing_type == "unknown":
                print("\nAd detected! Rebooting Spotify.\n")
                self.process_handler.getting_next_song = True
                self.reload_spotify()
            else:
                song = self.current_playback.item
                if self.current_playback.item != self.old_song:
                    print("Now Playing: \"{}\" by {}".format(song.name, ", ".join([artist.name for artist in song.artists])))
                # Wait for the song to end.
                evnt.wait((self.current_playback.item.duration_ms - self.current_playback.progress_ms) / 1000)
                self.process_handler.getting_next_song = True
                self.old_song = self.current_playback.item

    # Reopen Spotify and play the next song.
    def reload_spotify(self):
        self.process_handler.set_restarting(True)
        self.app.kill()
        time.sleep(2)
        self.app.start(spotify_path)

        time.sleep(1)
        window = self.app.windows()[0]
        window.set_focus()
        pyautogui.press("playpause")
        pyautogui.press("nexttrack")
        window.minimize()

        self.process_handler.set_restarting(False)

async def main(program, process_handler):
    if process_handler.is_state_valid and not process_handler.getting_next_song:
        # Even though we can check for ads, 
        # we need to give Spotify some time to register our click on the play button.
        #await asyncio.sleep(0.3)
        await program.check_for_ads()

if __name__ == "__main__":
    # Get Spotify.exe path.
    spotify_path = os.path.expanduser("~") + "\\AppData\\Roaming\\Spotify\\Spotify.exe"
    print("INFO: Make sure Spotify was installed from spotify.com and not the Windows Store. Otherwise, this program will not open Spotify.\n")
    print("INFO: If Spotify is focused, the ad checker will stop because it assumes you will change the player settings (ex. position in song).")
    print("\nRunning...")

    try:
        # Get the token. If there is a config file, get the token from there. Otherwise, get the token from a prompt.
        try:
            config = tekore.config_from_file("./config.ini", return_refresh = True)
            (client_id, client_secret, redirect_url, refresh_token) = config
            token = tekore.refresh_user_token(ClientKeys.client_id, ClientKeys.client_secret, refresh_token)
        except:
            auth_helper = AuthHelper()
            token = auth_helper.get_token()
            tekore.config_to_file("./config.ini", ("client_id", "client_secret", "redirect_url", token.refresh_token))

        app.start(spotify_path)
        time.sleep(2)

        evnt = Event()
        process_handler = ProcessHandler(evnt, app)
        program = Program(app, evnt, process_handler)
        process_handler.start()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            loop.run_until_complete(main(program, process_handler))

    except:
        print(traceback.format_exc())
        input("Error detected. Press ENTER to close...")