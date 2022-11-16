import aubio
import numpy as np
import osc_client
import pyaudio
import threading
import collections


class BeatPrinter:
    def __init__(self):
        self.state: int = 0
        self.spinner = "▚▞"

    def print_bpm(self, bpm: float) -> None:
        print(f"{self.spinner[self.state]}\t{bpm:.1f} BPM")

        self.state = (self.state + 1) % len(self.spinner)


class BeatDetector:

    def __init__(self, client: osc_client.OSCclient, audio_device_index: int = 1, parent=None, buf_size: int = 128, verbose: bool = False):
        self.parent = parent  # MainFrame
        self.buf_size: int = buf_size  # buffer size
        self.verbose: bool = verbose  # Print BPM to console
        self.client = client  # OSC client
        self.blink = 0  # blinking state flag

        self.level_queue = collections.deque(maxlen=20)  # RMS Level queue
        self.level_reset = None  # Timer for resetting level
        self.audio_device_index = audio_device_index
        self.samplerate: int = 44100

        # Set up pyaudio and aubio beat detector
        self.p: pyaudio.PyAudio = pyaudio.PyAudio()

        # Callback to GUI
        if self.parent is not None:
            self.stream: pyaudio.Stream = self.p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.samplerate,
                input=True,
                input_device_index=self.audio_device_index,
                frames_per_buffer=self.buf_size,
                stream_callback=self._GUI_callback
            )
            """def reset_level():
                print("reset self.level")
                if self.parent.running:
                    self.level = [0]
            
            self.level_reset = threading.Timer(0.25, reset_level)
            self.level_reset.start()"""

        # Callback to Console
        else:
            self.stream: pyaudio.Stream = self.p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.samplerate,
                input=True,
                frames_per_buffer=self.buf_size,
                stream_callback=self._STANDALONE_callback
            )

        fft_size: int = self.buf_size * 2
        self.tempo = aubio.tempo("default", fft_size, self.buf_size, self.samplerate)

        # Set up OSC clients to send beat data to
        if self.verbose:
            self.spinner = BeatPrinter()

    def vu_meter(self, signal):
        #t0 = time.time_ns()

        # cur = np.sqrt((signal*signal).sum()/(1.*len(signal)))*10000 #10,1ms
        self.level = np.sqrt(signal.dot(signal)/signal.size) * 10000  # 9,0ms
        # cur = np.sqrt(np.mean(np.square(signal))) * 10000 #23,5ms
        # cur = np.max(np.abs(signal))*10000 #12,0ms

        #self.timings.append(time.time_ns() - t0)
        print(self.level)
        """if cur > self.amp:
            self.amp = cur
        elif self.amp > 0:
            self.amp -= 15
        #print(self.amp/100)
        #print('█'*round(self.amp/100))
        """

    def _GUI_callback(self, in_data, frame_count, time_info, status):
        """Callback for pyaudio stream\n
        Calculates BPM and sends them to the GUI\n
        Calculates RMS Level into variable self.level to fetch by PeakMeter\n
        Args:
            in_data (array): data from pyaudio stream
            frame_count (int): number of frames in in_data
            time_info (): time info from pyaudio stream
            status (): status from pyaudio stream

        Returns:
            None, paContinue: Tells pyaudio to continue streaming
        """

        signal = np.frombuffer(in_data, dtype=np.float32)
        beat = self.tempo(signal)

        # Calculate RMS Level for every frame and add it to a circular buffer
        self.level_queue.append(int(np.sqrt(signal.dot(signal)/signal.size) * 200))  # 9,0ms

        if beat[0]:

            bpm = round(self.tempo.get_bpm())

            if bpm > 20 and bpm < 200 and self.parent.running:

                if self.parent.sync:

                    # SEND to osc and BOTH display if sync is on
                    self.client.send_osc(self.parent.config['OSC']['BPM_ADRESS'], bpm, map_to_resolume=True)
                    threading.Thread(self.parent.update_bpm_display(bpm, send_to="both", Blink=True)).start()

                    # BLINK resync button to beat when syncing (tap thread taking over when no sync)
                    self.parent.button_resync.BackgroundColour = (220, 220, 220) if self.blink else self.parent.bg_grey
                    self.blink = not self.blink

                else:
                    # SEND only to LIVE display if sync is off
                    threading.Thread(self.parent.update_bpm_display(bpm, send_to="live", Blink=False)).start()

        if self.parent.running:
            return (None, pyaudio.paContinue)
        else:
            return (None, pyaudio.paComplete)

    def _STANDALONE_callback(self, in_data, frame_count, time_info, status):
        signal = np.frombuffer(in_data, dtype=np.float32)
        beat = self.tempo(signal)
        if beat[0]:
            self.spinner.print_bpm(self.tempo.get_bpm())

        return None, pyaudio.paContinue  # Tell pyAudio to continue

    def resync_bar(self):
        """Send resync command to Resolume"""
        self.client.send_osc(self.parent.config['OSC']['RESYNC_BAR_ADRESS'], 1)

    def __del__(self):
        """Close pyaudio stream and terminate pyaudio
        """
        if self.level_reset is not None:
            self.level_reset.cancel()
        self.stream.close()
        self.p.terminate()


def test():
    import os
    import time

    client = osc_client.OSCclient("127.0.0.1", 7000)
    bd = BeatDetector(client, verbose=True, buf_size=128)
    try:
        # Audio processing happens in separate thread, so put this thread to sleep
        if os.name == 'nt':  # Windows is not able to pause the main thread :(
            while True:
                time.sleep(1)
        else:
            signal.pause()
    except:
        # print(sum(bd.timings)/len(bd.timings))
        pass


if __name__ == "__main__":
    test()
