# 小凯哥语音输入法

<p align="center">
  <img src="docs/whisper_claudecode.png" alt="Project Poster" />
</p>

<p align="center">
  <a href="./VERSION">
    <img src="https://img.shields.io/badge/version-3.3.0-blue.svg" alt="Version" />
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/python-3.12+-green.svg" alt="Python" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License" />
  </a>
  <a href="docs/README_zh-CN.md">
    <img src="https://img.shields.io/badge/docs-中文文档-red.svg" alt="Chinese Documentation" />
  </a>
</p>

基于 Whisper-Input-Next 开发的个人 AI 语音输入工具，支持中文听写、多语言翻译和转写历史。

## 💰 Why Pay $12/Month? Use Open Source Instead!

**Typeless charges $12/month** for their voice keyboard, but you know what? This open-source project does the same thing for **FREE** - you only pay for the underlying API costs (Doubao ASR or OpenAI GPT-4o transcribe), which is incredibly cheap compared to Typeless's subscription.

- Typeless: $144/year subscription + you don't own the service
- **Whisper-Input-Next**: $0 + only pay for what you use (Doubao streaming ASR is super cheap!)

Stop renting your tools. Own them.

## 🚀 Project Background

This project is based on [ErlichLiu/Whisper-Input](https://github.com/ErlichLiu/Whisper-Input) for secondary development. The original project has been inactive for months, so we have made extensive feature expansions and architectural optimizations, adding important features like OpenAI GPT-4o transcribe integration, audio archiving, local whisper support, and more. [Why use this project?](./docs/[V3.0.0]_知乎blog.md)

## ✨ Key Features

### 🔥 NEW in v3.3.0: Two-Pass Recognition & Accuracy Boost
- **Two-Pass Recognition**: Enables `enable_nonstream` for sentence-level re-recognition using the higher-accuracy nostream model during speech pauses, significantly improving transcription quality
- **Deferred Text Output**: All text stays in floating preview during recording; final text is pasted only after recording stops, allowing full ASR context optimization
- **DJI Wireless Mic Support**: Auto-detects and prioritizes DJI Wireless Microphone as input device

### Doubao Streaming ASR (since v3.2.0)
- **Real-time Streaming Transcription**: Powered by ByteDance's Doubao Seed ASR 2.0, transcription appears as you speak
- **Floating Preview Window**: Shows pending text in real-time near your input field, like an IME
- **Now Default for Win+F**: The best voice input experience, set as default (configurable)
- 👉 [How to get your API keys](#how-to-get-doubao-api-keys)

### 🎯 Core Functions
- **Multi-platform Transcription Services**: Doubao Streaming ASR (default), OpenAI GPT-4o transcribe, local whisper.cpp
- **Smart Hotkeys**: Win+F (Doubao streaming, default) / Win+I (local cost-saving mode)
- **Audio Archive**: Automatically save all recordings, support history playback
- **Failure Retry**: Intelligent error handling and retry mechanism

### 🔧 Technical Features
- **Dual Processor Architecture**: Streaming + Batch processors working simultaneously
- **180s Long Audio Support**: Support up to 3 minutes of continuous recording
- **Smart Status Indicators**: Simple numeric status display (0, 1, !)
- **Cache System**: Audio archive with transcription result caching

### 🌟 User Experience
- **No Clipboard Pollution**: Clean status display without interfering with system clipboard
- **One-click Retry**: Failed transcriptions can be retried without re-recording
- **Real-time Input**: Transcription results appear directly at cursor position
- **Privacy Protection**: Local processing option, data not uploaded

## 当前桌面版：语音转写与多语言翻译

当前版本提供新的 PyQt5 控制台、SQLite 转写历史，以及独立的语音翻译快捷键。翻译不是由 ASR 单独完成，而是采用两段式模型链路：

```text
中文语音
  -> 阿里云 Qwen ASR（语音转中文文字）
  -> 阿里云 Qwen-MT（中文翻译为目标语言）
  -> 流式预览并粘贴到当前输入框
```

默认操作：

| 操作 | 功能 |
|------|------|
| 按住右 `Alt`，松开 | 普通语音转写 |
| 按住右 `Command`，松开 | 识别中文并翻译为目标语言 |
| 打开“快捷键与文本” | 切换英语、日语、俄语等目标语言 |
| 打开“历史记录” | 查看成功、失败、耗时、模型和翻译结果 |

苹果键盘使用右 `Command` 作为翻译快捷键，对应配置值 `cmd_r`。

翻译默认复用阿里云 DashScope 密钥，不需要额外的 OpenAI 密钥。核心配置如下：

```bash
TRANSCRIPTION_SERVICE=aliyun
BATCH_TRANSCRIPTION_SERVICE=aliyun
DASHSCOPE_API_KEY=your_dashscope_key
DASHSCOPE_ASR_MODEL=qwen3-asr-flash

TRANSLATION_SERVICE=aliyun
TRANSLATION_TARGET_LANGUAGE=en
DASHSCOPE_TRANSLATION_MODEL=qwen-mt-flash
TRANSLATION_HOTKEY=cmd_r
TRANSLATION_HOTKEY_MODE=hold

TRANSCRIPTION_HOTKEY=alt_r
TRANSCRIPTION_HOTKEY_MODE=hold

PASTE_HOTKEY=auto
PASTE_DELAY_MS=80
HISTORY_RETENTION_DAYS=1
HISTORY_MAX_RECORDS=5000
TERMINAL_MODE_ENABLED=false
TERMINAL_MODE_KEY=m
CHINESE_CONVERSION=none
CLEAN_ASR_FILLERS=true
NORMALIZE_TRANSCRIPT_TEXT=true
SMART_SENTENCE_ENDING=false
```

`TRANSLATION_TARGET_LANGUAGE` 支持 `en`、`ja`、`ru`、`ko`、`fr`、`de`、`es`、`pt`、`it`、`ar` 和 `zh`。修改控制台设置后点击“保存并重启”即可加载新目标语言。

“粘贴与文本”页面提供智能粘贴模式。普通桌面应用使用 `Ctrl+V`，Linux 终端和 CLI 使用 `Ctrl+Shift+V`；也可以固定使用 `Shift+Insert`。本地文字处理支持繁体转简体、简体转繁体、口头禅与短重复清理、空格与重复标点规范化，以及可选的句末标点补全。

终端模式可单独开启并设置模式键。按住普通听写键开始录音后，再按一次模式键，本次结果会跳过人设改写、移除句末语气标点，并将“空格、斜杠、双横杠、管道符、等号、艾特”等明确口述转换为命令符号。程序只粘贴结果，不会自动发送回车执行命令。

### 人设与实时改写

控制台提供独立的“人设与改写”页面。开启后，普通听写按“语音识别 → 词库纠错 → 人设改写 → 粘贴”的顺序处理；翻译快捷键仍走独立翻译链路。

内置人设包括文言文、网络热梗、AI 提示词和正式表达，也可以创建自定义人设。改写模型可在阿里云 Qwen Flash 与火山方舟 Doubao Seed 之间切换，并可配置失败备用模型。

```bash
PERSONA_REWRITE_ENABLED=true
PERSONA_REWRITE_PROVIDER=qwen
PERSONA_FALLBACK_PROVIDER=ark
QWEN_REWRITE_MODEL=qwen-flash
ARK_API_KEY=your_ark_key
ARK_REWRITE_MODEL=doubao-seed-2-0-mini-260428
```

Qwen 改写复用 `DASHSCOPE_API_KEY`。Qwen 和火山方舟都关闭思考模式，避免实时输入时把时间和输出额度消耗在推理内容上；如果所有改写模型都失败，程序会输入原始转写结果。

### 轻量个人资料库

控制台提供“个人资料库”页面，资料以 Markdown 保存在
`data/memory/`。表达风格会用于人设改写，固定回复和
`knowledge/` 下的知识文件按关键词选取，不需要向量数据库或本地大模型。

语音说“快捷回复 + 分组名”可直接展开固定回复，例如“快捷回复 稍后回复”。
这个过程完全在本机完成，不调用语言模型。

### 词库与自动纠错

控制台提供独立的“词库与纠错”页面。每个词条由“口述形式”和“输出结果”组成，保存后无需重启，下一次语音输入立即生效。

| 口述形式 | 输出结果 |
|----------|----------|
| `S S H` | `SSH` |
| `V P S` | `VPS` |
| `香港杠` | `香港-` |

词库会应用于普通转写、翻译前的中文原文和流式识别结果。词条可以单独停用、搜索、编辑或删除。

启动控制台：

```bash
./launch-control-ui.sh
```

## 📦 Quick Start

### Environment Requirements
- Python 3.12+
- macOS/Linux (Windows support in development)
- Network connection (only required for cloud services)
- **Local whisper.cpp** (required when using local transcription features)
- Linux: PortAudio runtime (`sudo apt install libportaudio2` on Ubuntu/Debian)

### Installation Steps

1. **Clone Project**
```bash
git clone https://github.com/Mor-Li/Whisper-Input-Next.git
cd Whisper-Input-Next
```

2. **Create Virtual Environment**
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or .venv\\Scripts\\activate  # Windows
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

**Using uv (optional):**
```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
```

4. **Install Local whisper.cpp (Optional, required for local transcription)**
```bash
# Clone whisper.cpp repository
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp

# Compile (macOS/Linux)
make

# Download model file (recommend large-v3)
bash ./models/download-ggml-model.sh large-v3

# Record whisper-cli path for later configuration in .env file
echo "Whisper CLI Path: $(pwd)/build/bin/whisper-cli"
cd ..
```

5. **Configure Environment Variables**
```bash
cp .env.example .env
# Edit .env file, configure necessary parameters:
# - DOUBAO_APP_KEY / DOUBAO_ACCESS_KEY: required for Doubao streaming
# - SYSTEM_PLATFORM: mac / linux / win
# - OFFICIAL_OPENAI_API_KEY: optional, for OpenAI batch transcription/translation
# - WHISPER_CLI_PATH / WHISPER_MODEL_PATH: optional, for local transcription
```

6. **Run Program**
```bash
python main.py
# or use startup script
chmod +x start.sh
./start.sh
```

### ⚠️ Important Notes

**Required Configuration:**
- `OFFICIAL_OPENAI_API_KEY`: OpenAI GPT-4o transcribe API key
- `WHISPER_CLI_PATH`: Local whisper.cpp executable absolute path
- `WHISPER_MODEL_PATH`: whisper model file path (relative to whisper.cpp root directory)

**whisper.cpp Installation Guide:**
1. Clone and compile from [whisper.cpp repository](https://github.com/ggerganov/whisper.cpp)
2. Download large-v3 model: `bash ./models/download-ggml-model.sh large-v3`
3. Configure correct paths in .env

## ⚙️ Configuration Guide

### Environment Variable Configuration

Configure the following parameters in the `.env` file:

```bash
# ============ Doubao Streaming ASR (Recommended, Default) ============
# Get your API keys from Volcengine Console (see screenshot below)
DOUBAO_APP_KEY=your_app_id_here        # APP ID from console
DOUBAO_ACCESS_KEY=your_access_token_here  # Access Token from console

# Transcription service selection: "doubao" (default, streaming) or "openai" (batch)
TRANSCRIPTION_SERVICE=doubao

# ============ OpenAI Configuration (Optional, for batch mode) ============
OFFICIAL_OPENAI_API_KEY=sk-proj-xxx

# ============ Local whisper.cpp (Optional, for Win+I) ============
WHISPER_CLI_PATH=/path/to/whisper.cpp/build/bin/whisper-cli
WHISPER_MODEL_PATH=models/ggml-large-v3.bin

# ============ Keyboard & System Configuration ============
TRANSCRIPTIONS_BUTTON=f
TRANSLATIONS_BUTTON=win
SYSTEM_PLATFORM=linux  # mac/linux/win

# Feature switches
CONVERT_TO_SIMPLIFIED=false
ADD_SYMBOL=false
OPTIMIZE_RESULT=false
```

<a id="how-to-get-doubao-api-keys"></a>
**How to get Doubao API keys**:

1. Go to [Volcengine Console - Speech Recognition](https://console.volcengine.com/ark/region:ark+cn-beijing/tts/speechRecognition)
2. Find your **APP ID** and **Access Token** in the "服务接口认证信息" section (see screenshot below)

<p align="center">
  <img src="assets/images/volcengine_doubao_api_keys.png" alt="Volcengine Doubao API Keys" width="800" />
</p>

**Important Notes**:
- **Doubao Streaming ASR** is now the default and recommended transcription service
- Set `TRANSCRIPTION_SERVICE=openai` to use OpenAI batch mode instead

### Quick Start with Aliases (Recommended)

Add these aliases to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
alias whisper_input='cd /path/to/Whisper-Input-Next && ./start.sh'
alias whisper_input_off='tmux send-keys -t whisper-input C-c 2>/dev/null; tmux kill-session -t whisper-input 2>/dev/null'
```

Replace `/path/to/Whisper-Input-Next` with your actual project path.

### Hotkey Instructions

| Hotkey | Function | Service | Features |
|--------|----------|---------|-----------|
| `Win+F` | **Real-time streaming transcription** | Doubao Seed ASR 2.0 (default) | Ultra-low latency, floating preview, text appears as you speak |
| `Win+I` | Local transcription | whisper.cpp | Offline processing, privacy protection |

> **Note**: Set `TRANSCRIPTION_SERVICE=openai` in `.env` to use OpenAI GPT-4o transcribe instead of Doubao for Win+F.

### Status Indicators

The program displays concise status indicators at the cursor position during runtime:

| Status | Meaning | Action |
|--------|---------|--------|
| `0` | Recording | Press hotkey again to stop recording |
| `1` | Transcribing | Please wait for transcription to complete |
| `!` | Transcription failed/error | Press `Win+F` again to retry (audio saved) |

**Design Optimizations**:
- Use concise numeric status, avoid complex emoji symbols
- No system clipboard pollution, display only at cursor position
- Clear and intuitive status, easy to quickly identify

**Retry Mechanism Instructions**:
- When transcription fails, the system saves the recording and displays `!` status
- No need to re-record, simply press `Win+F` to retry
- Retry uses previously saved audio until transcription succeeds

## 📚 Feature Documentation

- [🔊 Audio Archive Feature](./docs/[V3.0.0]_AUDIO_ARCHIVE_FEATURE.md) - *Introduced in v3.0.0*
- [🤖 Kimi Polish Integration](./docs/[DEPRECATED]_KIMI_USAGE.md) - *Deprecated*
- [📊 Status Display Improvements](./docs/[V3.0.0]_STATUS_DISPLAY_IMPROVEMENTS.md) - *Introduced in v3.0.0*
- [🔄 Branch Differences Comparison](./docs/[V3.0.0]_BRANCH_DIFFERENCES.md) - *Introduced in v3.0.0*
- [📋 Version Control Documentation](./docs/[V3.0.0]_VERSION_CONTROL.md) - *Established in v3.0.0*

## 🛠️ Development Status

### ✅ Completed Features
- [x] **Two-pass recognition for higher accuracy** *(NEW in v3.3.0)*
- [x] **Deferred text output with full-context optimization** *(NEW in v3.3.0)*
- [x] **DJI Wireless Mic auto-detection** *(NEW in v3.3.0)*
- [x] **Doubao Streaming ASR integration** *(v3.2.0)*
- [x] **Floating preview window for real-time feedback** *(v3.2.0)*
- [x] OpenAI GPT-4o transcribe integration
- [x] Audio archive system
- [x] Local whisper support
- [x] Dual processor architecture
- [x] Smart retry mechanism
- [x] Project documentation improvement
- [x] 10-minute recording limit protection
- [x] Status indicator delay optimization
- [x] Audio format conversion support (m4a to wav)
- [x] Bilingual documentation system
- [x] GPT-4o terminology standardization

### 🚧 In Development  
*No features currently in development*

### 📋 Planned Features
*No features currently planned*

### 🧪 Experimental Features History

#### iOS Keyboard Extension Experiment (August 14, 2025)
**Status**: ❌ Discontinued due to Apple's restrictions  
Attempted to create iOS keyboard extension but discovered that even Sogou Input Method cannot directly record audio in keyboard extensions due to Apple's system limitations. iOS voice input is currently not feasible as a seamless keyboard extension.

## 🤝 Contributing Guidelines

We welcome all forms of contributions! Whether it's:

- 🐛 **Bug Reports**: Found an issue? [Create an Issue](https://github.com/Mor-Li/Whisper-Input-Next/issues)
- 💡 **Feature Suggestions**: Have great ideas? [Start a Discussion](https://github.com/Mor-Li/Whisper-Input-Next/discussions)
- 📝 **Code Contributions**: Submit Pull Requests
- 📚 **Documentation Improvements**: Help improve documentation
- 🌍 **Translations**: Help translate to more languages

### Development Environment Setup

```bash
# Clone repository
git clone https://github.com/Mor-Li/Whisper-Input-Next.git
cd Whisper-Input-Next

# Create development environment
uv venv --python 3.12
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Start development
python main.py
```

## 🙏 Acknowledgments

- Thanks to [ErlichLiu/Whisper-Input](https://github.com/ErlichLiu/Whisper-Input) for the original project foundation
- Thanks to [ByteDance/Volcengine](https://www.volcengine.com/) for the excellent Doubao Seed ASR 2.0 streaming API
- Thanks to OpenAI for providing excellent transcription API services
- Thanks to [whisper.cpp](https://github.com/ggerganov/whisper.cpp) community for local processing support
- Thanks to all contributors and users for their support

## 📞 Contact Information

- **Project Address**: https://github.com/Mor-Li/Whisper-Input-Next  
- **Issue Reports**: [Issues](https://github.com/Mor-Li/Whisper-Input-Next/issues)
- **Feature Suggestions**: [Discussions](https://github.com/Mor-Li/Whisper-Input-Next/discussions)

## 📋 Changelog

### v3.3.0 (2026-03-11)
- **Two-pass recognition**: Enable `enable_nonstream` for sentence-level re-recognition with nostream model, significantly improving accuracy (e.g. "广告位" → "光标位置")
- **Deferred text output**: All text stays in floating preview during recording; final text pasted only after stop, allowing full ASR context optimization
- **DJI Wireless Mic support**: Auto-detect and prioritize DJI Wireless Microphone as highest priority input device
- **Lower latency**: Reduce streaming chunk size from 200ms to 100ms
- **Faster streaming**: Remove artificial delays in audio packet sending

### v3.2.0 (2025-07-27)
- **Doubao Streaming ASR**: Real-time streaming transcription powered by ByteDance Seed ASR 2.0
- **Floating preview window**: Shows pending text in real-time near input field
- **Auto audio device switching**: Priority-based microphone selection

### v3.0.0
- OpenAI GPT-4o transcribe integration
- Audio archive system
- Local whisper.cpp support
- Dual processor architecture

---

**⭐ If this project helps you, please give it a Star for support!**
