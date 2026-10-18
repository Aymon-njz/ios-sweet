#!/usr/bin/env python3
"""Create the Android boot image v2 format used by the original shim.

Unlike header v4, v2 carries its own DTB and ramdisk.  It is kept as an
Onyx temporary-boot fallback because Qualcomm ABL otherwise sources the
ramdisk solely from the installed vendor_boot partition.
"""
import argparse
import struct
from pathlib import Path

MAGIC = b"ANDROID!"
PAGE_SIZE = 4096
HEADER_SIZE = 1660


def padded(blob):
    return blob + b"\0" * ((-len(blob)) % PAGE_SIZE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel", required=True)
    parser.add_argument("--ramdisk", required=True)
    parser.add_argument("--dtb", required=True)
    parser.add_argument("--cmdline", default="console=null")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    kernel = Path(args.kernel).read_bytes()
    ramdisk = Path(args.ramdisk).read_bytes()
    dtb = Path(args.dtb).read_bytes()
    cmdline = args.cmdline.encode("ascii")
    if len(cmdline) >= 1536:
        raise SystemExit("command line exceeds Android boot v2 limit")
    header = bytearray(HEADER_SIZE)
    header[:8] = MAGIC
    # Kernel/ramdisk addresses reproduce the active vendor_boot header.
    struct.pack_into("<10I", header, 8, len(kernel), 0x8000, len(ramdisk),
                     0x1000000, 0, 0, 0x100, PAGE_SIZE, 0, 0)
    struct.pack_into("<I", header, 48, 0)  # os_version
    header[64:64 + min(len(cmdline), 512)] = cmdline[:512]
    header[608:608 + max(0, len(cmdline) - 512)] = cmdline[512:]
    struct.pack_into("<I", header, 1632, 0)  # recovery_dtbo_size
    struct.pack_into("<QIIQ", header, 1636, 0, HEADER_SIZE, len(dtb), 0x1f00000)
    Path(args.output).write_bytes(padded(header) + padded(kernel) + padded(ramdisk) + padded(dtb))


if __name__ == "__main__":
    main()
