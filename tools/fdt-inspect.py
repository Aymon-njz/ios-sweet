#!/usr/bin/env python3
"""Print selected properties from a flattened device tree.

This intentionally has no third-party dependency: it is used when bringing a
new Qualcomm board up and the only available hardware description is the FDT
that its booted Android kernel exposes at /sys/firmware/fdt.
"""
import argparse
import struct
from pathlib import Path

MAGIC = 0xD00DFEED
BEGIN_NODE, END_NODE, PROP, NOP, END = 1, 2, 3, 4, 9


def align4(value):
    return (value + 3) & ~3


def cstring(blob, offset):
    end = blob.index(b"\0", offset)
    return blob[offset:end].decode("ascii", "replace")


def cells(value):
    if len(value) % 4:
        return value.hex()
    return " ".join(f"0x{part:08x}" for part in struct.unpack(f">{len(value) // 4}I", value))


def printable(value):
    if not value:
        return "<empty>"
    if value.endswith(b"\0"):
        parts = value[:-1].split(b"\0")
        if all(part and all(32 <= byte < 127 for byte in part) for part in parts):
            return " | ".join(part.decode() for part in parts)
    return cells(value)


def parse(path):
    blob = Path(path).read_bytes()
    magic, total, off_struct, off_strings, off_rsvmap, version, last, boot_cpu, size_strings, size_struct = struct.unpack_from(
        ">10I", blob
    )
    if magic != MAGIC or total > len(blob):
        raise ValueError(f"{path}: not a complete FDT")
    struct_block = blob[off_struct:off_struct + size_struct]
    strings = blob[off_strings:off_strings + size_strings]
    offset, stack, nodes = 0, [], []
    current = None
    while offset < len(struct_block):
        token, = struct.unpack_from(">I", struct_block, offset)
        offset += 4
        if token == BEGIN_NODE:
            name = cstring(struct_block, offset)
            offset = align4(offset + len(name) + 1)
            stack.append(name)
            current = {"path": "/" + "/".join(part for part in stack if part), "props": {}}
            nodes.append(current)
        elif token == END_NODE:
            stack.pop()
            current = None
        elif token == PROP:
            length, nameoff = struct.unpack_from(">II", struct_block, offset)
            offset += 8
            value = struct_block[offset:offset + length]
            offset = align4(offset + length)
            if current is not None:
                current["props"][cstring(strings, nameoff)] = value
        elif token == NOP:
            continue
        elif token == END:
            break
        else:
            raise ValueError(f"{path}: invalid FDT token {token} at {offset - 4:#x}")
    return nodes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dtb")
    parser.add_argument("--match", action="append", default=[], help="case-insensitive substring of a node path or compatible value")
    parser.add_argument("--property", action="append", default=["compatible", "reg", "interrupts", "interrupt-names", "status"], help="property to print; repeatable")
    args = parser.parse_args()
    wanted = set(args.property)
    for node in parse(args.dtb):
        compatible = printable(node["props"].get("compatible", b""))
        haystack = f'{node["path"]} {compatible}'.lower()
        if args.match and not any(match.lower() in haystack for match in args.match):
            continue
        selected = [(name, value) for name, value in node["props"].items() if name in wanted]
        if selected:
            print(node["path"])
            for name, value in selected:
                print(f"  {name}: {printable(value)}")


if __name__ == "__main__":
    main()
