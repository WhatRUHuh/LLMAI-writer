#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QComboBox, QGroupBox, QFormLayout,
    QSpinBox, QDoubleSpinBox, QMessageBox, QSplitter, QFileDialog, QProgressBar,
    QDialog, QInputDialog, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot

from generators.outline_generator import OutlineGenerator
from utils.async_utils import GenerationThread, ProgressIndicator
from utils.prompt_manager import PromptManager
from ui.character_selector_dialog import CharacterSelectorDialog


class OutlineTab(QWidget):
    """大纲生成标签页"""

    def __init__(self, main_window):
        super().__init__()

        self.main_window = main_window
        self.outline_generator = None
        self.generation_thread = None
        self.progress_indicator = ProgressIndicator(self)
        self.selected_characters = []  # 初始化选中的角色列表

        # 获取提示词管理器
        self.prompt_manager = self.main_window.prompt_manager

        # 获取配置管理器
        self.config_manager = self.main_window.config_manager

        # 初始化UI
        self._init_ui()

        # 加载保存的输入值
        self._load_saved_inputs()

    def _init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 创建左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 创建模型选择组
        model_group = QGroupBox("模型选择")
        model_layout = QFormLayout()

        self.model_combo = QComboBox()
        # 只添加标准模型，不显示具体的自定义模型
        self.model_combo.addItems(["GPT", "Claude", "Gemini", "自定义OpenAI", "ModelScope", "Ollama", "SiliconFlow"]) # 直接添加到硬编码列表
        # 添加模型选择变更事件
        self.model_combo.currentIndexChanged.connect(lambda: self._save_input_value("selected_model", self.model_combo.currentText()))

        model_layout.addRow("AI模型:", self.model_combo)

        # 温度设置已移除

        # 添加提示词模板选择
        template_layout = QHBoxLayout()

        self.template_combo = QComboBox()
        self.template_combo.addItem("选择提示词模板")

        # 加载大纲生成模板
        outline_templates = self.prompt_manager.get_templates_by_category("outline")
        for template in outline_templates:
            self.template_combo.addItem(template.name)

        self.template_combo.currentIndexChanged.connect(self._on_template_selected)
        # 添加模板选择变更事件，保存选择的模板
        self.template_combo.currentIndexChanged.connect(lambda: self._save_input_value("selected_template", self.template_combo.currentText()))
        template_layout.addWidget(self.template_combo)

        # 添加新建、编辑和保存模板按钮
        self.new_template_button = QPushButton("新建")
        self.new_template_button.clicked.connect(self._create_new_template)
        template_layout.addWidget(self.new_template_button)

        self.edit_template_button = QPushButton("编辑")
        self.edit_template_button.setEnabled(False)
        self.edit_template_button.clicked.connect(self._edit_template)
        template_layout.addWidget(self.edit_template_button)

        self.delete_template_button = QPushButton("删除")
        self.delete_template_button.clicked.connect(self._delete_template)
        self.delete_template_button.setEnabled(False)  # 初始禁用
        template_layout.addWidget(self.delete_template_button)

        model_layout.addRow("提示词模板:", template_layout)

        model_group.setLayout(model_layout)
        left_layout.addWidget(model_group)

        # 创建基本信息组
        info_group = QGroupBox("基本信息")
        info_layout = QFormLayout()

        # 添加小说标题输入框
        self.title_edit = QLineEdit()
        self.title_edit.textChanged.connect(lambda: self._save_input_value("title", self.title_edit.text()))
        info_layout.addRow("小说标题:", self.title_edit)

        # 添加小说类型输入框
        self.genre_edit = QLineEdit()
        self.genre_edit.textChanged.connect(lambda: self._save_input_value("genre", self.genre_edit.text()))
        info_layout.addRow("小说类型:", self.genre_edit)

        # 添加小说主题输入框 - 使用文本编辑框并添加滚动条
        self.theme_edit = QTextEdit()
        self.theme_edit.setMinimumHeight(60)  # 设置最小高度
        self.theme_edit.setMaximumHeight(100)  # 设置最大高度
        self.theme_edit.textChanged.connect(lambda: self._save_input_value("theme", self.theme_edit.toPlainText()))
        info_layout.addRow("小说主题:", self.theme_edit)

        # 添加小说风格输入框 - 使用文本编辑框并添加滚动条
        self.style_edit = QTextEdit()
        self.style_edit.setMinimumHeight(60)  # 设置最小高度
        self.style_edit.setMaximumHeight(100)  # 设置最大高度
        self.style_edit.textChanged.connect(lambda: self._save_input_value("style", self.style_edit.toPlainText()))
        info_layout.addRow("小说风格:", self.style_edit)

        # 添加小说简介输入框 - 使用文本编辑框并添加滚动条
        self.synopsis_edit = QTextEdit()
        self.synopsis_edit.setMinimumHeight(80)  # 设置最小高度
        self.synopsis_edit.setMaximumHeight(120)  # 设置最大高度
        self.synopsis_edit.textChanged.connect(lambda: self._save_input_value("synopsis", self.synopsis_edit.toPlainText()))
        info_layout.addRow("小说简介:", self.synopsis_edit)

        # 添加卷数设置
        self.volume_count_spin = QSpinBox()
        self.volume_count_spin.setRange(1, 999)
        self.volume_count_spin.setValue(3)
        self.volume_count_spin.setSuffix(" 卷")
        self.volume_count_spin.valueChanged.connect(lambda: self._save_input_value("volume_count", self.volume_count_spin.value()))
        info_layout.addRow("卷数:", self.volume_count_spin)

        # 添加每卷章节数设置
        self.chapters_per_volume_spin = QSpinBox()
        self.chapters_per_volume_spin.setRange(1, 999)
        self.chapters_per_volume_spin.setValue(10)
        self.chapters_per_volume_spin.setSuffix(" 章/卷")
        self.chapters_per_volume_spin.valueChanged.connect(lambda: self._save_input_value("chapters_per_volume", self.chapters_per_volume_spin.value()))
        info_layout.addRow("每卷章节数:", self.chapters_per_volume_spin)

        # 添加每章字数设置
        self.words_per_chapter_spin = QSpinBox()
        self.words_per_chapter_spin.setRange(100, 100000)
        self.words_per_chapter_spin.setValue(3000)
        self.words_per_chapter_spin.setSingleStep(500)
        self.words_per_chapter_spin.setSuffix(" 字/章")
        self.words_per_chapter_spin.valueChanged.connect(lambda: self._save_input_value("words_per_chapter", self.words_per_chapter_spin.value()))
        info_layout.addRow("每章字数:", self.words_per_chapter_spin)

        # 创建角色设置组
        character_group = QGroupBox("角色设置")
        character_group_layout = QVBoxLayout()

        # 创建滚动区域
        character_scroll = QScrollArea()
        character_scroll.setWidgetResizable(True)
        character_scroll.setFrameShape(QScrollArea.Shape.NoFrame)  # 移除边框

        # 创建内容widget
        character_content = QWidget()
        character_layout = QFormLayout(character_content)
        character_layout.setContentsMargins(0, 0, 0, 0)  # 减少边距

        # 添加新生成角色数量设置
        self.new_character_count_spin = QSpinBox()
        self.new_character_count_spin.setRange(0, 100)
        self.new_character_count_spin.setValue(5)
        self.new_character_count_spin.setSuffix(" 个")
        self.new_character_count_spin.valueChanged.connect(lambda: self._save_input_value("new_character_count", self.new_character_count_spin.value()))
        character_layout.addRow("新生成角色数量:", self.new_character_count_spin)

        # 添加选择当前范围大纲出现角色的按钮
        self.selected_characters = []  # 存储选中的角色
        character_select_layout = QHBoxLayout()
        self.character_select_button = QPushButton("选择角色")
        self.character_select_button.clicked.connect(self._select_characters)
        character_select_layout.addWidget(self.character_select_button)

        self.character_count_label = QLabel("已选择: 0 个角色")
        character_select_layout.addWidget(self.character_count_label)

        character_layout.addRow("选择出场角色:", character_select_layout)

        # 设置滚动区域的内容
        character_scroll.setWidget(character_content)

        # 添加滚动区域到角色设置组
        character_group_layout.addWidget(character_scroll)
        character_group.setLayout(character_group_layout)

        # 设置最小高度，确保至少显示两个选项
        character_group.setMinimumHeight(100)

        info_layout.addRow(character_group)

        info_group.setLayout(info_layout)
        left_layout.addWidget(info_group)

        # 创建操作按钮组
        button_group = QGroupBox("操作")
        button_layout = QVBoxLayout()

        self.generate_button = QPushButton("生成大纲")
        self.generate_button.setProperty("primary", True)  # 设置为主要按钮
        self.generate_button.clicked.connect(self.generate_outline)
        button_layout.addWidget(self.generate_button)

        # 已移除读取大纲和保存大纲按钮
        self.save_button = QPushButton("清空输出")
        self.save_button.clicked.connect(lambda: self.output_edit.clear())
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)

        button_group.setLayout(button_layout)
        left_layout.addWidget(button_group)

        # 添加弹性空间
        left_layout.addStretch()

        # 创建右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # 创建生成范围控制组
        range_group = QGroupBox("生成范围")
        range_layout = QHBoxLayout()

        # 起始卷号
        start_volume_layout = QHBoxLayout()
        start_volume_layout.addWidget(QLabel("起始卷:"))
        self.start_volume_spin = QSpinBox()
        self.start_volume_spin.setRange(1, 999)
        self.start_volume_spin.setValue(1)
        self.start_volume_spin.valueChanged.connect(lambda: self._save_input_value("start_volume", self.start_volume_spin.value()))
        start_volume_layout.addWidget(self.start_volume_spin)
        range_layout.addLayout(start_volume_layout)

        # 起始章节
        start_chapter_layout = QHBoxLayout()
        start_chapter_layout.addWidget(QLabel("起始章:"))
        self.start_chapter_spin = QSpinBox()
        self.start_chapter_spin.setRange(1, 999)
        self.start_chapter_spin.setValue(1)
        self.start_chapter_spin.valueChanged.connect(lambda: self._save_input_value("start_chapter", self.start_chapter_spin.value()))
        start_chapter_layout.addWidget(self.start_chapter_spin)
        range_layout.addLayout(start_chapter_layout)

        # 结束卷号
        end_volume_layout = QHBoxLayout()
        end_volume_layout.addWidget(QLabel("结束卷:"))
        self.end_volume_spin = QSpinBox()
        self.end_volume_spin.setRange(1, 999)
        self.end_volume_spin.setValue(1)
        self.end_volume_spin.valueChanged.connect(lambda: self._save_input_value("end_volume", self.end_volume_spin.value()))
        end_volume_layout.addWidget(self.end_volume_spin)
        range_layout.addLayout(end_volume_layout)

        # 结束章节
        end_chapter_layout = QHBoxLayout()
        end_chapter_layout.addWidget(QLabel("结束章:"))
        self.end_chapter_spin = QSpinBox()
        self.end_chapter_spin.setRange(1, 999)
        self.end_chapter_spin.setValue(10)
        self.end_chapter_spin.valueChanged.connect(lambda: self._save_input_value("end_chapter", self.end_chapter_spin.value()))
        end_chapter_layout.addWidget(self.end_chapter_spin)
        range_layout.addLayout(end_chapter_layout)

        range_group.setLayout(range_layout)
        right_layout.addWidget(range_group)

        # 创建输出区域
        output_group = QGroupBox("生成结果")
        output_layout = QVBoxLayout()

        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        output_layout.addWidget(self.output_edit)

        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        self.progress_bar.setVisible(False)
        output_layout.addWidget(self.progress_bar)

        output_group.setLayout(output_layout)
        right_layout.addWidget(output_group)

        # 添加面板到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        # 设置分割器比例
        splitter.setSizes([300, 700])

    def _on_template_selected(self, index):
        """模板选择事件处理"""
        if index <= 0:  # 第一项是提示文本
            self.edit_template_button.setEnabled(False)
            self.delete_template_button.setEnabled(False)
            return

        template_name = self.template_combo.currentText()
        template = self.prompt_manager.get_template(template_name)

        if template:
            # 启用编辑和删除按钮
            self.edit_template_button.setEnabled(True)
            self.delete_template_button.setEnabled(True)

            # 显示模板信息
            QMessageBox.information(
                self,
                f"模板: {template_name}",
                f"描述: {template.description}\n\n分类: {template.category}"
            )

    def _get_model_type(self):
        """获取选择的模型类型"""
        model_text = self.model_combo.currentText().lower()
        if model_text == "gpt":
            return "gpt"
        elif model_text == "claude":
            return "claude"
        elif model_text == "gemini":
            return "gemini"
        elif model_text == "自定义openai":
            return "custom_openai"
        elif model_text == "modelscope":
            return "modelscope"
        elif model_text == "ollama":
            return "ollama"
        elif model_text == "siliconflow": # 添加 SiliconFlow 处理
            return "siliconflow"
        else:
            return "gpt"  # 默认使用GPT # 保持原来的默认逻辑

    def _update_buttons(self, has_outline):
        """更新按钮状态"""
        # 现在只更新清空输出按钮
        self.save_button.setEnabled(has_outline)

    def _stream_callback(self, chunk):
        """流式生成回调函数"""
        self.output_edit.insertPlainText(chunk)
        # 滚动到底部
        scrollbar = self.output_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @pyqtSlot(str)
    def _on_progress(self, chunk):
        """处理进度信号"""
        self._stream_callback(chunk)

    @pyqtSlot(object)
    def _on_finished(self, result):
        """处理完成信号"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)

        # 更新UI
        self.generate_button.setEnabled(True)
        self.save_button.setEnabled(True)

        # 在大纲中添加原始输入信息
        result["input_info"] = {
            "title": self.title_edit.text().strip(),
            "genre": self.genre_edit.text().strip(),
            "theme": self.theme_edit.toPlainText().strip(),
            "style": self.style_edit.toPlainText().strip(),
            "synopsis": self.synopsis_edit.toPlainText().strip()
        }

        # 获取生成范围
        start_volume = self.start_volume_spin.value()
        start_chapter = self.start_chapter_spin.value()
        end_volume = self.end_volume_spin.value()
        end_chapter = self.end_chapter_spin.value()

        # 如果指定了生成范围，则将生成的内容合并到已有大纲中
        if start_volume and end_volume:
            # 获取已有大纲
            existing_outline = self.main_window.get_outline()
            if existing_outline:
                # 将生成的卷和章节合并到已有大纲中
                self._merge_volumes(existing_outline, result, start_volume, start_chapter, end_volume, end_chapter)
                # 使用合并后的大纲
                result = existing_outline

        # 设置大纲
        self.main_window.set_outline(result)

        # 更新按钮状态
        self._update_buttons(True)

        # 更新状态栏
        self.main_window.status_bar_manager.show_message("大纲生成完成")

        # 显示完成消息
        QMessageBox.information(self, "生成完成", "大纲生成完成！")

    @pyqtSlot(str)
    def _on_error(self, error_message):
        """处理错误信号"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)

        # 更新UI
        self.generate_button.setEnabled(True)

        # 更新状态栏
        self.main_window.status_bar_manager.show_message("大纲生成失败")

        # 显示错误消息
        QMessageBox.warning(self, "生成失败", f"生成大纲时出错: {error_message}")

    def _merge_volumes(self, existing_outline, new_outline, start_volume, start_chapter, end_volume, end_chapter):
        """将新生成的卷和章节合并到已有大纲中

        Args:
            existing_outline: 已有的大纲
            new_outline: 新生成的大纲
            start_volume: 起始卷号（从1开始）
            start_chapter: 起始章节号（从1开始）
            end_volume: 结束卷号（从1开始）
            end_chapter: 结束章节号（从1开始）
        """
        # 确保已有大纲中有volumes字段
        if 'volumes' not in existing_outline:
            existing_outline['volumes'] = []

        # 如果新大纲中没有volumes字段，直接返回
        if 'volumes' not in new_outline or not new_outline['volumes']:
            return

        # 遍历新生成的卷
        for new_volume in new_outline['volumes']:
            # 提取卷号（从标题中提取数字）
            volume_title = new_volume.get('title', '')
            volume_number = 0

            # 尝试从标题中提取卷号
            import re
            match = re.search(r'第(\d+)卷', volume_title)
            if match:
                volume_number = int(match.group(1))

            # 如果卷号在指定范围内
            if start_volume <= volume_number <= end_volume:
                # 检查已有大纲中是否已有该卷
                existing_volume_index = None
                for i, vol in enumerate(existing_outline['volumes']):
                    vol_title = vol.get('title', '')
                    match = re.search(r'第(\d+)卷', vol_title)
                    if match and int(match.group(1)) == volume_number:
                        existing_volume_index = i
                        break

                # 如果已有该卷，替换或合并章节
                if existing_volume_index is not None:
                    # 保留卷标题和简介
                    existing_outline['volumes'][existing_volume_index]['title'] = new_volume.get('title', existing_outline['volumes'][existing_volume_index]['title'])
                    existing_outline['volumes'][existing_volume_index]['description'] = new_volume.get('description', existing_outline['volumes'][existing_volume_index]['description'])

                    # 确保章节列表存在
                    if 'chapters' not in existing_outline['volumes'][existing_volume_index]:
                        existing_outline['volumes'][existing_volume_index]['chapters'] = []

                    # 如果有新章节
                    if 'chapters' in new_volume and new_volume['chapters']:
                        # 遍历新章节
                        for new_chapter in new_volume['chapters']:
                            # 提取章节号
                            chapter_title = new_chapter.get('title', '')
                            chapter_number = 0

                            match = re.search(r'第(\d+)章', chapter_title)
                            if match:
                                chapter_number = int(match.group(1))

                            # 判断章节是否在范围内
                            in_range = True
                            if volume_number == start_volume and start_chapter and chapter_number < start_chapter:
                                in_range = False
                            if volume_number == end_volume and end_chapter and chapter_number > end_chapter:
                                in_range = False

                            if in_range:
                                # 检查是否已有该章节
                                existing_chapter_index = None
                                for j, chap in enumerate(existing_outline['volumes'][existing_volume_index]['chapters']):
                                    chap_title = chap.get('title', '')
                                    match = re.search(r'第(\d+)章', chap_title)
                                    if match and int(match.group(1)) == chapter_number:
                                        existing_chapter_index = j
                                        break

                                # 如果已有该章节，替换
                                if existing_chapter_index is not None:
                                    existing_outline['volumes'][existing_volume_index]['chapters'][existing_chapter_index] = new_chapter
                                else:
                                    # 如果没有，添加到适当位置
                                    # 找到插入位置
                                    insert_index = 0
                                    for j, chap in enumerate(existing_outline['volumes'][existing_volume_index]['chapters']):
                                        chap_title = chap.get('title', '')
                                        match = re.search(r'第(\d+)章', chap_title)
                                        if match and int(match.group(1)) < chapter_number:
                                            insert_index = j + 1

                                    # 插入新章节
                                    existing_outline['volumes'][existing_volume_index]['chapters'].insert(insert_index, new_chapter)
                else:
                    # 如果没有该卷，添加到适当位置
                    # 找到插入位置
                    insert_index = 0
                    for i, vol in enumerate(existing_outline['volumes']):
                        vol_title = vol.get('title', '')
                        match = re.search(r'第(\d+)卷', vol_title)
                        if match and int(match.group(1)) < volume_number:
                            insert_index = i + 1

                    # 插入新卷
                    existing_outline['volumes'].insert(insert_index, new_volume)

        # 最终排序卷和章节，确保顺序正确
        if 'volumes' in existing_outline and existing_outline['volumes']:
            # 对卷进行排序
            def get_volume_number(volume):
                title = volume.get('title', '')
                match = re.search(r'第(\d+)卷', title)
                if match:
                    return int(match.group(1))
                return 0

            existing_outline['volumes'].sort(key=get_volume_number)

            # 对每个卷的章节进行排序
            for volume in existing_outline['volumes']:
                if 'chapters' in volume and volume['chapters']:
                    def get_chapter_number(chapter):
                        title = chapter.get('title', '')
                        match = re.search(r'第(\d+)章', title)
                        if match:
                            return int(match.group(1))
                        return 0

                    volume['chapters'].sort(key=get_chapter_number)

        # 更新其他字段（如果有新内容）
        if 'title' in new_outline and new_outline['title'] and not existing_outline.get('title'):
            existing_outline['title'] = new_outline['title']
        if 'theme' in new_outline and new_outline['theme'] and not existing_outline.get('theme'):
            existing_outline['theme'] = new_outline['theme']
        if 'synopsis' in new_outline and new_outline['synopsis'] and not existing_outline.get('synopsis'):
            existing_outline['synopsis'] = new_outline['synopsis']
        if 'worldbuilding' in new_outline and new_outline['worldbuilding'] and not existing_outline.get('worldbuilding'):
            existing_outline['worldbuilding'] = new_outline['worldbuilding']

        # 合并角色数据 - 只添加新生成的角色，不替换已有角色
        if 'characters' in new_outline and new_outline['characters']:
            if not existing_outline.get('characters'):
                # 如果已有大纲中没有角色数据，直接使用新生成的角色数据
                existing_outline['characters'] = new_outline['characters']
            else:
                # 如果已有大纲中已有角色数据，合并新生成的角色数据
                existing_characters = existing_outline.get('characters', [])
                new_characters = new_outline.get('characters', [])

                # 获取已有角色的名称列表，用于检查重复
                existing_names = [char.get('name', '') for char in existing_characters]

                # 添加不重复的新角色
                for new_char in new_characters:
                    new_name = new_char.get('name', '')
                    if new_name and new_name not in existing_names:
                        existing_characters.append(new_char)
                        existing_names.append(new_name)

                # 更新角色数据
                existing_outline['characters'] = existing_characters

    def _select_characters(self):
        """选择章节出场角色"""
        # 获取当前小说的所有角色
        outline = self.main_window.get_outline()
        if not outline or "characters" not in outline or not outline["characters"]:
            QMessageBox.warning(self, "提示", "当前小说没有角色数据，请先在人物编辑标签页添加角色。")
            return

        # 获取所有角色
        all_characters = outline["characters"]

        # 创建角色选择对话框
        dialog = CharacterSelectorDialog(self, all_characters, self.selected_characters)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 获取选中的角色
            self.selected_characters = dialog.get_selected_characters()
            # 更新已选择角色数量标签
            self.character_count_label.setText(f"已选择: {len(self.selected_characters)} 个角色")

    def generate_outline(self):
        """生成大纲"""
        # 获取输入
        title = self.title_edit.text().strip()
        genre = self.genre_edit.text().strip()
        theme = self.theme_edit.toPlainText().strip()  # 使用toPlainText()获取QTextEdit的内容
        style = self.style_edit.toPlainText().strip()  # 使用toPlainText()获取QTextEdit的内容
        synopsis = self.synopsis_edit.toPlainText().strip()  # 使用toPlainText()获取QTextEdit的内容
        volume_count = self.volume_count_spin.value()
        chapters_per_volume = self.chapters_per_volume_spin.value()
        words_per_chapter = self.words_per_chapter_spin.value()

        # 获取新的角色设置
        new_character_count = self.new_character_count_spin.value()
        selected_characters = self.selected_characters

        if not theme:
            QMessageBox.warning(self, "输入错误", "请输入小说主题")
            return

        # 获取模型
        model_type = self._get_model_type()
        try:
            model = self.main_window.get_model(model_type)
        except ValueError as e:
            QMessageBox.warning(self, "模型错误", str(e))
            return

        # 温度设置已移除

        # 创建大纲生成器
        self.outline_generator = OutlineGenerator(model, self.main_window.config_manager)

        # 清空输出
        self.output_edit.clear()

        # 禁用生成按钮
        self.generate_button.setEnabled(False)

        # 显示进度条
        self.progress_bar.setVisible(True)

        # 更新状态栏
        self.main_window.status_bar_manager.show_message("正在生成大纲...")

        # 检查是否使用模板
        template_name = self.template_combo.currentText()
        if template_name and template_name != "选择提示词模板":
            template = self.prompt_manager.get_template(template_name)
            if template:
                # 记录使用模板
                self.main_window.status_bar_manager.show_message(f"正在使用模板 '{template_name}' 生成大纲...")

        # 获取生成范围
        start_volume = self.start_volume_spin.value()
        start_chapter = self.start_chapter_spin.value()
        end_volume = self.end_volume_spin.value()
        end_chapter = self.end_chapter_spin.value()

        # 获取已有大纲（如果有）
        existing_outline = self.main_window.get_outline()

        # 创建并启动生成线程
        self.generation_thread = GenerationThread(
            self.outline_generator.generate_outline,
            (title, genre, theme, style, synopsis, volume_count, chapters_per_volume, words_per_chapter,
             new_character_count, selected_characters, start_volume, start_chapter, end_volume, end_chapter, existing_outline),
            {"callback": self._stream_callback}
        )

        # 连接信号
        self.generation_thread.progress_signal.connect(self._on_progress)
        self.generation_thread.finished_signal.connect(self._on_finished)
        self.generation_thread.error_signal.connect(self._on_error)

        # 启动线程
        self.generation_thread.start()

        # 记录提示词历史
        self.prompt_manager.add_history(
            prompt=f"大纲生成: {title} - {theme}",
            model=model_type,
            metadata={
                "title": title,
                "genre": genre,
                "theme": theme,
                "volume_count": volume_count,
                "chapters_per_volume": chapters_per_volume
            }
        )

    # 删除了optimize_outline方法

    # 删除了expand_chapters方法

    # 已移除save_outline方法
    # 这个功能现在由主窗口的工具栏按钮提供

    # 已移除load_outline方法
    # 这个功能现在由主窗口的工具栏按钮提供

    def _create_new_template(self):
        """创建新模板"""
        # 创建编辑对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("创建新模板")
        dialog.resize(600, 500)

        layout = QVBoxLayout(dialog)

        # 模板名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("模板名称:"))
        name_edit = QLineEdit(f"自定义大纲模板_{len(self.prompt_manager.get_templates_by_category('outline')) + 1}")
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)

        # 模板描述
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("模板描述:"))
        desc_edit = QLineEdit("自定义大纲生成模板")
        desc_layout.addWidget(desc_edit)
        layout.addLayout(desc_layout)

        # 模板分类
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("模板分类:"))
        category_edit = QLineEdit("outline")
        category_edit.setEnabled(False)  # 固定为outline分类
        category_layout.addWidget(category_edit)
        layout.addLayout(category_layout)

        # 模板内容
        content_label = QLabel("模板内容:")
        layout.addWidget(content_label)

        content_edit = QTextEdit()
        default_content = """请为我创建一部小说的详细大纲，具体要求如下：

小说标题：[用户输入的标题]
小说类型：[用户输入的类型]
主题：[用户输入的主题]
风格：[用户输入的风格]
简介：[用户输入的简介]

卷数：[用户设置的卷数] 卷
每卷章节数：[用户设置的章节数] 章
每章字数：[用户设置的字数] 字

人物设置：
新生成角色数量：[用户设置的新生成角色数量] 个
已选择出场角色：[用户选择的角色数量] 个

生成范围：从第[起始卷]卷第[起始章]章 到 第[结束卷]卷第[结束章]章

请生成以下内容：
1. 小说标题
2. 核心主题
3. 主要人物（包括姓名、身份、性格特点和背景故事）
4. 故事梗概
5. 分卷结构（每卷包含标题、简介和具体章节）
6. 世界观设定

特别要求：
1. 卷标题必须包含卷号，如"第一卷：卷标题"
2. 章节标题必须包含章节号，如"第一章：章节标题"
3. 只生成指定范围内的卷和章节，但保持与已有大纲的一致性
4. 在生成的内容中充分利用已选择的出场角色

请确保大纲结构完整、逻辑合理，并以JSON格式返回。"""
        content_edit.setPlainText(default_content)
        layout.addWidget(content_edit)

        # 按钮
        button_layout = QHBoxLayout()

        save_button = QPushButton("保存")
        save_button.clicked.connect(dialog.accept)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        # 显示对话框
        if dialog.exec() == QDialog.DialogCode.Accepted:
            template_name = name_edit.text()
            template_content = content_edit.toPlainText()
            template_desc = desc_edit.text()

            # 添加模板
            success = self.prompt_manager.add_template(
                template_name,
                template_content,
                "outline",
                template_desc
            )

            if success:
                # 添加到下拉框
                self.template_combo.addItem(template_name)
                self.template_combo.setCurrentText(template_name)

                QMessageBox.information(self, "保存成功", f"模板 '{template_name}' 已创建")
            else:
                QMessageBox.warning(self, "保存失败", f"模板 '{template_name}' 已存在或保存失败")

    def _edit_template(self):
        """编辑选中的模板"""
        if self.template_combo.currentIndex() <= 0:
            return

        template_name = self.template_combo.currentText()
        template = self.prompt_manager.get_template(template_name)

        if not template:
            return

        # 创建编辑对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(f"编辑模板: {template_name}")
        dialog.resize(600, 500)

        layout = QVBoxLayout(dialog)

        # 模板名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("模板名称:"))
        name_edit = QLineEdit(template.name)
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)

        # 模板描述
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("模板描述:"))
        desc_edit = QLineEdit(template.description)
        desc_layout.addWidget(desc_edit)
        layout.addLayout(desc_layout)

        # 模板分类
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("模板分类:"))
        category_edit = QLineEdit(template.category)
        category_layout.addWidget(category_edit)
        layout.addLayout(category_layout)

        # 模板内容
        content_label = QLabel("模板内容:")
        layout.addWidget(content_label)

        content_edit = QTextEdit()
        content_edit.setPlainText(template.content)
        layout.addWidget(content_edit)

        # 按钮
        button_layout = QHBoxLayout()

        save_button = QPushButton("保存")
        save_button.clicked.connect(dialog.accept)
        button_layout.addWidget(save_button)

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        # 显示对话框
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 检查名称是否变更
            new_name = name_edit.text()
            old_name = template.name

            # 更新模板内容
            success = self.prompt_manager.update_template(
                old_name,
                content_edit.toPlainText(),
                category_edit.text(),
                desc_edit.text()
            )

            # 如果名称变更，需要删除旧模板并创建新模板
            if success and new_name != old_name:
                # 保存模板内容
                content = content_edit.toPlainText()
                category = category_edit.text()
                description = desc_edit.text()

                # 删除旧模板
                self.prompt_manager.delete_template(old_name)

                # 创建新模板
                self.prompt_manager.add_template(
                    new_name,
                    content,
                    category,
                    description
                )

                # 更新下拉框
                current_index = self.template_combo.currentIndex()
                self.template_combo.setItemText(current_index, new_name)

                QMessageBox.information(self, "保存成功", f"模板 '{new_name}' 已更新")
            elif success:
                QMessageBox.information(self, "保存成功", f"模板 '{old_name}' 已更新")

    def _save_as_template(self):
        """保存当前设置为新模板"""
        # 获取当前设置
        title = self.title_edit.text().strip()
        genre = self.genre_edit.text().strip()
        theme = self.theme_edit.toPlainText().strip()
        style = self.style_edit.toPlainText().strip()
        synopsis = self.synopsis_edit.toPlainText().strip()
        volume_count = self.volume_count_spin.value()
        chapters_per_volume = self.chapters_per_volume_spin.value()
        words_per_chapter = self.words_per_chapter_spin.value()

        # 获取新的角色设置
        new_character_count = self.new_character_count_spin.value()
        selected_characters_count = len(self.selected_characters)

        # 获取生成范围
        start_volume = self.start_volume_spin.value()
        start_chapter = self.start_chapter_spin.value()
        end_volume = self.end_volume_spin.value()
        end_chapter = self.end_chapter_spin.value()

        # 创建模板内容
        template_content = f"""请为我创建一部小说的详细大纲，具体要求如下：

小说标题：{title if title else '[用户输入的标题]'}
小说类型：{genre if genre else '[用户输入的类型]'}
主题：{theme if theme else '[用户输入的主题]'}
风格：{style if style else '[用户输入的风格]'}
简介：{synopsis if synopsis else '[用户输入的简介]'}

卷数：{volume_count} 卷
每卷章节数：{chapters_per_volume} 章
每章字数：{words_per_chapter} 字

人物设置：
新生成角色数量：{new_character_count} 个
已选择出场角色：{selected_characters_count} 个

生成范围：从第{start_volume}卷第{start_chapter}章 到 第{end_volume}卷第{end_chapter}章

请生成以下内容：
1. 小说标题
2. 核心主题
3. 主要人物（包括姓名、身份、性格特点和背景故事）
4. 故事梗概
5. 分卷结构（每卷包含标题、简介和具体章节）
6. 世界观设定

特别要求：
1. 卷标题必须包含卷号，如"第一卷：卷标题"
2. 章节标题必须包含章节号，如"第一章：章节标题"
3. 只生成指定范围内的卷和章节，但保持与已有大纲的一致性
4. 在生成的内容中充分利用已选择的出场角色

请确保大纲结构完整、逻辑合理，并以JSON格式返回。"""

        # 获取模板名称
        template_name, ok = QInputDialog.getText(
            self, "保存模板", "请输入模板名称:",
            text=f"自定义大纲模板_{len(self.prompt_manager.get_templates_by_category('outline')) + 1}"
        )

        if ok and template_name:
            # 获取模板描述
            template_desc, ok = QInputDialog.getText(
                self, "模板描述", "请输入模板描述:",
                text=f"基于当前设置创建的大纲模板"
            )

            if ok:
                # 添加模板
                success = self.prompt_manager.add_template(
                    template_name,
                    template_content,
                    "outline",
                    template_desc
                )

                if success:
                    # 添加到下拉框
                    self.template_combo.addItem(template_name)
                    self.template_combo.setCurrentText(template_name)

                    QMessageBox.information(self, "保存成功", f"模板 '{template_name}' 已保存")
                else:
                    QMessageBox.warning(self, "保存失败", f"模板 '{template_name}' 已存在或保存失败")

    def _delete_template(self):
        """删除当前选中的模板"""
        if self.template_combo.currentIndex() <= 0:
            return

        template_name = self.template_combo.currentText()

        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除模板 '{template_name}' 吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 删除模板
            success = self.prompt_manager.delete_template(template_name)

            if success:
                # 从下拉框中移除
                current_index = self.template_combo.currentIndex()
                self.template_combo.removeItem(current_index)

                # 禁用编辑和删除按钮
                self.edit_template_button.setEnabled(False)
                self.delete_template_button.setEnabled(False)

                QMessageBox.information(self, "删除成功", f"模板 '{template_name}' 已删除")
            else:
                QMessageBox.warning(self, "删除失败", f"模板 '{template_name}' 删除失败")

    def _save_input_value(self, key, value):
        """保存输入值到配置

        Args:
            key: 配置键名
            value: 配置值
        """
        try:
            # 使用配置管理器的方法保存值
            self.config_manager.set_outline_input(key, value)
        except Exception as e:
            print(f"保存输入值时出错: {e}")

    def _load_saved_inputs(self):
        """从配置加载保存的输入值"""
        try:
            # 加载模型选择
            selected_model = self.config_manager.get_outline_input("selected_model")
            if selected_model:
                # 查找模型在下拉框中的索引
                index = self.model_combo.findText(selected_model)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)

            # 加载提示词模板选择
            selected_template = self.config_manager.get_outline_input("selected_template")
            if selected_template and selected_template != "选择提示词模板":
                # 查找模板在下拉框中的索引
                index = self.template_combo.findText(selected_template)
                if index >= 0:
                    self.template_combo.setCurrentIndex(index)

            # 加载文本输入框的值
            title = self.config_manager.get_outline_input("title")
            if title:
                self.title_edit.setText(title)

            genre = self.config_manager.get_outline_input("genre")
            if genre:
                self.genre_edit.setText(genre)

            theme = self.config_manager.get_outline_input("theme")
            if theme:
                self.theme_edit.setPlainText(theme)

            style = self.config_manager.get_outline_input("style")
            if style:
                self.style_edit.setPlainText(style)

            synopsis = self.config_manager.get_outline_input("synopsis")
            if synopsis:
                self.synopsis_edit.setPlainText(synopsis)

            # 加载数值输入框的值
            volume_count = self.config_manager.get_outline_input("volume_count")
            if volume_count:
                self.volume_count_spin.setValue(int(volume_count))

            chapters_per_volume = self.config_manager.get_outline_input("chapters_per_volume")
            if chapters_per_volume:
                self.chapters_per_volume_spin.setValue(int(chapters_per_volume))

            words_per_chapter = self.config_manager.get_outline_input("words_per_chapter")
            if words_per_chapter:
                self.words_per_chapter_spin.setValue(int(words_per_chapter))

            new_character_count = self.config_manager.get_outline_input("new_character_count")
            if new_character_count:
                self.new_character_count_spin.setValue(int(new_character_count))

            # 加载生成范围的值
            start_volume = self.config_manager.get_outline_input("start_volume")
            if start_volume:
                self.start_volume_spin.setValue(int(start_volume))

            start_chapter = self.config_manager.get_outline_input("start_chapter")
            if start_chapter:
                self.start_chapter_spin.setValue(int(start_chapter))

            end_volume = self.config_manager.get_outline_input("end_volume")
            if end_volume:
                self.end_volume_spin.setValue(int(end_volume))

            end_chapter = self.config_manager.get_outline_input("end_chapter")
            if end_chapter:
                self.end_chapter_spin.setValue(int(end_chapter))

        except Exception as e:
            print(f"加载保存的输入值时出错: {e}")
