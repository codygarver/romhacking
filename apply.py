#!/usr/bin/env python3

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
    rom_files = glob.glob(roms_dir + "/*.gb*") + \
        glob.glob(roms_dir + "/*.nes")

    # Populate roms dictionary with found files respective metadata
    roms_dict = {}
    for rom_path in rom_files:
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
    root_dir = str(pathlib.Path.home()) + "/romhacking"
    output_dir = root_dir + "/output"
    patches_dir = root_dir + "/patches"
    roms_dir = root_dir + "/roms"

    patches_file = open(root_dir + "/" + "config.json")
    patches_dict = json.load(patches_file)

    roms_dict = get_roms_dict(roms_dir)
    for rom in roms_dict:
        # Only patch roms with matching patch
        if roms_dict[rom]["patch_path"]:
            count = 1
            length = len(roms_dict[rom]["patch_path"])
            input_path = ""
            for path in roms_dict[rom]["patch_path"]:
                # Input patch
                patch_path = patches_dir + "/" + path
                if count == length:
                    output_name = roms_dict[rom]["game"] + \
                        ": " + \
                        roms_dict[rom]["patch_name"] + " patched " + \
                        roms_dict[rom]["version"] + \
                        roms_dict[rom]["extension"]
                else:
                    output_name = "output" + str(count) + ".tmp"
                # Output patched rom
                output_path = output_dir + "/" + \
                    roms_dict[rom]["platform"] + "/" + output_name

                # Patch rom
                if not input_path:
                    input_path = roms_dict[rom]["rom_path"]
                apply_patch(input_path,
                            patch_path, output_path)
                input_path = output_path

                # Clean up temporary files
                if count == length:
                    tmp_glob = glob.glob(
                        output_dir + "/" + roms_dict[rom]["platform"] + "/*.tmp")
                    for tmp_file in tmp_glob:
                        os.remove(tmp_file)
                else:
                    count = count + 1

            # Compress patched rom
            print("Success! " + output_path)
