"""test_cmd_uplink.py:

Test command dispatcher with basic integration tests.
"""


from pathlib import Path

def test_send_uplink_command(fprime_test_api):
    """Test that commands may be sent

    Tests command send, dispatch, and receipt using send_and_assert command with a pair of CmdDispatcher commands.
    """
    # Files are in /tmp/ (copied there by conftest.py fixture)
    tmp_dir = Path("/tmp")

    # file_path = test_seq.seq  and destination = /tmp/test_seq.seq (for fileManager)
    assert fprime_test_api.uplink_file_and_await_completion(
        str(tmp_dir / "test_seq.seq"), "/tmp/test_seq.seq", timeout=20
    ), "Failed to uplink test_seq.seq"

    # for fileDownlink
    assert fprime_test_api.uplink_file_and_await_completion(
        str(tmp_dir / "test_seq_wait.seq"), "/tmp/test_seq_wait.seq", timeout=20
    ), "Failed to uplink test_seq_wait.seq"

    # for health, fileDownlink, fileManager
    assert fprime_test_api.uplink_file_and_await_completion(
        str(tmp_dir / "1MiB.txt"), "/tmp/1MiB.txt", timeout=20
    ), "Failed to uplink 1MiB.txt"
