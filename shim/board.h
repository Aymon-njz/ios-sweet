#pragma once

/* Board constants needed before XNU has parsed its Apple Device Tree. */
#if defined(ONYX)
#define BOARD_NAME       "onyx"
#define FB_BASE          0xfc800000UL /* live FDT: reserved-memory/splash_region */
#define FB_PHYS          FB_BASE
#define FB_W             1280
#define FB_H             2772
#define FB_STRIDE        (FB_W * 4)
#define GICD_BASE        0x17100000UL /* live FDT: interrupt-controller@17100000 */
#define GICR_BASE        0x17180000UL
#define GICR_SIZE        0x00200000UL
#else
#define BOARD_NAME       "sweet"
#define FB_BASE          0x9c000000UL
#define FB_PHYS          FB_BASE
#define FB_W             1080
#define FB_H             2400
#define FB_STRIDE        (FB_W * 4)
#define GICD_BASE        0x17a00000UL
#define GICR_BASE        0x17a60000UL
#define GICR_SIZE        0x00100000UL
#endif

/* Qualcomm restart registers must be verified separately for every board. */
#define IMEM_RESTART_REASON 0x146aa65cUL
#define PSHOLD              0x0c264000UL
