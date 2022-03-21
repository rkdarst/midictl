import argparse
import collections
from collections import namedtuple
import functools
from functools import partial
import glob
import os
import re
import subprocess
import sys
import time
import traceback

import mido
import pulsectl

P = pulsectl.Pulse()
# Check available devices with:
# P.source_list() / P.sink_list()
# P.source_output_list() / P.sink_input_list()


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

    # Read config file, saving its modification time for automatic relead.
    CONFIG_MODIFICATION_TIME = os.stat(__file__).st_mtime
    for configfile in args.config:
        exec(open(configfile).read(), globals())
        CONFIG_MODIFICATION_TIME = max(CONFIG_MODIFICATION_TIME, os.stat(configfile).st_mtime)

    # Open the device
    f = open(args.device_file, 'rb')

    # Main loop
    parser = mido.Parser()
    start_time = time.time()
    while True:
        # To prevent blocking and other problems, we (unfortunately) have to
        # read byte-by-byte.  We do manual reading like this instead of some
        # more direct method to prevent dependencies on other compiled Python
        # extensions.
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
            # Restart script if config has been modified
            mtime = max(os.stat(fname).st_mtime
                        for fname in [__file__] + args.config)
            if mtime > CONFIG_MODIFICATION_TIME:
                f.close()
                print("Restarting to reload config...")
                os.execv(sys.executable, [sys.executable] + sys.argv)

            # Actual event handler
            print(msg)
            handle(msg)


def handle(msg):
    """Dispatch a single message to any handlers.

    This function is called once per message, and matches all dispatch
    filters.  Anything that matches all of the filters receives the event.
    """
    for dis, func in DISPATCHERS:
        if    (dis.t  is None or dis.t == msg.type) \
          and (dis.ch is None or dis.ch == msg.channel) \
          and (dis.n  is None or dis.n == getattr(msg, 'note', None)) \
          and (dis.c  is None or dis.c == getattr(msg, 'control', None)) \
          and (dis.p  is None or dis.p == getattr(msg, 'program', None)) \
          and (dis.b  is None or BUTTONMAP[msg.channel][dis.b] == getattr(msg, 'note', None)) \
          and (dis.val is None or dis.val == getattr(msg, 'value', None)) \
          and (dis.vel is None or dis.vel == getattr(msg, 'velocity', None)) \
          :
            if isinstance(func, partial):
                print("  -->", func.func.__name__, func.args, func.keywords)
            else:
                print("  -->", func.__name__)
            func(msg)


class Counter:
    """Incrementing counter with dict-like interface

    This is use to record number of button presses, to implement things
    such as toggles.
    """
    def __init__(self):
        self._data = collections.defaultdict(lambda: -1)
    def __getitem__(self, name):
        self._data[name] += 1
        return self._data[name]
COUNTER = Counter()


RATE_LIMIT_STATE = collections.defaultdict(lambda: {'last_time': [], 'last_msg': None, 'lock': threading.Lock()})
import threading
def rate_limit(rate=.5):
    """Decorator to limit rate a function can be called.

    In addition to rate limiting, when it is called, it is always called
    with the _last_ value.  In addition, ensure it is called with that
    last value.  Thus, we can't drop calls that occur too fast, but we
    have to keep a memory of the value passed, and make sure that we run
    it on that final value at least once.  This happens by starting a
    callback for each dropped function (once per interval), which runs
    (on the most recent value) at the end of that interval.

    This should probably be refactored, this was my first hack attempt
    while experimenting with it.
    """
    # This is currently kind of a hack and can probably be re-written
    # completely later.
    def wrapper(f):
        @functools.wraps(f)
        def invoke(msg, *args, RLID=None, **kwargs):
            if RLID is not None:
                ID = RLID
            else:
                ID = hash(tuple(kwargs.items()))
            state = RATE_LIMIT_STATE[ID]
            now = time.time()
            last_time = state['last_time'] = [ t for t in state['last_time'] if t+rate > now ]
            #print(last_time)
            if not last_time:
                #print('... running')
                # append last_time
                last_time.append(now)
                # run right now
                T = threading.Thread(target=f, args=(msg,)+args, kwargs=kwargs, daemon=True)
                T.start()
            elif last_time[-1] > now:
                #print('... already queued')
                state['last_msg'] = msg
                return
            else:
                #print('... queuing')
                # append last_time
                last_time.append(now+rate)
                state['last_msg'] = msg
                # delay invoke
                def delay_invoke(*args, **kwargs):
                    #print("delay_invoke")
                    time.sleep(rate)
                    f(state['last_msg'], *args, **kwargs)
                    #print("running")
                T = threading.Thread(target=delay_invoke, args=args, kwargs=kwargs, daemon=True)
                T.start()

        return invoke
    return wrapper


#
# PulseAudio-related functions
#
def find_pulse(sel):
    """Find PulseAudio devices matching a certain selector.

    Returns an iterator over PulseAudio sources/sinks (or items attached
    to the sources/sinks) which match certain criteria.
    """
    # First get a basic iterater, then filter the iterator progressively using
    # three more functions.
    it = find_pulse_basic(sel)
    it = pulse_filter_card_name(sel, it)
    it = pulse_filter_item_name(sel, it)
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

def pulse_filter_card_name(sel, it):
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
        if re.search(sel.name, card.name):
            yield item

def pulse_filter_item_name(sel, it):
    """Filter PulseAudio based on source/sink item name
    """
    if sel.it is None or sel.it == '*':
        yield from it
    for item in it:
        if re.search(sel.it, item.proplist.get('application.name', '')):
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
        P.mute(source, new_mute)

def volume(msg, sel, low=0, high=1):
    """Set volume"""
    for source in find_pulse(sel):
        volume = low + (high-low)*msg.value/127
        P.volume_set_all_chans(source, volume)


def pulse_move(msg, sel, move_to, counter=None):
    """Move a pulse item to a differest source/sink

    sel: selects the device
    move_to: List of selectors to move the selected devices to
    counter: optional, used to count button presses.

    """
    if counter is None:
        counter = hash((sel, move_to))
    count = COUNTER[counter]
    """Move a PulseAudio device to a different card"""
    if isinstance(move_to, (tuple, list)) and not isinstance(move_to, Selector):
        move_to = move_to[count%len(move_to)]
    speaker = next(iter(find_pulse(move_to)))
    for source in find_pulse(sel):
        try:
            if move_to.t == 'sink':
                P.sink_input_move(source.index, speaker.index)
            else:
                P.source_output_move(source.index, speaker.index)
        except:
            traceback.print_exc()
    if move_to.t == 'sink':
        P.sink_default_set(speaker)
    else:
        P.source_default_set(speaker)

#
# v4l2 cameras control
#
#  Requirements: v4l2-ctl command line utility installed (debian: v4l-utils)
def v4l2_set(msg, control, low=0, high=255, value=None, zero=None):
    """Use v4l2 to adjust exposure"""
    if zero is not None and getattr(msg, 'value', None) == 0:
        value = zero
    elif hasattr(msg, 'value'):
        value = low + (high-low)*msg.value/127
    cmd = ['v4l2-ctl', '--set-ctrl', control%{'value':value}]
    subprocess.call(cmd)
def camera_exposure(msg, low=0, high=1000, control='exposure_auto=1,exposure_absolute=%(value)s'):
    """Use v4l2 to adjust exposure"""
    return v4l2_set(msg, low=low, high=high, control=control)
def camera_exposure_auto(msg, control='exposure_auto=3'):
    """Use v4l2 to set exposure to auto-mode"""
    return v4l2_set(msg, control=control)
camera_brightness = partial(v4l2_set, control='brightness=%(value)s', zero=128)
camera_contrast = partial(v4l2_set, control='contrast=%(value)s', zero=128)
camera_saturation = partial(v4l2_set, control='saturation=%(value)s', zero=128)
camera_sharpness = partial(v4l2_set, control='sharpness=%(value)s', zero=128)
camera_gain = partial(v4l2_set, control='gain=%(value)s', zero=64)
camera_wb_temp = partial(v4l2_set, control='white_balance_temperature_auto=0,white_balance_temperature=%(value)s', low=2000, high=6500)
camera_wb_auto = partial(v4l2_set, control='white_balance_temperature_auto=1')
camera_pan = partial(v4l2_set, control='pan_absolute=%(value)s', low=-36000, high=36000, zero=0)
camera_tilt = partial(v4l2_set, control='tilt_absolute=%(value)s', low=-36000, high=36000, zero=0)



def keystroke(msg, x11_name, stroke):
    """Send a keystroke to an application window

    Dependency: xdotool
    This has to:
      - focus the other window
      - send the keystroke
      - re-focus the original window

    TODO:
    - How to find window name?
    - Search by other tools
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
    return keystroke(msg, x11_name='Zoom Meeting$', stroke='alt+v')

def zoom_raisehand(msg):
    return keystroke(msg, x11_name='Zoom Meeting$', stroke='alt+y')

def teams_mute(msg):
    return keystroke(msg,
                     x11_name=r'\(Meeting\) \| Microsoft Teams - Google Chrome$',
                     stroke='ctrl+shift+m')


# https://github.com/Elektordi/obs-websocket-py
from obswebsocket import obsws, requests as obs_requests
import obswebsocket.exceptions
OBS = obsws("localhost", 4445, "password")

def obs(f):
    """Decorator to create OBS websocket connection per-call.

    This is useful when you have async executaion.
    """
    @functools.wraps(f)
    def new(*args, **kwargs):
        OBS2 = obsws(OBS.host, OBS.port, OBS.password)
        try:
            OBS2.connect()
        except obswebsocket.exceptions.ConnectionFailure as e:
            print("Could not connect to OBS: %s"%str(e))
            return None
        ret = f(*args, **kwargs, OBS=OBS2)
        OBS2.disconnect()
        return ret
    return new

@obs
def obs_switch(msg, scene, OBS):
    OBS.call(obs_requests.SetCurrentScene(scene))

@obs
def obs_mute(msg, source, mute=None, OBS=None):
    """Toggle or set mute

    if the argument `mute` is None, toggle.  Otherwise set it to this
    value.  If source is a list and reuest toggling, get the state of
    the first source, toggle it, and set all sources to that value.
    """
    if not isinstance(source, (list,tuple)):
        # Single source
        if mute is None:
            OBS.call(obs_requests.ToggleMute(source))
        else:
            OBS.call(obs_requests.SetMute(source, mute=mute))
    else:
        # Multiple devices.  Get the mute status of the first one, invert it,
        # and set all to that status.
        if mute is None:
            try:
                mute = not OBS.call(obs_requests.GetMute(source[0])).getMuted()
            except KeyError:
                print("KeyError, perhaps unknown source: %s"%source[0])
        for src in source:
            OBS.call(obs_requests.SetMute(src, mute=mute))


@obs
def obs_scene_item_visible(msg, item, visible=None, OBS=None):
    """Toggle or set scene item visibility

    This works just like `obs_mute`, but for scene item visibility.
    """
    if not isinstance(item, (list,tuple)):
        item = [item]
    if visible is None:
        visible = not OBS.call(obs_requests.GetSceneItemProperties(item[0])).getVisible()
    for item_ in item:
        OBS.call(obs_requests.SetSceneItemProperties(item_, visible=visible))

@obs
def obs_toggle_recording(msg, state=None, OBS=None):
    """Toggle or set recording status
    """
    if state is None:
        OBS.call(obs_requests.StartStopRecording())
    elif state:
        OBS.call(obs_requests.StartRecording())
    else:
        OBS.call(obs_requests.StopRecording())



@obs
def obs_text_clock(msg, source, OBS=None):
    """Update the NN value of a xx:NN text message"""
    ret = OBS.call(obs_requests.GetTextFreetype2Properties(source))
    text = ret.getText()
    new_time = int(msg.value/127 * 59)
    def replace(m):
        return "{0}{1:02d}{2}".format(m.group(1), new_time, m.group(3))
    new_text = re.sub(r'([xX?]{2}:)(\d{2})(\s+|$)', replace, text)
    ret = OBS.call(obs_requests.SetTextFreetype2Properties(source, text=new_text))

@rate_limit(.25)
@obs
def obs_scale_source(msg, source, scene=None, scale=None, low=0, high=1, OBS=None):
    """Scale an OBS scene element.

    This adjusts the scale of a scene element (obs terminology: source).
    Internally, it seems that x_scale and y_scale are the internal
    values, so we can directly set those.  To control the anchor point
    of the scaling, edit the transform in OBS.
    """
    if not isinstance(scene, (list, tuple)):
        scene = [ scene ]
    for scene_ in scene:
        if scale is None:
            scale = low + (high-low)*(msg.value/127)
        #ret = OBS.call(obs_requests.GetSceneItemProperties(source, scene_name=scene))
        #print(ret)
        #width = (msg.value/255) * ret.getSourceWidth()
        ret = OBS.call(obs_requests.SetSceneItemTransform(source, scene_name=scene_, x_scale=scale, y_scale=scale, rotation=0))#ret.getRotation()))
        #print(ret)

CROP_FACTORS = {
    None: {'top':  0, 'bottom':  0, 'left':  0, 'right':  0, },
    1:    {'top':  0, 'bottom':  0, 'left': 59, 'right':  59, },
    2:    {'top': 90, 'bottom':  0, 'left': 12, 'right': 12, },  # checked
    3:    {'top':  4, 'bottom':  0, 'left': 60, 'right': 60, },  # checked
    5:    {'top': 50, 'bottom':  0, 'left': 11, 'right': 11, },  # checked
    }
@rate_limit(.25)
@obs
def obs_set_crop(msg, source, scene=None, OBS=None):
    """Set cropping (special use)
    """
    # One person
    if msg.value < 1:
        crop = CROP_FACTORS[1]
        print("  crop → 1 person")
    # Two people
    elif msg.value < 40:
        crop = CROP_FACTORS[2]
        print("  crop → 2 people")
    # 3-4 people
    elif msg.value < 80:
        crop = CROP_FACTORS[3]
        print("  crop → 3-4 people")
    # 5-6 people
    elif msg.value < 127:
        crop = CROP_FACTORS[5]
        print("  crop → 5-6 people")
    else:
        crop = CROP_FACTORS[None]
        print("  crop → uncropped")
    if isinstance(scene, str):
        scene = [scene]
    for scene_ in scene:
        ret = OBS.call(obs_requests.SetSceneItemProperties(source, scene_name=scene, crop=crop))
    #print(ret)

@obs
def obs_recording_time_copy(msg, OBS=None, selection='clipboard'):
    """Copy current recording timestamp to clipboard

    Copy current recording time to the clipboard.  This currently
    depends on the xclip utility, so only works on Unix.  It also seems
    to be about three seconds behind reality (unknown reason).  In some
    sense this is useful, since it gives you some buffer.  It needs to
    be investigated in the future, though.

    selection: 'primary' or 'secondary' or 'clipboard'.
    """
    ret = OBS.call(obs_requests.GetRecordingStatus())
    if not ret.getIsRecording():
        return
    timestamp = ret.getRecordTimecode() # string
    #print(timestamp)
    # convert to seconds
    parts = timestamp.split(':')
    seconds = float(parts[-1]) + float(parts[-2])*60 + float(parts[-3])*3600
    # convert back to HH:MM:SS with better format
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if hours:
        timestamp = '%d:%02d:%02d'%(hours, minutes, seconds)
    else:
        timestamp ='%d:%02d'%(minutes, seconds)

    selection = 'clipboard' # 'primary' or 'secondary' or 'clipboard'
    subprocess.run(['xclip', '-in', '-selection', 'clipboard'],
                   input=timestamp, encoding='utf8')

#@rate_limit(.25)




# External processes
def call(msg, cmd):
    # Note: this has not been tested,
    subprocess.Popen(cmd, shell=True)



@rate_limit()
def echo(msg, text="TEST"):
    print(text, msg)

# t = type ('note_on', 'note_off', 'control_change')
# ch = channel (int)
# n = note (int)
# c = control (int)
Dispatch = namedtuple('Dispatch',
                      ['t', 'ch', 'n', 'c', 'p', 'b', 'val', 'vel'],
                      defaults=[None, None, None, None, None, None, None, None])

# Select PulseAudio devices.
# t = 'source', 'sink'.  Select either sources or sinks.
# name = 'match the name.  Non-glob pattern match
# i = if True, find items instead of sources
Selector = namedtuple('Selector',
                      ['t', 'name', 'it', 'desc', 'last'],
                      defaults=[None, None, None, None, None])
class Not:
    """Equality compariason returns true if values are not equal"""
    def __init__(self, x):
        self.value = x
    def __eq__(self, other):
        return not self.value == other
class Range:
    """Equality compariason returns true if values are not equal"""
    def __init__(self, low, high):
        self.low, self.high = low, high
    def __eq__(self, other):
        return self.low <= other < self.high
class In:
    """Equality compariason returns true if values are not equal"""
    def __init__(self, *args):
        self.items = args
    def __eq__(self, other):
        return other in self.items
# The definitions of the 't' argument of the Selector
ON = 'note_on'
OFF = 'note_off'
CC = 'control_change'
PC = 'program_change'




if __name__ == "__main__":
    listen(sys.argv[0:])
