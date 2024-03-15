# Act based on MIDI events


## Installation and basic usage

Installation: The package is currently not installable, but will be
made into a Python package later.

Usage: `python midictl.py [-c config.py] [midi_device]`.  Note that
this opens the raw `/dev/midi*` device, to avoid having to install
some compiled MIDI libraries.

## Features

* Restarts when config changes (but loses one event)



## Architecture and configuration

The main entry point is `listen`, which parses arguments, opens the
device, listens to the MIDI device, and dispatches each event to the
`handle` function.

The `handle` function is called for each MIDI event that comes in.  For each
event, it searches the `DISPATCHERS` list, which is pairs of
`(dispatch_selector, callback_function)`.  Any row which matches the
dispatch_selector is called as `callback_function(msg)`, where `msg`
is the MIDI event from the mido library.  Functions can do whatever.

The namedtuple class `Dispatch` is the dispatch selector, which has
properties to select on midi events.  A MIDI event is sent to each
callbacks which has every given property matching the event.  Dispatch
properties include:
* `t`: type (string: `note_on`, `note_off`, `control_change`,
  `program_change`; has shortcut symbols `ON`, `OFF`, `CC`, `PC`.)
* `ch`: channel
* `n`: note
* `c`: control
* `p`: program
* `b`: look up note through `BUTTONMAP` to be simpler than remembering
  all nodes.
  If : `note == BUTTONMAP[msg.channel][dispatcher.b]`
* `val`: value
* `vel`: velocity
All given selectors must
match (AND).  To implement an OR,
one usually adds multiple similar selectors to `DISPATCHERS`.

It will always print event before it dispatches them, so you can start
with an empty config file and slowly add things.

For an example configuration, see `config.py`



## Available events

The following events can be triggered

* `mute`: Mute PulseAudio devices
* `volume`: Adjust PulseAudio volumes
* `pulse_move`: Move PulseAudio inputs/outputs to different cards
* V4L camera exposure
  * `camera_exposure`: Set camera exposure to value
  * `camera_exposure_auto`: Set camera exposure to auto mode
* `keystroke`: Send a keystroke to an X11 application.  Several
  pre-made bindings are:
  * `zoom_mute`: Toggle Zoom application mute
  * `zoom_video`: Toggle Zoom application video
  * `teams_mute`: Toggle Microsoft Teams mute in Chrome web browser.
* OBS
  * `obs_switch`: Switch OBS scenes

* PulseAudio mutes and volume changes. `Selector` is namedtuple which
  can select which pulse devices to operate on,


## Utility functions

These functions can be used to modify other functions:

* `rate_limit`: A continuous event (such as turning a knob) won't be
  called more than every `rate` seconds.  It makes sure to call with
  the final value.
* `delay`: can be used to detect long presses and similar and
  distinguish them from short presses.  Example: push button quickly
  to switch to scene A, press button long to switch to scene B.


## Configuration examples

Config is by default read from a `config.py` file, which gets executed
in the module namespace so has full control of everything.  Examples
are below:


Turning control knob 5 adjusts the microphone volume for all items on
the PulseAudio source that contains `USB_Advanced` in the name.

```python
mic = Selector(t='source', name='USB_Advanced', it='*')
DISPATCHERS = [
    (Dispatch(t=CC, c= 5), partial(volume, sel=mic)),
]
```

Mute the HDMI PluseAudio device (contains 'hdmi' in the PulseAudio
name), when button 7 is pressed on channel 0.  Instead of defining the
button by note, set up an indirect BUTTONMAP, so that different MIDI
channels have consistent button names, even if their notes are
inconsistent.  This saves re-programming the device just for this
purpose.

```python
BUTTONMAP = {
    # channel: [note_for_button_id]
    0: [None, 36, 37, 38, 39, 40, 41, 42, 43],
    1: [None, 35, 36, 42, 39, 37, 38, 46, 44],
    2: [None, 60, 62, 64, 65, 67, 69, 71, 72],
    3: [None, 36, 38, 40, 41, 43, 45, 47, 48],
    }

hdmi = Selector(t='sink', name='hdmi'),
DISPATCHERS = [
    (Dispatch(t=ON, ch=0, b= 7), partial(mute, sel=hdmi)),
]
```

Toggle Zoom mute, when you push note 43 on channel 0.

```python
DISPATCHERS = [
    (Dispatch(t=ON, ch=0, n=43), zoom_mute),
]
```

Turning control knob 6 on channel 0 will adjust the camera exposure
setting via the v4l2 Linux camera system.  If the knob is turned to
zero, it will go to auto-mode.  If you turn it to anything else, it
will adjust the exposure

```python
DISPATCHERS = [
    (Dispatch(t=CC, ch=0, c= 6, val=Not(0)), partial(camera_exposure, low=50, high=500)),
    (Dispatch(t=CC, ch=0, c= 6, val=0), camera_exposure_auto),
]
```

Toggle OBS studio scenes when pushing buttons on channel 1, via the
OBS websocket plugin-in.

```python
OBS = obsws("localhost", 4444, "password")
DISPATCHERS = [
    (Dispatch(t=ON, ch=1, b= 1), partial(obs_switch, scene='Title card')),
    (Dispatch(t=ON, ch=1, b= 5), partial(obs_switch, scene='Gallery')),
]
```


## OS packages
* xdotool
* v4l2-utils


## Status

Alpha, active development.  But works and somewhat stable.
