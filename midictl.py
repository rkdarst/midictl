import argparse
from collections import namedtuple
from functools import partial
import glob
import os
import subprocess
import sys
import time
import traceback

import mido
import pulsectl

P = pulsectl.Pulse()



def listen(argv):
    """Main event loop.

    Listen for MIDI events and call the handler for each.
    """
#    input_name = list(filter(lambda x: "lpd8" in x.lower(), mido.get_input_names()))[0]
#    with mido.open_input(input_name) as port:
    parser = argparse.ArgumentParser()
    parser.add_argument('device_file', nargs='?', default=glob.glob('/dev/midi*')[0])
    parser.add_argument('--config', '-c', nargs='*', default=['config.py'])
    args = parser.parse_args()

    CONFIG_MODIFICATION_TIME = os.stat(__file__).st_mtime

    for configfile in args.config:
        exec(open(configfile).read(), globals())
        CONFIG_MODIFICATION_TIME = max(CONFIG_MODIFICATION_TIME, os.stat(configfile).st_mtime)

    f = open(args.device_file, 'rb')

    parser = mido.Parser()
    start_time = time.time()
    while True:
        b = f.read(1)
        # We need to flush any bytes remaining in the device file, or else they
        # will all be delivered now.
        if time.time() < start_time + 0.1:
            continue
        #
        b = b[0] # byte to int
        parser.feed_byte(b)
        msg = parser.get_message()
        if msg:
            print(msg)
            handle(msg)

            # Restart script if config has been modified
            mtime = max(os.stat(fname).st_mtime
                        for fname in [__file__] + args.config)
            if mtime > CONFIG_MODIFICATION_TIME:
                f.close()
                print("Restarting to reload config...")
                os.execv(sys.executable, [sys.executable] + sys.argv)


def handle(msg):
    """Dispatch a single message to any handlers.

    This function is called once per message, and matches all dispatch
    filters.  Anything that matches all receives the event.
    """
    for dis, func in DISPATCHERS:
        if    (dis.t  is None or dis.t == msg.type) \
          and (dis.ch is None or dis.ch == msg.channel) \
          and (dis.n  is None or dis.n == getattr(msg, 'note', None)) \
          and (dis.c  is None or dis.c == getattr(msg, 'control', None)) \
          and (dis.p  is None or dis.p == getattr(msg, 'program', None)) \
          and (dis.b  is None or BUTTONMAP[msg.channel][dis.b] == getattr(msg, 'note', None)) \
          :
            if isinstance(func, partial):
                print("  -->", func.func.__name__, func.args, func.keywords)
            else:
                print("  -->", func.__name__)
            func(msg)

def find_pulse(sel):
    """Find PulseAudio devices matching a certain selector.

    Returns an iterator, filtered based on selection criteria."""
    it = find_pulse_basic(sel)
    it = pulse_filter_name(sel, it)
    #print('a', list(it))
    it = pulse_filter_it(sel, it)
    it = pulse_filter_last(sel, it)
    return it

def find_pulse_basic(sel):
    """Yields a basic list of PulseAudio devices.

    This is filter down by other filters.
    """
    if sel.t == 'source':
        type_ = 'source'
        item_list   = P.source_output_list
        card_list   = P.source_list
        card_lookup = {x.index: x for x in P.source_list()}
    if sel.t == 'sink':
        type_ = 'sink'
        item_list   = P.sink_input_list
        card_list   = P.sink_list
        card_lookup = {x.index: x for x in P.sink_list()}

    if sel.it is not None:
        # Filtering for items
        for src in item_list():
            src.card_object = card_lookup[getattr(src, type_)]
            yield src
    else:
        # Filtering for cards
        for src in card_list():
            yield src

def pulse_filter_name(sel, it):
    """Filter PulseAudio based on the card name
    """
    #print(sel.name)
    if not sel.name or sel.name == '*':
        yield from it
    for item in it:
        if hasattr(item, 'card_object'):
            card = item.card_object
        else:
            card = item
        #print(card, card.name)
        if sel.name in card.name:
            yield item

def pulse_filter_it(sel, it):
    """Filter PulseAudio based on source/sink item name
    """
    if sel.it is None or sel.it == '*':
        yield from it
    for item in it:
        if sel.it in src.proplist['application.process.binary']:
            yield item

def pulse_filter_last(sel, it):
    """Filter PulseAudio based on being the last item or not
    """
    items = tuple(it)
    if sel.last is False:
        return items[:-1]
    if sel.last is True:
        return items[-1:]
    return items



def mute(msg, sel, state=None):
    """Toggle or set mute"""
    for source in find_pulse(sel):
        mute = source.mute
        if state is not None:
            new_mute = state
        else:
            new_mute = not mute
        print(new_mute)
        P.mute(source, new_mute)

def volume(msg, sel, low=0, high=1):
    """Set volume"""
    for source in find_pulse(sel):
        volume = low + (high-low)*msg.value/127
        P.volume_set_all_chans(source, volume)


def pulse_move(msg, sel, move_to):
    """Move a PulseAudio device to a different card"""
    speaker = next(iter(find_pulse(move_to)))
    print(speaker)
    for source in find_pulse(sel):
        print(source)
        try:
            P.sink_input_move(source.index, speaker.index)
        except:
            traceback.print_exc()
    P.sink_default_set(speaker)


# v4l cameras exposures
#  Requirements: v4l2-ctl command line utility installed (debian: v4l-utils)
def camera_exposure(msg, low=0, high=500, control='exposure_auto=1,exposure_absolute=%s'):
    """Use v4l2 to adjust exposure"""
    exposure = low + (high-low)*msg.value/127
    cmd = ['v4l2-ctl', '--set-ctrl', control%exposure]
    subprocess.call(cmd)
def camera_exposure_auto(msg, control='exposure_auto=3'):
    """Use v4l2 to set exposure to auto-mode"""
    cmd = ['v4l2-ctl', '--set-ctrl', control]
    subprocess.call(cmd)



def keystroke(msg, x11_name, stroke):
    """Send a keystroke to an application window

    Dependency: xdotool
    This has to:
      - focus the other window
      - send the keystroke
      - re-focus the original window
    """
    # WARNING: this prints an error if the window is not visible on the screen.
    cmd = ['xdotool', 'search', '--name', x11_name,
           'windowfocus',
           'key', 'alt+apostrophe', stroke,
           'windowfocus', subprocess.getoutput('xdotool getwindowfocus')
           ]
    subprocess.call(cmd)


def zoom_mute(msg, ignore_fast=None):
    """Zoom software mute via simulater keypress.

    If ignore_fast is a number, ignore note_on events with more than
    this velocity.  This can be useful for re-synchronizing a keypad
    toggleable key with the application state.
    """
    if ignore_fast and msg.type == 'note_on' and msg.velocity >= ignore_fast:
        print("Fast press, ignoring")
        return
    return keystroke(msg, x11_name='Zoom Meeting$', stroke='alt+a')

def zoom_video(msg):
    return keystroke(msg, x11_name='^Zoom Meeting$', stroke='alt+v')

def teams_mute(msg):
    return keystroke(msg,
                     x11_name=r'\(Meeting\) \| Microsoft Teams - Google Chrome$',
                     stroke='ctrl+shift+m')


#
from obswebsocket import obsws, requests as obs_requests
OBS = obsws("localhost", 4444, "password")
def obs_switch(msg, scene):
    OBS.connect()
    OBS.call(obs_requests.SetCurrentScene(scene))
    OBS.disconnect()



# t = type ('note_on', 'note_off', 'control_change')
# ch = channel (int)
# n = note (int)
# c = control (int)
Dispatch = namedtuple('Dispatch',
                      ['t', 'ch', 'n', 'c', 'p', 'b'],
                      defaults=[None, None, None, None, None, None])

# Select PulseAudio devices.
# t = 'source', 'sink'.  Select either sources or sinks.
# name = 'match the name.  Non-glob pattern match
# i = if True, find items instead of sources
Selector = namedtuple('Selector',
                      ['t', 'name', 'it', 'desc', 'last'],
                      defaults=[None, None, None, None, None])

ON = 'note_on'
OFF = 'note_off'
CC = 'control_change'
PC = 'program_change'




if __name__ == "__main__":
    listen(sys.argv[0:])
