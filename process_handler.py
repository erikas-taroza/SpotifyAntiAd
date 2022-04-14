import threading, time
from pycaw.pycaw import AudioSession, AudioUtilities
from pycaw.api.endpointvolume import IAudioMeterInformation

class ProcessHandler(threading.Thread):
    def __init__(self, evnt, window):
        threading.Thread.__init__(self)
        self.can_check_ads = False
        self.evnt = evnt
        self.window = window
        self.restarting = False
        self.audio_meter = None

    def run(self):
        while True:
            if not self.restarting:
                self.poll_process_state()

    # Check if the process (Spotify) is giving audio output.
    def poll_process_state(self):
        vol = self.try_get_meter()
        if vol == 0 or self.window.windows()[0].is_active():
            self.can_check_ads = False
            self.evnt.set()
            self.evnt.clear()
        elif vol > 0:
            self.can_check_ads = True
        time.sleep(3)

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

    def set_restarting(self, value):
        self.restarting = value
        if value:
            self.audio_meter = None