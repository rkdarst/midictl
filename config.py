# Inputs
mic = Selector(t='source', name='input.*USB_Advanced')
camera = Selector(t='source', name='input.*C922')
headset_mic = Selector(t='source', name='input.*HyperX')
mic_items = mic._replace(it='*')
camera_items = camera._replace(it='*')
headset_mic_items = headset_mic._replace(it='*')
# Outputs
hdmi     = Selector(t='sink',   name='hdmi', name_not='monitor')
hdmi_items = Selector(t='sink', name='hdmi', name_not='monitor', it='*')
headphones       = Selector(t='sink', name='HyperX', name_not='monitor')
headphones_items = Selector(t='sink', name='HyperX', name_not='monitor', it='*')
# Monitors of these:
hdmi_mon       = Selector(t='source',   name='hdmi.*monitor')
hdmi_mon_items = Selector(t='source', name='hdmi.*monitor', it='*')
headphones_mon       = Selector(t='source', name='HyperX.*monitor')
headphones_mon_items = Selector(t='source', name='HyperX.*monitor', it='*')



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
    # Moving audio between devices: speakers
    (Dispatch(t=CC, c=105), partial(pulse_move, sel=Selector(t='sink',                   it='*'),     move_to=hdmi)),
    (Dispatch(t=CC, c=105), partial(pulse_move, sel=Selector(t='source', name='monitor', it='OBS'),   move_to=hdmi_mon)),
    (Dispatch(t=CC, c=105), partial(call, cmd="pactl set-card-profile alsa_card.pci-0000_06_00.1 output:hdmi-stereo-extra5")),  # 2023: R monitor
    (Dispatch(t=CC, c=107), partial(call, cmd="pactl set-card-profile alsa_card.pci-0000_06_00.1 output:hdmi-stereo-extra4")),  # 2023: vr
    (Dispatch(t=CC, c=106), partial(pulse_move, sel=Selector(t='sink',                   it='*'),     move_to=headphones)),
    (Dispatch(t=CC, c=106), partial(pulse_move, sel=Selector(t='source', name='monitor', it='OBS'),   move_to=headphones_mon)),

    # Moving audio between devices: microphones
    (Dispatch(t=CC, c=101), partial(pulse_move, sel=Selector(t='source', it='*', name_not='monitor'), move_to=camera)),
    (Dispatch(t=CC, c=102), partial(pulse_move, sel=Selector(t='source', it='*', name_not='monitor'), move_to=headset_mic)),
    (Dispatch(t=CC, c=103), partial(pulse_move, sel=Selector(t='source', it='*', name_not='monitor'), move_to=mic)),

    # Microphones
    # toggle:
    #(Dispatch(t=ON, ch=0, n=43), partial(mute, sel=mic_items)),
    #(Dispatch(t=ON, ch=0, b=4), partial(mute, sel=mic_items, state=False)),
    #(Dispatch(t=OFF,ch=0, b=4), partial(mute, sel=mic_items, state=True)),
    # PTT:
    #(Dispatch(t=ON, ch=0, b=3), partial(mute, sel=mic_items, state=False)),
    #(Dispatch(t=OFF,ch=0, b=3), partial(mute, sel=mic_items, state=True)),
    # volume:
    (Dispatch(t=CC,ch=Not(2), c= 5), partial(volume, sel=mic_items)),

    # Microphone mute toggle
    (Dispatch(t=ON, ch=In(0,2), b=4), partial(zoom_mute, ignore_fast=100)),
    (Dispatch(t=ON, ch=0, b=4), partial(teams_mute)),
    (Dispatch(t=OFF,ch=0, b=4), partial(zoom_mute)),
    (Dispatch(t=OFF,ch=0, b=4), partial(teams_mute)),
    (Dispatch(t=CC, c=104),     partial(zoom_mute)),
    # PTT
    (Dispatch(t=ON, ch=0, b=3), partial(zoom_mute)),
    (Dispatch(t=OFF,ch=0, b=3), partial(zoom_mute)),
    # Video toggle
    (Dispatch(t=OFF,ch=0, b=8), partial(zoom_video)),
    (Dispatch(t=OFF,ch=0, b=8), partial(teams_video)),
    (Dispatch(t=CC, c=108),     partial(zoom_video)),
    (Dispatch(t=CC, c=108),     partial(teams_video)),
    # Raise/lower hand
    (Dispatch(t=OFF,ch=0, b=2), partial(zoom_raisehand)),
    (Dispatch(t=OFF,ch=0, b=2), partial(teams_raisehand)),

    # Volumes, speakers
    (Dispatch(t=ON, ch=0, b= 7), partial(mute, sel=hdmi)),
    (Dispatch(t=CC,       c= 1), partial(volume, sel=hdmi, low=0, high=1)),
    (Dispatch(t=CC,       c= 1), partial(volume, sel=headphones, low=0, high=1)),
    (Dispatch(t=CC, ch=0, c= 2), partial(volume, sel=hdmi_items._replace(last=True), low=0, high=1)),
    #(Dispatch(t=CC, ch=0, c= 3), partial(volume, sel=hdmi_items._replace(last=False), low=0, high=1)),
    #(Dispatch(t=CC,       c= 8), partial(volume, sel=Selector(t='sink', it='Chrome'), low=0, high=.7)),
    #(Dispatch(t=CC,       c= 4), partial(volume, sel=Selector(t='sink', it='ZOOM'), low=0, high=.7)),

    # Moving speakers between sources
    #(Dispatch(t=ON, ch=0, b= 5), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=headphones)),
    #(Dispatch(t=ON, ch=0, b= 6), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=hdmi)),
    #(Dispatch(t=ON, ch=3, b= 1), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=hdmi)),
    #(Dispatch(t=ON, ch=3, b= 5), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=headphones)),
    #(Dispatch(t=ON, ch=0, b= 5), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=(headphones, hdmi))),
    #(Dispatch(t=ON, ch=3, b= 5), partial(pulse_move, sel=Selector(t='sink', it='*'), move_to=(headphones, hdmi))),
    #(Dispatch(t=ON, ch=0, b= 5), partial(call, cmd="pactl set-card-profile alsa_card.pci-0000_06_00.1 output:hdmi-stereo-extra3")),

    # Move microphone between sources
    #(Dispatch(t=ON, ch=0, b= 1), partial(pulse_move, sel=Selector(t='source', it='*'), move_to=(mic, camera, headset_mic))),

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

@rate_limit(0.25)
def zoom_placement(msg, RLID='zoom_placement'):
    from subprocess import call
    if msg.value < 1:
        call(['xdotool', 'search', '--onlyvisible', '--name', 'Zoom Meeting$', 'windowmove', '4', '1025'   , 'windowsize', '1190', '802', ])
        call(['xdotool', 'search', '--onlyvisible', '--name', '^Zoom$',         'windowmove', '4536', '856', 'windowsize', '500', '414',  ])
    elif msg.value < 10:
        call(['xdotool', 'search', '--onlyvisible', '--name', 'Zoom Meeting$', 'windowmove', '1575', '867', 'windowsize', '1190', '802', ])
        call(['xdotool', 'search', '--onlyvisible', '--name', '^Zoom$',         'windowmove', '4536', '856', 'windowsize', '500', '414',  ])
    elif msg.value < 35:
        call(['xdotool', 'search', '--onlyvisible', '--name', 'Zoom Meeting$', 'windowmove', '4', '1025'   , 'windowsize', '1190', '802', ])
        call(['xdotool', 'search', '--onlyvisible', '--name', '^Zoom$',         'windowmove', '3120', '840', 'windowsize', '1920', '1080',  ])
    elif msg.value < 64:
        call(['xdotool', 'search', '--onlyvisible', '--name', 'Zoom Meeting$', 'windowmove', '1575', '867', 'windowsize', '1190', '802', ])
        call(['xdotool', 'search', '--onlyvisible', '--name', '^Zoom$',         'windowmove', '3120', '840', 'windowsize', '1920', '1080',  ])


        #call(['xdotool', 'search', '--onlyvisible', '--name', '^Zoom$', 'windowsize', '840', '1080'])
DISPATCHERS.append(
    (Dispatch(t=CC, ch=0, c= 3), partial(zoom_placement)),
)



# Five main scenes
OBS = obsws("k8.zgib.net", 4445, "Vae9kaiM*ai2eothie9u")
TITLE = 'Title'
GALLERY = 'Gallery'
LSCREEN = 'Broadcaster-Screen'
RSCREEN = 'Screenshare'
NOTES = 'Notes'
RSCREENLANDSCAPE = 'ScreenshareLandscape'
SCENES_WITH_PIP = (RSCREEN, 'ScreenshareCrop', RSCREENLANDSCAPE, LSCREEN, NOTES)
# The "picture in picture" camera insert into the other scenes
PIP = '_GalleryCapture[hidden]'
# Names of the audio devices
OBS_AUDIO_DESKTOP = 'Instructors'
OBS_AUDIO_MIC = 'BroadcasterMic'



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
    (Dispatch(      ch=1, b= 1), delay( 0, .5)(partial(obs_switch, scene=NOTES))),
    (Dispatch(      ch=1, b= 1), delay(.5, 10)(partial(obs_switch, scene=TITLE))),
    (Dispatch(t=ON, ch=1, b= 5), partial(obs_switch, scene=GALLERY)),
    (Dispatch(t=ON, ch=1, b= 2), partial(obs_switch, scene=LSCREEN)),
    (Dispatch(      ch=1, b= 6), delay( 0, .5)(partial(obs_switch, scene=RSCREEN))),
    (Dispatch(      ch=1, b= 6), delay(.5, 10)(partial(obs_switch, scene=RSCREENLANDSCAPE))),
    #(Dispatch(t=ON, ch=1, b= 3), partial(obs_switch, scene=NOTES)),

    # OBS Mute toggle
    (Dispatch(      ch=1, b= 3), partial(obs_mute, source=[OBS_AUDIO_MIC])),
    (Dispatch(      ch=1, b= 7), partial(obs_mute, source=[OBS_AUDIO_DESKTOP])),

    # Zoom audio/video toggle
    (Dispatch(      ch=1, b= 4), partial(zoom_mute)),
    (Dispatch(      ch=1, b= 8), partial(zoom_video)),

    # Misc functions
    #(Dispatch(t=ON, ch=1, b= 7), partial(obs_recording_time_copy)),
    #(Dispatch(t=ON, ch=1, b= 2), partial(obs_scene_item_visible, item=['HackMD capture'])),
    (Dispatch(t=CC, ch=1, c= 2), mpv_speed_control),

    # Controls
    # clock
    #(Dispatch(t=CC, ch=1, c= 5), partial(rate_limit(rate=.1)(obs_text_clock), source='Clock')),
    # camera_exposure
    (Dispatch(t=CC, ch=1, c= 6, val=Not(0)), partial(camera_exposure, high=200)),
    (Dispatch(t=CC, ch=1, c= 6, val=0), partial(camera_exposure_auto)),
    (Dispatch(t=CC, ch=1, c= 6), partial(camera_gain, low=64)),

    # PIP size
    (Dispatch(t=CC, ch=1, c= 7), partial(obs_scale_source, scene=SCENES_WITH_PIP,  source=PIP, high=1)),

    (Dispatch(t=CC, ch=1, c= 3), partial(obs_set_crop, scene=SCENES_WITH_PIP + (GALLERY,),  source=PIP)),
    (Dispatch(t=CC, ch=1, c= 8), camera_pan),
    (Dispatch(t=CC, ch=1, c= 4), camera_tilt),
    #(Dispatch(t=CC, ch=1, c= 8), partial(obs_scale_source, scene='Remote', source='Camera2')),
]
