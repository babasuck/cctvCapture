import argparse
import datetime
import os
import time

import cv2
from typing import List
import logging
import logging.config
import m3u8
import requests
import urllib3
from m3u8 import M3U8
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def load_chunks(file: str) -> List:
    with open(file, "r") as f:
        urls = list(map(lambda r: r.replace("\n", ""), f.readlines()))
        parts = list(map(lambda r: r.split("$"), urls))

    def process_part(part):
        if len(part) != 3:
            logging.error(f"Error: Content from {part} is not an m3u8 file")
            return None
        part[1] = load_m3u8(part)
        return part if part[1] is not None else None

    with ThreadPoolExecutor() as executor:
        future_to_part = {executor.submit(process_part, part): part for part in parts}
        processed_parts = []
        for future in as_completed(future_to_part):
            result = future.result()
            if result is not None:
                processed_parts.append(result)

    return processed_parts


def load_m3u8(chunk: List):
    url = chunk[0] + chunk[1]
    try:
        response = requests.get(url, verify=False, timeout=10)
        if response.status_code != 200:
            logging.error(f"Error: Received status code {response.status_code} from {url}")
            return None
        if not response.text.startswith("#EXTM3U"):
            logging.error(f"Error: Content from {url} is not an m3u8 file")
            return None
        playlist = m3u8.load(url, verify_ssl=False)
        logging.debug(f"Successfully loaded playlist from {url}")
        return playlist
    except (ValueError, IOError) as e:
        logging.error(f"Error loading playlist from {url}: {str(e)}")
        return None


def process_playlist(playlist: List, output_dir: str):
    base = playlist[0]
    pl: M3U8 = playlist[1]
    dir_name = playlist[2]

    full_output_dir = os.path.join(output_dir, dir_name)

    if not os.path.exists(full_output_dir):
        os.makedirs(full_output_dir)

    if len(pl.segments) == 0:
        logging.error(f"In playlist {playlist}. Is no segments!")
        return

    last = pl.segments[-1]
    video_url = base + last.uri

    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = f"{full_output_dir}/{dir_name}_{current_time}.jpg"

    save_frame_from_video(video_url, save_path)


def save_frame_from_video(url, save_path, scale_factor=0.5, quality=90):
    cap = cv2.VideoCapture(url)

    if not cap.isOpened():
        logging.error(f"Failed to open video from URL: {url}")
        return

    # Читаем первый кадр
    ret, frame = cap.read()

    if ret:
        # Уменьшаем размер изображения (например, вдвое)
        new_width = int(frame.shape[1] * scale_factor)
        new_height = int(frame.shape[0] * scale_factor)
        resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # Сохраняем изображение с указанием качества
        cv2.imwrite(save_path, resized_frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        logging.debug(f"Frame saved at path: {save_path} with quality={quality} and scale_factor={scale_factor}")
    else:
        logging.error("Failed to read the frame from the video")

    cap.release()


def main(interval: int, output_dir: str):
    while True:
        logger = logging.getLogger()
        start_time = time.time()

        parts = load_chunks("chunks")
        cleaned_parts = list(filter(lambda x: x is not None, parts))

        for part in cleaned_parts:
            process_playlist(part, output_dir)

        execution_time = time.time() - start_time
        logger.debug(f"Execution completed in {execution_time:.2f} seconds")

        logger.debug(f"Waiting for {interval} minutes before the next execution.")
        time.sleep(interval * 60)


if __name__ == "__main__":
    logging.config.fileConfig('logging_config.ini')
    logger = logging.getLogger()

    parser = argparse.ArgumentParser(description="Run the task every n minutes.")
    parser.add_argument(
        "--interval",
        type=int,
        default=20,
        help="Interval in minutes between each execution (default is 20 minutes)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./output",
        help="Directory where images will be saved (default is './output')"
    )

    args = parser.parse_args()

    main(args.interval, args.output_dir)
