#!/usr/bin/env python3

from bs4 import BeautifulSoup
import glob
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import zipfile


def extract(rom_path):
    # Only attempt to extract zip files
    if pathlib.Path(rom_path).suffix == ".zip":
        # Extract zip to temp dir
        tmp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(rom_path, "r") as zip_ref:
            zip_ref.extractall(tmp_dir)

        # Get the (first) file with a known extension in temp dir
        rom_glob = glob.glob(tmp_dir + "/*.gb*") + \
            glob.glob(tmp_dir + "/*.nes")
        rom_path = rom_glob[0]

    return rom_path


def compress(rom_path):
    output_dir = pathlib.Path(rom_path).parent
    os.chdir(output_dir)

    # Compress patched rom
    output_zip = pathlib.Path(rom_path).stem + ".zip"
    with zipfile.ZipFile(output_zip, "w") as zip_ref:
        zip_ref.write(os.path.basename(rom_path))

    return output_zip


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
    rom_files = glob.glob(roms_dir + "/*.zip") + \
        glob.glob(roms_dir + "/*.gb*") + \
        glob.glob(roms_dir + "/*.nes")

    # Populate roms dictionary with found files respective metadata
    roms_dict = {}
    for rom_path in rom_files:
        roms_dict.update({pathlib.Path(rom_path).stem: {
            "extension": pathlib.Path(extract(rom_path)).suffix,
            "filename": pathlib.Path(rom_path).name,
            "patch_name": "",
            "patch_path": "",
            "platform": "",
            "rom_path": rom_path,
            "sha1": get_hash(extract(rom_path)),
            "version": "",
        }})

    # Match roms by hash with known patch paths
    for rom in roms_dict:
        for patch in patches_dict:
            # Compare rom sha1 hash sum against patch's required hash
            if roms_dict[rom]["sha1"].upper() == patches_dict[patch]["sha1"].upper():
                # Add match's patch name to roms dictionary
                roms_dict[rom]["patch_name"] = patch
                # Add match's patch path to roms dictionary
                roms_dict[rom]["patch_path"] = patches_dict[patch]["filename"]
                # Add match's patch version to roms dictionary
                roms_dict[rom]["version"] = patches_dict[patch]["version"]
                # Add match's patch platform to roms dictionary
                roms_dict[rom]["platform"] = patches_dict[patch]["platform"]

    #print(json.dumps(roms_dict, sort_keys=True, indent=4))

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
            # Input rom
            rom_path = roms_dict[rom]["rom_path"]
            # Input patch
            patch_path = patches_dir + "/" + roms_dict[rom]["patch_path"]
            # Output patched rom
            output_path = output_dir + "/" + \
                roms_dict[rom]["platform"] + "/" + \
                roms_dict[rom]["patch_name"] + " patched " + \
                roms_dict[rom]["version"] + \
                roms_dict[rom]["extension"]

            # Patch rom
            apply_patch(rom_path, patch_path, output_path)

            # Compress patched rom
            print("Success! " + compress(output_path))

            # Delete uncompressed patched rom
            os.remove(output_path)
