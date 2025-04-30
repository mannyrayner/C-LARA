from .refactor_trim_imports_libcst import trim_imports_from_file

from .clara_utils import copy_file

import re, shutil, sys
from pathlib import Path

# --- adjust if needed ---------------------------------------------------
PROJECT_ROOT  = Path(__file__).resolve().parent.parent    #  <clara_app>/..  ?
CLARA_APP     = PROJECT_ROOT / "clara_app"
# ------------------------------------------------------------------------

def clean_all_views():
    for vf in CLARA_APP.glob("*_views.py"):
        cleaned = vf.with_name(vf.stem + "_cleaned.py")
        print(f"• trimming {vf.name} → {cleaned.name}")
        trim_imports_from_file(str(vf), str(cleaned))

def copy_cleaned_views() -> None:
    for vf in CLARA_APP.glob("*_views.py"):
        cleaned = vf.with_name(vf.stem + "_cleaned.py")
        if cleaned.exists():
            print(f"• copying {cleaned.name}  →  {vf.name}")
            shutil.copy2(cleaned, vf)          # preserves mtime & perms
        else:
            print(f"  (skip {vf.name} – no _cleaned version)")
            
