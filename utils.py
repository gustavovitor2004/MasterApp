"""
utils.py

Small, dependency-light helpers shared across the app:
- URL validation
- Platform detection (YouTube, Instagram, Twitter/X, TikTok, Reddit, Facebook, generic)
- ffmpeg detection
- human-readable formatting for byte sizes / ETA / speed
- filesystem-safe filename helper
"""

import os
import re
import shutil
import subprocess
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

# Ordered so more specific hosts are checked before generic fallbacks.
PLATFORM_PATTERNS = [
    ("YouTube", re.compile(r"(youtube\.com|youtu\.be|music\.youtube\.com)", re.I)),
    ("Instagram", re.compile(r"instagram\.com", re.I)),
    ("Twitter/X", re.compile(r"(twitter\.com|x\.com)", re.I)),
    ("TikTok", re.compile(r"tiktok\.com", re.I)),
    ("Reddit", re.compile(r"reddit\.com", re.I)),
    ("Facebook", re.compile(r"(facebook\.com|fb\.watch)", re.I)),
    ("Vimeo", re.compile(r"vimeo\.com", re.I)),
    ("Twitch", re.compile(r"twitch\.tv", re.I)),
]

PLATFORM_ICONS = {
    "YouTube": "\U0001F534",       # red circle
    "Instagram": "\U0001F4F7",     # camera
    "Twitter/X": "\U0001F426",     # bird
    "TikTok": "\U0001F3B5",        # musical note
    "Reddit": "\U0001F47D",        # alien
    "Facebook": "\U0001F535",      # blue circle
    "Vimeo": "\U0001F3AC",         # clapper
    "Twitch": "\U0001F47E",        # game controller-ish
    "Outro": "\U0001F310",         # globe
}


def detect_platform(url: str) -> str:
    """Return a human-readable platform label detected from the URL host."""
    for label, pattern in PLATFORM_PATTERNS:
        if pattern.search(url):
            return label
    return "Outro"


def platform_icon(label: str) -> str:
    return PLATFORM_ICONS.get(label, PLATFORM_ICONS["Outro"])


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

def is_valid_url(url: str) -> bool:
    """Basic structural validation - not a guarantee yt-dlp can extract it,
    but enough to catch empty/garbage input before we hit the network."""
    if not url or not url.strip():
        return False
    url = url.strip()
    try:
        result = urlparse(url)
    except ValueError:
        return False
    if result.scheme not in ("http", "https"):
        return False
    if not result.netloc:
        return False
    return True


def split_urls(text: str) -> list:
    """Split multi-line pasted text into a list of individual, valid URLs."""
    candidates = re.split(r"[\r\n]+", text)
    urls = []
    for c in candidates:
        c = c.strip()
        if c and is_valid_url(c):
            urls.append(c)
    return urls


# ---------------------------------------------------------------------------
# ffmpeg detection
# ---------------------------------------------------------------------------

def find_ffmpeg(custom_path: str = "") -> str:
    """Return a usable ffmpeg executable path/name, or '' if none found."""
    if custom_path:
        candidate = custom_path
        if os.path.isdir(candidate):
            candidate = os.path.join(candidate, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if os.path.isfile(candidate):
            return candidate

    found = shutil.which("ffmpeg")
    if found:
        return found

    if os.name == "nt":
        # winget installs ffmpeg as a "portable" package and exposes it via
        # a shim in this fixed folder. Checking it directly means the app
        # can find ffmpeg right after `instalar.bat` runs, even before the
        # user has restarted the PC and the PATH change has fully
        # propagated to every already-running process.
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            winget_shim = os.path.join(local_app_data, "Microsoft", "WinGet", "Links", "ffmpeg.exe")
            if os.path.isfile(winget_shim):
                return winget_shim

    return ""


def ffmpeg_is_working(ffmpeg_path: str) -> bool:
    """Actually try to run ffmpeg -version to confirm it's a real binary."""
    if not ffmpeg_path:
        return False
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        proc = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            timeout=5,
            creationflags=creationflags,
        )
        return proc.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_bytes_per_sec(num_bytes) -> str:
    if not num_bytes:
        return "-- MB/s"
    num_bytes = float(num_bytes)
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB/s"


def format_eta(seconds) -> str:
    if seconds is None:
        return "--"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def format_size(num_bytes) -> str:
    if not num_bytes:
        return "--"
    num_bytes = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def safe_filename(name: str) -> str:
    """Strip characters that are illegal in Windows filenames."""
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    return name.strip()[:150] or "video"


def height_to_label(height) -> str:
    """Map a pixel height back onto one of our quality labels for display."""
    if not height:
        return "desconhecida"
    if height >= 2160:
        return "4K (2160p)"
    if height >= 1080:
        return "1080p"
    if height >= 720:
        return "720p"
    if height >= 480:
        return "480p"
    if height >= 360:
        return "360p"
    return f"{height}p"
