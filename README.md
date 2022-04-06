# romhacking
Simple manager and patcher for rom hacks from romhacking.net
## How it works
`romhacking.py` uses a json file to store rom hack metadata and can scrape [romhacking.net](https://romhacking.net) pages for remote metadata, such as the latest version. It can then tell you if your local version is out-of-date.

`apply_patches.py` scans your roms' checksums and uses `romhacking.py`'s rom hack metadata json file to match roms with rom hacks and patch the roms using [flips](https://github.com/Alcaro/Flips).
