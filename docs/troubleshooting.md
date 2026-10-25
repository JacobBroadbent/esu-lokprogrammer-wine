# Troubleshooting

## FTDI visible, but LokProgrammer not found

Linux USB enumeration proves that the adapter exists, not that the programmer has external power or that its protocol works. Inspect `udevadm`, `/dev/serial/by-id/`, session groups and read/write permissions. Select COM1 explicitly and make sure its symlink and Wine registry mapping agree. Another adapter may be an Arduino; do not guess from `/dev/ttyUSB0` numbering.

The original Wine-GE 8-26 connection failed before useful communication because .NET rejected the reported maximum baud capability of 131072. The pinned Wine 11.20 runner reports BAUD_USER. The application was observed to probe 921600 baud, time out and communicate at 115200 baud. Do not force a different baud rate based solely on that probe.

## WMI InvalidCastException

Check that Lutris launches **LokProgrammerWineCompat.exe**, not the original application, and that `0Harmony.dll` is beside it. Run the helper's `--check-wmi` mode with the same prefix/runner; this does not open a serial device. The generic JIT-debugging advice in a .NET error dialog is not a repair.

Native Microsoft WMI and `WMIDisableCOMSecurity` were tested in disposable clones during the investigation. They did not provide the working fix and are not part of this setup.

## FileNotFoundException naming the helper assembly

Keep the output basename `LokProgrammerWineCompat.exe` when compiling. The child AppDomain loads its initializer by assembly name. For a test build, use a different **directory**, not a different compiler output filename followed by a rename. Do not rename `0Harmony.dll`.

## Mono enumeration or .NET installation waits

A Winetricks Mono-enumeration pipeline inherited output pipes from Wine background processes and never reached EOF. The setup script downloads and verifies Winetricks 20260125, then replaces that one pipeline with output redirected to a file inside the prefix before grep runs. The local patched file retains the upstream Winetricks license; system Winetricks is untouched.

Winetricks also waits for `wineserver -w` when changing Windows versions. An idle explorer or .NET optimization service may keep it waiting. First inspect the **specific prefix's** task list and installation log. Allow active Microsoft installers and `msiexec` to finish. Do not blindly kill Wine or use a timeout that terminates an active installer.

In the original investigation, after confirming there were no active installers and only idle background processes remained, a prefix-specific `wineserver -k` let the version-change step continue. That is a manual recovery step, never automated by this repo, and must never be used during programming/firmware operations. Keep a backup before experimenting on an existing prefix.

## Apparent freeze or very slow reads

A reading progress window alone does not prove useful communication. The early serial failure blocked even a nominal 200 ms read. The initial finite-timeout workaround then made progress but waited two seconds for short replies. Use the final available-byte version and check actual read progress.

An additional intermittent idle UI/repaint stall was reported after decoder reading worked. The outer window could still resize, and resizing sometimes restored the controls. One WM_NULL check returned immediately. The UI later recovered without a settings change. Its cause remains unresolved.

A Wine virtual-desktop test was prepared but **not performed**. If you try one, first save your project and finish device operations. Back up the Lutris settings, enable a virtual desktop using the classic Wine runner, and ensure the saved application window position lies inside that desktop. Do not report it as a verified fix based on this repo.

## Projects appear missing

A previous failed install may have a different `drive_c`. Use the prefix shown in your working Lutris entry. The optional `map-downloads` command maps the actual Linux Downloads folder as D: in this prefix. Opening an `.esux` file does not require copying it into Program Files. ZIP downloads must be extracted first.

## Rollback

Save the project, finish all decoder operations, and close the application normally.

- Restore a prior helper revision from `PREFIX/lokprogrammer-compat-backups/TIMESTAMP/` by copying its files back beside ESU's executable. Preserve the helper filename.
- To remove the workaround entirely, select the original `LokProgrammer.exe` in Lutris. Its earlier WMI/serial failures can return. Remove only the helper and Harmony files once they are no longer in use.
- The optional D: mapping is a symlink under `PREFIX/dosdevices/d:`. Removing that symlink does not remove Downloads.
- COM1 has both a symlink and an HKLM Wine Ports value; restore both when changing a mapping. The scripts do not delete prefixes or uninstall the ESU application.

## VM fallback

A Windows VM with USB passthrough remains an alternative if a needed operation fails under Wine. No VM is needed to explain the successful reads recorded here. Host-specific VM scripts from the original investigation are deliberately excluded from this repo; configure your virtualization software and pass through the identified FTDI USB device if you take that route.
