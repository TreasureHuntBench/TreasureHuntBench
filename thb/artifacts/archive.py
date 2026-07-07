"""ZIP archive artifacts, optionally AES-password-protected (pyzipper)."""

import os
from typing import Dict, Optional

import pyzipper


def write_zip(path: str, files: Dict[str, str],
              password: Optional[str] = None) -> str:
    """Write ``files`` (arcname -> text content) into a ZIP at ``path``."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    if password:
        zf = pyzipper.AESZipFile(path, "w", compression=pyzipper.ZIP_DEFLATED,
                                 encryption=pyzipper.WZ_AES)
        zf.setpassword(password.encode("utf-8"))
    else:
        zf = pyzipper.ZipFile(path, "w", compression=pyzipper.ZIP_DEFLATED)
    with zf:
        for arcname in sorted(files):
            zf.writestr(arcname, files[arcname])
    return path


def read_zip_entry(path: str, arcname: str,
                   password: Optional[str] = None) -> str:
    with pyzipper.AESZipFile(path) as zf:
        if password:
            zf.setpassword(password.encode("utf-8"))
        return zf.read(arcname).decode("utf-8")


def list_zip(path: str):
    with pyzipper.AESZipFile(path) as zf:
        return sorted(zf.namelist())
