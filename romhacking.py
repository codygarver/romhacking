#!/usr/bin/env python3

from bs4 import BeautifulSoup
import argparse
import json
import os
import pathlib
import re
import requests
import signal
import sys

try:
    from github import Github
except:
    pass


def get_romhacking(url):
    html = requests.get(url)
    soup = BeautifulSoup(html.text, "html.parser")

    rom_info_div = soup.find(
        "div", {"id": "rom_info"})

    list_items = rom_info_div.find_all("li")

    sha1 = ""
    sha1_line_regex = "^(FILE\/ROM\sSHA\-1\:.*|.*ROM\sSHA\-1\:.*|SHA\-1\:.*|.*SHA\-1.*|SHA\s1)"
    sha1_sum_regex = "[a-f0-9]{40}"
    for item in list_items:
        if re.search(sha1_line_regex, item.text):
            sha1 = re.search(sha1_sum_regex, item.text.lower()).group()
            break

    table_body = soup.find(
        "table", {"class": "entryinfo entryinfosmall"})

    rows = table_body.find_all("tr")

    rom_info = []

    for row in rows:
        cols = row.find_all("td")
        rom_info = rom_info + [cols[0].text.strip()]

    category = re.search("hacks|translations", url).group()

    if not category or not rom_info:
        print("Error: failed to fetch rom info for " + url)
        exit(1)

    if args.debug:
        print(rom_info)

    title = soup.find("meta", property="og:title")
    name = title["content"]
    name = re.sub("\/", "&", name)

    id = re.search(r'\d+', url).group()

    def get_platform(platform):
        platform = platform.lower()
        if platform == "nintendo ds":
            platform = "nds"
        elif platform == "nintendo entertainment system":
            platform = "nes"
        elif platform == "playstation portable":
            platform = "psp"
        elif platform == "super nintendo":
            platform = "snes"

        return platform

    length_error = "Error: rom info too short, bad page?"

    if category == "hacks":
        if len(rom_info) != 12:
            print(length_error)
            exit(1)

        game = soup.find("h4", {"class": "date"}).text.strip()
        game = re.sub("Hack of ", "", game)
        game = re.sub("\u00e9", "e", game)  # Pokémon to Pokemon
        game = re.sub("\u2019", "\'", game)  # '

        modified = rom_info[11]
        platform = get_platform(rom_info[3])
        version = rom_info[7]

    if category == "translations":
        if len(rom_info) != 14:
            print(length_error)
            exit(1)

        # game is first string before linebreak
        game = rom_info[0].strip().split("\n")[0]
        modified = rom_info[13]
        platform = get_platform(rom_info[4])
        version = rom_info[9]

    return game, name, id, modified, platform, version, sha1, category


def sigint_handler():
    sys.exit(0)


def add(url):
    game, name, id, modified, platform, version, sha1, category = get_romhacking(
        url)

    # Create category if nonexistent
    if category not in patches_dict:
        patches_dict[category] = {}

    # Create entry if nonexistent
    if id not in patches_dict[category]:
        patches_dict[category][id] = {
            "filename": [""],
            "game": game,
            "modified": modified,
            "name": name,
            "platform": platform,
            "sha1": sha1.upper(),
            "version": version
        }
        print("Added " + name)
    # Or update existing entry
    else:
        patches_dict[category][id]["game"] = game
        patches_dict[category][id]["modified"] = modified
        patches_dict[category][id]["name"] = name
        patches_dict[category][id]["platform"] = platform
        patches_dict[category][id]["version"] = version
        print("Updated " + name)

    if args.debug:
        print(json.dumps(patches_dict, sort_keys=True, indent=4))

    with open(args.config, "w") as out_file:
        json.dump(patches_dict, out_file, indent=4, sort_keys=True)


def update():
    if not os.path.exists(args.config):
        print("Error, config.json does not exist! First initialize it with --add")
        exit(1)

    for category in patches_dict:
        for patch in patches_dict[category]:
            game = patches_dict[category][patch]["game"]
            local_date = patches_dict[category][patch]["modified"]
            local_version = patches_dict[category][patch]["version"]
            name = patches_dict[category][patch]["name"]
            issue_title = "Update " + game + " " + name
            url = "https://www.romhacking.net/" + \
                category + \
                "/" + patch
            _, _, _, latest_date, _, latest_version, _, _ = get_romhacking(
                url)
            if local_version != latest_version or local_date != latest_date:
                if args.update_github:
                    github(issue_title, local_version,
                           latest_version, latest_date, url)
                else:
                    print(issue_title + " (" + patch + ")")
                    print("Local Version: " + local_version)
                    print("Latest Version: " + latest_version)
                    print("Local Date: " + local_date)
                    print("Latest Date: " + latest_date)
                    print("URL: " + url + "\n")


def github(romhack_name, local_version, latest_version, latest_date, url):
    github_repo = os.environ['GITHUB_REPOSITORY']
    github_token = os.environ['GITHUB_TOKEN']
    github = Github(github_token)
    repo = github.get_repo(github_repo)

    def github_issue_exists(title):
        open_issues = repo.get_issues(state='open')
        for issue in open_issues:
            if issue.title == title and issue.user.login == "github-actions[bot]":
                return True
        return False

    issue_title = "%s" % (romhack_name)
    if not github_issue_exists(issue_title):
        issue = repo.create_issue(
            issue_title, "%s version %s available %s, updated %s" % (romhack_name, latest_version, url, latest_date))
        print("%s version %s available (local version: %s) %s - Created issue %d" %
              (romhack_name, latest_version, local_version, url, issue.number))


def tests():
    if not patches_dict:
        print("Empty config")
        exit(1)

    fail = False

    for category in patches_dict:
        for patch in patches_dict[category]:
            # Test missing sha1sum
            if not patches_dict[category][patch]["sha1"]:
                print("Error: Missing sha1: " +
                      patches_dict[category][patch]["name"] + " (" + patch + ")")
                fail = True

            # Test missing patch filename
            if len(patches_dict[category][patch]["filename"]) == 0:
                print("Error: Missing patch filename: " + patches_dict[category][patch].get(
                    "name") + " (" + patch + ")")
                fail = True

            for patch_file in patches_dict[category][patch].get("filename"):
                # Test missing patch filename
                if not patch_file:
                    print("Error: Missing patch filename: " + patches_dict[category][patch].get(
                        "name") + " (" + patch + ")")
                    fail = True

                # Test missing patch file
                if not os.path.exists("patches/" + patch_file):
                    print("Error: Missing patch file: " + patches_dict[category][patch].get(
                        "name") + " (" + patch + ") " +
                        patch_file)
                    fail = True

    # Test unknown patch files
    dict_files = []
    for category in patches_dict:
        for patch in patches_dict[category]:
            dict_files = dict_files + \
                patches_dict[category][patch].get("filename")

    patches_path = pathlib.Path("patches/")
    ips_files = patches_path.glob("*.ips")
    found_files = []
    for file in ips_files:
        found_files = found_files + [file.name]
    unknown_files = [f for f in found_files if f not in dict_files]
    if unknown_files:
        for file in unknown_files:
            print("Unknown patch file: " + file)
        fail = True

    if fail:
        exit(1)


signal.signal(signal.SIGINT, sigint_handler)

if __name__ == "__main__":
    # Configure argparse
    description = "Manage rom hacks and check for updates"
    parser = argparse.ArgumentParser(
        description=description)
    parser.add_argument("--config")
    parser.add_argument("--debug", action='store_true')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--add")
    group.add_argument("--tests", action='store_true')
    group.add_argument("--update", action='store_true')
    group.add_argument("--update-github", action='store_true')

    args = parser.parse_args()

    # Sometimes require --config
    if args.add and (args.config is None):
        parser.error("--add requires --config")
    if args.tests and (args.config is None):
        parser.error("--tests requires --config")
    if args.update and (args.config is None):
        parser.error("--update requires --config")
    if args.update_github and (args.config is None):
        parser.error("--update_github requires --config")

    # Read json to dictionary
    if os.path.exists(args.config) and os.stat(args.config).st_size != 0:
        patches_file = open(args.config)
        patches_dict = json.load(patches_file)
    else:
        patches_dict = {}

    if args.add:
        add(args.add)

    if args.tests:
        tests()

    if args.update or args.update_github:
        update()
