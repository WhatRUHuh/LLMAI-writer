import json
import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QComboBox, QGroupBox, QFormLayout,
    QMessageBox, QSplitter, QDialog, QListWidget, QListWidgetItem,
    QTabWidget, QInputDialog, QScrollArea, QMenu, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtGui import QAction, QCursor

# 使用通用组件
from utils.async_utils import GenerationThread, ProgressIndicator
from ui.components import AIGenerateDialog


class ChapterOutlineTab(QWidget):
    """章节大纲编辑标签页"""

    def __init__(self, main_window):
        super().__init__()

        self.main_window = main_window
        self.outline = None
        self.current_volume_index = -1
        self.current_chapter_index = -1
        
        # 标记是否有未保存的修改
        self.has_unsaved_changes = False
        # 记录原始内容，用于检测修改
        self.original_volume_title = ""
        self.original_volume_intro = ""
        self.original_chapter_title = ""
        self.original_chapter_summary = ""
        
        # 防止无限循环的标记
        self._updating_from_external = False
        
        # 延迟保存定时器（用于自动保存）
        self.auto_save_timer = QTimer()
        self.auto_save_timer.setSingleShot(True)  # 只触发一次
        self.auto_save_timer.timeout.connect(self._delayed_auto_save)
        self.auto_save_delay = 5000  # 5秒延迟，给用户更多思考时间

        # 初始化UI
        self._init_ui()

        # 加载大纲
        self._load_outline()

    def _init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 创建左侧面板（卷和章节列表）
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 卷列表
        volume_group = QGroupBox("卷列表")
        volume_layout = QVBoxLayout()

        self.volume_list = QListWidget()
        self.volume_list.currentRowChanged.connect(self._on_volume_selected)
        self.volume_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.volume_list.customContextMenuRequested.connect(self._show_volume_context_menu)
        # 启用拖放功能
        self.volume_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.volume_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.volume_list.setDragEnabled(True)
        self.volume_list.setAcceptDrops(True)
        self.volume_list.setDropIndicatorShown(True)
        # 连接拖放信号
        self.volume_list.model().rowsMoved.connect(self._on_volume_moved)
        volume_layout.addWidget(self.volume_list)

        # 卷操作按钮
        volume_button_layout = QHBoxLayout()

        self.add_volume_button = QPushButton("添加卷")
        self.add_volume_button.clicked.connect(self._add_volume)
        volume_button_layout.addWidget(self.add_volume_button)

        volume_layout.addLayout(volume_button_layout)
        volume_group.setLayout(volume_layout)
        left_layout.addWidget(volume_group)

        # 章节列表
        chapter_group = QGroupBox("章节列表")
        chapter_layout = QVBoxLayout()

        self.chapter_list = QListWidget()
        self.chapter_list.currentRowChanged.connect(self._on_chapter_selected)
        self.chapter_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chapter_list.customContextMenuRequested.connect(self._show_chapter_context_menu)
        # 启用拖放功能
        self.chapter_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.chapter_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.chapter_list.setDragEnabled(True)
        self.chapter_list.setAcceptDrops(True)
        self.chapter_list.setDropIndicatorShown(True)
        # 连接拖放信号
        self.chapter_list.model().rowsMoved.connect(self._on_chapter_moved)
        chapter_layout.addWidget(self.chapter_list)

        # 章节操作按钮
        chapter_button_layout = QHBoxLayout()

        self.add_chapter_button = QPushButton("添加章节")
        self.add_chapter_button.clicked.connect(self._add_chapter)
        self.add_chapter_button.setEnabled(False)
        chapter_button_layout.addWidget(self.add_chapter_button)

        chapter_layout.addLayout(chapter_button_layout)
        chapter_group.setLayout(chapter_layout)
        left_layout.addWidget(chapter_group)

        # 添加左侧面板到分割器
        splitter.addWidget(left_panel)

        # 创建右侧面板（编辑区域）
        right_panel = QScrollArea()
        right_panel.setWidgetResizable(True)
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)

        # 卷编辑区域
        self.volume_edit_group = QGroupBox("卷编辑")
        volume_edit_layout = QVBoxLayout()

        # 卷标题
        volume_title_layout = QHBoxLayout()
        volume_title_layout.addWidget(QLabel("卷标题:"))

        self.volume_title_edit = QLineEdit()
        self.volume_title_edit.textChanged.connect(self._on_content_changed)
        self.volume_title_edit.editingFinished.connect(self._on_editing_finished)
        volume_title_layout.addWidget(self.volume_title_edit)

        self.volume_title_ai_button = QPushButton("AI生成")
        self.volume_title_ai_button.clicked.connect(lambda: self._generate_with_ai("卷标题", self.volume_title_edit.text(), self.volume_title_edit.setText))
        volume_title_layout.addWidget(self.volume_title_ai_button)

        volume_edit_layout.addLayout(volume_title_layout)

        # 卷简介
        volume_edit_layout.addWidget(QLabel("卷简介:"))

        self.volume_intro_edit = QTextEdit()
        self.volume_intro_edit.setMinimumHeight(100)
        self.volume_intro_edit.textChanged.connect(self._on_content_changed)
        # QTextEdit没有editingFinished信号，使用focusOutEvent
        self.volume_intro_edit.focusOutEvent = self._create_focus_out_handler(self.volume_intro_edit.focusOutEvent)
        volume_edit_layout.addWidget(self.volume_intro_edit)

        volume_intro_button_layout = QHBoxLayout()
        volume_intro_button_layout.addStretch()

        self.volume_intro_ai_button = QPushButton("AI生成")
        self.volume_intro_ai_button.clicked.connect(lambda: self._generate_with_ai("卷简介", self.volume_intro_edit.toPlainText(), self.volume_intro_edit.setPlainText))
        volume_intro_button_layout.addWidget(self.volume_intro_ai_button)

        volume_edit_layout.addLayout(volume_intro_button_layout)

        self.volume_edit_group.setLayout(volume_edit_layout)
        right_layout.addWidget(self.volume_edit_group)

        # 章节编辑区域
        self.chapter_edit_group = QGroupBox("章节编辑")
        chapter_edit_layout = QVBoxLayout()

        # 章节标题
        chapter_title_layout = QHBoxLayout()
        chapter_title_layout.addWidget(QLabel("章节标题:"))

        self.chapter_title_edit = QLineEdit()
        self.chapter_title_edit.textChanged.connect(self._on_content_changed)
        self.chapter_title_edit.editingFinished.connect(self._on_editing_finished)
        chapter_title_layout.addWidget(self.chapter_title_edit)

        self.chapter_title_ai_button = QPushButton("AI生成")
        self.chapter_title_ai_button.clicked.connect(lambda: self._generate_with_ai("章节标题", self.chapter_title_edit.text(), self.chapter_title_edit.setText))
        chapter_title_layout.addWidget(self.chapter_title_ai_button)

        chapter_edit_layout.addLayout(chapter_title_layout)

        # 章节摘要
        chapter_edit_layout.addWidget(QLabel("章节摘要:"))

        self.chapter_summary_edit = QTextEdit()
        self.chapter_summary_edit.setMinimumHeight(150)
        self.chapter_summary_edit.textChanged.connect(self._on_content_changed)
        # QTextEdit没有editingFinished信号，使用focusOutEvent
        self.chapter_summary_edit.focusOutEvent = self._create_focus_out_handler(self.chapter_summary_edit.focusOutEvent)
        chapter_edit_layout.addWidget(self.chapter_summary_edit)

        chapter_summary_button_layout = QHBoxLayout()
        chapter_summary_button_layout.addStretch()

        # 添加选择角色按钮
        self.chapter_summary_select_characters_button = QPushButton("选择角色")
        self.chapter_summary_select_characters_button.clicked.connect(lambda: self._select_characters_for_summary())
        chapter_summary_button_layout.addWidget(self.chapter_summary_select_characters_button)

        self.chapter_summary_ai_button = QPushButton("AI生成")
        self.chapter_summary_ai_button.clicked.connect(lambda: self._generate_with_ai("章节摘要", self.chapter_summary_edit.toPlainText(), self.chapter_summary_edit.setPlainText))
        chapter_summary_button_layout.addWidget(self.chapter_summary_ai_button)

        chapter_edit_layout.addLayout(chapter_summary_button_layout)

        self.chapter_edit_group.setLayout(chapter_edit_layout)
        right_layout.addWidget(self.chapter_edit_group)

        # 保存按钮和自动保存选项
        save_layout = QHBoxLayout()
        
        # 自动保存复选框
        self.auto_save_checkbox = QCheckBox("自动保存")
        self.auto_save_checkbox.setToolTip("启用后，修改内容时会自动保存，无需手动点击保存按钮")
        self.auto_save_checkbox.setChecked(True)  # 默认启用自动保存
        save_layout.addWidget(self.auto_save_checkbox)
        
        save_layout.addStretch()

        self.save_button = QPushButton("保存修改")
        self.save_button.clicked.connect(self._save_outline)
        save_layout.addWidget(self.save_button)

        right_layout.addLayout(save_layout)

        # 设置右侧面板
        right_panel.setWidget(right_content)
        splitter.addWidget(right_panel)

        # 设置分割器比例
        splitter.setSizes([300, 700])

        # 初始禁用编辑区域
        self.volume_edit_group.setEnabled(False)
        self.chapter_edit_group.setEnabled(False)

    def _load_outline(self):
        """加载大纲"""
        self.outline = self.main_window.get_outline()
        if not self.outline:
            return

        # 清空列表
        self.volume_list.clear()
        self.chapter_list.clear()

        # 加载卷列表
        volumes = self.outline.get("volumes", [])
        for i, volume in enumerate(volumes):
            title = volume.get("title", f"第{i+1}卷")
            self.volume_list.addItem(title)
        
        # 重置修改状态
        self.has_unsaved_changes = False
        self.save_button.setText("保存修改")
        self._update_original_content()

    def _on_volume_selected(self, index):
        """卷选择事件"""
        # 如果点击的是当前卷，直接返回
        if index == self.current_volume_index:
            return
        
        # 选择切换时不需要立即保存，交给失去焦点或延迟保存处理
        
        self.current_volume_index = index
        self.current_chapter_index = -1

        # 清空章节列表
        self.chapter_list.clear()

        # 禁用章节编辑区域
        self.chapter_edit_group.setEnabled(False)

        if index < 0:
            # 禁用卷编辑区域
            self.volume_edit_group.setEnabled(False)
            self.add_chapter_button.setEnabled(False)
            return

        # 启用卷编辑区域和添加章节按钮
        self.volume_edit_group.setEnabled(True)
        self.add_chapter_button.setEnabled(True)

        # 加载卷信息
        volumes = self.outline.get("volumes", [])
        
        if index < len(volumes):
            volume = volumes[index]
            self.volume_title_edit.setText(volume.get("title", f"第{index+1}卷"))
            # 使用description字段作为卷简介
            self.volume_intro_edit.setPlainText(volume.get("description", ""))

            # 加载章节列表
            chapters = volume.get("chapters", [])
            
            for i, chapter in enumerate(chapters):
                title = chapter.get("title", f"第{i+1}章")
                self.chapter_list.addItem(title)
        
        # 更新原始内容记录
        self._update_original_content()

    def _on_chapter_selected(self, index):
        """章节选择事件"""
        # 如果点击的是当前章节，直接返回
        if index == self.current_chapter_index:
            return
        
        # 选择切换时不需要立即保存，交给失去焦点或延迟保存处理
        
        self.current_chapter_index = index

        if index < 0:
            # 禁用章节编辑区域
            self.chapter_edit_group.setEnabled(False)
            return

        # 启用章节编辑区域
        self.chapter_edit_group.setEnabled(True)

        # 加载章节信息
        volumes = self.outline.get("volumes", [])
        
        if self.current_volume_index < len(volumes):
            volume = volumes[self.current_volume_index]
            chapters = volume.get("chapters", [])
            
            if index < len(chapters):
                chapter = chapters[index]
                title = chapter.get("title", f"第{index+1}章")
                summary = chapter.get("summary", "")
                
                self.chapter_title_edit.setText(title)
                self.chapter_summary_edit.setPlainText(summary)
        
        # 更新原始内容记录
        self._update_original_content()

    def _add_volume(self):
        """添加卷"""
        if not self.outline:
            QMessageBox.warning(self, "错误", "请先生成大纲")
            return

        # 获取卷标题
        title, ok = QInputDialog.getText(self, "添加卷", "请输入卷标题:")
        if not ok or not title:
            return

        # 添加卷
        if "volumes" not in self.outline:
            self.outline["volumes"] = []

        new_volume = {
            "title": title,
            "description": "",  # 卷简介
            "chapters": []
        }

        self.outline["volumes"].append(new_volume)

        # 更新卷列表
        self.volume_list.addItem(title)

        # 选择新添加的卷
        self.volume_list.setCurrentRow(self.volume_list.count() - 1)

    def _add_chapter(self):
        """添加章节"""
        if self.current_volume_index < 0:
            return

        # 获取章节标题
        title, ok = QInputDialog.getText(self, "添加章节", "请输入章节标题:")
        if not ok or not title:
            return

        # 添加章节
        volumes = self.outline.get("volumes", [])
        if self.current_volume_index < len(volumes):
            volume = volumes[self.current_volume_index]
            if "chapters" not in volume:
                volume["chapters"] = []

            # 获取当前章节数量，用于生成章节序号
            chapter_count = len(volume["chapters"])
            chapter_number = chapter_count + 1

            # 如果标题中没有包含章节序号，自动添加
            if not title.startswith(f"第{chapter_number}章") and not title.startswith(f"第{chapter_number} 章"):
                title = f"第{chapter_number}章：{title}"

            new_chapter = {
                "title": title,
                "summary": ""
            }

            volume["chapters"].append(new_chapter)

            # 更新章节列表
            self.chapter_list.addItem(title)

            # 选择新添加的章节
            self.chapter_list.setCurrentRow(self.chapter_list.count() - 1)

    def _show_volume_context_menu(self, position):
        """显示卷右键菜单"""
        if self.volume_list.count() == 0:
            return

        menu = QMenu()

        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(lambda: self._edit_volume_title())
        menu.addAction(edit_action)

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_volume())
        menu.addAction(delete_action)

        menu.exec(QCursor.pos())

    def _show_chapter_context_menu(self, position):
        """显示章节右键菜单"""
        if self.chapter_list.count() == 0:
            return

        menu = QMenu()

        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(lambda: self._edit_chapter_title())
        menu.addAction(edit_action)

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_chapter())
        menu.addAction(delete_action)

        menu.exec(QCursor.pos())

    def _edit_volume_title(self):
        """编辑卷标题"""
        current_item = self.volume_list.currentItem()
        if not current_item:
            return

        current_title = current_item.text()
        new_title, ok = QInputDialog.getText(self, "编辑卷标题", "请输入新的卷标题:", text=current_title)
        if not ok or not new_title:
            return

        # 更新卷标题
        current_item.setText(new_title)
        self.volume_title_edit.setText(new_title)

        # 更新大纲数据
        volumes = self.outline.get("volumes", [])
        if self.current_volume_index < len(volumes):
            volumes[self.current_volume_index]["title"] = new_title

    def _edit_chapter_title(self):
        """编辑章节标题"""
        current_item = self.chapter_list.currentItem()
        if not current_item:
            return

        current_title = current_item.text()
        new_title, ok = QInputDialog.getText(self, "编辑章节标题", "请输入新的章节标题:", text=current_title)
        if not ok or not new_title:
            return

        # 更新章节标题
        current_item.setText(new_title)
        self.chapter_title_edit.setText(new_title)

        # 更新大纲数据
        volumes = self.outline.get("volumes", [])
        if self.current_volume_index < len(volumes):
            volume = volumes[self.current_volume_index]
            chapters = volume.get("chapters", [])
            if self.current_chapter_index < len(chapters):
                chapters[self.current_chapter_index]["title"] = new_title

    def _delete_volume(self):
        """删除卷"""
        if self.current_volume_index < 0:
            return

        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这个卷吗？这将同时删除卷中的所有章节。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 删除卷
        volumes = self.outline.get("volumes", [])
        if self.current_volume_index < len(volumes):
            volumes.pop(self.current_volume_index)

            # 更新卷列表
            self.volume_list.takeItem(self.current_volume_index)

            # 清空章节列表
            self.chapter_list.clear()

            # 禁用编辑区域
            self.volume_edit_group.setEnabled(False)
            self.chapter_edit_group.setEnabled(False)
            self.add_chapter_button.setEnabled(False)

    def _delete_chapter(self):
        """删除章节"""
        if self.current_volume_index < 0 or self.current_chapter_index < 0:
            return

        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这个章节吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 删除章节
        volumes = self.outline.get("volumes", [])
        if self.current_volume_index < len(volumes):
            volume = volumes[self.current_volume_index]
            chapters = volume.get("chapters", [])
            if self.current_chapter_index < len(chapters):
                chapters.pop(self.current_chapter_index)

                # 更新章节列表
                self.chapter_list.takeItem(self.current_chapter_index)

                # 禁用章节编辑区域
                self.chapter_edit_group.setEnabled(False)

    def _on_volume_moved(self, parent, start, end, destination, row):
        """处理卷拖放事件"""
        # 计算源和目标索引
        from_index = start
        to_index = row
        if to_index > from_index:
            to_index -= 1

        # 如果源和目标相同，不需要处理
        if from_index == to_index:
            return

        # 移动大纲中的卷
        volumes = self.outline.get("volumes", [])
        volume = volumes.pop(from_index)
        volumes.insert(to_index, volume)

        # 更新当前选中的卷
        self.current_volume_index = to_index

    def _on_chapter_moved(self, parent, start, end, destination, row):
        """处理章节拖放事件"""
        # 如果没有选中卷，不需要处理
        if self.current_volume_index < 0:
            return

        # 计算源和目标索引
        from_index = start
        to_index = row
        if to_index > from_index:
            to_index -= 1

        # 如果源和目标相同，不需要处理
        if from_index == to_index:
            return

        # 移动大纲中的章节
        volumes = self.outline.get("volumes", [])
        volume = volumes[self.current_volume_index]
        chapters = volume.get("chapters", [])
        chapter = chapters.pop(from_index)
        chapters.insert(to_index, chapter)

        # 更新所有章节的序号
        self._update_chapter_numbers()

        # 更新当前选中的章节
        self.current_chapter_index = to_index

    def _update_chapter_numbers(self):
        """更新所有章节的序号"""
        if self.current_volume_index < 0:
            return

        volumes = self.outline.get("volumes", [])
        if self.current_volume_index < len(volumes):
            volume = volumes[self.current_volume_index]
            chapters = volume.get("chapters", [])

            # 清空章节列表
            self.chapter_list.clear()

            # 更新每个章节的标题和序号
            for i, chapter in enumerate(chapters):
                # 提取原标题（去除序号部分）
                title = chapter.get("title", "")
                chapter_number = i + 1

                # 如果标题包含“第”和“章”，则提取内容部分
                if "第" in title and "章" in title:
                    # 尝试提取“章：”后面的内容
                    parts = title.split("章：", 1)
                    if len(parts) > 1:
                        title = parts[1]
                    else:
                        # 尝试提取“章 ”后面的内容
                        parts = title.split("章 ", 1)
                        if len(parts) > 1:
                            title = parts[1]
                        else:
                            # 如果上述方法都失败，则保留原标题
                            pass

                # 更新章节标题
                new_title = f"第{chapter_number}章：{title}"
                chapter["title"] = new_title

                # 更新章节列表
                item = QListWidgetItem(new_title)
                item.setData(Qt.ItemDataRole.UserRole, i)
                self.chapter_list.addItem(item)

            # 选中当前章节
            if self.current_chapter_index >= 0 and self.current_chapter_index < self.chapter_list.count():
                self.chapter_list.setCurrentRow(self.current_chapter_index)

    def _save_outline(self, show_message=True):
        """保存大纲

        Args:
            show_message: 是否显示消息对话框
        """
        if not self.outline:
            return

        # 保存当前编辑的卷和章节
        if self.current_volume_index >= 0:
            volumes = self.outline.get("volumes", [])
            if self.current_volume_index < len(volumes):
                volume = volumes[self.current_volume_index]
                volume["title"] = self.volume_title_edit.text()
                # 更新description字段作为卷简介
                volume["description"] = self.volume_intro_edit.toPlainText()

                if self.current_chapter_index >= 0:
                    chapters = volume.get("chapters", [])
                    if self.current_chapter_index < len(chapters):
                        chapter = chapters[self.current_chapter_index]
                        chapter["title"] = self.chapter_title_edit.text()
                        chapter["summary"] = self.chapter_summary_edit.toPlainText()

        # 保存大纲
        self.main_window.set_outline(self.outline)
        
        # 重置未保存修改标记
        self.has_unsaved_changes = False
        self.save_button.setText("保存修改")
        
        # 更新原始内容记录
        self._update_original_content()

        if show_message:
            QMessageBox.information(self, "保存成功", "大纲修改已保存")

    def _select_characters_for_summary(self):
        """为章节摘要选择出场角色"""
        if not self.outline or "characters" not in self.outline or not self.outline["characters"]:
            QMessageBox.warning(self, "提示", "当前小说没有角色数据，请先在人物编辑标签页添加角色。")
            return

        # 获取当前章节的已选角色（如果有）
        selected_characters = []
        if self.current_volume_index >= 0 and self.current_chapter_index >= 0:
            volumes = self.outline.get("volumes", [])
            if self.current_volume_index < len(volumes):
                volume = volumes[self.current_volume_index]
                chapters = volume.get("chapters", [])
                if self.current_chapter_index < len(chapters):
                    chapter = chapters[self.current_chapter_index]
                    selected_characters = chapter.get("characters", [])

        # 获取所有角色
        all_characters = self.outline["characters"]

        # 创建角色选择对话框
        from ui.character_selector_dialog import CharacterSelectorDialog
        dialog = CharacterSelectorDialog(self, all_characters, selected_characters)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 获取选中的角色
            selected_characters = dialog.get_selected_characters()

            # 保存选中的角色到当前章节
            if self.current_volume_index >= 0 and self.current_chapter_index >= 0:
                volumes = self.outline.get("volumes", [])
                if self.current_volume_index < len(volumes):
                    volume = volumes[self.current_volume_index]
                    chapters = volume.get("chapters", [])
                    if self.current_chapter_index < len(chapters):
                        chapter = chapters[self.current_chapter_index]
                        chapter["characters"] = selected_characters

                        # 自动保存
                        self._save_outline(show_message=False)
                        self.main_window.status_bar_manager.show_message(f"已为章节设置{len(selected_characters)}个出场角色")

    def _generate_with_ai(self, field_name, current_text, set_func):
        """使用AI生成内容"""
        # 获取总大纲信息
        outline_info = {}
        if self.outline:
            outline_info = {
                "title": self.outline.get("title", ""),
                "theme": self.outline.get("theme", ""),
                "synopsis": self.outline.get("synopsis", ""),
                "worldbuilding": self.outline.get("worldbuilding", "")
            }

        # 根据不同的字段添加额外的上下文信息
        context_info = {}

        # 如果是卷简介，添加卷标题信息
        if field_name == "卷简介" and self.current_volume_index >= 0:
            volumes = self.outline.get("volumes", [])
            if self.current_volume_index < len(volumes):
                volume = volumes[self.current_volume_index]
                context_info["volume_title"] = volume.get("title", "")

        # 如果是章节摘要，添加卷标题、卷简介、章节标题信息以及前10章和后3章的标题和摘要
        if field_name == "章节摘要" and self.current_volume_index >= 0 and self.current_chapter_index >= 0:
            volumes = self.outline.get("volumes", [])
            if self.current_volume_index < len(volumes):
                volume = volumes[self.current_volume_index]
                context_info["volume_title"] = volume.get("title", "")
                context_info["volume_description"] = volume.get("description", "")

                chapters = volume.get("chapters", [])
                if self.current_chapter_index < len(chapters):
                    chapter = chapters[self.current_chapter_index]
                    context_info["chapter_title"] = chapter.get("title", "")
                    context_info["chapter_number"] = self.current_chapter_index + 1

                    # 添加章节出场角色信息
                    chapter_characters = chapter.get("characters", [])
                    if chapter_characters:
                        context_info["chapter_characters"] = chapter_characters

                    # 添加前10章的标题和摘要
                    previous_chapters = []
                    start_idx = max(0, self.current_chapter_index - 10)
                    for i in range(start_idx, self.current_chapter_index):
                        if i < len(chapters):
                            prev_chapter = chapters[i]
                            previous_chapters.append({
                                "title": prev_chapter.get("title", ""),
                                "summary": prev_chapter.get("summary", "")
                            })
                    context_info["previous_chapters"] = previous_chapters

                    # 添加后3章的标题和摘要
                    next_chapters = []
                    end_idx = min(len(chapters), self.current_chapter_index + 4)
                    for i in range(self.current_chapter_index + 1, end_idx):
                        if i < len(chapters):
                            next_chapter = chapters[i]
                            next_chapters.append({
                                "title": next_chapter.get("title", ""),
                                "summary": next_chapter.get("summary", "")
                            })
                    context_info["next_chapters"] = next_chapters

        dialog = AIGenerateDialog(
            self,
            f"AI生成{field_name}",
            field_name,
            current_text,
            models=self._get_available_models(),
            default_model="GPT",
            outline_info=outline_info,
            context_info=context_info,
            prompt_manager=self.main_window.prompt_manager,
            # 新增：传递知识库管理器和可用知识库列表
            knowledge_base_manager=self.main_window.get_knowledge_base_manager(),
            available_knowledge_bases=self.main_window.get_available_knowledge_bases(),
            config_manager=self.main_window.config_manager # 哼，最后的最后，也不能忘了它！
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = dialog.get_result()
            if result:
                set_func(result)
                # 在使用AI生成结果后自动保存
                self._save_outline()
                # 不显示保存成功对话框，只显示状态栏消息
                self.main_window.status_bar_manager.show_message("已使用AI生成结果并保存")

    def _get_available_models(self):
        """获取可用的模型列表"""
        # 动态获取所有可用模型，包括自定义模型
        if hasattr(self, 'main_window') and self.main_window:
            return self.main_window.get_available_models()
        else:
            # fallback to hardcoded list if main_window is not available
            return ["GPT", "Claude", "Gemini", "自定义OpenAI", "ModelScope", "Ollama", "SiliconFlow"]

    def _on_content_changed(self):
        """内容发生变化时的处理"""
        # 检查是否启用了自动保存
        if self.auto_save_checkbox.isChecked():
            # 延迟自动保存：重启定时器
            self.auto_save_timer.stop()  # 停止之前的定时器
            self.auto_save_timer.start(self.auto_save_delay)  # 开始新的延迟
        else:
            # 标记有未保存的修改
            self.has_unsaved_changes = True
            # 更新保存按钮文本以提示用户
            if self.has_unsaved_changes:
                self.save_button.setText("保存修改 *")
            else:
                self.save_button.setText("保存修改")
    
    def _delayed_auto_save(self):
        """延迟自动保存（定时器触发）"""
        if (self.auto_save_checkbox.isChecked() and 
            not self._updating_from_external):
            print("DEBUG: Performing delayed auto save")
            self._save_current_edits_silent()
    
    def _on_editing_finished(self):
        """编辑完成时的处理（适用于QLineEdit）"""
        if (self.auto_save_checkbox.isChecked() and 
            not self._updating_from_external):
            # 停止定时器，立即保存
            self.auto_save_timer.stop()
            print("DEBUG: Performing immediate auto save (editing finished)")
            self._save_current_edits_silent()
    
    def _create_focus_out_handler(self, original_handler):
        """创建失去焦点事件处理器（适用于QTextEdit）"""
        def focus_out_event(event):
            # 先调用原始的焦点事件处理
            original_handler(event)
            # 然后处理自动保存
            if (self.auto_save_checkbox.isChecked() and 
                not self._updating_from_external):
                # 停止定时器，立即保存
                self.auto_save_timer.stop()
                print("DEBUG: Performing immediate auto save (focus out)")
                self._save_current_edits_silent()
        return focus_out_event
    
    def _save_current_edits_silent(self):
        """静默保存当前编辑的内容（不显示提示框）"""
        if not self.outline:
            return
        
        # 记住当前焦点控件
        focused_widget = self.focusWidget()
        
        print(f"DEBUG: _save_current_edits_silent called, volume_index={self.current_volume_index}, chapter_index={self.current_chapter_index}")
        
        # 保存当前编辑的卷和章节
        if self.current_volume_index >= 0:
            volumes = self.outline.get("volumes", [])
            if self.current_volume_index < len(volumes):
                volume = volumes[self.current_volume_index]
                volume["title"] = self.volume_title_edit.text()
                volume["description"] = self.volume_intro_edit.toPlainText()
                
                if self.current_chapter_index >= 0:
                    chapters = volume.get("chapters", [])
                    if self.current_chapter_index < len(chapters):
                        chapter = chapters[self.current_chapter_index]
                        chapter["title"] = self.chapter_title_edit.text()
                        chapter["summary"] = self.chapter_summary_edit.toPlainText()
        
        # 设置标记，防止 update_outline 被触发
        self._updating_from_external = True
        
        try:
            # 保存到主窗口 - 这里可能会触发其他组件的更新
            print("DEBUG: About to call main_window.set_outline")
            self.main_window.set_outline(self.outline)
            print("DEBUG: main_window.set_outline completed")
            
            self.has_unsaved_changes = False
            self.save_button.setText("保存修改")
            
            # 更新原始内容记录
            self._update_original_content()
            
        finally:
            # 清除标记
            self._updating_from_external = False
            
            # 尝试恢复焦点
            if (focused_widget and focused_widget in [self.volume_title_edit, self.volume_intro_edit, 
                                                     self.chapter_title_edit, self.chapter_summary_edit]):
                print(f"DEBUG: Restoring focus to {focused_widget}")
                focused_widget.setFocus()
    
    def _update_original_content(self):
        """更新原始内容记录"""
        self.original_volume_title = self.volume_title_edit.text() if hasattr(self, 'volume_title_edit') else ""
        self.original_volume_intro = self.volume_intro_edit.toPlainText() if hasattr(self, 'volume_intro_edit') else ""
        self.original_chapter_title = self.chapter_title_edit.text() if hasattr(self, 'chapter_title_edit') else ""
        self.original_chapter_summary = self.chapter_summary_edit.toPlainText() if hasattr(self, 'chapter_summary_edit') else ""
    
    def _has_unsaved_changes(self):
        """检查是否有未保存的修改"""
        if not hasattr(self, 'auto_save_checkbox') or self.auto_save_checkbox.isChecked():
            # 如果启用了自动保存，则认为没有未保存的修改
            return False
        
        # 检查当前内容是否与原始内容不同
        return (
            (hasattr(self, 'volume_title_edit') and self.volume_title_edit.text() != self.original_volume_title) or
            (hasattr(self, 'volume_intro_edit') and self.volume_intro_edit.toPlainText() != self.original_volume_intro) or
            (hasattr(self, 'chapter_title_edit') and self.chapter_title_edit.text() != self.original_chapter_title) or
            (hasattr(self, 'chapter_summary_edit') and self.chapter_summary_edit.toPlainText() != self.original_chapter_summary)
        )
    
    def _prompt_save_changes(self):
        """提示用户是否保存修改"""
        if not self._has_unsaved_changes():
            return True  # 没有修改，直接返回True
        
        reply = QMessageBox.question(
            self, 
            "保存修改",
            "当前内容已修改但未保存，是否要保存这些修改？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 用户选择保存
            self._save_current_edits_silent()
            return True
        elif reply == QMessageBox.StandardButton.No:
            # 用户选择不保存
            return True
        else:
            # 用户选择取消
            return False

    def update_outline(self):
        """更新大纲（供外部调用）"""
        print("DEBUG: update_outline called from external")
        
        # 防止无限循环：如果当前正在外部更新，直接返回
        if self._updating_from_external:
            print("DEBUG: Already updating from external, skipping")
            return
            
        print(f"DEBUG: Current state before update - volume_index={self.current_volume_index}, chapter_index={self.current_chapter_index}")
        
        # 设置标记，防止循环更新
        self._updating_from_external = True
        
        try:
            # 记录当前选择状态
            old_volume_index = self.current_volume_index
            old_chapter_index = self.current_chapter_index
            
            self._load_outline()
            
            # 尝试恢复选择状态（不触发自动保存）
            if old_volume_index >= 0 and old_volume_index < self.volume_list.count():
                print(f"DEBUG: Restoring volume selection to {old_volume_index}")
                self.volume_list.blockSignals(True)
                self.volume_list.setCurrentRow(old_volume_index)
                self.volume_list.blockSignals(False)
                # 直接设置状态，不调用事件处理器
                self._restore_volume_state(old_volume_index)
                
                if old_chapter_index >= 0 and old_chapter_index < self.chapter_list.count():
                    print(f"DEBUG: Restoring chapter selection to {old_chapter_index}")
                    self.chapter_list.blockSignals(True)
                    self.chapter_list.setCurrentRow(old_chapter_index)
                    self.chapter_list.blockSignals(False)
                    # 直接设置状态，不调用事件处理器
                    self._restore_chapter_state(old_chapter_index)
        finally:
            # 确保清除标记
            self._updating_from_external = False
    
    def _restore_volume_state(self, volume_index):
        """恢复卷状态（不触发保存）"""
        self.current_volume_index = volume_index
        self.current_chapter_index = -1

        # 清空章节列表
        self.chapter_list.clear()

        # 禁用章节编辑区域
        self.chapter_edit_group.setEnabled(False)

        if volume_index < 0:
            # 禁用卷编辑区域
            self.volume_edit_group.setEnabled(False)
            self.add_chapter_button.setEnabled(False)
            return

        # 启用卷编辑区域和添加章节按钮
        self.volume_edit_group.setEnabled(True)
        self.add_chapter_button.setEnabled(True)

        # 加载卷信息
        volumes = self.outline.get("volumes", [])
        if volume_index < len(volumes):
            volume = volumes[volume_index]
            self.volume_title_edit.setText(volume.get("title", f"第{volume_index+1}卷"))
            self.volume_intro_edit.setPlainText(volume.get("description", ""))

            # 加载章节列表
            chapters = volume.get("chapters", [])
            for i, chapter in enumerate(chapters):
                title = chapter.get("title", f"第{i+1}章")
                self.chapter_list.addItem(title)
        
        # 更新原始内容记录
        self._update_original_content()
    
    def _restore_chapter_state(self, chapter_index):
        """恢复章节状态（不触发保存）"""
        self.current_chapter_index = chapter_index

        if chapter_index < 0:
            # 禁用章节编辑区域
            self.chapter_edit_group.setEnabled(False)
            return

        # 启用章节编辑区域
        self.chapter_edit_group.setEnabled(True)

        # 加载章节信息
        volumes = self.outline.get("volumes", [])
        if self.current_volume_index < len(volumes):
            volume = volumes[self.current_volume_index]
            chapters = volume.get("chapters", [])
            if chapter_index < len(chapters):
                chapter = chapters[chapter_index]
                self.chapter_title_edit.setText(chapter.get("title", f"第{chapter_index+1}章"))
                self.chapter_summary_edit.setPlainText(chapter.get("summary", ""))
        
        # 更新原始内容记录
        self._update_original_content()
