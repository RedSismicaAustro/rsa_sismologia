#!/usr/bin/env python3
# version_control_system_advanced.py

import sys
import os
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
                             QLabel, QFileDialog, QMessageBox, QTabWidget,
                             QTextEdit, QProgressDialog, QSplitter, QGroupBox,
                             QComboBox, QDateEdit, QDateTimeEdit, QCalendarWidget,
                             QDialog, QDialogButtonBox, QFormLayout)
from PyQt5.QtCore import Qt, QDateTime, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QColor, QBrush

class FileInfo:
    """Clase para almacenar información de un archivo o directorio"""
    def __init__(self, path, name, created, modified, size=0, hash_value=None):
        self.path = path
        self.name = name
        self.created = created
        self.modified = modified
        self.size = size
        self.hash_value = hash_value
        self.is_directory = False
        
    def to_dict(self):
        return {
            'path': self.path,
            'name': self.name,
            'created': self.created,
            'modified': self.modified,
            'size': self.size,
            'hash': self.hash_value,
            'is_directory': self.is_directory
        }
    
    @staticmethod
    def from_dict(data):
        info = FileInfo(data['path'], data['name'], data['created'], 
                       data['modified'], data['size'], data['hash'])
        info.is_directory = data['is_directory']
        return info

class DirectoryScanner(QThread):
    """Thread para escanear directorios sin bloquear la UI"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    file_scanned = pyqtSignal(str)
    
    def __init__(self, directory):
        super().__init__()
        self.directory = directory
        
    def get_file_hash(self, filepath):
        """Calcula el hash MD5 de un archivo para detectar cambios de contenido"""
        try:
            hash_md5 = hashlib.md5()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            return None
    
    def get_file_info(self, filepath):
        """Obtiene información detallada de un archivo o directorio"""
        try:
            stat = os.stat(filepath)
            name = os.path.basename(filepath)
            
            # Obtener fechas
            created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            size = stat.st_size if os.path.isfile(filepath) else 0
            
            info = FileInfo(filepath, name, created, modified, size)
            info.is_directory = os.path.isdir(filepath)
            
            # Calcular hash solo para archivos
            if not info.is_directory:
                info.hash_value = self.get_file_hash(filepath)
                
            return info
        except Exception as e:
            print(f"Error al obtener info de {filepath}: {e}")
            return None
    
    def scan_directory(self, path, progress_counter):
        """Escanea recursivamente un directorio"""
        structure = {}
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                info = self.get_file_info(item_path)
                
                if info:
                    structure[item] = info.to_dict()
                    
                    if info.is_directory:
                        structure[item]['children'] = self.scan_directory(item_path, progress_counter + 1)
                    
                    self.file_scanned.emit(item)
                    self.progress.emit(progress_counter, item)
                    
        except Exception as e:
            print(f"Error al escanear {path}: {e}")
        
        return structure
    
    def run(self):
        """Ejecuta el escaneo en un hilo separado"""
        self.progress.emit(0, "Iniciando escaneo...")
        result = self.scan_directory(self.directory, 0)
        self.finished.emit(result)

class VersionCompareDialog(QDialog):
    """Diálogo para seleccionar versiones a comparar"""
    def __init__(self, snapshots, parent=None):
        super().__init__(parent)
        self.snapshots = snapshots
        self.selected_version1 = None
        self.selected_version2 = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Comparar Versiones")
        self.setModal(True)
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Combo para tipo de comparación
        self.compare_type = QComboBox()
        self.compare_type.addItems([
            "Versión anterior inmediata",
            "Primera versión del día anterior",
            "Primera versión de la semana anterior",
            "Primera versión del mes anterior",
            "Versión específica",
            "Rango de fechas"
        ])
        self.compare_type.currentTextChanged.connect(self.on_compare_type_changed)
        form_layout.addRow("Tipo de comparación:", self.compare_type)
        
        # Widgets para versión específica
        self.version_combo = QComboBox()
        self.version_combo.addItems(sorted(self.snapshots.keys(), reverse=True))
        form_layout.addRow("Seleccionar versión:", self.version_combo)
        self.version_combo.setVisible(False)
        
        # Widgets para rango de fechas
        self.start_date = QDateTimeEdit()
        self.start_date.setDateTime(QDateTime.currentDateTime())
        self.start_date.setCalendarPopup(True)
        self.end_date = QDateTimeEdit()
        self.end_date.setDateTime(QDateTime.currentDateTime())
        self.end_date.setCalendarPopup(True)
        
        date_range_layout = QHBoxLayout()
        date_range_layout.addWidget(self.start_date)
        date_range_layout.addWidget(QLabel("hasta"))
        date_range_layout.addWidget(self.end_date)
        
        form_layout.addRow("Rango de fechas:", date_range_layout)
        self.start_date.setVisible(False)
        self.end_date.setVisible(False)
        
        layout.addLayout(form_layout)
        
        # Botones
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.on_compare_type_changed(self.compare_type.currentText())
        
    def on_compare_type_changed(self, text):
        """Muestra/oculta widgets según el tipo de comparación"""
        self.version_combo.setVisible(text == "Versión específica")
        self.start_date.setVisible(text == "Rango de fechas")
        self.end_date.setVisible(text == "Rango de fechas")
    
    def get_versions_to_compare(self, current_version):
        """Obtiene las versiones a comparar según la selección"""
        sorted_versions = sorted(self.snapshots.keys(), reverse=True)
        
        if self.compare_type.currentText() == "Versión anterior inmediata":
            # Encontrar la versión anterior inmediata
            if current_version in sorted_versions:
                idx = sorted_versions.index(current_version)
                if idx + 1 < len(sorted_versions):
                    return current_version, sorted_versions[idx + 1]
            return current_version, None
            
        elif self.compare_type.currentText() == "Primera versión del día anterior":
            current_date = datetime.strptime(current_version[:8], "%Y%m%d").date()
            previous_date = current_date - timedelta(days=1)
            previous_date_str = previous_date.strftime("%Y%m%d")
            
            # Buscar la primera versión del día anterior
            for version in sorted_versions:
                if version.startswith(previous_date_str):
                    return current_version, version
            return current_version, None
            
        elif self.compare_type.currentText() == "Primera versión de la semana anterior":
            current_date = datetime.strptime(current_version[:8], "%Y%m%d").date()
            previous_week = current_date - timedelta(weeks=1)
            previous_week_str = previous_week.strftime("%Y%m%d")
            
            # Buscar la primera versión de la semana anterior
            for version in sorted_versions:
                if version.startswith(previous_week_str):
                    return current_version, version
            return current_version, None
            
        elif self.compare_type.currentText() == "Primera versión del mes anterior":
            current_date = datetime.strptime(current_version[:8], "%Y%m%d").date()
            if current_date.month == 1:
                previous_month = current_date.replace(year=current_date.year-1, month=12, day=1)
            else:
                previous_month = current_date.replace(month=current_date.month-1, day=1)
            previous_month_str = previous_month.strftime("%Y%m")
            
            # Buscar la primera versión del mes anterior
            for version in sorted_versions:
                if version.startswith(previous_month_str):
                    return current_version, version
            return current_version, None
            
        elif self.compare_type.currentText() == "Versión específica":
            return current_version, self.version_combo.currentText()
            
        elif self.compare_type.currentText() == "Rango de fechas":
            start = self.start_date.dateTime().toString("yyyyMMdd_HHmmss")
            end = self.end_date.dateTime().toString("yyyyMMdd_HHmmss")
            return start, end
            
        return current_version, None

class VersionControlSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_directory = None
        self.current_snapshot = None
        self.current_version_name = None
        self.snapshots = {}  # Diccionario para almacenar versiones
        self.snapshots_file = "version_history.json"
        self.load_snapshots()
        self.init_ui()
        
    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        self.setWindowTitle("Sistema Avanzado de Control de Versiones")
        self.setGeometry(100, 100, 1400, 900)
        
        # Estilo
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QTreeWidget {
                alternate-background-color: #f9f9f9;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
        """)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Panel de control superior
        control_panel = QHBoxLayout()
        
        self.select_btn = QPushButton("📁 Seleccionar Directorio")
        self.select_btn.clicked.connect(self.select_directory)
        
        self.save_version_btn = QPushButton("💾 Guardar Versión Actual")
        self.save_version_btn.clicked.connect(self.save_version)
        self.save_version_btn.setEnabled(False)
        
        self.compare_btn = QPushButton("🔍 Comparar con...")
        self.compare_btn.clicked.connect(self.compare_with_dialog)
        self.compare_btn.setEnabled(False)
        
        self.refresh_btn = QPushButton("🔄 Actualizar")
        self.refresh_btn.clicked.connect(self.refresh_current)
        self.refresh_btn.setEnabled(False)
        
        self.export_btn = QPushButton("📄 Exportar Reporte")
        self.export_btn.clicked.connect(self.export_report)
        self.export_btn.setEnabled(False)
        
        control_panel.addWidget(self.select_btn)
        control_panel.addWidget(self.save_version_btn)
        control_panel.addWidget(self.compare_btn)
        control_panel.addWidget(self.refresh_btn)
        control_panel.addWidget(self.export_btn)
        control_panel.addStretch()
        
        main_layout.addLayout(control_panel)
        
        # Panel de información actual
        info_frame = QWidget()
        info_frame.setStyleSheet("background-color: #e3f2fd; border-radius: 5px; padding: 5px;")
        info_layout = QHBoxLayout(info_frame)
        
        self.current_info_label = QLabel("📂 No hay directorio seleccionado")
        self.current_info_label.setFont(QFont("Arial", 10))
        info_layout.addWidget(self.current_info_label)
        
        self.version_info_label = QLabel("")
        self.version_info_label.setFont(QFont("Arial", 9))
        self.version_info_label.setStyleSheet("color: #666;")
        info_layout.addWidget(self.version_info_label)
        info_layout.addStretch()
        
        main_layout.addWidget(info_frame)
        
        # Splitter principal
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel izquierdo - Tree de estructura actual
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_label = QLabel("📂 Estructura Actual del Directorio")
        left_label.setFont(QFont("Arial", 11, QFont.Bold))
        left_layout.addWidget(left_label)
        
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Nombre", "Fecha Creación", "Fecha Modificación", "Tamaño", "Hash MD5"])
        self.tree_widget.setAlternatingRowColors(True)
        self.tree_widget.setIndentation(20)
        self.tree_widget.setColumnWidth(0, 300)
        left_layout.addWidget(self.tree_widget)
        
        # Panel derecho - Tabs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.tab_widget = QTabWidget()
        
        # Tab de versiones guardadas
        versions_tab = QWidget()
        versions_layout = QVBoxLayout(versions_tab)
        
        # Filtros de versiones
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtrar:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Todas", "Este mes", "Este año", "Última semana"])
        self.filter_combo.currentTextChanged.connect(self.filter_versions)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()
        versions_layout.addLayout(filter_layout)
        
        self.versions_tree = QTreeWidget()
        self.versions_tree.setHeaderLabels(["Versión", "Fecha y Hora", "Cambios", "Estado"])
        self.versions_tree.setAlternatingRowColors(True)
        self.versions_tree.setColumnWidth(0, 200)
        versions_layout.addWidget(self.versions_tree)
        
        btn_layout = QHBoxLayout()
        load_version_btn = QPushButton("Cargar Versión Seleccionada")
        load_version_btn.clicked.connect(self.load_selected_version)
        delete_version_btn = QPushButton("Eliminar Versión")
        delete_version_btn.clicked.connect(self.delete_selected_version)
        delete_version_btn.setStyleSheet("background-color: #f44336;")
        btn_layout.addWidget(load_version_btn)
        btn_layout.addWidget(delete_version_btn)
        versions_layout.addLayout(btn_layout)
        
        self.tab_widget.addTab(versions_tab, "📚 Historial de Versiones")
        
        # Tab de comparación
        compare_tab = QWidget()
        compare_layout = QVBoxLayout(compare_tab)
        
        # Selector rápido de comparación
        quick_compare_layout = QHBoxLayout()
        quick_compare_layout.addWidget(QLabel("Comparación rápida:"))
        
        self.quick_compare_combo = QComboBox()
        self.quick_compare_combo.addItems([
            "Versión anterior",
            "Primera del día anterior",
            "Primera de la semana anterior",
            "Primera del mes anterior"
        ])
        quick_compare_layout.addWidget(self.quick_compare_combo)
        
        quick_compare_btn = QPushButton("Comparar")
        quick_compare_btn.clicked.connect(self.quick_compare)
        quick_compare_layout.addWidget(quick_compare_btn)
        quick_compare_layout.addStretch()
        
        compare_layout.addLayout(quick_compare_layout)
        
        # Resultados de comparación
        self.compare_text = QTextEdit()
        self.compare_text.setReadOnly(True)
        self.compare_text.setFont(QFont("Courier", 10))
        compare_layout.addWidget(self.compare_text)
        
        self.tab_widget.addTab(compare_tab, "🔍 Comparar Versiones")
        
        # Tab de estadísticas
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        
        refresh_stats_btn = QPushButton("Actualizar Estadísticas")
        refresh_stats_btn.clicked.connect(self.update_statistics)
        stats_layout.addWidget(refresh_stats_btn)
        
        self.tab_widget.addTab(stats_tab, "📊 Estadísticas")
        
        right_layout.addWidget(self.tab_widget)
        
        # Agregar widgets al splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 600])
        
        main_layout.addWidget(splitter)
        
        # Cargar versiones existentes
        self.update_versions_tree()
        
    def get_version_timestamp(self):
        """Genera un timestamp para la versión actual"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def save_version(self):
        """Guarda la versión actual del directorio con timestamp automático"""
        if not self.current_directory:
            QMessageBox.warning(self, "Advertencia", "Primero seleccione un directorio")
            return
        
        version_name = self.get_version_timestamp()
        
        # Escanear y guardar
        progress = QProgressDialog("Guardando versión...", "Cancelar", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        scanner = DirectoryScanner(self.current_directory)
        scanner.finished.connect(lambda result: self.save_snapshot(version_name, result))
        scanner.start()
        
        while scanner.isRunning():
            QApplication.processEvents()
        
        progress.close()
    
    def save_snapshot(self, version_name, structure):
        """Guarda un snapshot de la versión"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calcular cambios con la versión anterior
        changes_count = self.calculate_changes_with_previous(structure)
        
        self.snapshots[version_name] = {
            'timestamp': timestamp,
            'datetime': datetime.now(),
            'structure': structure,
            'directory': self.current_directory,
            'changes': changes_count
        }
        
        self.save_snapshots_to_file()
        self.update_versions_tree()
        
        self.current_version_name = version_name
        self.current_snapshot = structure
        
        self.version_info_label.setText(f"✓ Versión actual: {self.format_version_name(version_name)}")
        
        QMessageBox.information(self, "Éxito", 
            f"Versión guardada correctamente\n\n"
            f"Nombre: {self.format_version_name(version_name)}\n"
            f"Fecha: {timestamp}\n"
            f"Cambios detectados: {changes_count}")
        
        self.status_label.setText(f"Versión guardada - {self.format_version_name(version_name)}")
    
    def calculate_changes_with_previous(self, new_structure):
        """Calcula los cambios entre la nueva versión y la anterior"""
        if len(self.snapshots) == 0:
            return "Primera versión"
        
        last_version = sorted(self.snapshots.keys())[-1]
        last_structure = self.snapshots[last_version]['structure']
        
        changes = self.compare_structures(last_structure, new_structure)
        
        added = len([c for c in changes.values() if c == 'added'])
        modified = len([c for c in changes.values() if c == 'modified'])
        deleted = len([c for c in changes.values() if c == 'deleted'])
        
        return f"+{added} ~{modified} -{deleted}"
    
    def format_version_name(self, version_name):
        """Formatea el nombre de la versión para mostrar"""
        try:
            dt = datetime.strptime(version_name, "%Y%m%d_%H%M%S")
            return dt.strftime("%d/%m/%Y %H:%M:%S")
        except:
            return version_name
    
    def update_versions_tree(self):
        """Actualiza el árbol de versiones"""
        self.versions_tree.clear()
        
        for version_name in sorted(self.snapshots.keys(), reverse=True):
            version_data = self.snapshots[version_name]
            item = QTreeWidgetItem(self.versions_tree)
            item.setText(0, self.format_version_name(version_name))
            item.setText(1, version_data['timestamp'])
            item.setText(2, version_data.get('changes', 'Sin cambios'))
            item.setText(3, "Guardada")
            item.setData(0, Qt.UserRole, version_name)
    
    def filter_versions(self):
        """Filtra las versiones según el criterio seleccionado"""
        filter_type = self.filter_combo.currentText()
        now = datetime.now()
        
        self.versions_tree.clear()
        
        for version_name in sorted(self.snapshots.keys(), reverse=True):
            version_data = self.snapshots[version_name]
            version_date = version_data['datetime']
            
            show = True
            if filter_type == "Este mes":
                show = version_date.year == now.year and version_date.month == now.month
            elif filter_type == "Este año":
                show = version_date.year == now.year
            elif filter_type == "Última semana":
                show = version_date >= now - timedelta(days=7)
            
            if show:
                item = QTreeWidgetItem(self.versions_tree)
                item.setText(0, self.format_version_name(version_name))
                item.setText(1, version_data['timestamp'])
                item.setText(2, version_data.get('changes', 'Sin cambios'))
                item.setText(3, "Guardada")
                item.setData(0, Qt.UserRole, version_name)
    
    def quick_compare(self):
        """Comparación rápida con versión anterior según selección"""
        if not self.current_version_name:
            QMessageBox.warning(self, "Advertencia", "Primero debe guardar una versión actual")
            return
        
        compare_type = self.quick_compare_combo.currentText()
        
        if compare_type == "Versión anterior":
            self.compare_with_previous()
        elif compare_type == "Primera del día anterior":
            self.compare_with_previous_day()
        elif compare_type == "Primera de la semana anterior":
            self.compare_with_previous_week()
        elif compare_type == "Primera del mes anterior":
            self.compare_with_previous_month()
    
    def compare_with_previous(self):
        """Compara con la versión anterior inmediata"""
        if len(self.snapshots) < 2:
            QMessageBox.warning(self, "Advertencia", "Se necesitan al menos 2 versiones para comparar")
            return
        
        sorted_versions = sorted(self.snapshots.keys())
        current_idx = sorted_versions.index(self.current_version_name)
        
        if current_idx > 0:
            previous_version = sorted_versions[current_idx - 1]
            self.perform_comparison(previous_version, self.current_version_name)
        else:
            QMessageBox.information(self, "Info", "Esta es la primera versión, no hay versión anterior")
    
    def compare_with_previous_day(self):
        """Compara con la primera versión del día anterior"""
        current_date = datetime.strptime(self.current_version_name[:8], "%Y%m%d").date()
        previous_date = current_date - timedelta(days=1)
        previous_date_str = previous_date.strftime("%Y%m%d")
        
        # Buscar la primera versión del día anterior
        previous_version = None
        for version in sorted(self.snapshots.keys()):
            if version.startswith(previous_date_str):
                previous_version = version
                break
        
        if previous_version:
            self.perform_comparison(previous_version, self.current_version_name)
        else:
            QMessageBox.information(self, "Info", "No se encontró ninguna versión del día anterior")
    
    def compare_with_previous_week(self):
        """Compara con la primera versión de la semana anterior"""
        current_date = datetime.strptime(self.current_version_name[:8], "%Y%m%d").date()
        previous_week = current_date - timedelta(weeks=1)
        previous_week_str = previous_week.strftime("%Y%m%d")
        
        previous_version = None
        for version in sorted(self.snapshots.keys()):
            if version.startswith(previous_week_str):
                previous_version = version
                break
        
        if previous_version:
            self.perform_comparison(previous_version, self.current_version_name)
        else:
            QMessageBox.information(self, "Info", "No se encontró ninguna versión de la semana anterior")
    
    def compare_with_previous_month(self):
        """Compara con la primera versión del mes anterior"""
        current_date = datetime.strptime(self.current_version_name[:8], "%Y%m%d").date()
        if current_date.month == 1:
            previous_month = current_date.replace(year=current_date.year-1, month=12, day=1)
        else:
            previous_month = current_date.replace(month=current_date.month-1, day=1)
        previous_month_str = previous_month.strftime("%Y%m")
        
        previous_version = None
        for version in sorted(self.snapshots.keys()):
            if version.startswith(previous_month_str):
                previous_version = version
                break
        
        if previous_version:
            self.perform_comparison(previous_version, self.current_version_name)
        else:
            QMessageBox.information(self, "Info", "No se encontró ninguna versión del mes anterior")
    
    def compare_with_dialog(self):
        """Abre diálogo para comparar versiones"""
        if len(self.snapshots) < 2:
            QMessageBox.warning(self, "Advertencia", "Se necesitan al menos 2 versiones para comparar")
            return
        
        dialog = VersionCompareDialog(self.snapshots, self)
        if dialog.exec_() == QDialog.Accepted:
            v1, v2 = dialog.get_versions_to_compare(self.current_version_name)
            if v1 and v2:
                self.perform_comparison(v2, v1)  # v2 es la anterior, v1 es la actual
    
    def perform_comparison(self, version_old, version_new):
        """Realiza la comparación entre dos versiones"""
        old_structure = self.snapshots[version_old]['structure']
        new_structure = self.snapshots[version_new]['structure']
        
        changes = self.compare_structures(old_structure, new_structure)
        self.show_changes_report(changes, version_old, version_new)
        
        # Resaltar cambios en el árbol
        self.highlight_changes_in_tree(changes)
        
        self.tab_widget.setCurrentIndex(1)
    
    def compare_structures(self, old_structure, new_structure, path=""):
        """Compara dos estructuras de directorios y detecta cambios"""
        changes = {}
        
        # Detectar archivos añadidos o modificados
        for name, new_data in new_structure.items():
            full_path = os.path.join(path, name) if path else name
            
            if name not in old_structure:
                changes[full_path] = 'added'
            else:
                old_data = old_structure[name]
                # Comparar fecha de modificación y hash
                if (new_data.get('modified') != old_data.get('modified') or
                    new_data.get('hash') != old_data.get('hash')):
                    changes[full_path] = 'modified'
                
                # Comparar subdirectorios recursivamente
                if 'children' in new_data and 'children' in old_data:
                    sub_changes = self.compare_structures(old_data['children'], 
                                                         new_data['children'], 
                                                         full_path)
                    changes.update(sub_changes)
        
        # Detectar archivos eliminados
        for name, old_data in old_structure.items():
            full_path = os.path.join(path, name) if path else name
            if name not in new_structure:
                changes[full_path] = 'deleted'
        
        return changes
    
    def show_changes_report(self, changes, version_old, version_new):
        """Muestra un reporte detallado de cambios"""
        old_date = self.format_version_name(version_old)
        new_date = self.format_version_name(version_new)
        
        report = f"{'='*80}\n"
        report += f"REPORTE DE COMPARACIÓN DE VERSIONES\n"
        report += f"{'='*80}\n\n"
        report += f"📅 Versión anterior: {old_date}\n"
        report += f"📅 Versión actual:   {new_date}\n"
        report += f"{'-'*80}\n\n"
        
        added = [f for f, t in changes.items() if t == 'added']
        modified = [f for f, t in changes.items() if t == 'modified']
        deleted = [f for f, t in changes.items() if t == 'deleted']
        
        if added:
            report += f"🟢 ARCHIVOS NUEVOS ({len(added)}):\n"
            for file in added:
                report += f"   + {file}\n"
            report += "\n"
        
        if modified:
            report += f"🟡 ARCHIVOS MODIFICADOS ({len(modified)}):\n"
            for file in modified:
                report += f"   ~ {file}\n"
            report += "\n"
        
        if deleted:
            report += f"🔴 ARCHIVOS ELIMINADOS ({len(deleted)}):\n"
            for file in deleted:
                report += f"   - {file}\n"
            report += "\n"
        
        if not changes:
            report += "✅ No se detectaron cambios entre las versiones\n"
        
        report += f"\n{'='*80}\n"
        report += f"RESUMEN: +{len(added)} agregados, ~{len(modified)} modificados, -{len(deleted)} eliminados\n"
        
        self.compare_text.setText(report)
    
    def highlight_changes_in_tree(self, changes):
        """Resalta los cambios en el árbol de directorios"""
        # Implementación para resaltar en el árbol
        pass
    
    def update_statistics(self):
        """Actualiza las estadísticas del sistema"""
        stats = f"{'='*60}\n"
        stats += "ESTADÍSTICAS DEL SISTEMA DE VERSIONES\n"
        stats += f"{'='*60}\n\n"
        
        stats += f"📊 Total de versiones guardadas: {len(self.snapshots)}\n"
        
        if self.snapshots:
            # Versiones por mes
            stats += "\n📅 VERSIONES POR MES:\n"
            months = {}
            for version in self.snapshots.keys():
                month = version[:6]
                months[month] = months.get(month, 0) + 1
            
            for month, count in sorted(months.items()):
                date_obj = datetime.strptime(month, "%Y%m")
                stats += f"   {date_obj.strftime('%B %Y')}: {count} versión(es)\n"
            
            # Versiones por día de semana
            stats += "\n📆 DISTRIBUCIÓN POR DÍA DE SEMANA:\n"
            weekdays = {}
            for version_data in self.snapshots.values():
                weekday = version_data['datetime'].strftime('%A')
                weekdays[weekday] = weekdays.get(weekday, 0) + 1
            
            for day, count in weekdays.items():
                stats += f"   {day}: {count}\n"
        
        self.stats_text.setText(stats)
        self.tab_widget.setCurrentIndex(2)
    
    def export_report(self):
        """Exporta un reporte completo"""
        if not self.snapshots:
            QMessageBox.warning(self, "Advertencia", "No hay versiones para exportar")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar Reporte", 
                                                   f"reporte_versiones_{datetime.now().strftime('%Y%m%d')}.txt",
                                                   "Archivos de texto (*.txt)")
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("REPORTE COMPLETO DE VERSIONES\n")
                f.write("="*60 + "\n\n")
                
                for version in sorted(self.snapshots.keys(), reverse=True):
                    version_data = self.snapshots[version]
                    f.write(f"Versión: {self.format_version_name(version)}\n")
                    f.write(f"Fecha: {version_data['timestamp']}\n")
                    f.write(f"Cambios: {version_data.get('changes', 'N/A')}\n")
                    f.write("-"*40 + "\n")
            
            QMessageBox.information(self, "Éxito", f"Reporte exportado a:\n{file_path}")
    
    def load_selected_version(self):
        """Carga una versión seleccionada para visualizar"""
        selected = self.versions_tree.currentItem()
        if selected:
            version_name = selected.data(0, Qt.UserRole)
            if version_name in self.snapshots:
                snapshot = self.snapshots[version_name]
                self.current_snapshot = snapshot['structure']
                self.display_tree(snapshot['structure'])
                self.version_info_label.setText(f"📖 Visualizando versión: {self.format_version_name(version_name)}")
    
    def delete_selected_version(self):
        """Elimina la versión seleccionada"""
        selected = self.versions_tree.currentItem()
        if selected:
            version_name = selected.data(0, Qt.UserRole)
            reply = QMessageBox.question(self, 'Confirmar', 
                                        f'¿Eliminar versión {self.format_version_name(version_name)}?',
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                del self.snapshots[version_name]
                self.save_snapshots_to_file()
                self.update_versions_tree()
                QMessageBox.information(self, "Éxito", "Versión eliminada")
    
    def save_snapshots_to_file(self):
        """Guarda los snapshots en un archivo"""
        # Convertir datetime a string para JSON
        serializable_snapshots = {}
        for version, data in self.snapshots.items():
            serializable_data = data.copy()
            serializable_data['datetime'] = data['datetime'].isoformat()
            serializable_snapshots[version] = serializable_data
        
        with open(self.snapshots_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_snapshots, f, ensure_ascii=False, indent=2)
    
    def load_snapshots(self):
        """Carga los snapshots desde el archivo"""
        if os.path.exists(self.snapshots_file):
            try:
                with open(self.snapshots_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for version, version_data in data.items():
                        version_data['datetime'] = datetime.fromisoformat(version_data['datetime'])
                        self.snapshots[version] = version_data
            except Exception as e:
                print(f"Error al cargar snapshots: {e}")
    
    def select_directory(self):
        """Selecciona el directorio a versionar"""
        directory = QFileDialog.getExistingDirectory(self, "Seleccionar Directorio")
        if directory:
            self.current_directory = directory
            self.scan_and_display_directory(directory)
            self.save_version_btn.setEnabled(True)
            self.compare_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            self.current_info_label.setText(f"📂 Directorio: {directory}")
            self.status_label = QLabel(f"Directorio actual: {directory}")
    
    def scan_and_display_directory(self, directory, highlight_changes=None):
        """Escanea y muestra el directorio en el árbol"""
        self.tree_widget.clear()
        
        progress = QProgressDialog("Escaneando directorio...", "Cancelar", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        scanner = DirectoryScanner(directory)
        scanner.progress.connect(lambda val, msg: progress.setLabelText(msg))
        scanner.finished.connect(lambda result: self.display_tree(result, highlight_changes))
        scanner.file_scanned.connect(lambda file: None)
        
        scanner.start()
        
        while scanner.isRunning():
            QApplication.processEvents()
        
        progress.close()
    
    def display_tree(self, structure, highlight_changes=None, parent_item=None, path=""):
        """Muestra la estructura del directorio en el árbol"""
        if parent_item is None:
            parent_item = self.tree_widget
            root_info = FileInfo(self.current_directory, 
                                os.path.basename(self.current_directory),
                                "", "", 0)
            root_item = QTreeWidgetItem(parent_item)
            root_item.setText(0, root_info.name)
            root_item.setText(1, "Directorio raíz")
            root_item.setText(2, "Directorio raíz")
            root_item.setText(3, "")
            parent_item = root_item
        
        for name, data in structure.items():
            item = QTreeWidgetItem(parent_item)
            item.setText(0, name)
            
            # Aplicar resaltado si hay cambios
            if highlight_changes and name in highlight_changes:
                change_type = highlight_changes[name]
                if change_type == 'added':
                    item.setForeground(0, QBrush(QColor(0, 150, 0)))
                elif change_type == 'modified':
                    item.setForeground(0, QBrush(QColor(255, 140, 0)))
                elif change_type == 'deleted':
                    item.setForeground(0, QBrush(QColor(200, 0, 0)))
            
            item.setText(1, data.get('created', 'N/A'))
            item.setText(2, data.get('modified', 'N/A'))
            
            if data.get('size', 0) > 0:
                size_str = f"{data['size'] / 1024:.2f} KB" if data['size'] < 1048576 else f"{data['size'] / 1048576:.2f} MB"
                item.setText(3, size_str)
            else:
                item.setText(3, "<DIR>")
            
            if data.get('hash'):
                item.setText(4, data['hash'][:8] + "...")
            
            if 'children' in data and data['children']:
                self.display_tree(data['children'], highlight_changes, item, 
                                os.path.join(path, name) if path else name)
    
    def refresh_current(self, highlight_changes=None):
        """Actualiza la vista actual del directorio"""
        if self.current_directory:
            self.scan_and_display_directory(self.current_directory, highlight_changes)

def main():
    app = QApplication(sys.argv)
    window = VersionControlSystem()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()