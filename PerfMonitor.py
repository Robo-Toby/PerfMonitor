from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QGroupBox, QPushButton, QMessageBox
from PySide6.QtCore import Qt, QTimer
import psutil
import subprocess
import os
import platform

# ---------- Constants -----------------------------------------------
CPU_MAX_TEMP = 95   # 95°C for AMD Ryzen 5000 Series
GPU_MAX_TEMP = 90   # 90°C for many, but also RTX 5070Ti
GPU_BASE_CLK = 2300 # 2300 MHz Base Clock for RTX 5070Ti

# ---------- GPU helper ---------------------------------------------
try:
    import pynvml
    _NVML_AVAILABLE = True
except ImportError:          
    _NVML_AVAILABLE = False

def _gpu_stats() -> dict:
    """
    Return a dictionary containing:
    * ``util``       average GPU utilisation (0-100 %).
    * ``vram``       average VRAM utilisation (0-100 %).
    * ``vram_used``  average VRAM used (MiB).
    * ``vram_total`` average VRAM total (MiB).
    * ``clock``      average GPU graphics clock (MHz). 0 if unavailable.
    * ``name``       GPU name.
    * ``temperature``  average GPU temperature (°C).
    * ``power_usage``  average power consumption (W).
    * ``max_power_limit``  max power limit (W).
    The function first attempts to use the NVML (pynvml) API; on any
    exception it falls back to ``nvidia-smi``.  If neither method works,
    all values default to ``0``.
    """
    util_avg = 0
    vram_avg = 0
    vram_used_avg = 0
    vram_total_avg = 0
    clock_avg = 0
    name = ""
    temperature_avg = 0
    power_usage_avg = 0
    max_power_limit_avg = 0
    # ------------------------------------------------------------
    # NVML (pynvml) path
    # ------------------------------------------------------------
    if _NVML_AVAILABLE:
        try:
            pynvml.nvmlInit()
            count = pynvml.nvmlDeviceGetCount()
            if count > 0:
                util_sum = 0
                vram_sum = 0
                used_sum = 0
                total_sum = 0
                clock_sum = 0
                temperature_sum = 0
                power_usage_sum = 0
                max_power_limit_sum = 0
                for i in range(count):
                    h = pynvml.nvmlDeviceGetHandleByIndex(i)
                    # GPU utilisation
                    util_sum += pynvml.nvmlDeviceGetUtilizationRates(h).gpu
                    # VRAM utilisation (percent)
                    mem = pynvml.nvmlDeviceGetMemoryInfo(h)
                    vram_sum += int((mem.used / mem.total) * 100) if mem.total else 0
                    # Absolute VRAM (MiB)
                    used_sum += mem.used // (1024 * 1024)
                    total_sum += mem.total // (1024 * 1024)
                    # Graphics clock (MHz)
                    try:
                        clock_sum += pynvml.nvmlDeviceGetClockInfo(h, pynvml.NVML_CLOCK_GRAPHICS)
                    except Exception:
                        pass  # ignore if clock info not available
                    # GPU name
                    name = pynvml.nvmlDeviceGetName(h).decode("utf-8")
                    # Temperature (°C)
                    temperature_sum += pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
                    # Power usage (W)
                    power_usage_sum += pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0
                    # Max power limit (W)
                    max_power_limit_sum += pynvml.nvmlDeviceGetEnforcedPowerLimit(h) / 1000.0
                util_avg = int(util_sum / count)
                vram_avg = int(vram_sum / count)
                vram_used_avg = int(used_sum / count)
                vram_total_avg = int(total_sum / count)
                clock_avg = int(clock_sum / count) if count else 0
                temperature_avg = int(temperature_sum / count) if count else 0
                power_usage_avg = float(power_usage_sum / count) if count else 0.0
                max_power_limit_avg = float(max_power_limit_sum / count) if count else 0.0
            else:
                raise RuntimeError("NVML reports 0 GPUs")
        except Exception:
            # Fall back to nvidia‑smi below
            pass
    # ------------------------------------------------------------
    # nvidia‑smi fallback
    # ------------------------------------------------------------
    if util_avg == 0 or vram_avg == 0 or vram_used_avg == 0 or vram_total_avg == 0:
        try:
            cmd = [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total,clocks.current.graphics,name,temperature.gpu,power.draw,power.limit",
                "--format=csv,noheader,nounits",
            ]
            output = subprocess.check_output(cmd, encoding="utf-8")
            lines = output.strip().split("\n")
            util_vals = []
            used_vals = []
            total_vals = []
            clock_vals = []
            name_vals = []
            temperature_vals = []
            power_usage_vals = []
            max_power_limit_vals = []
            for line in lines:
                parts = [x.strip() for x in line.split(",")]
                if len(parts) == 8:
                    util, used, total, clock, gpu_name, temperature, power_usage, max_power_limit = parts
                    util_vals.append(int(util))
                    used_vals.append(int(used))
                    total_vals.append(int(total))
                    clock_vals.append(int(clock))
                    name_vals.append(gpu_name)
                    temperature_vals.append(int(temperature))
                    power_usage_vals.append(float(power_usage))
                    max_power_limit_vals.append(float(max_power_limit))
                else:
                    # Unexpected column count – skip this line
                    continue
            count = len(util_vals)
            if count:
                util_avg = int(sum(util_vals) / count)
                vram_used_avg = int(sum(used_vals) / count)
                vram_total_avg = int(sum(total_vals) / count)
                vram_avg = int(sum([u / t * 100 for u, t in zip(used_vals, total_vals)]) / count) if count else 0
                clock_avg = int(sum(clock_vals) / count)
                name = name_vals[0] if count else ""
                temperature_avg = int(sum(temperature_vals) / count) if count else 0
                power_usage_avg = float(sum(power_usage_vals) / count) if count else 0.0
                max_power_limit_avg = float(sum(max_power_limit_vals) / count) if count else 0.0
        except Exception:
            # If even the fallback fails, keep all averages at 0
            pass
    return {
        "util": util_avg,
        "vram": vram_avg,
        "vram_used": vram_used_avg,
        "vram_total": vram_total_avg,
        "clock": clock_avg,
        "name": name,
        "temperature": temperature_avg,
        "power_usage": power_usage_avg,
        "max_power_limit": max_power_limit_avg,
    }

def get_cpu_temperature() -> float:
    """returns avg (accross CCDs and Ctl.) CPU Temp for AMD CPUs (float)
        or None, in case of failure"""
    temps = psutil.sensors_temperatures()
    if 'k10temp' in temps:
        core_temp_sensors = temps['k10temp']
        avg_temperature = sum(sensor.current for sensor in core_temp_sensors) / len(core_temp_sensors)
        return avg_temperature
    return None

# ------------------------------------------------------------------
#  Helper class – a single gauge + label for one metric
# ------------------------------------------------------------------
class GaugeWidget(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        # ----- UI --------------------------------------------------
        self.layout = QVBoxLayout(self)
        self.label = QLabel(title, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)          # percent
        self.progress.setTextVisible(True)      # show the numeric value
        self.progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.progress)

    def set_value(self, percent: int, label: str = None):
        self.progress.setValue(percent)
        if label is not None:
            self.label.setText(label)
# ------------------------------------------------------------------
#  Main window – assemble several GaugeWidgets in a QVBoxLayout
# ------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PerfMonitor")
        
        # ----- Central widget & main layout -----------------------
        central = QWidget(self)
        self.setCentralWidget(central)
        
        # Main horizontal layout
        self.main_layout = QHBoxLayout(central)

        # ----- CPU group ------------------------------------------
        cpu_group = QGroupBox("CPU")
        cpu_layout = QVBoxLayout(cpu_group)
        self.cpu_label = QLabel("CPU:")
        self.cpu_gauge = GaugeWidget("CPU %")
        cpu_layout.addWidget(self.cpu_label)
        cpu_layout.addWidget(self.cpu_gauge)
        self.cpu_temp_gauge = GaugeWidget("CPU Temp")
        cpu_layout.addWidget(self.cpu_temp_gauge)
        cpu_group.setLayout(cpu_layout)

        # ----- Memory group ----------------------------------------
        mem_group = QGroupBox("Memory")
        mem_layout = QVBoxLayout(mem_group)
        self.mem_label = QLabel("RAM:")
        self.mem_gauge = GaugeWidget("RAM %")
        mem_layout.addWidget(self.mem_label)
        mem_layout.addWidget(self.mem_gauge)
        mem_group.setLayout(mem_layout)

        # ----- GPU group ------------------------------------------
        gpu_name = _gpu_stats().get("name", "GPU")
        gpu_group = QGroupBox(gpu_name)
        gpu_layout = QVBoxLayout(gpu_group)
        self.gpu_gauge = GaugeWidget("GPU %")
        gpu_layout.addWidget(self.gpu_gauge)
        self.gpu_clock_gauge = GaugeWidget("GPU Clock (MHz)")
        gpu_layout.addWidget(self.gpu_clock_gauge)
        self.gpu_temp_gauge = GaugeWidget("GPU Temp")
        gpu_layout.addWidget(self.gpu_temp_gauge)
        self.gpu_mem_gauge = GaugeWidget("VRAM %")
        gpu_layout.addWidget(self.gpu_mem_gauge)
        self.gpu_power_gauge = GaugeWidget("GPU Power:")
        gpu_layout.addWidget(self.gpu_power_gauge)
        gpu_group.setLayout(gpu_layout)

        # ----- Ollama GPU/CPU Toggle --------------------------------------
        self.restart_ollama = QPushButton("Restart Ollama (empty VRAM)")
        self.restart_ollama.clicked.connect(self.restart_ollama_service)

        # Add CPU and Memory groups to a vertical layout on the left
        left_layout = QVBoxLayout()
        left_layout.addWidget(cpu_group)
        left_layout.addWidget(mem_group)
        left_layout.addWidget(self.restart_ollama)

        # Add both layouts (left and GPU) to the main horizontal layout
        self.main_layout.addLayout(left_layout)
        self.main_layout.addWidget(gpu_group)

        # ----- Timer to update the gauges every 500 ms ---------------------
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_metrics)
        self.timer.start(500)
        self.show()

    def restart_ollama_service(self):
        """Attempt to restart the Ollama backend on Linux."""
        system = platform.system()
        try:
            if system == "Linux":
                # --- 1. Try user service first (may fail silently) ---
                result = subprocess.run(
                    ["systemctl", "--user", "restart", "ollama"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                if result.returncode == 0:
                    return True
                # --- 2. Fallback: system-wide service ---
                result = subprocess.run(
                    ["systemctl", "restart", "ollama"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                if result.returncode == 0:
                    return True
                # --- Neither worked ---
                raise RuntimeError(
                    f"systemctl returned errors:\n\n"
                    f"--user: {result.stderr.decode('utf-8')}"
                )
            else:
                raise RuntimeError("Unsupported OS")
        except Exception as e:
            QMessageBox.warning(self, "Restart Failed", f"Could not restart Ollama:\n{e}")
            return False
        
    # ------------------------------------------------------------------
    #  Update the gauges from psutil (CPU) and NVML (GPU)
    # ------------------------------------------------------------------
    def update_metrics(self):
        
        # ----- CPU ------------------------------------------
        cpu_pct = psutil.cpu_percent(interval=None)
        self.cpu_gauge.set_value(cpu_pct)

        # CPU Temperature
        cpu_temp = get_cpu_temperature() 
        # Normalize CPU temperature to a scale of [0, 100] and set the label
        self.cpu_temp_gauge.set_value(
            min(max(cpu_temp / CPU_MAX_TEMP * 100, 0), 100),
            label=f"CPU Temp: {round(cpu_temp, 2)}°C"
        )

        # ----- GPU ------------------------------------------
        stats = _gpu_stats()  

        # Update GPU Utilization Gauge
        self.gpu_gauge.set_value(stats.get("util",0))

        # Update GPU Power Usage Gauge
        self.gpu_power_gauge.set_value(
            min(max((stats.get("power_usage",0) / stats.get("max_power_limit",0)) * 100, 0), 100),
            label=f"Power: {stats.get("power_usage",0)}W / {stats.get('max_power_limit',0)}W"
        )

        # Update GPU Temperature Gauge
        self.gpu_temp_gauge.set_value(
            min(max(stats.get("temperature",0) / GPU_MAX_TEMP * 100, 0), 100),
            label=f"GPU Temp: {stats.get('temperature',0)}°C"
        )

        # Update GPU Clock Speed Gauge
        clock_mhz = stats.get("clock", 0) or 0  # Get GPU clock speed in MHz
        if clock_mhz:
            clock_percent = int(clock_mhz / GPU_BASE_CLK * 100)  # Calculate percentage of base clock
        else:
            clock_percent = 0

        # Clamp the clock percentage to [0, 100]
        clock_percent_clamp = min(max(clock_percent, 0), 100)

        # Update GPU Clock Gauge with label showing MHz and percentage of base clock
        self.gpu_clock_gauge.set_value(
            clock_percent_clamp,
            label=f"{clock_mhz:,} MHz ({clock_percent}% of base clock)"
        )

        # Update GPU Memory Usage Gauge
        self.gpu_mem_gauge.set_value(
            stats.get("vram",0),
            label=f"VRAM: {stats.get('vram_used',0):,} MiB / {stats.get('vram_total',0):,} MiB"
        )

        # ----- RAM ------------------------------------------
        mem = psutil.virtual_memory()  # Get memory usage statistics
        mem_pct = mem.percent  # Calculate memory usage percentage

        # Update Memory Gauge with label showing used and total RAM
        self.mem_gauge.set_value(
            mem_pct,
            label=f"RAM: {mem.used / (1024 ** 3):.2f} GiB / {mem.total / (1024 ** 3):.2f} GiB"
        )

# ------------------------------------------------------------------
#  Main
# ------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec()