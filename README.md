# KVMC 2.0

Copyright (C) 2018 - LinuxDojo Pty Ltd
https://github.com/gmurdocca/kvmc

KVMC is a hardware device that allows control of a second computer via a direct
connection to its HDMI/VGA and USB port. It presents a virtual keyboard and
mouse to the remote computer that echo's the controling computer's keystrokes
and mouse activity. The remote computer's live display is visible on the
controlling computer in a GUI app that behaves similarly to a virtual console
interface to a virtual machine.

## Features:

- Direct (not network based) Keyboard/Video/Mouse control of any computer 
- Recording of keystrokes and mouse activity for later replay
- Paste typable text from clipboard as keystrokes on remote machine
- Null-modem style serial link for data transfer (files, etc)

# Building:

## Build Hardware:

TODO

## Build and Deploy Software:

### Controll-side Teensy

This is to program the Teensy attached to the controlling computer. These steps
assume you are building on Linux.

Ensure the following packages (or their equivalents) are installed:

```
avr-gcc
avr-libc
```

Connect the Teensy to a USB port, then:

```
cd kvmc_in
make
make program
```

### Remote-side Teensy

This is to program the Teensy attached to the remote computer.

Ensure the following software is installed:

- Teensyduino (See here: https://www.pjrc.com/teensy/td_download.html - Follow
  the steps listed)

Open file kvmc_out/kvmc_out.ino in Arduino IDE. Select the following options in
the IDE:

- Tools -> Board: Teensy 2.0
- Tools -> USB Type: Serial + Keyboard + Mouse + Joystck

Compile and write to the Teensy:

- Sketch -> Verify/Compile (follow prompts)


### USB Storage Device Software

TODO




# USAGE

## To start KVMC:

1. Connect the KVMC Control port to a USB3.0 compliant port via USB and boot from USB
2. Start the KVMC app from the desktop
3. Connect server VGA port, then connect server USB port.

NOTE: Shutdown Lubuntu before unplugging the "laptop" port else you will risk
corrupting the ext2 filesystem in the file "casper-rw" on the root of the USB
key (located at /cdrom/casper-rw in Lubuntu). If corruption occurs, you may not
be able to boot Lubuntu. If this happens, fix it by mounting the USB key's fist
partition on a separate Linux system and enter as root:

  e2fsck -y <mount_point>/casper-rw

## Session recording and playback

Record to a file every keystroke and mouse event (and serial message, see
below) that you perform when controlling the remote computer for later
playback.  Select File -> Record/Replay Session Input. Good for repeating
arduous, repetitive, manual user input tasks.

## Paste as keystrokes

Paste whatever typable text is in your clipboard as keystrokes on the remote
machine.

## Transferring files between local and remote computers

The KVMC acts as a null-modem serial cable. Just fire up a terminal emulator on
both machines to transfer files with a binary serial protocol like Zmodem. Use
115200bps 8N1 for both sides of the serial connection.

Lubuntu comes with minicom which can be started from a shell. Open LXTerminal
and type "sudo minicom". The serial port you need to specify in minicom is
displayed on the bottom left of the KVMC App window in green. To get help in
minicom, press Ctrl-A then press Z.

The KVMC box presents a USB serial device on the remote machine. If the remote
computer runs Windows, this will appear as something like COM13, but you need
to install a serial driver before it will see this com port. To do so, open
notepad on the remote, choose Edit -> Paste as Keystrokes -> Paste Windows
Serial Driver -> click Paste. Then save the file as serial.inf in Windows,
right click it and install. Note on Mac and Linux machines there is no need to
install a driver for serial comms to work. Now you can fire up Hyperterm or
your favorite terminal emulator and you're away (give puttyZ for Windows a go,
there's a copy in KVMC's Lubuntu at /home/lubuntu/KVMC/puttyz.zip).

If you are recording during a serial session, only outgoing serial packets
sent by the controlling computer will be saved and replayed.

## Troubleshooting

- Keyboard/mouse events not working or behaving weirdly? Try reconnecting
  the Server USB cable (can take a few tries).

- App not starting or crashing? Try running it from the CLI to see any errors.
  Start LXTermial and type:

    sudo /home/lubuntu/KVMC/kvmc-1.1/kvmc.py"

- Things are terrible? Disconnect everything and try reboot. If you have to do
  this too often to get out of a pickle, remove the USB key from inside the
  KVMC (3 screws) and boot from it. Once booted, attach the KVMC box and fire
  up the KVMC app. You can then detach and re-attach the KVMC box without
  rebooting Lubuntu, making sure to close and open the KVMC GUI app each time.

- Cant close the KVMC App? Open a shell and type "sudo pkill -9 -f kvmc.py" to
  kill it.
