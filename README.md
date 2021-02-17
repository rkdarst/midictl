# Act based on MIDI events

Usage: `python midictl.py`.  Note that this opens the raw `/dev/midi*`
device, to avoid having to 

Programming:

The `DISPATCHERS` list is pairs of (dispatch_selector, callback_function)
pairs.  Functions do various things.

`Dispatch` is the dispatch selector, it is a named tuple with
properties `type`, `channel`, `note`, `control` which match with MIDI
events.

Events you can trigger are currently:

* PulseAudio mutes and volume changes. `Selector` is namedtuple which
  can select which pulse devices to operate on,


# Status

Alpha, active development.
