import os
import sys

def get_app_name():
    return "rootChat"

def get_user_config_dir():
    """Returns ~/.config/localchat for configuration files."""
    path = os.path.expanduser(f"~/.config/{get_app_name()}")
    os.makedirs(path, exist_ok=True)
    return path

def get_user_data_dir():
    """Returns ~/.local/share/localchat for database and user data."""
    path = os.path.expanduser(f"~/.local/share/{get_app_name()}")
    os.makedirs(path, exist_ok=True)
    return path

def get_user_state_dir():
    """Returns ~/.local/state/localchat for logs and volatile state."""
    path = os.path.expanduser(f"~/.local/state/{get_app_name()}")
    os.makedirs(path, exist_ok=True)
    return path

def get_resource_path(relative_path):
    """Get absolute path to a bundled resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Development mode: base path is the directory containing app.py
        base_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    return os.path.join(base_path, relative_path)

def get_app_icon():
    """Builds a complete multi-resolution QIcon supporting all standard FreeDesktop sizes."""
    from PySide6.QtGui import QIcon
    icon = QIcon()
    sizes = [16, 24, 32, 48, 64, 128, 256, 512]
    for sz in sizes:
        p = get_resource_path(f"resources/icons/rootChat_{sz}.png")
        if os.path.exists(p):
            icon.addFile(p)
    master_path = get_resource_path("resources/icons/rootChat.png")
    if os.path.exists(master_path):
        icon.addFile(master_path)
    svg_path = get_resource_path("resources/icons/rootChat.svg")
    if os.path.exists(svg_path):
        icon.addFile(svg_path)
    return icon

def set_linux_process_name(name: str = "rootChat"):
    """Sets the Linux process comm name and window class so desktop docks match properly."""
    try:
        import ctypes
        libc = ctypes.CDLL("libc.so.6")
        PR_SET_NAME = 15
        libc.prctl(PR_SET_NAME, name.encode("utf-8"), 0, 0, 0)
    except Exception:
        pass

