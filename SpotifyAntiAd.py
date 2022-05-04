import threading
import traceback, time, tekore, asyncio
from logger import Logger
from client_keys import ClientKeys
from auth_helper import AuthHelper
from process_handler import ProcessHandler
from threading import Event
from pywinauto import Application

# Using this version of pywinauto: https://github.com/pywinauto/pywinauto/tree/44ca38c0617299d7c4158cbb887fe0ec3dfc7135
# For some reason the program suddenly stopped working so switching to the updated lib and refactoring solved the problem.
app = Application()
class Program:
    def __init__(self, token, evnt, process_handler):
        self.evnt = evnt
        self.process_handler: ProcessHandler = process_handler
        self.spotify = tekore.Spotify(token, asynchronous = True)
        self.current_playback = None
        self.old_song = None
        self.is_playing_song = False
        self.got_ad = False

        self.restart_timed_out = False

    # Check the current playback to see if an ad is playing.
    async def check_for_ads(self):
        self.current_playback: tekore.model.CurrentlyPlaying = await self.spotify.playback_currently_playing()
        Logger.log("Getting playback state.")

        if self.current_playback != None:
            # Check for ads.
            if self.current_playback.currently_playing_type == "ad" or self.current_playback.currently_playing_type == "unknown":
                Logger.log("\nAd detected! Rebooting Spotify.\n", True)
                self.reload_spotify()
                self.got_ad = True
            # Set the song duration and wait.
            else:
                song = self.current_playback.item
                if self.current_playback.item != self.old_song:
                    artists = ", ".join([artist.name for artist in song.artists])
                    Logger.log(f"Now Playing: \"{song.name}\" by {artists}", True)

                seconds_left = (self.current_playback.item.duration_ms - self.current_playback.progress_ms) / 1000
                # This happens when the API says the song is done but the player is behind. Give some time for the player to catch up.
                if seconds_left == 0:
                    Logger.log("Song has ended but the player is behind. Waiting...")
                    time.sleep(1)
                    return
                
                self.got_ad = False
                self.old_song = self.current_playback.item

                # Wait for the song to end.
                self.is_playing_song = True
                self.evnt.wait(seconds_left + 1.5) # Add 1.5s to the wait time to mitigate the player being behind the API. We don't want to delay too much because the ad will play for longer (if there is one).
                self.is_playing_song = False
        
        # I don't know why this happens. 
        # However, if it happens after we reloaded for an ad, then we should only wait for the state.
        else:
            Logger.log("Playback received is None.")
            if not self.got_ad:
                Logger.log("Restarting Spotify because we did not get an ad when the playback was None.")
                self.reload_spotify()
            Logger.log("Waiting for a better state because playback was None.")
            await self.wait_for_state()

    # Check every time period for a usable state. We can check at this interval because no ads should be playing.
    async def wait_for_state(self):
        while self.current_playback == None:
            Logger.log("Trying to get a better state...")
            time.sleep(30)
            self.current_playback = await self.spotify.playback_currently_playing()

    # Reopen Spotify and play the next song.
    def reload_spotify(self):
        Logger.log("Reloading Spotify...")

        # Stop the current thread.
        self.process_handler.restarting = True
        self.process_handler.join()

        # Create a new thread.
        self.process_handler = ProcessHandler(self.evnt, app)
        self.process_handler.program = self

        self.process_handler.restart_process()
        
        # def timeout():
        #     time.sleep(2)
        #     self.restart_timed_out = True
        #     print("timed out")

        # Play the next track.
        #t = threading.Thread(target = timeout)
        #t.start()
        # while self.process_handler.is_meter_available() == None: # While loop to ensure that the next track is played.
        #     if not self.restart_timed_out:
        #         self.process_handler.window.send_keystrokes("^{VK_RIGHT}")
        #         self.process_handler.window.minimize()
        #         print("soft")
        #     else:
        #         self.process_handler.window.set_focus().type_keys("^{VK_RIGHT}").minimize()
        #     time.sleep(0.1)

        # while self.process_handler.is_meter_available() == None:
        #     self.process_handler.window.send_keystrokes("^{VK_RIGHT}")
        #     self.process_handler.window.minimize()
        #     time.sleep(0.1)
        #     print("soft")

        # Play the next track.
        self.process_handler.window.send_keystrokes("^{VK_RIGHT}")
        self.process_handler.window.minimize()

        #t.join()
        #self.restart_timed_out = False
        # Waits for Soptify API to receive the input above.
        time.sleep(1)
        self.process_handler.start() # Start listening for window updates again.

async def main(program, process_handler):
    if process_handler.is_state_valid:
        await program.check_for_ads()

if __name__ == "__main__":
    print("INFO: Make sure Spotify was installed from spotify.com and not the Windows Store. Otherwise, this program will not open Spotify.\n")
    print("INFO: If Spotify is focused, the ad checker will stop because it assumes you will change the player settings (ex. position in song).\n")
    Logger.log("Running...", True)

    token = None

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

        evnt = Event()
        process_handler = ProcessHandler(evnt, app)
        process_handler.start_process()
        time.sleep(2)
    
        program = Program(token, evnt, process_handler)
        process_handler.program = program
        process_handler.start()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            loop.run_until_complete(main(program, process_handler))

    except:
        Logger.log(traceback.format_exc(), True)
        input("Error detected. Press ENTER to close...")