import sys
import os
import asyncio
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget,
    QMessageBox, QFileDialog, QToolBar, QStatusBar
)
from PyQt6.QtGui import QFont, QFontDatabase, QIcon, QKeySequence, QAction
from PyQt6.QtCore import Qt, QSize

from ui.icons import get_new_icon, get_open_icon, get_save_icon, get_stats_icon, get_theme_icon, get_help_icon, get_about_icon
from ui.app_icon import set_app_icon

from utils.config_manager import ConfigManager
from utils.data_manager import NovelDataManager
from utils.prompt_manager import PromptManager
from utils.async_utils import AsyncHelper, ProgressIndicator
from models.gpt_model import GPTModel
from models.claude_model import ClaudeModel
from models.gemini_model import GeminiModel
from models.custom_openai_model import CustomOpenAIModel
from models.modelscope_model import ModelScopeModel
from models.ollama_model import OllamaModel
from models.siliconflow_model import SiliconFlowModel # 导入 SiliconFlow 模型
from embedding_models.siliconflow_embedding import SiliconFlowEmbedding # 导入 SiliconFlow 嵌入模型
from utils.knowledge_base_manager import KnowledgeBaseManager # 导入知识库管理器

from ui.components import ThemeManager, StatusBarManager, KeyboardShortcutManager
from ui.outline_tab import OutlineTab
from ui.outline_edit_tab import OutlineEditTab
from ui.chapter_outline_tab import ChapterOutlineTab
from ui.chapter_tab import ChapterTab
from ui.character_tab import CharacterTab
from ui.character_relationship_tab import CharacterRelationshipTab
from ui.chapter_analysis_tab import ChapterAnalysisTab
from ui.statistics_tab import StatisticsTab
from ui.settings_tab import SettingsTab
from ui.knowledge_base_tab import KnowledgeBaseTab

class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()

        # 设置窗口标题和大小
        self.setWindowTitle("AI小说生成器 v0.80")
        self.resize(1200, 800)

        # 加载配置
        self.config_manager = ConfigManager()

        # 创建数据管理器
        self.data_manager = NovelDataManager(cache_enabled=True)

        # 创建提示词管理器
        self.prompt_manager = PromptManager()

        # 创建异步助手
        self.async_helper = AsyncHelper(self)

        # 创建进度指示器
        self.progress_indicator = ProgressIndicator(self)

        # 加载字体
        self._load_font()

        # 初始化AI模型（必须在UI初始化之前，因为UI需要访问模型信息）
        self._init_models()

        # 初始化UI
        self._init_ui()

        # 初始化 Embedding 模型 (需要放在模型初始化之后，因为它可能依赖模型配置)
        self._init_embedding_model()

        # 初始化知识库管理器 (需要 Embedding 模型)
        self._init_knowledge_base_manager()

        # 创建主题管理器
        self.theme_manager = ThemeManager(QApplication.instance())

        # 创建状态栏管理器
        self.status_bar_manager = StatusBarManager(self.statusBar())

        # 创建键盘快捷键管理器
        self.shortcut_manager = KeyboardShortcutManager(self)

        # 显示欢迎消息
        self.status_bar_manager.show_message("欢迎使用AI小说生成器")

    def _load_font(self):
        """加载字体"""
        font_path = "SourceHanSansCN-Normal.otf"
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                # 直接使用字体文件名作为字体名
                self.font = QFont("SourceHanSansCN-Normal", 10)
                QApplication.setFont(self.font)
            else:
                print("无法加载字体文件")
        else:
            print(f"字体文件不存在: {font_path}")

    def _init_ui(self):
        """初始化UI"""
        # 创建状态栏
        self.setStatusBar(QStatusBar())

        # 创建工具栏
        self._create_toolbar()

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)

        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self._on_tab_changed)  # 连接标签页切换事件
        main_layout.addWidget(self.tab_widget)

        # 创建各个标签页
        self.outline_tab = OutlineTab(self)
        self.outline_edit_tab = OutlineEditTab(self)
        self.chapter_outline_tab = ChapterOutlineTab(self)
        self.chapter_tab = ChapterTab(self)
        self.character_tab = CharacterTab(self)
        self.character_relationship_tab = CharacterRelationshipTab(self)
        self.chapter_analysis_tab = ChapterAnalysisTab(self)
        self.statistics_tab = StatisticsTab(self)
        self.knowledge_base_tab = KnowledgeBaseTab(self)
        self.settings_tab = SettingsTab(self)

        # 添加标签页
        self.tab_widget.addTab(self.outline_tab, "大纲生成")
        self.tab_widget.addTab(self.outline_edit_tab, "总大纲编辑")
        self.tab_widget.addTab(self.chapter_outline_tab, "章节大纲编辑")
        self.tab_widget.addTab(self.chapter_tab, "章节生成")
        self.tab_widget.addTab(self.character_tab, "人物编辑")
        self.tab_widget.addTab(self.character_relationship_tab, "人物关系图")
        self.tab_widget.addTab(self.chapter_analysis_tab, "章节分析")
        self.tab_widget.addTab(self.knowledge_base_tab, "知识库")
        self.tab_widget.addTab(self.statistics_tab, "统计信息")
        self.tab_widget.addTab(self.settings_tab, "设置")

    def _init_models(self):
        """初始化AI模型"""
        try:
            self.gpt_model = GPTModel(self.config_manager)
            self.has_gpt = True
        except Exception as e:
            self.has_gpt = False
            print(f"GPT模型初始化失败: {e}")

        try:
            self.claude_model = ClaudeModel(self.config_manager)
            self.has_claude = True
        except Exception as e:
            self.has_claude = False
            print(f"Claude模型初始化失败: {e}")

        try:
            self.gemini_model = GeminiModel(self.config_manager)
            self.has_gemini = True
        except Exception as e:
            self.has_gemini = False
            print(f"Gemini模型初始化失败: {e}")

        # 初始化自定义OpenAI兼容API
        self.has_custom_openai = False
        if self.config_manager.is_custom_openai_enabled():
            try:
                self.custom_openai_model = CustomOpenAIModel(self.config_manager)
                self.has_custom_openai = True
            except Exception as e:
                print(f"自定义OpenAI模型初始化失败: {e}")

        # 初始化多个自定义OpenAI模型
        self.custom_openai_models = {}
        if self.config_manager.is_custom_openai_models_enabled():
            models = self.config_manager.get_custom_openai_models()
            for model_config in models:
                try:
                    model_name = model_config.get('name')
                    if model_name:
                        model = CustomOpenAIModel(self.config_manager, model_config)
                        self.custom_openai_models[model_name] = model
                        print(f"初始化自定义模型: {model_name}")
                except Exception as e:
                    print(f"自定义模型 '{model_config.get('name', '未命名')}' 初始化失败: {e}")

        # 初始化ModelScope API
        self.has_modelscope = False
        if self.config_manager.is_modelscope_enabled():
            try:
                self.modelscope_model = ModelScopeModel(self.config_manager)
                self.has_modelscope = True
            except Exception as e:
                print(f"ModelScope模型初始化失败: {e}")

        # 初始化Ollama API
        self.has_ollama = False
        if self.config_manager.is_ollama_enabled():
            try:
                self.ollama_model = OllamaModel(self.config_manager)
                self.has_ollama = True
            except Exception as e:
                print(f"Ollama模型初始化失败: {e}")

        # 初始化 SiliconFlow API
        self.has_siliconflow = False
        # 检查配置中是否有 siliconflow_api_key 来决定是否启用
        if self.config_manager.get_api_key('siliconflow'):
            try:
                self.siliconflow_model = SiliconFlowModel(self.config_manager)
                self.has_siliconflow = True
            except Exception as e:
                print(f"SiliconFlow模型初始化失败: {e}")

        # 检查是否至少有一个模型可用
        if not any([self.has_gpt, self.has_claude, self.has_gemini, self.has_custom_openai, self.has_modelscope, self.has_ollama, self.has_siliconflow, bool(self.custom_openai_models)]):
            QMessageBox.warning(
                self,
                "模型初始化失败",
                "所有AI模型初始化失败，请检查API密钥和网络连接。"
            )

    def get_model(self, model_type):
        """获取指定类型的模型"""
        # 检查是否是自定义模型
        if model_type in self.custom_openai_models:
            return self.custom_openai_models[model_type]

        # 检查标准模型
        if model_type == "gpt" and self.has_gpt:
            return self.gpt_model
        elif model_type == "claude" and self.has_claude:
            return self.claude_model
        elif model_type == "gemini" and self.has_gemini:
            return self.gemini_model
        elif model_type == "custom_openai" and self.has_custom_openai:
            return self.custom_openai_model
        elif model_type == "modelscope" and self.has_modelscope:
            return self.modelscope_model
        elif model_type == "ollama" and self.has_ollama:
            return self.ollama_model
        elif model_type == "siliconflow":
            if self.has_siliconflow:
                return self.siliconflow_model
            else:
                # 如果请求了 SiliconFlow 但它不可用（通常是缺少API Key），则明确报错
                raise ValueError("SiliconFlow模型未配置或初始化失败 (请检查config.ini中的API Key)")
        else:
            # 如果模型类型字符串本身就不认识
             raise ValueError(f"未知的模型类型: {model_type}")

    def get_available_models(self):
        """获取所有可用的模型列表（包括自定义模型）"""
        models = []
        
        # 添加标准模型
        if self.has_gpt:
            models.append("GPT")
        if self.has_claude:
            models.append("Claude") 
        if self.has_gemini:
            models.append("Gemini")
        if self.has_custom_openai:
            models.append("自定义OpenAI")
        if self.has_modelscope:
            models.append("ModelScope")
        if self.has_ollama:
            models.append("Ollama")
        if self.has_siliconflow:
            models.append("SiliconFlow")
            
        # 添加多个自定义模型
        if self.custom_openai_models:
            models.extend(list(self.custom_openai_models.keys()))
            
        return models

    def _init_embedding_model(self):
        """初始化 Embedding 模型"""
        # 优先使用 SiliconFlow Embedding，如果配置了的话
        if self.config_manager.get_api_key('siliconflow_embedding') or self.config_manager.get_api_key('siliconflow'): # 兼容旧配置
             try:
                 # 注意：SiliconFlowEmbedding 可能需要 config_manager
                 self.embedding_model = SiliconFlowEmbedding(self.config_manager)
                 print("SiliconFlow Embedding 模型初始化成功。")
             except Exception as e:
                 self.embedding_model = None
                 print(f"SiliconFlow Embedding 模型初始化失败: {e}")
                 QMessageBox.warning(self, "Embedding模型失败", "SiliconFlow Embedding 模型初始化失败，知识库功能可能受限。")
        else:
             self.embedding_model = None
             print("未配置 SiliconFlow Embedding 模型。知识库功能将受限。")
             # 这里可以考虑添加对其他 Embedding 模型的支持，或者提示用户配置

    def _init_knowledge_base_manager(self):
        """初始化知识库管理器"""
        if self.embedding_model:
            try:
                self.knowledge_base_manager = KnowledgeBaseManager(config_manager=self.config_manager, embedding_model=self.embedding_model) # 同时传递配置管理器和嵌入模型
                print("知识库管理器初始化成功。")
            except Exception as e:
                self.knowledge_base_manager = None
                print(f"知识库管理器初始化失败: {e}")
                QMessageBox.warning(self, "知识库管理器失败", f"知识库管理器初始化失败: {e}")
        else:
            self.knowledge_base_manager = None
            print("由于 Embedding 模型未初始化，知识库管理器无法初始化。")
            # 可以选择性地在这里也弹窗提示用户

    def get_knowledge_base_manager(self):
        """获取知识库管理器实例"""
        # 添加一个检查，确保管理器已成功初始化
        if not hasattr(self, 'knowledge_base_manager') or self.knowledge_base_manager is None:
             print("警告: 尝试访问未初始化的知识库管理器。")
             # 可以选择抛出异常或返回 None，这里返回 None 可能更安全
             # raise RuntimeError("知识库管理器未成功初始化。")
             return None
        return self.knowledge_base_manager

    def get_available_knowledge_bases(self):
        """获取可用的知识库列表"""
        if self.knowledge_base_manager:
            try:
                return self.knowledge_base_manager.list_knowledge_bases()
            except Exception as e:
                print(f"获取知识库列表失败: {e}")
                return []
        return []

    def _create_toolbar(self):
        """创建工具栏"""
        # 创建主工具栏
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)  # 显示图标和文本
        self.addToolBar(toolbar)

        # 文件操作
        new_action = QAction(get_new_icon(), "新建", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_novel)
        toolbar.addAction(new_action)

        open_action = QAction(get_open_icon(), "打开", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.load_novel)
        toolbar.addAction(open_action)

        save_action = QAction(get_save_icon(), "保存", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_novel_quick)
        save_action.setProperty("primary", True)  # 设置为主要按钮
        toolbar.addAction(save_action)

        save_as_action = QAction(get_save_icon(), "另存为", self) 
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_novel)
        toolbar.addAction(save_as_action)

        toolbar.addSeparator()

        # 统计
        stats_action = QAction(get_stats_icon(), "统计信息", self)
        stats_action.setShortcut(QKeySequence("Ctrl+I"))
        stats_action.triggered.connect(self.show_statistics)
        toolbar.addAction(stats_action)

        # 主题切换
        theme_action = QAction(get_theme_icon(), "切换主题", self)
        theme_action.setShortcut(QKeySequence("Ctrl+T"))
        theme_action.triggered.connect(self.toggle_theme)
        toolbar.addAction(theme_action)

        # 帮助
        help_action = QAction(get_help_icon(), "帮助", self)
        help_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)

        # 关于
        about_action = QAction(get_about_icon(), "关于", self)
        about_action.triggered.connect(self.show_about)
        toolbar.addAction(about_action)

    def toggle_theme(self):
        """切换主题"""
        self.theme_manager.toggle_theme()

        # 更新状态栏消息
        theme_name = "深色" if self.theme_manager.current_theme == ThemeManager.DARK_THEME else "明亮"
        self.status_bar_manager.show_message(f"已切换到{theme_name}主题")

    def show_statistics(self):
        """显示统计信息"""
        # 检查是否有大纲
        if not self.data_manager.get_outline():
            QMessageBox.warning(self, "统计失败", "没有可统计的内容")
            return

        # 切换到统计标签页
        self.tab_widget.setCurrentWidget(self.statistics_tab)

        # 更新统计信息
        self.statistics_tab.update_statistics()

    def show_help(self):
        """显示帮助"""
        # 显示快捷键列表
        shortcut_descriptions = self.shortcut_manager.get_shortcut_descriptions()
        shortcut_text = "\n".join(shortcut_descriptions)

        QMessageBox.information(
            self,
            "快捷键帮助",
            f"可用的快捷键:\n\n{shortcut_text}"
        )

    def show_about(self):
        """显示关于信息"""
        # 显示作者信息
        QMessageBox.information(
            self,
            "关于作者",
            "作者：你算啥呢呀？\n\n"
            "仓库地址：https://github.com/WhatRUHuh/LLMAI-writer\n\n"
            "B站主页：https://space.bilibili.com/586587271\n\n"
            "声明：本项目免费开源，如果你是花钱买的说明你被坑了"
        )

    def new_novel(self):
        """新建小说"""
        # 检查是否有未保存的更改
        if self.data_manager.is_modified():
            reply = QMessageBox.question(
                self,
                "确认新建",
                "当前有未保存的更改，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

        # 清空数据
        self.data_manager.clear()

        # 更新UI
        self.set_outline(None)

        # 更新状态栏
        self.status_bar_manager.show_message("已创建新小说")

    def set_outline(self, outline):
        """设置小说大纲"""
        self.data_manager.set_outline(outline)
        # 更新各个标签页
        self.outline_edit_tab.update_outline()
        self.chapter_outline_tab.update_outline()
        self.chapter_tab.update_outline(outline)
        # 更新人物编辑标签页
        self.character_tab.update_characters()
        # 更新章节分析标签页
        self.chapter_analysis_tab.set_outline(outline)
        # 更新人物关系图标签页
        self.character_relationship_tab.set_outline(outline)
        # 更新统计标签页
        self.statistics_tab.update_statistics()

    def get_outline(self):
        """获取小说大纲"""
        return self.data_manager.get_outline()

    def set_chapter(self, volume_index, chapter_index, content):
        """设置章节内容"""
        self.data_manager.set_chapter(volume_index, chapter_index, content)

    def get_chapter(self, volume_index, chapter_index):
        """获取章节内容"""
        return self.data_manager.get_chapter(volume_index, chapter_index)

    def _on_tab_changed(self, index):
        """处理标签页切换事件

        在切换标签页时自动保存当前标签页的内容

        Args:
            index: 新标签页的索引
        """
        # 获取当前标签页
        current_tab = self.tab_widget.currentWidget()

        # 根据标签页类型执行不同的保存操作
        if current_tab == self.outline_edit_tab:
            # 自动保存总大纲编辑页面的内容
            try:
                # 调用保存方法，但不显示消息框
                if hasattr(self.outline_edit_tab, 'outline') and self.outline_edit_tab.outline:
                    # 更新大纲数据
                    self.outline_edit_tab.outline["title"] = self.outline_edit_tab.title_edit.text()
                    self.outline_edit_tab.outline["theme"] = self.outline_edit_tab.theme_edit.toPlainText()
                    self.outline_edit_tab.outline["synopsis"] = self.outline_edit_tab.synopsis_edit.toPlainText()
                    self.outline_edit_tab.outline["worldbuilding"] = self.outline_edit_tab.world_edit.toPlainText()

                    # 保存大纲
                    self.set_outline(self.outline_edit_tab.outline)
                    self.status_bar_manager.show_message("总大纲已自动保存")
            except Exception as e:
                print(f"自动保存总大纲时出错: {e}")

        elif current_tab == self.chapter_outline_tab:
            # 自动保存章节大纲编辑页面的内容
            try:
                # 调用保存方法，但不显示消息框
                if hasattr(self.chapter_outline_tab, 'outline') and self.chapter_outline_tab.outline:
                    # 保存当前编辑的卷和章节
                    if self.chapter_outline_tab.current_volume_index >= 0:
                        volumes = self.chapter_outline_tab.outline.get("volumes", [])
                        if self.chapter_outline_tab.current_volume_index < len(volumes):
                            volume = volumes[self.chapter_outline_tab.current_volume_index]
                            volume["title"] = self.chapter_outline_tab.volume_title_edit.text()
                            # 更新description字段作为卷简介
                            volume["description"] = self.chapter_outline_tab.volume_intro_edit.toPlainText()

                            if self.chapter_outline_tab.current_chapter_index >= 0:
                                chapters = volume.get("chapters", [])
                                if self.chapter_outline_tab.current_chapter_index < len(chapters):
                                    chapter = chapters[self.chapter_outline_tab.current_chapter_index]
                                    chapter["title"] = self.chapter_outline_tab.chapter_title_edit.text()
                                    chapter["summary"] = self.chapter_outline_tab.chapter_summary_edit.toPlainText()

                    # 保存大纲
                    self.set_outline(self.chapter_outline_tab.outline)
                    self.status_bar_manager.show_message("章节大纲已自动保存")
            except Exception as e:
                print(f"自动保存章节大纲时出错: {e}")

        elif current_tab == self.chapter_tab:
            # 自动保存章节内容
            try:
                if self.chapter_tab.current_volume_index >= 0 and self.chapter_tab.current_chapter_index >= 0:
                    # 获取章节内容
                    content = self.chapter_tab.output_edit.toPlainText()
                    if content:
                        # 保存章节内容
                        self.set_chapter(self.chapter_tab.current_volume_index, self.chapter_tab.current_chapter_index, content)
                        self.status_bar_manager.show_message("章节内容已自动保存")
            except Exception as e:
                print(f"自动保存章节内容时出错: {e}")

        elif current_tab == self.character_tab:
            # 自动保存人物数据
            try:
                if hasattr(self.character_tab, '_save_characters'):
                    self.character_tab._save_characters()
                    self.status_bar_manager.show_message("人物数据已自动保存")
            except Exception as e:
                print(f"自动保存人物数据时出错: {e}")

        elif current_tab == self.character_relationship_tab:
            # 自动保存人物关系数据
            try:
                if hasattr(self.character_relationship_tab, 'save_relationships_to_data'):
                    self.character_relationship_tab.save_relationships_to_data()
                    self.status_bar_manager.show_message("人物关系数据已自动保存")
            except Exception as e:
                print(f"自动保存人物关系数据时出错: {e}")

    def save_novel_quick(self):
        """快速保存小说 (Ctrl+S)"""
        # 检查是否有大纲
        if not self.data_manager.get_outline():
            QMessageBox.warning(self, "保存失败", "没有可保存的大纲数据")
            return

        # 检查是否已有保存路径
        current_file = self.data_manager.current_file
        
        if current_file:
            # 直接保存到当前文件
            self.progress_indicator.start()
            self.status_bar_manager.show_message("正在保存小说...")
            
            success = self.data_manager.save_to_file(current_file)
            
            self.progress_indicator.stop()
            
            if success:
                self.status_bar_manager.show_message(f"小说已保存")
            else:
                self.status_bar_manager.show_message("保存失败")
                QMessageBox.warning(self, "保存失败", "保存小说时出错")
        else:
            # 没有当前文件，调用另存为
            self.save_novel()

    def save_novel(self):
        """另存为小说 (Ctrl+Shift+S)"""
        # 显示进度指示器
        self.progress_indicator.start()
        self.status_bar_manager.show_message("正在保存小说...")

        # 检查是否有大纲
        if not self.data_manager.get_outline():
            self.progress_indicator.stop()
            QMessageBox.warning(self, "保存失败", "没有可保存的大纲数据")
            return

        # 选择保存文件
        filepath, _ = QFileDialog.getSaveFileName(self, "另存为小说", "", "AI小说文件 (*.ainovel)")
        if not filepath:
            self.progress_indicator.stop()
            return

        # 如果文件名没有.ainovel后缀，添加后缀
        if not filepath.endswith('.ainovel'):
            filepath += '.ainovel'

        # 保存小说数据
        success = self.data_manager.save_to_file(filepath)

        # 停止进度指示器
        self.progress_indicator.stop()

        if success:
            # current_file is already set by save_to_file method
            self.status_bar_manager.show_message(f"小说已保存到: {filepath}")
            QMessageBox.information(self, "保存成功", f"小说已保存到: {filepath}")
        else:
            self.status_bar_manager.show_message("保存失败")
            QMessageBox.warning(self, "保存失败", "保存小说时出错")

    def load_novel(self):
        """加载小说"""
        # 检查是否有未保存的更改
        if self.data_manager.is_modified():
            reply = QMessageBox.question(
                self,
                "确认加载",
                "当前有未保存的更改，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

        # 选择小说文件
        filepath, _ = QFileDialog.getOpenFileName(self, "选择小说文件", "", "AI小说文件 (*.ainovel);;JSON文件 (*.json)")
        if not filepath:
            return

        # 显示进度指示器
        self.progress_indicator.start()
        self.status_bar_manager.show_message("正在加载小说...")

        try:
            # 加载小说数据
            success = self.data_manager.load_from_file(filepath)

            # 停止进度指示器
            self.progress_indicator.stop()

            if success:
                # 更新UI
                outline = self.data_manager.get_outline()
                self.set_outline(outline)

                self.status_bar_manager.show_message(f"已加载小说: {filepath}")
                QMessageBox.information(self, "加载成功", "小说已加载")
            else:
                self.status_bar_manager.show_message("加载失败")
                QMessageBox.warning(self, "加载失败", "无法加载文件，格式可能不兼容")

        except Exception as e:
            # 停止进度指示器
            self.progress_indicator.stop()
            self.status_bar_manager.show_message("加载失败")
            QMessageBox.warning(self, "加载失败", f"加载小说时出错: {e}")

    def load_file(self, filepath):
        """加载指定文件

        Args:
            filepath: 文件路径
        """
        # 显示进度指示器
        self.progress_indicator.start()
        self.status_bar_manager.show_message(f"正在加载文件: {filepath}...")

        try:
            # 加载小说数据
            success = self.data_manager.load_from_file(filepath)

            # 停止进度指示器
            self.progress_indicator.stop()

            if success:
                # 更新UI
                outline = self.data_manager.get_outline()
                self.set_outline(outline)

                self.status_bar_manager.show_message(f"已加载小说: {filepath}")
            else:
                self.status_bar_manager.show_message("加载失败")
                QMessageBox.warning(self, "加载失败", "无法加载文件，格式可能不兼容")

        except Exception as e:
            # 停止进度指示器
            self.progress_indicator.stop()
            self.status_bar_manager.show_message("加载失败")
            QMessageBox.warning(self, "加载失败", f"加载文件时出错: {e}")


def run_app():
    """运行应用程序"""
    app = QApplication(sys.argv)

    # 设置应用程序样式
    app.setStyle("Fusion")

    # 应用默认样式表
    from ui.styles import get_style
    app.setStyleSheet(get_style("light"))

    # 设置应用程序图标
    set_app_icon(app)

    # 创建主窗口
    window = MainWindow()
    window.show()

    # 运行应用程序
    sys.exit(app.exec())
