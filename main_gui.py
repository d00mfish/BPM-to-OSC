#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python version: 3.9.13 64-Bit
# WxPython: v4.1.1
#
# Autor: Leonhard Axtner (d00mfish) 2022
# Developed with VSCode using following Plugins:
#   Python, Pylance, GitLens, German language pack,Python Docstring Generator
#
# TODO:
# - Other output (Midi clock?)
# - Darkmode?

# Imports:
from os import remove, system
from pathlib import Path
from subprocess import call
from platform import system
from time import time
from threading import Thread, Event

# local
from sevensegment import SevenSegmentDisp
import beatfinder
import osc_client

import configparser
import pyaudio


import wx
import wx.lib.masked.ipaddrctrl as ipctrl
import wx.lib.agw.peakmeter as PM


class Main_Frame(wx.Frame):
    '''Frame Class
    '''
    sel_msg_frame = None
    sel_bus_frame = None
    CONF_PATH = Path(Path.home(), "AppData/Roaming/BPMtoOSC/lastsession.ini")
    #CONF_PATH = Path("lastsession.ini")

    def __init__(self, parent=None):
        """Initialize Config Window
            - Reads config file and sets variables
            - Initializes GUI
        """
        # wx.Frame init
        style_dep = wx.DEFAULT_FRAME_STYLE ^ wx.MAXIMIZE_BOX  # ^ wx.RESIZE_BORDER
        super(Main_Frame, self).__init__(parent, title="BPMtoOSC", style=style_dep)

        # Config Setup
        self.config = configparser.ConfigParser()

        # Manage close event
        wx.CloseEvent.SetCanVeto(wx.CloseEvent(), False)

        # Audio Setup
        self.audio = pyaudio.PyAudio()
        self.audio_device = 1

        # OSC Setup
        self.osc_client = None

        # BPM Setup
        self.beatfinder = None  # audio analysis instance
        self.send_bpm = 128  # sent bpm when sync is diasabled (used to hold last live or tap value)
        self.beat_divider = 1  # divides beat to get 1/2, 1/4
        self.no_sync_send_thread = Thread(target=self.send_thread_when_no_sync)

        self.bpm_thread_wait_and_terminate = Event()  # c based event to wait in thread or terminate
        self.bpm_thread_wait_and_terminate.clear()

        self.last_tap = list()  # list of taps to determine bpm
        self.buttons_to_disable = list()  # list of buttons to disableon start/stop

        # Flags
        self.bpm_blink = False  # Blinking sevenseg background
        self.sync = True  # sync live bpm to send bpm
        self.resync = False  # resync to bar
        self.running = False
        self.retrys = 3
        self.led_counter = 3

        self.Read_LastSession_ini()
        self.InitUI()

        self.Centre()  # centre window on screen

# PEAK METER
        self.uv_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnUVTimer)

        self.uv_timer.Start(20)
        # self.peak_meter.Start(50)
        #self.peak_meter.SetData(0, 0, 1)

    def OnUVTimer(self, event):
        if self.running:
            avg = [sum(self.beatfinder.level_queue)/len(self.beatfinder.level_queue)
                   if len(self.beatfinder.level_queue) > 0 else 0]
            # print(avg)
            self.peak_meter.SetData(avg, 0, 1)
            pass

    def Read_LastSession_ini(self):
        """Reading / creating lastsession.ini
        """
        try:
            # if no config found, create one with default values
            self.config.read(self.CONF_PATH)
            if self.config.sections() == []:
                self.config['OSC'] = {'IP': '127.000.000.001',
                                      'PORT': 7000,
                                      'RESYNC_BAR_ADRESS': '/composition/tempocontroller/resync',
                                      'BPM_ADRESS': '/composition/tempocontroller/tempo'}
                self.config['AUDIO'] = {'device_index': '1'}
        except:
            if self.retrys > 0:
                self.retrys -= 1
                print("Error reading config file. Deleting and creating new one.")
                remove(self.CONF_PATH)
                self.Read_LastSession_ini()

    def InitUI(self):
        """Actual GUI Setup of main config Window
        """

        panel = wx.Panel(self)
        sizer = wx.GridBagSizer(14, 4)
        
        # 7seg background blink
        self.bg_grey = wx.Colour(240, 240, 240)
        self.bg_a = (self.bg_grey,(220, 220, 220))
        #self.bg_b = (220, 220, 220), self.bg_grey

        buttonfont = wx.Font(20, family=wx.DEFAULT, style=wx.NORMAL, weight=wx.BOLD)

        # Title Connect to Box
        self.ip_stuff_sizer = wx.StaticBoxSizer(wx.HORIZONTAL, panel, label="OSC Adress and Port")
        #title_connect = wx.StaticText(panel, label="OSC Adress and Port")

        # Textbox IP-Adress
        self.text_ip = ipctrl.IpAddrCtrl(panel)
        self.text_ip.SetValue(self.config['OSC']['IP'])
        self.ip_stuff_sizer.Add(self.text_ip, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, border=5)

        # Numberbox Port
        self.text_port = wx.SpinCtrl(panel)
        self.text_port.SetMax(65535)
        self.text_port.SetMin(0)
        self.text_port.SetValue(self.config['OSC']['PORT'])
        self.ip_stuff_sizer.Add(self.text_port, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, border=5)
        
        #self.ip_stuff_sizer.AddStretchSpacer()

        """# Textbox OSC Adress
        self.osc_adress_box = wx.TextCtrl(panel, value=self.config['OSC']['BPM_ADRESS'])
        self.ip_stuff_sizer.Add(self.osc_adress_box, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, border=5)
        # self.ip_stuff_sizer.AddStretchSpacer()

        # Send Value Selection
        self.send_format = wx.Choice(panel, choices=["Resolume BPM", "Actual BPM", "True / False"])
        print(self.config['OSC']['BPM_SEND_FORMAT'])
        self.send_format.SetSelection(int(self.config['OSC']['BPM_SEND_FORMAT']))
        self.ip_stuff_sizer.Add(self.send_format, 0, wx.LEFT | wx.ALIGN_CENTER, border=5)"""

        # Text Connectionstatus
        self.text_connection = wx.StaticText(panel, label="", style=wx.EXPAND | wx.ALIGN_RIGHT | wx.ALIGN_BOTTOM)
        self.text_connection.SetFont(wx.Font(12, family=wx.DEFAULT, style=wx.NORMAL, weight=wx.BOLD))
        self.text_connection.SetBackgroundColour(self.bg_grey)
        # Enter current status after trying to connect with ini information
        self.ip_stuff_sizer.Add(self.text_connection, 2, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, border=5)

        

        # Button Ping
        self.button_ping = wx.Button(panel, wx.ID_ANY, label="Ping")
        self.ip_stuff_sizer.Add(self.button_ping, 0, wx.RIGHT | wx.LEFT | wx.ALIGN_CENTER, border=5)
        self.Bind(wx.EVT_BUTTON, self.on_button_ping, self.button_ping)
        
        sizer.Add(self.ip_stuff_sizer, pos=(0, 0), span=(2, 4), flag=wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, border=10)
        #sizer.Add(self.ip_stuff_sizer, pos=(1, 0), span=(1, 4), flag=wx.EXPAND, border=10)

        # Title Open File
        audiosizer = wx.StaticBoxSizer(wx.HORIZONTAL, panel, label="Audio Input Device")

        # Audio device selection
        self.audio_selection = wx.ComboBox(panel, style=wx.CB_READONLY)
        self.on_button_reload(None)  # fill combobox with devices
        self.audio_selection.SetSelection(int(self.config['AUDIO']['device_index']))

        audiosizer.Add(self.audio_selection, 2, wx.EXPAND | wx.ALL, border=5)

# PEAK METER
        self.peak_meter = PM.PeakMeterCtrl(panel, -1, style=wx.SIMPLE_BORDER, agwStyle=PM.PM_HORIZONTAL)
        self.peak_meter.SetMeterBands(1, 48)
        self.peak_meter.SetFalloffEffect(False)
        self.peak_meter.SetBandsColour((150, 220, 150), (255, 255, 150), (220, 150, 150))
        self.peak_meter.SetRangeValue(20, 60, 80)
        #self.peak_meter.SetData([0], 0, 1)

        audiosizer.Add(self.peak_meter, 2, wx.EXPAND | wx.ALL | wx.FIXED_MINSIZE, border=5)

        sizer.Add(audiosizer, pos=(2, 0), span=(1, 4), flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        # Disabled reload button as pyaudio needs a complete restart to reload devices
        """ # Button Reload devices
        self.button_reload = wx.Button(panel, wx.ID_ANY, label="Reload")
        sizer.Add(self.button_reload, pos=(3, 3), flag=wx.TOP | wx.RIGHT, border=10)
        self.Bind(wx.EVT_BUTTON, self.on_button_reload, self.button_reload)"""

# SEPARATOR
        line1 = wx.StaticLine(panel)
        sizer.Add(line1, pos=(3, 0), span=(1, 4), flag=wx.EXPAND, border=10)

# BEAT LEDS

        beat_led_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.leds = []

        for i in range(4):
            #led = wx.TextCtrl(panel, value="", style=wx.TE_READONLY | wx.BORDER_STATIC)
            led = wx.StaticText(panel, label="", style=wx.BORDER_STATIC)
            led.SetFont(wx.Font(15, family=wx.DEFAULT, style=wx.NORMAL, weight=wx.BOLD))
            led.SetBackgroundColour((50, 0, 0))
            self.leds.append(led)

        for led in self.leds:
            beat_led_sizer.Add(led, 1, wx.EXPAND | wx.RIGHT | wx.LEFT, border=5)

        sizer.Add(beat_led_sizer, pos=(4, 0), span=(1, 4), flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=5)

# SEVEN SEGMENT DISPLAYS
        sevenseg_sizer = wx.BoxSizer(orient=wx.HORIZONTAL)

        self.live_disp = (SevenSegmentDisp(panel), SevenSegmentDisp(panel), SevenSegmentDisp(panel))
        self.send_disp = (SevenSegmentDisp(panel), SevenSegmentDisp(panel), SevenSegmentDisp(panel))

        # DISPLAY 1
        bpm_box_live = wx.StaticBoxSizer(wx.HORIZONTAL, panel, label="LIVE")
        for digit in self.live_disp:
            digit.SetTilt(5)
            digit.SetColours(segment_on=((0, 71, 77)), background=self.bg_grey, segment_off=(220, 220, 220))
            digit.SetGeometry(width=38, height=38, thickness=10, separation=2)
            digit.EnableDot(False)
            digit.EnableColon(False)
            digit.SetValue("-")
            bpm_box_live.Add(digit, 1, wx.EXPAND | wx.DOWN, 5)

        # DISPLAY 2
        bpm_box_sending = wx.StaticBoxSizer(wx.HORIZONTAL, panel, label="SEND")
        for digit in self.send_disp:
            digit.SetTilt(5)
            digit.SetColours(segment_on=(85, 0, 0), background=self.bg_grey, segment_off=(220, 220, 220))
            digit.SetGeometry(width=38, height=38, thickness=10, separation=2)
            digit.EnableDot(False)
            digit.EnableColon(False)
            digit.SetValue("-")
            bpm_box_sending.Add(digit, 1, wx.EXPAND | wx.DOWN, 5)

        sevenseg_sizer.Add(bpm_box_live, 3, wx.EXPAND | wx.LEFT, 10)
        

# SYNC BUTTON
        self.sevenseg_button_sizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.button_sync = wx.ToggleButton(panel, label='S\nY\nN\nC')  # \n➜
        self.button_sync.SetForegroundColour((150, 220, 150))
        self.button_sync.SetValue(True)
        #self.button_sync.SetFont(wx.Font(25, family=wx.DEFAULT, style=wx.NORMAL, weight=wx.BOLD))
        self.button_sync.SetFont(buttonfont)
        self.buttons_to_disable.append(self.button_sync)
        #sevenseg_sizer.Add(self.button_sync, 1, wx.EXPAND | wx.UP, 5)
        self.sevenseg_button_sizer.Add(self.button_sync, 3, wx.EXPAND, 5)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_button_sync, self.button_sync)
        
# Live Halftime Button
        self.button_halftime = wx.ToggleButton(panel, label='1/2')
        self.button_halftime.SetFont(buttonfont)
        self.buttons_to_disable.append(self.button_halftime)
        self.sevenseg_button_sizer.Add(self.button_halftime, 1, wx.EXPAND, 5)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_button_halftime, self.button_halftime)
        
        # add the sevensesg button sizer between the displays
        sevenseg_sizer.Add(self.sevenseg_button_sizer, 1, wx.EXPAND | wx.UP, 5)
        sevenseg_sizer.Add(bpm_box_sending, 3, wx.EXPAND | wx.RIGHT, 10)

        sizer.Add(sevenseg_sizer, pos=(5, 0), span=(3, 4), flag=wx.EXPAND, border=10)


# BUTTONS: |  RE-   | +1 | -1 |
#          | SYNC   | x2 | /2 |
#         |  >||   |  TAP    |

# up/down/x2/:2 BUTTONS
        button_sizer = wx.BoxSizer(orient=wx.VERTICAL)

        sub_button_sizer_top = wx.BoxSizer(orient=wx.HORIZONTAL)

        sub_button_sizer_top_vert_1 = wx.BoxSizer(orient=wx.VERTICAL)
        sub_button_sizer_top_vert_2 = wx.BoxSizer(orient=wx.VERTICAL)

        self.button_plus_one = wx.Button(panel, label='+1')
        self.button_plus_one.SetFont(buttonfont)
        self.buttons_to_disable.append(self.button_plus_one)
        sub_button_sizer_top_vert_2.Add(self.button_plus_one, 1, flag=wx.EXPAND, border=10)
        self.Bind(wx.EVT_BUTTON, self.on_button_plus_one, self.button_plus_one)

        self.button_minus_one = wx.Button(panel, label='-1')
        self.button_minus_one.SetFont(buttonfont)
        self.buttons_to_disable.append(self.button_minus_one)
        sub_button_sizer_top_vert_1.Add(self.button_minus_one, 1, flag=wx.EXPAND, border=10)
        self.Bind(wx.EVT_BUTTON, self.on_button_minus_one, self.button_minus_one)

        self.button_double = wx.Button(panel, label='x2')
        self.button_double.SetFont(buttonfont)
        self.buttons_to_disable.append(self.button_double)
        sub_button_sizer_top_vert_2.Add(self.button_double, 1, flag=wx.EXPAND, border=10)
        self.Bind(wx.EVT_BUTTON, self.on_button_double, self.button_double)

        self.button_half = wx.Button(panel, label='/2')
        self.button_half.SetFont(buttonfont)
        self.buttons_to_disable.append(self.button_half)
        sub_button_sizer_top_vert_1.Add(self.button_half, 1, flag=wx.EXPAND, border=10)
        self.Bind(wx.EVT_BUTTON, self.on_button_half, self.button_half)

# RESYNC BUTTON

        self.button_resync = wx.Button(panel, label='RESYNC BAR')
        self.button_resync.SetFont(buttonfont)
        self.buttons_to_disable.append(self.button_resync)
        #sizer.Add(self.button_resync, pos=(12, 2), span=(2, 2),flag=wx.EXPAND | wx.ALL ^ wx.TOP, border=10)
        sub_button_sizer_top.Add(self.button_resync, 2, flag=wx.EXPAND, border=10)
        self.Bind(wx.EVT_BUTTON, self.on_button_resync, self.button_resync)

        sub_button_sizer_top.Add(sub_button_sizer_top_vert_1, 1, flag=wx.EXPAND, border=10)
        sub_button_sizer_top.Add(sub_button_sizer_top_vert_2, 1, flag=wx.EXPAND, border=10)

# START STOP & TAP BUTTON (BPM) BUTTON
        sub_button_sizer_bot = wx.BoxSizer(orient=wx.HORIZONTAL)

        self.button_startstop = wx.ToggleButton(panel, label='START / STOP')
        self.button_startstop.SetFont(buttonfont)
        #sizer.Add(self.button_startstop, pos=(12, 0), span=(2, 2),flag=wx.EXPAND | wx.ALL ^ wx.TOP, border=10)
        sub_button_sizer_bot.Add(self.button_startstop, 1, flag=wx.EXPAND, border=10)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_button_startstop, self.button_startstop)

        self.button_tap = wx.Button(panel, label='TAP')
        self.button_tap.SetFont(buttonfont)
        self.buttons_to_disable.append(self.button_tap)
        sub_button_sizer_bot.Add(self.button_tap, 1, flag=wx.EXPAND, border=10)
        #sizer.Add(self.button_tap, pos=(8, 0), span=(3, 4), flag=wx.EXPAND | wx.ALL ^ wx.TOP, border=10)
        self.Bind(wx.EVT_BUTTON, self.on_button_tap, self.button_tap)

        button_sizer.Add(sub_button_sizer_top, 3, flag=wx.EXPAND | wx.TOP, border=-5)
        button_sizer.Add(sub_button_sizer_bot, 3, flag=wx.EXPAND, border=10)
        sizer.Add(button_sizer, pos=(8, 0), span=(7, 4), flag=wx.EXPAND | wx.ALL ^ wx.TOP, border=10)

        for b in self.buttons_to_disable:
            b.Disable()

        # some window properties
        self.Bind(wx.EVT_CLOSE, self.close)
        self.SetMinSize(wx.Size(645, 650))
        self.SetMaxSize(wx.Size(950, 750))
        # self.SetBackgroundColour((92,92,92))
        sizer.AddGrowableCol(2)
        sizer.AddGrowableRow(7)
        panel.SetSizer(sizer)
        sizer.Fit(self)

    def on_button_plus_one(self, event):
        self.on_button_halftime(None, reset=True)
        self.next_led()
        if self.sync:
            self.switch_sync(False)
        if self.send_bpm < 499:
            self.send_bpm += 1
            self.update_bpm_display(self.send_bpm, send_to="send")

    def on_button_minus_one(self, event):
        self.on_button_halftime(None, reset=True)
        if self.sync:
            self.switch_sync(False)
        if self.send_bpm > 20:
            self.send_bpm -= 1
            self.update_bpm_display(self.send_bpm, send_to="send")

    def on_button_double(self, event):
        self.on_button_halftime(None, reset=True)
        if self.sync:
            self.switch_sync(False)
        if self.send_bpm*2 <= 500:
            self.send_bpm *= 2
            self.update_bpm_display(self.send_bpm, send_to="send")

    def on_button_half(self, event):
        self.on_button_halftime(None, reset=True)
        if self.sync:
            self.switch_sync(False)
        if self.send_bpm/2 >= 20:
            self.send_bpm = round(self.send_bpm/2)
            self.update_bpm_display(self.send_bpm, send_to="send")

    def on_button_halftime(self, event, reset=False):
        if reset:
            self.button_halftime.SetValue(False)
        
        self.beat_divider = 2 if self.button_halftime.GetValue() else 1


    def on_button_reload(self, event):
        """Reloads the audio devices"""

        self.audio_selection.Clear()

        info = self.audio.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')

        for i in range(numdevices):
            if (self.audio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                # self.device_list.append((i) + " - " + self.audio.get_device_info_by_host_api_device_index(0, i).get('name'))

                if i != 1:
                    self.audio_selection.Append(
                        self.audio.get_device_info_by_host_api_device_index(0, i).get('name'))
                else:
                    self.audio_selection.Append(
                        "DEFAULT: " + self.audio.get_device_info_by_host_api_device_index(0, i).get('name'))
        # self.audio_selection.Append(str(i) + " - " + self.audio.get_device_info_by_host_api_device_index(0, i).get('name'))

        # if function gets called from read last session
        if event is None:
            self.audio_selection.SetSelection(self.audio_device)

        """if event is not None:
            self.audio_selection.Popup()"""

    def on_button_tap(self, event):
        """count time between taps and calculate bpm\n
        Args:
            event (ex.EVENT): unused
        """

        # calculate only after 2+ tabs
        if len(self.last_tap) > 1:

            # add time and timedelta to list
            self.last_tap.append((time(), time() - self.last_tap[-1][0]))

            # Clear if previous taps are too old
            if time() - self.last_tap[-2][0] > 1:
                self.last_tap = [self.last_tap[-1]]

            else:
                # disable sync if it was enabled
                # this also starts the osc sending thread
                if self.sync:
                    self.switch_sync(False)

                # Calculate the BPM, set variable for thread and display it
                self.send_bpm = round(60 / (sum([x[1] for x in self.last_tap[1:]]) / len(self.last_tap[1:])))
                self.update_bpm_display(self.send_bpm, send_to="send")

        elif len(self.last_tap) == 1:
            self.last_tap.append((time(), time() - self.last_tap[-1][0]))

        else:
            # if no taps yet, add first tap
            self.last_tap.append((time(), None))

    def on_button_sync(self, event):
        self.switch_sync(self.button_sync.GetValue())
        self.button_resync.BackgroundColour = self.bg_grey

    def on_button_resync(self, event):
        # reset bar animation
        self.next_led(reset=True)

        # reset bpm timer
        self.resync = True
        self.bpm_thread_wait_and_terminate.set()

        if self.beatfinder:
            self.beatfinder.resync_bar()

        self.resync = False
        self.bpm_thread_wait_and_terminate.clear()

    def on_button_startstop(self, event):
        """Starts and stops the audio and OSC stream

        Args:
            event (wx.EVENT): unused
        """
        if self.button_startstop.GetValue():
            print("Starting")

            # save input to config
            self.config['AUDIO']['device_index'] = str(self.audio_selection.GetSelection())
            self.config['OSC']['IP'] = self.text_ip.GetValue().replace(" ", "")
            self.config['OSC']['PORT'] = str(self.text_port.GetValue())

            # create worker instances
            self.osc_client = osc_client.OSCclient(self.config['OSC']['IP'], int(self.config['OSC']['PORT']))
            self.beatfinder = beatfinder.BeatDetector(self.osc_client, self.audio_selection.GetSelection(), parent=self)

            # gui changes
            self.button_startstop.SetBackgroundColour((220, 150, 150))
            self.audio_selection.Disable()
            for b in self.buttons_to_disable:
                b.Enable()

            self.running = True

        else:
            print("Stopping")

            self.running = False

            # delete worker instances
            del self.beatfinder
            self.beatfinder = None
            del self.osc_client
            self.osc_client = None

            # gui changes
            self.audio_selection.Enable()
            for b in self.buttons_to_disable:
                b.Disable()
            self.button_startstop.SetBackgroundColour(wx.NullColour)
            self.peak_meter.SetData([0], 0, 1)
            self.update_bpm_display("---", send_to="both")

    def on_button_ping(self, event):
        '''Establish Websocket connection
            - Create Websocket connection
            - Set Status in Interface wether connected, connecting or connection error
        '''
        # set gui status: connecting
        wx.SetCursor(wx.Cursor(wx.CURSOR_WAIT))
        self.button_ping.Disable()
        #self.text_connection.SetForegroundColour((255, 206, 13))
        #self.text_connection.SetLabel("Pinging...")
        self.ip_stuff_sizer.Layout()

        # save input to config
        self.config['OSC']['IP'] = self.text_ip.GetValue()
        self.config['OSC']['PORT'] = str(self.text_port.GetValue())

        # send ping
        param = '-n' if system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', self.config['OSC']['IP'].replace(" ", "")]

        # success
        if call(command) == 0:
            self.text_connection.SetForegroundColour((0, 184, 0))
            self.text_connection.SetLabel("Reachable")
            self.ip_stuff_sizer.Layout()

        # no answer
        else:
            print('No ping answer')
            self.text_connection.SetForegroundColour((220, 0, 0))
            self.text_connection.SetLabel("Unreachable")
            self.ip_stuff_sizer.Layout()

        # gui restore
        wx.SetCursor(wx.Cursor(wx.CURSOR_DEFAULT))
        self.button_ping.Enable()

    def switch_sync(self, state: bool):
        """Changes state of sync flag and button\n
        Starts thread to emit "send bpm" 

        Args:
            state (bool): State to switch to
        """
        #stop sync
        if not state and self.sync:
            self.bpm_thread_wait_and_terminate.clear()  # clearing thread terminating event
            self.sync = False
            self.button_sync.SetForegroundColour((220, 150, 150))
            # self.button_sync.SetLabel('❌')
            
            self.button_sync.SetValue(False)
            
            #must be called first to get the beat_divider into the thread
            self.no_sync_send_thread = Thread(target=self.send_thread_when_no_sync)
            self.no_sync_send_thread.start()
            
            #self.button_halftime.SetValue(False)
            self.button_halftime.Disable()
            #self.on_button_halftime(None)

        #start sync
        elif state and not self.sync:
            self.bpm_thread_wait_and_terminate.set()  # setting thread terminating event
            self.sync = False
            self.sync = True
            self.button_sync.SetForegroundColour((150, 220, 150))
            # self.button_sync.SetLabel('➜')
            self.button_sync.SetValue(True)
            
            self.button_halftime.SetValue(True if self.beat_divider == 2 else False)
            self.button_halftime.Enable()
        else:
            print("Sync state already set to {}".format(state))

    def update_bpm_display(self, bpm, send_to: str = "both", Blink=False):
        """Iterates through digits and sets them accordinglly

        Args:
            bpm (int | str): bpm value to set
            send_to (str): wich display to update, can be "both", "live" or "send". Defaults to "both."
            Blink (bool, optional): wether the background should alternate color. Defaults to False.
        """
        # convert to array of chars

        def set_digits(bpm, send_to):

            bpm_digits = [d for d in str(bpm)]
            bpm_digits.reverse()

            def send_to_disp(disp):
                """actual update function

                Args:
                    disp (self.live_disp | self.send_disp): display to update
                """
                # set new background color
                new_bg = self.bg_a[::-1] if disp[0].GetColours()['background'] == self.bg_grey else self.bg_a
                
                for i, digit in enumerate(disp):

                    # set 0 in front if bpm has less than 3 digits
                    if len(bpm_digits) > 2:
                        digit.SetValue(bpm_digits[2-i])
                    else:
                        digit.SetValue(bpm_digits[2-i] if i > 0 else 0)

                    # blinking background
                    if Blink:
                        digit.SetColours(background=new_bg[0], segment_off=new_bg[1])


            # send to display
            if send_to == "both":
                send_to_disp(self.live_disp)
                send_to_disp(self.send_disp)
            elif send_to == "send":
                send_to_disp(self.send_disp)
            elif send_to == "live":
                send_to_disp(self.live_disp)

            self.bpm_blink = not (self.bpm_blink)

        Thread(target=set_digits, args=(bpm, send_to)).start()

    def next_led(self, reset=False, thread=True):

        def set_leds(rst):
            def set_background(led, color: tuple):
                # need to update label to see changes
                led.SetBackgroundColour(color)
                led.Refresh()
            if rst:
                set_background(self.leds[0], (200, 0, 0))
                set_background(self.leds[1], (50, 0, 0))
                set_background(self.leds[2], (50, 0, 0))
                set_background(self.leds[3], (50, 0, 0))
                if self.led_counter == 0:
                    self.led_counter = -1
                else:
                    self.led_counter = 3
            if self.led_counter < 3:
                set_background(self.leds[self.led_counter], (50, 0, 0))
                set_background(self.leds[self.led_counter+1], (200, 0, 0))
                self.led_counter += 1
            else:
                self.led_counter = 0
                set_background(self.leds[-1], (50, 0, 0))
                set_background(self.leds[self.led_counter], (200, 0, 0))

        if thread:
            Thread(target=set_leds, args=(reset,)).start()
        else:
            set_leds(reset)

    def send_thread_when_no_sync(self):
        """When sync is disabled, this thread sends the bpm showed in send display.\n
        This can either be an old live value or a tabbed in value.
        A more efficient way is needed.
        """
        """# time compensation over 4 beats to be more accurate
            beat_counter += 1
            if beat_counter == 1:
                prev = time.time() # time compensation
            elif beat_counter == 4:
                comp = (time.time() - prev) - ((60/self.send_bpm)*8)
                beat_counter = 0"""
        # trigger at least once set_osc
        prev_bpm = self.send_bpm
        self.send_bpm//=self.beat_divider
        #self.osc_client.send_osc(self.config['OSC']['BPM_ADRESS'], self.send_bpm, map_to_resolume=True)

        # send bpm only on change
        while True:
            prev_time = time()  # time compensation
            self.next_led(thread=False)
            #self.osc_client.send_osc("/composition/tempocontroller/tempo", self.send_bpm, map_to_resolume=True)

            if prev_bpm != self.send_bpm:
                self.osc_client.send_osc(self.config['OSC']['BPM_ADRESS'], self.send_bpm, map_to_resolume=True)
                self.update_bpm_display(self.send_bpm, send_to="send", Blink=True) # send bpm to send display
                prev_bpm = self.send_bpm
                
            # efficient c based busy wating with instant return option
            if self.bpm_thread_wait_and_terminate.wait(60/self.send_bpm - (time()-prev_time)):
                if self.resync:
                    continue
                else:
                    return

    def close(self, event):  # save settings to ini and close down
        """Ask User if event can be vetoed (No force close event).
        """
        if self.running:
            if wx.MessageBox("Do you really want to close BPMtoOSC?",
                             "Please confirm",
                             wx.ICON_QUESTION | wx.YES_NO) != wx.YES:
                try:
                    event.Veto()
                except:
                    pass
                return

        # create directory if it does not exist
        self.CONF_PATH.parent.mkdir(parents=True, exist_ok=True)

        # save config
        with open(self.CONF_PATH, 'w') as configfile:
            self.config.write(configfile)

        # close everything
        self.Destroy()

    def __del__(self):
        """stop all threads and close down
        """
        self.bpm_thread_wait_and_terminate.set()
        self.running = False
        self.sync = False
        self.uv_timer.stop()
        self.peak_meter.Stop()

        self.no_sync_send_thread.join()

        if self.beatfinder:
            del self.beatfinder
        if self.osc_client:
            del self.osc_client

        self.parent.Destroy()


def main():
    app = wx.App(0)
    frame = Main_Frame(None)
    app.SetTopWindow(frame)
    frame.Show()
    app.MainLoop()


# debug and testing
if __name__ == '__main__':
    #import wx.lib.inspection
    # wx.lib.inspection.InspectionTool().Show()
    main()
