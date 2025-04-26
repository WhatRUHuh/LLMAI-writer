import os
import configparser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QFormLayout, QCheckBox,
    QMessageBox, QSpinBox, QComboBox, QDoubleSpinBox,
    QInputDialog, QDialog, QScrollArea
)
from PyQt6.QtCore import Qt

class SettingsTab(QWidget):
    """设置标签页"""

    def __init__(self, main_window):
        super().__init__()

        self.main_window = main_window
        self.config_manager = main_window.config_manager

        # 初始化UI
        self._init_ui()

        # 加载配置
        self._load_config()

    def _init_ui(self):
        """初始化UI"""
        # 创建主布局
        outer_layout = QVBoxLayout(self)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)  # 移除边框

        # 创建内容widget
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)

        # 创建代理设置组
        proxy_group = QGroupBox("代理设置")
        proxy_layout = QFormLayout()

        self.proxy_enabled = QCheckBox("启用代理")
        proxy_layout.addRow("", self.proxy_enabled)

        self.proxy_host = QLineEdit()
        proxy_layout.addRow("代理主机:", self.proxy_host)

        self.proxy_port = QSpinBox()
        self.proxy_port.setRange(1, 65535)
        self.proxy_port.setValue(10808)
        proxy_layout.addRow("代理端口:", self.proxy_port)

        proxy_group.setLayout(proxy_layout)
        main_layout.addWidget(proxy_group)

        # 创建API密钥设置组
        api_group = QGroupBox("API密钥设置")
        api_layout = QFormLayout()

        self.gpt_api_key = QLineEdit()
        self.gpt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("OpenAI API密钥:", self.gpt_api_key)

        self.claude_api_key = QLineEdit()
        self.claude_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("Anthropic API密钥:", self.claude_api_key)

        self.gemini_api_key = QLineEdit()
        self.gemini_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("Google API密钥:", self.gemini_api_key)

        # 自定义OpenAI API密钥已移至自定义OpenAI兼容API设置组

        # 添加ModelScope API密钥
        self.modelscope_api_key = QLineEdit()
        self.modelscope_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("ModelScope API密钥:", self.modelscope_api_key)

        # 添加 SiliconFlow API密钥
        self.siliconflow_api_key = QLineEdit()
        self.siliconflow_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("SiliconFlow API密钥:", self.siliconflow_api_key)

        api_group.setLayout(api_layout)

        main_layout.addWidget(api_group)

        # 创建模型设置组
        model_group = QGroupBox("模型设置")
        model_layout = QFormLayout()

        self.gpt_model = QLineEdit()
        model_layout.addRow("GPT模型:", self.gpt_model)

        self.claude_model = QLineEdit()
        model_layout.addRow("Claude模型:", self.claude_model)

        self.gemini_model = QLineEdit()
        model_layout.addRow("Gemini模型:", self.gemini_model)

        # 自定义OpenAI模型已移至自定义OpenAI兼容API设置组

        # 添加ModelScope模型
        self.modelscope_model = QLineEdit()
        model_layout.addRow("ModelScope模型:", self.modelscope_model)

        # 添加Ollama模型
        self.ollama_model = QLineEdit()
        model_layout.addRow("Ollama模型:", self.ollama_model)

        # 添加 SiliconFlow 模型
        self.siliconflow_model = QLineEdit()
        model_layout.addRow("SiliconFlow模型:", self.siliconflow_model)

        model_group.setLayout(model_layout)

        main_layout.addWidget(model_group)

        # 创建自定义OpenAI API设置组
        custom_openai_group = QGroupBox("自定义OpenAI兼容API设置")
        custom_openai_layout = QFormLayout()

        # 移除启用复选框，默认启用自定义OpenAI兼容API

        # 添加API密钥、模型名称和URL输入框
        self.custom_openai_api_key = QLineEdit()
        self.custom_openai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        custom_openai_layout.addRow("API密钥:", self.custom_openai_api_key)

        self.custom_openai_model = QLineEdit()
        custom_openai_layout.addRow("模型名称:", self.custom_openai_model)

        self.custom_openai_url = QLineEdit()
        self.custom_openai_url.setPlaceholderText("https://your-custom-api-endpoint.com/v1/chat/completions")
        custom_openai_layout.addRow("API地址:", self.custom_openai_url)

        custom_openai_group.setLayout(custom_openai_layout)

        main_layout.addWidget(custom_openai_group)

        # 添加Ollama API设置组
        ollama_group = QGroupBox("Ollama本地模型设置")
        ollama_layout = QFormLayout()

        self.ollama_url = QLineEdit()
        self.ollama_url.setPlaceholderText("http://localhost:11434/api/chat")
        ollama_layout.addRow("API地址:", self.ollama_url)

        ollama_group.setLayout(ollama_layout)

        main_layout.addWidget(ollama_group)

        # 创建自定义模型管理组
        custom_models_group = QGroupBox("自定义模型管理")
        custom_models_layout = QVBoxLayout()

        # 添加自定义模型选择下拉框
        model_selection_layout = QHBoxLayout()
        model_selection_layout.addWidget(QLabel("选择模型:"))

        self.custom_model_combo = QComboBox()
        self.custom_model_combo.addItem("选择自定义模型")
        self.custom_model_combo.currentIndexChanged.connect(self._on_custom_model_selected)
        model_selection_layout.addWidget(self.custom_model_combo)

        custom_models_layout.addLayout(model_selection_layout)

        # 添加按钮布局
        buttons_layout = QHBoxLayout()

        self.add_model_button = QPushButton("添加模型")
        self.add_model_button.clicked.connect(self._add_custom_model)
        buttons_layout.addWidget(self.add_model_button)

        self.edit_model_button = QPushButton("编辑模型")
        self.edit_model_button.clicked.connect(self._edit_custom_model)
        self.edit_model_button.setEnabled(False)
        buttons_layout.addWidget(self.edit_model_button)

        self.delete_model_button = QPushButton("删除模型")
        self.delete_model_button.clicked.connect(self._delete_custom_model)
        self.delete_model_button.setEnabled(False)
        buttons_layout.addWidget(self.delete_model_button)

        custom_models_layout.addLayout(buttons_layout)

        custom_models_group.setLayout(custom_models_layout)
        main_layout.addWidget(custom_models_group)

        # ModelScope API设置已在代码中配置好，不需要在UI中显示

        # 创建按钮布局
        button_layout = QHBoxLayout()

        self.save_button = QPushButton("保存设置")
        self.save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_button)

        self.reset_button = QPushButton("重置设置")
        self.reset_button.clicked.connect(self._load_config)
        button_layout.addWidget(self.reset_button)

        main_layout.addLayout(button_layout)

        # 添加弹性空间
        main_layout.addStretch()

        # 设置滚动区域的内容
        scroll_area.setWidget(content_widget)

        # 添加滚动区域到外层布局
        outer_layout.addWidget(scroll_area)

    def _load_config(self):
        """加载配置"""
        config = self.config_manager.config

        # 加载代理设置
        if "PROXY" in config:
            proxy_config = config["PROXY"]
            self.proxy_enabled.setChecked(proxy_config.getboolean("enabled", False))
            self.proxy_host.setText(proxy_config.get("host", "127.0.0.1"))
            self.proxy_port.setValue(proxy_config.getint("port", 10808))

        # 加载API密钥设置
        if "API_KEYS" in config:
            api_config = config["API_KEYS"]
            self.gpt_api_key.setText(api_config.get("gpt_api_key", ""))
            self.claude_api_key.setText(api_config.get("claude_api_key", ""))
            self.gemini_api_key.setText(api_config.get("gemini_api_key", ""))
            self.custom_openai_api_key.setText(api_config.get("custom_openai_api_key", ""))
            self.modelscope_api_key.setText(api_config.get("modelscope_api_key", ""))
            self.siliconflow_api_key.setText(api_config.get("siliconflow_api_key", "")) # 加载 SiliconFlow API Key

        # 加载模型设置
        if "MODELS" in config:
            model_config = config["MODELS"]
            self.gpt_model.setText(model_config.get("gpt_model", "gpt-4-turbo"))
            self.claude_model.setText(model_config.get("claude_model", "claude-3-opus-20240229"))
            self.gemini_model.setText(model_config.get("gemini_model", "gemini-2.0-flash"))
            # self.custom_openai_model已移至自定义OpenAI兼容API设置组
            self.modelscope_model.setText(model_config.get("modelscope_model", "deepseek-ai/DeepSeek-R1"))
            self.ollama_model.setText(model_config.get("ollama_model", "llama3.2"))
            self.siliconflow_model.setText(model_config.get("siliconflow_model", "deepseek-ai/DeepSeek-R1")) # 加载 SiliconFlow 模型

        # 加载自定义OpenAI API设置
        if "CUSTOM_OPENAI" in config:
            custom_openai_config = config["CUSTOM_OPENAI"]
            # 自定义OpenAI API始终启用，不需要复选框
            self.custom_openai_url.setText(custom_openai_config.get("api_url", ""))

        # 加载自定义OpenAI API密钥和模型名称
        if "API_KEYS" in config and "MODELS" in config:
            # 在自定义OpenAI兼容API设置组中显示
            self.custom_openai_api_key.setText(config["API_KEYS"].get("custom_openai_api_key", ""))
            self.custom_openai_model.setText(config["MODELS"].get("custom_openai_model", ""))

        # 加载自定义模型列表
        self.custom_model_combo.clear()
        self.custom_model_combo.addItem("选择自定义模型")

        models = self.config_manager.get_custom_openai_models()
        for model in models:
            model_name = model.get('name')
            if model_name:
                self.custom_model_combo.addItem(model_name)

        # 禁用编辑和删除按钮
        self.edit_model_button.setEnabled(False)
        self.delete_model_button.setEnabled(False)

        # ModelScope API设置已在代码中配置好，不需要在UI中显示

        # 加载Ollama API设置
        if "OLLAMA" in config:
            ollama_config = config["OLLAMA"]
            self.ollama_url.setText(ollama_config.get("api_url", "http://localhost:11434/api/chat"))

    def save_settings(self):
        """保存设置"""
        config = self.config_manager.config

        # 保存代理设置
        if "PROXY" not in config:
            config["PROXY"] = {}

        config["PROXY"]["enabled"] = str(self.proxy_enabled.isChecked()).lower()
        config["PROXY"]["host"] = self.proxy_host.text()
        config["PROXY"]["port"] = str(self.proxy_port.value())

        # 保存API密钥设置
        if "API_KEYS" not in config:
            config["API_KEYS"] = {}

        config["API_KEYS"]["gpt_api_key"] = self.gpt_api_key.text()
        config["API_KEYS"]["claude_api_key"] = self.claude_api_key.text()
        config["API_KEYS"]["gemini_api_key"] = self.gemini_api_key.text()
        config["API_KEYS"]["modelscope_api_key"] = self.modelscope_api_key.text()
        config["API_KEYS"]["siliconflow_api_key"] = self.siliconflow_api_key.text() # 保存 SiliconFlow API Key

        # 如果选中了自定义模型，则使用选中模型的API密钥
        if self.custom_model_combo.currentIndex() > 0:
            model_name = self.custom_model_combo.currentText()
            model_config = self.config_manager.get_custom_openai_model(model_name)
            if model_config:
                config["API_KEYS"]["custom_openai_api_key"] = model_config.get('api_key', '')
        else:
            # 否则使用输入框中的API密钥
            config["API_KEYS"]["custom_openai_api_key"] = self.custom_openai_api_key.text()

        # 保存模型设置
        if "MODELS" not in config:
            config["MODELS"] = {}

        config["MODELS"]["gpt_model"] = self.gpt_model.text()
        config["MODELS"]["claude_model"] = self.claude_model.text()
        config["MODELS"]["gemini_model"] = self.gemini_model.text()
        config["MODELS"]["modelscope_model"] = self.modelscope_model.text()
        config["MODELS"]["ollama_model"] = self.ollama_model.text()
        config["MODELS"]["siliconflow_model"] = self.siliconflow_model.text() # 保存 SiliconFlow 模型

        # 不再使用选中的自定义模型来覆盖基本设置

        # 保存自定义OpenAI API设置
        if "CUSTOM_OPENAI" not in config:
            config["CUSTOM_OPENAI"] = {}

        # 始终启用自定义OpenAI API，不需要enabled设置
        config["CUSTOM_OPENAI"]["api_url"] = self.custom_openai_url.text()

        # 保存自定义OpenAI API密钥和模型名称
        config["API_KEYS"]["custom_openai_api_key"] = self.custom_openai_api_key.text()
        config["MODELS"]["custom_openai_model"] = self.custom_openai_model.text()

        # ModelScope API设置已在代码中配置好，不需要在UI中显示

        # 保存Ollama API设置
        if "OLLAMA" not in config:
            config["OLLAMA"] = {}

        config["OLLAMA"]["api_url"] = self.ollama_url.text()

        # 保存配置
        self.config_manager.save_config()

        # 显示成功消息
        QMessageBox.information(self, "保存成功", "设置已保存")

        # 提示重启应用
        QMessageBox.warning(
            self,
            "需要重启",
            "某些设置更改需要重启应用才能生效。"
        )

    def _on_custom_model_selected(self, index):
        """处理自定义模型选择事件"""
        if index <= 0:  # 选择了第一项（提示文本）
            # 禁用编辑和删除按钮
            self.edit_model_button.setEnabled(False)
            self.delete_model_button.setEnabled(False)
            return

        # 启用编辑和删除按钮
        self.edit_model_button.setEnabled(True)
        self.delete_model_button.setEnabled(True)

        # 获取选中的模型配置
        model_name = self.custom_model_combo.currentText()
        model_config = self.config_manager.get_custom_openai_model(model_name)

        if model_config:
            # 更新自定义OpenAI兼容API设置
            self.custom_openai_api_key.setText(model_config.get('api_key', ''))
            self.custom_openai_model.setText(model_config.get('model_name', ''))
            self.custom_openai_url.setText(model_config.get('api_url', ''))

    def _add_custom_model(self):
        """添加新的自定义模型"""
        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("添加自定义模型")
        dialog.resize(500, 200)

        # 创建表单布局
        layout = QFormLayout(dialog)

        # 添加输入字段
        name_edit = QLineEdit()
        layout.addRow("模型名称:", name_edit)

        api_key_edit = QLineEdit()
        api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("API密钥:", api_key_edit)

        model_name_edit = QLineEdit()
        layout.addRow("模型标识:", model_name_edit)

        api_url_edit = QLineEdit("https://api.openai.com/v1/chat/completions")
        layout.addRow("API地址:", api_url_edit)

        # 添加按钮
        button_box = QHBoxLayout()
        save_button = QPushButton("保存")
        save_button.clicked.connect(dialog.accept)
        button_box.addWidget(save_button)

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)
        button_box.addWidget(cancel_button)

        layout.addRow("", button_box)

        # 显示对话框
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # 获取输入的值
        model_name = name_edit.text().strip()
        api_key = api_key_edit.text().strip()
        model_name_value = model_name_edit.text().strip()
        api_url = api_url_edit.text().strip()

        # 验证输入
        if not model_name:
            QMessageBox.warning(self, "验证失败", "模型名称不能为空")
            return

        if not api_key:
            QMessageBox.warning(self, "验证失败", "API密钥不能为空")
            return

        if not model_name_value:
            QMessageBox.warning(self, "验证失败", "模型标识不能为空")
            return

        if not api_url:
            QMessageBox.warning(self, "验证失败", "API地址不能为空")
            return

        # 检查模型名称是否已存在
        if self.config_manager.get_custom_openai_model(model_name):
            QMessageBox.warning(self, "添加失败", f"模型 '{model_name}' 已存在")
            return

        # 创建模型配置
        model_config = {
            'name': model_name,
            'api_key': api_key,
            'model_name': model_name_value,
            'api_url': api_url
        }

        # 添加模型
        success = self.config_manager.add_custom_openai_model(model_config)

        if success:
            # 添加到下拉框
            self.custom_model_combo.addItem(model_name)
            self.custom_model_combo.setCurrentText(model_name)

            # 更新自定义OpenAI兼容API设置
            self.custom_openai_api_key.setText(model_config.get('api_key', ''))
            self.custom_openai_model.setText(model_config.get('model_name', ''))
            self.custom_openai_url.setText(model_config.get('api_url', ''))

            QMessageBox.information(self, "添加成功", f"模型 '{model_name}' 已添加")
        else:
            QMessageBox.warning(self, "添加失败", f"模型 '{model_name}' 添加失败")

    def _edit_custom_model(self):
        """编辑选中的自定义模型"""
        # 获取当前选中的模型
        if self.custom_model_combo.currentIndex() <= 0:
            return

        model_name = self.custom_model_combo.currentText()
        model_config = self.config_manager.get_custom_openai_model(model_name)

        if not model_config:
            QMessageBox.warning(self, "编辑失败", f"无法获取模型 '{model_name}' 的配置")
            return

        # 创建对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(f"编辑模型: {model_name}")
        dialog.resize(500, 200)

        # 创建表单布局
        layout = QFormLayout(dialog)

        # 添加输入字段
        name_edit = QLineEdit(model_config.get('name', ''))
        name_edit.setReadOnly(True)  # 模型名称不可编辑
        layout.addRow("模型名称:", name_edit)

        api_key_edit = QLineEdit(model_config.get('api_key', ''))
        api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("API密钥:", api_key_edit)

        model_name_edit = QLineEdit(model_config.get('model_name', ''))
        layout.addRow("模型标识:", model_name_edit)

        api_url_edit = QLineEdit(model_config.get('api_url', ''))
        layout.addRow("API地址:", api_url_edit)

        # 添加按钮
        button_box = QHBoxLayout()
        save_button = QPushButton("保存")
        save_button.clicked.connect(dialog.accept)
        button_box.addWidget(save_button)

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)
        button_box.addWidget(cancel_button)

        layout.addRow("", button_box)

        # 显示对话框
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # 获取输入的值
        api_key = api_key_edit.text().strip()
        model_name_value = model_name_edit.text().strip()
        api_url = api_url_edit.text().strip()

        # 验证输入
        if not api_key:
            QMessageBox.warning(self, "验证失败", "API密钥不能为空")
            return

        if not model_name_value:
            QMessageBox.warning(self, "验证失败", "模型标识不能为空")
            return

        if not api_url:
            QMessageBox.warning(self, "验证失败", "API地址不能为空")
            return

        # 创建模型配置
        updated_config = {
            'name': model_name,
            'api_key': api_key,
            'model_name': model_name_value,
            'api_url': api_url
        }

        # 更新模型
        success = self.config_manager.update_custom_openai_model(model_name, updated_config)

        if success:
            # 更新自定义OpenAI兼容API设置
            self.custom_openai_api_key.setText(updated_config.get('api_key', ''))
            self.custom_openai_model.setText(updated_config.get('model_name', ''))
            self.custom_openai_url.setText(updated_config.get('api_url', ''))

            QMessageBox.information(self, "更新成功", f"模型 '{model_name}' 已更新")
        else:
            QMessageBox.warning(self, "更新失败", f"模型 '{model_name}' 更新失败")

    def _delete_custom_model(self):
        """删除选中的自定义模型"""
        # 获取当前选中的模型
        if self.custom_model_combo.currentIndex() <= 0:
            return

        model_name = self.custom_model_combo.currentText()

        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除模型 '{model_name}' 吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 删除模型
        success = self.config_manager.delete_custom_openai_model(model_name)

        if success:
            # 从下拉框中移除
            current_index = self.custom_model_combo.currentIndex()
            self.custom_model_combo.removeItem(current_index)

            # 禁用编辑和删除按钮
            self.edit_model_button.setEnabled(False)
            self.delete_model_button.setEnabled(False)

            QMessageBox.information(self, "删除成功", f"模型 '{model_name}' 已删除")
        else:
            QMessageBox.warning(self, "删除失败", f"模型 '{model_name}' 删除失败")
