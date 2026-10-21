"""Compose the usage video: intro.mp4 + recorded demo + outro.mp4 (ffmpeg, no grain/noise/blur/denoise filters).

Usage (repository root): .venv/Scripts/python.exe scripts/demo-video/compose.py
Reads recordings/timeline.json and recordings/frames/ (screencast frames from record.mjs, scaled down with lanczos) and the newest incoming/video_kit*/ folder.
Writes recordings/final/HeatTime_활용영상.mp4 (1920x1080 30fps H.264 CRF 20, AAC 192k, faststart)
and HeatTime_활용영상_720p.mp4. The music bed plays only under the demo part at -9 dB with 1.5 s fades;
a 20 ms 2400 Hz click made with aevalsrc marks the reschedule and approval clicks (no downloaded sounds).
"""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT/'recordings'
FINAL = REC/'final'
XF = 0.5


def kit():
    found = sorted((ROOT/'incoming').glob('video_kit*'), key=lambda p: p.stat().st_mtime, reverse=True)
    for folder in found:
        if all((folder/n).exists() for n in ('intro.mp4', 'outro.mp4', 'demo_bed.m4a')):
            return folder
    raise SystemExit('incoming/video_kit/에 intro.mp4, outro.mp4, demo_bed.m4a가 없습니다.')


def duration(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                         check=True, capture_output=True, text=True).stdout
    return float(out.strip())


def ff(args):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *args], check=True)


def main():
    t = json.loads((REC/'timeline.json').read_text(encoding='utf-8'))
    ev = {e['kind']: e['t'] for e in t['events'] if e['kind'] in ('demo-start', 'demo-end')}
    start, stop = ev['demo-start'], ev['demo-end']; length = stop - start
    clicks = [e['t'] - start for e in t['events'] if e['kind'] == 'click']
    k = kit(); FINAL.mkdir(parents=True, exist_ok=True)
    # Screencast frames (3840x2160, only when the page changes) -> constant 30 fps via the concat demuxer.
    frames = t['frames']; first = max(i for i, f in enumerate(frames) if f['t'] <= start)
    shown = [f for f in frames[first:] if f['t'] < stop]
    lines = ['ffconcat version 1.0']
    for i, f in enumerate(shown):
        begin = max(f['t'], start); finish = shown[i+1]['t'] if i+1 < len(shown) else stop
        lines += [f"file '{(Path(t['frames_dir'])/f['file']).as_posix()}'", f'duration {finish - begin:.6f}']
    lines.append(f"file '{(Path(t['frames_dir'])/shown[-1]['file']).as_posix()}'")
    listing = REC/'frames.ffconcat'; listing.write_text(chr(10).join(lines) + chr(10), encoding='utf-8')
    demo = REC/'demo-30fps.mp4'
    bed = f"[1:a]atrim=0:{length:.3f},volume=-9dB,afade=t=in:d=1.5,afade=t=out:st={length - 1.5:.3f}:d=1.5,aformat=sample_rates=48000:channel_layouts=stereo[bed]"
    parts = [bed]; labels = ['[bed]']
    for i, c in enumerate(clicks):
        ms = int(round(c*1000))
        parts.append(f"aevalsrc='0.6*sin(2*PI*2400*t)':s=48000:d=0.02,aformat=sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms},apad=whole_dur={length:.3f}[c{i}]")
        labels.append(f'[c{i}]')
    mix = ''.join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=first[a]"
    ff(['-f', 'concat', '-safe', '0', '-i', str(listing), '-i', str(k/'demo_bed.m4a'),
        '-filter_complex', ';'.join([f"[0:v]scale=1920:1080:flags=lanczos,fps=30,trim=0:{length:.3f},format=yuv420p,setsar=1[v]", *parts, mix]),
        '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-c:a', 'aac', '-b:a', '192k', str(demo)])
    # 2) intro + demo + outro with 0.5 s crossfades (video xfade, audio acrossfade).
    di, dd = duration(k/'intro.mp4'), duration(demo)
    graph = (f"[0:v]fps=30,format=yuv420p,setsar=1[v0];[1:v]fps=30,format=yuv420p,setsar=1[v1];[2:v]fps=30,format=yuv420p,setsar=1[v2];"
             f"[v0][v1]xfade=transition=fade:duration={XF}:offset={di - XF:.3f}[v01];"
             f"[v01][v2]xfade=transition=fade:duration={XF}:offset={di + dd - 2*XF:.3f},format=yuv420p[v];"
             f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo[a0];[1:a]aformat=sample_rates=48000:channel_layouts=stereo[a1];[2:a]aformat=sample_rates=48000:channel_layouts=stereo[a2];"
             f"[a0][a1]acrossfade=d={XF}[a01];[a01][a2]acrossfade=d={XF}[a]")
    full = FINAL/'HeatTime_활용영상.mp4'
    ff(['-i', str(k/'intro.mp4'), '-i', str(demo), '-i', str(k/'outro.mp4'), '-filter_complex', graph, '-map', '[v]', '-map', '[a]',
        '-r', '30', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(full)])
    small = FINAL/'HeatTime_활용영상_720p.mp4'
    ff(['-i', str(full), '-vf', 'scale=1280:720:flags=lanczos', '-r', '30', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(small)])
    info = {p.name: {'seconds': round(duration(p), 2), 'bytes': p.stat().st_size} for p in (full, small)}
    info['parts'] = {'intro': di, 'demo': round(dd, 2), 'outro': duration(k/'outro.mp4'), 'crossfade': XF, 'clicks_at_demo_seconds': clicks, 'kit': k.name}
    (FINAL/'compose.json').write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(info, ensure_ascii=False))


if __name__ == '__main__':
    main()
