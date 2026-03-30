# `post_process_videos.py` Usage Guide

This script post-processes a dual-camera recording folder by reading:

- `cam0.mp4`
- `cam1.mp4`

…and producing either:

- a **merged** “both cameras” video (stacked or side-by-side), or
- a **preview** snapshot image, or
- a **sync analysis** report, or
- an interactive **manual sync + cropping GUI** (optional).

---

## Requirements

- **Python 3.9+** (recommended)
- **FFmpeg + FFprobe** available on your `PATH`
  - Verify:

```bash
ffmpeg -version
ffprobe -version
```

- **Python packages** used by the script:

```bash
python -m pip install opencv-python pillow
```

Notes:
- `tkinter` is used for the GUI and is usually included with standard Python installations on Windows. If the GUI fails to launch due to `tkinter` missing, reinstall Python with Tcl/Tk enabled.

---

## Quick start (Windows PowerShell)

From the repo root:

```powershell
cd .\dual_camera\pc

# Basic merge (default vertical: cam0 on top, cam1 on bottom)
python .\post_process_videos.py "C:\path\to\record_2026-03-30_12-34-56"
```

This expects the folder to contain `cam0.mp4` and `cam1.mp4`.

---

## CLI: Common commands

### Create merged output video

- **Vertical** (default): cam0 on top, cam1 on bottom

```powershell
python .\post_process_videos.py "C:\path\to\record_..." --layout vertical
```

- **Horizontal**: side-by-side

```powershell
python .\post_process_videos.py "C:\path\to\record_..." --layout horizontal
```

By default, the output filename is auto-generated inside the recording folder, e.g.:
`<folder>_concatenated_fast_<layout>.mp4` (with suffixes for rotation/sync/crop when enabled).

### Write to an explicit output path

```powershell
python .\post_process_videos.py "C:\path\to\record_..." --output "C:\path\to\output\merged.mp4"
```

### Preview snapshot (JPG) instead of full video

```powershell
python .\post_process_videos.py "C:\path\to\record_..." --preview --layout horizontal
```

### Analyze synchronization only (no output video)

```powershell
python .\post_process_videos.py "C:\path\to\record_..." --analyze-sync
```

This prints frame counts, FPS, durations, and highlights mismatches.

### Force frame synchronization by trimming

If the two recordings differ slightly in frame count/duration, you can trim both to match:

```powershell
python .\post_process_videos.py "C:\path\to\record_..." --force-sync
```

Optionally choose an explicit frame count:

```powershell
python .\post_process_videos.py "C:\path\to\record_..." --force-sync --target-frames 12000
```

### Rotate either camera before merging

Allowed values: `0`, `90`, `180`, `270` (degrees)

```powershell
python .\post_process_videos.py "C:\path\to\record_..." --cam0-rotation 90 --cam1-rotation 0
```

### Crop each camera (rectangular crop)

Cropping is specified as **ratios** of the (optionally rotated) frame:

- `--cam*-crop-width`: \(0.1\) to \(1.0\)
- `--cam*-crop-height`: \(0.1\) to \(1.0\)
- `--cam*-crop-x`: \(0.0\) to \(0.9\) (offset ratio)
- `--cam*-crop-y`: \(0.0\) to \(0.9\) (offset ratio)

Example: keep the center 80% width x 80% height for both cams:

```powershell
python .\post_process_videos.py "C:\path\to\record_..." `
  --cam0-crop-width 0.8 --cam0-crop-height 0.8 --cam0-crop-x 0.1 --cam0-crop-y 0.1 `
  --cam1-crop-width 0.8 --cam1-crop-height 0.8 --cam1-crop-x 0.1 --cam1-crop-y 0.1 `
  --layout horizontal
```

Important:
- For `--layout horizontal` (hstack), both cropped videos should end up the **same height**.
- For `--layout vertical` (vstack), both cropped videos should end up the **same width**.

### “Super fast” mode

```powershell
python .\post_process_videos.py "C:\path\to\record_..." --super-fast
```

This uses a separate “maximum speed” path (implementation depends on your FFmpeg build and hardware).

### List recording folders

```powershell
python .\post_process_videos.py "C:\path\to\captures\record_..." --list-folders
```

Note:
- This command lists `record_*` folders in the **parent** directory of the folder you pass.
  - Example: passing `C:\captures\record_0001` will list under `C:\captures\`.

---

## Manual sync + cropping GUI

Launch the interactive GUI:

```powershell
python .\post_process_videos.py --gui
```

In the GUI you can:
- select a folder containing `cam0.mp4` / `cam1.mp4`
- preview frames for each camera with rotation
- manually align start frames
- set a final duration and generate trimmed videos
- configure and preview rectangular cropping
- generate a final merged output video

---

## Troubleshooting

### “ffmpeg not found” / “ffprobe not found”

- Install FFmpeg and ensure both `ffmpeg` and `ffprobe` are on your `PATH`.
- Reopen your terminal after installing so the updated `PATH` is picked up.

### OpenCV import error (`No module named cv2`)

```powershell
python -m pip install opencv-python
```

### PIL import error (`No module named PIL`)

```powershell
python -m pip install pillow
```

### GUI won’t start (tkinter missing)

- Reinstall Python from `python.org` and ensure “tcl/tk and IDLE” (Tkinter) is included.

