#!/usr/bin/env python3
"""Shared, offline, per-user installer (Python 3.10+, standard library only)."""

import argparse
import os
from pathlib import Path
import shutil
import sys
import tempfile


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
    parser.parse_args(argv)
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
    print(tr("Kör: agents-opencode", "Run: agents-opencode"))
    print(tr("Kör direkt utan PATH: ", "Run directly without PATH: ") + '"' + str(launcher) + '"')
    print(tr("Lägg vid behov till i PATH manuellt: ", "If needed, add to PATH manually: ") + str(bin_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
