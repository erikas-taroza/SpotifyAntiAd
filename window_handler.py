import threading, time

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
        if self.window.is_normal():
            self.can_check_ads = False
            # stop the blocking timer that waits to check for ads after the song
            self.evnt.set()
            self.evnt.clear()
        elif self.window.is_minimized():
            self.can_check_ads = True
