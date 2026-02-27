from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import List, Sequence, Tuple

import pyautogui
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver
from graph_to_times import TimeRange, crop_progress_region, graph_to_times, image_to_graph


def setup_driver(adblock_path: Path | None, firefox_binary: Path | None) -> WebDriver:
    options = FirefoxOptions()
    if firefox_binary:
        options.binary_location = str(firefox_binary)
    driver = webdriver.Firefox(options=options)
    if adblock_path:
        resolved = adblock_path.expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"adblock extension not found at {resolved}")
        if resolved.is_dir():
            raise ValueError("Firefox requires a packed XPI for add-ons; provide a .xpi path.")
        driver.install_addon(str(resolved), temporary=True)
        print(f"Adblock: installed Firefox addon from {resolved}")
    else:
        print("Adblock: no addon provided; running without extension.")
    return driver


def prepare_video(
    url: str,
    *,
    adblock_path: str | Path | None = None,
    firefox_binary: str | Path | None = None,
    screenshot_path: str | Path = "screenshots/screenshot.png",
    cropped_path: str | Path = "screenshots/screenshot_cropped.png",
    initial_wait_seconds: float = 0.0,
    reveal_wait_seconds: float = 3.0,
    show_plot: bool = True,
) -> List[TimeRange]:
    adblock = Path(adblock_path) if adblock_path else None
    firefox_bin = Path(firefox_binary) if firefox_binary else None
    if adblock is None:
        script_dir = Path(__file__).resolve().parent
        default_xpi_names = [
            "ublock_origin-1.69.0.xpi",
            "ublock_firefox.xpi",
        ]
        for name in default_xpi_names:
            candidate = script_dir / name
            if candidate.exists():
                adblock = candidate
                print(f"Adblock: auto-selected {candidate}")
                break
    screenshot_file = Path(screenshot_path)
    cropped_file = Path(cropped_path)
    cropped_file.parent.mkdir(parents=True, exist_ok=True)
    driver: WebDriver | None = None
    try:
        driver = setup_driver(adblock, firefox_bin)
        driver.get(url)
        time.sleep(reveal_wait_seconds)

        progress_bar = driver.find_element(By.CLASS_NAME, "ytp-progress-bar")
        progress_bar.click()
        actions = ActionChains(driver)
        actions.send_keys("c").perform()
        actions.reset_actions()
        actions.send_keys("f").perform()
        actions.reset_actions()
        # Start the video
        actions.send_keys("k").perform()
        actions.reset_actions()

        driver.execute_script(
            """
            (function(){
              const id = 'retention-blackout-style';
              if (document.getElementById(id)) return;
              const style = document.createElement('style');
              style.id = id;
              style.textContent = `
                .html5-video-container video,
                video {
                  filter: brightness(0) !important;
                  background: #000 !important;
                }
                .ytp-cued-thumbnail-overlay-image {
                  opacity: 0 !important;
                }
              `;
              document.head.appendChild(style);
            })();
            """
        )
        time.sleep(reveal_wait_seconds)

        screen_width, screen_height = pyautogui.size()
        bar_y = screen_height * (1 - 0.06666)
        pyautogui.moveTo(screen_width / 2, bar_y)

        video_length = driver.find_element(By.CLASS_NAME, "ytp-time-duration").text
        print(f"video length: {video_length}")
        time.sleep(reveal_wait_seconds)
        driver.save_screenshot(str(screenshot_file))
        crop_progress_region(screenshot_file, cropped_file)

        bar_heights = image_to_graph(cropped_file, show_plot=show_plot)
        time_ranges = graph_to_times(video_length, bar_heights)

        driver.execute_script(
            """
            (function(){
              const style = document.getElementById('retention-blackout-style');
              if (style) style.remove();
              const videos = document.querySelectorAll('video');
              videos.forEach(v => { v.style.filter = 'brightness(1)'; v.style.background=''; });
            })();
            """
        )
        pyautogui.moveTo(1, 1)

        player_to_screen_ratio = (2880 - 96) / 2880
        player_bar_width = screen_width * player_to_screen_ratio
        player_bar_offset = (screen_width - player_bar_width) / 2
        for start_seconds, start_percentage, duration in time_ranges:
            start_x = player_bar_offset + (player_bar_width * start_percentage)
            pyautogui.moveTo(start_x, bar_y)
            pyautogui.click()
            print(f"attempted to click time {start_seconds} at location {start_x:.2f}")
            pyautogui.moveTo(1, 1)
            time.sleep(duration + 1)
        return time_ranges
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open a YouTube video, detect key retention segments, and play them.")
    parser.add_argument("url", type=str, help="YouTube video URL")
    parser.add_argument("--no-plot", action="store_true", help="Disable bar detection plot display")
    parser.add_argument("--initial-wait", type=float, default=15.0, help="Seconds to wait after opening video")
    parser.add_argument("--reveal-wait", type=float, default=3.0, help="Seconds to wait before screenshot")
    parser.add_argument(
        "--adblock-path",
        type=str,
        default=None,
        help="Path to Firefox adblock addon (.xpi). If omitted, tries ublock_origin-1.69.0.xpi next to this script.",
    )
    parser.add_argument("--firefox-binary", type=str, default=None, help="Path to Firefox binary if not on PATH.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    ranges = prepare_video(
        args.url,
        adblock_path=args.adblock_path,
        initial_wait_seconds=args.initial_wait,
        reveal_wait_seconds=args.reveal_wait,
        show_plot=not args.no_plot,
    )
    print("time ranges:", ranges)


if __name__ == "__main__":
    main()
