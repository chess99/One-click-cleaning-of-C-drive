#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
C盘清理工具 - 用户界面
"""

import os

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)

from cleaner_logic import CleanerLogic


class ScanThread(QThread):
    """扫描线程，避免UI冻结"""
    update_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, cleaner):
        super().__init__()
        self.cleaner = cleaner
        
    def run(self):
        """运行扫描过程"""
        results = self.cleaner.scan_system()
        self.finished_signal.emit(results)


class CleanThread(QThread):
    """清理线程，避免UI冻结"""
    update_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, cleaner, selected_items):
        super().__init__()
        self.cleaner = cleaner
        self.selected_items = selected_items
        
    def run(self):
        """运行清理过程"""
        results = self.cleaner.clean_selected(self.selected_items, self.update_signal)
        self.finished_signal.emit(results)


class CleanerMainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.cleaner = CleanerLogic()
        self.scan_results = {}
        self.selected_items = []
        
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("C盘清理工具")
        self.setMinimumSize(800, 650)
        
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        info_group = QGroupBox("系统信息")
        info_layout = QVBoxLayout(info_group)
        self.disk_info_label = QLabel("C盘使用情况: 正在加载...")
        info_layout.addWidget(self.disk_info_label)
        
        button_layout = QHBoxLayout()
        self.scan_button = QPushButton("扫描系统")
        self.scan_button.setMinimumHeight(40)
        self.scan_button.clicked.connect(self.start_scan)
        button_layout.addWidget(self.scan_button)

        self.clean_button = QPushButton("清理选中项")
        self.clean_button.setMinimumHeight(40)
        self.clean_button.setEnabled(False)
        self.clean_button.clicked.connect(self.start_clean)
        button_layout.addWidget(self.clean_button)

        self.select_all_button = QPushButton("全选")
        self.select_all_button.setMinimumHeight(40)
        self.select_all_button.setEnabled(False)
        self.select_all_button.clicked.connect(self.select_all_items)
        button_layout.addWidget(self.select_all_button)

        self.deselect_all_button = QPushButton("取消全选")
        self.deselect_all_button.setMinimumHeight(40)
        self.deselect_all_button.setEnabled(False)
        self.deselect_all_button.clicked.connect(self.deselect_all_items)
        button_layout.addWidget(self.deselect_all_button)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_label = QLabel("")
        
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["项目", "大小", "路径"])
        self.results_tree.setColumnWidth(0, 250)
        self.results_tree.setColumnWidth(1, 100)
        self.results_tree.itemChanged.connect(self.on_item_changed)
        
        # Define display names for categories
        self.categories_display_names = {
            # 基本清理
            'temp': "临时文件",
            'recycle': "回收站",
            'cache': "浏览器缓存",
            'logs': "系统日志",
            'updates': "Windows更新缓存",
            'thumbnails': "缩略图缓存",

            # 扩展清理
            'prefetch': "预读取文件",
            'old_windows': "旧Windows文件",
            'error_reports': "错误报告",
            'service_packs': "服务包备份",
            'memory_dumps': "内存转储文件",
            'font_cache': "字体缓存",
            'disk_cleanup': "磁盘清理备份",

            # 新增安全清理项
            'app_cache': "应用程序缓存",
            'media_cache': "媒体播放器缓存",
            'search_index': "搜索索引临时文件",
            'backup_temp': "备份临时文件",
            'update_temp': "更新临时文件",
            'driver_backup': "驱动备份",
            'app_crash': "应用程序崩溃转储",
            'app_logs': "应用程序日志",
            'recent_items': "最近使用的文件列表",
            'notification': "Windows通知缓存",
            'dns_cache': "DNS缓存",
            'network_cache': "网络缓存", # Make sure this key exists in cleaner_logic results
            'printer_temp': "打印机临时文件", # Make sure this key exists in cleaner_logic results
            'device_temp': "设备临时文件",   # Make sure this key exists in cleaner_logic results
            'windows_defender': "Windows Defender缓存", # Make sure this key exists in cleaner_logic results
            'store_cache': "Windows Store缓存", # Make sure this key exists in cleaner_logic results
            'onedrive_cache': "OneDrive缓存", # Make sure this key exists in cleaner_logic results

            # 新增用户请求的清理项
            'downloads': "下载文件夹",
            'installer_cache': "安装程序缓存",
            'delivery_opt': "Windows传递优化缓存",
            
            # 大文件扫描
            'large_files': "大文件"
        }

        # Define default selection state for categories
        self.categories_default_selection = {
            # 基本清理
            'temp': True,
            'recycle': True,
            'cache': True,
            'logs': True,
            'updates': True,
            'thumbnails': True,

            # 扩展清理
            'prefetch': True,
            'old_windows': True,
            'error_reports': True,
            'service_packs': True,
            'memory_dumps': True,
            'font_cache': True,
            'disk_cleanup': True,

            # 新增安全清理项
            'app_cache': True,
            'media_cache': True,
            'search_index': True,
            'backup_temp': True,
            'update_temp': True,
            'driver_backup': True,
            'app_crash': True,
            'app_logs': True,
            'recent_items': True,
            'notification': True,
            'dns_cache': True,
            'network_cache': True, 
            'printer_temp': True,
            'device_temp': True,  
            'windows_defender': True,
            'store_cache': True, 
            'onedrive_cache': True,

            # 新增用户请求的清理项
            'downloads': False, # Do not select by default
            'installer_cache': True,
            'delivery_opt': True,
            
            # 大文件扫描
            'large_files': False # Do not select by default
        }
        
        safety_group = QGroupBox("安全选项")
        safety_layout = QVBoxLayout(safety_group)
        
        self.simulate_checkbox = QCheckBox("模拟模式 (不实际删除文件)")
        self.simulate_checkbox.setChecked(True)
        safety_layout.addWidget(self.simulate_checkbox)
        
        self.backup_checkbox = QCheckBox("删除前备份文件")
        self.backup_checkbox.setChecked(True)
        safety_layout.addWidget(self.backup_checkbox)

        backup_dir_layout = QHBoxLayout()
        backup_dir_label = QLabel("备份目录:")
        backup_dir_layout.addWidget(backup_dir_label)

        self.backup_dir_edit = QLineEdit(self.cleaner.backup_dir)
        backup_dir_layout.addWidget(self.backup_dir_edit)

        browse_backup_button = QPushButton("浏览...")
        browse_backup_button.clicked.connect(self.browse_backup_dir)
        backup_dir_layout.addWidget(browse_backup_button)
        safety_layout.addLayout(backup_dir_layout)

        self.backup_manager_button = QPushButton("备份管理")
        self.backup_manager_button.clicked.connect(self.open_backup_manager)
        safety_layout.addWidget(self.backup_manager_button, 0, Qt.AlignLeft)
        
        main_layout.addWidget(info_group)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.results_tree)
        main_layout.addWidget(safety_group)
        
        self.setCentralWidget(central_widget)
        
        self.update_disk_info()
    
    def update_disk_info(self):
        """更新磁盘信息"""
        disk_info = self.cleaner.get_disk_info()
        self.disk_info_label.setText(
            f"C盘总空间: {disk_info['total']:.2f} GB | "
            f"已用空间: {disk_info['used']:.2f} GB ({disk_info['percent']}%) | "
            f"可用空间: {disk_info['free']:.2f} GB"
        )
    
    def start_scan(self):
        """开始扫描系统"""
        self.scan_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.select_all_button.setEnabled(False)
        self.deselect_all_button.setEnabled(False)
        self.results_tree.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("正在扫描系统，请稍候...")
        
        self.scan_thread = ScanThread(self.cleaner)
        self.scan_thread.finished_signal.connect(self.on_scan_finished)
        self.scan_thread.start()
    
    def on_scan_finished(self, results):
        """扫描完成后的处理"""
        self.scan_results = results
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)
        
        if not results or not any(results.values()): # Check if results dict itself is empty or all its lists are empty
            self.status_label.setText("扫描完成，未发现可清理项目")
            self.select_all_button.setEnabled(False)
            self.deselect_all_button.setEnabled(False)
            self.results_tree.clear() # Clear tree if no results
            return
            
        total_size = sum(item['size'] for category_items in results.values() for item in category_items)
        self.status_label.setText(f"扫描完成，发现可释放空间: {self.format_size(total_size)}")
        
        self.populate_results_tree(results)
        self.update_selected_items() 
        self.select_all_button.setEnabled(True)
        self.deselect_all_button.setEnabled(True)
        
        self.update_disk_info()
    
    def populate_results_tree(self, results):
        """填充结果树"""
        self.results_tree.clear()
        
        original_signals_blocked = self.results_tree.signalsBlocked()
        self.results_tree.blockSignals(True)
        try:
            # Use the display name and default selection from our dictionaries
            # Order categories as they appear in categories_display_names for consistency,
            # if results might come in a different order.
            # For now, using results.items() which depends on cleaner_logic's output order.
            
            # Ensure all keys from results are present in categories_default_selection
            # and categories_display_names. Log a warning for missing ones.
            # This is important if cleaner_logic adds new categories.
            # For now, assume they are aligned.

            for category_key, items in results.items():
                if not items:
                    continue
                    
                category_size = sum(item['size'] for item in items)
                # Use the display name from our comprehensive dict, fallback to key if not found
                category_display_name = self.categories_display_names.get(category_key, category_key.replace('_', ' ').title())
                default_selected = self.categories_default_selection.get(category_key, True) # Default to True if key somehow missing
                
                category_item = QTreeWidgetItem(self.results_tree)
                category_item.setText(0, category_display_name)
                category_item.setText(1, self.format_size(category_size))
                category_item.setFlags(category_item.flags() | Qt.ItemIsUserCheckable)
                # Set check state based on default_selected for the category itself
                category_item.setCheckState(0, Qt.Checked if default_selected else Qt.Unchecked)
                category_item.setData(0, Qt.UserRole + 1, category_key) # Store category key for later use if needed
                
                for item_data in items:
                    file_item = QTreeWidgetItem(category_item)
                    base_name = os.path.basename(item_data['path'])
                    display_text = base_name

                    # Special handling for 'large_files' as in tkinter version
                    if category_key == 'large_files':
                        modified_time = item_data.get('modified', '未知')
                        extension = item_data.get('extension', '未知')
                        display_text = f"{base_name} [修改时间: {modified_time}] [类型: {extension}]"
                    
                    file_item.setText(0, display_text) # Column 0: Name (or enhanced name for large files)
                    file_item.setText(1, self.format_size(item_data['size'])) # Column 1: Size
                    file_item.setText(2, item_data['path']) # Column 2: Path
                    file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable)
                    # Set child item's check state based on the parent category's default_selected status
                    file_item.setCheckState(0, Qt.Checked if default_selected else Qt.Unchecked)
                    file_item.setData(0, Qt.UserRole, item_data) # Store the original item dict
            
            self.results_tree.expandAll()
        finally:
            self.results_tree.blockSignals(original_signals_blocked)
    
    def on_item_changed(self, item, column):
        """处理项目选择状态变化"""
        if column != 0:
            return

        # Block signals for the tree during this method's logic to prevent recursion
        # from programmatic setCheckState calls within this handler.
        original_signals_blocked = self.results_tree.signalsBlocked()
        self.results_tree.blockSignals(True)

        try:
            current_check_state = item.checkState(0)

            # If a category (parent) item is changed
            if item.parent() is None:
                for i in range(item.childCount()):
                    child = item.child(i)
                    if child.checkState(0) != current_check_state:
                        child.setCheckState(0, current_check_state)
            # If a file (child) item is changed
            else:
                parent = item.parent()
                all_children_fully_checked = True
                any_child_checked_or_partially = False

                for i in range(parent.childCount()):
                    child_state = parent.child(i).checkState(0)
                    if child_state != Qt.Checked:
                        all_children_fully_checked = False # If even one is not fully checked
                    if child_state == Qt.Checked or child_state == Qt.PartiallyChecked:
                        any_child_checked_or_partially = True
                
                if all_children_fully_checked:
                    if parent.checkState(0) != Qt.Checked:
                        parent.setCheckState(0, Qt.Checked)
                elif any_child_checked_or_partially: # Some are checked/partially, but not all are fully checked
                    if parent.checkState(0) != Qt.PartiallyChecked:
                        parent.setCheckState(0, Qt.PartiallyChecked)
                else: # No children are checked (all are Qt.Unchecked)
                    if parent.checkState(0) != Qt.Unchecked:
                        parent.setCheckState(0, Qt.Unchecked)
        finally:
            # Restore original signal blocking state
            self.results_tree.blockSignals(original_signals_blocked)
        
        # This call is now made after all programmatic changes within this handler are done
        # and signals are restored, so it reflects the final state.
        self.update_selected_items()
    
    def update_selected_items(self):
        """更新选中的项目列表 (Collects selected data and updates button state)"""
        self.selected_items = []
        
        # Iterate through all items to find checked children (file items)
        # No need to block signals here as we are only reading states, not setting them.
        iterator = QTreeWidgetItemIterator(self.results_tree)
        while iterator.value():
            item = iterator.value()
            # We are interested in actual file items (children of categories) that are checked
            if item.parent() is not None and item.checkState(0) == Qt.Checked:
                item_data = item.data(0, Qt.UserRole) # This is the original dict for the file
                if item_data: 
                    self.selected_items.append(item_data)
            iterator += 1 # Move to the next item in the tree
            
        self.clean_button.setEnabled(len(self.selected_items) > 0)
    
    def start_clean(self):
        """开始清理选中的项目"""
        if not self.selected_items:
            return
            
        total_size = sum(item['size'] for item in self.selected_items)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("确认清理")
        
        if self.simulate_checkbox.isChecked():
            msg.setText(f"您选择了模拟模式，将会模拟清理 {len(self.selected_items)} 个项目，总计 {self.format_size(total_size)}。")
        else:
            msg.setText(f"您确定要清理 {len(self.selected_items)} 个项目，总计 {self.format_size(total_size)} 吗？")
            msg.setInformativeText("此操作无法撤销！")
        
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if msg.exec_() != QMessageBox.Yes:
            return
        
        options = {
            'simulate': self.simulate_checkbox.isChecked(),
            'backup': self.backup_checkbox.isChecked(),
            'backup_dir': self.backup_dir_edit.text()
        }
        self.cleaner.set_options(options)
        
        self.scan_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.select_all_button.setEnabled(False)
        self.deselect_all_button.setEnabled(False)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, len(self.selected_items))
        self.status_label.setText("正在清理文件，请稍候...")
        
        self.clean_thread = CleanThread(self.cleaner, self.selected_items)
        self.clean_thread.update_signal.connect(self.on_clean_progress)
        self.clean_thread.finished_signal.connect(self.on_clean_finished)
        self.clean_thread.start()
    
    def on_clean_progress(self, file_path, progress):
        """清理进度更新"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"正在清理: {os.path.basename(file_path)}")
    
    def on_clean_finished(self, results):
        """清理选中项完成后的处理"""
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)
        # Enable buttons that should be active if scan results exist
        if self.scan_results:
            self.select_all_button.setEnabled(True)
            self.deselect_all_button.setEnabled(True)
        
        freed_space = results.get('freed_space', 0)
        errors = results.get('errors', [])
        
        if self.simulate_checkbox.isChecked():
            message = f"模拟清理完成，可释放空间: {self.format_size(freed_space)}"
        else:
            message = f"清理完成，已释放空间: {self.format_size(freed_space)}"
        
        if errors:
            message += f"，{len(errors)} 个错误"
        
        self.status_label.setText(message)
        
        if errors:
            error_msg = QMessageBox()
            error_msg.setIcon(QMessageBox.Warning)
            error_msg.setWindowTitle("清理错误")
            error_msg.setText(f"清理过程中发生 {len(errors)} 个错误")
            error_details = "\n".join([f"{err['path']}: {err['error']}" for err in errors[:10]])
            if len(errors) > 10:
                error_details += f"\n... 以及 {len(errors) - 10} 个其他错误"
            error_msg.setDetailedText(error_details)
            error_msg.exec_()
        
        self.update_disk_info()
        # Re-populate the tree. Items that were cleaned might no longer be part of scan_results 
        # if cleaner_logic.scan_system() is designed to exclude already handled/non-existent items.
        # Or, if cleaner_logic.clean_selected modifies scan_results, this will reflect changes.
        # For now, assume populate_results_tree with original scan_results is sufficient and selection states will clear.
        if self.scan_results: # Only populate if there were results to begin with
            self.populate_results_tree(self.scan_results) 
        self.update_selected_items() # Update button states and selected items list

    def select_all_items(self):
        """全选所有项目"""
        self.results_tree.blockSignals(True) # Block itemChanged signals during bulk update
        for i in range(self.results_tree.topLevelItemCount()):
            category_item = self.results_tree.topLevelItem(i)
            category_item.setCheckState(0, Qt.Checked)
            for j in range(category_item.childCount()):
                child_item = category_item.child(j)
                child_item.setCheckState(0, Qt.Checked)
        self.results_tree.blockSignals(False)
        self.update_selected_items() # Update the selected list and button states

    def deselect_all_items(self):
        """取消全选所有项目"""
        self.results_tree.blockSignals(True) # Block itemChanged signals during bulk update
        for i in range(self.results_tree.topLevelItemCount()):
            category_item = self.results_tree.topLevelItem(i)
            category_item.setCheckState(0, Qt.Unchecked)
            for j in range(category_item.childCount()):
                child_item = category_item.child(j)
                child_item.setCheckState(0, Qt.Unchecked)
        self.results_tree.blockSignals(False)
        self.update_selected_items() # Update the selected list and button states

    def browse_backup_dir(self):
        """浏览选择备份目录"""
        current_dir = self.backup_dir_edit.text()
        if not os.path.isdir(current_dir): # Check if current path is a valid directory
            current_dir = os.path.expanduser("~") # Default to home if not valid

        backup_dir = QFileDialog.getExistingDirectory(
            self, 
            "选择备份目录", 
            current_dir # Start browsing from current or home directory
        )

        if backup_dir: # If a directory was selected (not cancelled)
            self.backup_dir_edit.setText(backup_dir)
            # Optionally, update cleaner_logic immediately if desired, or just use the text field value at clean time
            # self.cleaner.set_options({'backup_dir': backup_dir}) 

    def open_backup_manager(self):
        QMessageBox.information(self, "提示", "'备份管理' 功能暂未实现。")
    
    @staticmethod
    def format_size(size_bytes):
        """格式化文件大小显示"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.2f} MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.2f} GB"

if __name__ == "__main__":
    import logging
    import sys

    from PyQt5.QtWidgets import QApplication

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename='cleaner.log'
    )
    logger = logging.getLogger('CleanerAppPyQt')

    app = QApplication(sys.argv)
    main_window = CleanerMainWindow()
    main_window.show()
    logger.info("应用程序已启动。")
    sys.exit(app.exec_()) 