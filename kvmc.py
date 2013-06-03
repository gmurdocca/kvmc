#!/usr/bin/env python
LICENSE = """kvmc
Copyright (c) 2012 George Murdocca

kvmc is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published
by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.

kvmc is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You can obtain a copy of the GNU General Public License at:
http://www.gnu.org/licenses/.
"""

VERSION = 1.1

import gtk
import serial
import time
import struct
import os
import sys
import gobject
import fcntl
import threading
import pty
import shlex
import signal

class Serial_Worker(threading.Thread):

    def __init__(self, teensy, serial_port_label):
        super(Serial_Worker, self).__init__()
        self.teensy = teensy
        self.serial_port_label = serial_port_label
        self.running = True
        self.pause = False
        self.init_pty()

    def init_pty(self):
        self.pty_master, pty_slave = pty.openpty()
        flags = fcntl.fcntl(self.pty_master, fcntl.F_GETFL, 0)
        fcntl.fcntl(self.pty_master, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        pty_name = os.ttyname(pty_slave)
        gobject.idle_add(self.update_label, pty_name)

    def update_label(self, pty_name):
        self.serial_port_label.set_text(" %s " % pty_name)
        return False

    def process_pty(self):
        # read a byte from the pty and send to kvmc
        byte = None
        try:
            byte = os.read(self.pty_master, 1)
        except OSError:
            # nothing to read
            pass
        if byte:
            self.teensy.send_serial(byte)
        # read a byte from the kvmc and send to pty
        try:
            byte = self.teensy.conn.read(1)
        except Exception, e:
            print "Error reading kvmc device: %s" % e
            self.quit()
        if byte:
            os.write(self.pty_master, byte)

    def quit(self):
        gtk.main_quit()
        self.running = False

    def run(self):
        while self.running:
            if not self.pause:
                self.process_pty()


class Replay_Worker(threading.Thread):

    def __init__(self, teensy, kvmc_gui):
        super(Replay_Worker, self).__init__()
        self.teensy = teensy
        self.kvmc_gui = kvmc_gui
        self.recorder_status_label = kvmc_gui.recorder_status_text
        self.replay_file = None
        self.running = True
        self.update_label()

    def update_label(self):
        if self.replay_file:
            self.recorder_status_label.set_text("  Replaying  ")
        else:
            self.recorder_status_label.set_text("    Idle     ")
        return True

    def run(self):
        while self.running:
            if self.replay_file:
                self.update_label()
                self.kvmc_gui.record.set_sensitive(False)
                self.kvmc_gui.replay.set_sensitive(False)
                self.kvmc_gui.editm.set_sensitive(False)
                self.kvmc_gui.grab_text_label.set_text("")
                if self.kvmc_gui.stop_button_handler:
                    self.kvmc_gui.stop_button.disconnect(self.kvmc_gui.stop_button_handler)
                self.kvmc_gui.stop_button_handler = \
                    self.kvmc_gui.stop_button.connect("clicked", self.kvmc_gui.do_stop, "replay")
                self.kvmc_gui.stop_button.set_sensitive(True)
                self.teensy.replay(self.replay_file)
                self.kvmc_gui.stop_button.set_sensitive(False)
                self.kvmc_gui.record.set_sensitive(True)
                self.kvmc_gui.replay.set_sensitive(True)
                self.kvmc_gui.editm.set_sensitive(True)
                self.replay_file = None
                self.kvmc_gui.grab_text_label.set_text("Click to control...")
                self.update_label()
            else:
                time.sleep(.1)

    def quit(self):
        gtk.main_quit()
        self.running = False
            

class Teensy_Connection():

    teensy_key_map = {
        'none': chr(0), 'a': chr(4), 'b': chr(5), 'c': chr(6), 'd': chr(7),
        'e': chr(8), 'f': chr(9), 'g': chr(10), 'h': chr(11), 'i': chr(12),
        'j': chr(13), 'k': chr(14), 'l': chr(15), 'm': chr(16), 'n': chr(17),
        'o': chr(18), 'p': chr(19), 'q': chr(20), 'r': chr(21), 's': chr(22),
        't': chr(23), 'u': chr(24), 'v': chr(25), 'w': chr(26), 'x': chr(27),
        'y': chr(28), 'z': chr(29), '1': chr(30), 'exclam': chr(30), '!': chr(30),
        '2': chr(31), 'at': chr(31), '@': chr(31), '3': chr(32),
        'numbersign': chr(32), '#': chr(32), '4': chr(33), 'dollar': chr(33),
        '$': chr(33), '5': chr(34), 'percent': chr(34), '%': chr(34),
        '6': chr(35), 'asciicircum': chr(35), '^': chr(35), '7': chr(36),
        'ampersand': chr(36), '&': chr(36), '8': chr(37), 'asterisk': chr(37),
        '*': chr(37), '9': chr(38), 'parenleft': chr(38), '(': chr(38),
        '0': chr(39), 'parenright': chr(39), ')': chr(39), 'return': chr(40),
        '\n': chr(40), 'escape': chr(41), 'backspace': chr(42), 'tab': chr(43),
        '\t': chr(43), 'space': chr(44), ' ': chr(44), 'minus': chr(45),
        '-': chr(45), 'underscore': chr(45), '_': chr(45), 'equal': chr(46),
        '=': chr(46), 'plus': chr(46), '+': chr(46), 'braceleft': chr(47),
        '{': chr(47), 'bracketleft': chr(47), '[': chr(47), 'braceright': chr(48),
        '}': chr(48), 'bracketright': chr(48), ']': chr(48), 'backslash': chr(49),
        '\\': chr(49), 'bar': chr(49), '|': chr(49),
        # XXX teensy's keylayouts.h defines KEY_NON_US_NUM 50 - should we use it?
        'semicolon': chr(51), ';': chr(51), 'colon': chr(51), ':': chr(51),
        'apostrophe': chr(52), "'": chr(52), 'quotedbl': chr(52), '"': chr(52),
        'grave': chr(53), '`': chr(53), 'asciitilde': chr(53), '~': chr(53),
        'comma': chr(54), ',': chr(54), 'less': chr(54), '<': chr(54),
        'period': chr(55), '.': chr(55), 'greater': chr(55), '>': chr(55),
        'slash': chr(56), '/': chr(56), 'question': chr(56), '?': chr(56),
        'caps_lock': chr(57), 'f1': chr(58), 'f2': chr(59), 'f3': chr(60),
        'f4': chr(61), 'f5': chr(62), 'f6': chr(63), 'f7': chr(64), 'f8': chr(65),
        'f9': chr(66), 'f10': chr(67), 'f11': chr(68), 'f12': chr(69),
        'print': chr(70), 'sys_req': chr(70), 'scroll_lock': chr(71),
        'pause': chr(72), 'break': chr(72), 'insert': chr(73), 'home': chr(74),
        'page_up': chr(75), 'delete': chr(76), 'end': chr(77), 'page_down': chr(78),
        'right': chr(79), 'left': chr(80), 'down': chr(81), 'up': chr(82),
        'num_lock': chr(83), 'kp_divide': chr(84), 'kp_multiply': chr(85),
        'kp_subtract': chr(86), 'kp_add': chr(87), 'kp_enter': chr(88),
        'kp_1': chr(89), 'kp_end': chr(89), 'kp_2': chr(90), 'kp_down': chr(90),
        'kp_3': chr(91), 'kp_page_down': chr(91), 'kp_4': chr(92),
        'kp_left': chr(92), 'kp_5': chr(93), 'kp_begin': chr(93), 'kp_6': chr(94),
        'kp_right': chr(94), 'kp_7': chr(95), 'kp_home': chr(95), 'kp_8': chr(96),
        'kp_up': chr(96), 'kp_9': chr(97), 'kp_page_up': chr(97), 'kp_0': chr(98),
        'kp_insert': chr(98), 'kp_decimal': chr(99), 'kp_delete': chr(99)}

    teensy_modkey_map = {
        'none': 0x00,
        'control_l': 0x01,
        #'control_r': 0x01, # used for ungrabbing mouse/keyboard
        'shift_l': 0x02,
        'shift_r': 0x02,
        'alt_l': 0x04,
        'alt_r': 0x04,
        'super_l': 0x08,
        'super_r': 0x08}

    teensy_mouse_button_map = {
        0: 0x00, # none
        1: 0x01, # left
        2: 0x02, # middle
        3: 0x04, # right
        4: 0x08, # wheel up
        5: 0x10} # wheel down

    # buttons on the VGA-to-TV scan line coverter
    sc_button_map = {
        "left": 0x01,
        "right": 0x02,
        "down": 0x04,
        "up": 0x08,
        "menu": 0x10,
        "zoom": 0x20}

    msg_type = {'keyboard': 0,
                'keyboard_modkey': 1,
                'mouse_button': 2,
                'mouse_move': 3,
                'mouse_wheel': 4,
                'serial': 5,
                'reset': 6,
                'sc': 7}

    # setup default config attributes
    conf_file = os.path.join(os.getenv("HOME") ,".kvmc", "config")
    kvmc_device = "/dev/ttyACM0"
    capture_device = "/dev/video0"
    capture_device_input = "0"
    replay_no_delay = False
    record_init_mouse_pointer = True
    # setup runtime attributes
    serial_lock = threading.Lock()
    recording_file = None
    replay_file = None
    rec_file_header = "kvmc%s" % VERSION
    stop_replay = False

    def __init__(self):
        self._init_states()
        try:
            self.connect()
        except Exception, e:
            print "Error opening kvmc device: %s\n%s\nCheck config at %s" %\
                (self.kvmc_device, e, self.conf_file)
            sys.exit(-1)

    def _init_states(self):
        # store the state of the 6 teensy keyboard values
        self.key_state = ["none", "none", "none", "none", "none", "none"]
        # store the values of the 4 teensy mod keys (ctrl, shift, alt, super)
        self.mod_key_state = ["none", "none", "none", "none"]
        # store the values of the 3 mouse buttons and scroll wheel
        self.mouse_button_state = [0, 0, 0, 0, 0]
        # store the values of mouse x and y
        self.mouse_position_state = [0, 0]
        # store the mouse wheel direction state 0, 1 -> up, down
        self.mouse_wheel_direction = 0

    def get_config(self, conf_file):
        if not os.path.exists(conf_file):
            self.set_config(conf_file)
        f = open(conf_file)
        conf_line = f.readlines()
        f.close()
        for line in conf_line:
            key, value = [i.strip() for i in line.split("=")]
            if key == "kvmc_device":
                self.kvmc_device = value
            elif key == "capture_device":
                self.capture_device = value
            elif key == "capture_device_input":
                self.capture_device_input = value
            elif key == "replay_no_delay":
                self.replay_no_delay = int(value)
            elif key == "record_init_mouse_pointer":
                self.record_init_mouse_pointer = int(value)

    def set_config(self, conf_file):
        conf_dir = os.path.dirname(conf_file)
        if not os.path.exists(conf_dir):
            os.mkdir(conf_dir)
        f = open(conf_file, "w")
        f.write("kvmc_device=%s\ncapture_device=%s\ncapture_device_input=%s\nreplay_no_delay=%s\nrecord_init_mouse_pointer=%s\n" % \
            (self.kvmc_device, self.capture_device, self.capture_device_input, int(self.replay_no_delay), int(self.record_init_mouse_pointer)))
        f.close()

    def connect(self):
        self.get_config(self.conf_file)
        conn = serial.Serial(self.kvmc_device,
                            baudrate=9600,
                            bytesize=serial.EIGHTBITS,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE,
                            timeout=0,
                            xonxoff=0,
                            rtscts=0
                            )
        conn.setDTR(True)
        self.conn = conn
        self.send_reset()

    def _send(self, data):
        self.serial_lock.acquire()
        try:
            self.conn.write(data)
            if self.recording_file and not self.recording_file.closed:
                try:
                    delay = time.time() - self.recording_timer
                    self.recording_file.write(struct.pack('>f', delay))
                    self.recording_file.write(data)
                    self.recording_timer = time.time()
                except IOError, e:
                    print "Error writing to recording file '%s': %s" % (self.recording_file.name, e)
                    sys.exit(-1)
        except serial.serialutil.SerialException, e:
            print "Error sending data to kvmc device: %s\n%s\nCheck config at %s" %\
                (self.kvmc_device, e, self.conf_file)
            sys.exit(-1)
        self.serial_lock.release()

    def _send_keyboard_state(self):
        self._send(chr(self.msg_type["keyboard"]))
        # send the current keyboard state to the teensy
        for key_name in self.key_state:
            self._send(self.teensy_key_map[key_name])

    def _send_keyboard_modkey_state(self):
        # create the mod_keys
        mod_keys =  self.teensy_modkey_map[self.mod_key_state[0]] |\
                    self.teensy_modkey_map[self.mod_key_state[1]] |\
                    self.teensy_modkey_map[self.mod_key_state[2]] |\
                    self.teensy_modkey_map[self.mod_key_state[3]] 
        self._send(chr((mod_keys << 3) | self.msg_type["keyboard_modkey"]))

    def _send_mouse_button_state(self):
        mouse_buttons = self.teensy_mouse_button_map[self.mouse_button_state[0]] |\
                        self.teensy_mouse_button_map[self.mouse_button_state[1]] |\
                        self.teensy_mouse_button_map[self.mouse_button_state[2]] |\
                        self.teensy_mouse_button_map[self.mouse_button_state[3]] |\
                        self.teensy_mouse_button_map[self.mouse_button_state[4]]
        self._send(chr( (mouse_buttons << 3) | self.msg_type["mouse_button"]))

    def _send_mouse_wheel_state(self):
        self._send(chr((self.mouse_wheel_direction << 3) | self.msg_type["mouse_wheel"]))

    def _send_mouse_move_state(self):
        self._send(chr(self.msg_type["mouse_move"]))
        self._send(struct.pack(">b",self.mouse_position_state[0]))
        self._send(struct.pack(">b",self.mouse_position_state[1]))

    def send_serial(self, byte):
        self._send(chr(self.msg_type["serial"]))
        self._send(byte)

    def send_reset(self):
        # send 6 reset packets incase we are in the middle of a multi-byte message, the
        # longest of which is 6 bytes (ie. the _send_keyboard_state message). If this is
        # the case (possible if a replay was stopped mid-stream) then this may cause
        # extraneous outout on the remote machine such as extra key presses.
        for i in range(7):
            self._send(chr(self.msg_type["reset"]))
        self._init_states()

    def press_sc_button(self, button):
        if button not in self.sc_button_map:
            print "Erorr: Unsupported scan line converter button: %s" % button
            return
        self._send(chr(self.msg_type["sc"]))
        self._send(chr(self.sc_button_map[button]))

    def press_key(self, key_name):
        key_name = key_name.lower()
        # bail if a non-supported key was pressed
        if key_name not in self.teensy_key_map and key_name not in self.teensy_modkey_map:
            print "Error Key '%s' not supported" % key_name
            return
        #if key currently pressed, reset teensy as we probably missed a gtk release event for some reason.
        if key_name in self.key_state or key_name in self.mod_key_state:
            self.send_reset()
        if key_name in self.teensy_key_map:
            if "none" in self.key_state:
                index = self.key_state.index("none")
                self.key_state[index] = key_name
                self._send_keyboard_state()
            else:
                print "Error: Max 6 simultaneous key presses exceeded, ignoring."
        elif key_name in self.teensy_modkey_map:
            index = self.mod_key_state.index("none")
            self.mod_key_state[index] = key_name
            self._send_keyboard_modkey_state()
        
    def release_key(self, key_name):
        key_name = key_name.lower()
        if key_name in self.key_state:
            index = self.key_state.index(key_name)
            self.key_state[index] = "none"
            self._send_keyboard_state()
        elif key_name in self.mod_key_state:
            index = self.mod_key_state.index(key_name)
            self.mod_key_state[index] = "none"
            self._send_keyboard_modkey_state()

    def press_mouse_button(self, mouse_button):
        # bail if a non-supported mouse button was pressed
        if mouse_button not in self.teensy_mouse_button_map:
            return
        # return if button is currently pressed
        if mouse_button in self.mouse_button_state:
            return
        index = self.mouse_button_state.index(0)
        self.mouse_button_state[index] = mouse_button
        self._send_mouse_button_state()

    def release_mouse_button(self, mouse_button):
        if mouse_button in self.mouse_button_state:
            index = self.mouse_button_state.index(mouse_button)
            self.mouse_button_state[index] = 0
        self._send_mouse_button_state()

    def move_mouse_wheel(self, direction):
        self.mouse_wheel_direction = direction
        self._send_mouse_wheel_state()

    def move_mouse(self, x, y):
        if -128 <= x <= 127 and -128 <= y <= 127:
            self.mouse_position_state = [x, y]
            self._send_mouse_move_state()
            self.mouse_position_state = [0, 0]

    def depress_key(self, char):
        self.press_key(char)
        time.sleep(.001)
        self.release_key(char)
        time.sleep(.001)

    def shift_depress_key(self, char):
        self.press_key("shift_l")
        time.sleep(.001)
        self.depress_key(char)
        self.release_key("shift_l")
        time.sleep(.001)

    def type_key(self, char):
        if char in [chr(i) for i in range(97, 123)]: # lowercase letter
            self.depress_key(char)
        elif char in [chr(i) for i in range(65, 91)]: # uppercase letter
            self.shift_depress_key(char)
        elif char in [chr(i) for i in range(48, 58)]: # number
            self.depress_key(char)
        elif char in ['`', '-', '=', '[', ']', '\\', ';', "'", ',', '.', '/', '\t', ' ', '\n']:
            self.depress_key(char)
        elif char in ['~', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', '{', '}', '|', ':', '"', '<', '>', '?']:
            self.shift_depress_key(char)
        else:
            print "Error: no supported keyboard key for character '%s' (Unicode code point/ASCII: %s)" % (char, ord(char))

    def start_recording(self, filename):
        recording_file = open(filename, 'w')
        recording_file.write(self.rec_file_header)
        self.recording_timer = time.time()
        self.recording_file = recording_file
        if self.record_init_mouse_pointer:
            for i in range(10):
                self.move_mouse(-127, 127)

    def stop_recording(self):
        self.recording_file.close()
        return self.recording_file.name

    def is_not_rec_file(self, filename):
        try:
            f = open(filename, 'r')
            header = f.read(len(self.rec_file_header))
            f.close()
        except Exception, e:
            return "Error reading file: %s" % e
        if not header in self.get_supported_rec_file_headers():
            return "File is not a kvmc recording."

    def get_supported_rec_file_headers(self):
        return [self.rec_file_header]

    def replay(self, filename):
        self.replay_file = filename
        f = open(filename)
        f.read(len(self.rec_file_header))
        while not self.stop_replay:
            try:
                delay = f.read(4)
                byte = f.read(1)
            except:
                print "Error: incorrectly formated kvmc recording file."
                sys.exit(-1)
            if not delay or not byte:
                break
            if not self.replay_no_delay:
                delay = struct.unpack('>f', delay)[0]
                time.sleep(delay)
            else:
                time.sleep(0.1)
            self._send(byte)
        if self.stop_replay:
            self.send_reset()
            self.stop_replay = False

    def close(self):
        self.conn.setDTR(False)
        self.conn.close()


class KVMC_GUI():

    grabbed_window = False
    mouse_x = None
    mouse_y = None
    mouse_update_timer = time.time()

    def __init__(self):
        # build the window
        self.display = gtk.gdk.Display(None)
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("kvmc v%s" % VERSION)
        self.window.set_default_size(640, 480)
        self.window.set_position(gtk.WIN_POS_CENTER)
        agr = gtk.AccelGroup()
        self.window.add_accel_group(agr)
        mb = gtk.MenuBar()
        filemenu = gtk.Menu()
        editmenu = gtk.Menu()
        helpmenu = gtk.Menu()
        filem = gtk.MenuItem("_File")
        filem.set_submenu(filemenu)
        self.editm = gtk.MenuItem("_Edit")
        self.editm.set_submenu(editmenu)
        helpm = gtk.MenuItem("Help")
        helpm.set_submenu(helpmenu)
        self.record = gtk.ImageMenuItem(gtk.STOCK_MEDIA_RECORD, agr)
        self.record.set_label("Record Session Input...")
        key, mod = gtk.accelerator_parse("<Control>R")
        self.record.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
        self.record.connect("activate", self.do_record)
        filemenu.append(self.record)
        self.replay = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PLAY, agr)
        self.replay.set_label("Replay Session Input...")
        key, mod = gtk.accelerator_parse("<Control>P")
        self.replay.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
        self.replay.connect("activate", self.do_replay)
        filemenu.append(self.replay)
        filemenu.append(gtk.SeparatorMenuItem())
        exit = gtk.ImageMenuItem(gtk.STOCK_QUIT, agr)
        key, mod = gtk.accelerator_parse("<Control>Q")
        exit.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
        exit.connect("activate", self.quit)
        filemenu.append(exit)
        paste = gtk.ImageMenuItem(gtk.STOCK_PASTE, agr)
        paste.set_label("Paste As Keystrokes")
        key, mod = gtk.accelerator_parse("<Control>V")
        paste.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
        paste.connect("activate", self.paste)
        editmenu.append(paste)
        editmenu.append(gtk.SeparatorMenuItem())
        control = gtk.ImageMenuItem(gtk.STOCK_FULLSCREEN, agr)
        control.set_label("Display Control")
        key, mod = gtk.accelerator_parse("<Control>O")
        control.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
        control.connect("activate", self.display_control)
        editmenu.append(control)
        self.setup = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES, agr)
        self.setup.connect("activate", self.preferences)
        editmenu.append(self.setup)
        about = gtk.ImageMenuItem(gtk.STOCK_ABOUT, agr)
        about.connect("activate", self.about)
        helpmenu.append(about)
        mb.append(filem)
        mb.append(self.editm)
        mb.append(helpm)
        vbox = gtk.VBox(False, 2)
        self.vbox = gtk.VBox()
        self.window.add(self.vbox)
        self.vbox.pack_start(mb, False, False, 0)
        self.movie_window = gtk.DrawingArea()
        self.vbox.add(self.movie_window)
        hbox = gtk.HBox()
        hbox.set_border_width(2)
        self.vbox.pack_start(hbox, False)
        hbox_left = gtk.HBox()
        serial_port_label = gtk.Label(" Serial Port: ")
        hbox_left.pack_start(serial_port_label, False)
        serial_event_box = gtk.EventBox()
        style = serial_event_box.get_style().copy()
        style.bg[gtk.STATE_NORMAL] = serial_event_box.get_colormap().alloc(0, 0, 0)
        serial_event_box.set_style(style)
        serial_event_box.show()
        self.serial_port_text = gtk.Label()
        style = self.serial_port_text.get_style().copy()
        style.fg[gtk.STATE_NORMAL] = self.serial_port_text.get_colormap().alloc(10000, 30000, 10000)
        self.serial_port_text.set_style(style)
        serial_event_box.add(self.serial_port_text)
        hbox_left.pack_start(serial_event_box, False)
        recorder_status_label = gtk.Label("   Recorder Status: ")
        hbox_left.pack_start(recorder_status_label, False)
        recorder_event_box = gtk.EventBox()
        style = recorder_event_box.get_style().copy()
        style.bg[gtk.STATE_NORMAL] = recorder_event_box.get_colormap().alloc(0, 0, 0)
        recorder_event_box.set_style(style)
        recorder_event_box.show()
        self.recorder_status_text = gtk.Label()
        style = self.recorder_status_text.get_style().copy()
        style.fg[gtk.STATE_NORMAL] = self.recorder_status_text.get_colormap().alloc(40000, 10000, 10000)
        self.recorder_status_text.set_style(style)
        recorder_event_box.add(self.recorder_status_text)
        hbox_left.pack_start(recorder_event_box, False)
        gtk.stock_add([(gtk.STOCK_MEDIA_RECORD, "_Stop", 0, 0, "")])
        self.stop_button = gtk.Button(stock=gtk.STOCK_MEDIA_STOP)
        self.stop_button.set_sensitive(False)
        hbox_left.pack_start(self.stop_button, False)
        hbox_right = gtk.HBox()
        self.grab_text_label = gtk.Label("Click to control...")
        hbox_right.pack_end(self.grab_text_label, False)
        hbox.pack_start(hbox_left, True)
        hbox.pack_start(hbox_right, True)
        self.window.connect("key_press_event", self.key_press_event_handler)
        self.window.connect("key_release_event", self.key_release_event_handler)
        self.window.connect("button_press_event", self.button_press_event_handler)
        self.window.connect("button_release_event", self.button_release_event_handler)
        self.window.connect("scroll-event", self.button_press_event_handler)
        self.window.connect("delete_event", self.quit)
        self.window.connect_after("motion_notify_event", self.motion_notify_event_handler)
        self.movie_window.connect("expose_event", self.expose_event_handler)
        self.all_events = gtk.gdk.KEY_PRESS_MASK \
                             | gtk.gdk.KEY_RELEASE_MASK \
                             | gtk.gdk.BUTTON_PRESS_MASK \
                             | gtk.gdk.BUTTON_RELEASE_MASK \
                             | gtk.gdk.SCROLL_MASK \
                             | gtk.gdk.POINTER_MOTION_MASK \
                             | gtk.gdk.POINTER_MOTION_HINT_MASK \
                             | gtk.gdk.EXPOSURE_MASK
        self.window.set_events(self.all_events)
        self.window.show_all()
        # create a teensy connection object
        self.teensy = Teensy_Connection()
        self.serial_thread = Serial_Worker(self.teensy, self.serial_port_text)
        self.serial_thread.start()
        self.replay_thread = Replay_Worker(self.teensy, self)
        self.replay_thread.start()
        # Set up video
        self.mplayer_fd = None
        self.mplayer_pid = None
        self.init_video()
        self.stop_button_handler = None
        # create an invisible mouse cursor for passing to pointer_grab
        pix_data = """/* XPM */
            static char * invisible_xpm[] = { "1 1 1 1", "c None", " "};"""
        color = gtk.gdk.Color()
        sys.stderr = open("/dev/null") # suppress gtk error
        pix = gtk.gdk.pixmap_create_from_data(None, pix_data, 1, 1, 1, color, color)
        sys.stderr = sys.__stderr__
        self.invisible = gtk.gdk.Cursor(pix, pix, color, color, 0, 0)

    def init_video(self):
        if self.mplayer_pid:
            os.close(self.mplayer_fd)
            self.mplayer_fd = None
            os.kill(self.mplayer_pid, signal.SIGTERM) 
            os.waitpid(self.mplayer_pid, 0)
        xid = self.movie_window.window.xid
        command = "mplayer -tv device=%s:input=%s:driver=v4l2 -wid %i -quiet tv://" % \
            (self.teensy.capture_device, self.teensy.capture_device_input, xid)
        command = shlex.split(command)
        pid, self.mplayer_fd = pty.fork()
        if pid == 0:
            # Child/Slave
            try:
                os.execlp(command[0], *command)
            except OSError, e:
                raise Exception("Could not start 'mplayer': %s" % e)
                sys.exit(-1)
        # Parent/Master
        self.mplayer_pid = pid

    def about(self, *args):
        about = gtk.AboutDialog()
        about.set_program_name("kvmc")
        about.set_version("%s" % VERSION)
        about.set_copyright("Copyright (c) 2012 George Murdocca")
        about.set_comments("A USB-to-KVM application that provides direct KVM control of a headless computer using a kvmc device, including paste-as-keystrokes, serial communications and session recording.")
        about.set_license(LICENSE)
        about.set_website("https://github.com/gmurdocca/kvmc")
        about.run()
        about.destroy()

    def paste(self, *args):
        wrap_checkbox_text = "Wrap Text"
        serial_checkbox_text = "Paste Windows Serial Driver"
        cb = gtk.Clipboard()
        cb_text = cb.wait_for_text() or ""
        if type(args[0]) == type(gtk.CheckButton()):
            if args[0].get_label() == wrap_checkbox_text:
                if args[0].get_active():
                    self.texteditor.set_wrap_mode(gtk.WRAP_WORD)
                else:
                    self.texteditor.set_wrap_mode(gtk.WRAP_NONE)
            elif args[0].get_label() == serial_checkbox_text:
                if args[0].get_active():
                    self.textbuffer.set_text(WINDOWS_USB_SERIAL_DRIVER_INF)
                else:
                    self.textbuffer.set_text(cb_text)
        else:
            dialog = gtk.Dialog("Paste Clipboard as Keystrokes",
                            self.window,
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            (gtk.STOCK_PASTE, 1, gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
            dialog.set_default_size(480, 360)

            paste_text_label = gtk.Label("Paste text:")
            paste_text_label.set_alignment(0, 0)
            dialog.vbox.pack_start(paste_text_label, False)

            table = gtk.Table(rows=3, columns=1, homogeneous=False)
            table.set_row_spacing(0, 2)
            table.set_col_spacing(0, 2)
            dialog.vbox.pack_start(table, gtk.TRUE, gtk.TRUE, 0)
            text_vbox = gtk.VBox()
            texteditorsw = gtk.ScrolledWindow()
            texteditorsw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            self.texteditor = gtk.TextView(buffer=None)
            self.textbuffer = self.texteditor.get_buffer()
            self.textbuffer.set_text(cb_text)
            self.texteditor.set_editable(False)
            self.texteditor.set_justification(gtk.JUSTIFY_LEFT)
            texteditorsw.add(self.texteditor)
            texteditorsw.show()
            self.texteditor.show()
            text_vbox.pack_start(texteditorsw)
            table.attach(text_vbox, 0, 1, 0, 1,
                         gtk.EXPAND | gtk.SHRINK | gtk.FILL,
                         gtk.EXPAND | gtk.SHRINK | gtk.FILL, 0, 0)
            unsupported_char_label = gtk.Label("Note: Unsupported characters will be ignored.")
            style = unsupported_char_label.get_style().copy()
            style.fg[gtk.STATE_NORMAL] = unsupported_char_label.get_colormap().alloc(40000, 0, 0)
            unsupported_char_label.set_style(style) 
            table.attach(unsupported_char_label, 0, 1, 1, 2, gtk.FILL, gtk.FILL, 0, 0)
            hbox = gtk.HBox()
            serial_checkbox = gtk.CheckButton(label=serial_checkbox_text)
            serial_checkbox.connect("toggled", self.paste, dialog)
            wrap_checkbox = gtk.CheckButton(label=wrap_checkbox_text)
            wrap_checkbox.connect("toggled", self.paste, dialog)
            wrap_checkbox.set_active(True)
            hbox.pack_start(wrap_checkbox, False)
            hbox.pack_end(serial_checkbox, False)
            table.attach(hbox, 0, 1, 2, 3, gtk.FILL, gtk.FILL, 0, 0)
            dialog.show_all()
            while True:
                result = dialog.run()
                if result == 1:
                    text_buffer = self.textbuffer.get_text(self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter())
                    for char in text_buffer:
                        self.teensy.type_key(char)
                    break
                else:
                    break
            dialog.destroy()

    def do_record(self, *args):
        chooser = gtk.FileChooserDialog(title="Record Session Input...", action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                                 gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        cwd = "."
        if self.teensy.recording_file:
            cwd = os.path.dirname(self.teensy.recording_file.name)
        chooser.set_current_folder(cwd)
        chooser.set_current_name("recording.kvmc")
        chooser.set_default_response(gtk.RESPONSE_OK)
        chooser.set_do_overwrite_confirmation(True)
        response = chooser.run()
        if response == gtk.RESPONSE_OK:
            self.record.set_sensitive(False)
            self.replay.set_sensitive(False)
            self.setup.set_sensitive(False)
            if self.stop_button_handler:
                self.stop_button.disconnect(self.stop_button_handler)
            self.stop_button_handler = self.stop_button.connect("clicked", self.do_stop, "record")
            self.stop_button.set_sensitive(True)
            selected_file = chooser.get_filename()
            self.rec_playback_path = os.path.dirname(selected_file)
            self.teensy.start_recording(chooser.get_filename())
            self.recorder_status_text.set_text("  Recording  ")
        chooser.destroy()

    def do_stop(self, *args):
        target = args[1]
        self.stop_button.set_sensitive(False)
        self.record.set_sensitive(True)
        self.replay.set_sensitive(True)
        self.setup.set_sensitive(True)
        if target == "record":
            self.recorder_status_text.set_text("    Idle     ")
            filename = self.teensy.stop_recording()
            md = gtk.MessageDialog(self.window, 
                gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, 
                gtk.BUTTONS_CLOSE, "Recording saved to file:\n%s" % filename)
            md.run()
            md.destroy()
        elif target == "replay":
            self.teensy.stop_replay = True
            

    def do_replay(self, *args):
        chooser = gtk.FileChooserDialog(title="Replay Session Input...", action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                                 gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_default_response(gtk.RESPONSE_OK)
        cwd = "."
        if self.teensy.replay_file:
            cwd = os.path.dirname(self.teensy.replay_file)
        chooser.set_current_folder(cwd)
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        chooser.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name("kvmc recordings")
        filter.add_pattern("*.kvmc")
        chooser.add_filter(filter)
        response = chooser.run()
        replay_file = None
        if response == gtk.RESPONSE_OK:
            replay_file = chooser.get_filename()
        chooser.destroy()
        if not replay_file:
            return
        error_msg = self.teensy.is_not_rec_file(replay_file)
        if error_msg:
            md = gtk.MessageDialog(self.window, 
                                   gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, 
                                   gtk.BUTTONS_CLOSE, error_msg)
            md.run()
            md.destroy()
            return
        md = gtk.Dialog("Confirm Replay", self.window,
                        gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                        (gtk.STOCK_YES, gtk.RESPONSE_OK, gtk.STOCK_NO, gtk.RESPONSE_CLOSE))
        md.set_resizable(False)
        msg = "Are you sure you want to replay session input from file:\n'%s'?" % os.path.basename(replay_file)
        md.vbox.pack_start(gtk.Label(msg), False)
        md.show_all()
        response = md.run()
        if response == gtk.RESPONSE_OK:
            self.replay_thread.replay_file = replay_file
        md.destroy()

    def preferences(self, *args):
        if type(args[0]) != type(gtk.ImageMenuItem()):
            args[1].response(args[2])
        else:
            dialog = gtk.Dialog("Preferences",
                        self.window,
                        gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,                       
                        (gtk.STOCK_SAVE, 1, gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
            dialog.set_resizable(False)
            table = gtk.Table(rows=5, columns=2, homogeneous=False)
            kvmc_in_label = gtk.Label("kvmc_in device:")
            kvmc_in_label.set_alignment(1, .5)   
            table.attach(kvmc_in_label, 0, 1, 0, 1)
            kvmc_device_entry = gtk.Entry()
            kvmc_device_entry.connect("activate", self.preferences, dialog, 1)
            kvmc_device_entry.set_text(self.teensy.kvmc_device)
            table.attach(kvmc_device_entry, 1, 2, 0, 1)
            capture_label = gtk.Label("capture device:")
            capture_label.set_alignment(1, .5)
            table.attach(capture_label, 0, 1, 1, 2)
            capture_device_entry = gtk.Entry()
            capture_device_entry.connect("activate", self.preferences, dialog, 1)
            capture_device_entry.set_text(self.teensy.capture_device)
            table.attach(capture_device_entry, 1, 2, 1, 2)
            capture_input_label = gtk.Label("capture device input:")
            capture_input_label.set_alignment(1, .5)
            table.attach(capture_input_label, 0, 1, 2, 3)
            capture_device_input_entry = gtk.Entry()
            capture_device_input_entry.connect("activate", self.preferences, dialog, 1)
            capture_device_input_entry.set_text(self.teensy.capture_device_input)
            table.attach(capture_device_input_entry, 1, 2, 2, 3)
            replay_speed_label = gtk.Label("Replay sessions at high speed (experimental):")
            replay_speed_label.set_alignment(1, .5)
            table.attach(replay_speed_label, 0, 1, 3, 4)
            replay_no_delay_checkbox = gtk.CheckButton(label=None)
            replay_no_delay_checkbox.set_active(self.teensy.replay_no_delay)
            table.attach(replay_no_delay_checkbox, 1,2,3,4)
            init_mouse_label = gtk.Label("Move mouse to bottom left on recording start:")
            init_mouse_label.set_alignment(1, .5)
            table.attach(init_mouse_label, 0, 1, 4, 5)
            record_init_mouse_pointer_checkbox = gtk.CheckButton(label=None)
            record_init_mouse_pointer_checkbox.set_active(self.teensy.record_init_mouse_pointer)
            table.attach(record_init_mouse_pointer_checkbox, 1,2,4,5)
            dialog.vbox.add(table)
            dialog.show_all()
            while True:
                result = dialog.run()
                if result == 1:
                    kvmc_device_text = kvmc_device_entry.get_text()
                    capture_device_text = capture_device_entry.get_text()
                    capture_device_input_text = capture_device_input_entry.get_text()
                    setup_error = None
                    if not os.path.exists(kvmc_device_text):
                        setup_error = "Specified kvmc device doesn't exist"
                    elif not os.path.exists(capture_device_text):
                        setup_error = "Specified capture device doesn't exist"
                    try:
                        capture_device_input_text = int(capture_device_input_text)
                    except ValueError:
                        setup_error = "Capture device input must be an integer"
                    if setup_error:
                        md = gtk.MessageDialog(self.window, 
                        gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_WARNING, 
                        gtk.BUTTONS_CLOSE, setup_error)
                        md.run()
                        md.destroy()
                    else:
                        self.teensy.kvmc_device = kvmc_device_text
                        self.teensy.capture_device = capture_device_text
                        self.teensy.capture_device_input = capture_device_input_text
                        self.teensy.replay_no_delay = replay_no_delay_checkbox.get_active()
                        self.teensy.record_init_mouse_pointer = record_init_mouse_pointer_checkbox.get_active()
                        self.teensy.set_config(self.teensy.conf_file)
                        self.serial_thread.pause = True
                        self.teensy.close()
                        self.teensy.__init__()
                        self.init_video()
                        self.serial_thread.pause = False
                        break
                else:
                    break
            dialog.destroy()

    def display_control(self, *args):
            dialog = gtk.Dialog("Display Control",
                        self.window,
                        gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,                       
                        (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
            dialog.set_resizable(False)
            sc_table = gtk.Table(rows=2, columns=3, homogeneous=True)
            sc_up = gtk.Button(stock=gtk.STOCK_GO_UP)
            sc_down = gtk.Button(stock=gtk.STOCK_GO_DOWN)
            sc_left = gtk.Button(stock=gtk.STOCK_GO_BACK)
            sc_right = gtk.Button(stock=gtk.STOCK_GO_FORWARD)
            sc_menu = gtk.Button(label="menu")
            sc_zoom = gtk.Button(label="zoom")
            sc_up.connect("clicked", self.press_sc_button, "up")
            sc_down.connect("clicked", self.press_sc_button, "down")
            sc_left.connect("clicked", self.press_sc_button, "left")
            sc_right.connect("clicked", self.press_sc_button, "right")
            sc_menu.connect("clicked", self.press_sc_button, "menu")
            sc_zoom.connect("clicked", self.press_sc_button, "zoom")
            sc_table.attach(sc_up, 1, 2, 0, 1)
            sc_table.attach(sc_down, 1, 2, 1, 2)
            sc_table.attach(sc_left, 0, 1, 1, 2)
            sc_table.attach(sc_right, 2, 3, 1, 2)
            sc_table.attach(sc_menu, 0, 1, 0, 1)
            sc_table.attach(sc_zoom, 2, 3, 0, 1)
            dialog.vbox.add(sc_table)
            dialog.show_all()
            dialog.run()
            dialog.destroy()

    def press_sc_button(self, *args):
        button = args[1]
        self.teensy.press_sc_button(button)

    def quit(self, *args):
        self.serial_thread.quit()
        self.replay_thread.quit()
        gtk.main_quit()

    def main(self):
        signal.signal(signal.SIGCHLD, self.handle_sigchld)
        gobject.threads_init()
        gtk.main()

    def handle_sigchld(self, signal_number, stack_frame):
        try:
            os.waitpid(-1, os.WNOHANG)
        except OSError:
            pass
        if self.mplayer_fd:
            mplayer_output = os.read(self.mplayer_fd, 1000)
            print mplayer_output
            print "Error: 'mplayer' unexpectedly closed. See above output for details and/or check config at %s" \
                % self.teensy.conf_file
            self.quit()

    def centre_mouse_in_widget(self, widget):
        top_left_x, top_left_y = self.window.get_position()
        centre_x = top_left_x + (widget.get_allocation().width / 2)
        centre_y = top_left_y + (widget.get_allocation().height / 2)
        gtk.gdk.Display.warp_pointer(self.display, self.display.get_default_screen(), centre_x, centre_y)

    def key_press_event_handler(self, widget, event):
        if self.grabbed_window:
            key_name = gtk.gdk.keyval_name(event.keyval)
            if key_name.lower() == "control_r":
                gtk.gdk.pointer_ungrab()
                gtk.gdk.keyboard_ungrab()
                self.grab_text_label.set_text("Click to control...")
                self.teensy.send_reset()
                self.grabbed_window = False
            else:
                self.teensy.press_key(key_name)
            return True
        return False

    def key_release_event_handler(self, widget, event):
        if self.grabbed_window:
            key_name = gtk.gdk.keyval_name(event.keyval)
            self.teensy.release_key(key_name)
        return True

    def button_press_event_handler(self, widget, event):
        event_attrs = dir(event)
        if not self.grabbed_window and not self.replay_thread.replay_file:
            if "button" in event_attrs and event.button == 1:
                self.teensy.send_reset()
                # lock mouse cursor to our window and hide it
                gtk.gdk.pointer_grab(widget.window,
                                     owner_events=True,
                                     event_mask=0,
                                     confine_to=widget.window,
                                     cursor=self.invisible)
                # lock keybord events to our window
                gtk.gdk.keyboard_grab(widget.window, owner_events=False)
                # lock mouse location to centre of window and store x, y
                self.centre_mouse_in_widget(widget)
                # update the toolbar
                self.grab_text_label.set_text("Right CTRL to release mouse...")
                self.grabbed_window = True
        else:
            if "button" in event_attrs:
                self.teensy.press_mouse_button(event.button)
            elif "direction" in event_attrs:
                if event.direction == gtk.gdk.SCROLL_UP:
                    self.teensy.move_mouse_wheel(0)
                elif event.direction == gtk.gdk.SCROLL_DOWN:
                    self.teensy.move_mouse_wheel(1)
        return True

    def button_release_event_handler(self, widget, event):
        if self.grabbed_window:
            self.teensy.release_mouse_button(event.button)
        return True

    def motion_notify_event_handler(self, widget, event):
        if self.grabbed_window:
            if not self.mouse_x or not self.mouse_y:
                # initialise mouse x,y on first event
                self.mouse_x = event.x
                self.mouse_y = event.y
            elif (time.time() - self.mouse_update_timer) > .01:
                self.mouse_update_timer = time.time()
                dist_x = (self.mouse_x - event.x) * -1
                dist_y = (self.mouse_y - event.y) * -1
                if dist_x + dist_y != 0:
                    self.centre_mouse_in_widget(widget)
                if dist_x > 127: dist_x = 127
                if dist_x < -127: dist_x = -127
                if dist_y > 127: dist_y = 127
                if dist_y < -127: dist_y = -127
                self.teensy.move_mouse(dist_x, dist_y)
        return True

    def expose_event_handler(self, widget, event):
        self.mouse_x = None
        self.mouse_y = None


WINDOWS_USB_SERIAL_DRIVER_INF = \
"""; Windows INF to load usbser driver for all CDC-ACM USB Serial Ports
; Copyright (C) 2008 PJRC.COM, LLC.
; Save as filename: cdc_acm_class.inf

[Version] 
Signature="$Windows NT$" 
Class=Ports
ClassGuid={4D36E978-E325-11CE-BFC1-08002BE10318} 
Provider=%MFGNAME% 
DriverVer=01/01/2008,1.0.0.0
[Manufacturer] 
%MFGNAME%=DeviceList, NTamd64
[DeviceList]
%DEVNAME%=DriverInstall,USB\Class_02&SubClass_02&Prot_01
[DeviceList.NTamd64]
%DEVNAME%=DriverInstall,USB\Class_02&SubClass_02&Prot_01
[DeviceList.NTia64]
%DEVNAME%=DriverInstall,USB\Class_02&SubClass_02&Prot_01
[SourceDisksNames]
1=%CD1NAME%
[SourceDisksFiles]
[DestinationDirs] 
DefaultDestDir=12 
[DriverInstall]
Include=mdmcpq.inf
CopyFiles=FakeModemCopyFileSection
AddReg=DriverAddReg
[DriverAddReg]
HKR,,EnumPropPages32,,"msports.dll,SerialPortPropPageProvider"
[DriverInstall.Services]
Include=mdmcpq.inf
AddService=usbser,0x00000002,LowerFilter_Service_Inst 
[Strings] 
MFGNAME="PJRC.COM, LLC."
DEVNAME="USB Serial (Communication Class, Abstract Control Model)"
CD1NAME="No CDROM required, usbser.sys is provided by Windows"
"""

if __name__ == "__main__":
    app = KVMC_GUI()
    app.main()

