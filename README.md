# Performance Monitor

A cross-platform desktop application built using PySide6 to monitor system metrics including CPU, Memory, and GPU performance.

It was developed to always have vital systems parameters in view while working with AI.

## Features
- **Real-time Monitoring**: Displays CPU usage, memory usage, GPU utilization, clock speed, temperature, VRAM usage, and power draw.
- **GPU Support**: Retrieves GPU statistics using either, depending on what is available, NVIDIA Management Library (NVML) and `nvidia-smi` for data collection.
- **Compatibility**: The tool was developed on Linux for Linux. It propably also runs on macOS, and Windows.

## Installation
1. Make sure Python 3.10 or higher must be installed on your system.
2. Install all requirements from requirements.txt `pip install -r requirements.txt`
3. Run the app `python3 PerMonitor.py`

## Contributing
You are welcome to contribute! If you have any improvements or bug fixes, please fork the repository, make your changes, and submit a pull request.

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.