# LLMAI-writer

<p align="center">
  <img src="resources/icon.png" alt="LLMAI-writer Logo" width="200"/>
</p>

LLMAI-writer 是一个功能强大的 AI 辅助小说创作工具，利用最先进的大型语言模型帮助作家构思、规划和创作小说。无论您是经验丰富的作家还是初学者，LLMAI-writer 都能帮助您更高效地完成创作过程。

## ✨ 功能特点

### 📝 全流程创作支持
- **大纲生成**：根据您的创意、主题和风格，AI 自动生成完整的小说大纲
- **总大纲编辑**：编辑小说标题、核心主题、故事梗概和世界观设定
- **章节大纲编辑**：管理卷和章节结构，编辑章节摘要
- **人物设计**：创建和管理小说中的角色，包括背景、性格、外貌等详细信息
- **章节生成**：基于大纲和前后章节上下文，生成连贯的章节内容

### 🤖 多模型支持
- **主流 AI 模型**：支持 OpenAI 的 GPT 系列、Anthropic 的 Claude 系列、Google 的 Gemini 系列
- **开源模型**：支持 ModelScope 的 DeepSeek-R1 模型、SiliconFlow 模型和 Ollama 本地模型
- **本地模型**：通过 Ollama 支持在本地运行开源大语言模型（如 Llama、Mistral、Vicuna 等）
- **自定义 API**：支持任何兼容 OpenAI 协议的 API 服务
- **流式输出**：所有模型均支持流式输出，实时查看生成过程

### 🛠️ 实用工具
- **提示词模板**：内置多种提示词模板，也可自定义和保存模板
- **上下文感知**：章节生成时自动考虑前后章节的内容，保持故事连贯性
- **自动编号**：自动为章节添加序号，并在重排序时更新
- **拖放排序**：支持通过拖放重新排序卷和章节
- **人物关系图**：自动生成并可视化小说中的人物关系网络
- **统计分析**：提供字数统计、章节分布等数据可视化
- **知识库管理**：导入多种格式文档（TXT、PDF、DOCX、JSON等）创建知识库，支持向量检索
- **深色模式**：支持明亮和深色两种界面主题

## 📋 系统要求

> **必读提示：** 本项目必须使用 **Python 3.10 或更高版本**，**推荐使用 Python 3.12 版本**！第一，Gemini 功能依赖的 google-genai 库仅支持 Python 3.9+ ，这是 Google 官方的要求。如果您使用较旧版本的 Python，请参考常见问题部分的解决方案。第二，因为本项目部分语法采用了Python 3.10+的语法，Python 3.9或以下需要自定更改不兼容语法。

- **操作系统**：Windows 10/11、macOS 10.14+、Linux
- **Python**：3.10 或更高版本（推荐 3.12）
- **网络连接**：用于访问 AI API 服务
- **硬盘空间**：约 100MB（不包括生成的小说文件）

## 🚀 安装说明



#### 1. 克隆仓库
```bash
git clone https://github.com/WhatRUHuh/LLMAI-writer.git
cd LLMAI-writer
```

#### 2. 安装依赖
```bash
pip install -r requirements.txt
```

#### 3. 配置 API 密钥
1. 复制 `config.example.ini` 为 `config.ini`
2. 编辑 `config.ini`，填入您的 API 密钥和其他配置


#### 配置和数据存储

- 首次运行时，复制 `config.example.ini` 为 `config.ini` 并进行配置
- 小说文件将保存在 `novels` 目录中，该目录会在容器和主机之间共享

## 📖 使用指南

> **小贴士：** 如果您此前从未接触过代码，建议您使用 Cursor、WindSurf、Cline、RooCode、Trae、Augment 等工具询问 AI 大模型，它们会自动帮您解释代码的功能和使用方法。

### 启动程序
```bash
python main.py
```

### 创作流程

#### 1. 大纲生成
- 在"大纲生成"标签页中填写小说的基本信息（标题、类型、主题、风格等）
- 设置卷数、每卷章节数和人物数量
- 选择生成范围，可以指定开始卷、开始章节、结束卷和结束章节，实现批量或部分生成
- 选择 AI 模型并点击"生成大纲"按钮

#### 2. 大纲编辑
- 在"总大纲编辑"标签页中完善标题、主题、简介和世界观设定
- 在"章节大纲编辑"标签页中管理卷和章节结构
- 使用 AI 辅助编辑功能优化大纲内容

#### 3. 人物设计
- 在"人物编辑"标签页中创建和管理角色
- 设置角色的基本信息、背景故事、性格特点等
- 使用 AI 辅助生成丰富的角色设定

#### 4. 章节创作
- 在"章节生成"标签页中选择要编辑的章节
- 使用 AI 辅助编辑功能生成章节内容
- 系统会自动考虑前后章节的内容，保持故事连贯性

#### 5. 章节分析与润色
- 在"章节分析"标签页中选择要分析的章节
- 选择分析选项（如剧情分析、优缺点分析、改进建议等）
- 查看分析结果并使用"章节改进"功能根据分析结果自动润色章节内容

#### 6. 人物关系可视化
- 在"人物关系图"标签页中查看小说中角色之间的关系网络
- 系统会自动分析角色之间的关联并生成可视化图表
- 可以调整图表布局，查看不同角色之间的连接

#### 7. 统计分析
- 在"统计"标签页中查看小说的各项统计数据
- 包括总字数、章节分布、卷数统计等信息
- 通过图表直观展示小说的结构和进度

#### 8. 知识库管理
- 在"知识库"标签页中创建和管理知识库
- 导入多种格式的文档（TXT、PDF、DOCX、JSON、AINOVEL等）
- 使用向量检索技术查询相关内容
- 支持自定义嵌入模型（默认使用BAAI/bge-m3）

#### 9. 保存和加载
- 使用工具栏上的"保存"和"打开"按钮保存和加载小说项目（.ainovel 格式）
- 可以导出为纯文本或其他格式

## ⚙️ 配置详解

`config.ini` 文件包含以下配置项：

### 代理设置
```ini
[PROXY]
host = 127.0.0.1
port = 10808
enabled = true/false
```

> **重要提示：** 本项目默认开启10808端口代理。如果出现网络相关问题（如API连接失败、404错误等），请在设置中关闭代理或修改为您自己的代理端口。

### API 密钥和模型设置

#### OpenAI (GPT) 设置
```ini
[API_KEYS]
gpt_api_key = your_openai_api_key_here

[MODELS]
gpt_model = gpt-4-turbo  # 或 gpt-4o, gpt-3.5-turbo 等
```

#### Claude 设置
```ini
[API_KEYS]
claude_api_key = your_anthropic_api_key_here

[MODELS]
claude_model = claude-3-opus-20240229  # 或 claude-3-sonnet, claude-3-haiku 等
```

#### Gemini 设置
```ini
[API_KEYS]
gemini_api_key = your_google_api_key_here

[MODELS]
gemini_model = gemini-2.0-flash  # 或 gemini-2.0-pro, gemini-1.5-pro 等
```

#### ModelScope 设置
```ini
[API_KEYS]
modelscope_api_key = your_modelscope_token_here

[MODELS]
modelscope_model = deepseek-ai/DeepSeek-R1

[MODELSCOPE]
base_url = https://api-inference.modelscope.cn/v1/
```

#### Ollama 本地模型设置
```ini
[MODELS]
ollama_model = llama3.2  # 或其他已安装的Ollama模型名称

[OLLAMA]
api_url = http://localhost:11434/api/chat
```

> **Ollama使用说明：** 要使用Ollama本地模型，您需要先在本地安装[Ollama](https://ollama.com/)，然后使用`ollama pull llama3.2`等命令下载模型。详细说明请参考Ollama官方文档。

#### SiliconFlow 模型设置
```ini
[API_KEYS]
siliconflow_api_key = your_siliconflow_api_key_here

[MODELS]
siliconflow_model = deepseek-ai/DeepSeek-R1  # 或其他支持的模型

[SILICONFLOW]
api_url = https://api.siliconflow.cn/v1/chat/completions
```

> **SiliconFlow使用说明：** SiliconFlow提供了高性能的AI模型API服务，支持DeepSeek等多种模型。您需要在SiliconFlow官网注册并获取API密钥。

#### 嵌入模型设置
```ini
[EMBEDDING_MODELS]
siliconflow_embedding_model = BAAI/bge-m3  # 或其他支持的嵌入模型
```

> **嵌入模型说明：** 嵌入模型用于知识库功能，将文本转换为向量以支持语义搜索。默认使用BAAI/bge-m3模型，您可以根据需要更换为其他支持的模型。

### 自定义 API 设置
```ini
[API_KEYS]
custom_openai_api_key = your_custom_api_key_here

[MODELS]
custom_openai_model = your_custom_model_name_here

[CUSTOM_OPENAI]
api_url = https://your-custom-openai-compatible-api.com/v1/chat/completions
```

### 多个自定义模型设置
```ini
[CUSTOM_OPENAI_MODELS]
models = [{
  "name": "example-model",
  "api_key": "your_custom_model_api_key_here",
  "model_name": "your_custom_model_name_here",
  "api_url": "https://your-custom-api-endpoint.com/v1/chat/completions"
}]
enabled = true
```

## 🔧 常见问题

### 传统安装相关问题

#### 安装依赖失败
如果安装依赖时遇到问题，可以尝试手动安装主要依赖：
```bash
pip install PyQt6 openai anthropic google-genai qasync aiohttp configparser faiss-cpu python-docx PyMuPDF
```

注意：如果安装 google-genai 失败，请确保您使用的是 Python 3.10 或更高版本。

如果您的 Python 版本低于 3.9，您有以下选择：
1. **升级 Python**：强烈推荐升级到 Python 3.10 或更高版本（尤其推荐 3.12）以获得完整功能
2. **使用 Docker 版本**：使用本项目提供的 Docker 配置，无需关心 Python 版本兼容问题
3. **移除 Gemini 相关代码**：如果无法升级 Python 且不想使用 Docker，您可以从项目中删除与 Gemini 相关的代码（主要在 `models/gemini_model.py` 和 UI 中的相关选项）

注意：根据 Google 官方文档，Gemini API 的 Python SDK 理论上仅支持 Python 3.9 及更高版本，但实际测试表明 3.10+ 更稳定，不存在兼容旧版本 Python 的方法。

#### API 连接问题
- 确保您的 API 密钥正确
- 如果需要代理访问 API，请在配置文件中正确设置代理
- 注意：本项目默认开启10808端口代理，如果出现404错误，请尝试关闭代理或修改为您自己的代理端口
- 检查网络连接是否正常

#### 界面显示异常
- 尝试重启应用程序
- 检查是否安装了最新版本的 PyQt6
- 在不同的操作系统上，界面可能有细微差异

#### 字体显示问题
- 本项目使用思源黑体（SourceHanSansCN-Normal.otf）作为默认字体
- 确保项目根目录下存在此字体文件
- 如果字体显示异常，可以尝试重新下载思源黑体并放置在项目根目录
- 如果仍有问题，程序会自动回退使用系统默认字体

### Ollama 本地模型相关问题

#### 安装和配置 Ollama
1. 从 [Ollama 官网](https://ollama.com/) 下载并安装 Ollama
2. 安装完成后，打开命令行终端，运行以下命令下载模型：
   ```bash
   ollama pull llama3.2
   ```
   您也可以下载其他模型，如 `mistral`、`vicuna` 等
3. 确保 Ollama 服务正在运行（安装后通常会自动启动）
4. 在 LLMAI-writer 的设置中配置 Ollama 模型名称和 API 地址

#### Ollama 连接问题
- 确保 Ollama 服务正在运行，可以在浏览器中访问 `http://localhost:11434` 检查
- 如果无法连接，尝试重启 Ollama 服务
- 如果使用非默认端口或远程 Ollama 服务，请在配置文件中相应修改 API URL

#### Ollama 模型生成速度慢
- Ollama 模型在本地运行，生成速度取决于您的硬件配置（特别是 GPU）
- 尝试使用更小的模型，如 `llama3.2:8b` 而非完整的 `llama3.2`
- 如果没有 GPU，生成速度会显著降低

### 生成内容相关问题

#### 生成限制和注意事项

> **重要提示：** 避免一次生成过多章节或过长内容。所有AI模型都有输出长度限制（token限制），超过限制会导致生成的内容不完整或被截断，建议每次生成大纲不超过三十个章节，每个章节的内容在几千字以内。

> **重要提示：** 本项目默认开启10808端口代理。如果出现网络相关问题（如API连接失败、404错误等），请在设置中关闭代理或修改为您自己的代理端口。

#### 大纲生成和人物生成空白问题
- **不要留空生成**：在生成大纲或人物时，请确保填写必要的基本信息，如小说标题、类型、主题等
- **提供足够信息**：在生成人物时，提供足够的背景信息和特征描述可以帮助 AI 生成更好的结果
- **使用提示词模板**：利用内置的提示词模板可以帮助生成更结构化的内容
- **尝试不同模型**：如果一个模型生成的结果不理想，尝试切换到其他模型

#### 生成内容质量问题
- **调整提示词**：如果生成的内容质量不理想，尝试调整提示词，提供更具体的指导
- **使用高级模型**：对于复杂的内容，使用更高级的模型（如 GPT-4、Claude 3 Opus）通常能获得更好的结果
- **分步生成**：对于复杂的小说，先生成总体大纲，然后逐步细化各部分
- **人工编辑**：生成后进行人工编辑和调整，结合 AI 和人类创造力通常能获得最佳结果
- **避免使用思考推理模型**：对于小说创作，专门的思考推理模型（如某些标有"思考""推理"的模型）与普通模型相比并无明显优势，但生成速度更慢、价格更高

#### 生成内容一致性问题
- **使用上下文感知功能**：生成章节时，系统会自动考虑前后章节的内容，保持故事连贯性
- **设置章节出场角色**：在生成章节前使用"选择角色"功能，指定该章节中需要出场的角色
- **使用章节分析功能**：利用章节分析功能检查内容一致性，并使用"章节改进"功能进行优化

### Docker 相关问题

#### 显示问题
如果应用程序窗口无法显示，可能是X11转发配置问题。尝试以下解决方案：

1. Linux用户确保已允许Docker访问X服务器：
   ```bash
   xhost +local:docker
   ```

2. 检查DISPLAY环境变量是否正确设置

3. Windows用户可能需要安装X服务器（如VcXsrv或Xming）并进行适当配置

#### 字体问题
如果中文字体显示不正确，可能需要安装额外的字体包。编辑Dockerfile，添加更多字体包，然后重新构建镜像：

```bash
docker-compose build --no-cache
```

#### 数据持久化
如果您需要在容器重启后保留数据，请确保：

1. `config.ini` 文件在主机上正确配置
2. `novels` 目录已创建并正确挂载
3. 不要删除这些挂载的目录和文件

## 📄 许可证

[MIT License](LICENSE)

## 🙏 致谢

- 特别感谢克劳德先生（Mr. Claude）与杰米尼先生（Mr. Gemini）以及纪皮提先生（Mr. GPT）在本项目开发过程中提供的源码支持与技术指导
- 感谢所有开源项目和 API 提供商，使本项目成为可能
- 感谢所有用户的反馈和建议，帮助我们不断改进

## 📞 联系方式

Mr. Claude：claude.ai
Mr. Gemini：gemini.google.com
Mr. GPT：chatgpt.com
如有问题或建议，请通过 GitHub Issues 与我们联系。
## 📜 授权协议 (License)

本项目基于 **GNU Affero General Public License v3.0 (AGPL-3.0)** 进行授权。

**⚠️ 重要提示：** 本项目的 [`LICENSE`](LICENSE) 文件中包含了在 AGPL-3.0 基础之上附加的 **补充条款**。这些补充条款对代码的商业使用等方面做出了额外约定。请务必在复制、使用、修改或分发本项目代码前，仔细阅读并理解 [`LICENSE`](LICENSE) 文件中的全部内容，特别是补充条款部分，以确保您的行为符合所有授权要求。

