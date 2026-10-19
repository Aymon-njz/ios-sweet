#!/usr/bin/env python3
"""Repack a header-v4 vendor_boot image with one temporary ramdisk payload.

This is deliberately narrow: it clones a verified stock image, preserves its
DTB and bootconfig, changes the ramdisk size and its sole table descriptor,
and writes a full partition-sized result.  It is for a reversible fastboot
test only; restore the input image immediately after testing.
"""
import argparse
import struct
from pathlib import Path

MAGIC = b"VNDRBOOT"
HEADER_VERSION_OFFSET = 8
PAGE_SIZE_OFFSET = 12
RAMDISK_SIZE_OFFSET = 24
HEADER_SIZE_OFFSET = 2096
DTB_SIZE_OFFSET = 2100
TABLE_SIZE_OFFSET = 2112
TABLE_NUM_OFFSET = 2116
TABLE_ENTRY_SIZE_OFFSET = 2120
BOOTCONFIG_SIZE_OFFSET = 2124


def align(value, page):
    return (value + page - 1) // page * page


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="verified stock vendor_boot image")
    parser.add_argument("ramdisk", help="replacement payload")
    parser.add_argument("output")
    args = parser.parse_args()

    image = bytearray(Path(args.source).read_bytes())
    payload = Path(args.ramdisk).read_bytes()
    if image[:8] != MAGIC or struct.unpack_from("<I", image, HEADER_VERSION_OFFSET)[0] != 4:
        raise SystemExit("source is not a vendor_boot header-v4 image")
    page = struct.unpack_from("<I", image, PAGE_SIZE_OFFSET)[0]
    header_size = struct.unpack_from("<I", image, HEADER_SIZE_OFFSET)[0]
    old_ramdisk_size = struct.unpack_from("<I", image, RAMDISK_SIZE_OFFSET)[0]
    dtb_size = struct.unpack_from("<I", image, DTB_SIZE_OFFSET)[0]
    table_size = struct.unpack_from("<I", image, TABLE_SIZE_OFFSET)[0]
    entries = struct.unpack_from("<I", image, TABLE_NUM_OFFSET)[0]
    entry_size = struct.unpack_from("<I", image, TABLE_ENTRY_SIZE_OFFSET)[0]
    bootconfig_size = struct.unpack_from("<I", image, BOOTCONFIG_SIZE_OFFSET)[0]
    if header_size > page or entries != 1 or entry_size < 8 or table_size < entry_size:
        raise SystemExit("unexpected vendor_boot v4 layout")

    old_ramdisk_offset = page
    old_dtb_offset = align(old_ramdisk_offset + old_ramdisk_size, page)
    old_table_offset = align(old_dtb_offset + dtb_size, page)
    old_bootconfig_offset = align(old_table_offset + table_size, page)
    dtb = bytes(image[old_dtb_offset:old_dtb_offset + dtb_size])
    table = bytearray(image[old_table_offset:old_table_offset + table_size])
    bootconfig = bytes(image[old_bootconfig_offset:old_bootconfig_offset + bootconfig_size])
    if len(dtb) != dtb_size or len(bootconfig) != bootconfig_size:
        raise SystemExit("truncated source image")

    ramdisk_size = len(payload)
    ramdisk_offset = page
    dtb_offset = align(ramdisk_offset + ramdisk_size, page)
    table_offset = align(dtb_offset + dtb_size, page)
    bootconfig_offset = align(table_offset + table_size, page)
    end = bootconfig_offset + bootconfig_size
    if end > len(image):
        raise SystemExit("replacement payload does not fit the partition")

    struct.pack_into("<I", image, RAMDISK_SIZE_OFFSET, ramdisk_size)
    # vendor_ramdisk_table_entry_v4 begins with size and offset.
    struct.pack_into("<II", table, 0, ramdisk_size, 0)
    image[ramdisk_offset:dtb_offset] = b"\0" * (dtb_offset - ramdisk_offset)
    image[ramdisk_offset:ramdisk_offset + ramdisk_size] = payload
    image[dtb_offset:dtb_offset + dtb_size] = dtb
    image[table_offset:table_offset + table_size] = table
    image[bootconfig_offset:bootconfig_offset + bootconfig_size] = bootconfig
    Path(args.output).write_bytes(image)
    print(f"ramdisk={ramdisk_size} dtb_offset={dtb_offset:#x} table_offset={table_offset:#x} output={len(image)}")


if __name__ == "__main__":
    main()
