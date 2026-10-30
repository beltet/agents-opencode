#!/usr/bin/env python3
"""Shared, offline, per-user installer (Python 3.10+, standard library only)."""

import argparse
import ntpath
import os
from pathlib import Path
import shutil
import sys
import tempfile


def broadcast_environment_change():
    """Notify Windows listeners, bounded to two seconds per recipient."""
    import ctypes
    from ctypes import wintypes

    send = ctypes.WinDLL("user32", use_last_error=True).SendMessageTimeoutW
    # WPARAM, LPARAM, LRESULT and DWORD_PTR are pointer-sized on Win64.
    send.argtypes = (wintypes.HWND, wintypes.UINT, ctypes.c_size_t,
                     ctypes.c_ssize_t, wintypes.UINT, wintypes.UINT,
                     ctypes.POINTER(ctypes.c_size_t))
    send.restype = ctypes.c_ssize_t
    message = ctypes.create_unicode_buffer("Environment")
    result = ctypes.c_size_t()
    return bool(send(0xFFFF, 0x001A, 0, ctypes.addressof(message),
                     0x0002, 2000, ctypes.byref(result)))  # SMTO_ABORTIFHUNG


def add_windows_user_path(bin_dir, *, registry=None, expand=None, notify=None):
    """Append only to HKCU Path; return (changed, notification_succeeded).

    Expansion is for comparison only. winreg uses ExpandEnvironmentStringsW,
    not POSIX expansion (which has different syntax/case/unknown-var rules).
    Dependencies are injectable so tests never touch the host registry.
    """
    if registry is None:
        import winreg as registry
    original, value_type = "", registry.REG_SZ
    try:
        with registry.OpenKey(registry.HKEY_CURRENT_USER, "Environment", 0,
                              registry.KEY_QUERY_VALUE) as key:
            try:
                original, value_type = registry.QueryValueEx(key, "Path")
            except FileNotFoundError:
                pass
    except FileNotFoundError:
        pass
    if value_type not in (registry.REG_SZ, registry.REG_EXPAND_SZ) or not isinstance(original, str):
        raise OSError("HKCU\\Environment\\Path must be REG_SZ or REG_EXPAND_SZ; value left unchanged")

    def comparison(entry):
        entry = entry.strip()
        if len(entry) >= 2 and entry[0] == entry[-1] == '"':
            entry = entry[1:-1].strip()
        if value_type == registry.REG_EXPAND_SZ:
            entry = (expand or registry.ExpandEnvironmentStrings)(entry)
        return ntpath.normcase(ntpath.normpath(entry)) if entry else ""

    target = str(bin_dir)
    if comparison(target) in (comparison(entry) for entry in original.split(";")):
        return False, True
    # Keep every existing byte/entry, including whitespace and empty entries.
    updated = original + (";" if original else "") + target
    with registry.CreateKeyEx(registry.HKEY_CURRENT_USER, "Environment", 0,
                              registry.KEY_SET_VALUE) as key:
        registry.SetValueEx(key, "Path", 0, value_type, updated)
    try:
        notified = bool((notify or broadcast_environment_change)())
    except Exception:
        # Notification is best effort; a committed registry write is not undone.
        notified = False
    return True, notified


def install_paths(platform=None, environ=None, home=None):
    """Accept an explicit platform so Windows paths can be tested on POSIX."""
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    if platform == "win32":
        base = Path(environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
        destination = base / "agents-opencode"
        return destination, destination / "bin"
    base = Path(environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    return base / "agents-opencode", Path(environ.get("XDG_BIN_HOME") or home / ".local" / "bin")


def install(source, destination, bin_dir, platform=None):
    """Stage a complete package, promote, then atomically publish its launcher.

    Only a recognized central installation may be replaced. Non-library files,
    including custom profiles, survive upgrades. A previous tree is retained
    until launcher publication succeeds, and restored on failure.
    """
    platform = sys.platform if platform is None else platform
    source, destination, bin_dir = map(Path, (source, destination, bin_dir))
    launcher_name = "agents-opencode.cmd" if platform == "win32" else "agents-opencode"
    launcher = bin_dir / launcher_name
    if not (source / "lib" / "manager.py").is_file():
        raise OSError("Missing source lib/manager.py")
    if destination.is_symlink():
        raise OSError(f"Refusing a symlink installation directory: {destination}")
    if destination.exists() and not (
        destination.is_dir()
        and (destination / "lib" / "manager.py").is_file()
        and (destination / "lib" / "profiles").is_dir()
    ):
        raise OSError(f"Refusing to replace an unrecognized directory: {destination}")
    if source.resolve().is_relative_to(destination.resolve()):
        raise OSError("Installation directory must not contain the source package")
    if launcher.is_symlink() or (launcher.exists() and not launcher.is_file()):
        raise OSError(f"Refusing to replace a non-regular launcher: {launcher}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".agents-opencode-new-", dir=destination.parent))
    previous = stage.with_name(stage.name + ".previous")
    promoted = False
    saved_previous = False
    pending_launcher = None
    try:
        # Preserve personal data and unrelated root entries without following links.
        if destination.exists():
            for entry in destination.iterdir():
                if entry.name == "lib":
                    continue
                target = stage / entry.name
                if entry.is_symlink():
                    target.symlink_to(os.readlink(entry), target_is_directory=entry.is_dir())
                elif entry.is_dir():
                    shutil.copytree(entry, target, symlinks=True)
                else:
                    shutil.copy2(entry, target)
        shutil.copytree(source / "lib", stage / "lib", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("README.md", "START_HAR.md", "START_HERE.md", "AGENT_CAST.md"):
            if (source / name).is_file():
                target = stage / name
                # Do not follow preserved user symlinks when updating product docs.
                if target.is_symlink():
                    target.unlink()
                shutil.copy2(source / name, target)
        # Read the launcher before touching the active installation.
        launcher_data = (source / launcher_name).read_bytes()
        if destination.exists():
            destination.rename(previous)
            saved_previous = True
        stage.rename(destination)
        promoted = True
        bin_dir.mkdir(parents=True, exist_ok=True)
        fd, pending = tempfile.mkstemp(prefix=".agents-opencode-launcher-", dir=bin_dir)
        pending_launcher = Path(pending)
        with os.fdopen(fd, "wb") as stream:
            stream.write(launcher_data)
        if platform != "win32":
            pending_launcher.chmod(0o755)
        os.replace(pending_launcher, launcher)
        pending_launcher = None
    except BaseException:
        # Recovery is best-effort: no secondary filesystem failure may hide the
        # original error or prevent the remaining recovery steps from running.
        def recover(action, description):
            try:
                action()
                return True
            except OSError as error:
                print(f"{description}: {error}", file=sys.stderr)
                return False

        if pending_launcher is not None:
            recover(lambda: pending_launcher.unlink(missing_ok=True),
                    f"Could not remove temporary launcher {pending_launcher}")
        if promoted:
            recover(lambda: destination.rename(stage),
                    f"Could not move failed installation aside at {destination}")
        if saved_previous:
            restored = recover(lambda: previous.rename(destination),
                               f"Could not restore previous installation to {destination}")
            if not restored:
                print(f"Previous installation retained for manual recovery at: {previous}",
                      file=sys.stderr)
        # Never clean up 'previous' on this path: it may be the only recoverable
        # installation. Guard staging cleanup too, preserving the original error.
        def remove_stage():
            if stage.exists():
                shutil.rmtree(stage)

        recover(remove_stage, f"Could not remove staging directory {stage}")
        raise
    # Cleanup failure must not turn a successful publication into a failed install.
    if saved_previous:
        try:
            shutil.rmtree(previous)
        except OSError:
            return launcher, previous
    return launcher, None


def main(argv=None):
    # Language selection precedes help, installation checks, and all filesystem work.
    source = Path(__file__).resolve().parent
    sys.path.insert(0, str(source / "lib"))
    import i18n

    preliminary = argparse.ArgumentParser(add_help=False)
    preliminary.add_argument("--lang")
    options, _ = preliminary.parse_known_args(argv)
    if options.lang in ("sv", "en"):
        i18n.set_language(options.lang)
    else:
        i18n.select_language()
    tr = i18n.tr
    parser = argparse.ArgumentParser(description=tr(
        "Installera agents-opencode för aktuell användare (utan nätverk).",
        "Install agents-opencode for the current user (offline)."))
    parser.add_argument("--lang", choices=("sv", "en"), help=tr("Språk", "Language"))
    parser.add_argument("--no-path", action="store_true", help=tr(
        "Ändra inte användarens PATH i Windows.", "Do not change the Windows user PATH."))
    options = parser.parse_args(argv)
    if sys.version_info < (3, 10):
        print(tr("Python 3.10 eller senare krävs.", "Python 3.10 or later is required."), file=sys.stderr)
        return 1
    destination, bin_dir = install_paths()
    try:
        launcher, backup = install(source, destination, bin_dir)
    except OSError as error:
        print(tr("Installationen misslyckades: ", "Installation failed: ") + str(error), file=sys.stderr)
        return 1
    print(tr("Installerat: ", "Installed: ") + str(launcher))
    if backup is not None:
        print(tr("Tidigare version finns kvar i: ", "Previous version retained at: ") + str(backup))
    status = 0
    if sys.platform == "win32" and not options.no_path:
        try:
            changed, notified = add_windows_user_path(bin_dir)
        except OSError as error:
            print(tr("Installationen finns kvar, men användarens PATH kunde inte uppdateras: ",
                     "Installation retained, but the user PATH could not be updated: ") + str(error),
                  file=sys.stderr)
            print(tr("Lägg till följande mapp i användarens Path under Miljövariabler: ",
                     "Add this folder to the user Path in Environment Variables: ") + str(bin_dir),
                  file=sys.stderr)
            status = 1
        else:
            print(tr("Användarens PATH uppdaterades." if changed else "Mappen finns redan i användarens PATH.",
                     "User PATH updated." if changed else "Folder is already in the user PATH."))
            if not notified:
                print(tr("Varning: Windows kunde inte meddelas om PATH-ändringen. Logga ut och in om det behövs.",
                         "Warning: Windows could not be notified of the PATH change. Sign out and back in if needed."),
                      file=sys.stderr)
    if sys.platform == "win32":
        print(tr("Öppna en ny terminal. Installationen kan inte ändra PATH i den överordnade processen eller befintliga terminaler.",
                 "Open a new terminal. The installer cannot update the parent process PATH or existing terminals."))
    print(tr("Kör: agents-opencode", "Run: agents-opencode"))
    print(tr("Kör direkt utan PATH: ", "Run directly without PATH: ") + '"' + str(launcher) + '"')
    print(tr("Lägg vid behov till i PATH manuellt: ", "If needed, add to PATH manually: ") + str(bin_dir))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
