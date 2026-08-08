import shutil
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
import time
import yt_dlp


def get_download_dir() -> Path:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()
    download_dir = filedialog.askdirectory(title="Select download folder")
    root.destroy()

    if not download_dir:
        download_dir = "downloads"

    path = Path(download_dir).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


DOWNLOAD_DIR = Path("downloads").resolve()

# Set this to "chrome", "firefox", "edge", "brave", etc. if you need to
# download private/unlisted playlists or videos -- yt-dlp
# will reuse your browser's login cookies. Leave as None otherwise.
COOKIES_FROM_BROWSER = None


def get_output_template(is_playlist: bool, media_ext: str = "%(ext)s") -> str:
    if is_playlist:
        return str(DOWNLOAD_DIR / "%(playlist_title)s" / ("%(title)s." + media_ext))
    return str(DOWNLOAD_DIR / ("%(title)s." + media_ext))


def progress_hook(d):
    if d["status"] == "downloading":
        pct = d.get("_percent_str", "").strip()
        speed = d.get("_speed_str", "").strip()
        eta = d.get("_eta_str", "").strip()
        print(f"\r  {pct}  {speed}  ETA {eta}   ", end="", flush=True)
    elif d["status"] == "finished":
        print()


def normalize_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned:
        return cleaned
    if cleaned.startswith(("http://", "https://")):
        return cleaned
    if "://" in cleaned:
        return cleaned
    return f"https://{cleaned}"


def download_audio(url: str, is_playlist: bool, media: str = "mp3") -> list[Path]:
    url = normalize_url(url)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    final_paths: list[Path] = []

    def pp_hook(d):
        if d["status"] == "finished" and d.get("postprocessor") == "FFmpegExtractAudio":
            filepath = Path(d["info_dict"]["filepath"])
            if filepath.suffix.lower() != ".mp3":
                filepath = filepath.with_suffix(".mp3")
            final_paths.append(filepath)

    # media: "mp3" for audio, "mp4" for video
    media = media.lower()
    if media == "mp4":
        fmt = "bestvideo+bestaudio/best"
        out_ext = "mp4"
    else:
        fmt = "bestaudio/best"
        out_ext = "mp3"

    ydl_opts = {
        "format": fmt,
        "outtmpl": get_output_template(is_playlist, out_ext),
        "noplaylist": not is_playlist,
        "concurrent_fragment_downloads": 8,
        "retries": 10,
        "progress_hooks": [progress_hook],
        "postprocessor_hooks": [pp_hook],
        "prefer_ffmpeg": True,
        "writethumbnail": True,
        # For MP3: extract audio and embed thumbnail/metadata. For MP4: keep best muxed output.
        "postprocessors": ([
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
            {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
            {"key": "FFmpegMetadata"},
            {"key": "EmbedThumbnail"},
        ] if media == "mp3" else []),
        "quiet": True,
        "no_warnings": True,
    }

    if COOKIES_FROM_BROWSER:
        ydl_opts["cookiesfrombrowser"] = (COOKIES_FROM_BROWSER,)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        if "403" in str(e):
            print(
                "\n✦ Got a 403 Forbidden error from YouTube. A few things to try:\n"
                "  1. If this playlist is private or unlisted, try setting it to "
                "Public temporarily (YouTube Studio > Content > Playlists > "
                "Visibility), then run the download again. Switch it back afterward.\n"
                "  2. Make sure yt-dlp is fully up to date:\n"
                "       pip install -U \"yt-dlp[default]\"\n"
                "  3. YouTube downloads now need a JS runtime (Deno) installed:\n"
                "       winget install DenoLand.Deno\n"
                "     then reopen your terminal so PATH picks it up.\n"
            )
        raise

    if not final_paths:
        final_paths = sorted(DOWNLOAD_DIR.rglob(f"*.{out_ext}"))

    return final_paths


def make_mp3(wav_path: Path) -> Path:
    def get_bitrate() -> str:
        bitrate = input("Enter desired MP3 bitrate (e.g., 128k, 192k, 320k, default 192k): ༘♡ ").strip()
        if not bitrate:
            return "192k"
        if bitrate.endswith("k") and bitrate[:-1].isdigit():
            return bitrate
        print("Invalid bitrate format. Please enter a number followed by 'k' (e.g., 128k). ༘♡")
        return get_bitrate()

    bitrate = get_bitrate()
    mp3_path = wav_path.with_suffix(".mp3")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-b:a", bitrate, str(mp3_path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return mp3_path


if __name__ == "__main__":
    print("╔═ * . · : · . ✧ ✦ ✧ . · : · . * ═╗")
    print("           Media Downloader          ")
    print("╚═ * . · : · . ✧ ✦ ✧ . · : · . * ═╝")
    print()
    print()
    print()
    print()

    if not shutil.which("ffmpeg"):
        print("ffmpeg is required (for WAV/MP3 conversion) so go download it and check it's in the PATH ")
        raise SystemExit(1)

    DOWNLOAD_DIR = get_download_dir()

    while True:
        media_input = input("Choose download format - mp3 or mp4 (default mp3): ").strip().lower()
        if not media_input:
            media = "mp3"
            print(f"✦ Download format set to: {media.upper()}")
        else:
            media = "mp4" if media_input == "mp4" else "mp3"
            print(f"✦ Download format set to: {media.upper()}")

        url = input(
            " Enter YouTube or SoundCloud URL (or press Enter/q to quit): "
        ).strip()
        if not url or url.lower() in {"q", "quit", "exit"}:
            print(" Goodbye! ")
            break

        is_playlist_input = input("Is this a playlist / SoundCloud set? (y/n, default n): ").strip().lower()
        is_playlist = is_playlist_input == "y"

        print(f"\nSaving files to: {DOWNLOAD_DIR}")
        print(" Downloading and converting to MP3 with metadata and embedded cover art...")

        start_time = time.time()
        mp3_files = download_audio(url, is_playlist, media)
        elapsed = time.time() - start_time

        print(f"\nDone in {elapsed:.1f} seconds.")
        print("Saved files:")
        for mp3 in mp3_files:
            print(f"  {mp3}")

        print("\n Ready for the next download!\n")
