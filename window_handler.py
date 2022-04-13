import threading, traceback
import _ctypes

class WindowHandler(threading.Thread):
    def __init__(self, evnt, window):
        self.can_check_ads = False
        self.evnt = evnt
        self.window = window
        self.program = None
        threading.Thread.__init__(self)

    def run(self):
        while True:
            if not self.program.restarting:
                self.poll_window_state()

    def poll_window_state(self):
        try:
            if self.window.is_normal():
                self.can_check_ads = False
                # stop the blocking timer that waits to check for ads after the song
                self.evnt.set()
                self.evnt.clear()
            elif self.window.is_minimized():
                self.can_check_ads = True
        # in uncommon cases, the window will not be available. if the program is not restarting and we get an error, print it
        except _ctypes.COMError:
            if not self.program.restarting:
                print(traceback.format_exc())
                input("Error detected. Press ENTER to close...")
