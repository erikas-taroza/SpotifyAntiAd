import traceback, time, tekore, asyncio, threading
from logger import Logger
from client_keys import ClientKeys
from auth_helper import AuthHelper
from process_handler import ProcessHandler
from threading import Event
from pywinauto import Application

# Using this version of pywinauto: https://github.com/pywinauto/pywinauto/tree/44ca38c0617299d7c4158cbb887fe0ec3dfc7135
# For some reason the program suddenly stopped working so switching to the updated lib and refactoring solved the problem.
app = Application(backend = "win32")

class Program:
    def __init__(self, token, evnt, process_handler):
        self.evnt:threading.Event = evnt
        self.process_handler: ProcessHandler = process_handler
        self.spotify = tekore.Spotify(token, asynchronous = True)
        self.current_playback = None
        self.old_song = None
        self.is_playing_song = False

    # Check the current playback to see if an ad is playing.
    async def check_for_ads(self):
        self.current_playback: tekore.model.CurrentlyPlaying = await self.spotify.playback_currently_playing()
        Logger.log("Getting playback state.")

        if self.current_playback != None:
            # Handle unknown type. Usually happens after a reboot. Proceed once the state has been updated.
            if self.current_playback.currently_playing_type == "unknown":
                self.current_playback = None
                await self.wait_for_state()

            # Check for ads.
            if self.current_playback.currently_playing_type == "ad":
                Logger.log("\nAd detected! Rebooting Spotify.\n", True)
                self.old_song = None
                self.reload_spotify()

            # Set the song duration and wait.
            else:
                song = self.current_playback.item
                if self.current_playback.item != self.old_song:
                    artists = ", ".join([artist.name for artist in song.artists])

                    if artists.isprintable() and song.name.isprintable():
                        Logger.log(f"Now Playing: \"{song.name}\" by {artists}", True)

                seconds_left = (self.current_playback.item.duration_ms - self.current_playback.progress_ms) / 1000
                # This happens when the API says the song is done but the player is behind. Give some time for the player to catch up.
                if seconds_left == 0:
                    Logger.log("Song has ended but the player is behind. Waiting...")
                    time.sleep(1)
                    return
                
                self.old_song = self.current_playback.item

                # Wait for the song to end.
                self.is_playing_song = True
                self.evnt.clear()
                self.evnt.wait(seconds_left + 1.5) # Add 1.5s to the wait time to mitigate the player being behind the API. We don't want to delay too much because the ad will play for longer (if there is one).
                self.is_playing_song = False
        
        # Usually we receive an empty playback when the Spotify app wasn't given enough time to communicate with the API.
        else:
            await self.wait_for_state()

    # Check every time period for a usable state. We can check at this interval because no ads should be playing.
    async def wait_for_state(self):
        Logger.log("Current playback is unavailable. Waiting for a better state...", True)

        while self.current_playback == None:
            time.sleep(30)
            Logger.log("Trying to get a better state...")

            pb = await self.spotify.playback_currently_playing()
            if pb != None and pb.currently_playing_type != "unknown":
                self.current_playback = pb
                break

    # Reopen Spotify and play the next song.
    def reload_spotify(self):
        Logger.log("Reloading Spotify...")

        # Stop the current thread.
        self.process_handler.restarting = True
        self.process_handler.join()

        # Create a new thread.
        self.process_handler = ProcessHandler(self.evnt, app)
        self.process_handler.program = self

        import win32gui, win32com.client, pyautogui
        prev = pyautogui.getActiveWindow()._hWnd

        self.process_handler.restart_process()
        self.process_handler.window.minimize()
        
        # Give focus back to the previous app.
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys("{F16}")
        win32gui.SetForegroundWindow(prev)

        # Play the next track.
        while self.process_handler.is_meter_available() == None:
            self.process_handler.window.send_message(0x0319, 0, 720896) # https://stackoverflow.com/questions/31733002/how-to-interact-with-spotifys-window-app-change-track-etc
            time.sleep(0.5)

        # Waits for the Spotify app to process inputs above.
        time.sleep(4.5)
        self.process_handler.start() # Start listening for window updates again.

async def main(program):
    if program.process_handler.is_state_valid:
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
        program = Program(token, evnt, process_handler)
        process_handler.program = program
        process_handler.start()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            loop.run_until_complete(main(program))

    except:
        Logger.log(traceback.format_exc(), True)
        input("Error detected. Press ENTER to close...")