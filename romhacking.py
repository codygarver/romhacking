#!/usr/bin/env python3

from bs4 import BeautifulSoup
import argparse
import json
import os
import re
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

    title = soup.find("meta", property="og:title")
    name = title["content"]
    platform = rom_info[3].lower()
    version = rom_info[7]

    return name, platform, version


def sigint_handler(signal, frame):
    sys.exit(0)


def add(hack):
    if hack.isnumeric():
        id = hack
        url = "https://www.romhacking.net/hacks/" + hack
    else:
        id = re.search(r'\d+', hack).group()
        url = hack

    name, platform, version = get_romhacking(url)

    patches_dict.update({name: {
        "filename": "",
        "id": id,
        "platform": platform,
        "sha1": "",
        "version": version
    }})

    if args.debug:
        print(json.dumps(patches_dict, sort_keys=True, indent=4))

    with open(args.config, "w") as out_file:
        json.dump(patches_dict, out_file, indent=4, sort_keys=True)

    print("Added " + name)


def update():
    if not os.path.exists(args.config):
        print("Error, config.json does not exist! First initialize it with --add")
        exit(1)

    for patch in patches_dict:
        local = patches_dict[patch]["version"]
        url = "https://www.romhacking.net/hacks/" + \
            patches_dict[patch]["id"]
        _, _, latest = get_romhacking(url)
        if local != latest:
            print("Outdated: " + patch)
            print("Local Version: " + local)
            print("Latest Version: " + latest)
            print("URL: " + url + "\n")


signal.signal(signal.SIGINT, sigint_handler)

if __name__ == "__main__":

    # Configure argparse
    description = "Manage rom hacks and check for updates"
    parser = argparse.ArgumentParser(
        description=description)
    parser.add_argument("--add")
    parser.add_argument("--config")
    parser.add_argument("--debug", action='store_true')
    parser.add_argument("--update", action='store_true')
    args = parser.parse_args()

    # Read json to dictionary
    if os.path.exists(args.config):
        patches_file = open(args.config)
        patches_dict = json.load(patches_file)
    else:
        patches_dict = {}

    if args.add:
        add(args.add)

    if args.update:
        update()
