#!/bin/bash
# Build the shim. --onyx writes an Android boot v4 image for temporary boot.
set -euo pipefail
cd "$(dirname "$0")"
target=${1:-}
payload=${2:-}
if [ "$target" = "--onyx" ] || [ "$target" = "--onyx-v2" ]; then
	board=ONYX
else
	board=SWEET
	payload=$target
fi
CC=${CC:-$(command -v aarch64-elf-gcc || command -v aarch64-linux-gnu-gcc)}
OBJCOPY=${OBJCOPY:-$(command -v aarch64-elf-objcopy || command -v aarch64-linux-gnu-objcopy)}
CFLAGS="-O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only -mstrict-align -fno-stack-protector -Wall -Wextra"
mkdir -p out
for f in start.S shim.c console.c mmu.c fdt.c loader.c ufs.c; do
	$CC $CFLAGS -D$board -c $f -o out/${f%.*}.o
done
# The image runs wherever ABL puts it with no relocation pass: only the
# header's image_size (start.o, linked at 0) may be an absolute address.
abs=$($CC -print-prog-name=readelf -r out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/ufs.o | grep -c ABS64 || true)
[ "$abs" = 0 ] || { echo "error: $abs absolute relocations in C objects" >&2; exit 1; }
$CC $CFLAGS -D$board -static -T shim.ld -Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N \
	out/start.o out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/ufs.o -o out/shim.elf
$OBJCOPY -O binary out/shim.elf out/Image
# ABL copies the file; pad to image_size so .bss/stacks exist as zeroed bytes.
size=$(python3 - <<'PY'
import subprocess
nm = subprocess.check_output(['aarch64-elf-nm', 'out/shim.elf'], text=True)
print(int(next(line.split()[0] for line in nm.splitlines() if line.split()[-1] == '_end'), 16))
PY
)
truncate -s "$size" out/Image
# Ramdisk: an xnu payload (tools/mkpayload.py) if given as $1, else an empty
# newc cpio (ABL dislikes a zero-size ramdisk on some builds) -> diagnostics.
if [ -n "$payload" ]; then
	cp "$payload" out/ramdisk.bin
else
	(cd out && rm -rf rd && mkdir rd && cd rd && find . | cpio -o -H newc --quiet | gzip -9 > ../ramdisk.bin)
fi
if [ "$target" = "--onyx" ]; then
	python3 ../tools/mkbootimg4.py --kernel out/Image --ramdisk out/ramdisk.bin \
		--cmdline "console=null" --output out/onyx-shim-boot.img
elif [ "$target" = "--onyx-v2" ]; then
	python3 ../tools/mkbootimg2.py --kernel out/Image --ramdisk out/ramdisk.bin \
		--dtb ../backup/onyx-2026-10-18/vendor_boot.dtb \
		--cmdline "console=null" --output out/onyx-shim-boot-v2.img
else
	mkbootimg --header_version 2 --kernel out/Image --ramdisk out/ramdisk.bin \
		--dtb ../dtb/boot_unpacked/dtb --base 0 --kernel_offset 0x8000 --ramdisk_offset 0x1000000 \
		--tags_offset 0x100 --dtb_offset 0x1f00000 --pagesize 4096 \
		--os_version 17.0.0 --os_patch_level 2035-06 \
		--cmdline "console=null" -o out/shim-boot.img
fi
# Host render of the console layout.
gcc -O1 -Wall -o out/host_test console.c host_test.c && ./out/host_test
ls -l out/Image out/*shim-boot.img
