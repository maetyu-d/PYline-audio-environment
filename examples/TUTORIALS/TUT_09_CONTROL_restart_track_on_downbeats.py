# Tutorial 09 (CONTROL): restarting another track on downbeats.
#
# Put this clip on a CONTROL track. It emits restart events that can drive other tracks.
#
# Params:
# - track: target track name (default "Track 2")
# - every_beats: restart every N beats (default 4 = downbeat)
# - from: track-local restart point (seconds, default 0.0)
# - hard: True/False (default False)
# - tail: tail seconds for soft restart
#
# Event schema example:
# {"type":"restart_track","track":"Track 2","at":0.0,"from":0.0,"hard":False,"tail":0.75}

def events(sr, duration, t0, params=None):
    params = params or {}
    bpm = float(params.get("bpm", 120.0))
    try:
        bpm = float(CLIP_BPM)
    except Exception:
        pass
    bpm = max(1.0, bpm)

    target = params.get("track", "Track 2")
    every_beats = max(1, int(params.get("every_beats", 4)))
    from_local = float(params.get("from", 0.0))
    hard = bool(params.get("hard", False))
    tail = float(params.get("tail", 0.75))

    spb = 60.0 / bpm
    t = 0.0
    k = 0
    evs = []
    while t <= duration + 1e-9:
        if (k % every_beats) == 0:
            evs.append({
                "type":"restart_track",
                "track": target,
                "at": t,
                "from": from_local,
                "hard": hard,
                "tail": tail
            })
        k += 1
        t += spb
    return evs
