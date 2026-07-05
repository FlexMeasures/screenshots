#!/usr/bin/env python3
"""Reapply CSP-safe vector logos + dark-mode styling to overview-flexEMS.svg.

See README.md in this directory for background, prerequisites, and usage.
"""

import re
import sys
from pathlib import Path

ASSETS_DIR = Path(__file__).parent / "logo_assets"

# Some assets (those using the display-toggle duplicate pattern, e.g. two
# sibling <g id="...-light"/"...-dark"> elements plus a trailing <style>)
# have more than one top-level node, which isn't valid as a standalone XML
# document (GNOME Image Viewer/librsvg will refuse to open such a file with
# "Extra content at the end of the document"). To keep those asset files
# independently openable/previewable, they're wrapped in an outer
# <svg data-standalone-wrapper="1"> ... </svg> that exists only for
# standalone-document validity; it must be stripped before splicing the
# fragment into the main diagram, since the diagram already provides the
# single root <svg> and the wrapper carries no positioning of its own.
_STANDALONE_WRAPPER_RE = re.compile(
    r'^<svg[^>]*\bdata-standalone-wrapper="1"[^>]*>(.*)</svg>\s*$', re.DOTALL
)


def _strip_standalone_wrapper(fragment: str) -> str:
    m = _STANDALONE_WRAPPER_RE.match(fragment.strip())
    return m.group(1) if m else fragment

# Each logo is located in a freshly-exported (draw.io) SVG by its raster
# <image width="..." height="..."/> placeholder -- draw.io always re-emits
# these as plain data-URI raster images on save, regardless of any previous
# patch. width/height are stable fingerprints across draw.io re-exports;
# x/y may drift a few pixels whenever the surrounding diagram is edited, so
# position is always read fresh from the current file, never hardcoded.
#
# asset: filename in logo_assets/ containing the pre-baked replacement
#   fragment(s), with its own coordinates baked in at `baked_x`/`baked_y`
#   (the position it happened to be at when extracted). The script rewrites
#   every occurrence of baked_x/baked_y inside that fragment to the position
#   actually found in the current file, so it doesn't matter if draw.io
#   shifted the icon since.
# shrink: optional (float < 1) -- used only for Home Assistant, whose
#   official logomark has no internal padding and must be rendered smaller
#   than its bounding box to avoid overlapping the caption below it. When
#   set, the script recomputes x/y/w/h fresh (shrunk + recentered) instead
#   of doing a simple coordinate substitution.
LOGOS = [
    {
        "name": "Home Assistant",
        "width": "49.87",
        "height": "49.87",
        "asset": "home_assistant.svg",
        "baked_x": "953.247",
        "baked_y": "267.987",
        "baked_w": "39.896",
        "baked_h": "39.896",
        "shrink": 0.80,
    },
    {
        "name": "Energy Flexibility (S2 icon)",
        "width": "30",
        "height": "30",
        "asset": "energy_flexibility.svg",
        "baked_x": "862.13",
        "baked_y": "272.94",
    },
    {
        "name": "ENTSO-E (Grid & Emissions)",
        "width": "77.78",
        "height": "22.12",
        "asset": "entsoe.svg",
        "baked_x": "881.24",
        "baked_y": "365",
    },
    {
        "name": "openADR (Demand Response)",
        "width": "91.33",
        "height": "19.76",
        "asset": "openadr.svg",
        "baked_x": "874.47",
        "baked_y": "434",
    },
    {
        "name": "OpenWeather",
        "width": "69.69",
        "height": "31",
        "asset": "openweather.svg",
        "baked_x": "850",
        "baked_y": "505",
    },
    {
        "name": "weatherapi",
        "width": "60",
        "height": "50",
        "asset": "weatherapi.svg",
        "baked_x": "938.13",
        "baked_y": "497",
    },
]


def fix_logo(svg: str, logo: dict) -> str:
    pat = re.compile(
        r'<image x="([-\d.]+)" y="([-\d.]+)" width="%s" height="%s"[^>]*/>'
        % (re.escape(logo["width"]), re.escape(logo["height"]))
    )
    m = pat.search(svg)
    if not m:
        print(f"  SKIP {logo['name']}: no matching raster placeholder found "
              f"(width={logo['width']} height={logo['height']}) -- already "
              f"patched, or draw.io changed its size/shape", file=sys.stderr)
        return svg

    found_x, found_y = m.group(1), m.group(2)
    fragment = (ASSETS_DIR / logo["asset"]).read_text()
    fragment = _strip_standalone_wrapper(fragment)

    if "shrink" in logo:
        x, y = float(found_x), float(found_y)
        w, h = float(logo["width"]), float(logo["height"])
        shrink = logo["shrink"]
        new_w, new_h = w * shrink, h * shrink
        new_x, new_y = x + (w - new_w) / 2, y + (h - new_h) / 2
        fragment = fragment.replace(f'x="{logo["baked_x"]}"', f'x="{new_x}"')
        fragment = fragment.replace(f'y="{logo["baked_y"]}"', f'y="{new_y}"')
        fragment = fragment.replace(f'width="{logo["baked_w"]}"', f'width="{new_w}"')
        fragment = fragment.replace(f'height="{logo["baked_h"]}"', f'height="{new_h}"')
    else:
        fragment = fragment.replace(f'x="{logo["baked_x"]}"', f'x="{found_x}"')
        fragment = fragment.replace(f'y="{logo["baked_y"]}"', f'y="{found_y}"')

    svg = svg[: m.start()] + fragment + svg[m.end() :]
    print(f"  OK   {logo['name']}: patched at ({found_x}, {found_y})")
    return svg


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} path/to/overview-flexEMS.svg", file=sys.stderr)
        sys.exit(1)

    target = Path(sys.argv[1])
    svg = target.read_text()

    print(f"Fixing logos in {target}")
    for logo in LOGOS:
        svg = fix_logo(svg, logo)

    target.write_text(svg)
    print("Done. Diff and render the file to confirm before committing.")


if __name__ == "__main__":
    main()
