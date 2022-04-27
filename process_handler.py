import threading, time, os, pyautogui
from pycaw.pycaw import AudioUtilities
from pycaw.api.endpointvolume import IAudioMeterInformation
from pywinauto import Application, WindowSpecification
from logger import Logger

spotify_path_quotations = "\"{}\\AppData\\Roaming\\Spotify\\Spotify.exe\"".format(os.path.expanduser("~"))
spotify_path_normal = os.path.expanduser("~") + "\\AppData\\Roaming\\Spotify\\Spotify.exe"

class ProcessHandler(threading.Thread):
    def __init__(self, evnt, app):
        threading.Thread.__init__(self)
        self.evnt: threading.Event = evnt
        self.app: Application = app
        self.window: WindowSpecification = None
        self.is_state_valid = False
        self.restarting = False
        self.audio_meter: IAudioMeterInformation = None
        self.program = None

    def run(self):
        while True:
            if not self.restarting:
                self.poll_process_state()

    # Check if the process (Spotify) is giving audio output.
    def poll_process_state(self):
        vol = self.try_get_meter()
        try:
            is_active = pyautogui.getActiveWindow()._hWnd == self.window.backend.element_info_class.get_active().parent.handle
            if vol == 0 or is_active:
                self.is_state_valid = False

                # Make sure that we are only resetting the event if we are supposed to.
                # Fixes the issue where the API gets called again because the event reset since it passed the if statement above.
                if is_active or self.program.old_song != self.program.current_playback.item or not self.program.is_song_playing:
                    self.evnt.set()
                    self.evnt.clear()
            elif vol > 0:
                self.is_state_valid = True

        # Sometimes the window will be None. Just continue.
        except:
            return

    # Try to get the audio meter. If it doesn't exist, wait until Spotify provides an audio output.
    def try_get_meter(self) -> int:
        try:
            return self.audio_meter.GetPeakValue()
        except AttributeError:
            Logger.log("\nCould not get audio output from Spotify. Waiting for output...")
            while self.audio_meter == None:
                session = self.is_meter_available()
                if session != None:
                    self.audio_meter = session._ctl.QueryInterface(IAudioMeterInformation)
                time.sleep(1)
            Logger.log("Got audio output.\n")
            return self.audio_meter.GetPeakValue()

    def is_meter_available(self):
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            if session.Process and session.Process.name() == "Spotify.exe":
                return session

        return None

    def restart_process(self):
        self.restarting = True
        self.audio_meter.Release()

        self.app.kill(soft = True)
        time.sleep(2)
        self.start_process()
        

        # Not set here because we wait some time for the Spotify API to get the play input. Set in Program.reload_spotify()
        #self.restarting = False

    def start_process(self):
        try:
            self.app.start(spotify_path_quotations)
        except:
            try:
                self.app.start(spotify_path_normal)
            except:
                Logger.log("Unable to open Spotify.")
        finally:
            time.sleep(1)
            self.window = self.app.Spotify