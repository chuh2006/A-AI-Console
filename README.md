基于策略模式构建的多模型聚合助手，支持 DeepSeek、Gemini 和 Qwen，集成了 OCR 增强、数学工具执行（旧版已实现）及自动化会话管理。

## 🛠 核心架构 
- **UI 层**: `ui_controller.py` 处理所有终端交互与流式渲染。
- **逻辑层**: `main.py` 调度配置、Session 与 LLM 工厂。
- **模型层**: `llm_base.py` 定义标准接口，各策略类实现具体 API 调用。
- **工具层**: `vision_tools.py` (OCR)、`title_generator.py` (自动命名)。

## 快速开始

### 1. 环境准备
- **Python**: 3.10+
- **Tesseract OCR**: 
  - Windows 需下载并安装 Tesseract 引擎。
  - **关键**: 将安装目录（如 `C:\Program Files\Tesseract-OCR`）添加到系统 `PATH` 环境变量。
  - **关键**: 新建系统变量 `TESSDATA_PREFIX` 指向 `tessdata` 文件夹。

### 2. 配置私钥
在项目根目录创建 `config.json`：
```json
{
    "api_keys": {
        "deepseek": "your_key",
        "gemini": "your_key",
        "qwen": "your_key"
    },
    "settings": {
        "default_temperature": 1.0,
        "auto_title_model": "选定一个较快的模型",
        "tesseract_path" : "Path/to/tesseract.exe"
    }
}
```

### 3. 运行
```
python main.py
```

## 使用

- **DeepSeek OCR**: 当使用 `deepseek-chat` 且输入图片路径时，模型会自动通过 `perform_ocr` 工具读取图片文字。
- **Gemini 增强**: 支持手动选择思考等级 (0-3) 及开启 Google 搜索工具。
- **会话保存和标题生成**: 所有对话将以 Markdown 格式存入 chat_result/，便于阅读。首次请求后会自动生成对话名和文件名。若文件名重复，系统会自动重命名为 标题(x).md。
- **重试机制**: 遭遇网络波动报错时，可输入 y 原地重试，不丢失上下文。
- **历史文件读取**: 可从保存的 Markdown 文件读取对话记录，可手动修改对话记录内容，但是核心对话记录的标题(即 system, user, assistant_answer)不能缺少。

## 注意

- **千问**: 千问由于使用了 OpenAI 兼容模式，仅支持访问在线图片。
- **特殊模型**: multi-assistant 和 数学工具在旧版本提供实现，目前暂未迁移。
- **其他有趣玩法**: 实现了输入输出的可选多种随机字符串插入；暂未迁移自动提问模式、自己回答和随机错误消息。