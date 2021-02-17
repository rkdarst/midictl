import argparse
from collections import namedtuple
from functools import partial
import glob
import os
import sys
import time

import mido
import pulsectl

P = pulsectl.Pulse()


def listen(argv):
#    input_name = list(filter(lambda x: "lpd8" in x.lower(), mido.get_input_names()))[0]
#    with mido.open_input(input_name) as port:
    parser = argparse.ArgumentParser()
    parser.add_argument('device_file', nargs='?', default=glob.glob('/dev/midi*')[0])
    args = parser.parse_args()

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


def handle(msg):
    for dis, func in DISPATCHERS:
        if    (dis.t  is None or dis.t == msg.type) \
          and (dis.ch is None or dis.ch == msg.channel) \
          and (dis.n  is None or dis.n == getattr(msg, 'note', None)) \
          and (dis.c  is None or dis.c == getattr(msg, 'control', None)) \
          and (dis.p  is None or dis.p == getattr(msg, 'program', None)):
            print('  -->', func)
            func(msg)


def find_pulse(sel):
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

    if sel.it:
        # Filtering for items
        if sel.last is True:
            yield item_list()[-1]
            return
        if sel.last is False:
            yield from item_list()[:-1]
        for src in item_list():
            if sel.name:
                if sel.name not in card_lookup[getattr(src, type_)].name:
                    continue
            if sel.it == '*':
                yield src
                continue
            if sel.it not in src.proplist['application.process.binary']:
                continue
            yield src
    else:
        # Filtering for cards
        for src in card_list():
            if sel.name == '*':
                yield src
                continue
            if sel.name not in src.name:
                continue
            yield src

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

# t = type ('note_on', 'note_off', 'control_change')
# ch = channel (int)
# n = note (int)
# c = control (int)
Dispatch = namedtuple('Dispatch',
                      ['t', 'ch', 'n', 'c', 'p'],
                      defaults=[None, None, None, None, None])

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
mic = Selector(t='source', name='USB_Advanced', it='*')
hdmi = Selector(t='sink', name='hdmi')
hdmi_all = Selector(t='sink', name='hdmi', it='*')
headphones = Selector(t='sink', name='hdmi', it='*')

# Program dispatches here.
DISPATCHERS = [
    (Dispatch(t=ON, ch=0, n=42), partial(mute, sel=mic, state=False)),
    (Dispatch(t=OFF,ch=0, n=42), partial(mute, sel=mic, state=True)),
    (Dispatch(t=ON, ch=0, n=43), partial(mute, sel=mic)),
    (Dispatch(t=CC, ch=0, c=1 ), partial(volume, sel=mic)),

    (Dispatch(t=ON, ch=0, n=39), partial(mute, sel=hdmi)),
    (Dispatch(t=CC, ch=0, c=5 ), partial(volume, sel=hdmi_all, low=0, high=.5)),
    (Dispatch(t=CC, ch=0, c=6 ), partial(volume, sel=hdmi_all._replace(last=True), low=0, high=.5)),
    (Dispatch(t=CC, ch=0, c=7 ), partial(volume, sel=hdmi_all._replace(last=False), low=0, high=.5)),
    ]


if __name__ == "__main__":
    listen(sys.argv[0:])
