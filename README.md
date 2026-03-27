# YouTube Retention Player (WIP)

This repo is an **in-progress YouTube video shortening tool**.  
Current behavior: it opens a YouTube video in Firefox, captures and analyzes the retention heatmap region, detects likely high-retention segments, and then auto-seeks/plays those segments in sequence.

## What It Does Today

The main script is `youtube_retention_player.py`.

End-to-end flow:

1. Launches Firefox with Selenium.
2. Optionally installs an adblock add-on (`.xpi`).
3. Opens a YouTube URL.
4. Uses player controls to enable captions, fullscreen, and playback.
5. Temporarily blacks out video pixels (retention graph stays visible) for cleaner screenshot analysis.
6. Takes a screenshot and crops the progress-bar/retention region.
7. Converts the cropped image into a 1D signal and detects top retention runs.
8. Converts detected runs into `(start_seconds, start_percentage, duration_seconds)`.
9. Uses `pyautogui` to click those timestamps on the progress bar and plays each detected segment.

## Current Controls (Automated)

The script sends these YouTube key controls:

- `c` -> Toggle captions on
- `f` -> Toggle fullscreen on
- `k` -> Play/pause (used here to start playback)

The script also uses mouse movement/clicking via `pyautogui`:

- Moves cursor near the bottom of the screen to reveal/engage progress bar UI.
- Clicks calculated X positions on the progress bar to jump to detected segments.
- Moves cursor to `(1, 1)` between interactions to avoid hover interference.

## CLI Usage

Run:

```bash
python youtube_retention_player.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Optional flags:

- `--no-plot`  
  Disables display plots (currently plots are saved to disk by default in this flow).
- `--initial-wait <seconds>`  
  Wait after opening the video (default: `15.0`, currently parsed but not actively used in `prepare_video` logic).
- `--reveal-wait <seconds>`  
  Delay around player-reveal/screenshot actions (default: `3.0`).
- `--adblock-path <path-to-addon.xpi>`  
  Firefox add-on path. If omitted, script tries:
  - `ublock_origin-1.69.0.xpi`
  - `ublock_firefox.xpi`
  from the repo root/script directory.
- `--firefox-binary <path>`  
  Explicit Firefox binary path if not on PATH.

## Files and Outputs

Core files:

- `youtube_retention_player.py` - browser automation + playback driver
- `graph_to_times.py` - image processing + retention run detection

Artifacts written under `screenshots/`:

- `screenshot.png` - full browser screenshot
- `screenshot_cropped.png` - cropped retention/progress region
- `screenshot_cropped_filtered.png` - optional filtered crop output (from helper flow)
- `graph_pixels.png` - raw intensity plot
- `graph.png` - detected retention bars plot

## Detection Logic (Current State)

In `graph_to_times.py`, the current pipeline:

- Keeps mostly grayscale pixels, suppresses bright whites/background noise.
- Optionally removes thin strand noise with morphology.
- Converts cropped image columns to averaged intensity values.
- Smooths and thresholds into a binary retention signal.
- Keeps top `N` longest runs (`top_sequences`, default `9`).
- Maps runs to time ranges using parsed video duration.

Output format:

- `TimeRange = Tuple[int, float, int]`
- `(start_seconds, start_percentage_of_video, duration_seconds)`

## Assumptions and Known Limitations

This is still prototype-level automation and currently assumes:

- YouTube player structure/classes remain stable (`ytp-*` selectors).
- Screen geometry and fullscreen bar placement are close to expected values.
- Progress bar mapping uses a hardcoded ratio tuned for a specific display setup.
- Browser/OS focus is not interrupted while automation runs.
- Cursor movement by the user during run may break timing/targeting.

Other limitations:

- No robust retry/error recovery around DOM timing/state transitions.
- `show_plot` and `--no-plot` are partially wired in current script path.
- `initial_wait_seconds` is exposed but not currently applied in `prepare_video`.
- Detection thresholds are heuristic and may need per-video tuning.

## Safety and Practical Notes

- Do not use keyboard/mouse during an active run unless you expect interference.
- Expect brittle behavior when YouTube UI, resolution, zoom, or window layout changes.
- Keep Firefox and driver compatibility aligned in your environment.

## Roadmap Ideas

Likely next improvements:

- Replace fixed geometry with DOM-derived progress-bar coordinates.
- Use direct JS seek (`video.currentTime = ...`) instead of GUI clicking.
- Add robust waits/assertions per player state.
- Add config file for detection thresholds and per-device profiles.
- Add tests around `graph_to_times` and image pipeline behavior.

---

Status: **WIP prototype** focused on proving the retention-based shortening flow end-to-end. In future, planning to deploy as a browser extension.
