import os, traceback, time, tekore, asyncio
from client_keys import ClientKeys
from auth_helper import AuthHelper
from pywinauto import Application
from process_handler import ProcessHandler
from threading import Event

spotify_path = ""
app = Application(backend = "uia")
token = None

# TODO:
# Fix delay problem by skipping the rest of the track or just accept the extra API calls. Maybe add 2 seconds to the event?
# Move everything app related from program to processhandler

class Program:
    def __init__(self, app, evnt, process_handler):
        self.app = app
        self.evnt = evnt
        self.process_handler: ProcessHandler = process_handler
        self.spotify = tekore.Spotify(token, asynchronous = True)
        self.current_playback = None
        self.old_song = None
        self.is_playing_song = False
        self.got_ad = False

    # Check the current playback to see if an ad is playing.
    async def check_for_ads(self):
        self.current_playback: tekore.model.CurrentlyPlaying = await self.spotify.playback_currently_playing()
        print("getting playback")

        if self.current_playback != None:
            # Check for ads.
            if self.current_playback.currently_playing_type == "ad" or self.current_playback.currently_playing_type == "unknown":
                print("\nAd detected! Rebooting Spotify.\n")
                self.reload_spotify()
                self.got_ad = True
            # Set the song duration and wait.
            else:
                song = self.current_playback.item
                if self.current_playback.item != self.old_song:
                    print("Now Playing: \"{}\" by {}".format(song.name, ", ".join([artist.name for artist in song.artists])))

                seconds_left = (self.current_playback.item.duration_ms - self.current_playback.progress_ms) / 1000
                # This happens when the API says the song is done but the player is behind. Give some time for the player to catch up.
                if seconds_left == 0:
                    await asyncio.sleep(1)
                    return
                
                self.got_ad = False
                self.old_song = self.current_playback.item

                # Wait for the song to end.
                self.is_playing_song = True
                evnt.wait(seconds_left + 1.5) # Add 1.5s to the wait time to mitigate the player being behind the API. We don't want to delay too much because the ad will play for longer (if there is one).
                self.is_playing_song = False
        
        # I don't know why this happens. 
        # However, if it happens after we reloaded for an ad, then we should only wait for the state.
        else:
            print("Got a None playback state.")
            if self.process_handler.try_get_meter() == 0:
                print("Returned method because there was 0 volume detected")
                return
            if not self.got_ad:
                print("Reloading Spotify because we didn't get an ad.")
                self.reload_spotify()
            print("Waiting for state")
            await self.wait_for_state()

    # Check every 10 seconds for a state until the state is not None.
    async def wait_for_state(self):
        while self.current_playback == None:
            await asyncio.sleep(10)
            self.current_playback = await self.spotify.playback_currently_playing()

    # Reopen Spotify and play the next song.
    def reload_spotify(self):
        self.process_handler.set_restarting(True)

        self.app.kill()
        time.sleep(2)
        self.app.start(spotify_path)

        time.sleep(1)
        window = self.app.windows()[0]
        # Play and go to the next track.
        window.type_keys("{VK_SPACE} ^{VK_RIGHT}")
        window.minimize()

        self.process_handler.set_restarting(False)

async def main(program, process_handler):
    if process_handler.is_state_valid:
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
        process_handler.program = program
        process_handler.start()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            loop.run_until_complete(main(program, process_handler))

    except:
        print(traceback.format_exc())
        input("Error detected. Press ENTER to close...")