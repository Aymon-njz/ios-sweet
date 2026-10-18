#!/usr/bin/env python3
"""Create a minimal Android boot image header v4 for `fastboot boot`.

The installed vendor_boot partition continues to supply the board DTB and
vendor ramdisk; this file is temporary and contains only a kernel and ramdisk.
"""
import argparse
import struct
from pathlib import Path

HEADER_VERSION = 4
HEADER_SIZE = 1580
PAGE_SIZE = 4096


def padded(blob):
    return blob + b"\0" * ((-len(blob)) % PAGE_SIZE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel", required=True)
    parser.add_argument("--ramdisk", required=True)
    parser.add_argument("--cmdline", default="console=null")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    kernel = Path(args.kernel).read_bytes()
    ramdisk = Path(args.ramdisk).read_bytes()
    cmdline = args.cmdline.encode("ascii")
    if len(cmdline) >= 1536:
        raise SystemExit("command line exceeds Android boot v4 limit")
    header = bytearray(HEADER_SIZE)
    header[:8] = b"ANDROID!"
    struct.pack_into("<5I", header, 8, len(kernel), len(ramdisk), 0, HEADER_SIZE, 0)
    struct.pack_into("<I", header, 40, HEADER_VERSION)
    header[44:44 + len(cmdline)] = cmdline
    struct.pack_into("<I", header, 1576, 0)  # signature_size
    Path(args.output).write_bytes(padded(header) + padded(kernel) + padded(ramdisk))


if __name__ == "__main__":
    main()
