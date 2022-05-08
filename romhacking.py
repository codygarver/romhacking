#!/usr/bin/env python3

from bs4 import BeautifulSoup
import argparse
import json
import os
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

    id = re.search(r'\d+', url).group()

    def get_platform(platform):
        if platform == "super nintendo":
            platform = "snes"
        elif platform == "nintendo entertainment system":
            platform = "nes"

        return platform

    length_error = "Error: rom info too short, bad page?"

    if category == "hacks":
        if len(rom_info) != 12:
            print(length_error)
            exit(1)

        modified = rom_info[11]
        platform = get_platform(rom_info[3].lower())
        version = rom_info[7]

    if category == "translations":
        if len(rom_info) != 14:
            print(length_error)
            exit(1)

        modified = rom_info[13]
        platform = get_platform(rom_info[4].lower())
        version = rom_info[9]

    return name, id, modified, platform, version, sha1, category


def sigint_handler(signal, frame):
    sys.exit(0)


def add(url):
    name, id, modified, platform, version, sha1, category = get_romhacking(url)

    patches_dict.update({name: {
        "category": category,
        "filename": "",
        "id": id,
        "modified": modified,
        "platform": platform,
        "sha1": sha1.upper(),
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
        local_version = patches_dict[patch]["version"]
        local_date = patches_dict[patch]["modified"]
        url = "https://www.romhacking.net/" + \
            patches_dict[patch]["category"] + "/" + patches_dict[patch]["id"]
        _, _, latest_date, _, latest_version, _, _ = get_romhacking(url)
        if local_version != latest_version or local_date != latest_date:
            if args.update_github:
                github(patch, local_version, latest_version, url)
            else:
                print("Outdated: " + patch)
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

    issue_title = "Update %s" % (romhack_name)
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

    for patch in patches_dict:
        for key in patches_dict[patch]:
            if not patches_dict[patch][key]:
                print("Missing " + key + ": " + patch +
                      " (" + patches_dict[patch]["id"] + ")")
                fail = True

        if patches_dict[patch]["filename"]:
            if not os.path.exists("patches/" + patches_dict[patch]["filename"]):
                print("Missing patch file: " + patches_dict[patch]["filename"])
                fail = True

    if fail:
        exit(1)


signal.signal(signal.SIGINT, sigint_handler)

if __name__ == "__main__":

    # Configure argparse
    description = "Manage rom hacks and check for updates"
    parser = argparse.ArgumentParser(
        description=description)
    parser.add_argument("--config", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--add")
    group.add_argument("--tests", action='store_true')
    group.add_argument("--update", action='store_true')
    group.add_argument("--update-github", action='store_true')
    parser.add_argument("--debug", action='store_true')

    args = parser.parse_args()

    # Read json to dictionary
    if os.path.exists(str(args.config)):
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
