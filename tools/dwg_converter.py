"""
DWG-to-DXF conversion utility.

Uses the bundled LibreDWG command-line tool `dwg2dxf.exe`
which is executed via subprocess. Produces a temporary .dxf file.
"""

import os
import tempfile
import subprocess
import logging

logger = logging.getLogger(__name__)

def _get_libredwg_path() -> str | None:
    """Get the path to the bundled LibreDWG dwg2dxf executable."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exe_path = os.path.join(base_dir, "tools", "bin", "libredwg", "dwg2dxf.exe")
    if os.path.isfile(exe_path):
        return exe_path
    return None

def convert_dwg_to_dxf(dwg_path: str) -> str:
    """Convert a .dwg file to .dxf using bundled LibreDWG.

    Args:
        dwg_path: Absolute path to the .dwg file.

    Returns:
        Path to the generated .dxf file.

    Raises:
        FileNotFoundError: If the DWG file doesn't exist.
        RuntimeError: If conversion fails or converter is not found.
    """
    if not os.path.isfile(dwg_path):
        raise FileNotFoundError(f"DWG file not found: {dwg_path}")

    dwg2dxf_exe = _get_libredwg_path()
    if not dwg2dxf_exe:
        raise RuntimeError(
            "Cannot convert DWG file — bundled LibreDWG dwg2dxf.exe not found.\n"
            "Please ensure tools/bin/libredwg/dwg2dxf.exe is present."
        )

    try:
        output_dir = tempfile.mkdtemp(prefix="dwg2dxf_libredwg_")
        filename = os.path.basename(dwg_path)
        dxf_name = os.path.splitext(filename)[0] + ".dxf"
        dxf_path = os.path.join(output_dir, dxf_name)

        cmd = [dwg2dxf_exe, "-y", "-o", dxf_path, dwg_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if os.path.isfile(dxf_path):
            logger.info(f"LibreDWG conversion succeeded: {dxf_path}")
            return dxf_path
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.warning(f"LibreDWG conversion produced no output file. Error: {error_msg}")
    except Exception as e:
        logger.warning(f"LibreDWG conversion failed: {e}")

    raise RuntimeError("Failed to convert DWG to DXF using LibreDWG.")
