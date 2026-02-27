from __future__ import annotations

from pathlib import Path
from typing import List, Sequence, Tuple

import cv2
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

TimeRange = Tuple[int, float, int]


def filter_top_sequences(values: Sequence[int], top_n: int, min_length: int = 1) -> List[int]:
    start: int | None = None
    sequences: List[Tuple[int, int]] = []
    for idx, value in enumerate(values):
        if value == 1 and start is None:
            start = idx
        elif value == 0 and start is not None:
            if idx - 1 - start + 1 >= min_length:
                sequences.append((start, idx - 1))
            start = None
    if start is not None:
        if len(values) - 1 - start + 1 >= min_length:
            sequences.append((start, len(values) - 1))
    sequences.sort(key=lambda seq: seq[1] - seq[0], reverse=True)
    output = [0] * len(values)
    for seq_start, seq_end in sequences[:top_n]:
        for idx in range(seq_start, seq_end + 1):
            output[idx] = 1
    return output


def image_to_graph(
    image_path: str | Path,
    whiteness_threshold: int = 200,  # ~5% below 255
    bar_threshold: float = 10.0,
    top_sequences: int = 9,
    show_plot: bool = False,
    save_raw_plot_path: str | Path | None = None,
    save_filtered_plot_path: str | Path | None = None,
    grayscale_tolerance: int = 10,
    remove_thin_strands: bool = True,
    smooth_kernel: int = 5,
    percentile_threshold: float = 90.0,
    min_run_length: int = 3,
) -> List[int]:
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    # Zero-out pixels that are not approximately grayscale
    r, g, b = img[:, :, 2], img[:, :, 1], img[:, :, 0]
    gray_mask = (
        (np.abs(r - g) <= grayscale_tolerance)
        & (np.abs(r - b) <= grayscale_tolerance)
        & (np.abs(g - b) <= grayscale_tolerance)
    )
    img[~gray_mask] = [0, 0, 0]
    threshold = np.array([whiteness_threshold, whiteness_threshold, whiteness_threshold], dtype=np.uint8)
    white_mask = (img >= threshold).all(axis=2)
    img[white_mask] = [0, 0, 0]
    # Paint surviving non-black pixels white for clarity before measuring intensities
    non_black_mask = (img > 0).any(axis=2)
    img[non_black_mask] = [255, 255, 255]
    if remove_thin_strands:
        # Remove thin 1px strands fully surrounded by black using morphological opening
        kernel = np.ones((3, 3), np.uint8)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        non_black = (gray > 0).astype(np.uint8)
        opened = cv2.morphologyEx(non_black, cv2.MORPH_OPEN, kernel)
        strand_mask = (non_black == 1) & (opened == 0)
        img[strand_mask] = [0, 0, 0]
    avg_pixel_values = np.mean(img, axis=0)
    avg_pixel_values = np.mean(avg_pixel_values[:, :2], axis=1)
    raw_series = avg_pixel_values.copy()
    if smooth_kernel > 1:
        kernel = np.ones(smooth_kernel) / smooth_kernel
        smoothed = np.convolve(raw_series, kernel, mode="same")
    else:
        smoothed = raw_series
    smoothed = np.where(smoothed < bar_threshold, 0, smoothed)
    positives = smoothed[smoothed > 0]
    if positives.size > 0:
        threshold_val = max(bar_threshold, np.percentile(positives, percentile_threshold))
    else:
        threshold_val = bar_threshold
    binary_series = [1 if value >= threshold_val else 0 for value in smoothed.tolist()]
    filtered = filter_top_sequences(binary_series, top_sequences, min_length=min_run_length)

    if show_plot or save_raw_plot_path:
        plt.figure(figsize=(20, 4))
        plt.plot(raw_series, linewidth=0.8)
        plt.title("Raw pixel intensities")
        if save_raw_plot_path:
            Path(save_raw_plot_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_raw_plot_path, bbox_inches="tight")
        if show_plot:
            plt.show()
        plt.close()

    if show_plot or save_filtered_plot_path:
        plt.figure(figsize=(20, 4))
        plt.bar(range(len(filtered)), filtered)
        plt.title("Detected retention bars")
        if save_filtered_plot_path:
            Path(save_filtered_plot_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_filtered_plot_path, bbox_inches="tight")
        if show_plot:
            plt.show()
        plt.close()
    return filtered


def parse_time_to_seconds(time_text: str) -> int:
    parts = [int(part) for part in time_text.strip().split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    raise ValueError(f"Unsupported time format: {time_text}")


def graph_to_times(total_time: str, bar_graph: Sequence[int]) -> List[TimeRange]:
    if not bar_graph:
        return []
    total_seconds = parse_time_to_seconds(total_time)
    step = total_seconds / len(bar_graph)
    time_ranges: List[TimeRange] = []
    start_time: float | None = None
    end_time: float | None = None
    for idx, is_bar in enumerate(bar_graph):
        current_time = idx * step
        if is_bar:
            if start_time is None:
                start_time = current_time
            end_time = current_time
            continue
        if start_time is not None and end_time is not None:
            duration = int(end_time) - int(start_time)
            time_ranges.append((int(start_time), int(start_time) / total_seconds, max(duration, 1)))
            start_time = None
            end_time = None
    if start_time is not None and end_time is not None:
        duration = int(end_time) - int(start_time)
        time_ranges.append((int(start_time), int(start_time) / total_seconds, max(duration, 1)))
    return time_ranges


def crop_progress_region(
    screenshot_path: Path,
    output_path: Path,
    left_offset: int = 48,
    top: int = 1400,
    bottom_offset: int = 125,
    filtered_output_path: Path | None = None,
    whiteness_threshold: int = 200,
    half_height: bool = False,
    grayscale_tolerance: int = 10,
    remove_thin_strands: bool = True,
    fixed_height: int | None = 150,
) -> None:
    with Image.open(screenshot_path) as img:
        width, height = img.size
        right = width - left_offset
        bottom = height - (bottom_offset + 20)  # raise bottom by additional 10px
        if fixed_height is not None:
            new_top = max(0, int(bottom - fixed_height))
        else:
            new_top = top
            current_height = bottom - top
            if half_height:
                new_height = current_height / 2
                new_top = max(0, int(bottom - new_height))
        cropped = img.crop((left_offset, new_top, right, bottom))
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cropped.save(output_path)

        if filtered_output_path:
            cropped_cv = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
            # Zero-out non-grayscale pixels for consistency with image_to_graph
            r, g, b = cropped_cv[:, :, 2], cropped_cv[:, :, 1], cropped_cv[:, :, 0]
            gray_mask = (
                (np.abs(r - g) <= grayscale_tolerance)
                & (np.abs(r - b) <= grayscale_tolerance)
                & (np.abs(g - b) <= grayscale_tolerance)
            )
            cropped_cv[~gray_mask] = [0, 0, 0]
            threshold = np.array([whiteness_threshold, whiteness_threshold, whiteness_threshold], dtype=np.uint8)
            white_mask = (cropped_cv >= threshold).all(axis=2)
            cropped_cv[white_mask] = [0, 0, 0]
            if remove_thin_strands:
                kernel = np.ones((3, 3), np.uint8)
                gray = cv2.cvtColor(cropped_cv, cv2.COLOR_BGR2GRAY)
                non_black = (gray > 0).astype(np.uint8)
                opened = cv2.morphologyEx(non_black, cv2.MORPH_OPEN, kernel)
                strand_mask = (non_black == 1) & (opened == 0)
                cropped_cv[strand_mask] = [0, 0, 0]
            # Paint surviving non-black pixels white for clarity
            non_black_mask = (cropped_cv > 0).any(axis=2)
            cropped_cv[non_black_mask] = [255, 255, 255]
            Path(filtered_output_path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(filtered_output_path), cropped_cv)


def run_on_screenshot(
    screenshot_path: Path = Path("screenshots/screenshot.png"),
    cropped_path: Path = Path("screenshots/screenshot_cropped.png"),
    filtered_cropped_path: Path = Path("screenshots/screenshot_cropped_filtered.png"),
    raw_plot_path: Path = Path("screenshots/graph_pixels.png"),
    filtered_plot_path: Path = Path("screenshots/graph.png"),
    whiteness_threshold: int = 200,
    bar_threshold: float = 10.0,
    top_sequences: int = 9,
    half_height: bool = False,
    grayscale_tolerance: int = 10,
    remove_thin_strands: bool = True,
    fixed_height: int | None = 150,
    smooth_kernel: int = 5,
    percentile_threshold: float = 90.0,
    min_run_length: int = 3,
) -> List[int]:
    crop_progress_region(
        screenshot_path,
        cropped_path,
        filtered_output_path=filtered_cropped_path,
        whiteness_threshold=whiteness_threshold,
        half_height=half_height,
        grayscale_tolerance=grayscale_tolerance,
        fixed_height=fixed_height,
    )
    bars = image_to_graph(
        cropped_path,
        whiteness_threshold=whiteness_threshold,
        bar_threshold=bar_threshold,
        top_sequences=top_sequences,
        show_plot=False,
        save_raw_plot_path=raw_plot_path,
        save_filtered_plot_path=filtered_plot_path,
        grayscale_tolerance=grayscale_tolerance,
        remove_thin_strands=remove_thin_strands,
        smooth_kernel=smooth_kernel,
        percentile_threshold=percentile_threshold,
        min_run_length=min_run_length,
    )
    return bars


if __name__ == "__main__":
    bars = run_on_screenshot()
    print("Detected bars:", bars)
