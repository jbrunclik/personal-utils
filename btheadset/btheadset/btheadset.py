#!/usr/bin/env python
"""Connect to a Bluetooth headset and use it as the default output sink."""

import logging
import re
import subprocess
from argparse import ArgumentParser, ArgumentTypeError
from datetime import datetime


class BTHeadsetError(Exception):
    pass


class BluetoothAddress:
    RE_BT_ADDRESS = re.compile("^([0-9a-f]{2}:){5}([0-9a-f]{2})$", re.IGNORECASE)

    @classmethod
    def __call__(cls, value):
        value = str(value)
        if not cls.RE_BT_ADDRESS.match(value):
            raise ArgumentTypeError(f'"{value}" is not a valid Bluetooth Address')
        return value.upper()


def __parse_args():
    parser = ArgumentParser(
        description="Connect a Bluetooth headset and use it as the default output sink"
    )
    parser.add_argument(
        "-b",
        "--bluetooth-address",
        type=BluetoothAddress(),
        required=True,
        help="Bluetooth Address of the headset",
    )
    parser.add_argument(
        "-c",
        "--connect-timeout",
        type=int,
        default=5,
        help="Bluetooth connect timeout (seconds)",
    )
    parser.add_argument(
        "-p",
        "--card-profile",
        type=str,
        default="a2dp_sink",
        help="Headset Bluetooth profile",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="enable verbose mode"
    )
    return parser.parse_args()


def connect_device(bluetooth_address):
    """Connect to the headset."""
    logging.info(f'Connecting to Bluetooth headset "{bluetooth_address}"')
    p = subprocess.run(
        ["/usr/bin/env", "bluetoothctl"],
        input=f"connect {bluetooth_address}".encode("utf-8"),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if f"Device {bluetooth_address} not available" in p.stdout.decode("utf-8"):
        raise BTHeadsetError(
            f'Bluetooth headset "{bluetooth_address}" is not available'
        )


def wait_until_connected(bluetooth_address, connect_timeout):
    """Busy wait until the headset gets connected (or until timeout)."""
    start = datetime.now()
    while (datetime.now() - start).total_seconds() < connect_timeout:
        p = subprocess.run(
            ["/usr/bin/env", "bluetoothctl"],
            input=f"info {bluetooth_address}".encode("utf-8"),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if "Connected: yes" in p.stdout.decode("utf-8"):
            logging.info(
                f'Successfully connected to Bluetooth headset "{bluetooth_address}"'
            )
            return
    raise BTHeadsetError(
        f'Timeout connecting to Bluetoot headset "{bluetooth_address}"'
    )


def get_card_index(bluetooth_address):
    """Get PulseAudio card index for the given headset."""
    card_name = f"bluez_card.{bluetooth_address.replace(':', '_')}"
    logging.debug(f'Getting card index of "{card_name}"')
    p = subprocess.run(
        ["/usr/bin/env", "pacmd", "list-cards"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    m = re.search(
        fr"index: (?P<card_index>\d+)\s*name: <{card_name}>",
        p.stdout.decode("utf-8"),
        re.MULTILINE,
    )
    if m is None:
        raise BTHeadsetError(f'Unable to find card index of "{card_name}"')
    card_index = m.group("card_index")
    logging.debug(f'Card "{card_name} has index {card_index}')
    return card_index


def set_card_profile(card_index, profile):
    """Set profile on a card to the given value."""
    logging.info(f'Setting card profile of {card_index} to "{profile}"')
    subprocess.run(
        ["/usr/bin/env", "pacmd", "set-card-profile", card_index, "off"], check=True,
    )
    subprocess.run(
        ["/usr/bin/env", "pacmd", "set-card-profile", card_index, profile], check=True,
    )


def get_sink_index(bluetooth_address, profile):
    """Get PulseAudio sink index for the given headset."""
    sink_name = f"bluez_sink.{bluetooth_address.replace(':', '_')}.{profile}"
    logging.debug(f'Getting sink index of "{sink_name}"')
    p = subprocess.run(
        ["/usr/bin/env", "pacmd", "list-sinks"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    m = re.search(
        fr"index: (?P<sink_index>\d+)\s*name: <{sink_name}>",
        p.stdout.decode("utf-8"),
        re.MULTILINE,
    )
    if m is None:
        raise BTHeadsetError(f'Unable to find sink index of "{sink_name}"')
    sink_index = m.group("sink_index")
    logging.debug(f'Sink "{sink_name} has index {sink_index}')
    return sink_index


def set_default_sink(sink_index):
    """Set default output sink."""
    logging.info(f"Setting default output sink to {sink_index}")
    subprocess.run(
        ["/usr/bin/env", "pacmd", "set-default-sink", sink_index], check=True,
    )


def main():
    # Parse command-line arguments.
    args = __parse_args()

    # Configure logging.
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level)

    # Connect to the headset.
    connect_device(args.bluetooth_address)
    wait_until_connected(args.bluetooth_address, args.connect_timeout)

    # Get headset card index.
    card_index = get_card_index(args.bluetooth_address)

    # Set headset card profile.
    set_card_profile(card_index, args.card_profile)

    # Get headset sink index.
    sink_index = get_sink_index(args.bluetooth_address, args.card_profile)

    # Set default sink.
    set_default_sink(sink_index)


if __name__ == "__main__":
    main()
