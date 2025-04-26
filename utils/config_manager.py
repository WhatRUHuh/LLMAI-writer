import configparser
import os

class ConfigManager:
    """配置管理器，负责读取和管理配置文件"""

    def __init__(self, config_path='config.ini'):
        self.config_path = config_path
        self.config = configparser.ConfigParser()

        if os.path.exists(config_path):
            self.config.read(config_path, encoding='utf-8')
        else:
            self._create_default_config()

    def _create_default_config(self):
        """创建默认配置文件"""
        self.config['PROXY'] = {
            'enabled': 'false',
            'host': '127.0.0.1',
            'port': '10808'
        }

        self.config['API_KEYS'] = {
            'gpt_api_key': 'your_openai_api_key_here',
            'claude_api_key': 'your_anthropic_api_key_here',
            'gemini_api_key': 'your_google_api_key_here',
            'custom_openai_api_key': 'your_custom_api_key_here',
            'modelscope_api_key': 'your_modelscope_token_here'
        }

        self.config['MODELS'] = {
            'gpt_model': 'gpt-4-turbo',
            'claude_model': 'claude-3-opus-20240229',
            'gemini_model': 'gemini-2.0-flash',
            'custom_openai_model': 'your_custom_model_name_here',
            'modelscope_model': 'deepseek-ai/DeepSeek-R1',
            'ollama_model': 'llama3.2'
        }

        self.config['CUSTOM_OPENAI'] = {
            # 不需要enabled设置，始终启用
            'api_url': 'https://your-custom-api-endpoint.com/v1/chat/completions'
        }

        # 添加自定义OpenAI模型配置部分
        self.config['CUSTOM_OPENAI_MODELS'] = {
            # 不需要enabled设置，始终启用
            'models': '[]'  # 使用JSON字符串存储模型列表
        }

        self.config['MODELSCOPE'] = {
            # 不需要enabled设置，始终启用
            'base_url': 'https://api-inference.modelscope.cn/v1/'
        }

        self.config['OLLAMA'] = {
            # 不需要enabled设置，始终启用
            'api_url': 'http://localhost:11434/api/chat'
        }

        # 添加大纲输入记忆配置部分
        self.config['OUTLINE_INPUTS'] = {
            # 默认为空，会在用户输入时自动保存
        }

        # 添加AI对话框记忆配置部分
        self.config['AI_DIALOG'] = {
            # 默认为空，会在用户选择模型时自动保存
        }

        with open(self.config_path, 'w', encoding='utf-8') as f:
            self.config.write(f)

    def get_proxy_settings(self):
        """获取代理设置"""
        if 'PROXY' not in self.config:
            return None

        proxy_config = self.config['PROXY']
        enabled = proxy_config.getboolean('enabled', fallback=True)

        if not enabled:
            return None

        host = proxy_config.get('host', fallback='127.0.0.1')
        port = proxy_config.getint('port', fallback=10808)

        return {
            'http': f'http://{host}:{port}',
            'https': f'http://{host}:{port}'
        }

    def get_api_key(self, model_type):
        """获取指定模型的API密钥"""
        if 'API_KEYS' not in self.config:
            return None

        key_name = f'{model_type}_api_key'
        return self.config['API_KEYS'].get(key_name, None)

    def get_model_name(self, model_type):
        """获取指定类型的模型名称"""
        if 'MODELS' not in self.config:
            return None

        model_name = f'{model_type}_model'
        return self.config['MODELS'].get(model_name, None)

    def get_config(self, section, key, default=None):
        """获取指定配置项"""
        if section not in self.config:
            return default

        return self.config[section].get(key, default)

    def set_config(self, section, key, value):
        """设置指定配置项"""
        if section not in self.config:
            self.config[section] = {}

        self.config[section][key] = str(value)

    def is_custom_openai_enabled(self):
        """检查自定义OpenAI API是否启用"""
        # 始终启用自定义OpenAI API
        return True

    def is_modelscope_enabled(self):
        """检查ModelScope API是否启用"""
        # ModelScope API始终启用
        return True

    def is_ollama_enabled(self):
        """检查Ollama API是否启用"""
        # Ollama API始终启用
        return True

    def is_custom_openai_models_enabled(self):
        """检查多个自定义OpenAI模型是否启用

        注意：多个自定义OpenAI模型始终启用，不需要额外的启用设置
        """
        return True

    def get_custom_openai_models(self):
        """获取所有自定义OpenAI模型配置"""
        if 'CUSTOM_OPENAI_MODELS' not in self.config:
            return []

        import json
        try:
            models_json = self.config['CUSTOM_OPENAI_MODELS'].get('models', '[]')
            return json.loads(models_json)
        except json.JSONDecodeError:
            return []

    def add_custom_openai_model(self, model_config):
        """添加一个自定义OpenAI模型配置

        Args:
            model_config: 模型配置字典，包含 name, api_key, model_name, api_url 等字段

        Returns:
            成功返回 True，失败返回 False
        """
        if 'CUSTOM_OPENAI_MODELS' not in self.config:
            self.config['CUSTOM_OPENAI_MODELS'] = {}
            # 不需要enabled设置，始终启用
            self.config['CUSTOM_OPENAI_MODELS']['models'] = '[]'

        # 获取当前模型列表
        models = self.get_custom_openai_models()

        # 检查是否已存在同名模型
        for model in models:
            if model.get('name') == model_config.get('name'):
                return False

        # 添加新模型
        models.append(model_config)

        # 保存模型列表
        import json
        self.config['CUSTOM_OPENAI_MODELS']['models'] = json.dumps(models, ensure_ascii=False)
        self.config['CUSTOM_OPENAI_MODELS']['enabled'] = 'true'

        # 保存配置
        self.save_config()
        return True

    def update_custom_openai_model(self, model_name, model_config):
        """更新一个自定义OpenAI模型配置

        Args:
            model_name: 要更新的模型名称
            model_config: 新的模型配置

        Returns:
            成功返回 True，失败返回 False
        """
        if 'CUSTOM_OPENAI_MODELS' not in self.config:
            return False

        # 获取当前模型列表
        models = self.get_custom_openai_models()

        # 查找并更新模型
        for i, model in enumerate(models):
            if model.get('name') == model_name:
                models[i] = model_config

                # 保存模型列表
                import json
                self.config['CUSTOM_OPENAI_MODELS']['models'] = json.dumps(models, ensure_ascii=False)

                # 保存配置
                self.save_config()
                return True

        return False

    def delete_custom_openai_model(self, model_name):
        """删除一个自定义OpenAI模型配置

        Args:
            model_name: 要删除的模型名称

        Returns:
            成功返回 True，失败返回 False
        """
        if 'CUSTOM_OPENAI_MODELS' not in self.config:
            return False

        # 获取当前模型列表
        models = self.get_custom_openai_models()

        # 查找并删除模型
        for i, model in enumerate(models):
            if model.get('name') == model_name:
                del models[i]

                # 保存模型列表
                import json
                self.config['CUSTOM_OPENAI_MODELS']['models'] = json.dumps(models, ensure_ascii=False)

                # 即使没有模型了，也不需要禁用自定义模型功能，始终启用

                # 保存配置
                self.save_config()
                return True

        return False

    def get_custom_openai_model(self, model_name):
        """获取指定名称的自定义OpenAI模型配置

        Args:
            model_name: 模型名称

        Returns:
            模型配置字典，如果不存在返回 None
        """
        models = self.get_custom_openai_models()

        for model in models:
            if model.get('name') == model_name:
                return model

        return None

    def get_outline_input(self, key, default=None):
        """获取大纲输入值

        Args:
            key: 输入项键名
            default: 默认值

        Returns:
            输入值，如果不存在返回默认值
        """
        if 'OUTLINE_INPUTS' not in self.config:
            return default

        return self.config['OUTLINE_INPUTS'].get(key, default)

    def set_outline_input(self, key, value):
        """设置大纲输入值

        Args:
            key: 输入项键名
            value: 输入值
        """
        if 'OUTLINE_INPUTS' not in self.config:
            self.config['OUTLINE_INPUTS'] = {}

        self.config['OUTLINE_INPUTS'][key] = str(value)
        self.save_config()

    def save_config(self):
        """保存配置到文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            self.config.write(f)
