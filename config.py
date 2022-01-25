# Inputs
mic = Selector(t='source', name='input.*USB_Advanced')
camera = Selector(t='source', name='input.*C922')
headset_mic = Selector(t='source', name='input.*HyperX')
mic_all = mic._replace(it='*')
camera_all = camera._replace(it='*')
headset_mic_all = headset_mic._replace(it='*')
# Outputs
hdmi = Selector(t='sink', name='hdmi')
hdmi_all = Selector(t='sink', name='hdmi', it='*')
headphones = Selector(t='sink', name='HyperX')
headphones_all = Selector(t='sink', name='HyperX', it='*')

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

# Program dispatches here.
DISPATCHERS = [
    # Moving audio between devices
    (Dispatch(t=CC, c=105), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=hdmi)),
    (Dispatch(t=CC, c=105), partial(call, cmd="pactl set-card-profile alsa_card.pci-0000_06_00.1 output:hdmi-stereo-extra3")),
    (Dispatch(t=CC, c=106), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=headphones)),
    (Dispatch(t=CC, c=101), partial(pulse_move, sel=Selector(t='source', it='*'), move_to=camera)),
    (Dispatch(t=CC, c=102), partial(pulse_move, sel=Selector(t='source', it='*'), move_to=headset_mic)),
    (Dispatch(t=CC, c=103), partial(pulse_move, sel=Selector(t='source', it='*'), move_to=mic)),

    # Microphones
    # toggle:
    #(Dispatch(t=ON, ch=0, n=43), partial(mute, sel=mic_all)),
    #(Dispatch(t=ON, ch=0, b=4), partial(mute, sel=mic_all, state=False)),
    #(Dispatch(t=OFF,ch=0, b=4), partial(mute, sel=mic_all, state=True)),
    # PTT:
    #(Dispatch(t=ON, ch=0, b=3), partial(mute, sel=mic_all, state=False)),
    #(Dispatch(t=OFF,ch=0, b=3), partial(mute, sel=mic_all, state=True)),
    # volume:
    (Dispatch(t=CC,ch=Not(2), c= 5), partial(volume, sel=mic_all)),

    # Zoom microphone mute toggle
    (Dispatch(t=ON, ch=In(0,2), b=4), partial(zoom_mute, ignore_fast=70)),
    (Dispatch(t=ON, ch=0, b=4), partial(teams_mute)),
    (Dispatch(t=OFF,ch=0, b=4), partial(zoom_mute)),
    (Dispatch(t=OFF,ch=0, b=4), partial(teams_mute)),
    # PTT
    (Dispatch(t=ON, ch=0, b=3), partial(zoom_mute)),
    (Dispatch(t=OFF,ch=0, b=3), partial(zoom_mute)),
    # Zoom video toggle
    (Dispatch(t=OFF,ch=0, b=8), partial(zoom_video)),
    # Zoom raise/lower hand
    (Dispatch(t=OFF,ch=0, b=2), partial(zoom_raisehand)),

    # Volumes, speakers
    (Dispatch(t=ON, ch=0, b= 7), partial(mute, sel=hdmi)),
    (Dispatch(t=CC,       c= 1), partial(volume, sel=hdmi, low=0, high=1)),
    (Dispatch(t=CC,       c= 1), partial(volume, sel=headphones, low=0, high=1)),
    (Dispatch(t=CC, ch=0, c= 2), partial(volume, sel=hdmi_all._replace(last=True), low=0, high=1)),
    #(Dispatch(t=CC, ch=0, c= 3), partial(volume, sel=hdmi_all._replace(last=False), low=0, high=1)),
    #(Dispatch(t=CC,       c= 8), partial(volume, sel=Selector(t='sink', it='Chrome'), low=0, high=.7)),
    #(Dispatch(t=CC,       c= 4), partial(volume, sel=Selector(t='sink', it='ZOOM'), low=0, high=.7)),

    # Moving speakers between sources
    #(Dispatch(t=ON, ch=0, b= 5), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=headphones)),
    #(Dispatch(t=ON, ch=0, b= 6), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=hdmi)),
    #(Dispatch(t=ON, ch=3, b= 1), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=hdmi)),
    #(Dispatch(t=ON, ch=3, b= 5), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=headphones)),
    (Dispatch(t=ON, ch=0, b= 5), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=(headphones, hdmi))),
    (Dispatch(t=ON, ch=3, b= 5), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=(headphones, hdmi))),
    (Dispatch(t=ON, ch=0, b= 5), partial(call, cmd="pactl set-card-profile alsa_card.pci-0000_06_00.1 output:hdmi-stereo-extra3")),

    # Move microphone between sources
    (Dispatch(t=ON, ch=0, b= 1), partial(pulse_move, sel=Selector(t='source', it='*'), move_to=(mic, camera, headset_mic))),

    # Camera exposure
    #(Dispatch(t=ON, ch=0, b= 1), partial(camera_exposure_auto)),
    (Dispatch(t=CC, ch=0, c= 6, val=Not(0)), partial(camera_exposure)),
    (Dispatch(t=CC, ch=0, c= 6, val=0), partial(camera_exposure_auto)),
    (Dispatch(t=CC, ch=0, c= 7), camera_gain),
    (Dispatch(t=CC, ch=0, c= 8), camera_pan),
    (Dispatch(t=CC, ch=0, c= 4), camera_tilt),

    # Camera exposure
    (Dispatch(t=CC, ch=2, c= 5, val=Not(0)), camera_wb_temp),
    (Dispatch(t=CC, ch=2, c= 5, val=0), camera_wb_auto),
    (Dispatch(t=CC, ch=2, c= 6), camera_brightness),
    (Dispatch(t=CC, ch=2, c= 2), camera_contrast),
    (Dispatch(t=CC, ch=2, c= 7), camera_saturation),
    (Dispatch(t=CC, ch=2, c= 3), camera_sharpness),
    #(Dispatch(t=CC, ch=2, c= 8, val=Not(0)), partial(camera_exposure)),
    #(Dispatch(t=CC, ch=2, c= 8, val=0), partial(camera_exposure_auto)),
    #(Dispatch(t=CC, ch=2, c= 4), camera_gain),
    ]

@rate_limit
def zoom_placement(msg, RLID='zoom_placement'):
    from subprocess import call
    if msg.value < 1:
        call(['xdotool', 'search', '--onlyvisible', '--name', '^Zoom Meeting$', 'windowmove', '4', '867'   , 'windowsize', '1190', '802', ])
        call(['xdotool', 'search', '--onlyvisible', '--name', '^Zoom$',         'windowmove', '4536', '856', 'windowsize', '500', '414',  ])
    elif msg.value < 10:
        call(['xdotool', 'search', '--onlyvisible', '--name', '^Zoom Meeting$', 'windowmove', '1575', '867', 'windowsize', '1190', '802', ])
        #call(['xdotool', 'search', '--onlyvisible', '--name', '^Zoom$',        'windowmove', '4536', '856', 'windowsize', '500', '414',  ])
    elif msg.value < 20:
        call(['xdotool', 'search', '--onlyvisible', '--name', '^Zoom Meeting$', 'windowmove', '4', '867'   , 'windowsize', '1190', '802', ])
        call(['xdotool', 'search', '--onlyvisible', '--name', '^Zoom$',         'windowmove', '4536', '856', 'windowsize', '100%', '100%',  ])


        #call(['xdotool', 'search', '--onlyvisible', '--name', '^Zoom$', 'windowsize', '840', '1080'])
DISPATCHERS.append(
    (Dispatch(t=CC, ch=0, c= 3), partial(zoom_placement)),
)

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


#OBS = obsws("k8.zgib.net", 4445, "the-password")


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
