"""
spotmap/downloader.py
=====================
Handles downloading and caching of boundary files.

- Lite files  → bundled inside the package (used by default)
- Full files  → downloaded from GitHub Releases on first use,
                cached in ~/.spotmap/data/
"""

import os
import urllib.request
from pathlib import Path
from importlib.resources import files

from spotmap.exceptions import BoundaryFileError

# =========================================================
# CONFIGURATION
# =========================================================

# Local cache directory — ~/.spotmap/data/
CACHE_DIR = Path.home() / ".spotmap" / "data"

# GitHub Releases download URLs
RELEASE_BASE = (
    "https://github.com/TharunMallesan/spotmap/"
    "releases/download/v1.0-boundaries"
)

FULL_FILES = {
    "state_boundary_full.fgb":    f"{RELEASE_BASE}/state_boundary_full.fgb",
    "district_boundary_full.fgb": f"{RELEASE_BASE}/district_boundary_full.fgb",
}

LITE_FILES = {
    "state_boundary_lite.fgb":    "state_boundary_lite.fgb",
    "district_boundary_lite.fgb": "district_boundary_lite.fgb",
}

# =========================================================
# PUBLIC FUNCTIONS
# =========================================================

def get_bundled_path(filename: str) -> str:
    """
    Returns the path to a LITE file bundled inside the package.
    These are always available after pip install — no download needed.
    """
    try:
        path = files("spotmap.data").joinpath(filename)
        path_str = str(path)
        if not os.path.exists(path_str):
            raise BoundaryFileError(
                f"Bundled file '{filename}' not found inside the package. "
                f"Try reinstalling: pip install --force-reinstall spotmap"
            )
        return path_str
    except Exception as e:
        raise BoundaryFileError(f"Could not locate bundled file '{filename}': {e}")


def get_full_path(filename: str, force: bool = False) -> str:
    """
    Returns the path to a FULL resolution file.
    Downloads from GitHub Releases on first use and caches in ~/.spotmap/data/.

    Parameters
    ----------
    filename : str
        e.g. 'state_boundary_full.fgb'
    force : bool
        If True, re-downloads even if already cached.
    """
    if filename not in FULL_FILES:
        raise BoundaryFileError(
            f"Unknown file: '{filename}'. "
            f"Available: {list(FULL_FILES.keys())}"
        )

    local_path = CACHE_DIR / filename

    if local_path.exists() and not force:
        return str(local_path)

    # Download
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    url = FULL_FILES[filename]

    print(f"[spotmap] Downloading {filename} (first time only)...")
    print(f"[spotmap] Source: {url}")

    try:
        urllib.request.urlretrieve(url, local_path, reporthook=_progress_hook)
        print(f"\n[spotmap] Saved to: {local_path}")
    except Exception as e:
        # Clean up partial download
        if local_path.exists():
            local_path.unlink()
        raise BoundaryFileError(
            f"Failed to download '{filename}' from GitHub Releases.\n"
            f"Error: {e}\n"
            f"You can manually download from:\n  {url}\n"
            f"and place it in: {CACHE_DIR}"
        )

    return str(local_path)


def download_boundaries(force: bool = False):
    """
    Pre-download both full resolution boundary files.
    Call this once if you want to use high-precision boundaries.

    Parameters
    ----------
    force : bool
        If True, re-downloads even if already cached.

    Example
    -------
    import spotmap
    spotmap.download_boundaries()
    """
    print("[spotmap] Downloading full resolution boundary files...")
    for filename in FULL_FILES:
        get_full_path(filename, force=force)
    print("[spotmap] All boundary files ready!")


def info():
    """Print info about cached and bundled files."""
    print("\n── SpotMap Boundary Files ──────────────────────")

    print("\nBundled (lite) files:")
    for name in LITE_FILES:
        try:
            path = get_bundled_path(name)
            size = os.path.getsize(path) / 1024
            print(f"  ✅ {name:<40} {size:>8.1f} KB")
        except BoundaryFileError:
            print(f"  ❌ {name:<40} NOT FOUND")

    print(f"\nCached (full) files — location: {CACHE_DIR}")
    for name in FULL_FILES:
        path = CACHE_DIR / name
        if path.exists():
            size = os.path.getsize(path) / (1024 * 1024)
            print(f"  ✅ {name:<40} {size:>8.1f} MB")
        else:
            print(f"  ⬇️  {name:<40} not downloaded yet")

    print()


# =========================================================
# INTERNAL HELPERS
# =========================================================

def _progress_hook(block_num, block_size, total_size):
    """Show a simple download progress indicator."""
    if total_size > 0:
        downloaded = block_num * block_size
        percent = min(100, downloaded * 100 / total_size)
        mb_done = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        print(
            f"\r[spotmap] {percent:5.1f}%  {mb_done:.1f} / {mb_total:.1f} MB",
            end="",
            flush=True
        )