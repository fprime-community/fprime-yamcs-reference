"""test_basic.py

YAMCS transport parity tests for the YamcsDeployment. Each test exercises a
built-in Svc component through the YAMCS path and verifies the same behavior
the normal GDS TCP transport provides.

Run with:
    pytest --use-yamcs [--yamcs-url http://host:port] \
           --dictionary <path-to-dictionary> \
           FprimeYamcsReference/YamcsDeployment/test/int/test_basic.py
"""

import time
from enum import Enum
from pathlib import Path

from fprime_gds.common.testing_fw import predicates
from fprime_gds.common.utils.event_severity import EventSeverity


FilterSeverity = Enum(
    "FilterSeverity",
    "WARNING_HI WARNING_LO COMMAND ACTIVITY_HI ACTIVITY_LO DIAGNOSTIC",
)


def set_event_filter(fprime_test_api, severity, enabled):
    enabled = "ENABLED" if enabled else "DISABLED"
    if isinstance(severity, FilterSeverity):
        severity = severity.name
    else:
        severity = FilterSeverity[severity].name
    try:
        fprime_test_api.send_command(
            "CdhCore.events.SET_EVENT_FILTER",
            [severity, enabled],
        )
        return True
    except AssertionError:
        return False


def set_default_filters(fprime_test_api):
    set_event_filter(fprime_test_api, "COMMAND", True)
    set_event_filter(fprime_test_api, "ACTIVITY_LO", True)
    set_event_filter(fprime_test_api, "ACTIVITY_HI", True)
    set_event_filter(fprime_test_api, "WARNING_LO", True)
    set_event_filter(fprime_test_api, "WARNING_HI", True)
    set_event_filter(fprime_test_api, "DIAGNOSTIC", False)


# ---------------------------------------------------------------------------
# Telemetry streaming
# ---------------------------------------------------------------------------

def test_is_streaming(fprime_test_api):
    """Verify telemetry is flowing through YAMCS.

    Waits for at least 5 telemetry updates from any channel.
    Tunables: count (5), timeout (10s).
    """
    results = fprime_test_api.assert_telemetry_count(5, timeout=10)
    for result in results:
        msg = "received channel {} update: {}".format(result.get_id(), result.get_str())
        print(msg)


# ---------------------------------------------------------------------------
# CmdDispatcher (Svc.CommandDispatcher -> CdhCore.cmdDisp)
# ---------------------------------------------------------------------------

def test_cmd_no_op(fprime_test_api):
    """Send two NO-OP commands and verify the command history increments.

    Tunables: max_delay (5s).
    """
    fprime_test_api.send_and_assert_command("CdhCore.cmdDisp.CMD_NO_OP", max_delay=5)
    assert fprime_test_api.get_command_test_history().size() == 1
    fprime_test_api.send_and_assert_command("CdhCore.cmdDisp.CMD_NO_OP", max_delay=5)
    assert fprime_test_api.get_command_test_history().size() == 2


def test_cmd_no_op_string(fprime_test_api):
    """Send NO-OP-STRING commands with different payloads and verify the
    NoOpStringReceived event carries the correct argument back.

    Tunables: test strings, max_delay (5s).
    """
    for count, value in enumerate(["Test String 1", "Some other string"], 1):
        events = [
            fprime_test_api.get_event_pred(
                "CdhCore.cmdDisp.NoOpStringReceived", [value]
            )
        ]
        fprime_test_api.send_and_assert_command(
            "CdhCore.cmdDisp.CMD_NO_OP_STRING",
            [value],
            max_delay=5,
            events=events,
        )
        assert fprime_test_api.get_command_test_history().size() == count


def test_cmd_clear_tracking(fprime_test_api):
    """Send CMD_CLEAR_TRACKING and verify dispatch + completion events.

    Tunables: max_delay (5s).
    """
    fprime_test_api.send_and_assert_command(
        "CdhCore.cmdDisp.CMD_CLEAR_TRACKING", max_delay=5
    )


def test_cmd_no_op_ordering(fprime_test_api):
    """Send repeated NO-OPs and verify the three expected events
    (OpCodeDispatched, NoOpReceived, OpCodeCompleted) arrive in order
    with no drops.

    Tunables: length (20 iterations), timeout per iteration (25s).
    """
    length = 20
    failed = 0
    evr_seq = [
        "CdhCore.cmdDisp.OpCodeDispatched",
        "CdhCore.cmdDisp.NoOpReceived",
        "CdhCore.cmdDisp.OpCodeCompleted",
    ]
    any_reordered = False
    dropped = False
    for i in range(length):
        results = fprime_test_api.send_and_await_event(
            "CdhCore.cmdDisp.CMD_NO_OP", events=evr_seq, timeout=25
        )
        msg = "NO_OP trial #{}".format(i)
        if not fprime_test_api.test_assert(len(results) == 3, msg, True):
            items = fprime_test_api.get_event_test_history().retrieve()
            last = None
            reordered = False
            for item in items:
                if last is not None:
                    if item.get_time() < last.get_time():
                        fprime_test_api.log(
                            "iteration #{}: reordered event: {}".format(i, item)
                        )
                        any_reordered = True
                        reordered = True
                        break
                last = item
            if not reordered:
                fprime_test_api.log(
                    "iteration #{}: dropped event".format(i)
                )
                dropped = True
            failed += 1
        fprime_test_api.clear_histories()

    case = True
    case &= fprime_test_api.test_assert(
        not any_reordered, "Expected no events to be reordered.", True
    )
    case &= fprime_test_api.test_assert(
        not dropped, "Expected no events to be dropped.", True
    )
    msg = "{} sequences failed out of {}".format(failed, length)
    case &= fprime_test_api.test_assert(failed == 0, msg, True)
    assert case


# ---------------------------------------------------------------------------
# EventManager (Svc.EventManager -> CdhCore.events)
# ---------------------------------------------------------------------------

def test_event_filter_state(fprime_test_api):
    """Send DUMP_FILTER_STATE and verify the command completes.

    Tunables: max_delay (5s).
    """
    fprime_test_api.send_and_assert_command(
        "CdhCore.events.DUMP_FILTER_STATE", max_delay=5
    )


def test_event_set_id_filter(fprime_test_api):
    """Enable an ID filter for event 0x507, send a NO-OP, then disable it.
    Verifies SET_ID_FILTER commands dispatch and complete through YAMCS.

    Tunables: event ID (0x507), max_delay (5s).
    """
    fprime_test_api.send_and_assert_command(
        "CdhCore.events.SET_ID_FILTER", ["0x507", "ENABLED"], max_delay=5
    )
    fprime_test_api.send_and_assert_command("CdhCore.cmdDisp.CMD_NO_OP", max_delay=5)
    fprime_test_api.send_and_assert_command(
        "CdhCore.events.SET_ID_FILTER", ["0x507", "DISABLED"], max_delay=5
    )


def test_event_severity_filter(fprime_test_api):
    """Verify severity-based event filtering. Sends NO-OPs with COMMAND
    severity enabled and disabled, then checks that COMMAND events appear
    or disappear accordingly while ACTIVITY_HI events always flow.

    Tunables: sleep durations (10s drain, 1.5s flush).
    """
    set_default_filters(fprime_test_api)
    try:
        cmd_events = fprime_test_api.get_event_pred(severity=EventSeverity.COMMAND)
        actHI_events = fprime_test_api.get_event_pred(
            severity=EventSeverity.ACTIVITY_HI
        )
        pred = predicates.greater_than(0)
        zero = predicates.equal_to(0)

        time.sleep(10)
        fprime_test_api.send_and_assert_command("CdhCore.cmdDisp.CMD_NO_OP")
        fprime_test_api.send_and_assert_command("CdhCore.cmdDisp.CMD_NO_OP")
        time.sleep(1.5)

        fprime_test_api.assert_event_count(pred, cmd_events)
        fprime_test_api.assert_event_count(pred, actHI_events)

        set_event_filter(fprime_test_api, FilterSeverity.COMMAND, False)
        time.sleep(10)
        fprime_test_api.clear_histories()
        fprime_test_api.send_command("CdhCore.cmdDisp.CMD_NO_OP")
        fprime_test_api.send_command("CdhCore.cmdDisp.CMD_NO_OP")
        time.sleep(1.5)

        fprime_test_api.assert_event_count(zero, cmd_events)
        fprime_test_api.assert_event_count(pred, actHI_events)
    finally:
        set_default_filters(fprime_test_api)


# ---------------------------------------------------------------------------
# Health (Svc.Health -> CdhCore.$health)
# ---------------------------------------------------------------------------

def test_health_enable_disable(fprime_test_api):
    """Disable and re-enable health monitoring globally.

    Tunables: max_delay (5s).
    """
    fprime_test_api.send_and_assert_command(
        "CdhCore.health.HLTH_ENABLE", ["DISABLED"], max_delay=5
    )
    fprime_test_api.send_and_assert_command(
        "CdhCore.health.HLTH_ENABLE", ["ENABLED"], max_delay=5
    )


def test_health_ping_enable(fprime_test_api):
    """Disable and re-enable health pinging for a specific component
    (FileHandling_fileManager).

    Tunables: component name (FileHandling_fileManager), max_delay (5s).
    """
    fprime_test_api.send_and_assert_command(
        "CdhCore.health.HLTH_PING_ENABLE",
        ["FileHandling_fileManager", "DISABLED"],
        max_delay=5,
    )
    fprime_test_api.send_and_assert_command(
        "CdhCore.health.HLTH_PING_ENABLE",
        ["FileHandling_fileManager", "ENABLED"],
        max_delay=5,
    )


# ---------------------------------------------------------------------------
# Version (Svc.Version -> CdhCore.version)
# ---------------------------------------------------------------------------

def test_version_report(fprime_test_api):
    """Request each version variant and verify the command completes.

    Tunables: variant list, max_delay (5s).
    """
    for variant in ["PROJECT", "FRAMEWORK", "LIBRARY", "CUSTOM", "ALL"]:
        fprime_test_api.send_and_assert_command(
            "CdhCore.version.VERSION", [variant], max_delay=5
        )


def test_version_enable_disable(fprime_test_api):
    """Enable and disable periodic version telemetry.

    Tunables: max_delay (5s).
    """
    fprime_test_api.send_and_assert_command(
        "CdhCore.version.ENABLE", ["ENABLED"], max_delay=5
    )
    fprime_test_api.send_and_assert_command(
        "CdhCore.version.ENABLE", ["DISABLED"], max_delay=5
    )


# ---------------------------------------------------------------------------
# SystemResources (Svc.SystemResources -> systemResources)
# ---------------------------------------------------------------------------

def test_system_resources_telemetry(fprime_test_api):
    """Verify system resource telemetry channels report non-zero values
    for memory and CPU.

    Tunables: timeout (10s), threshold (> 0).
    """
    above_zero = predicates.greater_than(0)
    fprime_test_api.assert_telemetry(
        "systemResources.MEMORY_TOTAL", above_zero, timeout=10
    )
    fprime_test_api.assert_telemetry(
        "systemResources.MEMORY_USED", above_zero, timeout=10
    )
    fprime_test_api.assert_telemetry(
        "systemResources.NON_VOLATILE_TOTAL", above_zero, timeout=10
    )
    fprime_test_api.assert_telemetry(
        "systemResources.CPU", predicates.greater_than(0.0), timeout=10
    )


def test_system_resources_enable_disable(fprime_test_api):
    """Disable and re-enable periodic system resource reporting.

    Tunables: max_delay (5s).
    """
    fprime_test_api.send_and_assert_command(
        "systemResources.ENABLE", ["DISABLED"], max_delay=5
    )
    fprime_test_api.send_and_assert_command(
        "systemResources.ENABLE", ["ENABLED"], max_delay=5
    )


# ---------------------------------------------------------------------------
# FileManager (Svc.FileManager -> FileHandling.fileManager)
# ---------------------------------------------------------------------------

def test_file_manager_create_remove_directory(fprime_test_api):
    """Create a temporary directory on the target and then remove it.

    Tunables: directory path (/tmp/yamcs_test_dir), max_delay (10s).
    """
    fprime_test_api.send_and_assert_command(
        "FileHandling.fileManager.CreateDirectory", ["/tmp/yamcs_test_dir"], max_delay=10
    )
    fprime_test_api.send_and_assert_command(
        "FileHandling.fileManager.RemoveDirectory", ["/tmp/yamcs_test_dir"], max_delay=10
    )


def test_file_manager_file_size(fprime_test_api):
    """Query the size of test_file.txt on the target filesystem.

    Tunables: file path (test_file.txt alongside this script), max_delay (10s).
    """
    test_file = Path(__file__).parent / "test_file.txt"
    fprime_test_api.send_and_assert_command(
        "FileHandling.fileManager.FileSize", [str(test_file)], max_delay=10
    )


# ---------------------------------------------------------------------------
# FileDownlink (Svc.FileDownlink -> FileHandling.fileDownlink)
# ---------------------------------------------------------------------------

def test_file_downlink_send_file(fprime_test_api):
    """Request a file downlink of test_file.txt to a destination filename.

    Tunables: source file (test_file.txt), dest name (yamcs_test_dl.txt),
    max_delay (30s).
    """
    test_file = Path(__file__).parent / "test_file.txt"
    fprime_test_api.send_and_assert_command(
        "FileHandling.fileDownlink.SendFile",
        [str(test_file), "yamcs_test_dl.txt"],
        max_delay=30,
    )


def test_file_downlink_cancel(fprime_test_api):
    """Send a Cancel command to FileDownlink.

    Tunables: max_delay (5s).
    """
    fprime_test_api.send_and_assert_command(
        "FileHandling.fileDownlink.Cancel", max_delay=5
    )


# ---------------------------------------------------------------------------
# FileUplink (Svc.FileUplink -> FileHandling.fileUplink)
# ---------------------------------------------------------------------------

def test_file_uplink(fprime_test_api):
    """Verify the FileUplink PacketsReceived telemetry channel is updating.

    Tunables: timeout (10s).
    """
    fprime_test_api.send_and_assert_command("CdhCore.cmdDisp.CMD_NO_OP", max_delay=5)
    fprime_test_api.assert_telemetry_count(
        1, channels="FileHandling.fileUplink.PacketsReceived", timeout=10
    )


# ---------------------------------------------------------------------------
# CmdSequencer (Svc.CmdSequencer -> cmdSeq)
# ---------------------------------------------------------------------------

def test_cmd_sequencer_validate(fprime_test_api):
    """Send CS_VALIDATE for a nonexistent file. The command dispatches
    through YAMCS but validation fails on the target — proves the
    sequencer command path works.

    Tunables: file path (/tmp/nonexistent.bin), max_delay (5s).
    """
    fprime_test_api.send_and_assert_command(
        "cmdSeq.CS_VALIDATE", ["/tmp/nonexistent.bin"], max_delay=5
    )
