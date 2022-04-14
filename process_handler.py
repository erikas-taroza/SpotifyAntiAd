import threading, pyautogui
from pycaw.pycaw import AudioSession, AudioUtilities
from pycaw.api.endpointvolume import IAudioMeterInformation

class ProcessHandler(threading.Thread):
    def __init__(self, evnt):
        threading.Thread.__init__(self)
        self.can_check_ads = False
        self.evnt = evnt
        self.program = None
        self.audio_meter = None

        # Make Spotify findable
        pyautogui.press("playpause")
        pyautogui.press("playpause")
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            session: AudioSession
            if session.Process and session.Process.name() == "Spotify.exe":
                self.audio_meter = session._ctl.QueryInterface(IAudioMeterInformation)

    def run(self):
        while True:
            if not self.program.restarting:
                self.poll_process_state()

    # Check if the process (Spotify) is giving audio output.
    def poll_process_state(self):
        if self.audio_meter.GetPeakValue() == 0:
            self.can_check_ads = False
            self.evnt.set()
            self.evnt.clear()
        else:
            self.can_check_ads = True
