import os
import subprocess
import time
from pathlib import Path


def test_seqgen(fprime_test_api):
    test_dir = Path(__file__).parent
    seq_file = test_dir / "test_seq_new.seq"
    seq_wait_file = test_dir / "test_seq_wait_new.seq"
    bin_file = test_dir / "ref_test_seq.bin"
    bin_wait_file = test_dir / "ref_test_seq_wait.bin"

    cmd_no_op = fprime_test_api.get_mnemonic("Svc.CommandDispatcher") + ".CMD_NO_OP"
    cmd_no_op_string = fprime_test_api.get_mnemonic("Svc.CommandDispatcher") + ".CMD_NO_OP_STRING"

    with open(seq_file, "w") as f:
        f.write("; A test sequence\n")
        f.write(";\n")
        f.write(f"R00:00:00 {cmd_no_op}\n\n")
        f.write("; Let's try out some commands with arguments\n")
        f.write(f'R00:00:01.050 {cmd_no_op_string} "Awesome String!";\n')

    with open(seq_wait_file, "w") as f:
        f.write("; A test sequence\n")
        f.write(";\n")
        f.write(f"R00:00:00 {cmd_no_op}\n\n")
        f.write("; Let's try out some commands with arguments\n")
        f.write(f'R00:00:01.050 {cmd_no_op_string} "SEQ WAIT 2 MINS!"\n')
        f.write(";\n")
        f.write(f'R00:02:00.050 {cmd_no_op_string} "SEQ after 2mins!"\n')
        f.write(";\n")
        f.write(f'R00:00:01.050 {cmd_no_op_string} "SEQ DONE !"\n')
        f.write(";\n")

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_AUTO", max_delay=10
    )

    result1 = subprocess.run([
        "fprime-seqgen",
        "--dictionary", str(fprime_test_api.dictionaries.dictionary_path),
        str(seq_file), str(bin_file),
    ], capture_output=True, text=True)
    assert result1.returncode == 0, f"fprime-seqgen failed:\n{result1.stdout}\n{result1.stderr}"

    result2 = subprocess.run([
        "fprime-seqgen",
        "-d", str(fprime_test_api.dictionaries.dictionary_path),
        str(seq_wait_file), str(bin_wait_file),
    ], capture_output=True, text=True)
    assert result2.returncode == 0, f"fprime-seqgen failed:\n{result2.stdout}\n{result2.stderr}"

    yamcs_client = fprime_test_api.pipeline.client_socket
    result = yamcs_client.upload_file(str(bin_file), "/tmp/ref_test_seq.bin", timeout=60)
    assert "COMPLETED" in str(result.state), f"Upload ref_test_seq.bin failed: {result.state}"

    result = yamcs_client.upload_file(str(bin_wait_file), "/tmp/ref_test_seq_wait.bin", timeout=60)
    assert "COMPLETED" in str(result.state), f"Upload ref_test_seq_wait.bin failed: {result.state}"

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_RUN",
        args=["/tmp/ref_test_seq.bin", "BLOCK"],
        max_delay=5,
    )

    os.remove(seq_file)
    os.remove(seq_wait_file)


def test_send_seq(fprime_test_api):
    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_VALIDATE",
        ["/tmp/ref_test_seq.bin"],
        max_delay=10,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_RUN",
        ["/tmp/ref_test_seq.bin", "BLOCK"],
        max_delay=5,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CommandDispatcher") + ".CMD_NO_OP_STRING",
        ["test_string_execute_2 auto completed"],
        max_delay=10,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_MANUAL", max_delay=10
    )
    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_AUTO", max_delay=10
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_MANUAL", max_delay=10
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_RUN",
        ["/tmp/ref_test_seq.bin", "NO_BLOCK"],
        max_delay=5,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_START", max_delay=10
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_CANCEL", max_delay=10
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CommandDispatcher") + ".CMD_NO_OP_STRING",
        ["manually START/CANCEL after cmd 0"],
        max_delay=10,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_VALIDATE",
        ["/tmp/ref_test_seq.bin"],
        max_delay=10,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_AUTO", max_delay=10
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_MANUAL", max_delay=10
    )

    fprime_test_api.send_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_START"
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_RUN",
        ["/tmp/ref_test_seq_wait.bin", "NO_BLOCK"],
        max_delay=5,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_START", max_delay=10
    )
    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CommandDispatcher") + ".CMD_NO_OP_STRING",
        ["manually START command 0"],
        max_delay=10,
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_STEP", max_delay=3
    )
    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CommandDispatcher") + ".CMD_NO_OP_STRING",
        ["manually START/STEP cmd 1 "],
        max_delay=3,
    )

    time.sleep(10)
    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_STEP", max_delay=10
    )
    time.sleep(130)
    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.CmdSequencer") + ".CS_STEP", max_delay=3
    )

    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + ".RemoveFile",
        ["/tmp/ref_test_seq.bin", True],
        max_delay=15,
    )
    fprime_test_api.send_and_assert_command(
        fprime_test_api.get_mnemonic("Svc.FileManager") + ".RemoveFile",
        ["/tmp/ref_test_seq_wait.bin", True],
        max_delay=15,
    )
