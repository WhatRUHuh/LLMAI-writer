import json
import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QGroupBox, QFormLayout,
    QMessageBox, QSplitter, QListWidget, QListWidgetItem,
    QLineEdit, QSpinBox, QDialog, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot

from utils.async_utils import GenerationThread, ProgressIndicator
from ui.components import AIGenerateDialog

class CharacterDetailDialog(QDialog):
    """角色详情对话框"""

    def __init__(self, parent=None, character=None):
        super().__init__(parent)
        self.character = character or {}
        self.setWindowTitle("角色详情")
        self.resize(600, 500)
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()

        self.name_edit = QLineEdit(self.character.get("name", ""))
        basic_layout.addRow("姓名:", self.name_edit)

        self.identity_edit = QLineEdit(self.character.get("identity", ""))
        basic_layout.addRow("身份:", self.identity_edit)

        # 确保年龄是字符串类型
        age_value = self.character.get("age", "")
        if isinstance(age_value, int):
            age_value = str(age_value)
        self.age_edit = QLineEdit(age_value)
        basic_layout.addRow("年龄:", self.age_edit)

        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["男", "女", "其他"])
        if "gender" in self.character:
            index = self.gender_combo.findText(self.character["gender"])
            if index >= 0:
                self.gender_combo.setCurrentIndex(index)
        basic_layout.addRow("性别:", self.gender_combo)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # 详细信息
        detail_group = QGroupBox("详细信息")
        detail_layout = QFormLayout()

        self.personality_edit = QTextEdit(self.character.get("personality", ""))
        self.personality_edit.setMinimumHeight(80)
        detail_layout.addRow("性格特点:", self.personality_edit)

        self.background_edit = QTextEdit(self.character.get("background", ""))
        self.background_edit.setMinimumHeight(100)
        detail_layout.addRow("背景故事:", self.background_edit)

        self.appearance_edit = QTextEdit(self.character.get("appearance", ""))
        self.appearance_edit.setMinimumHeight(80)
        detail_layout.addRow("外貌描述:", self.appearance_edit)

        self.abilities_edit = QTextEdit(self.character.get("abilities", ""))
        self.abilities_edit.setMinimumHeight(80)
        detail_layout.addRow("能力特长:", self.abilities_edit)

        self.goals_edit = QTextEdit(self.character.get("goals", ""))
        self.goals_edit.setMinimumHeight(80)
        detail_layout.addRow("目标动机:", self.goals_edit)

        detail_group.setLayout(detail_layout)
        layout.addWidget(detail_group)

        # 按钮
        button_layout = QHBoxLayout()

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.accept)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def get_character_data(self):
        """获取角色数据"""
        return {
            "name": self.name_edit.text(),
            "identity": self.identity_edit.text(),
            "age": self.age_edit.text(),
            "gender": self.gender_combo.currentText(),
            "personality": self.personality_edit.toPlainText(),
            "background": self.background_edit.toPlainText(),
            "appearance": self.appearance_edit.toPlainText(),
            "abilities": self.abilities_edit.toPlainText(),
            "goals": self.goals_edit.toPlainText()
        }





class CharacterTab(QWidget):
    """人物编辑标签页"""

    def __init__(self, main_window):
        super().__init__()

        self.main_window = main_window
        # 获取ConfigManager实例
        self.config_manager = self.main_window.config_manager
        self.characters = []
        self.generation_thread = None

        # 初始化UI
        self._init_ui()

        # 加载角色数据
        self._load_characters()

        # 加载上次选择的AI模型
        self._load_last_selected_model()

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

        # 创建角色列表组
        character_group = QGroupBox("角色列表")
        character_layout = QVBoxLayout()

        self.character_list = QListWidget()
        self.character_list.currentRowChanged.connect(self.on_character_selected)
        character_layout.addWidget(self.character_list)

        # 创建角色操作按钮
        button_layout = QHBoxLayout()

        self.add_button = QPushButton("添加角色")
        self.add_button.clicked.connect(self.add_character)
        button_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("编辑角色")
        self.edit_button.clicked.connect(self.edit_character)
        self.edit_button.setEnabled(False)
        button_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("删除角色")
        self.delete_button.clicked.connect(self.delete_character)
        self.delete_button.setEnabled(False)
        button_layout.addWidget(self.delete_button)

        character_layout.addLayout(button_layout)

        # 创建AI生成按钮
        ai_button_layout = QHBoxLayout()

        self.generate_button = QPushButton("AI生成角色")
        self.generate_button.clicked.connect(self.generate_character)
        ai_button_layout.addWidget(self.generate_button)

        self.model_combo = QComboBox()
        # 动态获取可用的模型列表
        if hasattr(self, 'main_window') and self.main_window:
            available_models = self.main_window.get_available_models()
        else:
            # fallback to hardcoded list if main_window is not available
            available_models = ["GPT", "Claude", "Gemini", "自定义OpenAI", "ModelScope", "Ollama", "SiliconFlow"]
        self.model_combo.addItems(available_models)
        ai_button_layout.addWidget(self.model_combo)

        character_layout.addLayout(ai_button_layout)

        character_group.setLayout(character_layout)
        left_layout.addWidget(character_group)

        # 创建右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # 创建角色详情组
        detail_group = QGroupBox("角色详情")
        detail_layout = QVBoxLayout()

        self.detail_edit = QTextEdit()
        self.detail_edit.setReadOnly(True)
        detail_layout.addWidget(self.detail_edit)

        detail_group.setLayout(detail_layout)
        right_layout.addWidget(detail_group)

        # 添加面板到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        # 设置分割器比例
        splitter.setSizes([300, 700])

    def _load_last_selected_model(self):
        """加载上次选择的AI模型"""
        last_model = self.config_manager.get_last_selected_model()
        if last_model:
            # 查找模型在下拉框中的索引
            index = self.model_combo.findText(last_model)
            if index >= 0:
                # 如果找到，则设置为当前选中项
                self.model_combo.setCurrentIndex(index)
                # print(f"Loaded last selected model: {last_model}") # 调试信息，可以移除
            # else:
                # print(f"Last selected model '{last_model}' not found in combo box items.") # 调试信息，可以移除

    def _load_characters(self):
        """加载角色数据"""
        # 从主窗口获取大纲
        try:
            outline = self.main_window.get_outline()
            if outline and "characters" in outline:
                self.characters = outline["characters"]
                self._update_character_list()
        except (AttributeError, TypeError):
            # 如果大纲还没有初始化，则忽略错误
            pass

    def _update_character_list(self):
        """更新角色列表"""
        self.character_list.clear()
        for character in self.characters:
            name = character.get("name", "未命名角色")
            identity = character.get("identity", "")
            display_text = f"{name} - {identity}" if identity else name
            item = QListWidgetItem(display_text)
            self.character_list.addItem(item)

    def _update_character_detail(self, character):
        """更新角色详情"""
        if not character:
            self.detail_edit.clear()
            return

        detail_text = ""

        # 基本信息
        name = character.get("name", "")
        if name:
            detail_text += f"姓名: {name}\n"

        identity = character.get("identity", "")
        if identity:
            detail_text += f"身份: {identity}\n"

        age = character.get("age", "")
        if age:
            detail_text += f"年龄: {age}\n"

        gender = character.get("gender", "")
        if gender:
            detail_text += f"性别: {gender}\n"

        detail_text += "\n"

        # 详细信息
        personality = character.get("personality", "")
        if personality:
            detail_text += f"性格特点:\n{personality}\n\n"

        background = character.get("background", "")
        if background:
            detail_text += f"背景故事:\n{background}\n\n"

        appearance = character.get("appearance", "")
        if appearance:
            detail_text += f"外貌描述:\n{appearance}\n\n"

        abilities = character.get("abilities", "")
        if abilities:
            detail_text += f"能力特长:\n{abilities}\n\n"

        goals = character.get("goals", "")
        if goals:
            detail_text += f"目标动机:\n{goals}\n\n"

        self.detail_edit.setPlainText(detail_text)

    def on_character_selected(self, row):
        """角色选择事件处理"""
        if row < 0 or row >= len(self.characters):
            self.edit_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self._update_character_detail(None)
            return

        self.edit_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self._update_character_detail(self.characters[row])

    def add_character(self):
        """添加角色"""
        dialog = CharacterDetailDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            character = dialog.get_character_data()
            self.characters.append(character)
            self._update_character_list()
            self._save_characters()

    def edit_character(self):
        """编辑角色"""
        row = self.character_list.currentRow()
        if row < 0 or row >= len(self.characters):
            return

        dialog = CharacterDetailDialog(self, self.characters[row])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.characters[row] = dialog.get_character_data()
            self._update_character_list()
            self._update_character_detail(self.characters[row])
            self._save_characters()

    def delete_character(self):
        """删除角色"""
        row = self.character_list.currentRow()
        if row < 0 or row >= len(self.characters):
            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除角色 '{self.characters[row].get('name', '未命名角色')}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.characters[row]
            self._update_character_list()
            self._save_characters()

    def generate_character(self):
        """AI生成角色"""
        # 创建对话框获取角色类型和基本信息
        dialog = QDialog(self)
        dialog.setWindowTitle("AI生成角色")
        dialog.resize(400, 300)

        layout = QVBoxLayout(dialog)

        # 角色类型
        type_group = QGroupBox("角色类型")
        type_layout = QFormLayout()

        character_type_combo = QComboBox()
        character_type_combo.addItems(["主角", "反派", "配角", "龙套"])
        type_layout.addRow("角色类型:", character_type_combo)

        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # 基本信息
        info_group = QGroupBox("基本信息")
        info_layout = QFormLayout()

        name_edit = QLineEdit()
        info_layout.addRow("姓名 (可选):", name_edit)

        gender_combo = QComboBox()
        gender_combo.addItems(["随机", "男", "女", "其他"])
        info_layout.addRow("性别:", gender_combo)

        age_edit = QLineEdit()
        info_layout.addRow("年龄 (可选):", age_edit)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 角色描述
        desc_group = QGroupBox("角色描述 (可选)")
        desc_layout = QVBoxLayout()

        desc_edit = QTextEdit()
        desc_layout.addWidget(desc_edit)

        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)

        # 按钮
        button_layout = QHBoxLayout()

        generate_button = QPushButton("生成")
        generate_button.clicked.connect(dialog.accept)
        button_layout.addWidget(generate_button)

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        # 显示对话框
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # 获取输入
        character_type = character_type_combo.currentText()
        name = name_edit.text().strip()
        gender = gender_combo.currentText()
        age = age_edit.text().strip()
        description = desc_edit.toPlainText().strip()

        # 获取总大纲信息
        outline = self.main_window.get_outline()
        outline_info = ""
        if outline:
            if outline.get("title"):
                outline_info += f"小说标题：{outline.get('title')}\n"
            if outline.get("theme"):
                outline_info += f"中心思想：{outline.get('theme')}\n"
            if outline.get("synopsis"):
                outline_info += f"故事梦概：{outline.get('synopsis')}\n"
            if outline.get("worldbuilding"):
                outline_info += f"世界观设定：{outline.get('worldbuilding')}\n"

        # 构建提示词
        prompt = f"""
        请为我生成一个详细的角色设定，角色类型为{character_type}。

        """

        # 添加总大纲信息（如果有）
        if outline_info:
            prompt += f"""
            小说信息：
            {outline_info}
            """

        if name:
            prompt += f"角色姓名: {name}\n"

        if gender != "随机":
            prompt += f"角色性别: {gender}\n"

        if age:
            prompt += f"角色年龄: {age}\n"

        if description:
            prompt += f"""
            其他描述:
            {description}
            """

        prompt += """
        请以JSON格式返回角色设定，包含以下字段:
        - name: 角色姓名
        - identity: 角色身份
        - age: 角色年龄
        - gender: 角色性别
        - personality: 性格特点（详细描述）
        - background: 背景故事（详细描述）
        - appearance: 外貌描述（详细描述）
        - abilities: 能力特长（详细描述）
        - goals: 目标动机（详细描述）

        请确保生成的角色设定丰富、合理、有深度，并且符合角色类型的特点。
        请确保角色设定与小说的整体设定保持一致。
        只返回JSON格式的内容，不要包含其他解释或说明。
        """

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
        elif model_text == "ollama":
            model_type = "ollama"
        elif model_text == "siliconflow": # 添加 SiliconFlow 处理
            model_type = "siliconflow"
        elif model_text in self.main_window.custom_openai_models: # 处理多个自定义模型
             model_type = model_text # 直接返回模型名称作为类型
        else:
            # 如果列表为空或选中的不在已知类型中，尝试返回第一个可用的
            if self.main_window.has_gpt: model_type = "gpt"
            elif self.main_window.has_claude: model_type = "claude"
            elif self.main_window.has_gemini: model_type = "gemini"
            elif self.main_window.has_custom_openai: model_type = "custom_openai"
            elif self.main_window.has_modelscope: model_type = "modelscope"
            elif self.main_window.has_ollama: model_type = "ollama"
            elif self.main_window.has_siliconflow: model_type = "siliconflow"
            elif self.main_window.custom_openai_models: model_type = list(self.main_window.custom_openai_models.keys())[0]
            else:
                 QMessageBox.warning(self, "模型错误", "没有可用的AI模型")
                 return # 没有可用模型，直接返回

        try:
            model = self.main_window.get_model(model_type)
        except ValueError as e:
            QMessageBox.warning(self, "模型错误", str(e))
            return

        # 创建生成对话框
        generation_dialog = QDialog(self)
        generation_dialog.setWindowTitle("生成中...")
        generation_dialog.resize(600, 400)

        gen_layout = QVBoxLayout(generation_dialog)

        output_edit = QTextEdit()
        output_edit.setReadOnly(True)
        gen_layout.addWidget(output_edit)

        # 添加进度条
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 0)  # 设置为不确定模式
        gen_layout.addWidget(progress_bar)

        # 创建并启动生成线程
        self.generation_thread = GenerationThread(
            model.generate_stream,
            (prompt,),
            {}
        )

        # 连接信号
        self.generation_thread.progress_signal.connect(
            lambda chunk: output_edit.insertPlainText(chunk)
        )

        self.generation_thread.finished_signal.connect(
            lambda result: self._on_generation_finished(result, generation_dialog)
        )

        self.generation_thread.error_signal.connect(
            lambda error: self._on_generation_error(error, generation_dialog)
        )

        # 启动线程
        self.generation_thread.start()

        # 显示生成对话框
        generation_dialog.exec()

    def _on_generation_finished(self, result, dialog):
        """生成完成事件处理"""
        dialog.accept()

        # 如果结果是字符串，尝试解析JSON
        if isinstance(result, str):
            try:
                # 尝试提取JSON部分
                json_start = result.find('{')
                json_end = result.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = result[json_start:json_end]
                    result = json.loads(json_text)
                else:
                    result = {"error": "无法解析响应", "raw_response": result}
            except json.JSONDecodeError:
                result = {"error": "无法解析JSON", "raw_response": result}

        if "error" in result:
            QMessageBox.warning(self, "生成失败", f"生成角色失败: {result['error']}")
            return

        # 添加生成的角色
        self.characters.append(result)
        self._update_character_list()
        self._save_characters()

        # 保存当前选择的AI模型
        selected_model_name = self.model_combo.currentText()
        self.config_manager.save_last_selected_model(selected_model_name)

        # 选中新角色
        self.character_list.setCurrentRow(len(self.characters) - 1)

        QMessageBox.information(self, "生成成功", f"成功生成角色: {result.get('name', '未命名角色')}")

    def _on_generation_error(self, error, dialog):
        """生成错误事件处理"""
        dialog.reject()
        QMessageBox.warning(self, "生成失败", f"生成角色时出错: {error}")

    def _save_characters(self):
        """保存角色数据"""
        try:
            # 获取当前大纲
            outline = self.main_window.get_outline()
            if not outline:
                # 如果大纲为None，创建一个新的大纲
                outline = {
                    "title": "",
                    "theme": "",
                    "characters": [],
                    "synopsis": "",
                    "volumes": [],
                    "worldbuilding": ""
                }

            # 更新角色数据
            outline["characters"] = self.characters

            # 保存大纲
            self.main_window.set_outline(outline)
        except Exception as e:
            print(f"保存角色数据时出错: {e}")

    def update_characters(self):
        """更新角色数据（供外部调用）"""
        try:
            self._load_characters()
        except Exception as e:
            print(f"更新角色数据时出错: {e}")