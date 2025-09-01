<h1 align="center">
 🚙🚗 cmdpasco
</h1>

<h3 align="center">
<i>Command prompt interface to PASCO Bluetooth devices</i>
</h3>

<div align="center">
  
[![GitHub License](https://img.shields.io/github/license/xhep-lab/cmdpasco?style=for-the-badge)](https://github.com/cmdpasco/stanhf?tab=GPL-3.0-1-ov-file#)
[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/xhep-lab/cmdpasco/python-app.yml?style=for-the-badge)](https://github.com/xhep-lab/cmdpasco/actions)
</div>


<br>

This is a low-level, cross-platform command prompt interface to PASCO Bluetooth devices. There are commands to scan, connect, disconnect and record data from devices etc.

## ✨ Install

The code aims to be cross-platform. Installation by

    pipx install git+https://github.com/xhep-lab/cmdpasco.git

## 📈 Run

Start the command prompt by

    cmdpasco

For help, enter `?` or `help` at the prompt. There are commands for

- `scan`: scan for available PASCO Bluetooth devices
- `connect`: connect to a PASCO Bluetooth device using the six-digit device code
- `info`: show information about connected devices
- `record`: record data from connected devices to disk
- `watch`: plot data from connected devices in real time

## 💡 Contribute

Contributions are strongly enouraged, especially from students using PASCO devices. Possibilities include:

- installation by Conda
- `watch` command that supports multiple measurements to watch
- `record` command that allows recorded data to be filtered
- Mock devices for testing - it's hard to develop the code as you have to have a PASCO device handy. Can we have a mock device for testing?
- And of course bug fixes!
  
Please feel free to make a pull request or raise an issue.
