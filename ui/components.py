#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI组件模块

提供通用的UI组件，用于减少重复代码和统一界面风格。
"""

import json
import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QComboBox, QGroupBox, QFormLayout,
    QMessageBox, QSplitter, QDialog, QListWidget, QListWidgetItem,
    QTabWidget, QInputDialog, QScrollArea, QProgressBar,
    QCheckBox, QSpinBox, QDoubleSpinBox, QFileDialog, QToolTip,
    QToolBar, QStatusBar, QMainWindow, QApplication, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QTimer, QPoint
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut, QFont, QColor, QPalette, QAction
from typing import List 
from utils.config_manager import ConfigManager 

from utils.async_utils import GenerationThread, ProgressIndicator, AsyncHelper
from ui.styles import get_style
from utils.knowledge_base_manager import KnowledgeBaseManager 


class AIGenerateDialog(QDialog):
    """
    AI生成对话框
 
    用于使用AI生成内容的通用对话框
    """
 
    def __init__(self, parent=None, title="AI生成", field_name="内容", current_text="",
                 models=None, default_model="GPT", outline_info=None, context_info=None, prompt_manager=None,
                 task_type="generate", selected_text=None, full_text=None, target_word_count=None,
                 knowledge_base_manager: KnowledgeBaseManager = None, # 新增知识库管理器
                 available_knowledge_bases: List[str] = None,
                 config_manager: ConfigManager = None): # 新增配置管理器，
        """
        初始化AI生成对话框

        Args:
            parent: 父窗口
            title: 对话框标题
            field_name: 字段名称 (例如 "章节内容", "章节摘要")
            current_text: 当前文本 (用于生成任务的上下文或基础)
            models: 可用的模型列表
            default_model: 默认选择的模型
            outline_info: 总大纲信息
            context_info: 上下文信息
            prompt_manager: 提示词管理器实例
            task_type: 任务类型 ('generate' 或 'polish')
            selected_text: 用户选定的文本 (用于润色任务)
            full_text: 完整的章节文本 (用于润色任务的上下文)
            target_word_count: 目标字数 (可选)
            knowledge_base_manager: 知识库管理器实例
            available_knowledge_bases: 可用的知识库名称列表
            config_manager: 配置管理器实例，哼，这个可是关键！
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 500)
        self.field_name = field_name
        self.current_text = current_text # 对于润色任务，这个可能为空
        self.result_text = ""
        self.generation_thread = None
        self.models = models or ["GPT", "Claude", "Gemini", "自定义OpenAI", "ModelScope", "Ollama", "SiliconFlow"] # 保持模型列表更新
        self.default_model = default_model # 这个 default_model 是传入的，优先级在已保存模型之后
        self.outline_info = outline_info or {}
        self.context_info = context_info or {}
        self.config_manager = config_manager # 保存配置管理器实例！
        # 保存新参数
        self.task_type = task_type
        self.selected_text = selected_text
        self.full_text = full_text
        self.target_word_count = target_word_count # 保存目标字数
        self.knowledge_base_manager = knowledge_base_manager
        self.available_knowledge_bases = available_knowledge_bases if available_knowledge_bases is not None else []
        self.kb_query_thread = None # 用于知识库查询的线程
        self.kb_result_buttons = [] # 用于存储知识库结果按钮

        # 获取提示词管理器
        if prompt_manager:
            self.prompt_manager = prompt_manager
        else:
            # 尝试从父窗口获取
            try:
                if hasattr(parent, 'prompt_manager'):
                    self.prompt_manager = parent.prompt_manager
                elif hasattr(parent, 'main_window') and hasattr(parent.main_window, 'prompt_manager'):
                    self.prompt_manager = parent.main_window.prompt_manager
                else:
                    self.prompt_manager = None
            except:
                self.prompt_manager = None

        # 初始化UI
        self._init_ui()

        # 添加快捷键
        self._setup_shortcuts()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 提示词部分
        prompt_group = QGroupBox("提示词")
        prompt_layout = QVBoxLayout()

        prompt_label = QLabel(f"请输入提示词，告诉AI如何生成新的{self.field_name}：")
        prompt_layout.addWidget(prompt_label)

        self.prompt_edit = QTextEdit()

        # 构建默认提示词 - 根据任务类型区分
        default_prompt = ""
        if self.task_type == "polish":
            # 构建润色任务的提示词
            default_prompt = f"""请根据以下上下文信息和要求，润色指定的文本段落。

**任务要求:**
1.  **重点润色**以下被 `[润色目标开始]` 和 `[润色目标结束]` 标记的文本段落。
2.  润色目标是使其语言更**生动、流畅、精炼**（或根据需要调整目标）。
3.  保持原文的核心意思和情节不变。
4.  确保润色后的文本与上下文**自然衔接**，风格保持一致。
5.  **只返回**润色后的目标文本段落本身，不要包含标记符或原文的其他部分。
"""
            # 移除润色任务的目标字数要求
            # if self.target_word_count: # 添加目标字数要求（可选）
            #     default_prompt += f"6. 目标字数：{self.target_word_count}字左右（仅供参考，优先保证润色质量）。\n"
            default_prompt += """
**小说信息:**
"""
            # 添加总大纲信息
            if self.outline_info: # 确保 outline_info 存在
                # 使用明确的4空格缩进重写此块
                if self.outline_info.get("title"):
                    default_prompt += f"- 小说标题：{self.outline_info.get('title')}\n"
                if self.outline_info.get("theme"):
                    default_prompt += f"- 中心思想：{self.outline_info.get('theme')}\n"
                if self.outline_info.get("synopsis"):
                    default_prompt += f"- 故事梗概：{self.outline_info.get('synopsis')}\n"
                if self.outline_info.get("worldbuilding"):
                    default_prompt += f"- 世界观设定：{self.outline_info.get('worldbuilding')}\n"
            # 确保此行与 if self.outline_info: 对齐
            default_prompt += "\n**章节上下文:**\n"
            # 添加章节上下文
            if self.context_info: # 确保 context_info 存在
                 if self.context_info.get("chapter_title"): default_prompt += f"- 当前章节：{self.context_info.get('chapter_title')}\n"
                 # 可以考虑添加前后章节摘要等 context_info 中的其他信息

            default_prompt += f"""
**完整章节内容 (包含需要润色的部分):**
---
{self.full_text if self.full_text else '(缺少完整章节内容)'}
---

**需要润色的文本段落:**
[润色目标开始]
{self.selected_text if self.selected_text else '(缺少选定文本)'}
[润色目标结束]

请开始润色，只输出润色后的目标段落："""

        else:
            # 保持原来的生成任务提示词逻辑
            default_prompt = f"请根据以下内容，生成一个新的{self.field_name}：\n\n"
            # 添加总大纲信息（如果有）
            if self.outline_info:
                if self.outline_info.get("title"): # 确保 outline_info 存在，并使用明确的4空格缩进重写此块
                    default_prompt += f"小说标题：{self.outline_info.get('title')}\n"
                if self.outline_info.get("theme"): # 确保 outline_info 存在，并使用明确的4空格缩进重写此块
                    default_prompt += f"中心思想：{self.outline_info.get('theme')}\n"
            if self.outline_info.get("synopsis"):
                default_prompt += f"故事梦概：{self.outline_info.get('synopsis')}\n"
            if self.outline_info.get("worldbuilding"):
                default_prompt += f"世界观设定：{self.outline_info.get('worldbuilding')}\n"
            default_prompt += "\n"

        # 添加上下文信息（如果有）
        if self.context_info:
            # 如果是卷简介，添加卷标题信息
            if self.field_name == "卷简介" and self.context_info.get("volume_title"):
                default_prompt += f"卷标题：{self.context_info.get('volume_title')}\n\n"

            # 如果是章节摘要，添加卷标题、卷简介、章节标题信息以及前10章和后3章的标题和摘要
            if self.field_name == "章节摘要":
                if self.context_info.get("volume_title"):
                    default_prompt += f"卷标题：{self.context_info.get('volume_title')}\n"
                if self.context_info.get("volume_description"):
                    default_prompt += f"卷简介：{self.context_info.get('volume_description')}\n"
                if self.context_info.get("chapter_title"):
                    default_prompt += f"章节标题：{self.context_info.get('chapter_title')}\n"
                if self.context_info.get("chapter_number"):
                    default_prompt += f"当前章节序号：第{self.context_info.get('chapter_number')}章\n"

                # 添加章节出场角色信息
                chapter_characters = self.context_info.get("chapter_characters", [])
                if chapter_characters:
                    default_prompt += "\n本章出场角色：\n"
                    for character in chapter_characters:
                        name = character.get("name", "未命名角色")
                        identity = character.get("identity", "")
                        personality = character.get("personality", "")
                        background = character.get("background", "")
                        default_prompt += f"- {name}：{identity}\n  性格：{personality}\n  背景：{background}\n"
                    default_prompt += "\n"

                # 添加当前章节摘要（如果有）
                current_summary = self.current_text.strip()
                if current_summary:
                    default_prompt += f"当前章节摘要：{current_summary}\n"
                default_prompt += "\n"

                # 添加前10章的标题和摘要
                previous_chapters = self.context_info.get("previous_chapters", [])
                if previous_chapters:
                    default_prompt += "前面章节的标题和摘要：\n"
                    for i, prev_chapter in enumerate(previous_chapters):
                        default_prompt += f"- {prev_chapter.get('title')}: {prev_chapter.get('summary')}\n"
                    default_prompt += "\n"

                # 添加后3章的标题和摘要
                next_chapters = self.context_info.get("next_chapters", [])
                if next_chapters:
                    default_prompt += "后面章节的标题和摘要：\n"
                    for i, next_chapter in enumerate(next_chapters):
                        default_prompt += f"- {next_chapter.get('title')}: {next_chapter.get('summary')}\n"
                    default_prompt += "\n"

            # 如果是章节内容，添加章节相关信息、前10章和后3章的标题和摘要，以及前一章的内容
            if self.field_name == "章节内容":
                # 添加明确的任务说明
                chapter_number = self.context_info.get("chapter_number", "")
                chapter_title = self.context_info.get("chapter_title", "")

                default_prompt += f"请生成第{chapter_number}章《{chapter_title}》的完整章节内容\n\n"

                if self.context_info.get("volume_title"):
                    default_prompt += f"卷标题：{self.context_info.get('volume_title')}\n"
                if self.context_info.get("volume_description"):
                    default_prompt += f"卷简介：{self.context_info.get('volume_description')}\n"
                if self.context_info.get("chapter_title"):
                    default_prompt += f"章节标题：{self.context_info.get('chapter_title')}\n"
                if self.context_info.get("chapter_summary"): # 在这里加上了对当前章节摘要的使用！哼哼！
                    default_prompt += f"当前章节摘要：{self.context_info.get('chapter_summary')}\n"
                if self.context_info.get("chapter_number"):
                    default_prompt += f"当前章节序号：第{self.context_info.get('chapter_number')}章\n"

                # 添加章节出场角色信息
                chapter_characters = self.context_info.get("chapter_characters", [])
                if chapter_characters:
                    default_prompt += "\n本章出场角色：\n"
                    for character in chapter_characters:
                        name = character.get("name", "未命名角色")
                        identity = character.get("identity", "")
                        personality = character.get("personality", "")
                        background = character.get("background", "")
                        default_prompt += f"- {name}：{identity}\n  性格：{personality}\n  背景：{background}\n"
                    default_prompt += "\n"

                default_prompt += "\n"

                # 添加前10章的标题和摘要
                previous_chapters = self.context_info.get("previous_chapters", [])
                if previous_chapters:
                    default_prompt += "前面章节的标题和摘要：\n"
                    for i, prev_chapter in enumerate(previous_chapters):
                        default_prompt += f"- {prev_chapter.get('title')}: {prev_chapter.get('summary')}\n"
                    default_prompt += "\n"

                # 添加前一章的内容
                previous_chapter_content = self.context_info.get("previous_chapter_content", "")
                if previous_chapter_content:
                    # 如果前一章内容过长，只取前5000个字符
                    if len(previous_chapter_content) > 5000:
                        previous_chapter_content = previous_chapter_content[:5000] + "...(省略后续内容)"
                    default_prompt += "前一章的内容：\n\n"
                    default_prompt += f"{previous_chapter_content}\n\n"

                # 添加后3章的标题和摘要
                next_chapters = self.context_info.get("next_chapters", [])
                if next_chapters:
                    default_prompt += "后面章节的标题和摘要：\n"
                    for i, next_chapter in enumerate(next_chapters):
                        default_prompt += f"- {next_chapter.get('title')}: {next_chapter.get('summary')}\n"
                    default_prompt += "\n"

        # 添加当前文本和要求
        current_text = self.current_text.strip()
        if current_text and self.field_name == "章节内容":
            default_prompt += f"当前进度：\n{current_text}\n\n"
        elif current_text:
            default_prompt += f"{current_text}\n\n"

        # 添加章节内容生成的特殊要求
        if self.field_name == "章节内容":
            default_prompt += "要求：\n1. 生成完整的章节内容\n2. 保持原有风格\n3. 更加生动详细\n4. 逻辑连贯\n5. 与小说的整体设定保持一致\n6. 与前后章节内容保持连贯"
            if self.target_word_count: # 添加目标字数要求
                default_prompt += f"\n7. 目标字数：{self.target_word_count}字左右"
        else:
            default_prompt += "要求：\n1. 保持原有风格\n2. 更加生动详细\n3. 逻辑连贯\n4. 与小说的整体设定保持一致"
            # 其他字段类型也可以添加字数要求，如果需要的话

        self.prompt_edit.setPlainText(default_prompt)
        prompt_layout.addWidget(self.prompt_edit)

        # 添加提示词模板选择
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("选择模板:"))

        self.template_combo = QComboBox()

        # 加载模板
        if self.prompt_manager:
            # 添加默认选项
            self.template_combo.addItem("选择提示词模板")

            # 根据字段名称确定模板分类
            category = "general"
            if self.field_name == "章节内容":
                category = "chapter"
            elif self.field_name == "章节摘要":
                category = "chapter_summary"
            elif self.field_name in ["标题", "中心思想", "故事梗概", "世界观设定"]:
                category = "outline"

            # 加载对应分类的模板
            templates = self.prompt_manager.get_templates_by_category(category)
            for template in templates:
                self.template_combo.addItem(template.name)
        else:
            # 如果没有提示词管理器，使用默认模板
            self.template_combo.addItems(["默认模板", "详细描述模板", "简洁模板", "创意模板"])

        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        template_layout.addWidget(self.template_combo)

        # 添加模板管理按钮
        self.new_template_button = QPushButton("新建模板")
        self.new_template_button.clicked.connect(self._create_new_template)
        template_layout.addWidget(self.new_template_button)

        self.edit_template_button = QPushButton("编辑模板")
        self.edit_template_button.clicked.connect(self._edit_template)
        self.edit_template_button.setEnabled(False)  # 初始禁用
        template_layout.addWidget(self.edit_template_button)

        self.delete_template_button = QPushButton("删除模板")
        self.delete_template_button.clicked.connect(self._delete_template)
        self.delete_template_button.setEnabled(False)  # 初始禁用
        template_layout.addWidget(self.delete_template_button)

        template_layout.addStretch()
        prompt_layout.addLayout(template_layout)

        prompt_group.setLayout(prompt_layout)
        layout.addWidget(prompt_group)

        # 模型选择
        model_layout = QHBoxLayout()
        model_label = QLabel("选择模型：")
        model_layout.addWidget(model_label)

        self.model_combo = QComboBox()
        self.model_combo.addItems(self.models)

        # 设置默认选中的模型
        selected_model_to_set = None
        if self.config_manager:
            last_selected_model = self.config_manager.get_last_selected_model()
            if last_selected_model and last_selected_model in self.models:
                selected_model_to_set = last_selected_model
                # print(f"调试：使用已保存的模型: {selected_model_to_set}") # 哼，调试信息，用完就删！

        if not selected_model_to_set and self.default_model and self.default_model in self.models:
            selected_model_to_set = self.default_model
            # print(f"调试：使用传入的默认模型: {selected_model_to_set}") # 哼，调试信息，用完就删！

        if not selected_model_to_set and self.models:
            selected_model_to_set = self.models[0]
            # print(f"调试：使用列表第一个模型: {selected_model_to_set}") # 哼，调试信息，用完就删！

        if selected_model_to_set:
            index = self.model_combo.findText(selected_model_to_set)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
            # else:
                # print(f"调试：模型 {selected_model_to_set} 在列表中找不到，将使用第一个。") # 哼，找不到就算了！
                # if self.models: self.model_combo.setCurrentIndex(0) # 以防万一
        elif self.models: # 如果一个都没选上，并且列表不为空，那就选第一个吧，真是麻烦！
            self.model_combo.setCurrentIndex(0)

        model_layout.addWidget(self.model_combo)

        # 温度设置已移除

        model_layout.addStretch()
        layout.addLayout(model_layout)
 
        # 知识库辅助部分
        self.kb_group = QGroupBox("知识库辅助")
        kb_layout = QVBoxLayout()
 
        self.enable_kb_checkbox = QCheckBox("启用知识库辅助")
        self.enable_kb_checkbox.setChecked(False) # 默认不启用
        self.enable_kb_checkbox.toggled.connect(self._on_toggle_knowledge_base)
        kb_layout.addWidget(self.enable_kb_checkbox)
 
        kb_controls_layout = QFormLayout()
        self.kb_select_combo = QComboBox()
        if self.available_knowledge_bases:
            self.kb_select_combo.addItems(self.available_knowledge_bases)
        else:
            self.kb_select_combo.addItem("无可用知识库")
            self.kb_select_combo.setEnabled(False)
        kb_controls_layout.addRow("选择知识库:", self.kb_select_combo)
 
        # 查询关键词输入和快速查询按钮的水平布局
        kb_query_input_layout = QHBoxLayout() # 新增：用于放置查询输入和快速查询按钮
        self.kb_query_edit = QLineEdit() # 原来的 self.kb_query_input
        kb_query_input_layout.addWidget(self.kb_query_edit)

        # 新增：“快速查询”按钮
        self.kb_quick_query_button = QPushButton("快速查询")
        self.kb_quick_query_button.setToolTip("使用上方主提示词内容作为关键词进行查询") 
        self.kb_quick_query_button.clicked.connect(self._on_quick_query_kb_clicked) # 连接信号
        kb_query_input_layout.addWidget(self.kb_quick_query_button)
        kb_controls_layout.addRow("查询关键词:", kb_query_input_layout) # 将整个水平布局添加到FormLayout

        self.kb_results_count_spinbox = QSpinBox()
        self.kb_results_count_spinbox.setMinimum(1)
        self.kb_results_count_spinbox.setMaximum(20) 
        self.kb_results_count_spinbox.setValue(5)   # 默认返回5条
        kb_controls_layout.addRow("返回结果数量:", self.kb_results_count_spinbox)
        kb_layout.addLayout(kb_controls_layout)
 
        self.kb_query_button = QPushButton("查询知识库")
        self.kb_query_button.clicked.connect(self._on_query_knowledge_base_clicked)
        kb_layout.addWidget(self.kb_query_button)
 
        # 给这个 QLabel 设置 objectName，方便查找
        self.kb_results_label = QLabel("选择应用的结果：")
        self.kb_results_label.setObjectName("kb_results_label")
        kb_layout.addWidget(self.kb_results_label)
 
        kb_results_actions_layout = QHBoxLayout()
        self.kb_select_all_button = QPushButton("全选/全不选")
        self.kb_select_all_button.setCheckable(True)
        self.kb_select_all_button.toggled.connect(self._on_select_all_kb_results_toggled)
        kb_results_actions_layout.addWidget(self.kb_select_all_button)
        kb_results_actions_layout.addStretch()
        kb_layout.addLayout(kb_results_actions_layout)
 
        self.kb_results_scroll_area = QScrollArea()
        self.kb_results_scroll_area.setWidgetResizable(True)
        self.kb_results_scroll_area.setFixedHeight(100) # 给滚动区域一个初始高度
        self.kb_results_widget = QWidget()
        self.kb_results_layout = QHBoxLayout(self.kb_results_widget) # 横向排列结果按钮
        self.kb_results_widget.setLayout(self.kb_results_layout)
        self.kb_results_scroll_area.setWidget(self.kb_results_widget)
        kb_layout.addWidget(self.kb_results_scroll_area)
 
        # 应用结果按钮的水平布局
        kb_apply_buttons_layout = QHBoxLayout() # 新增：用于放置两个应用结果的按钮

        self.kb_confirm_button = QPushButton("确认应用的查询结果") # 原来的 self.kb_confirm_apply_button
        self.kb_confirm_button.setToolTip("将选中的知识库结果替换或追加到主提示词的特定标记区域") # 哼，这个提示也不能少！
        self.kb_confirm_button.clicked.connect(self._on_confirm_apply_kb_results)
        kb_apply_buttons_layout.addWidget(self.kb_confirm_button)

        # 新增：“添加应用结果”按钮
        self.kb_add_apply_button = QPushButton("添加应用结果")
        self.kb_add_apply_button.setToolTip("将选中的知识库结果追加到主提示词的末尾（不使用标记）") # 哼，这个也得有提示！
        self.kb_add_apply_button.clicked.connect(self._on_add_applied_kb_results_clicked) # 连接信号
        kb_apply_buttons_layout.addWidget(self.kb_add_apply_button)

        kb_layout.addLayout(kb_apply_buttons_layout) # 将按钮布局添加到知识库组

        self.kb_group.setLayout(kb_layout)
        layout.addWidget(self.kb_group)

        self._on_toggle_knowledge_base(False) # 初始时根据复选框状态设置控件可用性

        # 生成按钮
        generate_button = QPushButton("生成")
        generate_button.clicked.connect(self.generate)
        layout.addWidget(generate_button)
 
        # 结果部分
        result_group = QGroupBox("生成结果")
        result_layout = QVBoxLayout()

        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        result_layout.addWidget(self.result_edit)

        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        self.progress_bar.setVisible(False)
        result_layout.addWidget(self.progress_bar)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # 按钮部分
        button_layout = QHBoxLayout()

        self.use_button = QPushButton("保存并使用")
        self.use_button.clicked.connect(self.accept)
        self.use_button.setEnabled(False)
        button_layout.addWidget(self.use_button)

        self.copy_button = QPushButton("复制结果")
        self.copy_button.clicked.connect(self._copy_result)
        self.copy_button.setEnabled(False)
        button_layout.addWidget(self.copy_button)

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def _setup_shortcuts(self):
        """设置快捷键"""
        # Ctrl+Enter 生成
        generate_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        generate_shortcut.activated.connect(self.generate)

        # Ctrl+C 复制结果
        copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        copy_shortcut.activated.connect(self._copy_result)

        # Esc 取消
        cancel_shortcut = QShortcut(QKeySequence("Esc"), self)
        cancel_shortcut.activated.connect(self.reject)

    def _on_template_changed(self, index):
        """模板选择变更事件"""
        # 启用/禁用删除模板按钮和编辑模板按钮
        if index <= 0 or not self.prompt_manager:  # 第一项是提示文本或没有提示词管理器
            self.delete_template_button.setEnabled(False)
            self.edit_template_button.setEnabled(False)
        else:
            self.delete_template_button.setEnabled(True)
            self.edit_template_button.setEnabled(True)

        # 如果有提示词管理器且选择了有效模板
        if self.prompt_manager and index > 0:
            template_name = self.template_combo.currentText()
            template = self.prompt_manager.get_template(template_name)
            if template:
                self.prompt_edit.setPlainText(template.content)
                return

        # 如果没有提示词管理器或没有选择有效模板，使用默认模板
        # 构建基本提示词前缀（包含总大纲信息和上下文信息）
        prefix = f"请根据以下内容，生成一个新的{self.field_name}：\n\n"

        # 添加总大纲信息
        if self.outline_info:
            if self.outline_info.get("title"):
                prefix += f"小说标题：{self.outline_info.get('title')}\n"
            if self.outline_info.get("theme"):
                prefix += f"中心思想：{self.outline_info.get('theme')}\n"
            if self.outline_info.get("synopsis"):
                prefix += f"故事梦概：{self.outline_info.get('synopsis')}\n"
            if self.outline_info.get("worldbuilding"):
                prefix += f"世界观设定：{self.outline_info.get('worldbuilding')}\n"
            prefix += "\n"

        # 添加上下文信息
        if self.context_info:
            # 如果是卷简介，添加卷标题信息
            if self.field_name == "卷简介" and self.context_info.get("volume_title"):
                prefix += f"卷标题：{self.context_info.get('volume_title')}\n\n"

            # 如果是章节摘要，添加卷标题、卷简介和章节标题信息
            if self.field_name == "章节摘要":
                if self.context_info.get("volume_title"):
                    prefix += f"卷标题：{self.context_info.get('volume_title')}\n"
                if self.context_info.get("volume_description"):
                    prefix += f"卷简介：{self.context_info.get('volume_description')}\n"
                if self.context_info.get("chapter_title"):
                    prefix += f"章节标题：{self.context_info.get('chapter_title')}\n"
                prefix += "\n"

        # 添加当前文本
        content = f"{self.current_text}\n\n"

        # 如果没有提示词管理器，使用默认模板
        if not self.prompt_manager:
            templates = {
                0: prefix + content + "要求：\n1. 保持原有风格\n2. 更加生动详细\n3. 逻辑连贯\n4. 与小说的整体设定保持一致",
                1: prefix + content + "要求：\n1. 保持原有风格和主题\n2. 增加细节描写和背景信息\n3. 使用丰富的修辞手法\n4. 确保逻辑连贯和情节合理\n5. 与小说的整体设定保持一致",
                2: prefix + content + "要求：\n1. 保持核心内容和主题\n2. 使用简洁有力的语言\n3. 去除冗余信息\n4. 突出重点\n5. 与小说的整体设定保持一致",
                3: prefix + content + "要求：\n1. 保持基本主题\n2. 加入创新的元素和视角\n3. 使用富有想象力的语言\n4. 创造出令人惊喜的内容\n5. 与小说的整体设定保持一致"
            }

            if index in templates:
                self.prompt_edit.setPlainText(templates[index])

    def _create_new_template(self):
        """创建新模板"""
        if not self.prompt_manager:
            QMessageBox.warning(self, "错误", "无法获取提示词管理器")
            return

        # 创建编辑对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("创建新模板")
        dialog.resize(600, 500)

        layout = QVBoxLayout(dialog)

        # 模板名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("模板名称:"))
        name_edit = QLineEdit(f"自定义{self.field_name}模板_{len(self.prompt_manager.get_templates_by_category('general')) + 1}")
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)

        # 模板描述
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("模板描述:"))
        desc_edit = QLineEdit(f"自定义{self.field_name}生成模板")
        desc_layout.addWidget(desc_edit)
        layout.addLayout(desc_layout)

        # 模板分类
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("模板分类:"))
        category_edit = QLineEdit()

        # 根据字段名称设置默认分类
        if self.field_name == "章节内容":
            category_edit.setText("chapter")
        elif self.field_name == "章节摘要":
            category_edit.setText("chapter_summary")
        elif self.field_name in ["标题", "中心思想", "故事梗概", "世界观设定"]:
            category_edit.setText("outline")
        else:
            category_edit.setText("general")

        category_layout.addWidget(category_edit)
        layout.addLayout(category_layout)

        # 模板内容
        content_label = QLabel("模板内容:")
        layout.addWidget(content_label)

        content_edit = QTextEdit()
        content_edit.setPlainText(self.prompt_edit.toPlainText())
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
            template_category = category_edit.text()

            # 添加模板
            success = self.prompt_manager.add_template(
                template_name,
                template_content,
                template_category,
                template_desc
            )

            if success:
                # 添加到下拉框
                self.template_combo.addItem(template_name)
                self.template_combo.setCurrentText(template_name)

                QMessageBox.information(self, "保存成功", f"模板 '{template_name}' 已创建")
            else:
                QMessageBox.warning(self, "保存失败", f"模板 '{template_name}' 已存在或保存失败")

    def _save_as_template(self):
        """保存当前提示词为模板"""
        if not self.prompt_manager:
            QMessageBox.warning(self, "错误", "无法获取提示词管理器")
            return

        template_name, ok = QInputDialog.getText(
            self, "保存模板", "请输入模板名称:",
            text=f"自定义{self.field_name}模板"
        )

        if ok and template_name:
            # 获取模板描述
            template_desc, ok = QInputDialog.getText(
                self, "模板描述", "请输入模板描述:",
                text=f"基于当前设置创建的{self.field_name}模板"
            )

            if ok:
                # 确定模板分类
                category = "general"
                if self.field_name == "章节内容":
                    category = "chapter"
                elif self.field_name == "章节摘要":
                    category = "chapter_summary"
                elif self.field_name in ["标题", "中心思想", "故事梗概", "世界观设定"]:
                    category = "outline"

                # 添加模板
                success = self.prompt_manager.add_template(
                    template_name,
                    self.prompt_edit.toPlainText(),
                    category,
                    template_desc
                )

                if success:
                    # 添加到下拉框
                    self.template_combo.addItem(template_name)
                    self.template_combo.setCurrentText(template_name)

                    QMessageBox.information(self, "保存成功", f"模板 '{template_name}' 已保存")
                else:
                    QMessageBox.warning(self, "保存失败", f"模板 '{template_name}' 已存在或保存失败")

    def _edit_template(self):
        """编辑当前选中的模板"""
        if not self.prompt_manager:
            QMessageBox.warning(self, "错误", "无法获取提示词管理器")
            return

        if self.template_combo.currentIndex() <= 0:
            return

        template_name = self.template_combo.currentText()
        template = self.prompt_manager.get_template(template_name)

        if not template:
            QMessageBox.warning(self, "错误", f"无法获取模板 '{template_name}'")
            return

        # 确定模板分类
        category = template.category

        # 获取当前编辑器中的内容
        current_content = self.prompt_edit.toPlainText()

        # 更新模板
        success = self.prompt_manager.update_template(
            template_name,
            current_content,
            category,
            template.description
        )

        if success:
            QMessageBox.information(self, "保存成功", f"模板 '{template_name}' 已更新")
        else:
            QMessageBox.warning(self, "保存失败", f"无法更新模板 '{template_name}'")

    def _delete_template(self):
        """删除当前选中的模板"""
        if not self.prompt_manager:
            QMessageBox.warning(self, "错误", "无法获取提示词管理器")
            return

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

                QMessageBox.information(self, "删除成功", f"模板 '{template_name}' 已删除")
            else:
                QMessageBox.warning(self, "删除失败", f"模板 '{template_name}' 删除失败")

    def _copy_result(self):
        """复制结果到剪贴板"""
        if self.result_text:
            QApplication.clipboard().setText(self.result_text)
            QToolTip.showText(self.copy_button.mapToGlobal(QPoint(0, 0)), "已复制到剪贴板", self)

    def generate(self):
        """生成内容"""
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "提示", "请输入提示词")
            return

        # 获取模型
        model_text = self.model_combo.currentText()
        model_text_lower = model_text.lower()
        
        # 转换为模型类型
        if model_text_lower == "gpt":
            model_type = "gpt"
        elif model_text_lower == "claude":
            model_type = "claude"
        elif model_text_lower == "gemini":
            model_type = "gemini"
        elif model_text_lower == "自定义openai":
            model_type = "custom_openai"
        elif model_text_lower == "modelscope":
            model_type = "modelscope"
        elif model_text_lower == "ollama":
            model_type = "ollama"
        elif model_text_lower == "siliconflow":
            model_type = "siliconflow"
        else:
            # 检查是否是自定义模型，自定义模型直接使用模型名称作为类型
            model_type = model_text
        try:
            # 尝试不同的方式获取main_window
            if hasattr(self.parent(), 'main_window'):
                main_window = self.parent().main_window
            elif hasattr(self.parent(), 'parent') and hasattr(self.parent().parent(), 'main_window'):
                main_window = self.parent().parent().main_window
            else:
                # 如果无法获取main_window，显示错误
                QMessageBox.warning(self, "错误", "无法获取main_window")
                return

            model = main_window.get_model(model_type)
            # 保存用户选择的模型
            if self.config_manager:
                self.config_manager.save_last_selected_model(model_text)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取模型失败: {str(e)}")
            return

        # 清空结果
        self.result_edit.clear()
        self.result_text = ""

        # 显示进度条
        self.progress_bar.setVisible(True)

        # 禁用生成按钮
        self.findChild(QPushButton, "").setEnabled(False)

        # 创建并启动生成线程
        self.generation_thread = GenerationThread(
            model.generate_stream,
            (prompt,),
            {}
        )

        # 连接信号
        self.generation_thread.progress_signal.connect(self._on_progress)
        self.generation_thread.finished_signal.connect(self._on_finished)
        self.generation_thread.error_signal.connect(self._on_error)

        # 启动线程
        self.generation_thread.start()

    def _on_progress(self, chunk):
        """处理进度信号"""
        self.result_edit.insertPlainText(chunk)
        self.result_text += chunk
        # 滚动到底部
        scrollbar = self.result_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_finished(self, result):
        """处理完成信号"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)

        # 启用按钮
        self.use_button.setEnabled(True)
        self.copy_button.setEnabled(True)
        self.findChild(QPushButton, "").setEnabled(True) # 重新启用生成按钮

        # 保存用户选择的模型
        if self.config_manager:
            selected_model_name = self.model_combo.currentText()
            self.config_manager.save_last_selected_model(selected_model_name)
            # print(f"调试：已保存选择的模型: {selected_model_name}") # 哼，调试信息，用完就删！

        QMessageBox.information(self, "完成", "内容生成完成")

    def _on_error(self, error):
        """处理错误信号"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)

        # 启用生成按钮
        self.findChild(QPushButton, "").setEnabled(True)

        QMessageBox.warning(self, "错误", f"生成内容时出错: {error}")

    def get_result(self):
        """获取生成结果"""
        return self.result_text
 
    # 新增：“快速查询”按钮的槽函数
    @pyqtSlot()
    def _on_quick_query_kb_clicked(self):
        """
        当“快速查询”按钮被点击时触发。
        使用主提示词编辑框的内容作为查询关键词，并执行知识库查询。
        """
        if not self.enable_kb_checkbox.isChecked():
            QMessageBox.information(self, "提示", "请先启用知识库辅助功能，再进行快速查询哦！")
            return

        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            QMessageBox.warning(self, "提示", "主提示词内容为空，无法进行快速查询！")
            return

        self.kb_query_edit.setText(prompt_text) # 将主提示词内容设置到查询输入框
        self._on_query_knowledge_base_clicked() # 调用现有的查询逻辑，哼，省点力气！

    # 新增：“添加应用结果”按钮的槽函数 (￣▽￣)~*
    @pyqtSlot()
    def _on_add_applied_kb_results_clicked(self):
        """
        当“添加应用结果”按钮被点击时触发。
        收集当前选中的知识库结果，格式化后追加到主提示词编辑框的末尾。
        """
        if not self.enable_kb_checkbox.isChecked():
            QMessageBox.information(self, "提示", "知识库辅助未启用，无法添加结果。先勾选上面的复选框啦，笨蛋！")
            return

        selected_texts = []
        for button in self.kb_result_buttons:
            if button.isChecked():
                selected_texts.append(button.property("full_text"))

        if not selected_texts:
            QMessageBox.information(self, "提示", "请至少选择一个知识库查询结果进行添加。")
            return

        # 格式化知识片段
        formatted_kb_results = "根据知识库查询，有以下相关结果参考：\n"
        for text in selected_texts:
            # 每个片段前加个小横杠，看起来整齐点！
            formatted_kb_results += f"- {text}\n"

        current_prompt = self.prompt_edit.toPlainText()
        # 追加到末尾，记得加个换行，不然黏在一起多难看！
        new_prompt = current_prompt.rstrip() + "\n\n" + formatted_kb_results.strip() # 确保追加的内容前后都有合适的间距

        self.prompt_edit.setPlainText(new_prompt)
        QMessageBox.information(self, "成功", "选中的知识库结果已成功追加到主提示词末尾！")


    def _on_toggle_knowledge_base(self, is_enabled: bool):
        """根据复选框状态控制知识库相关UI的显隐和可用性"""
        # 这些控件应该一直可见，但根据is_enabled来启用/禁用
        self.kb_select_combo.setEnabled(is_enabled and bool(self.available_knowledge_bases) and self.available_knowledge_bases[0] != "无可用知识库")
        self.kb_query_edit.setEnabled(is_enabled)
        # “快速查询”按钮的可用性也由复选框控制
        self.kb_quick_query_button.setEnabled(is_enabled)
        self.kb_results_count_spinbox.setEnabled(is_enabled)
        self.kb_query_button.setEnabled(is_enabled)

        # 这些控件的可见性也受is_enabled控制
        # 使用 objectName 查找 QLabel，而不是容易出错的 text
        kb_results_label = self.findChild(QLabel, "kb_results_label")
        if kb_results_label:
            kb_results_label.setVisible(is_enabled)
        self.kb_select_all_button.setVisible(is_enabled)
        self.kb_results_scroll_area.setVisible(is_enabled)
        self.kb_confirm_button.setVisible(is_enabled)
        # “添加应用结果”按钮的可见性也由复选框控制，哼，一个都不能少！
        self.kb_add_apply_button.setVisible(is_enabled)

        # 如果禁用了，清空结果区域并重置按钮
        if not is_enabled:
            self._clear_kb_results()
            self.kb_select_all_button.setChecked(False)

    def _clear_kb_results(self):
        """清空知识库查询结果区域"""
        for button in self.kb_result_buttons:
            self.kb_results_layout.removeWidget(button)
            button.deleteLater()
        self.kb_result_buttons.clear()
 
    def _on_query_knowledge_base_clicked(self):
        """处理查询知识库按钮点击事件"""
        if not self.knowledge_base_manager:
            QMessageBox.warning(self, "知识库错误", "知识库管理器未初始化！")
            return
 
        kb_name = self.kb_select_combo.currentText()
        query_text = self.kb_query_edit.text().strip()
        top_k = self.kb_results_count_spinbox.value()
 
        if not query_text:
            QMessageBox.warning(self, "输入提示", "请输入查询关键词！")
            return
 
        if kb_name == "无可用知识库":
            QMessageBox.warning(self, "选择提示", "请先配置并选择一个可用的知识库！")
            return
 
        # 清空旧结果
        self._clear_kb_results()
        self.kb_query_button.setEnabled(False) # 查询期间禁用按钮
        self.progress_bar.setVisible(True) # 显示主进度条
 
        # 使用类似GenerationThread的方式进行异步查询
        # 注意：KnowledgeBaseManager.query()本身可能是阻塞的，所以放入线程
        self.kb_query_thread = GenerationThread(
            self.knowledge_base_manager.query, # 传递方法本身
            (kb_name, query_text, top_k),      # 参数元组
            {}                                 # 关键字参数字典
        )
        self.kb_query_thread.finished_signal.connect(self._on_kb_query_finished)
        self.kb_query_thread.error_signal.connect(self._on_kb_query_error)
        self.kb_query_thread.start()
 
    def _on_kb_query_finished(self, results):
        """知识库查询完成后的处理"""
        self.kb_query_button.setEnabled(True) # 恢复按钮
        self.progress_bar.setVisible(False)   # 隐藏主进度条
 
        if not results:
            QMessageBox.information(self, "查询结果", "未能查询到相关知识片段。")
            return
 
        # 正确遍历字典列表，而不是尝试解包元组
        for i, result_item in enumerate(results):
            # 使用 .get() 安全地获取内容和得分，防止字典里没这些键，真是麻烦死了！
            doc_content = result_item.get('text', '')
            score = result_item.get('score', 0.0)

            # 创建一个可勾选的按钮来显示结果摘要
            # 为了简单，按钮文本可以是 "结果 N (相关度: X.XX)"
            # 实际内容存储在按钮的属性中
            summary = doc_content[:50] + "..." if len(doc_content) > 50 else doc_content # 简单摘要
            btn_text = f"片段{i+1} (相关度: {score:.2f})\n{summary}"
            result_button = QPushButton(btn_text)
            # 确保按钮是可勾选的，这样才能被选中！
            result_button.setCheckable(True)
            result_button.setChecked(False) # 默认不选中
            result_button.setProperty("full_text", doc_content) # 存储完整文本
            result_button.setToolTip(doc_content) # 鼠标悬浮显示完整内容
            # 连接 toggled 信号到样式更新方法，哼，看你还怎么普通！
            result_button.toggled.connect(lambda checked, b=result_button: self._update_kb_button_style(b, checked))
            # 设置初始样式（未选中）
            self._update_kb_button_style(result_button, False)
            self.kb_results_layout.addWidget(result_button)
            self.kb_result_buttons.append(result_button)
        self.kb_select_all_button.setChecked(False) # 新结果加载后，重置全选按钮

    def _on_kb_query_error(self, error_message):
        """知识库查询出错的处理"""
        self.kb_query_button.setEnabled(True) # 恢复按钮
        self.progress_bar.setVisible(False)   # 隐藏主进度条
        QMessageBox.critical(self, "查询失败", f"查询知识库时发生错误：\n{error_message}")
 
    def _on_select_all_kb_results_toggled(self, checked: bool):
        """处理全选/全不选按钮状态改变"""
        for button in self.kb_result_buttons:
            button.setChecked(checked)
            # 手动触发样式更新，不然怎么知道你变了！真是的！
            self._update_kb_button_style(button, checked)

    # 新增：更新知识库按钮样式的方法
    def _update_kb_button_style(self, button: QPushButton, checked: bool):
        """根据选中状态更新按钮样式"""
        if checked:
            # 选中状态：浅蓝色背景，蓝色边框，够醒目了吧！
            button.setStyleSheet("background-color: lightblue; border: 1px solid blue;")
        else:
            # 未选中状态：恢复默认样式，
            button.setStyleSheet("") # 清空样式，使用默认

    def _on_confirm_apply_kb_results(self):
        """
        收集选中的知识库结果并应用到主提示词编辑器。
        如果存在标记，则替换标记内容；否则，追加包含标记的整个块。

        """
        if not self.enable_kb_checkbox.isChecked():
            QMessageBox.information(self, "提示", "知识库辅助未启用，无法确认应用结果。！")
            return

        selected_texts = []
        for button in self.kb_result_buttons:
            if button.isChecked():
                selected_texts.append(button.property("full_text"))

        if not selected_texts:
            QMessageBox.information(self, "提示", "请至少选择一个知识库查询结果进行应用。")
            return

        # 格式化知识片段
        formatted_kb_content = "根据知识库查询，有以下相关结果参考：\n"
        for text in selected_texts:
            formatted_kb_content += f"- {text}\n"

        # 标记，哼，这些丑陋的标记！
        start_marker = "<!-- KB_RESULTS_START -->"
        end_marker = "<!-- KB_RESULTS_END -->"

        current_prompt = self.prompt_edit.toPlainText()
        start_index = current_prompt.find(start_marker)
        end_index = current_prompt.find(end_marker)

        # 准备要插入或替换的完整文本块，包含标记和格式化后的知识内容
        # 哼，换行符也要安排得明明白白！
        block_to_insert = f"\n{start_marker}\n{formatted_kb_content.strip()}\n{end_marker}\n"

        if start_index != -1 and end_index != -1 and start_index < end_index:
            # 标记存在且顺序正确，替换标记之间的内容（包括标记本身）
          
            before_marker_content = current_prompt[:start_index]
            after_marker_content = current_prompt[end_index + len(end_marker):]
            # 去掉可能的多余换行，再拼接，哼，细节决定成败！
            new_prompt = before_marker_content.rstrip() + block_to_insert.strip() + after_marker_content.lstrip()
            # 如果前面没有内容，确保新块不会顶格
            if not before_marker_content.strip():
                new_prompt = block_to_insert.strip() + after_marker_content.lstrip()
            # 如果后面没有内容，也处理一下
            if not after_marker_content.strip() and before_marker_content.strip():
                 new_prompt = before_marker_content.rstrip() + block_to_insert.strip()

        else:
            # 标记不存在或顺序不正确，则在末尾追加整个文本块
            
            new_prompt = current_prompt.rstrip() + "\n\n" + block_to_insert.strip() # 确保追加前有空行

        self.prompt_edit.setPlainText(new_prompt.strip()) # 最后再去除可能的多余空白
        QMessageBox.information(self, "成功", "选中的知识库结果已成功应用到主提示词中！")


class DraggableListWidget(QListWidget):
    """
    可拖放的列表控件

    支持项目拖放重新排序
    """

    item_moved = pyqtSignal(int, int)  # 从索引，到索引

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

        # 跟踪拖放操作
        self._drag_start_index = -1
        self.model().rowsMoved.connect(self._on_rows_moved)

    def dropEvent(self, event):
        """处理放下事件"""
        # 记录当前选中项的索引（拖动开始位置）
        self._drag_start_index = self.currentRow()
        super().dropEvent(event)

    def _on_rows_moved(self, parent, start, end, destination, row):
        """行移动事件处理"""
        if self._drag_start_index >= 0:
            # 计算新位置
            new_index = row
            if row > self._drag_start_index:
                new_index -= 1

            # 发出信号
            self.item_moved.emit(self._drag_start_index, new_index)

            # 重置拖动开始索引
            self._drag_start_index = -1


class ThemeManager:
    """
    主题管理器

    管理应用的主题（明亮/深色）
    """

    LIGHT_THEME = "light"
    DARK_THEME = "dark"

    def __init__(self, app):
        """
        初始化主题管理器

        Args:
            app: QApplication实例
        """
        self.app = app
        self.current_theme = self.LIGHT_THEME

    def set_theme(self, theme):
        """
        设置应用主题

        Args:
            theme: 主题名称，可以是 "light" 或 "dark"
        """
        if theme == self.current_theme:
            return

        if theme == self.DARK_THEME:
            self._set_dark_theme()
        else:
            self._set_light_theme()

        self.current_theme = theme

    def toggle_theme(self):
        """切换主题"""
        if self.current_theme == self.LIGHT_THEME:
            self.set_theme(self.DARK_THEME)
        else:
            self.set_theme(self.LIGHT_THEME)

    def _set_light_theme(self):
        """设置明亮主题"""
        self.app.setStyle("Fusion")

        # 使用默认调色板
        palette = QPalette()
        self.app.setPalette(palette)

        # 应用明亮主题样式表
        self.app.setStyleSheet(get_style("light"))

    def _set_dark_theme(self):
        """设置深色主题"""
        self.app.setStyle("Fusion")

        # 创建深色调色板
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)

        # 设置调色板
        self.app.setPalette(palette)

        # 应用深色主题样式表
        self.app.setStyleSheet(get_style("dark"))


class StatusBarManager:
    """
    状态栏管理器

    管理主窗口的状态栏
    """

    def __init__(self, status_bar):
        """
        初始化状态栏管理器

        Args:
            status_bar: QStatusBar实例
        """
        self.status_bar = status_bar
        self.message_timer = QTimer()
        self.message_timer.timeout.connect(self._clear_message)

        # 创建状态标签
        self.status_label = QLabel()
        self.status_bar.addWidget(self.status_label)

        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self.status_bar.addWidget(self.progress_bar)

    def show_message(self, message, timeout=3000):
        """
        显示临时消息

        Args:
            message: 要显示的消息
            timeout: 消息显示时间（毫秒）
        """
        self.status_label.setText(message)

        # 重置定时器
        self.message_timer.stop()
        self.message_timer.start(timeout)

    def show_permanent_message(self, message):
        """
        显示永久消息

        Args:
            message: 要显示的消息
        """
        self.message_timer.stop()
        self.status_label.setText(message)

    def _clear_message(self):
        """清除消息"""
        self.status_label.clear()
        self.message_timer.stop()

    def show_progress(self, value=None, maximum=None):
        """
        显示进度条

        Args:
            value: 当前进度值
            maximum: 最大进度值
        """
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)

        if maximum is not None:
            self.progress_bar.setMaximum(maximum)

        if value is not None:
            self.progress_bar.setValue(value)

    def hide_progress(self):
        """隐藏进度条"""
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)


class KeyboardShortcutManager:
    """
    键盘快捷键管理器

    管理应用的键盘快捷键
    """

    def __init__(self, main_window):
        """
        初始化键盘快捷键管理器

        Args:
            main_window: 主窗口实例
        """
        self.main_window = main_window
        self.shortcuts = {}

        # 设置常用快捷键
        self._setup_common_shortcuts()

    def _setup_common_shortcuts(self):
        """设置常用快捷键"""
        # 文件操作
        self.add_shortcut("Ctrl+N", self.main_window.new_novel, "新建小说")
        self.add_shortcut("Ctrl+O", self.main_window.load_novel, "打开小说")
        self.add_shortcut("Ctrl+S", self.main_window.save_novel, "保存小说")

        # 标签页切换
        self.add_shortcut("Ctrl+1", lambda: self.main_window.tab_widget.setCurrentIndex(0), "切换到大纲生成")
        self.add_shortcut("Ctrl+2", lambda: self.main_window.tab_widget.setCurrentIndex(1), "切换到总大纲编辑")
        self.add_shortcut("Ctrl+3", lambda: self.main_window.tab_widget.setCurrentIndex(2), "切换到章节大纲编辑")
        self.add_shortcut("Ctrl+4", lambda: self.main_window.tab_widget.setCurrentIndex(3), "切换到章节生成")
        self.add_shortcut("Ctrl+5", lambda: self.main_window.tab_widget.setCurrentIndex(4), "切换到人物编辑")
        self.add_shortcut("Ctrl+6", lambda: self.main_window.tab_widget.setCurrentIndex(5), "切换到设置")

        # 主题切换
        self.add_shortcut("Ctrl+T", self.main_window.toggle_theme, "切换主题")

    def add_shortcut(self, key_sequence, callback, description=None):
        """
        添加快捷键

        Args:
            key_sequence: 快捷键序列
            callback: 回调函数
            description: 快捷键描述
        """
        shortcut = QShortcut(QKeySequence(key_sequence), self.main_window)
        shortcut.activated.connect(callback)

        self.shortcuts[key_sequence] = {
            "shortcut": shortcut,
            "callback": callback,
            "description": description
        }

    def remove_shortcut(self, key_sequence):
        """
        移除快捷键

        Args:
            key_sequence: 要移除的快捷键序列
        """
        if key_sequence in self.shortcuts:
            shortcut = self.shortcuts[key_sequence]["shortcut"]
            shortcut.setEnabled(False)
            shortcut.deleteLater()
            del self.shortcuts[key_sequence]

    def get_shortcut_descriptions(self):
        """
        获取所有快捷键的描述

        Returns:
            快捷键描述列表
        """
        descriptions = []
        for key, data in self.shortcuts.items():
            if data["description"]:
                descriptions.append(f"{key}: {data['description']}")

        return descriptions
