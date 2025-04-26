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

from utils.async_utils import GenerationThread, ProgressIndicator, AsyncHelper
from ui.styles import get_style


class AIGenerateDialog(QDialog):
    """
    AI生成对话框

    用于使用AI生成内容的通用对话框
    """

    def __init__(self, parent=None, title="AI生成", field_name="内容", current_text="",
                 models=None, default_model="GPT", outline_info=None, context_info=None, prompt_manager=None,
                 task_type="generate", selected_text=None, full_text=None, target_word_count=None): # 添加新参数 target_word_count
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
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 500)
        self.field_name = field_name
        self.current_text = current_text # 对于润色任务，这个可能为空
        self.result_text = ""
        self.generation_thread = None
        self.models = models or ["GPT", "Claude", "Gemini", "自定义OpenAI", "ModelScope", "Ollama", "SiliconFlow"] # 保持模型列表更新

        # 获取配置管理器
        self.config_manager = None
        try:
            if hasattr(parent, 'config_manager'):
                self.config_manager = parent.config_manager
            elif hasattr(parent, 'main_window') and hasattr(parent.main_window, 'config_manager'):
                self.config_manager = parent.main_window.config_manager
        except:
            pass

        # 从配置中加载上次使用的模型
        saved_model = None
        if self.config_manager:
            saved_model = self.config_manager.get_config("AI_DIALOG", "last_used_model", None)

        # 确定默认模型：优先使用保存的模型，其次使用传入的默认模型，最后使用模型列表的第一个
        if saved_model and saved_model in self.models:
            self.default_model = saved_model
        else:
            self.default_model = default_model if default_model in self.models else self.models[0]

        self.outline_info = outline_info or {}
        self.context_info = context_info or {}
        # 保存新参数
        self.task_type = task_type
        self.selected_text = selected_text
        self.full_text = full_text
        self.target_word_count = target_word_count # 保存目标字数

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
                    # 如果前一章内容过长，只取前2000个字符
                    if len(previous_chapter_content) > 2000:
                        previous_chapter_content = previous_chapter_content[:2000] + "...(省略后续内容)"
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
        # 设置默认模型
        index = self.model_combo.findText(self.default_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        # 添加模型选择变更事件，保存选择的模型
        self.model_combo.currentIndexChanged.connect(self._save_selected_model)
        model_layout.addWidget(self.model_combo)

        # 温度设置已移除

        model_layout.addStretch()
        layout.addLayout(model_layout)

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

        self.use_button = QPushButton("使用结果")
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

    def _save_selected_model(self):
        """保存用户选择的模型"""
        if self.config_manager:
            selected_model = self.model_combo.currentText()
            # 确保 AI_DIALOG 部分存在
            if "AI_DIALOG" not in self.config_manager.config:
                self.config_manager.config["AI_DIALOG"] = {}
            # 保存选择的模型
            self.config_manager.config["AI_DIALOG"]["last_used_model"] = selected_model
            # 保存配置
            self.config_manager.save_config()

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
        model_text = self.model_combo.currentText().lower()
        # 转换为模型类型
        if model_text == "gpt":
            model_type = "gpt"
        elif model_text == "claude":
            model_type = "claude"
        elif model_text == "gemini":
            model_type = "gemini"
        elif model_text == "自定义openai":
            model_type = "custom_openai"
        elif model_text == "modelscope":
            model_type = "modelscope"
        elif model_text == "ollama": # 添加对Ollama的判断
            model_type = "ollama"
        else:
            # 如果下拉框里出现了这里没有处理的选项，显示错误
            QMessageBox.warning(self, "错误", f"无法识别的模型类型: {self.model_combo.currentText()}")
            return # 不继续执行生成
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
        self.findChild(QPushButton, "").setEnabled(True)

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
