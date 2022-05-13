import threading, time, os, pyautogui
from pycaw.pycaw import AudioUtilities
from pycaw.api.endpointvolume import IAudioMeterInformation
from pywinauto import Application, controls
from logger import Logger

spotify_path = "\"{}\\AppData\\Roaming\\Spotify\\Spotify.exe\"".format(os.path.expanduser("~"))

class ProcessHandler(threading.Thread):
    def __init__(self, evnt, app):
        threading.Thread.__init__(self)
        self.name = "ProcessHandlerThread"
        
        self.evnt: threading.Event = evnt
        self.app: Application = app
        self.window: controls.hwndwrapper.HwndWrapper = None
        self.is_state_valid = False
        self.restarting = False
        self.audio_meter: IAudioMeterInformation = None
        self.program = None

    def run(self):
        while not self.restarting:
            self.poll_process_state()

    # Check if the process (Spotify) is giving audio output.
    def poll_process_state(self):
        vol = self.try_get_meter()

        try:
            active_window = pyautogui.getActiveWindow()
            is_active = active_window._hWnd == self.window.handle and not active_window.isMinimized

            if vol == 0 or is_active:
                self.is_state_valid = False

                # Make sure that we are only resetting the event if we are supposed to.
                # Fixes the issue where the API gets called again because the event reset since it passed the if statement above.
                if is_active  or not self.program.is_playing_song:
                    if not self.evnt.isSet():
                        self.evnt.set()
                        
            elif vol > 0 and not is_active:
                self.is_state_valid = True

        # Sometimes the window will be None. Just continue.
        except:
            if not self.app.is_process_running():
                self.is_state_valid = False
                self.restarting = True
                Logger.log("Connection to Spotify has been lost. Restart the program to reconnect.", True)
            return

    # Try to get the audio meter. If it doesn't exist, wait until Spotify provides an audio output.
    def try_get_meter(self) -> float:
        try:
            return self.audio_meter.GetPeakValue()
        except AttributeError:
            Logger.log("\nCould not get audio output from Spotify. Waiting for output...")

            while self.audio_meter == None:
                session = self.is_meter_available()
                if session != None:
                    self.audio_meter = session._ctl.QueryInterface(IAudioMeterInformation)

            Logger.log("Got audio output.\n")
            return self.audio_meter.GetPeakValue()

    def is_meter_available(self):
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            if session.Process and session.Process.name() == "Spotify.exe":
                return session

        return None

    def restart_process(self):
        self.app.kill()
        self.start_process(True)

    # Tries to connect to Spotify if it is already started. Otherwise, it starts a new Spotify instance.
    def start_process(self, force_start = False):
        if force_start:
            self.app.start(spotify_path)
        else:
            try:
                self.app.connect(path = spotify_path[1:-1], timeout = 1) # Gets the first process opened from the path.
                Logger.log("Connected to existing Spotify instance.")
            except:
                self.app.start(spotify_path)
                
        time.sleep(0.5)
        self.window = self.app.Chrome_WidgetWin_0