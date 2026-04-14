# -*- coding: utf-8 -*-
"""
FluxKey - Unified Entry Point and Build System
  python main.py              -> Launch desktop app
  python main.py --build      -> Build Windows EXE + Inno Setup installer
  python main.py --linux      -> Build Linux binary + .tar.gz package
  python main.py --apk        -> Prepare mobile project + build APK
  python main.py --build --apk-> Build Windows + Android
  python main.py --linux --apk-> Build Linux + Android
"""

import sys, os, subprocess, shutil, platform

BASE     = os.path.dirname(os.path.abspath(__file__))
DIST     = os.path.join(BASE, "dist")
MOBILE   = os.path.join(BASE, "mobile")
ICO      = os.path.join(BASE, "fluxkey.ico")
PNG      = os.path.join(BASE, "fluxkey.png")   # Linux icon (PNG)

APP_NAME      = "FluxKey"
APP_VERSION   = "BETA 1.0.1"
APP_PUBLISHER = ".fluxtool"
EXE_NAME      = "FluxKey"
EXE_DIR       = os.path.join(DIST, EXE_NAME)
EXE_PATH      = os.path.join(EXE_DIR, EXE_NAME + ".exe")
INSTALLER     = os.path.join(DIST, APP_NAME + "_Installer.exe")
ISS_PATH      = os.path.join(DIST, APP_NAME + "_Setup.iss")

# Linux output paths
LINUX_DIR     = os.path.join(DIST, EXE_NAME + "_Linux")
LINUX_BIN     = os.path.join(LINUX_DIR, EXE_NAME)
LINUX_TAR     = os.path.join(DIST, APP_NAME + "_Linux.tar.gz")

ISCC_CANDIDATES = [
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
]


def banner(msg, c="="):  print("\n" + c*62 + "\n  " + msg + "\n" + c*62)
def step(msg):           print("\n  > " + msg)
def ok(msg):             print("  ok: " + msg)
def fail(msg):           print("\n  FAIL: " + msg); sys.exit(1)

def run(cmd, cwd=None):
    print("    $ " + " ".join(str(x) for x in cmd))
    r = subprocess.run(cmd, cwd=cwd or BASE)
    if r.returncode != 0: fail("Command failed (exit %d)" % r.returncode)
    return r

def pip_install(*pkgs):
    run([sys.executable, "-m", "pip", "install", "--quiet"] + list(pkgs))


# ── WINDOWS BUILD ─────────────────────────────────────────────────────────

def ensure_pyinstaller():
    step("Checking PyInstaller")
    try:
        import PyInstaller; ok("Already installed")  # noqa
    except ImportError:
        step("Installing..."); pip_install("pyinstaller"); ok("Done")


def clean_build():
    step("Cleaning")
    for p in (os.path.join(BASE,"build"), os.path.join(BASE,"FluxKey.spec")):
        if os.path.isdir(p):    shutil.rmtree(p, ignore_errors=True)
        elif os.path.isfile(p): os.remove(p)
    ok("Clean")


def build_exe():
    banner("Step 1 - EXE", "-")
    os.makedirs(DIST, exist_ok=True)
    sep = ";" if sys.platform == "win32" else ":"
    add_data = []
    for src, dst in [
        (os.path.join(BASE,"ui","styles.qss"),       "ui"),
        (ICO, "."),
    ]:
        if os.path.exists(src):
            add_data += ["--add-data", src + sep + dst]

    run([sys.executable, "-m", "PyInstaller",
         "--noconfirm", "--clean", "--windowed",
         "--name", EXE_NAME, "--distpath", DIST,
         "--workpath", os.path.join(BASE,"build"),
         "--icon", ICO,
    ] + add_data + [os.path.join(BASE,"main.py")])

    if os.path.exists(EXE_PATH): ok("EXE -> " + EXE_PATH)
    else: fail("EXE not found")


def write_iss():
    banner("Step 2 - Installer", "-")
    os.makedirs(DIST, exist_ok=True)
    lines = []
    lines.append("; FluxKey Inno Setup Script")
    lines.append('#define MyAppName "' + APP_NAME + '"'  )
    lines.append('#define MyAppVersion "' + APP_VERSION + '"')
    lines.append('#define MyAppPublisher "' + APP_PUBLISHER + '"')
    lines.append("")
    lines.append("[Setup]")
    lines.append("AppId={{E4A1B2C3-D5E6-F7A8-B9C0-D1E2F3A4B5C6}")
    lines.append("AppName={#MyAppName}")
    lines.append("AppVersion={#MyAppVersion}")
    lines.append("AppPublisher={#MyAppPublisher}")
    lines.append("DefaultDirName={autopf}\\{#MyAppName}")
    lines.append("DefaultGroupName={#MyAppName}")
    lines.append("AllowNoIcons=yes")
    lines.append("OutputDir=" + DIST)
    lines.append("OutputBaseFilename=" + APP_NAME + "_Installer")
    lines.append("SetupIconFile=" + ICO)
    lines.append("Compression=lzma2/ultra64")
    lines.append("SolidCompression=yes")
    lines.append("WizardStyle=modern")
    lines.append("PrivilegesRequiredOverridesAllowed=dialog")
    lines.append("UninstallDisplayIcon={app}\\" + EXE_NAME + ".exe")
    lines.append("CreateUninstallRegKey=yes")
    lines.append("")
    lines.append("[Languages]")
    lines.append('Name: "english"; MessagesFile: "compiler:Default.isl"')
    lines.append("")
    lines.append("[Tasks]")
    lines.append('Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \\')
    lines.append('      GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce')
    lines.append("")
    lines.append("[Files]")
    lines.append('Source: "' + EXE_DIR + '\\*"; DestDir: "{app}"; \\')
    lines.append("        Flags: ignoreversion recursesubdirs createallsubdirs")
    lines.append("")
    lines.append("[Icons]")
    lines.append('Name: "{group}\\{#MyAppName}"; Filename: "{app}\\' + EXE_NAME + '.exe"')
    lines.append('Name: "{group}\\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"')
    lines.append('Name: "{commondesktop}\\{#MyAppName}"; \\')
    lines.append('      Filename: "{app}\\' + EXE_NAME + '.exe"; Tasks: desktopicon')
    lines.append("")
    lines.append("[Run]")
    lines.append('Filename: "{app}\\' + EXE_NAME + '.exe"; \\')
    lines.append('          Description: "{cm:LaunchProgram,' + APP_NAME + '}"; \\')
    lines.append("          Flags: nowait postinstall skipifsilent")

    if os.path.exists(ISS_PATH): os.remove(ISS_PATH)
    with open(ISS_PATH, "w", encoding="utf-8") as f: f.write("\n".join(lines))
    ok("ISS -> " + ISS_PATH)

    iscc = shutil.which("ISCC") or shutil.which("iscc")
    if not iscc:
        for p in ISCC_CANDIDATES:
            if os.path.exists(p): iscc = p; break
    if not iscc:
        print("  WARNING: Inno Setup not found - get it from https://jrsoftware.org")
        print("  ISS is ready: " + ISS_PATH)
        return
    run([iscc, ISS_PATH])
    if os.path.exists(INSTALLER): ok("Installer -> " + INSTALLER)
    else: fail("Installer not found after ISCC")


def build_windows():
    banner("FluxKey - Windows Build", "#")
    ensure_pyinstaller(); clean_build(); build_exe(); write_iss()
    banner("Windows Build Complete", "-")
    print("  EXE:      ", EXE_DIR)
    if os.path.exists(INSTALLER): print("  Installer:", INSTALLER)


# ── ANDROID BUILD ─────────────────────────────────────────────────────────

BUILDOZER_SPEC = (
    "[app]\n"
    "title = FluxKey\n"
    "package.name = fluxkey\n"
    "package.domain = app.fluxkey\n"
    "source.dir = .\n"
    "source.include_exts = py,png,jpg,kv,atlas,json\n"
    "source.include_patterns = core/*.py\n"
    "version = " + APP_VERSION + "\n"
    "requirements = python3,kivy==2.3.0,cryptography\n"
    "orientation = portrait\n"
    "fullscreen = 0\n"
    "android.minapi = 26\n"
    "android.ndk = 25b\n"
    "android.sdk = 34\n"
    "android.accept_sdk_license = True\n"
    "android.arch = arm64-v8a\n"
    "android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE\n"
    "android.api = 34\n"
    "android.ndk_api = 26\n"
    "android.enable_androidx = True\n"
    "android.logcat_filters = *:S python:D\n"
    "\n[buildozer]\n"
    "log_level = 2\n"
    "warn_on_root = 1\n"
)


def setup_mobile():
    step("Assembling mobile project in " + MOBILE + "/")
    os.makedirs(os.path.join(MOBILE, "core"), exist_ok=True)

    # Always sync latest core files
    for fname in ("vault.py", "password_generator.py"):
        src = os.path.join(BASE, "core", fname)
        dst = os.path.join(MOBILE, "core", fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            ok("Synced core/" + fname)
    open(os.path.join(MOBILE, "core", "__init__.py"), "w").close()

    # Always write fresh buildozer.spec
    with open(os.path.join(MOBILE, "buildozer.spec"), "w") as f:
        f.write(BUILDOZER_SPEC)
    ok("buildozer.spec written")

    # Resolve mobile main.py — check multiple locations in priority order
    mobile_main_dst = os.path.join(MOBILE, "main.py")
    candidates = [
        os.path.join(MOBILE, "_mobile_src.py"),          # bundled copy
        os.path.join(BASE, "mobile", "_mobile_src.py"),  # inside project
    ]
    src_found = None
    for c in candidates:
        if os.path.exists(c):
            src_found = c; break

    if src_found:
        shutil.copy2(src_found, mobile_main_dst)
        ok("mobile/main.py ready from " + os.path.basename(src_found))
    elif os.path.exists(mobile_main_dst):
        ok("mobile/main.py already present")
    else:
        print("  ERROR: mobile/main.py not found!")
        print("  Expected: " + os.path.join(MOBILE, "_mobile_src.py"))
        sys.exit(1)

    with open(os.path.join(MOBILE, "README.md"), "w") as f:
        f.write(
            "# FluxKey Mobile\n\n"
            "Build APK:\n```\n"
            "cd mobile\n"
            "pip3 install buildozer cython\n"
            "buildozer android debug\n```\n\n"
            "APK: mobile/bin/FluxKey-" + APP_VERSION + "-arm64-v8a-debug.apk\n"
        )
    ok("README.md written")


def build_apk():
    banner("FluxKey - Android APK Build", "#")
    setup_mobile()

    if platform.system() == "Windows":
        print("\n  NOTE: APK compilation requires Linux or WSL.")
        print("  Mobile project is ready at: " + MOBILE)
        print("\n  To build:")
        print("    1. Open WSL")
        print("    2. cd " + MOBILE.replace("\\", "/"))
        print("    3. pip3 install buildozer cython")
        print("    4. buildozer android debug")
        print("\n  APK: mobile/bin/FluxKey-" + APP_VERSION + "-arm64-v8a-debug.apk")
        return

    # Linux/WSL path — attempt actual build
    buildozer_path = shutil.which("buildozer")
    if not buildozer_path:
        step("Installing buildozer + cython")
        pip_install("buildozer", "cython")
        buildozer_path = shutil.which("buildozer") or "buildozer"

    # Ensure system deps
    apt = shutil.which("apt-get")
    if apt:
        step("Ensuring system dependencies")
        subprocess.run(
            ["sudo", apt, "install", "-y", "-qq",
             "git", "zip", "unzip", "openjdk-17-jdk",
             "libffi-dev", "libssl-dev", "autoconf", "libtool", "pkg-config"],
            check=False
        )

    step("Running buildozer android debug  (first run ~30 min)")
    result = subprocess.run([buildozer_path, "android", "debug"], cwd=MOBILE)

    bin_dir = os.path.join(MOBILE, "bin")
    apk = None
    if os.path.isdir(bin_dir):
        for fname in os.listdir(bin_dir):
            if fname.endswith(".apk"):
                apk = os.path.join(bin_dir, fname); break

    if apk:
        os.makedirs(DIST, exist_ok=True)
        dest = os.path.join(DIST, APP_NAME + ".apk")
        shutil.copy2(apk, dest)
        ok("APK -> " + dest)
    elif result.returncode == 0:
        ok("Build done — check " + bin_dir)
    else:
        print("  Check output above. Retry: cd " + MOBILE + " && buildozer android debug")


# ── DESKTOP LAUNCH ────────────────────────────────────────────────────────

def _data_path(*parts):
    candidates = [os.path.join(BASE, *parts), os.path.join(os.getcwd(), *parts)]
    if hasattr(sys, "_MEIPASS"):
        candidates.insert(0, os.path.join(sys._MEIPASS, *parts))
    for p in candidates:
        if os.path.exists(p): return p
    return candidates[0]


def load_styles(app):
    qss = _data_path("ui", "styles.qss")
    if os.path.exists(qss):
        with open(qss, "r", encoding="utf-8") as f: app.setStyleSheet(f.read())


def get_icon():
    from PySide6.QtGui import QIcon
    # Prefer PNG on Linux (ICO works too, but PNG is native)
    if sys.platform != "win32":
        png = _data_path("fluxkey.png")
        if os.path.exists(png):
            return QIcon(png)
    ico = _data_path("fluxkey.ico")
    return QIcon(ico) if os.path.exists(ico) else QIcon()


def _create_shortcut():
    if sys.platform != "win32": return
    try:
        desktop  = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut = os.path.join(desktop, "FluxKey.lnk")
        if os.path.exists(shortcut): return
        exe = sys.executable
        ico = _data_path("fluxkey.ico")
        ps  = (
            '$s=(New-Object -COM WScript.Shell).CreateShortcut("' + shortcut + '");' +
            '$s.TargetPath="' + exe + '";' +
            '$s.IconLocation="' + ico + '";' +
            '$s.Description="FluxKey Password Manager";' +
            '$s.Save()'
        )
        subprocess.run(["powershell","-NoProfile","-NonInteractive","-Command",ps],
                       creationflags=0x08000000, timeout=10)
    except Exception: pass


def launch_app():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("FluxKey")
    app.setStyle("Fusion")
    icon = get_icon()
    app.setWindowIcon(icon)
    load_styles(app)
    _create_shortcut()
    from ui.login import LoginWindow
    win = LoginWindow(icon); win.show()
    sys.exit(app.exec())


# ── LINUX BUILD ───────────────────────────────────────────────────────────

def build_linux():
    """
    Build a self-contained Linux binary using PyInstaller.

    Produces:
      dist/FluxKey_Linux/          - folder with binary + all dependencies
      dist/FluxKey_Linux.tar.gz    - compressed archive ready to distribute

    Also writes:
      dist/FluxKey_Linux/FluxKey.desktop  - .desktop launcher for the system
      dist/install_linux.sh               - one-command installer script
    """
    banner("FluxKey - Linux Build", "#")

    if platform.system() == "Windows":
        print("\n  ERROR: Linux builds must be run on a Linux machine or WSL.")
        print("  On Windows, open WSL and run:")
        print("    cd " + BASE.replace("\\", "/"))
        print("    python main.py --linux")
        sys.exit(1)

    ensure_pyinstaller()

    # ── Clean previous Linux build ────────────────────────────────────────
    step("Cleaning previous Linux build")
    for p in (os.path.join(BASE, "build"), LINUX_DIR, LINUX_TAR):
        if os.path.isdir(p):    shutil.rmtree(p, ignore_errors=True)
        elif os.path.isfile(p): os.remove(p)
    # Remove only the Linux spec, not the Windows one
    spec = os.path.join(BASE, EXE_NAME + ".spec")
    if os.path.isfile(spec): os.remove(spec)
    ok("Clean")

    # ── Resolve icon: prefer PNG, fall back to ICO ────────────────────────
    step("Resolving icon")
    icon_arg = None
    if os.path.exists(PNG):
        icon_arg = PNG;  ok("Using fluxkey.png")
    elif os.path.exists(ICO):
        icon_arg = ICO;  ok("Using fluxkey.ico (PNG preferred on Linux)")
    else:
        ok("No icon found — building without one")

    # ── PyInstaller command ───────────────────────────────────────────────
    banner("Step 1 - Binary", "-")
    os.makedirs(DIST, exist_ok=True)

    add_data = []
    for src, dst in [
        (os.path.join(BASE, "ui", "styles.qss"), "ui"),
        (ICO, "."),
        (PNG, "."),
    ]:
        if os.path.exists(src):
            add_data += ["--add-data", src + ":" + dst]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--windowed",
        "--name",      EXE_NAME,
        "--distpath",  DIST,
        "--workpath",  os.path.join(BASE, "build"),
        "--onedir",                          # folder mode — faster startup than onefile
    ]
    if icon_arg:
        cmd += ["--icon", icon_arg]
    cmd += add_data
    cmd += [os.path.join(BASE, "main.py")]

    run(cmd)

    if not os.path.exists(LINUX_BIN):
        fail("Linux binary not found at: " + LINUX_BIN)
    ok("Binary -> " + LINUX_BIN)

    # ── Write .desktop launcher file ──────────────────────────────────────
    banner("Step 2 - Desktop launcher", "-")
    desktop_content = (
        "[Desktop Entry]\n"
        "Version=1.0\n"
        "Type=Application\n"
        "Name=FluxKey\n"
        "Comment=FluxKey Cyber Vault — Password Manager\n"
        "Exec={install_dir}/FluxKey\n"
        "Icon={install_dir}/fluxkey.png\n"
        "Terminal=false\n"
        "Categories=Utility;Security;\n"
        "Keywords=password;vault;security;encrypt;\n"
        "StartupNotify=true\n"
    )
    desktop_path = os.path.join(LINUX_DIR, "FluxKey.desktop")
    with open(desktop_path, "w") as f:
        f.write(desktop_content)
    ok(".desktop file -> " + desktop_path)

    # ── Write install_linux.sh ────────────────────────────────────────────
    banner("Step 3 - Installer script", "-")
    install_sh = os.path.join(DIST, "install_linux.sh")
    install_content = r"""#!/usr/bin/env bash
# FluxKey Linux Installer
# Usage: bash install_linux.sh

set -e

APP_NAME="FluxKey"
INSTALL_DIR="$HOME/.local/share/FluxKey"
BIN_LINK="$HOME/.local/bin/FluxKey"
DESKTOP_DIR="$HOME/.local/share/applications"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/FluxKey_Linux"

echo ""
echo "  ============================================"
echo "   FluxKey Linux Installer"
echo "  ============================================"
echo ""

# Check source exists
if [ ! -d "$SRC_DIR" ]; then
    echo "  ERROR: FluxKey_Linux/ folder not found next to this script."
    echo "  Make sure you extracted the archive first."
    exit 1
fi

# Create install dir
mkdir -p "$INSTALL_DIR"
mkdir -p "$HOME/.local/bin"
mkdir -p "$DESKTOP_DIR"

# Copy files
echo "  > Copying files to $INSTALL_DIR ..."
cp -r "$SRC_DIR/." "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/FluxKey"

# Symlink binary so 'FluxKey' works from terminal
ln -sf "$INSTALL_DIR/FluxKey" "$BIN_LINK"
echo "  ok: Symlink -> $BIN_LINK"

# Install .desktop file with real paths
DESKTOP_FILE="$DESKTOP_DIR/FluxKey.desktop"
sed "s|{install_dir}|$INSTALL_DIR|g" "$INSTALL_DIR/FluxKey.desktop" > "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"
echo "  ok: Desktop entry -> $DESKTOP_FILE"

# Update desktop database if possible
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

echo ""
echo "  ============================================"
echo "   FluxKey installed successfully!"
echo "  ============================================"
echo ""
echo "  Run from terminal:    FluxKey"
echo "  Or find it in your application menu."
echo ""
"""
    with open(install_sh, "w") as f:
        f.write(install_content)
    os.chmod(install_sh, 0o755)
    ok("Installer -> " + install_sh)

    # ── Write uninstall_linux.sh ──────────────────────────────────────────
    uninstall_sh = os.path.join(DIST, "uninstall_linux.sh")
    uninstall_content = r"""#!/usr/bin/env bash
# FluxKey Linux Uninstaller

echo ""
echo "  Uninstalling FluxKey..."
rm -rf "$HOME/.local/share/FluxKey"
rm -f  "$HOME/.local/bin/FluxKey"
rm -f  "$HOME/.local/share/applications/FluxKey.desktop"
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi
echo "  FluxKey removed. Your vault data in ~/.fluxkey is kept."
echo "  To remove vault data too: rm -rf ~/.fluxkey"
echo ""
"""
    with open(uninstall_sh, "w") as f:
        f.write(uninstall_content)
    os.chmod(uninstall_sh, 0o755)
    ok("Uninstaller -> " + uninstall_sh)

    # ── Package into tar.gz ───────────────────────────────────────────────
    banner("Step 4 - Packaging tar.gz", "-")
    step("Creating " + LINUX_TAR)
    import tarfile
    with tarfile.open(LINUX_TAR, "w:gz") as tar:
        # Add the binary folder
        tar.add(LINUX_DIR, arcname=EXE_NAME + "_Linux")
        # Add the shell scripts at the root of the archive
        tar.add(install_sh,   arcname="install_linux.sh")
        tar.add(uninstall_sh, arcname="uninstall_linux.sh")
    ok("Archive -> " + LINUX_TAR)

    # ── Summary ───────────────────────────────────────────────────────────
    banner("Linux Build Complete", "-")
    print("  Binary folder: ", LINUX_DIR)
    print("  Archive:       ", LINUX_TAR)
    print("  Installer:     ", install_sh)
    print()
    print("  Distribute the .tar.gz. Users extract and run:")
    print("    tar -xzf FluxKey_Linux.tar.gz")
    print("    bash install_linux.sh")
    print()
    print("  Or run directly without installing:")
    print("    ./FluxKey_Linux/FluxKey")


# ── ENTRY POINT ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    do_build = "--build" in sys.argv
    do_linux = "--linux" in sys.argv
    do_apk   = "--apk"   in sys.argv

    if do_build and do_apk:
        build_windows()
        build_apk()
        banner("All Builds Complete", "#")
        sys.exit(0)
    elif do_build and do_linux:
        build_windows()
        build_linux()
        banner("All Builds Complete", "#")
        sys.exit(0)
    elif do_build:
        build_windows(); sys.exit(0)
    elif do_linux and do_apk:
        build_linux()
        build_apk()
        banner("All Builds Complete", "#")
        sys.exit(0)
    elif do_linux:
        build_linux(); sys.exit(0)
    elif do_apk:
        build_apk(); sys.exit(0)
    else:
        launch_app()
