import os
import random
import tempfile
import time

from pathlib import Path


def test_yamcs_uplink_file(fprime_test_api):
    TEST_DATA = f"test uplink data {random.random()}\n"

    tmp_file_in = tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False)
    tmp_file_in.write(TEST_DATA)
    tmp_file_in.flush()
    tmp_file_in.close()

    remote_path = f"/tmp/yamcs_uplink_test_{random.randint(0, 10000)}.txt"

    yamcs_client = fprime_test_api.pipeline.client_socket
    result = yamcs_client.upload_file(tmp_file_in.name, remote_path, timeout=30)

    assert "COMPLETED" in str(result.state), f"Upload failed: {result.state}"

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + "." + "FileSize",
        [remote_path],
        max_delay=10,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + "." + "RemoveFile",
        [remote_path, True],
        max_delay=5,
    )

    os.unlink(tmp_file_in.name)


def test_yamcs_downlink_file(fprime_test_api):
    TEST_DATA = f"test downlink data {random.random()}\n"

    tmp_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", dir="/tmp/", delete=False)
    tmp_file.write(TEST_DATA)
    tmp_file.flush()
    tmp_file.close()

    yamcs_client = fprime_test_api.pipeline.client_socket
    result = yamcs_client.download_file(tmp_file.name, timeout=30)

    assert "COMPLETED" in str(result.state), f"Download failed: {result.stdout}\n{result.stderr}"

    storage = yamcs_client.yamcs.get_storage_client()
    object_name = tmp_file.name.split("/")[-1]
    data = storage.download_object(
        bucket_name="fprimeFilesIn",
        object_name=object_name,
    )
    assert data.decode() == TEST_DATA, f"Failure: {result.stdout}\n{result.stderr}"

    os.unlink(tmp_file.name)


def test_yamcs_file_manager(fprime_test_api):
    os.makedirs("/tmp/file", exist_ok=True)
    if os.path.exists("/tmp/file"):
        for f in os.listdir("/tmp/file"):
            os.remove(os.path.join("/tmp/file", f))
        os.rmdir("/tmp/file")
    if os.path.exists("/tmp/file2"):
        os.rmdir("/tmp/file2")

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + "." + "CreateDirectory",
        ["/tmp/file"],
        max_delay=10,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + "." + "CreateDirectory",
        ["/tmp/file2"],
        max_delay=10,
    )

    for path, size in [("/tmp/1MiB.txt", 1024 * 1024), ("/tmp/test_seq.seq", 64)]:
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(b"\0" * size)

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + "." + "FileSize",
        ["/tmp/1MiB.txt"],
        max_delay=50,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + "." + "MoveFile",
        ["/tmp/1MiB.txt", "/tmp/file/1MiB.txt"],
        max_delay=50,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + "." + "FileSize",
        ["/tmp/file/1MiB.txt"],
        max_delay=50,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + "." + "AppendFile",
        ["/tmp/test_seq.seq", "/tmp/file/test_seq.seq"],
    )
    time.sleep(10)

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + "." + "MoveFile",
        ["/tmp/file/1MiB.txt", "/tmp/1MiB.txt"],
        max_delay=50,
    )

    fprime_test_api.send_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + "." + "RemoveDirectory",
        ["/tmp/file"],
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + "." + "RemoveDirectory",
        ["/tmp/file2"],
        max_delay=10,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + "." + "RemoveFile",
        ["/tmp/file/test_seq.seq", True],
        max_delay=5,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + "." + "RemoveDirectory",
        ["/tmp/file"],
        max_delay=5,
    )
