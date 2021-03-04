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
    (Dispatch(t=ON, ch=0, b=4), partial(zoom_mute, ignore_fast=70)),
    (Dispatch(t=ON, ch=0, b=4), partial(teams_mute)),
    (Dispatch(t=OFF,ch=0, b=4), partial(zoom_mute)),
    (Dispatch(t=OFF,ch=0, b=4), partial(teams_mute)),
    (Dispatch(t=ON, ch=0, b=3), partial(zoom_mute)),
    (Dispatch(t=OFF,ch=0, b=3), partial(zoom_mute)),
    # Zoom video toggle
    (Dispatch(t=OFF,ch=0, b=8), partial(zoom_video)),

    # Volumes, speakers
    (Dispatch(t=ON, ch=0, b= 7), partial(mute, sel=hdmi)),
    (Dispatch(t=CC,       c= 1), partial(volume, sel=hdmi_all, low=0, high=.7)),
    (Dispatch(t=CC,       c= 1), partial(volume, sel=headphones_all, low=0, high=.7)),
    (Dispatch(t=CC, ch=0, c= 2), partial(volume, sel=hdmi_all._replace(last=True), low=0, high=.7)),
    (Dispatch(t=CC, ch=0, c= 3), partial(volume, sel=hdmi_all._replace(last=False), low=0, high=.7)),

    # Moving speakers between sources
    #(Dispatch(t=ON, ch=0, b= 5), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=headphones)),
    #(Dispatch(t=ON, ch=0, b= 6), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=hdmi)),
    #(Dispatch(t=ON, ch=3, b= 1), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=hdmi)),
    #(Dispatch(t=ON, ch=3, b= 5), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=headphones)),
    (Dispatch(t=ON, ch=0, b= 5), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=(hdmi, headphones))),
    (Dispatch(t=ON, ch=3, b= 5), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=(hdmi, headphones))),
    # Move microphone between sources
    (Dispatch(t=ON, ch=0, b= 1), partial(pulse_move, sel=Selector(t='source', it='*'), move_to=(mic, camera, headset_mic))),


    # Camera exposure
    #(Dispatch(t=ON, ch=0, b= 1), partial(camera_exposure_auto)),
    (Dispatch(t=CC, ch=0, c= 6, val=Not(0)), partial(camera_exposure)),
    (Dispatch(t=CC, ch=0, c= 6, val=0), partial(camera_exposure_auto)),
    (Dispatch(t=CC, ch=0, c= 7), camera_gain),

    # Camera exposure
    (Dispatch(t=CC, ch=2, c= 5, val=Not(0)), camera_wb_temp),
    (Dispatch(t=CC, ch=2, c= 5, val=0), camera_wb_auto),
    (Dispatch(t=CC, ch=2, c= 6), camera_brightness),
    (Dispatch(t=CC, ch=2, c= 2), camera_contrast),
    (Dispatch(t=CC, ch=2, c= 7), camera_saturation),
    (Dispatch(t=CC, ch=2, c= 3), camera_sharpness),
    (Dispatch(t=CC, ch=2, c= 8, val=Not(0)), partial(camera_exposure)),
    (Dispatch(t=CC, ch=2, c= 8, val=0), partial(camera_exposure_auto)),
    (Dispatch(t=CC, ch=2, c= 4), camera_gain),
    ]

TITLE = 'Title card'
GALLERY = 'Gallery'
LSCREEN = 'Desktop (local)+camera'
RSCREEN = 'Desktop (remote)+camera'
OBS_MICS = ['A_Desktop Audio', 'Yeti']
PIP = '_Zoom people overlay'

DISPATCHERS +=[
    # OBS
    (Dispatch(t=ON, ch=1, b= 1), partial(obs_switch, scene='Title card')),
    (Dispatch(t=ON, ch=1, b= 5), partial(obs_switch, scene='Gallery')),
    (Dispatch(t=ON, ch=1, b= 2), partial(obs_switch, scene='Desktop (local)+camera')),
    (Dispatch(t=ON, ch=1, b= 6), partial(obs_switch, scene='Desktop (remote)+camera')),
    #(Dispatch(t=CC, ch=1, c= 8), partial(rate_limit(rate=.1)(obs_text_clock), source='Title')),
    (Dispatch(t=ON, ch=1, b= 4), partial(obs_mute, source=['A_Desktop Audio', 'Yeti'])),
    #(Dispatch(t=ON, ch=1, b= 2), partial(obs_scene_item_visible, item=['HackMD capture'])),
    (Dispatch(t=CC, ch=1, c= 6, val=Not(0)), partial(camera_exposure)),
    (Dispatch(t=CC, ch=1, c= 6, val=0), partial(camera_exposure_auto)),
    (Dispatch(t=CC, ch=1, c= 7), camera_gain),
    (Dispatch(t=CC, ch=1, c= 8), partial(obs_scale_source, scene='Desktop (local)+camera', source='_Zoom people overlay')),
    (Dispatch(t=CC, ch=1, c= 8), partial(obs_scale_source, scene='Desktop (remote)+camera', source='_Zoom people overlay')),
]
