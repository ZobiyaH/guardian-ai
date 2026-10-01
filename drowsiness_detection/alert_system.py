import winsound
import threading
import time

class AlertSystem:
    def __init__(self):
        self.is_playing = False
        self.alarm_thread = None
        
    def play_alarm(self):
        # Play a continuous warning sound while flagged as playing
        while self.is_playing:
            # 2500 Hz frequency, 300 ms duration for an aggressive urgent beep
            winsound.Beep(2500, 300)
            time.sleep(0.1)
            
    def trigger(self):
        # Start the alarm thread if not already playing
        if not self.is_playing:
            self.is_playing = True
            self.alarm_thread = threading.Thread(target=self.play_alarm)
            self.alarm_thread.daemon = True
            self.alarm_thread.start()
            
    def stop(self):
        # Gracefully stop the alarm
        self.is_playing = False
        if self.alarm_thread is not None:
            self.alarm_thread.join(timeout=0.5)
