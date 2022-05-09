import threading, time, os, pyautogui
from pycaw.pycaw import AudioUtilities
from pycaw.api.endpointvolume import IAudioMeterInformation
from pywinauto import Application, WindowSpecification
from logger import Logger

spotify_path = "\"{}\\AppData\\Roaming\\Spotify\\Spotify.exe\"".format(os.path.expanduser("~"))

class ProcessHandler(threading.Thread):
    def __init__(self, evnt, app):
        threading.Thread.__init__(self)
        self.name = "ProcessHandlerThread"
        
        self.evnt: threading.Event = evnt
        self.app: Application = app
        self.window: WindowSpecification = None
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
                if is_active or self.program.old_song != self.program.current_playback.item or not self.program.is_song_playing:
                    self.evnt.set()
                    self.evnt.clear()
            elif vol > 0 and not is_active:
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
        time.sleep(0.5)
        self.start_process()

    def start_process(self):
        self.app.start(spotify_path)
        time.sleep(0.5)
        self.window = self.app.Chrome_WidgetWin_0