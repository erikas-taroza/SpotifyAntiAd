import threading, time, os, pyautogui, win32con
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
            is_active = pyautogui.getActiveWindow()._hWnd == self.window.handle

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
            # Handle app disconnect.
            if not self.app.is_process_running():
                self.handle_lost_process()

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

    # Returns the Spotify session if it is available.
    def is_meter_available(self):
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            if session.Process and session.Process.name() == "Spotify.exe":
                return session

        return None

    def restart_process(self):
        # Gracefully close all windows (like pressing the X button).
        for win in self.app.windows():
            win.send_message(win32con.WM_CLOSE, 0, 0)
        time.sleep(0.5)
        self.app.kill()
        self.start_process(True)

    # Tries to connect to Spotify if it is already started. Otherwise, it starts a new Spotify instance.
    def start_process(self, force_start = False):
        if force_start:
            self.app.start(spotify_path + " --minimized")
        else:
            try:
                self.app.connect(path = spotify_path[1:-1], timeout = 1) # Gets the first process opened from the path.
                Logger.log("Connected to existing Spotify instance.")
            except:
                self.app.start(spotify_path)
                
        time.sleep(0.5)
        self.window = self.app.Chrome_WidgetWin_0

    # Tries to reconnect to Spotify every second.
    def handle_lost_process(self):
        self.is_state_valid = False
        self.audio_meter = None
        self.program.old_song = None # Allows the Now Playing message to be reprinted if the same song is still playing.
        Logger.log("\nConnection to Spotify has been lost. Waiting for Spotify to reopen...", True)

        while not self.app.is_process_running():
            try:
                self.app.connect(path = spotify_path[1:-1], timeout = 1)
                Logger.log("Reconnected to Spotify.\n", True)
                break
            except:
                time.sleep(1)