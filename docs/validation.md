# Validation record

Recorded on 24 October 2026. Reports are deliberately limited to what was observed.

## Original hardware session

- Arch Linux, Lutris 0.5.22, KDE Plasma Wayland/XWayland.
- LokProgrammer 5.2.18 build B26120, native .NET Framework 4.8 (Release 528049).
- Dedicated win32 prefix, vanilla Wine 11.20 classic amd64 runner.
- FTDI FT232R, vendor/product 0403:6001, Linux `ftdi_sio`, stable by-id mapping to COM1.
- Current-session `uucp` permissions were already correct; no permission or kernel-driver modification was needed.
- Decoder model and programmer hardware revision were not recorded.

The user confirmed a completed decoder information/data read with the slower helper, then another completed read that was faster with the final helper. The final serial log contained 96 completed reads and 11,993 received bytes over approximately 6.9 seconds, with median availability wait 17.5 ms. Earlier short replies commonly waited two seconds. No controlled Windows baseline was measured.

The standalone checks opened/closed COM1 without transmitting commands, exercised zero-count reads, and checked a no-data 200 ms deadline. A candidate 1 ms inter-byte mode timed out after about 4 ms and was rejected. A helper test-build assembly naming problem was corrected before the faster application's successful read test.

No sound upload, intentional decoder-setting write or firmware update was initiated by the assistant. These operations are unverified. A user's later question about a possible firmware update was withdrawn without confirmation; no update success is claimed. The helper does not disable writing features in ESU's software.

An intermittent idle UI/repaint issue was observed and remains unresolved. No virtual desktop or DPI setting was applied as its fix.

## Repository validation

The repository keeps the successful runtime workarounds and adds non-hardware `--version` and `--check-wmi` diagnostics. The latter loads the initializer in a child AppDomain and runs real WMI queries, catching the assembly-name failure that a parent-only check would miss.

Python tests cover refusing unsafe prefix initialization/mapping replacement, a checksum mismatch, FTDI/device guards and running-application protection. Build checks do not substitute for hardware tests. GitHub CI uses Windows' WMI and has no programmer/decoder attached.

The fresh-prefix replay and build checks performed while assembling the repository are recorded below after completion. Do not infer that an unlisted platform/version or operation has been tested.

## Fresh-prefix replay during repository assembly

A separate fresh win32 prefix was initialized directly with the pinned
Wine 11.20 classic runner. The pinned Winetricks 20260125 script with the
Mono-listing adjustment completed native .NET 4.8 installation with exit 0.
The repository script generated a byte-for-byte identical adjusted script,
then its idempotent dotnet step and Windows 10 selection completed.

The repository's ESU installer step installed 5.2.18 in that disposable
prefix. Its helper installation, COM1 mapping through the selected FTDI
by-id alias, and Lutris-settings generation succeeded. The mapping guard
first refused Wine's existing `/dev/ttyS0` COM1 link; after inspecting it,
the mapping was explicitly replaced in the disposable prefix. The replay
also caught Wine regenerating its automatic link during a registry update;
the script now writes the stable symlink last, with a regression test. The stable symlink
was checked to retain the alias rather than resolve it into a ttyUSB number.
No serial port was opened by those mapping checks.

The repository helper compiled with native .NET's compiler as x86. Its
child-AppDomain/WMI check passed both in the original prefix and in the
fresh installation: one operating-system row and zero matching COM1 PnP
rows under Wine. This check does not transmit decoder commands. A new
hardware read or write was not repeated in the disposable prefix.

Nine Python guard tests passed locally. Windows build/WMI CI is configured
separately; its status must be checked on GitHub, not inferred from the
local Wine checks. Generated build artifacts and machine-specific settings
are ignored by Git and are not committed.
