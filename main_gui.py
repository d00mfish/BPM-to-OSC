#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Python version: 3.9.13 64-Bit
# WxPython: v4.1.1
#
# Autor: Leonhard Axtner
# Developed with VSCode using following Plugins:
#   Python, Pylance, GitLens, German language pack,Python Docstring Generator
#
# TODO:
# - Bar counter
# - Other output (Midi clock?)
# - BPM fine tune buttons
# - Beat blinkin leds of some sort
# - Darkmode?

# Imports:
from os import remove, system
from pathlib import Path
from subprocess import call
from platform import system
import time

from sevensegment import SevenSegmentDisp
import beatfinder
import osc_client

import configparser
import pyaudio
import threading

import wx
import wx.lib.masked.ipaddrctrl as ipctrl
import wx.lib.agw.peakmeter as PM


class Main_Frame(wx.Frame):
    '''Frame Class
    '''
    sel_msg_frame = None
    sel_bus_frame = None
    CONF_PATH = Path(Path.home(), "AppData/Roaming/BPMfinder/lastsession.ini")

    def __init__(self, parent=None):
        """Initialize Config Window
            - Reads config file and sets variables
            - Initializes GUI
        """
        # wx.Frame init
        style_dep = wx.DEFAULT_FRAME_STYLE ^ wx.MAXIMIZE_BOX  # ^ wx.RESIZE_BORDER
        super(Main_Frame, self).__init__(parent, title="BPM to OSC", style=style_dep)

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
        self.no_sync_send_thread = threading.Thread(target=self.send_thread_when_no_sync)
        self.last_tap = list()  # list of taps to determine bpm

        # Flags
        self.bpm_blink = False  # Blinking sevenseg background
        self.sync = True  # sync live bpm to send bpm
        self.running = False

        self.Read_LastSession_ini()
        self.InitUI()
        
        self.Centre() # centre window on screen
        
#PEAK METER
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimer)

        self.timer.Start(10)
        #self.peak_meter.Start(50)
        #self.peak_meter.SetData(0, 0, 1)

    def OnTimer(self, event):
        if self.running:
            avg = [sum(self.beatfinder.level_queue)/len(self.beatfinder.level_queue) if len(self.beatfinder.level_queue) > 0 else 0]
            #print(avg)
            self.peak_meter.SetData(avg, 0, 1)
            pass

    def Read_LastSession_ini(self):
        """Reading / creating lastsession.ini
        """

        """# if no config found, create one with default values
        if self.config.read(self.CONF_PATH.as_posix()) == []:
            self.config['OSC'] = {'IP': '127.000.000.001', 'PORT': 7000, 'RESYNC_BAR_ADRESS':
                                  '/composition/tempocontroller/resync', 'BPM_ADRESS': '/composition/tempocontroller/tempo'}
            self.config['AUDIO'] = {'device_index': '1'}

        # if config exists, fill global variables
        else:
            try:

                # if ip is not default value, try to connect to it
                if self.config['OSC']['IP'] != '127.000.000.001':
                    self.on_button_ping(None)

            except:
                # Regenerate config if something goes wrong
                print('Error reading config. Deleting and regenerating.')
                remove(self.CONF_PATH)
                self.Read_LastSession_ini()"""

        self.config['OSC'] = {'IP': '127.000.000.001', 'PORT': 7000, 'RESYNC_BAR_ADRESS':
                              '/composition/tempocontroller/resync', 'BPM_ADRESS': '/composition/tempocontroller/tempo'}
        self.config['AUDIO'] = {'device_index': '1'}

    def InitUI(self):
        """Actual GUI Setup of main config Window
        """
        global gwppath, TupleSelectedBusses

        panel = wx.Panel(self)
        sizer = wx.GridBagSizer(14, 4)

        self.bg_grey = wx.Colour(240, 240, 240)
        buttonfont = wx.Font(20, family=wx.DEFAULT, style=wx.NORMAL, weight=wx.BOLD)

        # Title Connect to Box
        title_connect = wx.StaticText(panel, label="OSC receiver address")
        sizer.Add(title_connect, pos=(0, 0), flag=wx.TOP | wx.LEFT, border=10)

        # Textbox IP-Adress
        self.text_ip = ipctrl.IpAddrCtrl(panel)
        self.text_ip.SetValue(self.config['OSC']['IP'])
        sizer.Add(self.text_ip, pos=(1, 0), span=(1, 1), flag=wx.LEFT, border=10)

        # Numberbox Port
        self.text_port = wx.SpinCtrl(panel)
        self.text_port.SetMax(65535)
        self.text_port.SetMin(0)
        self.text_port.SetValue(self.config['OSC']['PORT'])
        sizer.Add(self.text_port, pos=(1, 1), flag=wx.LEFT, border=10)

        # Text Connectionstatus
        self.text_connection = wx.TextCtrl(panel, style=wx.TE_READONLY | wx.BORDER_NONE)
        self.text_connection.SetFont(wx.Font(12, family=wx.DEFAULT, style=wx.NORMAL, weight=wx.BOLD))
        self.text_connection.SetBackgroundColour(self.bg_grey)
        # Enter current status after trying to connect with ini information
        sizer.Add(self.text_connection, pos=(1, 2),
                  flag=wx.LEFT | wx.RIGHT | wx.ALIGN_RIGHT | wx.ALIGN_BOTTOM, border=10)

        # Button Ping
        self.button_ping = wx.Button(panel, wx.ID_ANY, label="Ping")
        sizer.Add(self.button_ping, pos=(1, 3), flag=wx.ALIGN_RIGHT | wx.RIGHT, border=10)
        self.Bind(wx.EVT_BUTTON, self.on_button_ping, self.button_ping)

        # Title Open File
        title_select_device = wx.StaticText(panel, label="Select Input Device")
        sizer.Add(title_select_device, pos=(2, 0), flag=wx.TOP | wx.LEFT, border=10)

        audiosizer = wx.BoxSizer(wx.HORIZONTAL)

        # Audio device selection
        self.audio_selection = wx.ComboBox(panel, style=wx.CB_READONLY)
        self.on_button_reload(None)
        audiosizer.Add(self.audio_selection, 2, wx.EXPAND | wx.RIGHT, border=5)

# PEAK METER
        self.peak_meter = PM.PeakMeterCtrl(panel, -1, style=wx.SIMPLE_BORDER, agwStyle=PM.PM_HORIZONTAL)
        self.peak_meter.SetMeterBands(1, 42)
        self.peak_meter.SetFalloffEffect(False)
        self.peak_meter.SetBandsColour((150, 220, 150), (255, 255, 150), (220, 150, 150))
        self.peak_meter.SetRangeValue(20,60,80)
        
        audiosizer.Add(self.peak_meter, 2, wx.EXPAND | wx.LEFT | wx.FIXED_MINSIZE, border=5)

        sizer.Add(audiosizer, pos=(3, 0), span=(1, 4), flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        # Disabled reload button as pyaudio needs a complete restart to reload devices
        """ # Button Reload devices
        self.button_reload = wx.Button(panel, wx.ID_ANY, label="Reload")
        sizer.Add(self.button_reload, pos=(3, 3), flag=wx.TOP | wx.RIGHT, border=10)
        self.Bind(wx.EVT_BUTTON, self.on_button_reload, self.button_reload)"""

        # Separator
        line1 = wx.StaticLine(panel)
        sizer.Add(line1, pos=(4, 0), span=(1, 5), flag=wx.EXPAND | wx.TOP, border=10)

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
            digit.SetColours(segment_on=(77, 0, 0), background=self.bg_grey, segment_off=(220, 220, 220))
            digit.SetGeometry(width=38, height=38, thickness=10, separation=2)
            digit.EnableDot(False)
            digit.EnableColon(False)
            digit.SetValue("-")
            bpm_box_sending.Add(digit, 1, wx.EXPAND | wx.DOWN, 5)

        sevenseg_sizer.Add(bpm_box_live, 3, wx.EXPAND | wx.LEFT, 10)

        self.button_sync = wx.ToggleButton(panel, label='➜')
        self.button_sync.SetValue(True)
        self.button_sync.SetFont(buttonfont)
        sevenseg_sizer.Add(self.button_sync, 1, wx.EXPAND | wx.UP, 5)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_button_sync, self.button_sync)

        sevenseg_sizer.Add(bpm_box_sending, 3, wx.EXPAND | wx.RIGHT, 10)

        sizer.Add(sevenseg_sizer, pos=(5, 0), span=(3, 4), flag=wx.EXPAND, border=10)

# TAP BUTTON (BPM)
        button_sizer = wx.BoxSizer(orient=wx.VERTICAL)

        self.button_resync = wx.Button(panel, label='RESYNC BAR')
        self.button_resync.SetFont(buttonfont)
        #sizer.Add(self.button_resync, pos=(12, 2), span=(2, 2),flag=wx.EXPAND | wx.ALL ^ wx.TOP, border=10)
        button_sizer.Add(self.button_resync, 3, flag=wx.EXPAND, border=10)
        self.Bind(wx.EVT_BUTTON, self.on_button_resync, self.button_resync)


# START STOP RESYNC BUTTONS
        sub_button_sizer = wx.BoxSizer(orient=wx.HORIZONTAL)

        self.button_startstop = wx.ToggleButton(panel, label='START / STOP')
        self.button_startstop.SetFont(buttonfont)
        #sizer.Add(self.button_startstop, pos=(12, 0), span=(2, 2),flag=wx.EXPAND | wx.ALL ^ wx.TOP, border=10)
        sub_button_sizer.Add(self.button_startstop, 1, flag=wx.EXPAND, border=10)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_button_startstop, self.button_startstop)

        self.button_tap = wx.Button(panel, label='TAP')
        self.button_tap.SetFont(buttonfont)
        self.button_tap.Disable()
        sub_button_sizer.Add(self.button_tap, 1, flag=wx.EXPAND, border=10)
        #sizer.Add(self.button_tap, pos=(8, 0), span=(3, 4), flag=wx.EXPAND | wx.ALL ^ wx.TOP, border=10)
        self.Bind(wx.EVT_BUTTON, self.on_button_tap, self.button_tap)

        button_sizer.Add(sub_button_sizer, 3, flag=wx.EXPAND, border=10)
        sizer.Add(button_sizer, pos=(8, 0), span=(7, 4), flag=wx.EXPAND | wx.ALL ^ wx.TOP, border=10)

        # some window properties
        self.Bind(wx.EVT_CLOSE, self.close)
        self.SetMinSize(wx.Size(645, 600))
        self.SetMaxSize(wx.Size(1000, 700))
        # self.SetBackgroundColour((92,92,92))
        sizer.AddGrowableCol(2)
        sizer.AddGrowableRow(7)
        panel.SetSizer(sizer)
        sizer.Fit(self)

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
                        str(i) + " - " + self.audio.get_device_info_by_host_api_device_index(0, i).get('name'))
                else:
                    self.audio_selection.Append(
                        str(i) + " - " + self.audio.get_device_info_by_host_api_device_index(0, i).get('name') + " - DEFAULT")
        # self.audio_selection.Append(str(i) + " - " + self.audio.get_device_info_by_host_api_device_index(0, i).get('name'))

        # if function gets called from read last session
        if event is None:
            self.audio_selection.SetSelection(self.audio_device)

        """if event is not None:
            self.audio_selection.Popup()"""

    def on_button_tap(self, event):

        if len(self.last_tap) > 0:

            # add time and timedelta to list
            self.last_tap.append((time.time(), time.time() - self.last_tap[-1][0]))

            # Clear if previous taps are too old
            if time.time() - self.last_tap[-2][0] > 1:
                self.last_tap = [self.last_tap[-1]]

            else:
                if self.sync:
                    self.switch_sync(False)

                # Calculate the BPM
                self.send_bpm = round(60 / (sum([x[1] for x in self.last_tap[1:]]) / len(self.last_tap[1:])))
                threading.Thread(self.update_bpm_display(self.send_bpm, send_to="send")).start()

        else:
            self.last_tap.append((time.time(), None))

    def on_button_sync(self, event):
        self.switch_sync(self.button_sync.GetValue())
        self.button_resync.BackgroundColour = self.bg_grey

    def on_button_resync(self, event):
        if self.beatfinder:
            self.beatfinder.resync_bar()

    def on_button_startstop(self, event):
        if self.button_startstop.GetValue():
            print("Starting")
            self.config['AUDIO']['device_index'] = str(self.audio_selection.GetSelection())
            self.config['OSC']['IP'] = self.text_ip.GetValue().replace(" ", "")
            self.config['OSC']['PORT'] = str(self.text_port.GetValue())
            
            
            self.osc_client = osc_client.OSCclient(self.config['OSC']['IP'], int(self.config['OSC']['PORT']))
            self.beatfinder = beatfinder.BeatDetector(self.osc_client, self.audio_selection.GetSelection(), parent=self)
            
            self.running = True

            self.button_startstop.BackgroundColour = (255, 200, 200)

            self.button_tap.Enable()

        else:
            print("Stopping")
            self.running = False

            # self.switch_sync(False)
            del self.beatfinder
            self.beatfinder = None
            
            # update GUI
            self.button_tap.Disable()
            self.button_startstop.BackgroundColour = self.bg_grey

            self.no_sync_send_thread.join
            
            self.update_bpm_display("---", send_to="both")

    def on_button_ping(self, event):
        '''Establish Websocket connection
            - Create Websocket connection
            - Set Status in Interface wether connected, connecting or connection error
        '''
        global Connected

        # loading circle while parsing
        wx.SetCursor(wx.Cursor(wx.CURSOR_WAIT))

        # disable connect button during connect attempt
        self.button_ping.Disable()

        # get userinput and save into config
        self.config['OSC']['IP'] = self.text_ip.GetValue()
        self.config['OSC']['PORT'] = str(self.text_port.GetValue())

        # Set Text Message Connecting:
        self.text_connection.SetForegroundColour((255, 206, 13))
        self.text_connection.Clear()
        self.text_connection.AppendText("Pinging...")

        # Establish connection
        param = '-n' if system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', self.config['OSC']['IP'].replace(" ", "")]

        if call(command) == 0:
            # Set text message OK:
            self.text_connection.SetForegroundColour((0, 184, 0))
            self.text_connection.Clear()
            self.text_connection.AppendText("Reachable")
            Connected = True

        else:
            print('No ping answer')
            # Set Text Message Error:
            self.text_connection.SetForegroundColour((220, 0, 0))
            self.text_connection.Clear()
            self.text_connection.AppendText("Unreachable")
            Connected = False

            # Disable Ok button as no connection has been established
            self.button_ok.Disable()

        # reset cursor
        wx.SetCursor(wx.Cursor(wx.CURSOR_DEFAULT))

        # reenable button
        self.button_ping.Enable()

    def close(self, event):  # save settings to ini and close down
        """Ask User if event can be vetoed (No force close event).
        """
        if self.running:
            if wx.MessageBox("Do you really want to close Beatfinder?",
                             "Please confirm",
                             wx.ICON_QUESTION | wx.YES_NO) != wx.YES:
                try:
                    event.Veto()
                except:
                    pass
                return

        # create directory if not exist
        self.CONF_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(self.CONF_PATH, 'w') as configfile:
            self.config.write(configfile)

        # close everything if no veto (force close) event is given
        self.Destroy()

    def switch_sync(self, state: bool):
        """Changes state of sync flag and button\n
        Starts thread to emit "send bpm" 

        Args:
            state (bool): State to switch to
        """
        if not state and self.sync:
            self.sync = False
            self.button_sync.SetLabel('❌')
            self.button_sync.SetValue(False)
            self.no_sync_send_thread = threading.Thread(target=self.send_thread_when_no_sync).start()
            
        elif state and not self.sync:
            self.sync = True
            self.button_sync.SetLabel('➜')
            self.button_sync.SetValue(True)
                        
        else:
            print("Sync state already set to {}".format(state))

    def update_bpm_display(self, bpm, send_to: str, Blink=False):

            bpm_digits = [d for d in str(bpm)]
            bpm_digits.reverse()

            def send_to_disp(disp):
                for i, digit in enumerate(disp):

                    if len(bpm_digits) > 2:
                        digit.SetValue(bpm_digits[2-i])
                    else:
                        digit.SetValue(bpm_digits[2-i] if i > 0 else 0)

                    # Blinking background
                    if Blink:
                        if self.bpm_blink:
                            digit.SetColours(background=self.bg_grey, segment_off=(220, 220, 220))
                        else:
                            digit.SetColours(background=(220, 220, 220), segment_off=self.bg_grey)

            # send to display
            if self.sync or send_to == "both":
                send_to_disp(self.live_disp)
                send_to_disp(self.send_disp)
            elif send_to == "send":
                send_to_disp(self.send_disp)
            else:
                send_to_disp(self.live_disp)

            self.bpm_blink = not (self.bpm_blink)

    def send_thread_when_no_sync(self):
        last_send = time.time()
        blink = False

        while True:
            if time.time() - last_send >= 60/self.send_bpm:
                last_send = time.time()

                self.osc_client.send_osc("/composition/tempocontroller/tempo", self.send_bpm, map_to_resolume=True)

                self.button_resync.BackgroundColour = (220, 220, 220) if blink else self.bg_grey

                blink = not blink

            # exit conditions

            if self.sync or not(self.running):
                return

            time.sleep(0.05)  # New solution needed

    def __del__(self):
        self.sync = False
        self.timer.cancel()
        self.peak_meter.Stop()
        
        self.no_sync_send_thread.join()
        
        if self.beatfinder:
            del self.beatfinder
        if self.osc_client:
            del self.osc_client


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
