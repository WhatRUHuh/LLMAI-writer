import google.generativeai as genai
import asyncio
from models.ai_model import AIModel

class GeminiModel(AIModel):
    """Google Gemini模型实现"""

    def __init__(self, config_manager):
        """
        初始化Gemini模型

        Args:
            config_manager: 配置管理器实例
        """
        super().__init__(config_manager)
        self.api_key = config_manager.get_api_key('gemini')
        self.model_name = config_manager.get_model_name('gemini')

        if not self.api_key:
            raise ValueError("Google API密钥未配置")

        if not self.model_name:
            self.model_name = "gemini-2.0-flash"

        # 配置代理
        if self.proxy:
            import os
            proxy_url = self.proxy["https"]
            os.environ["HTTP_PROXY"] = proxy_url
            os.environ["HTTPS_PROXY"] = proxy_url

        # 初始化Gemini API客户端
        self.client = genai.Client(api_key=self.api_key)

    async def generate(self, prompt, callback=None):
        """
        生成文本（非流式）

        Args:
            prompt: 提示词
            callback: 回调函数，用于处理生成的文本块

        Returns:
            生成的文本
        """

        # 在事件循环中运行同步API调用
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
        )

        return response.text

    async def generate_stream(self, prompt, callback=None):
        """
        流式生成文本

        Args:
            prompt: 提示词
            callback: 回调函数，用于处理生成的文本块

        Returns:
            生成的文本流（异步生成器）
        """

        # 在事件循环中运行同步API调用
        loop = asyncio.get_event_loop()
        response_stream = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content_stream(
                model=self.model_name,
                contents=prompt
            )
        )

        # 处理流式响应
        async for chunk in self._process_stream(response_stream):
            if callback:
                callback(chunk)
            yield chunk

        # 异步生成器不能使用return返回值

    async def _process_stream(self, response_stream):
        """
        处理Gemini流式响应

        Args:
            response_stream: Gemini流式响应

        Yields:
            文本块
        """
        for chunk in response_stream:
            chunk_text = ""
            if hasattr(chunk, 'text'):
                chunk_text = chunk.text
            elif hasattr(chunk, 'parts') and chunk.parts:
                chunk_text = chunk.parts[0].text
            elif hasattr(chunk, 'content') and chunk.content:
                chunk_text = chunk.content.parts[0].text

            if chunk_text:
                yield chunk_text

            # 给异步事件循环一个机会执行
            await asyncio.sleep(0)
