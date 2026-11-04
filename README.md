# hakuX-Linux

> **This is a fork.** It carries the AArch64 Linux / libretro port of hakuX
> ([PR #9](https://github.com/rfandango/hakuX/pull/9) by [portare-ch](https://github.com/portare-ch/hakuX))
> on top of hakuX 1.3.0, with small Linux fixes, for handhelds running [ROCKNIX](https://rocknix.org)
> (it is the Xbox core used by [pocket-ui](https://github.com/robbyczgw-cla/pocket-ui)).
> hakuX itself is by [rfandango](https://github.com/rfandango/hakuX) and stays GPL-3.0; please report
> Android issues there. Fixes that help everyone are offered back upstream.
> Branch `linux-1.3.0`; build and test notes: `docs/` (libretro section).

# hakuX

hakuX runs original Xbox games on Android (arm64), tuned for Adreno GPUs.

Its core runs the game's x86 code on a JIT (a FEX fork) under a
reimplementation of the Xbox kernel, and draws by decoding the push buffer
the game's own Direct3D sends the NV2A into Vulkan. Audio is the MCPX APU,
ported from xemu.

## hakuX is free

hakuX is free, and always will be. The only official download is
[hakuX's GitHub releases](https://github.com/rfandango/hakuX/releases).

If you paid for hakuX in any way, shape or form, you were scammed. That
includes a store purchase, a subscription, an in-app unlock, a "premium"
build, or an app that repackages it. Ask for a refund wherever you paid, and
get hakuX here for free.

## Requirements

- An arm64 Android device with Vulkan. Custom Turnip drivers can be loaded
  for Adreno GPUs.
- Your own game images (ISO or XISO), dumped from discs you own.

No BIOS, MCPX ROM or hard disk image is needed. hakuX doesn't include any
copyrighted Xbox software.

## Building

See [android/README.md](android/README.md). The RetroArch core for AArch64 Linux,
with how to build and test it, is in [native/libretro/README.md](native/libretro/README.md).

## License

hakuX is free software under the GNU General Public License, version 3 or
later ([COPYING](COPYING)): anyone who distributes it, or a work based on it,
must make the complete source available under the same license. The code
ported from xemu (the MCPX APU) and the third-party components keep their
own licenses, listed in [LICENSE](LICENSE) and [licenses/](licenses/).

## Notes

- hakuX is not affiliated with Microsoft.
