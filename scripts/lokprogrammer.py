#!/usr/bin/env python3
"""Explicit setup steps for the documented LokProgrammer/Wine experiment."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / 'dependencies.json').read_text())
DATA = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
DEFAULT_PREFIX = DATA / 'lutris/prefixes/esu-lokprogrammer'
DEFAULT_WINE = DATA / 'lutris/runners/wine' / LOCK['wine']['directory'] / 'bin/wine'


def sha256(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def download(key):
    item = LOCK[key]
    dest = ROOT / '.cache' / Path(item['url']).name
    dest.parent.mkdir(exist_ok=True)
    if not dest.exists() or sha256(dest) != item['sha256']:
        partial = dest.with_suffix(dest.suffix + '.partial')
        print('Downloading', item['url'], flush=True)
        try:
            request = urllib.request.Request(item['url'], headers={'User-Agent': 'lokprogrammer-wine/0.1'})
            with urllib.request.urlopen(request, timeout=90) as response, partial.open('wb') as f:
                shutil.copyfileobj(response, f)
            if sha256(partial) != item['sha256']:
                raise RuntimeError('SHA-256 mismatch: ' + str(partial))
            partial.replace(dest)
        finally:
            partial.unlink(missing_ok=True)
    return dest


def harmony():
    package = download('harmony')
    dest = ROOT / '.cache/harmony'
    dest.mkdir(exist_ok=True)
    with zipfile.ZipFile(package) as z:
        for member, name in [('lib/net472/0Harmony.dll', '0Harmony.dll'), ('LICENSE', 'Harmony-LICENSE.txt')]:
            (dest / name).write_bytes(z.read(member))
    return dest


def env_for(args):
    env = os.environ.copy()
    env.update(WINEPREFIX=str(args.prefix), WINEARCH='win32', WINEDEBUG='-all',
               WINE=str(args.wine), WINESERVER=str(args.wine.parent / 'wineserver'))
    env['PATH'] = str(args.wine.parent) + os.pathsep + env.get('PATH', '')
    return env


def wine(args, *words, capture=False, extra=None):
    env = env_for(args)
    if extra:
        env.update(extra)
    return subprocess.run([str(args.wine), *map(str, words)], env=env, check=True,
                          text=True, capture_output=capture)


def require_prefix(args):
    registry = args.prefix / 'system.reg'
    if not registry.is_file() or '#arch=win32' not in registry.read_text(errors='replace')[:300]:
        raise RuntimeError('Expected an initialized win32 prefix. Use a separate prefix and init-prefix.')


def winpath(args, path):
    # A normal Wine prefix maps Z: to /. Do not silently alter an existing drive.
    if (args.prefix / 'dosdevices/z:').resolve() != Path('/'):
        raise RuntimeError('Build/setup commands require Wine\'s normal Z: -> / mapping.')
    return 'Z:' + str(Path(path).resolve()).replace('/', '\\')


def application(args):
    if args.app_dir:
        folder = args.app_dir
        if not (folder / 'LokProgrammer.exe').is_file():
            raise RuntimeError('No LokProgrammer.exe in --app-dir')
        return folder
    matches = list((args.prefix / 'drive_c').glob('Program Files*/**/LokProgrammer.exe'))
    if len(matches) != 1:
        raise RuntimeError('Expected one LokProgrammer.exe; install ESU first or specify --app-dir.')
    return matches[0].parent


def require_closed(args):
    result = wine(args, 'tasklist', '/FO', 'CSV', '/NH', capture=True)
    for row in csv.reader(result.stdout.splitlines()):
        if row and row[0].casefold() in {'lokprogrammer.exe', 'lokprogrammerwinecompat.exe'}:
            raise RuntimeError('Save your project, finish device operations and close LokProgrammer first.')


def validate_link(link, target, replace=False):
    target = Path(target).absolute()
    if link.is_symlink() and os.readlink(link) == str(target):
        return
    if link.exists() or link.is_symlink():
        if not replace or not link.is_symlink():
            raise RuntimeError('Existing mapping retained: ' + str(link) + '; use --replace to replace a symlink.')


def set_link(link, target, replace=False):
    target = Path(target).absolute()
    validate_link(link, target, replace)
    if link.is_symlink() and os.readlink(link) == str(target):
        return
    if link.is_symlink():
        link.unlink()
    link.symlink_to(target, target_is_directory=target.is_dir())


def configure_port_mapping(args, device):
    link = args.prefix / 'dosdevices/com1'
    validate_link(link, device, args.replace)
    # Launching reg may cause Wine to regenerate old automatic mappings first.
    # Commit the registry value, then install the stable alias as the final step.
    wine(args, 'reg', 'add', r'HKLM\Software\Wine\Ports', '/v', 'COM1', '/t', 'REG_SZ', '/d', str(device), '/f')
    set_link(link, device, replace=True)


def inspect(args):
    print('Prefix:', args.prefix)
    print('Wine:', args.wine)
    for path in sorted(Path('/dev/serial/by-id').glob('*')):
        print('Serial:', path, '->', path.resolve(),
              'read/write=' + str(os.access(path, os.R_OK | os.W_OK)))
        if shutil.which('udevadm'):
            result = subprocess.run(['udevadm', 'info', '--query=property', '--name', str(path)],
                                    capture_output=True, text=True)
            print('\n'.join('  ' + line for line in result.stdout.splitlines()
                            if line.startswith(('ID_VENDOR_ID=', 'ID_MODEL_ID=', 'ID_MODEL='))))
    for name in ['com1', 'c:', 'd:', 'z:']:
        path = args.prefix / 'dosdevices' / name
        if path.is_symlink():
            print(name, '->', os.readlink(path))
    if hasattr(os, 'getgroups'):
        import grp
        print('Session groups:', ', '.join(grp.getgrgid(g).gr_name for g in os.getgroups()))


def fetch_runner(args):
    parent = DATA / 'lutris/runners/wine'
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / LOCK['wine']['directory']
    if target.exists():
        print('Existing runner retained:', target)
        return
    archive = download('wine')
    with tempfile.TemporaryDirectory(dir=parent, prefix='.lokprogrammer-') as tmp:
        with tarfile.open(archive) as tar:
            tar.extractall(tmp, filter='data')
        shutil.move(str(Path(tmp) / LOCK['wine']['directory']), target)
    print('Installed pinned runner:', target)


def init_prefix(args):
    if args.prefix.exists() and any(args.prefix.iterdir()):
        raise RuntimeError('Refusing to initialize a nonempty prefix.')
    args.prefix.mkdir(parents=True, exist_ok=True)
    wine(args, 'wineboot', '-u', extra={'WINEDLLOVERRIDES': 'winegstreamer=;mscoree,mshtml='})
    require_prefix(args)
    print('Created win32 prefix. Next: install-dotnet. No adapter mapping changed.')


def install_dotnet(args):
    require_prefix(args)
    require_closed(args)
    upstream = download('winetricks')
    text = upstream.read_text()
    old = '''        mono_uuid="$(WINEDEBUG=-all "${WINE_ARCH}" uninstaller --list 2>&1 | grep "${mono_installer_desc}" | cut -f1 -d\\|)"'''
    new = '''        WINEDEBUG=-all "${WINE_ARCH}" uninstaller --list > "${WINEPREFIX}/winetricks-mono-list.txt" 2>&1
        mono_uuid="$(grep "${mono_installer_desc}" "${WINEPREFIX}/winetricks-mono-list.txt" | cut -f1 -d\\|)"'''
    if text.count(old) != 1:
        raise RuntimeError('Pinned Winetricks Mono listing did not match; refusing an unverified patch.')
    patched = ROOT / '.cache/winetricks-local'
    patched.write_text(text.replace(old, new))
    patched.chmod(0o755)
    print('Installing native .NET 4.8 with pinned Winetricks; see docs/troubleshooting.md for idle restart waits.', flush=True)
    subprocess.run([str(patched), '-q', 'dotnet48'], env=env_for(args), check=True)
    wine(args, 'winecfg', '-v', 'win10')


def install_esu(args):
    require_prefix(args)
    require_closed(args)
    if not args.installer.is_file():
        raise RuntimeError('Installer does not exist.')
    wine(args, winpath(args, args.installer), '/S')
    print('Installer finished. Installed folder:', application(args))


def map_port(args):
    require_prefix(args)
    require_closed(args)
    device = Path(os.path.abspath(args.device.expanduser()))
    if device.parent != Path('/dev/serial/by-id') or not device.exists():
        raise RuntimeError('Supply an existing /dev/serial/by-id/ device, not a ttyUSB number.')
    if not os.access(device, os.R_OK | os.W_OK):
        raise RuntimeError('No read/write device access; check uucp membership and the current login session.')
    if shutil.which('udevadm'):
        result = subprocess.run(['udevadm', 'info', '--query=property', '--name', str(device)],
                                capture_output=True, text=True, check=True)
        if 'ID_VENDOR_ID=0403' not in result.stdout.splitlines():
            raise RuntimeError('This helper targets FTDI adapters; selected device is not identified as FTDI (0403).')
    configure_port_mapping(args, device)
    print('COM1 mapped to', device)


def build(args):
    require_prefix(args)
    deps = harmony()
    dest = ROOT / 'build'
    dest.mkdir(exist_ok=True)
    output = dest / 'LokProgrammerWineCompat.exe'
    # Filename matters: a child AppDomain resolves the launcher's assembly name.
    sources = [ROOT / 'src' / n for n in ['LokProgrammerWineCompat.cs', 'WmiDirectScopeCheck.cs', 'SerialTimeoutCompat.cs']]
    wine(args, r'C:\windows\Microsoft.NET\Framework\v4.0.30319\csc.exe',
         '/nologo', '/platform:x86', '/reference:System.Management.dll',
         '/reference:' + winpath(args, deps / '0Harmony.dll'), '/main:LokProgrammerWineCompat',
         '/out:' + winpath(args, output), *[winpath(args, p) for p in sources])
    for name in ['0Harmony.dll', 'Harmony-LICENSE.txt']:
        shutil.copy2(deps / name, dest / name)
    (dest / 'SHA256SUMS').write_text(''.join(sha256(p) + '  ' + p.name + '\n'
        for p in sorted(dest.iterdir()) if p.name != 'SHA256SUMS' and p.is_file()))
    print('Built', output)


def install_helper(args):
    require_prefix(args)
    require_closed(args)
    folder = application(args)
    sources = [ROOT / 'build' / n for n in ['LokProgrammerWineCompat.exe', '0Harmony.dll', 'Harmony-LICENSE.txt']]
    if not all(p.is_file() for p in sources):
        raise RuntimeError('Build first; helper/dependency files are missing.')
    backup = args.prefix / 'lokprogrammer-compat-backups' / str(time.time_ns())
    for source in sources:
        target = folder / source.name
        if target.exists():
            backup.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup / target.name)
        shutil.copy2(source, target)
    config = folder / 'LokProgrammer.exe.config'
    if not config.exists():
        shutil.copy2(ROOT / 'config/LokProgrammer.exe.config', config)
    print('Installed helper beside unchanged ESU executable:', folder)
    if backup.exists():
        print('Previous helper files backed up:', backup)


def lutris_config(args):
    folder = application(args)
    config = {
        'game': {'arch': 'win32', 'exe': str(folder / 'LokProgrammerWineCompat.exe'),
                 'prefix': str(args.prefix), 'working_dir': str(folder)},
        'system': {'disable_runtime': True},
        'wine': {'version': args.wine.parent.parent.name, 'dxvk': False, 'dxvk_nvapi': False,
                 'vkd3d': False, 'esync': False, 'fsync': False, 'show_debug': '-all'}}
    # JSON is valid YAML and quotes paths correctly. This is a configuration
    # reference, not a Lutris installer: follow the README's local-game steps.
    output = ROOT / 'build/lutris-game.yml'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(config, indent=2) + '\n')
    print('Local-game settings reference (not an import installer):', output)


def downloads(args):
    require_prefix(args)
    folder = args.folder.expanduser().resolve()
    if not folder.is_dir():
        raise RuntimeError('Downloads folder does not exist.')
    set_link(args.prefix / 'dosdevices/d:', folder, args.replace)
    print('Wine D: ->', folder)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', type=Path, default=DEFAULT_PREFIX)
    parser.add_argument('--wine', type=Path, default=DEFAULT_WINE)
    parser.add_argument('--app-dir', type=Path)
    commands = parser.add_subparsers(dest='command', required=True)
    actions = {'inspect': inspect, 'fetch-runner': fetch_runner, 'init-prefix': init_prefix,
               'install-dotnet': install_dotnet, 'build': build, 'install-helper': install_helper,
               'lutris-config': lutris_config, 'fetch-harmony': lambda args: print(harmony())}
    for name, action in actions.items():
        commands.add_parser(name).set_defaults(action=action)
    command = commands.add_parser('install-esu')
    command.add_argument('installer', type=Path)
    command.set_defaults(action=install_esu)
    command = commands.add_parser('map-port')
    command.add_argument('device', type=Path)
    command.add_argument('--replace', action='store_true')
    command.set_defaults(action=map_port)
    command = commands.add_parser('map-downloads')
    command.add_argument('--folder', type=Path, default=Path.home() / 'Downloads')
    command.add_argument('--replace', action='store_true')
    command.set_defaults(action=downloads)
    args = parser.parse_args(argv)
    args.prefix = args.prefix.expanduser().resolve()
    args.wine = args.wine.expanduser().resolve()
    if args.app_dir:
        args.app_dir = args.app_dir.expanduser().resolve()
    if hasattr(os, 'geteuid') and os.geteuid() == 0 and args.command != 'inspect':
        parser.error('Run as your ordinary user, not root.')
    try:
        args.action(args)
    except (RuntimeError, OSError, subprocess.CalledProcessError, tarfile.TarError, zipfile.BadZipFile) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
