from __future__ import annotations

import sys
import json
import random
import zipfile
from html import escape
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .api_client import ApiClient
from .diagnostics import LOG_PATH, log_event, reset_log
from .runtime import BackendRuntime

try:
    from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal
    from PySide6.QtGui import QAction, QColor, QPainter, QPen
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QDoubleSpinBox,
        QFormLayout,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSplitter,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QHeaderView,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PySide6 is not installed. Run: pip install -r backend/requirements.txt"
    ) from exc


APP_TITLE = "IoT Security Monitoring"
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"
MAX_SESSION_SAMPLES = 500
MAX_SESSION_ALERTS = 200
MAX_ACTION_QUEUE = 200


class BarChartWidget(QWidget):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title
        self.values: dict[str, int] = {}
        self.setMinimumHeight(220)

    def set_values(self, values: dict[str, int]) -> None:
        self.values = values
        self.update()

    def paintEvent(self, event: Any) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(16, 16, -16, -20)
        painter.setPen(QColor("#f2f2f2"))
        painter.drawText(rect.left(), rect.top(), self.title)

        chart = rect.adjusted(0, 30, 0, -20)
        if not self.values:
            painter.setPen(QColor("#9ca3af"))
            painter.drawText(chart, Qt.AlignmentFlag.AlignCenter, "No session data")
            return

        max_value = max(self.values.values()) or 1
        labels = list(self.values)
        gap = 14
        bar_width = max(24, int((chart.width() - gap * (len(labels) - 1)) / len(labels)))
        colors = {
            "critical": QColor("#ef4444"),
            "high": QColor("#f97316"),
            "medium": QColor("#eab308"),
            "low": QColor("#22c55e"),
        }
        for index, label in enumerate(labels):
            value = self.values[label]
            height = int((chart.height() - 34) * value / max_value)
            x = chart.left() + index * (bar_width + gap)
            y = chart.bottom() - 24 - height
            painter.fillRect(x, y, bar_width, height, colors.get(label, QColor("#38bdf8")))
            painter.setPen(QColor("#f2f2f2"))
            painter.drawText(x, chart.bottom() - 6, bar_width, 16, Qt.AlignmentFlag.AlignCenter, label)
            painter.drawText(x, y - 18, bar_width, 16, Qt.AlignmentFlag.AlignCenter, str(value))


class ScoreChartWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.points: list[tuple[float, float]] = []
        self.setMinimumHeight(220)

    def set_points(self, points: list[tuple[float, float]]) -> None:
        self.points = points
        self.update()

    def paintEvent(self, event: Any) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(16, 16, -16, -20)
        painter.setPen(QColor("#f2f2f2"))
        painter.drawText(rect.left(), rect.top(), "ML Reconstruction Error vs Threshold")
        chart = rect.adjusted(0, 34, 0, -16)
        painter.setPen(QPen(QColor("#4b5563"), 1))
        painter.drawRect(chart)

        if not self.points:
            painter.setPen(QColor("#9ca3af"))
            painter.drawText(chart, Qt.AlignmentFlag.AlignCenter, "No ML alerts yet")
            return

        max_value = max(max(error, threshold) for error, threshold in self.points) or 1.0
        threshold = self.points[-1][1]
        threshold_y = chart.bottom() - int(chart.height() * threshold / max_value)
        painter.setPen(QPen(QColor("#22c55e"), 2, Qt.PenStyle.DashLine))
        painter.drawLine(chart.left(), threshold_y, chart.right(), threshold_y)
        painter.drawText(chart.left() + 4, max(chart.top(), threshold_y - 18), f"threshold {threshold:.4f}")

        if len(self.points) == 1:
            x_values = [chart.center().x()]
        else:
            step = chart.width() / (len(self.points) - 1)
            x_values = [int(chart.left() + step * index) for index in range(len(self.points))]

        previous: tuple[int, int] | None = None
        painter.setPen(QPen(QColor("#ef4444"), 2))
        for x, (error, _threshold) in zip(x_values, self.points, strict=False):
            y = chart.bottom() - int(chart.height() * error / max_value)
            painter.setBrush(QColor("#ef4444"))
            painter.drawEllipse(x - 4, y - 4, 8, 8)
            if previous is not None:
                painter.drawLine(previous[0], previous[1], x, y)
            previous = (x, y)


class WorkerSignals(QObject):
    finished = Signal(str, object)
    failed = Signal(str, str)


class ApiWorker(QRunnable):
    def __init__(
        self,
        name: str,
        base_url: str,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.name = name
        self.base_url = base_url
        self.action = action
        self.payload = payload
        self.signals = WorkerSignals()

    def run(self) -> None:
        api = ApiClient(self.base_url)
        try:
            if self.action == "status":
                result = {
                    "status": api.system_status(),
                    "devices": api.registered_devices(),
                }
            elif self.action == "clear":
                result = api.clear_data()
            elif self.action == "send_sample":
                result = api.send_network_sample(self.payload or default_network_sample())
            elif self.action == "demo_scenario":
                result = api.run_demo_scenario()
            elif self.action == "ml_test":
                result = api.run_device_tests()
            else:
                raise ValueError(f"Unknown action: {self.action}")
            self.signals.finished.emit(self.name, result)
        except Exception as exc:
            self.signals.failed.emit(self.name, str(exc))
        finally:
            api.close()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1100, 720)

        self.runtime = BackendRuntime()
        self.base_url = self.runtime.start()
        self.thread_pool = QThreadPool.globalInstance()
        self._busy = False
        self._action_queue: list[tuple[str, str, dict[str, Any] | None]] = []
        self._alerts: list[dict[str, Any]] = []
        self._samples: list[dict[str, Any]] = []
        self._visible_alerts: list[dict[str, Any]] = []
        self._last_ml_status: dict[str, Any] = {}
        self._registered_device_ids: list[str] = ["dev-001"]
        self._live_simulator_enabled = False
        self._live_normal_sent = 0
        self._live_anomaly_sent = 0
        self._live_alerts_generated = 0
        self._live_last_anomaly = "-"
        self._live_next_anomaly_seconds = 0
        self._backend_restart_attempts = 0
        self._defense_demo_running = False

        self._build_ui()
        self._build_menu()
        log_event("app_started", base_url=self.base_url, diagnostics_log=str(LOG_PATH))

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start(5000)
        self.refresh_status()

    def closeEvent(self, event: Any) -> None:
        log_event("app_closing")
        self.refresh_timer.stop()
        if hasattr(self, "live_normal_timer"):
            self.live_normal_timer.stop()
        if hasattr(self, "live_anomaly_timer"):
            self.live_anomaly_timer.stop()
        self.thread_pool.waitForDone(1500)
        self.runtime.stop()
        event.accept()

    def _build_menu(self) -> None:
        open_log = QAction("Open diagnostics log", self)
        open_log.triggered.connect(self.open_diagnostics_log)
        self.menuBar().addAction(open_log)

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)

        header = QHBoxLayout()
        title = QLabel("<h2>IoT Security Monitoring</h2>")
        self.engine_label = QLabel("Engine: starting")
        self.db_label = QLabel("DB: unknown")
        self.ml_label = QLabel("ML: unknown")
        self.base_url_label = QLabel(self.base_url)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.engine_label)
        header.addWidget(self.db_label)
        header.addWidget(self.ml_label)
        header.addWidget(self.base_url_label)
        layout.addLayout(header)

        actions = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_status)
        self.clear_button = QPushButton("Clear Session")
        self.clear_button.clicked.connect(self.clear_session)
        actions.addWidget(self.refresh_button)
        actions.addWidget(self.clear_button)
        actions.addStretch()
        layout.addLayout(actions)

        self.tabs = QTabWidget()
        self.overview_tab_widget = self._overview_tab()
        self.devices_tab_widget = self._devices_tab()
        self.simulator_tab_widget = self._simulator_tab()
        self.alerts_tab_widget = self._alerts_tab()
        self.ml_model_tab_widget = self._ml_model_tab()
        self.reports_tab_widget = self._reports_tab()
        self.diagnostics_tab_widget = self._diagnostics_tab()
        self.tabs.addTab(self.overview_tab_widget, "Overview")
        self.tabs.addTab(self.devices_tab_widget, "Devices")
        self.tabs.addTab(self.simulator_tab_widget, "Simulator")
        self.tabs.addTab(self.alerts_tab_widget, "Alerts")
        self.tabs.addTab(self.ml_model_tab_widget, "ML Model")
        self.tabs.addTab(self.reports_tab_widget, "Reports")
        self.tabs.addTab(self.diagnostics_tab_widget, "Diagnostics")
        layout.addWidget(self.tabs, 1)

        self.setCentralWidget(root)

    def _overview_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        splitter = QSplitter(Qt.Orientation.Vertical)

        metrics_panel = QWidget()
        counts = QGridLayout(metrics_panel)
        self.devices_count = self._metric("Registered Devices")
        self.telemetry_count = self._metric("Telemetry Events")
        self.alerts_count = self._metric("Alerts")
        counts.addWidget(self.devices_count, 0, 0)
        counts.addWidget(self.telemetry_count, 0, 1)
        counts.addWidget(self.alerts_count, 0, 2)
        splitter.addWidget(metrics_panel)

        demo_panel = QWidget()
        demo_layout = QVBoxLayout(demo_panel)
        demo_actions = QHBoxLayout()
        self.defense_demo_button = QPushButton("Prepare Defense Demo")
        self.defense_demo_button.clicked.connect(self.run_defense_demo)
        demo_actions.addWidget(self.defense_demo_button)
        demo_actions.addStretch()
        demo_layout.addLayout(demo_actions)
        self.defense_demo_text = QTextEdit()
        self.defense_demo_text.setReadOnly(True)
        self.defense_demo_text.setMinimumHeight(130)
        self.defense_demo_text.setPlaceholderText("One-click demo result will appear here.")
        demo_layout.addWidget(self.defense_demo_text, 1)
        splitter.addWidget(demo_panel)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setPlaceholderText(
            "Clean shell is ready. New features will be added here step by step."
        )
        self.readiness_text = QTextEdit()
        self.readiness_text.setReadOnly(True)
        self.readiness_text.setMinimumHeight(170)
        self.readiness_text.setPlaceholderText("System readiness will appear after refresh.")
        status_panel = QWidget()
        status_layout = QVBoxLayout(status_panel)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.addWidget(QLabel("System Readiness"))
        status_layout.addWidget(self.readiness_text, 1)
        status_layout.addWidget(QLabel("System Status"))
        status_layout.addWidget(self.status_text, 2)
        splitter.addWidget(status_panel)
        splitter.setSizes([160, 190, 520])
        layout.addWidget(splitter, 1)
        return tab

    def _devices_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.devices_table = QTableWidget()
        splitter.addWidget(self.devices_table)
        splitter.setSizes([620])
        layout.addWidget(splitter, 1)
        return tab

    def _simulator_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form = QFormLayout()
        self.sample_device_id = QComboBox()
        self.sample_device_id.setEditable(True)
        self.sample_device_id.addItem("dev-001")
        self.sample_protocol = QComboBox()
        self.sample_protocol.addItems(["HTTP", "MQTT", "TCP", "UDP"])
        self.sample_bytes = self._double_input(0, 1_000_000, 512.0)
        self.sample_packets = self._double_input(0, 100_000, 0.2)
        self.sample_connections = self._int_input(0, 10_000, 1)
        self.sample_latency = self._double_input(0, 60_000, 12.0)
        self.sample_loss = self._double_input(0, 100, 0.0)
        form.addRow("Device ID", self.sample_device_id)
        form.addRow("Protocol", self.sample_protocol)
        form.addRow("Bytes/sec", self.sample_bytes)
        form.addRow("Packets/sec", self.sample_packets)
        form.addRow("Connections", self.sample_connections)
        form.addRow("Latency ms", self.sample_latency)
        form.addRow("Packet loss %", self.sample_loss)
        layout.addLayout(form)

        presets = QHBoxLayout()
        self.attack_profile = QComboBox()
        self.attack_profile.addItems(
            [
                "Normal",
                "Flood",
                "Bandwidth only",
                "Packets only",
                "Connections only",
                "Latency only",
                "Packet loss only",
                "Random anomaly",
            ]
        )
        apply_profile = QPushButton("Apply Profile")
        apply_profile.clicked.connect(self.apply_selected_attack_profile)
        normal = QPushButton("Normal preset")
        normal.clicked.connect(self.apply_normal_preset)
        attack = QPushButton("Flood attack")
        attack.clicked.connect(self.apply_attack_preset)
        bandwidth = QPushButton("Bandwidth only")
        bandwidth.clicked.connect(self.apply_bandwidth_only_preset)
        packets = QPushButton("Packets only")
        packets.clicked.connect(self.apply_packets_only_preset)
        connections = QPushButton("Connections only")
        connections.clicked.connect(self.apply_connections_only_preset)
        latency = QPushButton("Latency only")
        latency.clicked.connect(self.apply_latency_only_preset)
        loss = QPushButton("Packet loss only")
        loss.clicked.connect(self.apply_packet_loss_only_preset)
        presets.addWidget(QLabel("Traffic profile"))
        presets.addWidget(self.attack_profile)
        presets.addWidget(apply_profile)
        presets.addWidget(normal)
        presets.addWidget(attack)
        presets.addWidget(bandwidth)
        presets.addWidget(packets)
        presets.addWidget(connections)
        presets.addWidget(latency)
        presets.addWidget(loss)
        presets.addStretch()
        layout.addLayout(presets)

        actions = QHBoxLayout()
        self.send_sample_button = QPushButton("Send Network Sample")
        self.send_sample_button.clicked.connect(self.send_network_sample)
        self.demo_scenario_button = QPushButton("Run Demo Scenario")
        self.demo_scenario_button.clicked.connect(self.run_demo_scenario)
        self.auto_send_button = QPushButton("Start Auto Send (5s)")
        self.auto_send_button.clicked.connect(self.toggle_auto_send)
        self.live_sim_button = QPushButton("Live Devices: Off")
        self.live_sim_button.clicked.connect(self.toggle_live_simulator)
        actions.addWidget(self.send_sample_button)
        actions.addWidget(self.demo_scenario_button)
        actions.addWidget(self.auto_send_button)
        actions.addWidget(self.live_sim_button)
        actions.addStretch()
        layout.addLayout(actions)

        self.sample_timer = QTimer(self)
        self.sample_timer.timeout.connect(self.send_network_sample)
        self.live_normal_timer = QTimer(self)
        self.live_normal_timer.timeout.connect(self.send_live_normal_sample)
        self.live_anomaly_timer = QTimer(self)
        self.live_anomaly_timer.setSingleShot(True)
        self.live_anomaly_timer.timeout.connect(self.send_live_anomaly_sample)
        self.sample_text = QTextEdit()
        self.sample_text.setReadOnly(True)
        self.sample_text.setPlaceholderText("Last network sample payload will appear here.")
        layout.addWidget(QLabel("Last sent payload"))
        layout.addWidget(self.sample_text, 1)
        self.live_status_text = QTextEdit()
        self.live_status_text.setReadOnly(True)
        self.live_status_text.setMinimumHeight(110)
        self.live_status_text.setPlaceholderText("Live simulator status.")
        layout.addWidget(QLabel("Live simulator status"))
        layout.addWidget(self.live_status_text, 1)
        self.live_log_text = QTextEdit()
        self.live_log_text.setReadOnly(True)
        self.live_log_text.document().setMaximumBlockCount(300)
        self.live_log_text.setPlaceholderText("Live simulator events will appear here.")
        layout.addWidget(QLabel("Live simulator log"))
        layout.addWidget(self.live_log_text, 1)
        self._render_live_status()
        return tab

    def _alerts_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        filters = QHBoxLayout()
        self.alert_time_filter = QComboBox()
        self.alert_time_filter.addItems(["Last 24 hours", "Last hour", "All"])
        self.alert_severity_filter = QComboBox()
        self.alert_attack_filter = QComboBox()
        self.alert_source_filter = QComboBox()
        self.alert_device_filter = QComboBox()
        self.alert_search = QLineEdit()
        self.alert_search.setPlaceholderText("Search in message...")
        reset = QPushButton("Reset filters")
        reset.clicked.connect(self.reset_alert_filters)
        for combo in [
            self.alert_severity_filter,
            self.alert_attack_filter,
            self.alert_source_filter,
            self.alert_device_filter,
        ]:
            combo.addItem("All")
            combo.currentTextChanged.connect(self._render_alerts)
        self.alert_time_filter.currentTextChanged.connect(self._render_alerts)
        self.alert_search.textChanged.connect(self._render_alerts)
        filters.addWidget(QLabel("Time range"))
        filters.addWidget(self.alert_time_filter)
        filters.addWidget(QLabel("Severity"))
        filters.addWidget(self.alert_severity_filter)
        filters.addWidget(QLabel("Type"))
        filters.addWidget(self.alert_attack_filter)
        filters.addWidget(QLabel("Source"))
        filters.addWidget(self.alert_source_filter)
        filters.addWidget(QLabel("Device"))
        filters.addWidget(self.alert_device_filter)
        filters.addWidget(self.alert_search)
        filters.addWidget(reset)
        layout.addLayout(filters)

        self.alerts_table = QTableWidget()
        self.alerts_table.itemSelectionChanged.connect(self._render_alert_detail)
        layout.addWidget(self.alerts_table, 2)
        self.alert_detail_text = QTextEdit()
        self.alert_detail_text.setReadOnly(True)
        self.alert_detail_text.setMinimumHeight(150)
        self.alert_detail_text.setPlaceholderText("Select an alert to view ML details.")
        layout.addWidget(QLabel("Alert Details"))
        layout.addWidget(self.alert_detail_text, 1)
        self._render_alerts()
        return tab

    def _ml_model_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        splitter = QSplitter(Qt.Orientation.Vertical)

        info_panel = QWidget()
        info_layout = QVBoxLayout(info_panel)
        self.ml_model_text = QTextEdit()
        self.ml_model_text.setReadOnly(True)
        info_layout.addWidget(QLabel("Model Status"))
        info_layout.addWidget(self.ml_model_text, 1)
        splitter.addWidget(info_panel)

        test_panel = QWidget()
        test_layout = QVBoxLayout(test_panel)
        actions = QHBoxLayout()
        self.test_ml_button = QPushButton("Test ML Model")
        self.test_ml_button.clicked.connect(self.test_ml_model)
        actions.addWidget(self.test_ml_button)
        actions.addStretch()
        test_layout.addLayout(actions)
        self.ml_test_text = QTextEdit()
        self.ml_test_text.setReadOnly(True)
        self.ml_test_text.setPlaceholderText("Run Test ML Model to verify normal and attack inference.")
        test_layout.addWidget(self.ml_test_text, 1)
        splitter.addWidget(test_panel)
        splitter.setSizes([360, 260])
        layout.addWidget(splitter, 1)
        self._render_ml_model_status({})
        return tab

    def _reports_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        splitter = QSplitter(Qt.Orientation.Vertical)

        top = QWidget()
        top_layout = QVBoxLayout(top)
        metrics = QGridLayout()
        self.report_samples_count = self._metric("Samples Sent")
        self.report_alerts_count = self._metric("ML Alerts")
        self.report_critical_count = self._metric("Critical Alerts")
        self.report_max_score = self._metric("Max ML Score")
        metrics.addWidget(self.report_samples_count, 0, 0)
        metrics.addWidget(self.report_alerts_count, 0, 1)
        metrics.addWidget(self.report_critical_count, 0, 2)
        metrics.addWidget(self.report_max_score, 0, 3)
        top_layout.addLayout(metrics)

        charts = QSplitter(Qt.Orientation.Horizontal)
        self.report_severity_chart = BarChartWidget("Alerts by Severity")
        self.report_score_chart = ScoreChartWidget()
        charts.addWidget(self.report_severity_chart)
        charts.addWidget(self.report_score_chart)
        charts.setSizes([420, 620])
        top_layout.addWidget(charts, 1)
        splitter.addWidget(top)

        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        actions = QHBoxLayout()
        self.export_report_button = QPushButton("Export Session Report")
        self.export_report_button.clicked.connect(self.export_session_report)
        self.save_report_button = QPushButton("Save Report Only")
        self.save_report_button.clicked.connect(self.save_session_report)
        self.evidence_pack_button = QPushButton("Export Evidence Pack")
        self.evidence_pack_button.clicked.connect(self.export_evidence_pack)
        actions.addWidget(QLabel("Session Samples"))
        actions.addStretch()
        actions.addWidget(self.save_report_button)
        actions.addWidget(self.export_report_button)
        actions.addWidget(self.evidence_pack_button)
        bottom_layout.addLayout(actions)
        self.report_samples_table = QTableWidget()
        bottom_layout.addWidget(self.report_samples_table, 1)
        splitter.addWidget(bottom)

        risk_panel = QWidget()
        risk_layout = QVBoxLayout(risk_panel)
        risk_layout.addWidget(QLabel("Device Risk Summary"))
        self.device_risk_table = QTableWidget()
        risk_layout.addWidget(self.device_risk_table, 1)
        splitter.addWidget(risk_panel)

        timeline_panel = QWidget()
        timeline_layout = QVBoxLayout(timeline_panel)
        timeline_layout.addWidget(QLabel("Alert Timeline"))
        self.alert_timeline_table = QTableWidget()
        timeline_layout.addWidget(self.alert_timeline_table, 1)
        splitter.addWidget(timeline_panel)

        archive_panel = QWidget()
        archive_layout = QVBoxLayout(archive_panel)
        archive_actions = QHBoxLayout()
        refresh_archive = QPushButton("Refresh Report Archive")
        refresh_archive.clicked.connect(self.refresh_report_archive)
        archive_actions.addWidget(QLabel("Report Archive"))
        archive_actions.addStretch()
        archive_actions.addWidget(refresh_archive)
        archive_layout.addLayout(archive_actions)
        self.report_archive_table = QTableWidget()
        archive_layout.addWidget(self.report_archive_table, 1)
        splitter.addWidget(archive_panel)

        splitter.setSizes([300, 220, 190, 190, 190])
        layout.addWidget(splitter, 1)
        self._render_reports()
        self.refresh_report_archive()
        return tab

    def _diagnostics_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        actions = QHBoxLayout()
        refresh = QPushButton("Refresh Diagnostics")
        refresh.clicked.connect(self.refresh_diagnostics_view)
        open_log = QPushButton("Open Log File")
        open_log.clicked.connect(self.open_diagnostics_log)
        actions.addWidget(QLabel(str(LOG_PATH)))
        actions.addStretch()
        actions.addWidget(refresh)
        actions.addWidget(open_log)
        layout.addLayout(actions)
        self.diagnostics_text = QTextEdit()
        self.diagnostics_text.setReadOnly(True)
        self.diagnostics_text.setPlaceholderText("Diagnostics log tail will appear here.")
        layout.addWidget(self.diagnostics_text, 1)
        self.refresh_diagnostics_view()
        return tab

    def _double_input(self, minimum: float, maximum: float, value: float) -> QDoubleSpinBox:
        field = QDoubleSpinBox()
        field.setRange(minimum, maximum)
        field.setDecimals(3)
        field.setValue(value)
        return field

    def _int_input(self, minimum: int, maximum: int, value: int) -> QDoubleSpinBox:
        field = QDoubleSpinBox()
        field.setRange(minimum, maximum)
        field.setDecimals(0)
        field.setValue(value)
        return field

    def _metric(self, title: str) -> QLabel:
        label = QLabel(f"<b>{title}</b><br>0")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumHeight(80)
        return label

    def refresh_status(self) -> None:
        log_event("button_clicked", button="Refresh")
        self._run_worker("Refresh", "status")

    def clear_session(self) -> None:
        log_event("button_clicked", button="Clear Session")
        self._clear_session_state()
        self.engine_label.setText("Engine: online (session cleared)")

    def _clear_session_state(self) -> None:
        self._alerts.clear()
        self._samples.clear()
        self._live_normal_sent = 0
        self._live_anomaly_sent = 0
        self._live_alerts_generated = 0
        self._live_last_anomaly = "-"
        self._render_alerts()
        self._render_reports()
        self._render_live_status()
        self.sample_text.clear()
        if hasattr(self, "live_log_text"):
            self.live_log_text.clear()
        self.refresh_diagnostics_view()

    def send_network_sample(self) -> None:
        payload = self.current_network_sample()
        self.sample_text.setPlainText(format_payload(payload))
        log_event("button_clicked", button="Send Network Sample", payload=payload)
        self._run_worker("Send Network Sample", "send_sample", payload=payload)

    def run_demo_scenario(self) -> None:
        log_event("button_clicked", button="Run Demo Scenario")
        self._run_worker("Run Demo Scenario", "demo_scenario")

    def run_defense_demo(self) -> None:
        log_event("button_clicked", button="Prepare Defense Demo")
        self._defense_demo_running = True
        self._clear_session_state()
        self.defense_demo_text.setPlainText(
            "Preparing defense demo...\n"
            "Session cleared.\n"
            "Running multi-device scenario."
        )
        self._run_worker("Prepare Defense Demo", "demo_scenario")

    def test_ml_model(self) -> None:
        log_event("button_clicked", button="Test ML Model")
        self._run_worker("Test ML Model", "ml_test")

    def apply_selected_attack_profile(self) -> None:
        profile = self.attack_profile.currentText()
        handlers = {
            "Normal": self.apply_normal_preset,
            "Flood": self.apply_attack_preset,
            "Bandwidth only": self.apply_bandwidth_only_preset,
            "Packets only": self.apply_packets_only_preset,
            "Connections only": self.apply_connections_only_preset,
            "Latency only": self.apply_latency_only_preset,
            "Packet loss only": self.apply_packet_loss_only_preset,
        }
        if profile == "Random anomaly":
            payload, label = self._random_single_metric_anomaly()
            self._apply_payload_to_fields(payload)
            self.sample_text.setPlainText(format_payload(self.current_network_sample()))
            log_event("simulator_preset_applied", preset=f"random_{label}")
            return
        handlers.get(profile, self.apply_normal_preset)()

    def apply_normal_preset(self) -> None:
        self.sample_protocol.setCurrentText("HTTP")
        self.sample_bytes.setValue(512.0)
        self.sample_packets.setValue(0.2)
        self.sample_connections.setValue(1)
        self.sample_latency.setValue(12.0)
        self.sample_loss.setValue(0.0)
        self.sample_text.setPlainText(format_payload(self.current_network_sample()))
        log_event("simulator_preset_applied", preset="normal")

    def apply_attack_preset(self) -> None:
        self.sample_protocol.setCurrentText("HTTP")
        self.sample_bytes.setValue(25000.0)
        self.sample_packets.setValue(120.0)
        self.sample_connections.setValue(80)
        self.sample_latency.setValue(450.0)
        self.sample_loss.setValue(18.0)
        self.sample_text.setPlainText(format_payload(self.current_network_sample()))
        log_event("simulator_preset_applied", preset="attack_like")

    def apply_bandwidth_only_preset(self) -> None:
        self.apply_normal_preset()
        self.sample_bytes.setValue(25000.0)
        self.sample_text.setPlainText(format_payload(self.current_network_sample()))
        log_event("simulator_preset_applied", preset="bandwidth_only")

    def apply_packets_only_preset(self) -> None:
        self.apply_normal_preset()
        self.sample_packets.setValue(120.0)
        self.sample_text.setPlainText(format_payload(self.current_network_sample()))
        log_event("simulator_preset_applied", preset="packets_only")

    def apply_connections_only_preset(self) -> None:
        self.apply_normal_preset()
        self.sample_connections.setValue(80)
        self.sample_text.setPlainText(format_payload(self.current_network_sample()))
        log_event("simulator_preset_applied", preset="connections_only")

    def apply_latency_only_preset(self) -> None:
        self.apply_normal_preset()
        self.sample_latency.setValue(900.0)
        self.sample_text.setPlainText(format_payload(self.current_network_sample()))
        log_event("simulator_preset_applied", preset="latency_only")

    def apply_packet_loss_only_preset(self) -> None:
        self.apply_normal_preset()
        self.sample_loss.setValue(22.0)
        self.sample_text.setPlainText(format_payload(self.current_network_sample()))
        log_event("simulator_preset_applied", preset="packet_loss_only")

    def _apply_payload_to_fields(self, payload: dict[str, Any]) -> None:
        self.sample_device_id.setCurrentText(str(payload.get("device_id") or "dev-001"))
        self.sample_protocol.setCurrentText(str(payload.get("protocol") or "HTTP"))
        self.sample_bytes.setValue(float(payload.get("bytes_per_second") or 0.0))
        self.sample_packets.setValue(float(payload.get("packets_per_second") or 0.0))
        self.sample_connections.setValue(int(payload.get("connection_count") or 0))
        self.sample_latency.setValue(float(payload.get("latency_ms") or 0.0))
        self.sample_loss.setValue(float(payload.get("packet_loss_percent") or 0.0))

    def current_network_sample(self) -> dict[str, Any]:
        return {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "device_id": self.sample_device_id.currentText().strip() or "dev-001",
            "protocol": self.sample_protocol.currentText(),
            "bytes_per_second": float(self.sample_bytes.value()),
            "packets_per_second": float(self.sample_packets.value()),
            "connection_count": int(self.sample_connections.value()),
            "latency_ms": float(self.sample_latency.value()),
            "packet_loss_percent": float(self.sample_loss.value()),
        }

    def toggle_auto_send(self) -> None:
        if self.sample_timer.isActive():
            self.sample_timer.stop()
            self.auto_send_button.setText("Start Auto Send (5s)")
            log_event("auto_send_stopped")
            return
        self.sample_timer.start(5000)
        self.auto_send_button.setText("Stop Auto Send")
        log_event("auto_send_started", interval_ms=5000)
        self.send_network_sample()

    def toggle_live_simulator(self) -> None:
        if self._live_simulator_enabled:
            self._live_simulator_enabled = False
            self.live_normal_timer.stop()
            self.live_anomaly_timer.stop()
            self.live_sim_button.setText("Live Devices: Off")
            self._append_live_log("Live simulator stopped.")
            log_event("live_simulator_stopped")
            return
        self._live_simulator_enabled = True
        self.live_sim_button.setText("Live Devices: On")
        self.live_normal_timer.start(3000)
        self._append_live_log("Live simulator started. Normal samples every 3s; random anomaly every 10-20s.")
        log_event("live_simulator_started")
        self.send_live_normal_sample()
        self._schedule_next_live_anomaly()

    def send_live_normal_sample(self) -> None:
        if not self._live_simulator_enabled:
            return
        payload = self._normal_payload_for_device(self._random_device_id())
        self._live_normal_sent += 1
        self._append_live_log(f"normal -> {payload['device_id']}")
        self._render_live_status()
        self._run_worker("Live Device Sample", "send_sample", payload=payload)

    def send_live_anomaly_sample(self) -> None:
        if not self._live_simulator_enabled:
            return
        payload, label = self._random_single_metric_anomaly()
        self._live_anomaly_sent += 1
        self._live_last_anomaly = label
        self._append_live_log(f"anomaly:{label} -> {payload['device_id']}")
        self._render_live_status()
        self._run_worker("Live Device Sample", "send_sample", payload=payload)
        self._schedule_next_live_anomaly()

    def _schedule_next_live_anomaly(self) -> None:
        if not self._live_simulator_enabled:
            return
        delay_ms = random.randint(10_000, 20_000)
        self._live_next_anomaly_seconds = delay_ms // 1000
        self.live_anomaly_timer.start(delay_ms)
        self._render_live_status()
        self._append_live_log(f"next anomaly in {delay_ms // 1000}s")

    def _random_device_id(self) -> str:
        return random.choice(self._registered_device_ids or ["dev-001"])

    def _normal_payload_for_device(self, device_id: str) -> dict[str, Any]:
        payload = default_network_sample()
        payload["device_id"] = device_id
        payload["protocol"] = random.choice(["HTTP", "MQTT", "TCP", "UDP"])
        payload["bytes_per_second"] = round(random.uniform(420.0, 780.0), 2)
        payload["packets_per_second"] = round(random.uniform(0.1, 0.8), 3)
        payload["connection_count"] = random.randint(1, 3)
        payload["latency_ms"] = round(random.uniform(8.0, 35.0), 2)
        payload["packet_loss_percent"] = round(random.uniform(0.0, 0.6), 3)
        return payload

    def _random_single_metric_anomaly(self) -> tuple[dict[str, Any], str]:
        payload = self._normal_payload_for_device(self._random_device_id())
        metric = random.choice(
            [
                "bytes_per_second",
                "packets_per_second",
                "connection_count",
                "latency_ms",
                "packet_loss_percent",
            ]
        )
        intensity = random.choice(["slightly_high", "strongly_high", "strongly_low"])
        if metric == "packet_loss_percent" and intensity == "strongly_low":
            intensity = "strongly_high"
        if metric == "bytes_per_second":
            payload[metric] = random.choice([6000.0, 25000.0, 90000.0]) if intensity != "strongly_low" else 0.0
        elif metric == "packets_per_second":
            payload[metric] = random.choice([12.0, 120.0, 800.0]) if intensity != "strongly_low" else 0.0
        elif metric == "connection_count":
            payload[metric] = random.choice([21, 80, 500]) if intensity != "strongly_low" else 0
        elif metric == "latency_ms":
            payload[metric] = random.choice([220.0, 900.0, 5000.0]) if intensity != "strongly_low" else 0.0
        elif metric == "packet_loss_percent":
            payload[metric] = random.choice([6.0, 22.0, 70.0]) if intensity != "strongly_low" else 0.0
        return payload, f"{metric}:{intensity}"

    def _append_live_log(self, message: str) -> None:
        if not hasattr(self, "live_log_text"):
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.live_log_text.append(f"[{timestamp}] {message}")

    def _render_live_status(self) -> None:
        if not hasattr(self, "live_status_text"):
            return
        queue_size = len(getattr(self, "_action_queue", []))
        status = "running" if self._live_simulator_enabled else "stopped"
        lines = [
            f"Status: {status}",
            f"Normal samples sent: {self._live_normal_sent}",
            f"Anomaly samples sent: {self._live_anomaly_sent}",
            f"Alerts generated: {self._live_alerts_generated}",
            f"Last anomaly: {self._live_last_anomaly}",
            f"Next anomaly in: {self._live_next_anomaly_seconds}s" if self._live_simulator_enabled else "Next anomaly in: -",
            f"Queued actions: {queue_size}",
            f"History limits: {MAX_SESSION_SAMPLES} samples / {MAX_SESSION_ALERTS} alerts",
        ]
        self.live_status_text.setPlainText("\n".join(lines))

    def _render_simple_table(
        self,
        table: QTableWidget,
        headers: list[str],
        rows: list[list[Any]],
        stretch_column: int | None = None,
    ) -> None:
        table.setColumnCount(len(headers))
        table.setRowCount(len(rows))
        table.setHorizontalHeaderLabels(headers)
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                cell = QTableWidgetItem(str(value or ""))
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row_index, column_index, cell)
        header = table.horizontalHeader()
        for column in range(len(headers)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        if stretch_column is not None and 0 <= stretch_column < len(headers):
            header.setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)

    def _device_risk_rows(self) -> list[list[Any]]:
        device_ids = sorted(
            set(self._registered_device_ids)
            | {str(sample.get("device_id")) for sample in self._samples if sample.get("device_id")}
            | {str(alert.get("device_id")) for alert in self._alerts if alert.get("device_id")}
        )
        rows: list[list[Any]] = []
        for device_id in device_ids:
            sample_count = sum(1 for sample in self._samples if sample.get("device_id") == device_id)
            alerts = [alert for alert in self._alerts if alert.get("device_id") == device_id]
            max_score = max(
                [float(alert.get("reconstruction_error") or 0.0) for alert in alerts]
                or [0.0]
            )
            risk = "Normal"
            if any(str(alert.get("severity")) == "critical" for alert in alerts):
                risk = "Critical"
            elif alerts:
                risk = "Suspicious"
            rows.append([device_id, sample_count, len(alerts), self._format_number(max_score), risk])
        return rows

    def _run_worker(
        self,
        name: str,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if self._busy:
            if name == "Refresh" and any(item[0] == "Refresh" for item in self._action_queue):
                log_event("action_rejected", action=name, reason="refresh_already_queued")
                return
            if len(self._action_queue) >= MAX_ACTION_QUEUE:
                dropped = self._action_queue.pop(0)
                log_event("action_queue_dropped", dropped_action=dropped[0])
            self._action_queue.append((name, action, payload))
            self._render_live_status()
            log_event("action_queued", action=name, queue_size=len(self._action_queue))
            return
        self._busy = True
        self._set_action_buttons_enabled(False)
        self.engine_label.setText(f"Engine: busy ({name})")
        log_event("action_started", action=name)
        worker = ApiWorker(name, self.base_url, action, payload=payload)
        worker.signals.finished.connect(self._handle_worker_result)
        worker.signals.failed.connect(self._handle_worker_error)
        self.thread_pool.start(worker)

    def _start_next_queued_action(self) -> None:
        if self._busy or not self._action_queue:
            self._render_live_status()
            return
        name, action, payload = self._action_queue.pop(0)
        self._render_live_status()
        self._run_worker(name, action, payload=payload)

    def _handle_worker_result(self, name: str, result: Any) -> None:
        self._busy = False
        self._set_action_buttons_enabled(True)
        log_event("action_finished", action=name, result_type=type(result).__name__)
        if name in {"Send Network Sample", "Live Device Sample"}:
            self._record_sample_response(result)
            if name == "Live Device Sample":
                alerts = result.get("alerts", [])
                received = result.get("received_sample", {})
                if alerts:
                    self._live_alerts_generated += len(alerts)
                self._append_live_log(
                    f"accepted <- {received.get('device_id')} alerts={len(alerts)}"
                )
                self._render_live_status()
            self.engine_label.setText("Engine: online (sample sent)")
            self._start_next_queued_action()
            return
        if name in {"Run Demo Scenario", "Prepare Defense Demo"}:
            for item in result.get("results", []):
                self._record_sample_response(item)
            if name == "Prepare Defense Demo":
                html_path, json_path, severity_png, score_png = self._write_session_report()
                self._defense_demo_running = False
                summary = [
                    "Defense demo ready.",
                    "",
                    f"Samples sent: {result.get('samples_sent', 0)}",
                    f"ML alerts: {result.get('alerts_created', 0)}",
                    f"Devices: {len(self._registered_device_ids)}",
                    "",
                    f"HTML report: {html_path}",
                    f"JSON evidence: {json_path}",
                    f"Severity chart: {severity_png}",
                    f"ML score chart: {score_png}",
                ]
                self.defense_demo_text.setPlainText("\n".join(summary))
                self.tabs.setCurrentWidget(self.overview_tab_widget)
                self.engine_label.setText("Engine: defense demo ready")
            else:
                self.tabs.setCurrentWidget(self.reports_tab_widget)
                self.engine_label.setText(
                    "Engine: demo completed "
                    f"({result.get('samples_sent', 0)} samples, "
                    f"{result.get('alerts_created', 0)} alerts)"
                )
            self._start_next_queued_action()
            return
        if name == "Test ML Model":
            passed = 0
            lines = [
                "ML device test completed.",
                "",
                f"Devices tested: {result.get('devices_tested', 0)}",
                f"Tests run: {result.get('tests_run', 0)}",
                f"Alerts created: {result.get('alerts_created', 0)}",
                "",
            ]
            for item in result.get("results", []):
                normal = item.get("normal", {})
                attack = item.get("attack", {})
                self._record_sample_response(normal)
                self._record_sample_response(attack)
                normal_alerts = len(normal.get("alerts", []))
                attack_alerts = len(attack.get("alerts", []))
                ok = normal_alerts == 0 and attack_alerts >= 1
                if ok:
                    passed += 1
                lines.append(
                    f"{item.get('device_id')} / {item.get('device_name')}: "
                    f"normal={normal_alerts}, attack={attack_alerts} -> "
                    f"{'PASS' if ok else 'CHECK'}"
                )
            self.ml_test_text.setPlainText(
                "\n".join(lines)
                + "\n\n"
                + f"Overall: {passed}/{result.get('devices_tested', 0)} device profiles passed."
            )
            self.tabs.setCurrentWidget(self.ml_model_tab_widget)
            self.engine_label.setText("Engine: online (ML test completed)")
            self._start_next_queued_action()
            return
        self._render_status(result["status"], result["devices"])
        self._backend_restart_attempts = 0
        self._start_next_queued_action()

    def _handle_worker_error(self, name: str, message: str) -> None:
        self._busy = False
        self._set_action_buttons_enabled(True)
        self.engine_label.setText(f"Engine: error ({name})")
        self.status_text.setPlainText(message)
        log_event("action_failed", action=name, error=message)
        if name == "Refresh":
            self._restart_backend_after_failure(message)
        self._start_next_queued_action()

    def _record_sample_response(self, result: dict[str, Any]) -> None:
        received = result.get("received_sample") or {}
        alerts = result.get("alerts", [])
        self._samples.insert(
            0,
            {
                **received,
                "alert_count": len(alerts),
                "max_reconstruction_error": max(
                    [float(alert.get("reconstruction_error") or 0.0) for alert in alerts]
                    or [0.0]
                ),
                "max_threshold": max(
                    [float(alert.get("threshold") or 0.0) for alert in alerts]
                    or [0.0]
                ),
            },
        )
        del self._samples[MAX_SESSION_SAMPLES:]
        for alert in alerts:
            self._alerts.insert(0, alert)
        del self._alerts[MAX_SESSION_ALERTS:]
        self._sync_alert_filters()
        self._render_alerts()
        self._render_reports()
        self.refresh_diagnostics_view()

    def _set_action_buttons_enabled(self, enabled: bool) -> None:
        for button in [
            getattr(self, "refresh_button", None),
            getattr(self, "clear_button", None),
            getattr(self, "defense_demo_button", None),
            getattr(self, "send_sample_button", None),
            getattr(self, "demo_scenario_button", None),
            getattr(self, "test_ml_button", None),
            getattr(self, "export_report_button", None),
            getattr(self, "save_report_button", None),
            getattr(self, "evidence_pack_button", None),
        ]:
            if button is not None:
                button.setEnabled(enabled)

    def _restart_backend_after_failure(self, reason: str) -> None:
        if self._backend_restart_attempts >= 2:
            self.engine_label.setText("Engine: offline")
            log_event("backend_restart_skipped", reason="max_attempts", error=reason)
            return
        self._backend_restart_attempts += 1
        try:
            log_event("backend_restart_started", attempt=self._backend_restart_attempts)
            self.runtime.stop()
            self.base_url = self.runtime.start()
            self.base_url_label.setText(self.base_url)
            self.engine_label.setText("Engine: restarted")
            log_event("backend_restart_finished", base_url=self.base_url)
        except Exception as exc:
            self.engine_label.setText("Engine: offline")
            log_event("backend_restart_failed", error=str(exc))

    def _render_status(
        self,
        status: dict[str, Any],
        devices: list[dict[str, Any]],
    ) -> None:
        counts = status.get("counts", {})
        ml_status = status.get("ml_status", {})
        self._last_ml_status = ml_status
        self.engine_label.setText("Engine: online")
        self.db_label.setText("DB: ready" if status.get("database_ready") else "DB: off")
        self.ml_label.setText(
            "ML: ready" if ml_status.get("ready_for_inference") else "ML: unavailable"
        )
        self.devices_count.setText(
            f"<b>Registered Devices</b><br>{counts.get('registered_devices', 0)}"
        )
        self.telemetry_count.setText(
            f"<b>Telemetry Events</b><br>{counts.get('telemetry_events', 0)}"
        )
        self.alerts_count.setText(f"<b>Alerts</b><br>{counts.get('alerts', 0)}")
        self._render_devices(devices)
        lines = [
            f"Backend: {status.get('backend_status')}",
            f"Database: {status.get('database_url')}",
            "",
            "ML model:",
            f"  path: {ml_status.get('model_path')}",
            f"  format: {ml_status.get('model_format')}",
            f"  exists: {ml_status.get('model_exists')}",
            f"  ready: {ml_status.get('ready_for_inference')}",
            f"  detail: {ml_status.get('detail')}",
            "",
            f"Diagnostics log: {LOG_PATH}",
        ]
        self.status_text.setPlainText("\n".join(lines))
        self._render_readiness(status, devices)
        self._render_ml_model_status(ml_status)

    def _render_readiness(
        self,
        status: dict[str, Any],
        devices: list[dict[str, Any]],
    ) -> None:
        if not hasattr(self, "readiness_text"):
            return
        counts = status.get("counts", {})
        ml_status = status.get("ml_status", {})
        checks = [
            ("Backend online", status.get("backend_status") == "ok"),
            ("Database ready", bool(status.get("database_ready"))),
            ("ML model ready", bool(ml_status.get("ready_for_inference"))),
            ("Five devices registered", len(devices) >= 5 and counts.get("registered_devices", 0) >= 5),
            ("No dynamic DB alerts", counts.get("alerts", 0) == 0),
            ("No dynamic DB telemetry", counts.get("telemetry_events", 0) == 0),
            ("Reports directory available", REPORTS_DIR.exists()),
            ("Diagnostics log path configured", bool(LOG_PATH)),
        ]
        passed = sum(1 for _label, ok in checks if ok)
        lines = [f"Readiness: {passed}/{len(checks)} checks passed", ""]
        for label, ok in checks:
            lines.append(f"{'PASS' if ok else 'CHECK'}  {label}")
        self.readiness_text.setPlainText("\n".join(lines))

    def _render_devices(self, devices: list[dict[str, Any]]) -> None:
        headers = [
            "Device ID",
            "Name",
            "Type",
            "Mode",
            "IP",
            "MAC",
        ]
        rows = [
            [
                item.get("device_id"),
                item.get("device_name"),
                item.get("device_type"),
                item.get("device_mode"),
                item.get("ip_address") or "-",
                item.get("mac_address") or "-",
            ]
            for item in devices
        ]
        if hasattr(self, "sample_device_id"):
            current_device = self.sample_device_id.currentText()
            device_ids = [str(item.get("device_id")) for item in devices if item.get("device_id")]
            self._registered_device_ids = device_ids or ["dev-001"]
            self.sample_device_id.blockSignals(True)
            self.sample_device_id.clear()
            self.sample_device_id.addItems(device_ids or ["dev-001"])
            if current_device in device_ids:
                self.sample_device_id.setCurrentText(current_device)
            self.sample_device_id.blockSignals(False)
        self.devices_table.setColumnCount(len(headers))
        self.devices_table.setRowCount(len(rows))
        self.devices_table.setHorizontalHeaderLabels(headers)
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                cell = QTableWidgetItem(str(value))
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.devices_table.setItem(row_index, column_index, cell)
        if self.devices_table.property("columnsSized") != True:
            self.devices_table.resizeColumnsToContents()
            self.devices_table.setProperty("columnsSized", True)

    def _sync_alert_filters(self) -> None:
        self._sync_combo(self.alert_severity_filter, [a.get("severity") for a in self._alerts])
        self._sync_combo(self.alert_attack_filter, [a.get("attack_type") for a in self._alerts])
        self._sync_combo(self.alert_source_filter, [a.get("source") for a in self._alerts])
        self._sync_combo(self.alert_device_filter, [a.get("device_id") for a in self._alerts])

    def _sync_combo(self, combo: QComboBox, values: list[Any]) -> None:
        current = combo.currentText()
        items = ["All", *sorted({str(value) for value in values if value})]
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(items)
        if current in items:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def reset_alert_filters(self) -> None:
        self.alert_time_filter.setCurrentText("Last 24 hours")
        self.alert_severity_filter.setCurrentText("All")
        self.alert_attack_filter.setCurrentText("All")
        self.alert_source_filter.setCurrentText("All")
        self.alert_device_filter.setCurrentText("All")
        self.alert_search.clear()
        self._render_alerts()

    def _filtered_alerts(self) -> list[dict[str, Any]]:
        selected_time = self.alert_time_filter.currentText()
        severity = self.alert_severity_filter.currentText()
        attack_type = self.alert_attack_filter.currentText()
        source = self.alert_source_filter.currentText()
        device = self.alert_device_filter.currentText()
        search = self.alert_search.text().strip().lower()
        now = datetime.now().astimezone()
        result: list[dict[str, Any]] = []
        for alert in self._alerts:
            if severity != "All" and alert.get("severity") != severity:
                continue
            if attack_type != "All" and alert.get("attack_type") != attack_type:
                continue
            if source != "All" and alert.get("source") != source:
                continue
            if device != "All" and alert.get("device_id") != device:
                continue
            searchable = " ".join(
                [
                    str(alert.get("message", "")),
                    str(alert.get("explanation", "")),
                    str(alert.get("device_id", "")),
                    str(alert.get("device_name", "")),
                ]
            ).lower()
            if search and search not in searchable:
                continue
            timestamp = self._parse_alert_time(alert.get("timestamp"))
            if selected_time == "Last hour" and timestamp and timestamp < now - timedelta(hours=1):
                continue
            if selected_time == "Last 24 hours" and timestamp and timestamp < now - timedelta(hours=24):
                continue
            result.append(alert)
        return result

    def _parse_alert_time(self, value: Any) -> datetime | None:
        if not value:
            return None
        try:
            raw = str(value).replace("Z", "+00:00")
            parsed = datetime.fromisoformat(raw)
            if parsed.tzinfo is None:
                parsed = parsed.astimezone()
            return parsed.astimezone()
        except ValueError:
            return None

    def _render_alerts(self) -> None:
        self._visible_alerts = self._filtered_alerts()
        headers = [
            "Timestamp",
            "Device ID",
            "Device Name",
            "Severity",
            "Type of Attack",
            "Source",
            "ML Score",
            "Threshold",
            "Risk",
            "Message",
        ]
        rows = [
            [
                item.get("timestamp"),
                item.get("device_id"),
                item.get("device_name"),
                item.get("severity"),
                item.get("attack_type"),
                item.get("source"),
                self._format_number(item.get("reconstruction_error")),
                self._format_number(item.get("threshold")),
                item.get("risk_level"),
                item.get("message"),
            ]
            for item in self._visible_alerts
        ]
        self.alerts_table.blockSignals(True)
        self.alerts_table.setColumnCount(len(headers))
        self.alerts_table.setRowCount(len(rows))
        self.alerts_table.setHorizontalHeaderLabels(headers)
        self.alerts_table.setWordWrap(True)
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                cell = QTableWidgetItem(str(value or ""))
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if headers[column_index] == "Message":
                    cell.setToolTip(str(row[-1] or ""))
                self.alerts_table.setItem(row_index, column_index, cell)
        self.alerts_table.blockSignals(False)
        header = self.alerts_table.horizontalHeader()
        for column in range(len(headers)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(headers.index("Message"), QHeaderView.ResizeMode.Stretch)
        self.alerts_table.resizeRowsToContents()
        self._render_alert_detail()

    def _render_alert_detail(self) -> None:
        if not hasattr(self, "alert_detail_text"):
            return
        row = self.alerts_table.currentRow() if hasattr(self, "alerts_table") else -1
        if row < 0 or row >= len(self._visible_alerts):
            self.alert_detail_text.setPlainText("Select an alert to view ML details.")
            return
        alert = self._visible_alerts[row]
        lines = [
            f"Device: {alert.get('device_name')} ({alert.get('device_id')})",
            f"Severity: {alert.get('severity')}",
            f"Source: {alert.get('source')}",
            f"Type: {alert.get('attack_type')}",
            "",
            "ML decision:",
            f"  reconstruction error: {self._format_number(alert.get('reconstruction_error'))}",
            f"  threshold: {self._format_number(alert.get('threshold'))}",
            f"  risk level: {alert.get('risk_level')}",
            "",
            "Explanation:",
            str(alert.get("explanation") or alert.get("message") or ""),
        ]
        self.alert_detail_text.setPlainText("\n".join(lines))

    def _render_ml_model_status(self, ml_status: dict[str, Any]) -> None:
        if not hasattr(self, "ml_model_text"):
            return
        ready = "ready" if ml_status.get("ready_for_inference") else "not ready"
        lines = [
            "Model type: PyTorch autoencoder",
            "Dataset/features: CICIoT2023 / 46 network features",
            f"Runtime status: {ready}",
            f"Model path: {ml_status.get('model_path', '-')}",
            f"Model format: {ml_status.get('model_format', '-')}",
            f"Feature count: {ml_status.get('feature_count', '-')}",
            f"Threshold: {self._format_number(ml_status.get('threshold'))}",
            f"Loaded: {ml_status.get('model_loaded', False)}",
            "",
            "How the decision works:",
            "The simulator sends a compact local-network sample. The backend converts it",
            "into CICIoT2023-style features and passes them into the autoencoder.",
            "If reconstruction error is higher than the threshold, the traffic is treated",
            "as anomalous and an ML alert is created.",
            "",
            f"Detail: {ml_status.get('detail', '-')}",
        ]
        self.ml_model_text.setPlainText("\n".join(lines))

    def _render_reports(self) -> None:
        alert_count = len(self._alerts)
        critical_count = sum(1 for alert in self._alerts if alert.get("severity") == "critical")
        scores = [
            float(alert.get("reconstruction_error") or 0.0)
            for alert in self._alerts
            if alert.get("reconstruction_error") is not None
        ]
        max_score = max(scores) if scores else 0.0
        self.report_samples_count.setText(f"<b>Samples Sent</b><br>{len(self._samples)}")
        self.report_alerts_count.setText(f"<b>ML Alerts</b><br>{alert_count}")
        self.report_critical_count.setText(f"<b>Critical Alerts</b><br>{critical_count}")
        self.report_max_score.setText(f"<b>Max ML Score</b><br>{max_score:.4f}")

        severity_values = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        for alert in self._alerts:
            severity = str(alert.get("severity") or "").lower()
            if severity in severity_values:
                severity_values[severity] += 1
        self.report_severity_chart.set_values(severity_values)

        score_points = [
            (
                float(alert.get("reconstruction_error") or 0.0),
                float(alert.get("threshold") or 0.0),
            )
            for alert in reversed(self._alerts)
            if alert.get("reconstruction_error") is not None
        ]
        self.report_score_chart.set_points(score_points)
        self._render_samples_table()
        if hasattr(self, "device_risk_table"):
            self._render_simple_table(
                self.device_risk_table,
                ["Device ID", "Samples", "Alerts", "Max ML Score", "Risk"],
                self._device_risk_rows(),
                stretch_column=0,
            )
        if hasattr(self, "alert_timeline_table"):
            rows = [
                [
                    alert.get("timestamp"),
                    alert.get("device_id"),
                    alert.get("severity"),
                    alert.get("message"),
                ]
                for alert in self._alerts[:50]
            ]
            self._render_simple_table(
                self.alert_timeline_table,
                ["Timestamp", "Device", "Severity", "Event"],
                rows,
                stretch_column=3,
            )

    def _render_samples_table(self) -> None:
        headers = [
            "Timestamp",
            "Device ID",
            "Protocol",
            "Bytes/sec",
            "Packets/sec",
            "Connections",
            "Latency ms",
            "Loss %",
            "Alerts",
            "ML Score",
        ]
        rows = [
            [
                sample.get("timestamp"),
                sample.get("device_id"),
                sample.get("protocol"),
                self._format_number(sample.get("bytes_per_second")),
                self._format_number(sample.get("packets_per_second")),
                sample.get("connection_count"),
                self._format_number(sample.get("latency_ms")),
                self._format_number(sample.get("packet_loss_percent")),
                sample.get("alert_count"),
                self._format_number(sample.get("max_reconstruction_error")),
            ]
            for sample in self._samples
        ]
        self.report_samples_table.setColumnCount(len(headers))
        self.report_samples_table.setRowCount(len(rows))
        self.report_samples_table.setHorizontalHeaderLabels(headers)
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                cell = QTableWidgetItem(str(value or ""))
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.report_samples_table.setItem(row_index, column_index, cell)
        header = self.report_samples_table.horizontalHeader()
        for column in range(len(headers)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def refresh_report_archive(self) -> None:
        if not hasattr(self, "report_archive_table"):
            return
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(
            [
                path
                for path in REPORTS_DIR.glob("*")
                if path.is_file() and path.suffix.lower() in {".html", ".json", ".png", ".zip"}
            ],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )[:40]
        rows = [
            [
                path.name,
                path.suffix.lower().lstrip("."),
                self._format_number(path.stat().st_size / 1024),
                datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            ]
            for path in files
        ]
        self._render_simple_table(
            self.report_archive_table,
            ["File", "Type", "KB", "Modified"],
            rows,
            stretch_column=0,
        )

    def save_session_report(self) -> None:
        html_path, _json_path, _severity_png_path, _score_png_path = self._write_session_report()
        self.engine_label.setText(f"Report saved: {html_path.name}")

    def export_session_report(self) -> None:
        html_path, _json_path, _severity_png_path, _score_png_path = self._write_session_report()
        self.engine_label.setText(f"Report exported: {html_path.name}")
        self._open_local_file(html_path)

    def export_evidence_pack(self) -> None:
        pack_path = self._write_evidence_pack()
        self.engine_label.setText(f"Evidence pack exported: {pack_path.name}")

    def _write_evidence_pack(self) -> Path:
        html_path, json_path, severity_png_path, score_png_path = self._write_session_report()
        pack_path = REPORTS_DIR / (
            "iot_security_evidence_pack_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".zip"
        )
        readme = self._build_evidence_readme(
            html_path,
            json_path,
            severity_png_path,
            score_png_path,
        )
        with zipfile.ZipFile(pack_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in [html_path, json_path, severity_png_path, score_png_path]:
                if path.is_file():
                    archive.write(path, arcname=f"reports/{path.name}")
            for path in [
                LOG_PATH,
                Path(__file__).resolve().parents[1] / "logs" / "network_samples.log",
            ]:
                if path.is_file():
                    archive.write(path, arcname=f"logs/{path.name}")
            for path in [
                Path(__file__).resolve().parents[1] / "README.md",
                Path(__file__).resolve().parents[1] / "docs" / "demo-script.md",
                Path(__file__).resolve().parents[1] / "docs" / "architecture.md",
                Path(__file__).resolve().parents[1] / "docs" / "ml-integration.md",
            ]:
                if path.is_file():
                    archive.write(path, arcname=f"docs/{path.name}")
            archive.writestr("EVIDENCE_PACK_README.txt", readme)
        log_event("evidence_pack_exported", path=str(pack_path))
        return pack_path

    def _build_evidence_readme(
        self,
        html_path: Path,
        json_path: Path,
        severity_png_path: Path,
        score_png_path: Path,
    ) -> str:
        return "\n".join(
            [
                "IoT Security Monitoring Evidence Pack",
                "",
                f"Generated at: {datetime.now().astimezone().isoformat(timespec='seconds')}",
                f"Backend URL: {self.base_url}",
                "",
                "Session summary:",
                f"- Samples: {len(self._samples)}",
                f"- ML alerts: {len(self._alerts)}",
                f"- Devices: {len(self._registered_device_ids)}",
                f"- Max ML score: {max([float(a.get('reconstruction_error') or 0.0) for a in self._alerts] or [0.0]):.6f}",
                "",
                "Included report artifacts:",
                f"- reports/{html_path.name}",
                f"- reports/{json_path.name}",
                f"- reports/{severity_png_path.name}",
                f"- reports/{score_png_path.name}",
                "",
                "Included logs:",
                "- logs/desktop_diagnostics.log",
                "- logs/network_samples.log",
                "",
                "Included docs:",
                "- docs/README.md",
                "- docs/demo-script.md",
                "- docs/architecture.md",
                "- docs/ml-integration.md",
            ]
        )

    def _write_session_report(self) -> tuple[Path, Path, Path, Path]:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        stem = (
            "iot_security_session_report_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
        )
        json_path = REPORTS_DIR / f"{stem}.json"
        html_path = REPORTS_DIR / f"{stem}.html"
        severity_png_path = REPORTS_DIR / f"{stem}_alerts_by_severity.png"
        score_png_path = REPORTS_DIR / f"{stem}_ml_score_vs_threshold.png"
        QApplication.processEvents()
        self.report_severity_chart.grab().save(str(severity_png_path))
        self.report_score_chart.grab().save(str(score_png_path))
        payload = {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "base_url": self.base_url,
            "artifacts": {
                "html_report": str(html_path),
                "json_report": str(json_path),
                "severity_chart_png": str(severity_png_path),
                "score_chart_png": str(score_png_path),
            },
            "summary": {
                "samples_sent": len(self._samples),
                "ml_alerts": len(self._alerts),
                "critical_alerts": sum(
                    1 for alert in self._alerts if alert.get("severity") == "critical"
                ),
                "max_reconstruction_error": max(
                    [
                        float(alert.get("reconstruction_error") or 0.0)
                        for alert in self._alerts
                    ]
                    or [0.0]
                ),
            },
            "samples": self._samples,
            "alerts": self._alerts,
            "device_risk_summary": self._device_risk_rows(),
        }
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        html_path.write_text(self._build_report_html(payload), encoding="utf-8")
        log_event(
            "session_report_exported",
            json_path=str(json_path),
            html_path=str(html_path),
            severity_png=str(severity_png_path),
            score_png=str(score_png_path),
        )
        self.refresh_report_archive()
        return html_path, json_path, severity_png_path, score_png_path

    def _build_report_html(self, payload: dict[str, Any]) -> str:
        summary = payload["summary"]
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for alert in self._alerts:
            severity = str(alert.get("severity") or "").lower()
            if severity in severity_counts:
                severity_counts[severity] += 1

        score_points = [
            (
                float(alert.get("reconstruction_error") or 0.0),
                float(alert.get("threshold") or 0.0),
            )
            for alert in reversed(self._alerts)
            if alert.get("reconstruction_error") is not None
        ]
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>IoT Security Monitoring Session Report</title>
  <style>
    body {{ margin: 0; background: #f4f6f8; color: #172033; font-family: Arial, sans-serif; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    h2 {{ margin: 28px 0 12px; font-size: 18px; }}
    .muted {{ color: #667085; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 22px 0; }}
    .card {{ background: white; border: 1px solid #d9dee7; border-radius: 8px; padding: 16px; }}
    .metric {{ font-size: 28px; font-weight: 700; margin-top: 8px; }}
    .split {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #d9dee7; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 9px 10px; text-align: left; vertical-align: top; font-size: 13px; }}
    th {{ background: #eef2f7; color: #344054; }}
    .badge {{ display: inline-block; padding: 3px 8px; border-radius: 6px; color: white; font-weight: 700; }}
    .critical {{ background: #dc2626; }} .high {{ background: #ea580c; }} .medium {{ background: #ca8a04; }} .low {{ background: #16a34a; }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; margin: 0; font-family: Consolas, monospace; }}
    @media print {{ body {{ background: white; }} main {{ padding: 18px; }} .card, table {{ break-inside: avoid; }} }}
  </style>
</head>
<body>
<main>
  <h1>IoT Security Monitoring Session Report</h1>
  <div class="muted">Generated: {escape(str(payload["generated_at"]))} | Backend: {escape(str(payload["base_url"]))}</div>

  <section class="grid">
    {self._html_metric("Samples Sent", summary["samples_sent"])}
    {self._html_metric("ML Alerts", summary["ml_alerts"])}
    {self._html_metric("Critical Alerts", summary["critical_alerts"])}
    {self._html_metric("Max ML Score", f'{summary["max_reconstruction_error"]:.6f}')}
  </section>

  <section class="card">
    <h2>Executive Summary</h2>
    <p>
      This session demonstrates local-network IoT traffic monitoring with an ML anomaly detection layer.
      The simulator sends simplified network telemetry, the backend adapts it into CICIoT2023 feature space,
      and the PyTorch autoencoder classifies traffic as normal or anomalous by reconstruction error.
    </p>
  </section>

  <section class="split">
    <div class="card">
      <h2>System Architecture</h2>
      <p>
        The desktop application controls a local FastAPI engine. Static registered device metadata is kept in
        SQLite, while dynamic network samples and ML alerts are treated as session evidence and exported into
        report artifacts.
      </p>
    </div>
    <div class="card">
      <h2>Detection Pipeline</h2>
      <p>
        Registered device -> network sample -> CICIoT feature adapter -> PyTorch autoencoder ->
        reconstruction error check -> ML alert -> analytics dashboard -> exported report.
      </p>
    </div>
  </section>

  <section class="card">
    <h2>ML Methodology</h2>
    <p>
      The autoencoder is trained to reconstruct normal CICIoT2023 traffic features. During inference,
      abnormal behavior produces a higher reconstruction error. If the error is greater than the configured
      threshold, the system creates an alert with severity derived from the model risk level.
    </p>
  </section>

  <section class="split">
    <div class="card">
      <h2>Alerts by Severity</h2>
      {self._severity_svg(severity_counts)}
    </div>
    <div class="card">
      <h2>ML Score vs Threshold</h2>
      {self._score_svg(score_points)}
    </div>
  </section>

  <h2>ML Alerts</h2>
  {self._alerts_html_table()}

  <h2>Network Samples</h2>
  {self._samples_html_table()}

  <h2>Device Risk Summary</h2>
  {self._device_risk_html_table()}

  <h2>Alert Timeline</h2>
  {self._alert_timeline_html_table()}

  <section class="card">
    <h2>Method Notes</h2>
    <p>
      Dynamic traffic samples and alerts are intentionally kept out of the database during the prototype phase.
      Static registered device data remains in DB; session evidence is exported into this report and raw JSON.
    </p>
  </section>

  <section class="card">
    <h2>Conclusion</h2>
    <p>
      The prototype demonstrates a complete intelligent monitoring workflow for IoT device security:
      controlled traffic generation, ML-based anomaly detection, explainable alert presentation,
      and reproducible evidence export for review.
    </p>
  </section>
</main>
</body>
</html>
"""

    def _html_metric(self, title: str, value: Any) -> str:
        return (
            '<div class="card">'
            f'<div class="muted">{escape(str(title))}</div>'
            f'<div class="metric">{escape(str(value))}</div>'
            '</div>'
        )

    def _severity_svg(self, counts: dict[str, int]) -> str:
        width, height = 480, 240
        labels = list(counts)
        max_value = max(counts.values()) or 1
        colors = {
            "critical": "#dc2626",
            "high": "#ea580c",
            "medium": "#ca8a04",
            "low": "#16a34a",
        }
        bars: list[str] = []
        bar_width = 72
        gap = 32
        start_x = 34
        for index, label in enumerate(labels):
            value = counts[label]
            bar_height = int(150 * value / max_value)
            x = start_x + index * (bar_width + gap)
            y = 178 - bar_height
            bars.append(
                f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{colors[label]}"/>'
                f'<text x="{x + bar_width / 2}" y="{y - 8}" text-anchor="middle" font-size="13">{value}</text>'
                f'<text x="{x + bar_width / 2}" y="214" text-anchor="middle" font-size="13">{label}</text>'
            )
        return f'<svg viewBox="0 0 {width} {height}" width="100%" height="240" role="img">{"".join(bars)}</svg>'

    def _score_svg(self, points: list[tuple[float, float]]) -> str:
        width, height = 520, 240
        if not points:
            return '<div class="muted">No ML alerts in this session.</div>'
        max_value = max(max(error, threshold) for error, threshold in points) or 1.0
        left, top, chart_w, chart_h = 42, 22, 438, 168
        threshold = points[-1][1]
        threshold_y = top + chart_h - int(chart_h * threshold / max_value)
        if len(points) == 1:
            coords = [(left + chart_w // 2, top + chart_h - int(chart_h * points[0][0] / max_value))]
        else:
            coords = [
                (
                    int(left + chart_w * index / (len(points) - 1)),
                    top + chart_h - int(chart_h * error / max_value),
                )
                for index, (error, _threshold) in enumerate(points)
            ]
        polyline = " ".join(f"{x},{y}" for x, y in coords)
        circles = "".join(f'<circle cx="{x}" cy="{y}" r="4" fill="#dc2626"/>' for x, y in coords)
        return (
            f'<svg viewBox="0 0 {width} {height}" width="100%" height="240" role="img">'
            f'<rect x="{left}" y="{top}" width="{chart_w}" height="{chart_h}" fill="none" stroke="#d0d5dd"/>'
            f'<line x1="{left}" y1="{threshold_y}" x2="{left + chart_w}" y2="{threshold_y}" stroke="#16a34a" stroke-width="2" stroke-dasharray="6 4"/>'
            f'<text x="{left + 6}" y="{max(14, threshold_y - 8)}" font-size="12" fill="#166534">threshold {threshold:.6f}</text>'
            f'<polyline points="{polyline}" fill="none" stroke="#dc2626" stroke-width="2"/>'
            f'{circles}'
            f'<text x="{left}" y="220" font-size="12" fill="#667085">chronological session alerts</text>'
            f'</svg>'
        )

    def _alerts_html_table(self) -> str:
        if not self._alerts:
            return '<div class="card muted">No ML alerts in this session.</div>'
        rows = []
        for alert in self._alerts:
            severity = escape(str(alert.get("severity") or ""))
            rows.append(
                "<tr>"
                f"<td>{escape(str(alert.get('timestamp') or ''))}</td>"
                f"<td>{escape(str(alert.get('device_id') or ''))}</td>"
                f"<td>{escape(str(alert.get('device_name') or ''))}</td>"
                f'<td><span class="badge {severity}">{severity}</span></td>'
                f"<td>{escape(str(alert.get('source') or ''))}</td>"
                f"<td>{self._format_number(alert.get('reconstruction_error'))}</td>"
                f"<td>{self._format_number(alert.get('threshold'))}</td>"
                f"<td>{escape(str(alert.get('message') or ''))}</td>"
                f"<td><pre>{escape(str(alert.get('explanation') or ''))}</pre></td>"
                "</tr>"
            )
        return (
            "<table><thead><tr><th>Timestamp</th><th>Device ID</th><th>Device Name</th>"
            "<th>Severity</th><th>Source</th><th>ML Score</th><th>Threshold</th><th>Message</th><th>Explanation</th>"
            "</tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

    def _samples_html_table(self) -> str:
        if not self._samples:
            return '<div class="card muted">No samples sent in this session.</div>'
        rows = []
        for sample in self._samples:
            rows.append(
                "<tr>"
                f"<td>{escape(str(sample.get('timestamp') or ''))}</td>"
                f"<td>{escape(str(sample.get('device_id') or ''))}</td>"
                f"<td>{escape(str(sample.get('protocol') or ''))}</td>"
                f"<td>{self._format_number(sample.get('bytes_per_second'))}</td>"
                f"<td>{self._format_number(sample.get('packets_per_second'))}</td>"
                f"<td>{escape(str(sample.get('connection_count') or ''))}</td>"
                f"<td>{self._format_number(sample.get('latency_ms'))}</td>"
                f"<td>{self._format_number(sample.get('packet_loss_percent'))}</td>"
                f"<td>{escape(str(sample.get('alert_count') or 0))}</td>"
                "</tr>"
            )
        return (
            "<table><thead><tr><th>Timestamp</th><th>Device ID</th><th>Protocol</th>"
            "<th>Bytes/sec</th><th>Packets/sec</th><th>Connections</th><th>Latency ms</th>"
            "<th>Loss %</th><th>Alerts</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

    def _device_risk_html_table(self) -> str:
        rows = []
        for device_id, sample_count, alert_count, max_score, risk in self._device_risk_rows():
            rows.append(
                "<tr>"
                f"<td>{escape(str(device_id))}</td>"
                f"<td>{escape(str(sample_count))}</td>"
                f"<td>{escape(str(alert_count))}</td>"
                f"<td>{escape(str(max_score))}</td>"
                f"<td>{escape(str(risk))}</td>"
                "</tr>"
            )
        return (
            "<table><thead><tr><th>Device ID</th><th>Samples</th><th>Alerts</th>"
            "<th>Max ML Score</th><th>Risk</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

    def _alert_timeline_html_table(self) -> str:
        if not self._alerts:
            return '<div class="card muted">No alert timeline in this session.</div>'
        rows = []
        for alert in self._alerts[:50]:
            rows.append(
                "<tr>"
                f"<td>{escape(str(alert.get('timestamp') or ''))}</td>"
                f"<td>{escape(str(alert.get('device_id') or ''))}</td>"
                f"<td>{escape(str(alert.get('severity') or ''))}</td>"
                f"<td>{escape(str(alert.get('message') or ''))}</td>"
                "</tr>"
            )
        return (
            "<table><thead><tr><th>Timestamp</th><th>Device</th><th>Severity</th>"
            "<th>Event</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table>"
        )

    def _open_local_file(self, path: Path) -> None:
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices

            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception as exc:
            log_event("open_file_failed", path=str(path), error=str(exc))

    def refresh_diagnostics_view(self) -> None:
        if not hasattr(self, "diagnostics_text"):
            return
        if not LOG_PATH.is_file():
            self.diagnostics_text.setPlainText("Diagnostics log is not created yet.")
            return
        lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        self.diagnostics_text.setPlainText("\n".join(lines[-300:]))

    @staticmethod
    def _format_number(value: Any) -> str:
        if value is None:
            return ""
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        if abs(number) >= 100:
            return f"{number:.1f}"
        return f"{number:.4f}"

    def open_diagnostics_log(self) -> None:
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices

            QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_PATH)))
        except Exception as exc:
            log_event("open_log_failed", error=str(exc))


def default_network_sample() -> dict[str, Any]:
    return {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "device_id": "dev-001",
        "protocol": "HTTP",
        "bytes_per_second": 512.0,
        "packets_per_second": 0.2,
        "connection_count": 1,
        "latency_ms": 12.0,
        "packet_loss_percent": 0.0,
    }


def attack_network_sample() -> dict[str, Any]:
    return {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "device_id": "dev-001",
        "protocol": "HTTP",
        "bytes_per_second": 25000.0,
        "packets_per_second": 120.0,
        "connection_count": 80,
        "latency_ms": 450.0,
        "packet_loss_percent": 18.0,
    }


def format_payload(payload: dict[str, Any]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in payload.items())


def main() -> int:
    reset_log()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
