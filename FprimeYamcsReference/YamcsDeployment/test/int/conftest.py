"""
Shared pytest fixtures for FprimeYamcsReference integration tests.

This module provides common fixtures for setting up test files
that are required by integration test suites.
"""

import shutil
import pytest
import subprocess
from pathlib import Path


def find_fprime_location():
    """
    Find the fprime repository location dynamically.

    Searches in order:
    1. lib/fprime submodule (if exists)
    2. fprime-svc directory (CI artifact structure)
    3. Git submodule path
    4. Environment variable FPRIME_LOCATION
    """
    # Try relative path to submodule
    current_file = Path(__file__).resolve()
    potential_submodule = current_file.parent.parent.parent.parent.parent / "lib" / "fprime"
    if potential_submodule.exists() and (potential_submodule / "Svc").exists():
        return potential_submodule

    # Try CI artifact structure (fprime-svc directory)
    # When CI copies artifacts, fprime Svc is at ./fprime-svc/
    # which is actually lib/fprime/Svc, so we return a mock path
    cwd = Path.cwd()
    fprime_svc = cwd / "fprime-svc"
    if fprime_svc.exists() and fprime_svc.is_dir():
        # fprime-svc IS the Svc directory, so we need to return a fake parent
        # that allows accessing fprime-svc as if it were lib/fprime/Svc
        # We'll return cwd and adjust the source_dir logic below
        return fprime_svc  # Special case: return Svc directory directly

    # Try finding via git submodule
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=current_file.parent,
            check=True
        )
        repo_root = Path(result.stdout.strip())
        fprime_path = repo_root / "lib" / "fprime"
        if fprime_path.exists() and (fprime_path / "Svc").exists():
            return fprime_path
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Check environment variable
    import os
    if "FPRIME_LOCATION" in os.environ:
        fprime_path = Path(os.environ["FPRIME_LOCATION"])
        if fprime_path.exists() and (fprime_path / "Svc").exists():
            return fprime_path

    return None


@pytest.fixture(scope="session", autouse=True)
def setup_test_files():
    """
    Copy test files to /tmp/ for use by integration tests.

    Many integration tests (FileManager, FileDownlink, etc.) expect
    test files to exist in /tmp/ on the target filesystem.
    """
    # Find fprime location dynamically
    fprime_lib = find_fprime_location()

    if fprime_lib is None:
        print("Warning: Could not locate fprime repository. Test files will not be copied.")
        yield
        return

    print(f"Found fprime location: {fprime_lib}")

    # Check if fprime_lib is the Svc directory directly (CI artifact case)
    if (fprime_lib / "FileUplink").exists():
        # fprime_lib is actually the Svc directory
        source_dir = fprime_lib / "FileUplink" / "test" / "int"
        print(f"Using CI artifact structure, source_dir: {source_dir}")
    else:
        # Normal case: fprime_lib is the fprime root
        source_dir = fprime_lib / "Svc" / "FileUplink" / "test" / "int"
        print(f"Using normal structure, source_dir: {source_dir}")

    test_files = [
        "test_seq.seq",
        "test_seq_wait.seq",
        "1MiB.txt",
    ]

    # Copy files to /tmp/ if they don't exist or are different
    for filename in test_files:
        source = source_dir / filename
        dest = Path("/tmp") / filename

        if source.exists():
            try:
                shutil.copy2(source, dest)
                print(f"Copied {source} -> {dest}")
            except (IOError, PermissionError) as e:
                print(f"Warning: Could not copy {filename} to /tmp/: {e}")
        else:
            print(f"Warning: Source file {source} does not exist")

    yield

    # Cleanup is optional - comment out if you want files to persist
    # for filename in test_files:
    #     dest = Path("/tmp") / filename
    #     if dest.exists():
    #         dest.unlink()
