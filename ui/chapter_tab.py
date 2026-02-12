from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QComboBox, QGroupBox, QFormLayout, QLineEdit, QLabel,
    QMessageBox, QSplitter, QListWidget, QListWidgetItem,
    QDialog
)
from PyQt6.QtCore import Qt

from ui.components import AIGenerateDialog


class ChapterTab(QWidget):
    """章节生成标签页"""

    def __init__(self, main_window):
        super().__init__()

        self.main_window = main_window
        self.chapter_generator = None
        self.generation_thread = None
        self.outline = None
        self.current_volume_index = -1
        self.current_chapter_index = -1

        self.selected_characters_for_chapter = [] # 用于存储当前章节选定的角色

        # 初始化UI
        self._init_ui()

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

        # 创建卷选择组 (删除了之前的模型选择组)
        volume_group = QGroupBox("卷选择")
        volume_layout = QVBoxLayout()

        self.volume_list = QListWidget()
        self.volume_list.currentRowChanged.connect(self.on_volume_selected)
        volume_layout.addWidget(self.volume_list)

        volume_group.setLayout(volume_layout)
        left_layout.addWidget(volume_group)

        # 创建章节选择组
        chapter_group = QGroupBox("章节选择")
        chapter_layout = QVBoxLayout()

        self.chapter_list = QListWidget()
        self.chapter_list.currentRowChanged.connect(self.on_chapter_selected)
        chapter_layout.addWidget(self.chapter_list)

        chapter_group.setLayout(chapter_layout)
        left_layout.addWidget(chapter_group)

        # 创建操作按钮组
        button_group = QGroupBox("操作")
        button_layout = QVBoxLayout()

        # 生成章节按钮已移除，使用AI辅助编辑按钮替代

        self.save_button = QPushButton("保存章节")
        self.save_button.setProperty("primary", True)  # 设置为主要按钮
        self.save_button.clicked.connect(self.save_chapter)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)

        button_group.setLayout(button_layout)
        left_layout.addWidget(button_group)

        # 添加弹性空间
        left_layout.addStretch()

        # 创建右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # 创建章节信息组
        info_group = QGroupBox("章节信息")
        info_layout = QVBoxLayout()

        self.info_edit = QTextEdit()
        self.info_edit.setReadOnly(False)  # 设置为可编辑
        info_layout.addWidget(self.info_edit)

        info_group.setLayout(info_layout)
        right_layout.addWidget(info_group)
        info_group.setFixedHeight(300)

        # 创建输出区域
        output_group = QGroupBox("章节内容")
        output_layout = QVBoxLayout()

        self.output_edit = QTextEdit()
        # 连接信号，以便在选择文本时启用/禁用润色按钮
        self.output_edit.selectionChanged.connect(self._update_polish_button_state)
        output_layout.addWidget(self.output_edit)

        # 添加AI生成按钮和选择角色按钮
        ai_button_layout = QHBoxLayout()

        # 添加选择角色按钮
        self.select_characters_button = QPushButton("选择角色")
        self.select_characters_button.clicked.connect(self._select_characters)
        self.select_characters_button.setEnabled(False) # 初始禁用
        ai_button_layout.addWidget(self.select_characters_button)

        # 添加字数输入框和确认按钮
        ai_button_layout.addWidget(QLabel("目标字数:"))
        self.word_count_input = QLineEdit()
        self.word_count_input.setPlaceholderText("选填")
        self.word_count_input.setFixedWidth(60) # 固定宽度
        ai_button_layout.addWidget(self.word_count_input)
        # 确认按钮暂时不需要，直接在生成时读取输入框内容
        # self.confirm_word_count_button = QPushButton("确认字数")
        # self.confirm_word_count_button.clicked.connect(self._confirm_word_count) # 需要实现 _confirm_word_count 方法
        # ai_button_layout.addWidget(self.confirm_word_count_button)

        self.ai_generate_button = QPushButton("AI辅助编辑")
        self.ai_generate_button.clicked.connect(self._generate_with_ai)
        self.ai_generate_button.setEnabled(False)
        ai_button_layout.addWidget(self.ai_generate_button)

        # 添加选定文本润色按钮
        self.polish_button = QPushButton("选定文本润色")
        self.polish_button.clicked.connect(self._polish_selected_text)
        self.polish_button.setEnabled(False) # 初始禁用
        ai_button_layout.addWidget(self.polish_button)


        ai_button_layout.addStretch()
        output_layout.addLayout(ai_button_layout)

        # 进度条已移除，使用AI生成对话框中的进度条

        output_group.setLayout(output_layout)
        right_layout.addWidget(output_group)

        # 添加面板到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        # 设置分割器比例
        splitter.setSizes([300, 700])

    def update_outline(self, outline):
        """更新大纲"""
        self.outline = outline

        # 清空卷列表
        self.volume_list.clear()

        # 添加卷
        if outline and "volumes" in outline:
            for i, volume in enumerate(outline["volumes"]):
                title = volume.get("title", f"第{i+1}卷")
                item = QListWidgetItem(title)
                item.setData(Qt.ItemDataRole.UserRole, i)
                self.volume_list.addItem(item)

    def on_volume_selected(self, row):
        """卷选择事件处理"""
        if row < 0:
            return

        self.current_volume_index = row

        # 清空章节列表
        self.chapter_list.clear()

        # 添加章节
        if self.outline and "volumes" in self.outline and row < len(self.outline["volumes"]):
            volume = self.outline["volumes"][row]
            if "chapters" in volume:
                for i, chapter in enumerate(volume["chapters"]):
                    title = chapter.get("title", f"第{i+1}章")
                    item = QListWidgetItem(title)
                    item.setData(Qt.ItemDataRole.UserRole, i)
                    self.chapter_list.addItem(item)

    def on_chapter_selected(self, row):
        """章节选择事件处理"""
        if row < 0 or self.current_volume_index < 0:
            return

        self.current_chapter_index = row

        # 更新章节信息
        if (self.outline and "volumes" in self.outline and
            self.current_volume_index < len(self.outline["volumes"])):

            volume = self.outline["volumes"][self.current_volume_index]
            if "chapters" in volume and row < len(volume["chapters"]):
                chapter = volume["chapters"][row]
                title = chapter.get("title", f"第{row+1}章")
                summary = chapter.get("summary", "")

                self.info_edit.setText(f"标题: {title}\n\n摘要: {summary}")

                # 加载章节内容（如果有）
                content = self.main_window.get_chapter(self.current_volume_index, row)
                if content:
                    self.output_edit.setPlainText(content)
                else:
                    self.output_edit.clear()

                # 生成按钮已移除

                # 启用AI辅助编辑按钮和选择角色按钮
                self.ai_generate_button.setEnabled(True)
                self.select_characters_button.setEnabled(True)

                # 如果有内容，启用保存按钮
                self.save_button.setEnabled(bool(self.output_edit.toPlainText()))
                # 更新润色按钮状态
                self._update_polish_button_state()


    def _update_polish_button_state(self):
        """根据是否有选中文本更新润色按钮状态"""
        has_selection = self.output_edit.textCursor().hasSelection()
        # 只有在章节被选中且有文本被选中时才启用
        can_polish = self.current_volume_index >= 0 and self.current_chapter_index >= 0 and has_selection
        self.polish_button.setEnabled(can_polish)


    # _get_model_type 方法已不再需要，因为模型选择在 AIGenerateDialog 中进行
    # 因此整个函数都被注释掉了
    # def _get_model_type(self):
    #     """获取选择的模型类型"""
    #     # model_text = self.model_combo.currentText().lower() # 这行代码引用了已删除的 model_combo，需要删除
    #     if model_text == "gpt":
    #         return "gpt"
    #     elif model_text == "claude":
    #         return "claude"
    #     elif model_text == "gemini":
    #         return "gemini"
    #     elif model_text == "自定义openai":
    #         return "custom_openai"
    #     elif model_text == "modelscope":
    #         return "modelscope"
    #     elif model_text == "ollama":
    #          return "ollama"
    #     elif model_text == "siliconflow": # 添加 SiliconFlow 处理
    #          return "siliconflow"
    #     elif model_text in self.main_window.custom_openai_models: # 处理多个自定义模型
    #          return model_text # 直接返回模型名称作为类型
    #     else:
    #         # 如果列表为空或选中的不在已知类型中，尝试返回第一个可用的
    #         if self.main_window.has_gpt: return "gpt"
    #         if self.main_window.has_claude: return "claude"
    #         if self.main_window.has_gemini: return "gemini"
    #         if self.main_window.has_custom_openai: return "custom_openai"
    #         if self.main_window.has_modelscope: return "modelscope"
    #         if self.main_window.has_ollama: return "ollama"
    #         if self.main_window.has_siliconflow: return "siliconflow"
    #         if self.main_window.custom_openai_models: return list(self.main_window.custom_openai_models.keys())[0]
    #         raise ValueError("没有可用的AI模型") # 如果真的一个都没有

    def _stream_callback(self, chunk):
        """流式生成回调函数"""
        self.output_edit.insertPlainText(chunk)
        # 滚动到底部
        scrollbar = self.output_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # 生成章节相关的信号处理方法已移除，使用 _generate_with_ai 方法替代

    # generate_chapter 方法已移除，使用 _generate_with_ai 方法替代

    def save_chapter(self, show_message=True):
        """保存章节

        Args:
            show_message: 是否显示消息对话框
        """
        if self.current_volume_index < 0 or self.current_chapter_index < 0:
            if show_message:
                QMessageBox.warning(self, "保存失败", "请先选择一个章节")
            return

        # 获取章节内容
        content = self.output_edit.toPlainText()
        if not content:
            if show_message:
                QMessageBox.warning(self, "保存失败", "章节内容为空")
            return

        # 保存章节内容
        self.main_window.set_chapter(self.current_volume_index, self.current_chapter_index, content)

        # 显示成功消息
        if show_message:
            QMessageBox.information(self, "保存成功", "章节已保存")

        # 启用保存按钮
        self.save_button.setEnabled(True)

    def _select_characters(self):
        """选择章节出场角色"""
        if self.current_volume_index < 0 or self.current_chapter_index < 0:
            QMessageBox.warning(self, "提示", "请先选择一个章节")
            return

        if not self.outline or "characters" not in self.outline or not self.outline["characters"]:
            QMessageBox.warning(self, "提示", "当前小说没有角色数据，请先在人物编辑标签页添加角色。")
            return

        # 获取当前章节的已选角色（如果有）
        # selected_characters = [] # 不再需要局部变量
        volumes = self.outline.get("volumes", [])
        if self.current_volume_index < len(volumes):
            volume = volumes[self.current_volume_index]
            chapters = volume.get("chapters", [])
            if self.current_chapter_index < len(chapters):
                chapter = chapters[self.current_chapter_index]
                self.selected_characters_for_chapter = chapter.get("characters", []) # 加载已选角色到成员变量

        # 获取所有角色
        all_characters = self.outline["characters"]

        # 创建角色选择对话框
        from ui.character_selector_dialog import CharacterSelectorDialog
        # 传入已选角色
        dialog = CharacterSelectorDialog(self, all_characters, self.selected_characters_for_chapter)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 获取选中的角色
            self.selected_characters_for_chapter = dialog.get_selected_characters()

            # 保存选中的角色到当前章节的 outline 数据中
            volumes = self.outline.get("volumes", [])
            if self.current_volume_index < len(volumes):
                volume = volumes[self.current_volume_index]
                chapters = volume.get("chapters", [])
                if self.current_chapter_index < len(chapters):
                    chapter = chapters[self.current_chapter_index]
                    # 将选中的角色名字列表存入 chapter 字典
                    chapter["characters"] = self.selected_characters_for_chapter

                    # 更新大纲
                    self.main_window.set_outline(self.outline)
                    self.main_window.status_bar_manager.show_message(f"已为章节设置{len(self.selected_characters_for_chapter)}个出场角色")

    def _generate_with_ai(self):
        """使用AI生成内容"""
        if self.current_volume_index < 0 or self.current_chapter_index < 0:
            QMessageBox.warning(self, "生成失败", "请先选择一个章节")
            return

        # 获取总大纲信息
        outline_info = {}
        if self.outline:
            outline_info = {
                "title": self.outline.get("title", ""),
                "theme": self.outline.get("theme", ""),
                "synopsis": self.outline.get("synopsis", ""),
                "worldbuilding": self.outline.get("worldbuilding", "")
            }

        # 获取上下文信息
        context_info = {}
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
                context_info["chapter_summary"] = chapter.get("summary", "") # 把摘要加上了！看你还漏不漏！

                # 添加章节出场角色信息 (使用 self.selected_characters_for_chapter)
                # chapter_characters = chapter.get("characters", []) # 从 outline 获取
                if self.selected_characters_for_chapter:
                    context_info["chapter_characters"] = self.selected_characters_for_chapter

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

                # 添加前一章的内容
                if self.current_chapter_index > 0:
                    prev_chapter_index = self.current_chapter_index - 1
                    prev_chapter_content = self.main_window.get_chapter(self.current_volume_index, prev_chapter_index)
                    if prev_chapter_content:
                        context_info["previous_chapter_content"] = prev_chapter_content

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

        # 获取当前章节信息
        current_text = self.output_edit.toPlainText()
        chapter_info = self.info_edit.toPlainText()

        # 获取目标字数
        target_word_count_str = self.word_count_input.text().strip()
        target_word_count = None
        if target_word_count_str.isdigit():
            target_word_count = int(target_word_count_str)
        elif target_word_count_str: # 如果输入了但不是数字，给个提示
             QMessageBox.warning(self, "提示", "目标字数请输入有效的数字。")
             # 可以选择在这里 return，或者继续生成但不带字数要求

        dialog = AIGenerateDialog(
            self,
            "AI生成章节内容",
            "章节内容",
            current_text,
            # 动态获取可用的模型列表
            models=self.main_window.get_available_models(),
            # default_model="GPT", # 不再需要传递默认模型，让对话框自己处理
            outline_info=outline_info,
            context_info=context_info,
            prompt_manager=self.main_window.prompt_manager,
            target_word_count=target_word_count, # 传递目标字数
            # 新增：传递知识库管理器和可用知识库列表
            knowledge_base_manager=self.main_window.get_knowledge_base_manager(),
            available_knowledge_bases=self.main_window.get_available_knowledge_bases(),
            config_manager=self.main_window.config_manager # 哼，把配置管理器也给它安排上！
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            result = dialog.get_result()
            if result:
                self.output_edit.setPlainText(result)
                self.save_button.setEnabled(True)
                # 在使用AI生成结果后自动保存
                self.save_chapter(show_message=False)
                # 显示状态栏消息
                self.main_window.status_bar_manager.show_message("已使用AI生成结果并保存")


    def _polish_selected_text(self):
        """使用AI润色选定的文本"""
        if self.current_volume_index < 0 or self.current_chapter_index < 0:
            QMessageBox.warning(self, "润色失败", "请先选择一个章节")
            return

        cursor = self.output_edit.textCursor()
        if not cursor.hasSelection():
            QMessageBox.warning(self, "润色失败", "请先在章节内容中选定需要润色的文本")
            return

        selected_text = cursor.selectedText()
        full_text = self.output_edit.toPlainText()

        # 获取总大纲信息 (与 _generate_with_ai 类似)
        outline_info = {}
        if self.outline:
            outline_info = {
                "title": self.outline.get("title", ""),
                "theme": self.outline.get("theme", ""),
                "synopsis": self.outline.get("synopsis", ""),
                "worldbuilding": self.outline.get("worldbuilding", "")
            }

        # 获取上下文信息 (与 _generate_with_ai 类似)
        context_info = {}
        volumes = self.outline.get("volumes", [])
        if self.current_volume_index < len(volumes):
            volume = volumes[self.current_volume_index]
            context_info["volume_title"] = volume.get("title", "")
            context_info["volume_description"] = volume.get("description", "")

            chapters = volume.get("chapters", [])
            if self.current_chapter_index < len(chapters):
                chapter = chapters[self.current_chapter_index]
                context_info["chapter_title"] = chapter.get("title", "")
                context_info["chapter_number"] = self.current_chapter_index + 1 # 修正变量名
                # 使用 self.selected_characters_for_chapter
                if self.selected_characters_for_chapter:
                    context_info["chapter_characters"] = self.selected_characters_for_chapter
                previous_chapters = []
                start_idx = max(0, self.current_chapter_index - 10)
                for i in range(start_idx, self.current_chapter_index):
                    if i < len(chapters):
                        prev_chapter = chapters[i]
                        previous_chapters.append({"title": prev_chapter.get("title", ""),"summary": prev_chapter.get("summary", "")})
                context_info["previous_chapters"] = previous_chapters
                if self.current_chapter_index > 0:
                    prev_chapter_index = self.current_chapter_index - 1
                    prev_chapter_content = self.main_window.get_chapter(self.current_volume_index, prev_chapter_index)
                    if prev_chapter_content:
                        context_info["previous_chapter_content"] = prev_chapter_content
                next_chapters = []
                end_idx = min(len(chapters), self.current_chapter_index + 4)
                for i in range(self.current_chapter_index + 1, end_idx):
                     if i < len(chapters):
                        next_chapter = chapters[i]
                        next_chapters.append({"title": next_chapter.get("title", ""),"summary": next_chapter.get("summary", "")})
                context_info["next_chapters"] = next_chapters


        # 获取目标字数 (润色时也可能需要，虽然通常润色不限制字数，但保留逻辑)
        target_word_count_str = self.word_count_input.text().strip()
        target_word_count = None
        if target_word_count_str.isdigit():
            target_word_count = int(target_word_count_str)
        elif target_word_count_str:
             QMessageBox.warning(self, "提示", "目标字数请输入有效的数字。")


        # 调用修改后的 AIGenerateDialog
        dialog = AIGenerateDialog(
            self,
            "AI文本润色",
            "润色结果",
            "", # 初始文本为空，因为我们要在prompt里提供上下文
            models=self.main_window.get_available_models(), # 动态获取可用的模型列表
            # default_model="GPT", # 不再需要传递默认模型
            outline_info=outline_info,
            context_info=context_info,
            prompt_manager=self.main_window.prompt_manager,
            # 传递新参数
            task_type="polish",
            selected_text=selected_text,
            full_text=full_text,
            target_word_count=target_word_count, # 传递目标字数
            # 新增：传递知识库管理器和可用知识库列表
            knowledge_base_manager=self.main_window.get_knowledge_base_manager(),
            available_knowledge_bases=self.main_window.get_available_knowledge_bases(),
            config_manager=self.main_window.config_manager # 哼，这里也一样，不能漏了！
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            polished_result = dialog.get_result()
            if polished_result:
                # 替换选定的文本
                cursor.insertText(polished_result)
                # 更新状态栏和保存按钮
                self.save_button.setEnabled(True)
                self.main_window.status_bar_manager.show_message("选定文本已润色")
                # 可以选择自动保存
                # self.save_chapter(show_message=False)

