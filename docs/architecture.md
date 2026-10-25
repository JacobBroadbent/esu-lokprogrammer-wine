# Compatibility launcher

Lutris starts Wine, Wine starts `LokProgrammerWineCompat.exe`, and the launcher loads the unchanged `LokProgrammer.exe` in a child .NET AppDomain **inside the same Windows process**. It remains present for the session. There is no separate daemon or replacement ESU protocol implementation.

Harmony 2.3.3 installs in-memory hooks before ESU starts. The normal launch path follows the version that completed the hardware tests. The repository adds a `--check-wmi` path to verify assembly loading and WMI without a serial device.

## WMI connection

The original read failed in `System.StubHelpers.InterfaceMarshaler.ConvertToNative`, reached from `System.Management.SecuredIWbemServicesHandler.ExecQuery_`. The application's captured queries were:

```sql
SELECT Caption, Service FROM Win32_PnpEntity WHERE Caption LIKE '%(COM%'
SELECT Service FROM Win32_PnpEntity WHERE Caption LIKE '%(COM1%'
```

Those exact queries worked in small independent .NET tests but failed inside the application. WMI warm-up and a worker-thread retry did not resolve the failure.

Before `ManagementObjectSearcher.Get()`, the helper calls the local Wine WMI locator directly through COM on the current thread. It wraps the resulting real `IWbemServices` pointer and assigns it to the searcher's `ManagementScope` private `wbemServices` field. The ordinary .NET query then runs. Connections to other machines or with an explicit username are rejected by this narrow helper.

The tested Wine PnP query returned zero matching rows. No FTDI records or query results are fabricated. The direct connection avoided the observed COM-conversion failure; this experiment does not prove every detail of its underlying Wine/CLR cause.

## Serial deadline and available-byte reads

.NET Framework uses `MAXDWORD` values to request Windows' special first-byte timeout mode. Wine 11.20's server serial code calculates an asynchronous total timeout using the multiplier and byte count without implementing that special case. A nominal 200 ms no-data read consequently remained stuck beyond a six-second watchdog.

The first workaround changed native read timeouts to interval=0, multiplier=0 and the requested positive constant. This restored bounded reads but forced each short response to wait for the complete deadline, often two seconds while ESU requested up to 8192 bytes. A 1 ms inter-byte variant returned a timeout after 4 ms in the no-data test, so it was rejected.

The final workaround:

1. Applies a regular finite native read deadline to **COM1** after opening, after SerialPort timeout property changes and before byte-array reads. Native write-timeout values are preserved.
2. Waits for `SerialPort.BytesToRead` to become positive, checking the requested positive deadline and sleeping approximately 1 ms between checks.
3. Limits the original byte-array read's count to the lesser of requested count and currently available bytes.
4. Lets the original .NET read copy the actual bytes and propagate errors.

A partial return is allowed by the SerialPort read contract. The helper leaves ordinary argument validation, zero-count reads, other COM ports and nonpositive/infinite read timeouts to the original method. It does not change ESU commands, baud-rate selection, packet contents, or decoder firmware. It also does not disable the ESU application's write features.

This remains an experimental approximation of Windows timeout behavior. Availability can race with another reader; an original read can then still reach its finite native deadline. Concurrent reads, disconnect recovery, repeated long sessions and write operations have not been exhaustively tested.

## Implementation dependencies

- .NET private `ManagementScope.wbemServices` and `SerialStream._handle` fields.
- `ole32` COM activation and the WMI locator interface.
- `kernel32` Get/SetCommTimeouts through Wine.
- Harmony runtime method patches in this process.

Updating .NET, ESU or Wine can change these assumptions. The launcher must stay beside the ESU executable and `0Harmony.dll`, with its assembly filename retained. The ESU application's existing `.config` is used for its child AppDomain.

Diagnostic logs record query text, timestamps, read counts, settings and wait durations. They do not record packet payloads. The normal WMI log is `%LOCALAPPDATA%\LokProgrammerWineCompat.log`; set `LOKPROGRAMMER_DIAGNOSTIC_LOG` to override it. Serial timing logs are enabled only when `LOKPROGRAMMER_SERIAL_LOG` names a Wine-visible file path. Review logs before sharing them.

## Primary sources

- [Wine 11.20 serial capabilities](https://github.com/wine-mirror/wine/blob/wine-11.20/dlls/ntdll/unix/serial.c)
- [Wine 11.20 asynchronous serial timeouts](https://github.com/wine-mirror/wine/blob/wine-11.20/server/serial.c)
- [Windows COMMTIMEOUTS behavior](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-commtimeouts)
- [.NET Framework SerialStream](https://github.com/microsoft/referencesource/blob/main/System/sys/system/IO/ports/SerialStream.cs)
- [.NET Framework SerialPort](https://github.com/microsoft/referencesource/blob/main/System/sys/system/IO/ports/SerialPort.cs)
- [Harmony](https://github.com/pardeike/Harmony)
