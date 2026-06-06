import sys
from typing import List, Tuple
from collections import deque

import nidaqmx
from nidaqmx.system import System
from nidaqmx.constants import LineGrouping, TerminalConfiguration

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import pyqtgraph as pg


class DigitalPlotWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Gráfica digital")
        self.resize(920, 760)

        self.max_points = 300
        self.x_data = deque(maxlen=self.max_points)
        self.y_data = deque(maxlen=self.max_points)
        self.counter = 0

        layout = QVBoxLayout(self)

        self.info_label = QLabel("Canal: ---")
        layout.addWidget(self.info_label)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle("Estado digital")
        self.plot_widget.setLabel("left", "Estado")
        self.plot_widget.setLabel("bottom", "Muestra")
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setYRange(-0.1, 1.1)
        self.plot_widget.getAxis("left").setTicks([[(0, "LOW"), (1, "HIGH")]])

        self.curve = self.plot_widget.plot([], [], stepMode="center")
        layout.addWidget(self.plot_widget)

    def set_channel_name(self, channel_name: str) -> None:
        self.info_label.setText(f"Canal: {channel_name}")

    def clear_plot(self) -> None:
        self.x_data.clear()
        self.y_data.clear()
        self.counter = 0
        self.curve.setData([], [])

    def add_point(self, value: int) -> None:
        self.x_data.append(self.counter)
        self.y_data.append(int(value))
        self.counter += 1
        self.curve.setData(list(self.x_data), list(self.y_data))


class AnalogPlotWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Gráfica analógica")
        self.resize(900, 450)

        self.max_points = 500
        self.x_data = deque(maxlen=self.max_points)
        self.y_data = deque(maxlen=self.max_points)
        self.counter = 0

        layout = QVBoxLayout(self)

        self.info_label = QLabel("Canal: ---")
        layout.addWidget(self.info_label)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle("Voltaje analógico")
        self.plot_widget.setLabel("left", "Voltaje", units="V")
        self.plot_widget.setLabel("bottom", "Muestra")
        self.plot_widget.showGrid(x=True, y=True)

        self.curve = self.plot_widget.plot([], [])
        layout.addWidget(self.plot_widget)

    def set_channel_name(self, channel_name: str) -> None:
        self.info_label.setText(f"Canal: {channel_name}")

    def clear_plot(self) -> None:
        self.x_data.clear()
        self.y_data.clear()
        self.counter = 0
        self.curve.setData([], [])

    def set_y_range(self, min_val: float, max_val: float) -> None:
        self.plot_widget.setYRange(min_val, max_val)

    def add_point(self, value: float) -> None:
        self.x_data.append(self.counter)
        self.y_data.append(float(value))
        self.counter += 1
        self.curve.setData(list(self.x_data), list(self.y_data))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Lector NI-DAQ - Digital y Analógico (Qt6)")
        self.resize(1000, 760)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.read_current_mode)

        self.port_states: List[QLabel] = []
        self.digital_plot_window = DigitalPlotWindow()
        self.analog_plot_window = AnalogPlotWindow()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # =========================
        # Configuración general
        # =========================
        top_box = QGroupBox("Configuración general")
        top_form = QFormLayout(top_box)

        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Digital", "Analógico"])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(50, 5000)
        self.interval_spin.setValue(200)
        self.interval_spin.setSuffix(" ms")

        top_form.addRow("Dispositivo:", self.device_combo)
        top_form.addRow("Modo:", self.mode_combo)
        top_form.addRow("Intervalo de lectura:", self.interval_spin)

        main_layout.addWidget(top_box)

        # =========================
        # Digital
        # =========================
        self.digital_box = QGroupBox("Entradas digitales")
        digital_layout = QFormLayout(self.digital_box)

        self.port_combo = QComboBox()
        self.port_combo.currentIndexChanged.connect(self.on_port_changed)

        self.digital_line_combo = QComboBox()
        self.digital_line_combo.currentIndexChanged.connect(self.on_digital_line_changed)

        digital_layout.addRow("Puerto digital:", self.port_combo)
        digital_layout.addRow("Canal a graficar:", self.digital_line_combo)

        self.digital_state_box = QGroupBox("Estado digital")
        self.digital_state_layout = QGridLayout(self.digital_state_box)

        self.port_value_label = QLabel("Valor entero: ---")
        self.binary_value_label = QLabel("Binario: ---")

        self.digital_state_layout.addWidget(self.port_value_label, 0, 0, 1, 2)
        self.digital_state_layout.addWidget(self.binary_value_label, 1, 0, 1, 2)

        digital_outer = QVBoxLayout()
        digital_outer.addWidget(self.digital_box)
        digital_outer.addWidget(self.digital_state_box)

        self.digital_widget = QWidget()
        self.digital_widget.setLayout(digital_outer)
        main_layout.addWidget(self.digital_widget)

        # =========================
        # Analógico
        # =========================
        self.analog_box = QGroupBox("Entradas analógicas")
        analog_form = QFormLayout(self.analog_box)

        self.ai_channel_combo = QComboBox()
        self.ai_channel_combo.currentIndexChanged.connect(self.on_ai_channel_changed)

        self.terminal_combo = QComboBox()
        self.terminal_combo.addItem("RSE", TerminalConfiguration.RSE)
        self.terminal_combo.addItem("NRSE", TerminalConfiguration.NRSE)
        self.terminal_combo.addItem("DIFF", TerminalConfiguration.DIFF)

        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(-1000.0, 1000.0)
        self.min_spin.setDecimals(3)
        self.min_spin.setValue(0.0)
        self.min_spin.valueChanged.connect(self.on_analog_range_changed)

        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(-1000.0, 1000.0)
        self.max_spin.setDecimals(3)
        self.max_spin.setValue(5.0)
        self.max_spin.valueChanged.connect(self.on_analog_range_changed)

        analog_form.addRow("Canal analógico:", self.ai_channel_combo)
        analog_form.addRow("Configuración terminal:", self.terminal_combo)
        analog_form.addRow("Mínimo esperado [V]:", self.min_spin)
        analog_form.addRow("Máximo esperado [V]:", self.max_spin)

        self.analog_result_box = QGroupBox("Lectura analógica")
        analog_result_layout = QFormLayout(self.analog_result_box)

        self.analog_value_label = QLabel("---")
        self.analog_value_label.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.analog_mode_label = QLabel("---")

        analog_result_layout.addRow("Voltaje:", self.analog_value_label)
        analog_result_layout.addRow("Modo terminal:", self.analog_mode_label)

        analog_outer = QVBoxLayout()
        analog_outer.addWidget(self.analog_box)
        analog_outer.addWidget(self.analog_result_box)

        self.analog_widget = QWidget()
        self.analog_widget.setLayout(analog_outer)
        main_layout.addWidget(self.analog_widget)

        # =========================
        # Botones
        # =========================
         # =========================
        # Botones
        # =========================
        buttons_box = QGroupBox("Acciones")
        buttons_layout = QGridLayout(buttons_box)
        buttons_layout.setContentsMargins(4, 4, 4, 4)
        buttons_layout.setHorizontalSpacing(4)
        buttons_layout.setVerticalSpacing(4)

        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.clicked.connect(self.load_devices)

        self.read_once_button = QPushButton("Leer")
        self.read_once_button.clicked.connect(self.read_current_mode)

        self.start_button = QPushButton("Iniciar")
        self.start_button.clicked.connect(self.start_reading)

        self.stop_button = QPushButton("Detener")
        self.stop_button.clicked.connect(self.stop_reading)
        self.stop_button.setEnabled(False)

        self.digital_plot_button = QPushButton("Gráf. digital")
        self.digital_plot_button.clicked.connect(self.show_digital_plot)

        self.analog_plot_button = QPushButton("Gráf. analógica")
        self.analog_plot_button.clicked.connect(self.show_analog_plot)

        for boton in (
            self.refresh_button,
            self.read_once_button,
            self.start_button,
            self.stop_button,
            self.digital_plot_button,
            self.analog_plot_button,
        ):
            boton.setMinimumHeight(26)
            boton.setMaximumHeight(26)

        self.start_button.setMinimumWidth(70)
        self.stop_button.setMinimumWidth(70)

        buttons_layout.addWidget(self.refresh_button,      0, 0)
        buttons_layout.addWidget(self.read_once_button,    0, 1)
        buttons_layout.addWidget(self.start_button,        0, 2)

        buttons_layout.addWidget(self.stop_button,         1, 0)
        buttons_layout.addWidget(self.digital_plot_button, 1, 1)
        buttons_layout.addWidget(self.analog_plot_button,  1, 2)

        main_layout.addWidget(buttons_box)
        # =========================
        # Log
        # =========================
        log_box = QGroupBox("Log")
        log_layout = QVBoxLayout(log_box)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)

        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_box)

        self.load_devices()
        self.on_mode_changed()

    def log(self, text: str) -> None:
        self.log_text.append(text)

    def load_devices(self) -> None:
        self.device_combo.clear()
        self.port_combo.clear()
        self.ai_channel_combo.clear()
        self.digital_line_combo.clear()
        self.clear_port_state()

        try:
            system = System.local()
            devices = list(system.devices)

            if not devices:
                QMessageBox.warning(self, "Sin dispositivos", "No se encontraron dispositivos NI-DAQ.")
                self.log("No se encontraron dispositivos NI-DAQ.")
                return

            for dev in devices:
                self.device_combo.addItem(dev.name)

            self.log("Dispositivos NI cargados.")
            self.on_device_changed()

        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar dispositivos:\n{exc}")
            self.log(f"Error cargando dispositivos: {exc}")

    def on_device_changed(self) -> None:
        self.port_combo.clear()
        self.ai_channel_combo.clear()
        self.digital_line_combo.clear()
        self.clear_port_state()

        dev_name = self.device_combo.currentText().strip()
        if not dev_name:
            return

        try:
            system = System.local()
            device = system.devices[dev_name]

            for port_name, line_count in self.get_device_ports(device):
                self.port_combo.addItem(f"{port_name} ({line_count} líneas)", (port_name, line_count))

            for ch_name in self.get_ai_channels(device):
                self.ai_channel_combo.addItem(ch_name)

            self.log(f"Configuración cargada para {dev_name}.")
            self.on_port_changed()
            self.on_ai_channel_changed()

        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo consultar el dispositivo:\n{exc}")
            self.log(f"Error consultando {dev_name}: {exc}")

    def on_mode_changed(self) -> None:
        is_digital = self.mode_combo.currentText() == "Digital"
        self.digital_widget.setVisible(is_digital)
        self.analog_widget.setVisible(not is_digital)
        self.digital_plot_button.setEnabled(is_digital)
        self.analog_plot_button.setEnabled(not is_digital)

    def get_device_ports(self, device) -> List[Tuple[str, int]]:
        ports_info: List[Tuple[str, int]] = []

        try:
            for port in device.di_ports:
                port_name = getattr(port, "name", str(port))
                line_count = (
                    getattr(port, "num_lines", None)
                    or getattr(port, "port_width", None)
                    or getattr(port, "number_of_lines", None)
                    or 8
                )
                ports_info.append((port_name, int(line_count)))
        except Exception:
            pass

        if not ports_info:
            try:
                port_map = {}
                for line in device.di_lines:
                    line_name = getattr(line, "name", str(line))
                    parts = line_name.split("/")
                    if len(parts) >= 2:
                        port_name = "/".join(parts[:2])
                        port_map.setdefault(port_name, 0)
                        port_map[port_name] += 1
                ports_info = sorted(port_map.items(), key=lambda x: x[0])
            except Exception:
                pass

        return ports_info

    def get_ai_channels(self, device) -> List[str]:
        channels = []
        try:
            for ch in device.ai_physical_chans:
                channels.append(getattr(ch, "name", str(ch)))
        except Exception:
            pass
        return channels

    def on_port_changed(self) -> None:
        data = self.port_combo.currentData()
        self.digital_line_combo.clear()

        if not data:
            self.clear_port_state()
            return

        port_name, line_count = data
        self.build_port_state(port_name, line_count)

        for i in range(line_count):
            self.digital_line_combo.addItem(f"{port_name}/line{i}", i)

        self.on_digital_line_changed()

    def on_digital_line_changed(self) -> None:
        selected_line = self.digital_line_combo.currentText().strip()
        if selected_line:
            self.digital_plot_window.set_channel_name(selected_line)
            self.digital_plot_window.clear_plot()

    def on_ai_channel_changed(self) -> None:
        selected_channel = self.ai_channel_combo.currentText().strip()
        if selected_channel:
            self.analog_plot_window.set_channel_name(selected_channel)
            self.analog_plot_window.clear_plot()
            self.on_analog_range_changed()

    def on_analog_range_changed(self) -> None:
        min_val = float(self.min_spin.value())
        max_val = float(self.max_spin.value())
        if min_val < max_val:
            self.analog_plot_window.set_y_range(min_val, max_val)

    def clear_port_state(self) -> None:
        for i in reversed(range(self.digital_state_layout.count())):
            item = self.digital_state_layout.itemAt(i)
            widget = item.widget()
            if widget and widget not in (self.port_value_label, self.binary_value_label):
                widget.setParent(None)

        self.port_states.clear()
        self.port_value_label.setText("Valor entero: ---")
        self.binary_value_label.setText("Binario: ---")

        if self.digital_state_layout.indexOf(self.port_value_label) == -1:
            self.digital_state_layout.addWidget(self.port_value_label, 0, 0, 1, 2)
        if self.digital_state_layout.indexOf(self.binary_value_label) == -1:
            self.digital_state_layout.addWidget(self.binary_value_label, 1, 0, 1, 2)

    def build_port_state(self, port_name: str, line_count: int) -> None:
        self.clear_port_state()

        start_row = 2
        for i in range(line_count):
            name_label = QLabel(f"Línea {i}:")
            state_label = QLabel("---")
            state_label.setMinimumWidth(90)
            state_label.setStyleSheet("font-weight: bold;")

            row = start_row + i
            self.digital_state_layout.addWidget(name_label, row, 0)
            self.digital_state_layout.addWidget(state_label, row, 1)

            self.port_states.append(state_label)

    def start_reading(self) -> None:
        self.timer.start(self.interval_spin.value())
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.log("Lectura periódica iniciada.")

    def stop_reading(self) -> None:
        self.timer.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.log("Lectura periódica detenida.")

    def show_digital_plot(self) -> None:
        if self.mode_combo.currentText() != "Digital":
            QMessageBox.information(self, "Información", "La gráfica digital solo está disponible en modo digital.")
            return

        self.digital_plot_window.show()
        self.digital_plot_window.raise_()
        self.digital_plot_window.activateWindow()

    def show_analog_plot(self) -> None:
        if self.mode_combo.currentText() != "Analógico":
            QMessageBox.information(self, "Información", "La gráfica analógica solo está disponible en modo analógico.")
            return

        self.analog_plot_window.show()
        self.analog_plot_window.raise_()
        self.analog_plot_window.activateWindow()

    def read_current_mode(self) -> None:
        if self.mode_combo.currentText() == "Digital":
            self.read_selected_port()
        else:
            self.read_selected_ai()

    def read_selected_port(self) -> None:
        data = self.port_combo.currentData()
        if not data:
            return

        port_name, line_count = data

        try:
            with nidaqmx.Task() as task:
                task.di_channels.add_di_chan(
                    port_name,
                    line_grouping=LineGrouping.CHAN_FOR_ALL_LINES
                )
                value = task.read()

            if isinstance(value, list):
                value = value[0]

            int_value = int(value)
            bits = format(int_value, f"0{line_count}b")

            self.port_value_label.setText(f"Valor entero: {int_value}")
            self.binary_value_label.setText(f"Binario: {bits}")

            for i in range(line_count):
                bit = (int_value >> i) & 0x1
                label = self.port_states[i]
                if bit:
                    label.setText("1 (HIGH)")
                    label.setStyleSheet("font-weight: bold; color: green;")
                else:
                    label.setText("0 (LOW)")
                    label.setStyleSheet("font-weight: bold; color: red;")

            selected_index = self.digital_line_combo.currentData()
            if selected_index is not None:
                selected_bit = (int_value >> int(selected_index)) & 0x1
                self.digital_plot_window.add_point(selected_bit)

        except Exception as exc:
            self.log(f"Error leyendo {port_name}: {exc}")
            if self.timer.isActive():
                self.stop_reading()

    def read_selected_ai(self) -> None:
        ch_name = self.ai_channel_combo.currentText().strip()
        if not ch_name:
            return

        terminal_config = self.terminal_combo.currentData()
        min_val = float(self.min_spin.value())
        max_val = float(self.max_spin.value())

        if min_val >= max_val:
            QMessageBox.warning(self, "Rango inválido", "El valor mínimo debe ser menor que el máximo.")
            return

        try:
            with nidaqmx.Task() as task:
                task.ai_channels.add_ai_voltage_chan(
                    ch_name,
                    terminal_config=terminal_config,
                    min_val=min_val,
                    max_val=max_val
                )
                value = task.read()

            value = float(value)
            self.analog_value_label.setText(f"{value:.6f} V")
            self.analog_mode_label.setText(self.terminal_combo.currentText())
            self.analog_plot_window.add_point(value)

        except Exception as exc:
            self.log(f"Error leyendo {ch_name} en {self.terminal_combo.currentText()}: {exc}")
            self.analog_value_label.setText("ERROR")
            if self.timer.isActive():
                self.stop_reading()


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()