from argparse import ArgumentTypeError
from contextlib import contextmanager

from btheadset import (
    BTHeadsetError,
    BluetoothAddress,
    connect_device,
    get_card_index,
    get_sink_index,
    wait_until_connected,
)

import pytest


@contextmanager
def does_not_raise():
    yield


@pytest.mark.parametrize(
    "bluetooth_address,expectation",
    [
        ("11:22:33:44:55:66", does_not_raise()),
        ("aa:bb:cc:dd:ee:ff", does_not_raise()),
        ("AA:BB:CC:DD:EE:FF", does_not_raise()),
        ("aa:bb:cc:DD:EE:FF", does_not_raise()),
        ("00:11:aa:bb:CC:DD", does_not_raise()),
        (0, pytest.raises(ArgumentTypeError)),
        ("foo", pytest.raises(ArgumentTypeError)),
        ("00:11:22", pytest.raises(ArgumentTypeError)),
        ("00:00:00:00:00:xx", pytest.raises(ArgumentTypeError)),
    ],
)
def test_bluetooth_address(bluetooth_address, expectation):
    with expectation:
        assert BluetoothAddress()(bluetooth_address) == bluetooth_address.upper()


@pytest.mark.parametrize(
    "bluetooth_address,stdout,expectation",
    [
        (
            "11:22:33:44:55:66",
            b"Attempting to connect to 11:22:33:44:55:66",
            does_not_raise(),
        ),
        (
            "AA:BB:CC:DD:EE:FF",
            b"Device AA:BB:CC:DD:EE:FF not available",
            pytest.raises(BTHeadsetError),
        ),
    ],
)
def test_connect_device(mocker, bluetooth_address, stdout, expectation):
    run = mocker.patch("subprocess.run")
    run.return_value.stdout = stdout
    with expectation:
        connect_device(bluetooth_address)
    assert run.call_count == 1


@pytest.mark.parametrize(
    "bluetooth_address,stdout,expectation",
    [
        ("11:22:33:44:55:66", b"Connected: yes", does_not_raise(),),
        ("AA:BB:CC:DD:EE:FF", b"", pytest.raises(BTHeadsetError),),
    ],
)
def test_wait_until_connected(mocker, bluetooth_address, stdout, expectation):
    run = mocker.patch("subprocess.run")
    run.return_value.stdout = stdout
    with expectation:
        # TODO(jirib): Mock the datetime to avoid the unnecessary 1s delay when
        # running this test.
        wait_until_connected(bluetooth_address, 1)
    assert run.called


@pytest.mark.parametrize(
    "bluetooth_address,stdout,expectation",
    [
        (
            "11:22:33:44:55:66",
            b"index: 1\nname: <bluez_card.11_22_33_44_55_66>",
            does_not_raise(),
        ),
        ("AA:BB:CC:DD:EE:FF", b"", pytest.raises(BTHeadsetError),),
    ],
)
def test_get_card_index(mocker, bluetooth_address, stdout, expectation):
    run = mocker.patch("subprocess.run")
    run.return_value.stdout = stdout
    with expectation:
        assert get_card_index(bluetooth_address) == "1"
    assert run.called


@pytest.mark.parametrize(
    "bluetooth_address,stdout,expectation",
    [
        (
            "11:22:33:44:55:66",
            b"index: 1\nname: <bluez_sink.11_22_33_44_55_66.a2dp_sink>",
            does_not_raise(),
        ),
        ("AA:BB:CC:DD:EE:FF", b"", pytest.raises(BTHeadsetError),),
    ],
)
def test_get_sink_index(mocker, bluetooth_address, stdout, expectation):
    run = mocker.patch("subprocess.run")
    run.return_value.stdout = stdout
    with expectation:
        assert get_sink_index(bluetooth_address, "a2dp_sink") == "1"
    assert run.called
