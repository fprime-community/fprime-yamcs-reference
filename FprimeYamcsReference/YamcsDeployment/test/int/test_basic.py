"""YAMCS transport integration tests for YamcsDeployment."""

import time
from enum import Enum

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


def test_is_streaming(fprime_test_api):
    results = fprime_test_api.assert_telemetry_count(5, timeout=10)
    for result in results:
        msg = "received channel {} update: {}".format(result.get_id(), result.get_str())
        print(msg)


def test_cmd_no_op(fprime_test_api):
    fprime_test_api.send_and_assert_command("CdhCore.cmdDisp.CMD_NO_OP", max_delay=5, timeout=15)
    assert fprime_test_api.get_command_test_history().size() == 1
    prev = fprime_test_api.get_command_test_history().size()
    fprime_test_api.send_and_assert_command("CdhCore.cmdDisp.CMD_NO_OP", max_delay=5, timeout=15)
    assert fprime_test_api.get_command_test_history().size() == prev + 1


def test_cmd_no_op_string(fprime_test_api):
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
            timeout=15,
            events=events,
        )
        assert fprime_test_api.get_command_test_history().size() == count


def test_cmd_no_op_ordering(fprime_test_api):
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


def test_event_severity_filter(fprime_test_api):
    set_default_filters(fprime_test_api)
    try:
        cmd_events = fprime_test_api.get_event_pred(severity=EventSeverity.COMMAND)
        actHI_events = fprime_test_api.get_event_pred(
            severity=EventSeverity.ACTIVITY_HI
        )
        pred = predicates.greater_than(0)
        zero = predicates.equal_to(0)

        time.sleep(10)
        fprime_test_api.send_and_assert_command("CdhCore.cmdDisp.CMD_NO_OP", timeout=15)
        fprime_test_api.send_and_assert_command("CdhCore.cmdDisp.CMD_NO_OP", timeout=15)
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


def test_health_ping_enable(fprime_test_api):
    fprime_test_api.send_and_assert_command(
        "CdhCore.health.HLTH_PING_ENABLE",
        ["FileHandling_fileManager", "DISABLED"],
        max_delay=5,
        timeout=15,
    )
    fprime_test_api.send_and_assert_command(
        "CdhCore.health.HLTH_PING_ENABLE",
        ["FileHandling_fileManager", "ENABLED"],
        max_delay=5,
        timeout=15,
    )


def test_file_manager_create_remove_directory(fprime_test_api):
    fprime_test_api.send_and_assert_command(
        "FileHandling.fileManager.CreateDirectory", ["/tmp/yamcs_test_dir"], max_delay=10, timeout=15
    )
    fprime_test_api.send_and_assert_command(
        "FileHandling.fileManager.RemoveDirectory", ["/tmp/yamcs_test_dir"], max_delay=10, timeout=15
    )


def test_file_manager_file_size(fprime_test_api):
    fprime_test_api.send_and_assert_command(
        "FileHandling.fileManager.FileSize",
        ["/tmp/test_file.txt"],
        max_delay=10,
        timeout=15,
    )


def test_file_downlink_send_file(fprime_test_api):
    fprime_test_api.send_and_assert_command(
        "FileHandling.fileDownlink.SendFile",
        ["/tmp/test_file.txt", "/tmp/yamcs_dl.txt"],
        max_delay=30,
        timeout=35,
    )


def test_file_uplink(fprime_test_api):
    fprime_test_api.send_and_assert_command("CdhCore.cmdDisp.CMD_NO_OP", max_delay=5, timeout=15)
    fprime_test_api.assert_telemetry_count(
        1, channels="FileHandling.fileUplink.PacketsReceived", timeout=10
    )


def test_cmd_sequencer_validate(fprime_test_api):
    fprime_test_api.send_command(
        "FprimeYamcsReference.cmdSeq.CS_VALIDATE", ["/tmp/nonexistent.bin"]
    )
    result = fprime_test_api.await_event(
        "FprimeYamcsReference.cmdSeq.CS_FileNotFound", timeout=5
    )
    assert result is not None
