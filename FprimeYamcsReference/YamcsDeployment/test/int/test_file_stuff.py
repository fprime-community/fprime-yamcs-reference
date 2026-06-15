"""test_file_stuff.py

Focused regression tests for the current YAMCS failures in YamcsDeployment.
"""

from pathlib import Path

from fprime_gds.common.testing_fw import predicates


def test_file_manager_file_size(fprime_test_api):
    """Query the size of a known test file on the target filesystem."""
    fprime_test_api.send_and_assert_command(
        "FileHandling.fileManager.FileSize",
        ["/tmp/test_file.txt"],
        max_delay=10,
    )


def test_file_downlink_send_file(fprime_test_api):
    """Request a file downlink of a known test file."""
    fprime_test_api.send_and_assert_command(
        "FileHandling.fileDownlink.SendFile",
        ["/tmp/test_file.txt", "/tmp/yamcs_test_dl.txt"],
        max_delay=30,
    )
