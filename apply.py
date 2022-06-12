#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import sys


def get_hash(rom_path):
    file_hash = hashlib.sha1(pathlib.Path(
        rom_path).read_bytes()).hexdigest()

    return file_hash


def apply_patch(rom_path, patch_path, output_path):
    try:
        command = ["flips", "--apply", patch_path,
                   rom_path, output_path]
        command_output = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT
        ).decode(encoding="UTF-8").split("\n")
        # print("\n".join(command_output))
    except subprocess.CalledProcessError as e:
        print(command)
        print("\n".join(e.output.decode().split("\n")))
        exit(1)


def get_roms_dict(roms_dir):
    roms_dir = pathlib.Path(roms_dir)
    rom_files = list(roms_dir.rglob("*.gb*")) +\
        list(roms_dir.rglob("*.nes"))

    # Populate roms dictionary with found files respective metadata
    roms_dict = {}
    for rom_path in rom_files:
        if pathlib.Path(rom_path).is_file():
            roms_dict.update({get_hash(pathlib.Path(rom_path).as_posix()): {
                "rom_path": pathlib.Path(rom_path).as_posix(),
            }})

    patches_dict_copy = patches_dict.copy()

    for category in patches_dict:
        for patch in patches_dict[category]:
            for hash in roms_dict:
                if patches_dict[category][patch]["sha1"].upper() == hash.upper():
                    rom_path = roms_dict[hash]["rom_path"]
                    patches_dict_copy[category][patch]["rom_path"] = rom_path
                    patches_dict_copy[category][patch]["extension"] = pathlib.Path(
                        rom_path).suffix
                    patches_dict_copy[category][patch]["rom_filename"] = pathlib.Path(
                        rom_path).name

    #print(json.dumps(patches_dict_copy, sort_keys=True, indent=4))

    return patches_dict_copy


def patch_roms():
    roms_dict = get_roms_dict(args.roms_dir)

    for category in roms_dict:
        for rom in roms_dict[category]:
            # Only patch roms with matching patch
            if roms_dict[category][rom]["filename"] and "rom_path" in roms_dict[category][rom]:
                count = 1
                length = len(roms_dict[category][rom]["filename"])
                input_path = ""
                for path in roms_dict[category][rom]["filename"]:
                    # Input patch
                    patch_path = pathlib.Path(args.patches_dir, path)

                    if count == length:
                        game = roms_dict[category][rom]["game"]
                        name = roms_dict[category][rom]["name"]
                        version = roms_dict[category][rom]["version"]
                        extension = roms_dict[category][rom]["extension"]
                        output_name = game + ": " + name + " patched " + version + extension
                    else:
                        output_name = "output" + str(count) + ".tmp"

                    # Output patched rom
                    output_dir = pathlib.Path(
                        args.output_dir, roms_dict[category][rom]["platform"])
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_path = pathlib.Path(
                        output_dir, output_name)

                    # Patch rom
                    if not input_path:
                        input_path = roms_dict[category][rom]["rom_path"]

                    if pathlib.Path(input_path).is_file():
                        apply_patch(input_path,
                                    patch_path, output_path)
                        input_path = output_path

                        # Clean up temporary files
                        if count == length:
                            tmp_glob = output_dir.glob("*.tmp")
                            for tmp_file in tmp_glob:
                                os.remove(tmp_file)
                            print("Success! " + output_path.name)
                        else:
                            count += 1


def sigint_handler():
    sys.exit(0)


signal.signal(signal.SIGINT, sigint_handler)

if __name__ == "__main__":
    # Configure argparse
    description = "Manage rom hacks and check for updates"
    parser = argparse.ArgumentParser(
        description=description)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--patches-dir", required=True)
    parser.add_argument("--roms-dir", required=True)

    args = parser.parse_args()

    # Read json to dictionary
    if os.path.exists(args.config) and os.stat(args.config).st_size != 0:
        patches_file = open(args.config)
        patches_dict = json.load(patches_file)
    else:
        exit(1)

    patch_roms()
