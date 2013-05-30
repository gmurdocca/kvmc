========
KVMC 1.1
========

Copyright (C) 2013 - George Murdocca
https://github.com/gmurdocca/kvmc

KVMC is a USB-to-KVM application and hardware device allowing a laptop to be
used as a raw KVM for a headless server, independent of server OS, supporting
keystroke/mouse event recording and replay, and null-modem style serial data
transfer. Basically use your laptop's screen, keyboard and mouse as if directly
plugged into the VGA and USB ports of an external machine, with some cool
extra features :)

See http://gmurdocca.livejournal.com/4211.html for hardware device
implementation, photos and more information.

To start KVMC:
==============

1. Connect KVMC "laptop" port to a laptop or PC via USB and boot from USB
2. Start the KVMC app from the desktop
3. Connect server VGA port, then connect server USB port.

NOTE: Shutdown Lubuntu before unplugging the "laptop" port else you will risk
corrupting the ext2 filesystem in the file "casper-rw" on the root of the USB
key (located at /cdrom/casper-rw in Lubuntu). If corruption occurs, you may not
be able to boot Lubuntu. If this happens, fix it by mounting the USB key's fist
partition on a separate Linux system and enter as root:

  e2fsck -y <mount_point>/casper-rw

Troubleshooting
===============

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

USAGE
=====

Session recording and playback
------------------------------

Record to a file every keystroke and mouse event (and serial message, see
below) that you perform when controlling the remote computer for later
playback.  Select File -> Record/Replay Session Input. Good for repeating
arduous, repetitive, manual user input tasks.

Paste as keystrokes
-------------------

Paste whatever typable text is in your clipboard as keystrokes on the remote
machine.

Transferring files between local and remote computers
-----------------------------------------------------

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

If you are recording during a serial session, only your outgoing serial packets
will be saved and replayed.

Display Control
---------------

You can adjust some display settings to try to make the remote screen a tad
clearer (it will never be very clear due to the VGA scanline converter chip
inside the box) using the Display Control option of the Edit menu. If the
image quality is still too unbearable, connect an external VGA monitor to the
optional port on the side of the KVMC box.


Enjoy!
George Murdocca

Any donations appreciated! To donate...
  via Paypal, send to email address: george (at) murdocca.com.au
  via Bitcoin, send to wallet address: 18w7kYPC3F6WM7839NuBNQsbzd8QsP1Agb
