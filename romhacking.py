#!/usr/bin/env python3

from bs4 import BeautifulSoup
import json
import requests
import signal
import sys


def get_romhacking(url):
    html = requests.get(url)

    soup = BeautifulSoup(html.text, "html.parser")

    table_body = soup.find(
        "table", {"class": "entryinfo entryinfosmall"})

    rows = table_body.find_all("tr")

    rom_info = []

    for row in rows:
        cols = row.find_all("td")
        rom_info = rom_info + [cols[0].text.strip()]

    if not rom_info or len(rom_info) != 12:
        print("Error: failed to fetch rom info for " + url)
        exit(1)

    name = rom_info[0]
    platform = rom_info[3].lower()
    version = rom_info[7]

    return name, platform, version


def sigint_handler(signal, frame):
    sys.exit(0)


signal.signal(signal.SIGINT, sigint_handler)

if __name__ == "__main__":
    # Read json to dictionary
    patches_json = "/Users/codygarver/Downloads/analogue-pocket/patches/patches.json"
    patches_file = open(patches_json)
    patches_dict = json.load(patches_file)

    for patch in patches_dict:
        local_version = patches_dict[patch]["version"]
        _, _, web_version = get_romhacking(patches_dict[patch]["url"])
        if local_version != web_version:
            print("Outdated!: " + patch)
            print("Link: " + patches_dict[patch]["url"])
