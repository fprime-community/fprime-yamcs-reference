"""
Shared pytest fixtures for FprimeYamcsReference integration tests.

This module provides common fixtures for setting up test files
that are required by integration test suites.
"""
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import pytest

logger = logging.getLogger(__name__)

REQUIRED_TEST_FILES = ["test_seq.seq", "test_seq_wait.seq", "1MiB.txt"]


def find_fprime_location() -> Optional[Path]:
    """Find fprime repository: git submodule → CI artifact → env var."""
    current_file = Path(__file__).resolve()

    # Try git submodule
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, cwd=current_file.parent, check=True, timeout=5
        )
        fprime_path = Path(result.stdout.strip()) / "lib" / "fprime"
        if (fprime_path / "Svc").exists():
            return fprime_path
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try CI artifact (fprime-svc directory)
    fprime_svc = Path.cwd() / "fprime-svc"
    if fprime_svc.is_dir() and (fprime_svc / "FileUplink").exists():
        return fprime_svc

    # Try environment variable
    fprime_env = os.environ.get("FPRIME_LOCATION")
    if fprime_env and (Path(fprime_env) / "Svc").exists():
        return Path(fprime_env)

    return None


def get_test_file_dir(fprime_lib: Path) -> Optional[Path]:
    """Get source directory for test files (handles both CI and normal structures)."""
    # CI artifact: fprime_lib IS the Svc directory
    if (fprime_lib / "FileUplink").is_dir():
        return fprime_lib / "FileUplink" / "test" / "int"
    
    # Normal: fprime_lib is fprime root
    source = fprime_lib / "Svc" / "FileUplink" / "test" / "int"
    return source if source.is_dir() else None


@pytest.fixture(scope="session", autouse=True)
def setup_test_files():
    """Copy test files from fprime to /tmp/ for integration tests."""
    fprime_lib = find_fprime_location()
    if not fprime_lib:
        logger.warning("Could not locate fprime repository")
        yield
        return

    source_dir = get_test_file_dir(fprime_lib)
    if not source_dir:
        logger.warning(f"Test files not found at: {source_dir}")
        yield
        return

    for filename in REQUIRED_TEST_FILES:
        source = source_dir / filename
        if source.exists():
            try:
                shutil.copy2(source, Path("/tmp") / filename)
            except (IOError, PermissionError) as e:
                logger.warning(f"Failed to copy {filename}: {e}")
        else:
            logger.warning(f"Source file not found: {source}")

    yield
