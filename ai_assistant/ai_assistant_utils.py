
import os, shutil, subprocess, importlib.util

def _maybe_cygpath(p: str) -> str:
    """
    If running on Windows and a POSIX-looking path was provided (e.g., /home/...),
    and 'cygpath' is available (Cygwin), convert to a native Windows path.
    Otherwise return the original.
    """
    if os.name != "nt":
        return p
    # Heuristic: POSIX-ish absolute path
    if not p or not p.startswith("/"):
        return p
    cyg = shutil.which("cygpath")
    if not cyg:
        return p
    try:
        win = subprocess.check_output([cyg, "-w", p], text=True).strip()
        return win
    except Exception:
        return p
