# This file gets exec():ed by the main script, so not all names are defined here.

# Since buttons can have different MIDI note events on different channels, this
# serves as a map between physical button number and note event, per-channel.
# I could also re-program the MIDI device, but I don't want to do that just
# yet.
BUTTONMAP = {
    # channel: [note_for_button_id]
    0: [None, 36, 37, 38, 39, 40, 41, 42, 43],
    1: [None, 35, 36, 42, 39, 37, 38, 46, 44],
    2: [None, 60, 62, 64, 65, 67, 69, 71, 72],
    3: [None, 36, 38, 40, 41, 43, 45, 47, 48],
    }



#OBS = obsws("k8.zgib.net", 4445, "the-password")

# Five main scenes
TITLE = 'Title'
GALLERY = 'Gallery'
LSCREEN = 'Local'
RSCREEN = 'Remote'
NOTES = 'Notes'
# The "picture in picture" camera insert into the other scenes
PIP = '_Camera'
# Names of the audio devices
OBS_AUDIO_DESKTOP = 'A_Desktop_Capture'
OBS_AUDIO_MIC = 'Mic'




DISPATCHERS +=[
    # OBS
    # Standard scene/source names:
    #   - Title
    #     - Clock (text that contains ([xX?]{2}:)(\d{2})(\s+|$)    )
    #   - Gallery
    #   - Local
    #     - Camera (source, capture of camera)
    #   - Remote
    #   - Notes

    # Scene switching
    (Dispatch(t=ON, ch=1, b= 1), partial(obs_switch, scene=TITLE)),
    (Dispatch(t=ON, ch=1, b= 5), partial(obs_switch, scene=GALLERY)),
    (Dispatch(t=ON, ch=1, b= 2), partial(obs_switch, scene=LSCREEN)),
    (Dispatch(t=ON, ch=1, b= 6), partial(obs_switch, scene=RSCREEN)),
    (Dispatch(t=ON, ch=1, b= 3), partial(obs_switch, scene=NOTES)),

    # Mute toggle
    (Dispatch(      ch=1, b= 4), partial(obs_mute, source=[OBS_AUDIO_MIC])),
    #(Dispatch(     ch=1, b= 4), partial(zoom_mute, ignore_fast=70)),
    (Dispatch(      ch=1, b= 8), partial(obs_mute, source=[OBS_AUDIO_DESKTOP])),

    # Misc functions
    (Dispatch(t=ON, ch=1, b= 7), partial(obs_recording_time_copy)),
    #(Dispatch(t=ON, ch=1, b= 2), partial(obs_scene_item_visible, item=['HackMD capture'])),

    # Controls
    # clock
    (Dispatch(t=CC, ch=1, c= 5), partial(rate_limit(rate=.1)(obs_text_clock), source='Clock')),
    # camera_exposure
    (Dispatch(t=CC, ch=1, c= 6, val=Not(0)), partial(camera_exposure)),
    (Dispatch(t=CC, ch=1, c= 6, val=0), partial(camera_exposure_auto)),
    #(Dispatch(t=CC, ch=1, c= 7), camera_gain),

    # PIP size
    (Dispatch(t=CC, ch=1, c= 3), partial(obs_scale_source, scene=(LSCREEN, RSCREEN, NOTES),  source=PIP, high=1)),

    (Dispatch(t=CC, ch=1, c= 7), partial(obs_set_crop, scene=(LSCREEN, RSCREEN, NOTES, GALLERY),  source=PIP)),
    (Dispatch(t=CC, ch=1, c= 8), camera_pan),
    (Dispatch(t=CC, ch=1, c= 4), camera_tilt),
    #(Dispatch(t=CC, ch=1, c= 8), partial(obs_scale_source, scene='Remote', source='Camera2')),
]
