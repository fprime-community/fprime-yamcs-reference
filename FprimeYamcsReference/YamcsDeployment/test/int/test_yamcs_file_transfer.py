"""test_yamcs_file_transfer.py:

Test YAMCS file transfer service for file upload and download.
This tests the YAMCS-specific file transfer capabilities.
"""

import random
import tempfile
from pathlib import Path


def test_yamcs_uplink_via_file_transfer(fprime_test_api):
    """Test file uplink using YAMCS file transfer service

    This test uploads a file using YAMCS file transfer and verifies
    the FSW receives it via FileReceived event.
    """
    TEST_DATA = f"test uplink data via YAMCS {random.random()}\n"

    # Create a temporary file with test data
    tmp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
    tmp_file.write(TEST_DATA)
    tmp_file.flush()
    tmp_file_path = tmp_file.name
    tmp_file.close()

    # Upload via YAMCS file transfer service
    destination = f"/tmp/yamcs_uplink_test_{random.randint(0, 10000)}.txt"

    # Use the YAMCS client to upload
    yamcs_client = fprime_test_api.pipeline.client_socket
    if not hasattr(yamcs_client, 'upload_file'):
        import pytest
        pytest.skip("Not using YAMCS transport")

    # Capture event history before upload (upload_file blocks until completion)
    start = fprime_test_api.get_event_test_history().size()

    # Upload and wait for completion
    transfer = yamcs_client.upload_file(tmp_file_path, destination, timeout=30)

    # Verify the upload completed successfully
    assert transfer is not None

    # Verify FSW received the file (check for FileReceived event)
    event = fprime_test_api.await_event("FileReceived", start=start, timeout=5)
    assert event is not None

    # Cleanup
    Path(tmp_file_path).unlink()

    # Verify file exists on FSW side
    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + ".FileSize",
        [destination],
        timeout=30,
    )


def test_yamcs_downlink_via_file_transfer(fprime_test_api):
    """Test file downlink using YAMCS file transfer service

    Uploads a file with known content to FSW, then requests it back through the
    YAMCS file transfer service (which drives FileDownlink.SendFile on FSW) and
    verifies the reassembled bucket object matches.
    """
    TEST_DATA = f"test downlink data via YAMCS {random.random()}\n"

    source_file = f"/tmp/yamcs_downlink_source_{random.randint(0, 10000)}.txt"

    tmp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False, dir="/tmp/")
    tmp_file.write(TEST_DATA)
    tmp_file.flush()
    tmp_file_path = tmp_file.name
    tmp_file.close()

    yamcs_client = fprime_test_api.pipeline.client_socket
    if not hasattr(yamcs_client, 'download_file'):
        import pytest
        pytest.skip("Not using YAMCS transport")

    try:
        # Upload the file so there is something on FSW to downlink
        start = fprime_test_api.get_event_test_history().size()
        yamcs_client.upload_file(tmp_file_path, source_file, timeout=30)
        assert fprime_test_api.await_event("FileReceived", start=start, timeout=10) is not None

        # Downlink it back under a distinct object name so the object staged
        # during upload cannot mask a downlink failure
        downloaded_object = f"yamcs_downloaded_{random.randint(0, 10000)}.txt"
        transfer = yamcs_client.download_file(
            source_file, object_name=downloaded_object, timeout=60
        )
        assert transfer is not None
        assert "COMPLETED" in str(transfer.state), f"Downlink did not complete: {transfer.state}"

        # Verify the reassembled object contents match what was uplinked
        storage = yamcs_client.yamcs.get_storage_client()
        content = storage.download_object(
            bucket_name="fprimeFilesIn", object_name=downloaded_object
        )
        assert content.decode() == TEST_DATA
    finally:
        Path(tmp_file_path).unlink()


def test_yamcs_large_file_transfer(fprime_test_api):
    """Test YAMCS file transfer with a larger file (1 MiB)

    Verifies that YAMCS file transfer can handle larger files.
    """
    yamcs_client = fprime_test_api.pipeline.client_socket
    if not hasattr(yamcs_client, 'upload_file'):
        import pytest
        pytest.skip("Not using YAMCS transport")

    # Use the existing 1MiB.txt file
    source_file = "/tmp/1MiB.txt"
    destination = "/tmp/yamcs_large_file_test.txt"

    # Capture event history before upload (upload blocks until completion)
    start = fprime_test_api.get_event_test_history().size()

    # Upload the large file with increased timeout
    transfer = yamcs_client.upload_file(source_file, destination, timeout=300)

    # Verify completion
    assert transfer is not None

    # Wait for FileReceived event
    event = fprime_test_api.await_event("FileReceived", start=start, timeout=30)
    assert event is not None

    # Verify file size on FSW
    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + ".FileSize",
        [destination],
        timeout=30,
    )
