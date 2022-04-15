import threading, time, os, pyautogui
from pycaw.pycaw import AudioSession, AudioUtilities
from pycaw.api.endpointvolume import IAudioMeterInformation

spotify_path = os.path.expanduser("~") + "\\AppData\\Roaming\\Spotify\\Spotify.exe"

class ProcessHandler(threading.Thread):
    def __init__(self, evnt, app):
        threading.Thread.__init__(self)
        self.evnt = evnt
        self.app = app
        self.window = self.app.windows()[0]
        self.is_state_valid = False
        self.restarting = False
        self.audio_meter = None
        self.program = None

    def run(self):
        while True:
            if not self.restarting:
                self.poll_process_state()

    # Check if the process (Spotify) is giving audio output.
    def poll_process_state(self):
        vol = self.try_get_meter()
        try:
            
            is_active = pyautogui.getActiveWindow()._hWnd == self.window.element_info.handle
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
            while self.audio_meter == None:
                sessions = AudioUtilities.GetAllSessions()
                for session in sessions:
                    session: AudioSession
                    if session.Process and session.Process.name() == "Spotify.exe":
                        self.audio_meter = session._ctl.QueryInterface(IAudioMeterInformation)
                time.sleep(1)
            return self.audio_meter.GetPeakValue()

    def restart_process(self):
        self.restarting = True
        self.audio_meter = None

        self.app.kill()
        time.sleep(2)
        self.app.start(spotify_path)
        time.sleep(1)
        self.window = self.app.windows()[0]

        # Not set here because we wait some time for the Spotify API to get the play input. Set in Program.reload_spotify()
        #self.restarting = False