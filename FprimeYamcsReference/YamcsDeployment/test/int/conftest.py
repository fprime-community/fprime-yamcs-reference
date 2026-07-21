"""
Shared pytest fixtures for F' Svc integration tests.

This module provides common fixtures for setting up test files
that are required by multiple integration test suites.
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

    # Try git submodule (current file is in lib/fprime/Svc/)
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, cwd=current_file.parent, check=True, timeout=5
        )
        repo_root = Path(result.stdout.strip())
        fprime_path = repo_root / "lib" / "fprime"
        if (fprime_path / "Svc").exists():
            logger.info(f"Found fprime via git submodule: {fprime_path}")
            return fprime_path
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try CI artifact (fprime-svc directory at repo root)
    fprime_svc = Path.cwd() / "fprime-svc"
    if fprime_svc.is_dir() and (fprime_svc / "FileUplink").exists():
        logger.info(f"Found fprime via CI artifact: {fprime_svc}")
        return fprime_svc

    # Try environment variable
    fprime_env = os.environ.get("FPRIME_LOCATION")
    if fprime_env and (Path(fprime_env) / "Svc").exists():
        logger.info(f"Found fprime via FPRIME_LOCATION env: {fprime_env}")
        return Path(fprime_env)

    # Fallback: assume we're already in lib/fprime/Svc/
    fprime_fallback = current_file.parent.parent
    if (fprime_fallback / "Svc").exists():
        logger.info(f"Found fprime via fallback (parent directory): {fprime_fallback}")
        return fprime_fallback

    return None


def get_test_file_dir(fprime_lib: Path) -> Optional[Path]:
    """Get source directory for test files (handles both CI and normal structures)."""
    # CI artifact: fprime_lib IS the Svc directory
    if (fprime_lib / "FileUplink").is_dir():
        source = fprime_lib / "FileUplink" / "test" / "int"
        if source.is_dir():
            logger.info(f"Test files source (CI artifact structure): {source}")
            return source
    
    # Normal: fprime_lib is fprime root
    source = fprime_lib / "Svc" / "FileUplink" / "test" / "int"
    if source.is_dir():
        logger.info(f"Test files source (normal structure): {source}")
        return source
    
    return None


@pytest.fixture(scope="session", autouse=True)
def setup_test_files():
    """
    Pre-populate /tmp/ with test files for FileManager/FileDownlink tests.
    
    Assumes FSW and GDS run on same machine (local/CI testing). Copies files
    to /tmp/ on the host, which FSW can then access as its /tmp/.
    
    Note: FileUplink test reads files directly from fprime repo and uploads
    them TO /tmp/ on FSW. This fixture is redundant for FileUplink but needed
    for standalone FileManager/FileDownlink test runs.
    """
    fprime_lib = find_fprime_location()
    if not fprime_lib:
        logger.warning("Could not locate fprime repository - test files not pre-populated")
        yield
        return

    source_dir = get_test_file_dir(fprime_lib)
    if not source_dir:
        logger.warning(f"Test files source directory not found under {fprime_lib}")
        yield
        return

    copied_count = 0
    for filename in REQUIRED_TEST_FILES:
        source = source_dir / filename
        dest = Path("/tmp") / filename
        
        if source.exists():
            try:
                shutil.copy2(source, dest)
                logger.info(f"Pre-populated /tmp/{filename} for FSW tests")
                copied_count += 1
            except (IOError, PermissionError) as e:
                logger.warning(f"Failed to copy {filename} to /tmp/: {e}")
        else:
            logger.warning(f"Source file not found: {source}")
    
    logger.info(f"Pre-populated {copied_count}/{len(REQUIRED_TEST_FILES)} test files to /tmp/")
    yield
