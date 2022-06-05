#!/usr/bin/env python3

import argparse
import glob
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
    rom_files = glob.glob(roms_dir + "/**/*.gb*", recursive=True) + \
        glob.glob(roms_dir + "/**/*.nes", recursive=True)

    # Populate roms dictionary with found files respective metadata
    roms_dict = {}
    for rom_path in rom_files:
        if pathlib.Path(rom_path).is_file():
            roms_dict.update({pathlib.Path(rom_path).stem: {
                "extension": pathlib.Path(rom_path).suffix,
                "filename": pathlib.Path(rom_path).name,
                "game": "",
                "patch_name": "",
                "patch_path": "",
                "platform": "",
                "rom_path": rom_path,
                "sha1": get_hash(rom_path),
                "version": "",
            }})

    # Match roms by hash with known patch paths
    for rom in roms_dict:
        for category in patches_dict:
            for patch in patches_dict[category]:
                # Compare rom sha1 hash sum against patch's required hash
                if roms_dict[rom]["sha1"].upper() == patches_dict[category][patch]["sha1"].upper():
                    # Add match's game's name to roms dictionary
                    roms_dict[rom]["game"] = patches_dict[category][patch]["game"]
                    # Add match's patch name to roms dictionary
                    roms_dict[rom]["patch_name"] = patches_dict[category][patch]["name"]
                    # Add match's patch path to roms dictionary
                    roms_dict[rom]["patch_path"] = patches_dict[category][patch]["filename"]
                    # Add match's patch platform to roms dictionary
                    roms_dict[rom]["platform"] = patches_dict[category][patch]["platform"]
                    # Add match's patch version to roms dictionary
                    roms_dict[rom]["version"] = patches_dict[category][patch]["version"]

    # print(json.dumps(roms_dict, sort_keys=True, indent=4))

    return roms_dict


def sigint_handler(signal, frame):
    sys.exit(0)


signal.signal(signal.SIGINT, sigint_handler)

if __name__ == "__main__":
    # Configure argparse
    description = "Manage rom hacks and check for updates"
    parser = argparse.ArgumentParser(
        description=description)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--roms-dir", required=True)
    parser.add_argument("--patches-dir", required=True)

    args = parser.parse_args()

    # Read json to dictionary
    if os.path.exists(args.config) and os.stat(args.config).st_size != 0:
        patches_file = open(args.config)
        patches_dict = json.load(patches_file)
    else:
        exit(1)

    roms_dict = get_roms_dict(args.roms_dir)
    for rom in roms_dict:
        # Only patch roms with matching patch
        if roms_dict[rom]["patch_path"]:
            count = 1
            length = len(roms_dict[rom]["patch_path"])
            input_path = ""
            for path in roms_dict[rom]["patch_path"]:
                # Input patch
                patch_path = args.patches_dir + "/" + path
                if count == length:
                    output_name = roms_dict[rom]["game"] + \
                        ": " + \
                        roms_dict[rom]["patch_name"] + " patched " + \
                        roms_dict[rom]["version"] + \
                        roms_dict[rom]["extension"]
                else:
                    output_name = "output" + str(count) + ".tmp"
                # Output patched rom
                output_path = args.output_dir + "/" + \
                    roms_dict[rom]["platform"] + "/" + output_name

                # Patch rom
                if not input_path:
                    input_path = roms_dict[rom]["rom_path"]

                if pathlib.Path(input_path).is_file():
                    apply_patch(input_path,
                                patch_path, output_path)
                    input_path = output_path

                    # Clean up temporary files
                    if count == length:
                        tmp_glob = glob.glob(
                            args.output_dir + "/" + roms_dict[rom]["platform"] + "/*.tmp")
                        for tmp_file in tmp_glob:
                            os.remove(tmp_file)
                        print("Success! " + output_path)
                    else:
                        count = count + 1
