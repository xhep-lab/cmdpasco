"""
Command prompt for PASCO devices
================================
"""

import time
import re
from functools import wraps

import cmd2
import matplotlib.pyplot as plt
import numpy as np
import pasco
from rich.console import Console


console = Console()


def positive_float(x):
    y = float(x)
    assert y > 0
    return y


def redraw(period):
    plt.gca().relim()
    plt.gca().autoscale_view()
    plt.draw()
    plt.pause(period)


def device_id(device):
    name_parts = device.name.rsplit(' ', 1)
    return name_parts[1][0:7]


class line_regex:
    def __init__(self, regex, example):
        self.r = re.compile(regex)
        self.example = example
        assert self.r.match(example) is not None

    def __call__(self, func):
        @wraps(func)
        def line_regex_func(this, line):
            line = str(line)
            if self.r.match(line) is None:
                expected = func.__name__[3:] + " " + self.example
                console.print(
                    f"Argument error. Expected e.g.\n\n{expected}",
                    style="bold red")
                return False
            return func(this, line)
        return line_regex_func


class line_types:
    def __init__(self, *types):
        self.types = types

    def __call__(self, func):
        @wraps(func)
        def line_types_func(this, line):
            parts = line.split()
            try:
                assert len(parts) == len(self.types)
                converted = [t(p) for t, p in zip(self.types, parts)]
            except BaseException:
                expected = func.__name__[3:] + " " + \
                    " ".join([t.__name__ for t in self.types])
                console.print(
                    f"Argument error. Expected\n\n{expected}",
                    style="bold red")
                return False
            return func(this, *converted)
        return line_types_func


def line_none(func):
    @wraps(func)
    def line_none_func(this, line):
        if line:
            expected = func.__name__[3:]
            console.print(
                f"Argument error. Expected\n\n{expected} # no arguments",
                style="bold red")
            return False
        return func(this)

    return line_none_func


def require_connection(func):
    @wraps(func)
    def require_connection_func(this, *args, **kwargs):
        if not this.devices:
            console.print("No connected devices", style="bold red")
            return False
        return func(this, *args, **kwargs)
    return require_connection_func


class PASCOShell(cmd2.Cmd):
    intro = 'Welcome to the PASCO shell. Type help or ? to list commands.\n'
    default_prompt = '(disconnected) '
    _devices = {}

    @line_none
    def do_quit(self):
        "Quit the PASCO shell"
        self.disconnect()
        return True

    @property
    def devices(self):
        for name, device in self._devices.copy().items():
            if not device.is_connected():
                console.print(
                    f"Device {device.name} disconnected", style="bold red")
                del self._devices[name]
        return self._devices

    @property
    def prompt(self):
        if self.devices:
            ids_ = ", ".join([device.name for device in self.devices.values()])
            return f"({ids_}) "
        return self.default_prompt

    @line_regex(r'^\s*\d\d\d-\d\d\d\s*$', '344-124')
    def do_connect(self, id_):
        """
        Connect by ID number written on device

        @param id_ ID number on device with form e.g., 344-124
        """
        device = pasco.PASCOBLEDevice()

        try:
            device.connect_by_id(id_)
        except Exception as e:
            console.print(f"Connection failed: {repr(e)}", style="bold red")
            return

        device.measurements = device.get_measurement_list()
        self._devices[id_] = device
        console.print(f"Device {device.name} connected", style="bold green")

    def disconnect(self):
        "Disconnect devices"
        for device in self.devices.values():
            device.disconnect()
        self.devices.clear()

    @line_none
    def do_disconnect(self):
        "Disconnect devices"
        self.disconnect()

    @require_connection
    @line_none
    def do_info(self):
        "Summarize available measurements and sensors"
        with console.pager():
            console.print(self.info())

    def info(self):
        info = {}
        for id_, device in self.devices.items():
            info[device.name] = {}
            for sensor in device.get_sensor_list():
                info[device.name][sensor] = {}
                for measurement in device.get_measurement_list(sensor):
                    sensor_id = device._measurement_sensor_ids[measurement]
                    for m in device._device_measurements[sensor_id].values():
                        if m['NameTag'] == measurement:
                            info[device.name][sensor][measurement] = m
                            break
        return info

    @line_none
    def do_scan(self):
        "Scan for bluetooth PASCO devices"
        dummy = pasco.PASCOBLEDevice()

        try:
            scan = dummy.scan()
        except Exception as e:
            console.print(f"Scan failed: {repr(e)}", style="bold red")
            return

        devices = {device.name: device_id(device) for device in scan}

        if devices:
            console.print(devices)
        else:
            console.print("No devices found", style="bold red")

    def _header(self):
        labels = [f"{device.name} {m} ({device.get_measurement_unit(m)})" for device in self.devices.values() for m in
                  device.measurements]
        return ", ".join(labels)

    @require_connection
    @line_types(positive_float)
    def do_record(self, period):
        """
        Record data from devices to disk

        @param period Period in seconds between measurements
        """
        def record():
            line = []
            before = time.time()

            for device in self.devices.values():
                result = device.read_data_list(device.measurements)
                line += [result[k] for k in device.measurements]

            after = time.time()
            timing = 0.5 * (before + after)
            return [timing] + line

        start = time.time()
        data = []

        with console.status("Recording data. Press Ctrl-C to stop...", spinner_style="red bold"):
            try:
                while True:
                    data.append(record())
                    time.sleep(period)
            except KeyboardInterrupt:
                pass

        if not data:
            console.print(f"No data recorded", style="bold")
            return

        data = np.array(data, dtype=float)
        data[:, 0] -= start
        file_name = time.strftime("cmdpasco_data_%Y_%m_%d_%H_%M_%S.txt")
        np.savetxt(file_name, data, header=self._header(), delimiter=",")
        console.print(f"Saved data to {file_name}", style="bold")

    @require_connection
    @line_types(positive_float, str)
    def do_watch(self, period, measurement):
        """
        Watch data accumulate in real time

        @param period Period in seconds between measurements
        @param measurement Measurement to watch
        """
        devices = {name: device for name, device in self.devices.items(
        ) if measurement in device.measurements}

        if not devices:
            console.print(
                f"No devices support measurement {measurement}",
                style="bold red")
            return

        data_x = [np.nan]
        data_y = [[np.nan]] * len(devices)
        unit_x = list(devices.values())[0].get_measurement_unit(measurement)

        plt.ion()
        lines = plt.plot(data_x, data_y, label=devices.keys())
        plt.legend()
        plt.xlabel("Time (s)")
        plt.ylabel(f"{measurement} ({unit_x})")
        plt.draw()

        def watch():
            before = time.time()
            data = [device.read_data(measurement)
                    for device in devices.values()]
            after = time.time()
            timing = 0.5 * (before + after)
            return [timing] + data

        start = time.time()

        with console.status("Watching data stream. Press Ctrl-C to stop...", spinner_style="bold blue"):
            try:
                while True:
                    stream = watch()

                    data_x.append(stream[0] - start)

                    for line, y, s in zip(lines, data_y, stream[1:]):
                        y.append(s)
                        line.set_data(data_x, y)

                    redraw(period)

            except KeyboardInterrupt:
                pass

        file_name = time.strftime("cmdpasco_data_%Y_%m_%d_%H_%M_%S.pdf")
        plt.savefig(file_name)
        console.print(f"Saved figure to {file_name}", style="bold")
        plt.close()
        plt.ioff()


def cli():
    PASCOShell().cmdloop()


if __name__ == '__main__':
    cli()
