#!/usr/bin/env nix-shell
#! nix-shell -i python3 -p "python3.withPackages (ps: with ps; [ requests pillow imageio shapely pyshp ])"
"""
make_hurricane_overlay_gif.py

Overlay active hurricane forecast cones and tracks on top of the latest 24-hour
GOES-19 GLM lightning-extent GIF for the south-eastern CONUS sector.

Usage (from shell):
    python make_hurricane_overlay_gif.py \
        --gif-url https://cdn.star.nesdis.noaa.gov/GOES19/GLM/SECTOR/se/EXTENT3/20251852306-20251860306-GOES19-GLM-SE-EXTENT3-600x600.gif \
        --output overlay_glm_hurricanes.gif

If --gif-url is not supplied, the script falls back to the hard-coded example
URL above. The script grabs the most recent cone-of-uncertainty shapefile(s)
for every *active* storm listed in the NHC Atlantic and East-Pacific GIS RSS
feeds, converts those polygons/centre-tracks to image-pixel coordinates, and
burns them into each frame of the lightning GIF.

Dependencies:
    nix-shell -p "python3.withPackages (ps: with ps; [ requests pillow imageio shapely pyshp ])"

These are pure-Python wheels on PyPI (no GDAL heavy-weight deps required).
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Iterator, List, Sequence, Tuple
from datetime import datetime, timedelta, timezone

import requests
from PIL import Image, ImageDraw, ImageSequence
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union
import shapefile  # pyshp

# -----------------------------------------------------------------------------
# Constants & configuration – tweak here if the GOES sector changes
# -----------------------------------------------------------------------------

# Default GIF to pull (24-hour lightning extent mosaic for GOES-19 / SE sector)
DEFAULT_GIF_URL = (
    "https://cdn.star.nesdis.noaa.gov/GOES19/GLM/SECTOR/se/EXTENT3/"
    "20251852306-20251860306-GOES19-GLM-SE-EXTENT3-600x600.gif"
)

# Lat/lon rectangle covered by the GOES SE sector GIF (approximate)
# Sources:  https://www.star.nesdis.noaa.gov/GOES/GOES19_GLMI.php   + eyeballing
# min/max longitudes must be WEST NEGATIVE in degrees east.
LON_MIN, LON_MAX = -100.0, -70.0   # degrees East (negative == West)
LAT_MIN, LAT_MAX =  20.0,  40.0   # degrees North

# NHC RSS feeds with active storm GIS links
ATLANTIC_FEED = "https://www.nhc.noaa.gov/gis-at.xml"
E_PACIFIC_FEED = "https://www.nhc.noaa.gov/gis-ep.xml"

# Regex pattern that captures the most recent 5-day cone shapefile archive
CONE_ZIP_REGEX = re.compile(r"https://www\.nhc\.noaa\.gov/gis/forecast/archive/[a-z0-9_]+_5day_(?:latest|\d+)\.zip")

# Regex for matching the track KMZ (optional line overlay)
TRACK_KMZ_REGEX = re.compile(r"https://www\.nhc\.noaa\.gov/storm_graphics/api/[A-Z0-9_]+TRACK(?:_[a-z]+)?\.kmz", re.I)


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def fetch_text(url: str, timeout: int = 20) -> str:
    """Download *url* and return decoded text (UTF-8)."""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def extract_links(feed_xml: str, pattern: re.Pattern[str]) -> List[str]:
    """Return all unique links in *feed_xml* that match *pattern*."""
    links = set(re.findall(pattern, feed_xml))
    return sorted(links)


def download_file(url: str, dest: Path, chunk: int = 2 ** 16) -> None:
    """Stream *url* to *dest*."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    with dest.open("wb") as fh:
        for block in r.iter_content(chunk):
            fh.write(block)


def lonlat_to_pixel(lon: float, lat: float, width: int, height: int) -> Tuple[int, int]:
    """Convert geographic coordinates to GIF pixel coordinates (simple linear)."""
    x = int((lon - LON_MIN) / (LON_MAX - LON_MIN) * width)
    y = int((LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * height)  # y inverted
    return x, y


def _parse_iso_time(val: str) -> datetime | None:
    """Attempt to parse various ISO-like datetime strings to UTC."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y%m%d %H%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(val.strip(), fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


# -----------------------------------------------------------------------------
# Shapefile handling
# -----------------------------------------------------------------------------

def load_cone_polygons(zip_path: Path) -> List[Polygon]:
    """Collect polygon geometries from any suitable layer in the *_5day_*.zip.

    Strategy:
    1. Build an ordered list of .shp files – prioritising filenames containing
       "cone" first, then the remainder in archive order.
    2. For each candidate layer, attempt to read it with *pyshp* and harvest
       polygon shapes – stop as soon as we find >0 polygons (most zips only
       contain one polygon layer anyway).
    3. Return the full list (can be empty if none found).
    """
    polygons: List[Polygon] = []

    with zipfile.ZipFile(zip_path) as zf, tempfile.TemporaryDirectory() as tdir:
        shp_members = [n for n in zf.namelist() if n.lower().endswith('.shp')]
        if not shp_members:
            return []

        # Sort so that *cone* layers are tried first
        shp_members.sort(key=lambda n: ("cone" not in n.lower(), n))

        for shp_member in shp_members:
            base_no_ext = shp_member[:-4]
            needed_exts = ['.shp', '.shx', '.dbf']
            extracted = {}
            success = True
            for ext in needed_exts:
                m_name = next((n for n in zf.namelist() if n.lower() == (base_no_ext + ext).lower()), None)
                if m_name is None:
                    success = False
                    break
                dst_path = Path(tdir) / Path(m_name).name
                with zf.open(m_name) as src, open(dst_path, 'wb') as dst:
                    dst.write(src.read())
                extracted[ext] = dst_path
            if not success:
                continue

            try:
                reader = shapefile.Reader(str(extracted['.shp']))
            except Exception:
                continue

            allowed_types = {shapefile.POLYGON, getattr(shapefile, 'POLYGONZ', 15), getattr(shapefile, 'POLYGONM', 25)}
            for rec in reader.shapeRecords():
                shape = rec.shape
                if shape.shapeType not in allowed_types:
                    continue
                parts = list(shape.parts) + [len(shape.points)]
                for i in range(len(parts) - 1):
                    pts = shape.points[parts[i]: parts[i + 1]]
                    if len(pts) >= 4:
                        poly = Polygon(pts)
                        if poly.is_valid:
                            polygons.append(poly)

            if polygons:
                # got at least one polygon layer; no need to inspect others
                break

    return polygons


def load_track_points(zip_path: Path) -> List[Tuple[float, float, datetime | None]]:
    """Return (lon, lat, datetime|None) tuples from best-track shapefile."""
    result: List[Tuple[float, float, datetime | None]] = []
    with zipfile.ZipFile(zip_path) as zf, tempfile.TemporaryDirectory() as tdir:
        shp_members = [n for n in zf.namelist() if n.lower().endswith('.shp')]
        if not shp_members:
            return []
        shp_members.sort(key=lambda n: ('pts' not in n.lower(), n))

        for shp_member in shp_members:
            base_no_ext = shp_member[:-4]
            needed = [base_no_ext + ext for ext in ('.shp', '.shx', '.dbf')]
            if not all(any(n.lower() == m.lower() for n in zf.namelist()) for m in needed):
                continue
            # extract required components
            extracted = {}
            for m in needed:
                member_real = next(n for n in zf.namelist() if n.lower() == m.lower())
                dest = Path(tdir) / Path(member_real).name
                with zf.open(member_real) as src, open(dest, 'wb') as dst:
                    dst.write(src.read())
                extracted[m[-4:]] = dest  # keyed by extension

            try:
                rdr = shapefile.Reader(str(extracted['.shp']))
            except Exception:
                continue

            # locate ISO_TIME field if present
            field_names = [f[0] for f in rdr.fields[1:]]
            iso_idx = field_names.index('ISO_TIME') if 'ISO_TIME' in field_names else None

            for sr in rdr.shapeRecords():
                shp = sr.shape
                rec = sr.record
                if not shp.points:
                    continue
                lon, lat = shp.points[0]
                dt = None
                if iso_idx is not None:
                    dt = _parse_iso_time(rec[iso_idx])
                result.append((lon, lat, dt))
            if result:
                break
    return result


# -----------------------------------------------------------------------------
# Main overlay routine
# -----------------------------------------------------------------------------

def create_overlay_gif(base_gif: Path, cones: Sequence[Polygon],
                       tracks: Sequence[Sequence[Tuple[float, float]]],
                       out_gif: Path) -> None:
    """Render cones, tracks, and current positions onto *base_gif* → *out_gif*."""
    base = Image.open(base_gif)
    width, height = base.size
    frames: List[Image.Image] = []
    # total number of frames for proportional indexing
    frames_total = getattr(base, "n_frames", sum(1 for _ in ImageSequence.Iterator(base)))

    # pre-convert polygons to pixel space
    px_cones = [[lonlat_to_pixel(lon, lat, width, height) for lon, lat in poly.exterior.coords]
                for poly in cones]
    px_tracks = [[lonlat_to_pixel(lon, lat, width, height) for lon, lat in seg]
                 for seg in tracks]

    for frame in ImageSequence.Iterator(base):
        fr = frame.convert("RGBA")
        draw = ImageDraw.Draw(fr, "RGBA")
        # cones – yellow outline
        for poly_px in px_cones:
            draw.polygon(poly_px, outline=(255, 255, 0, 255), fill=None)
        # tracks – cyan line
        for line_px in px_tracks:
            if len(line_px) > 1:
                draw.line(line_px, fill=(0, 255, 255, 255), width=2)
        # moving storm centre – red dot advances along track over frames
        for track_px in px_tracks:
            if not track_px:
                continue
            idx = int(frame.tell() / max(frames_total - 1, 1) * (len(track_px) - 1))
            x, y = track_px[idx]
            r = 4
            draw.ellipse((x - r, y - r, x + r, y + r), outline=(255, 0, 0, 255), fill=(255, 0, 0, 255))
        frames.append(fr)

    durations = [frame.info.get('duration', 100) for frame in ImageSequence.Iterator(base)]
    frames[0].save(out_gif, save_all=True, append_images=frames[1:], optimize=False,
                   duration=durations, loop=0)


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Overlay active NHC cones on GOES GLM GIF.")
    ap.add_argument("--gif-url", default=DEFAULT_GIF_URL,
                    help="Source GOES lightning GIF (24-hour animation).")
    ap.add_argument("--output", default="overlay_glm_hurricanes.gif",
                    help="Filename for the overlaid GIF.")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # 1. Download base GIF --------------------------------------------------
        print(f"Downloading base GIF… ({args.gif_url})")
        base_gif = tmp / "base.gif"
        download_file(args.gif_url, base_gif)

        # 2. Discover active storms (Atlantic + East-Pac) -----------------------
        cone_links: List[str] = []
        for feed in (ATLANTIC_FEED, E_PACIFIC_FEED):
            try:
                xml = fetch_text(feed)
            except Exception as exc:
                print(f"Warning: failed to fetch {feed}: {exc}")
                continue
            links = extract_links(xml, CONE_ZIP_REGEX)
            cone_links.extend(links)

        if not cone_links:
            print("No active storms with cone shapefiles found – nothing to overlay.")
            sys.exit(0)

        print("Found", len(cone_links), "active storm cone shapefile(s).")

        # 3. Download shapefiles and build polygons/track lines --------------
        all_polys: List[Polygon] = []
        all_tracks: List[List[Tuple[float, float]]] = []
        for url in cone_links:
            fname = tmp / Path(url).name
            base_id = Path(url).stem.split('_')[0]  # e.g., al032025
            print("  •", url.split("/")[-1])
            try:
                download_file(url, fname)
                polys = load_cone_polygons(fname)
                all_polys.extend(polys)
            except Exception as exc:
                print(f"    ! Failed to process {url}: {exc}")

            # attempt to fetch best-track for this storm
            bt_url = f"https://www.nhc.noaa.gov/gis/best_track/{base_id}_best_track.zip"
            try:
                bt_path = tmp / Path(bt_url).name
                download_file(bt_url, bt_path)
                pts = load_track_points(bt_path)
                if pts:
                    # extract lon/lat regardless of length of tuple
                    all_tracks.append([(p[0], p[1]) for p in pts])
            except Exception as exc:
                print(f"    ! Failed to get track for {base_id}: {exc}")

        if not all_polys:
            print("Could not extract any polygons from shapefiles – aborting.")
            sys.exit(1)

        # 4. Overlay and save ---------------------------------------------------
        out_path = Path(args.output)
        # Ensure destination directory exists
        out_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Rendering overlay GIF → {out_path.resolve()}")
        create_overlay_gif(base_gif, all_polys, all_tracks, out_path)
        print("Done! ")


if __name__ == "__main__":
    main() 
