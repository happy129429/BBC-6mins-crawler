# BBC-6mins-crawler BBC六分钟英语爬虫

语言：[English](README.md) / [简体中文](README-zh.md)

## 简介

这是一套 Python 脚本，用于从 BBC 官网批量抓取 BBC学英语六分钟英语（BBC Learning English's 6 Minute English）栏目的节目元数据、文字稿和媒体文件，满足个人英语学习中节目保存与离线学习的需求。

工作流程分两个相对独立的步骤：

1. **JSON 生成器**（`scripts/json_generator.py`）：抓取栏目主页的节目元数据（标题、链接、日期、简介），以**增量合并**的方式写入 JSON 文件——已有记录中的 `media_download_url`、`local_media_path` 等下载进度字段**永不被覆盖**，可放心反复运行。
2. **下载器**（`scripts/downloader.py`）：读取 JSON，按日期从旧到新逐期下载文字稿（清洗后保存为 txt）和媒体文件，并将下载结果回写 JSON。已完成的节目自动跳过，中断后可续跑。

## 项目结构

```
BBC-6mins-crawler/
├── .gitignore              # 忽略字节码缓存、日志、下载产物等
├── LICENSE                 # GPL-3.0
├── README.md               # 英文说明
├── README-zh.md            # 中文说明（本文件）
├── requirements.txt        # 运行依赖
├── requirements-dev.txt    # 开发/测试依赖
├── pytest.ini              # 测试配置
├── scripts/
│   ├── config.py           # 配置集中管理（保存路径、开关、超时、重试等）
│   ├── utils.py            # 公共工具（文件名清洗、文字稿清理、媒体链接提取、重试、日志）
│   ├── json_generator.py   # 元数据抓取 + 增量合并
│   └── downloader.py       # 文字稿/媒体下载器
└── tests/                  # 离线单元测试（pytest + 本地 HTML fixtures）
```

## 环境要求

- Python 3.8+（开发与测试环境为 Python 3.12）
- 运行依赖：`requests`、`beautifulsoup4`
- 可选外部工具：
  - **ffmpeg**：从视频提取音频时需要；缺失时该功能自动降级跳过
  - **yt-dlp**：处理"没有下载直链、只提供 mpd 流媒体清单"的页面时需要；缺失时此类页面会记录失败并跳过

## 安装

```bash
pip install -r requirements.txt
```

开发与运行测试：

```bash
pip install -r requirements-dev.txt
```

## 使用方法

在项目根目录下按顺序运行两个脚本（JSON 文件与日志默认生成在工作目录）：

```bash
# 第一步：抓取/增量更新元数据（重复运行安全，不会丢失已有下载进度）
python3 scripts/json_generator.py

# 第二步：下载文字稿与媒体（已完成的节目自动跳过）
python3 scripts/downloader.py
```

Windows 下将 `python3` 换成 `python` 即可。终端输出默认为简体中文。

**保存目录**：默认下载到当前工作目录下的 `downloads/`。两种自定义方式：

```bash
# 方式一：环境变量（推荐，无需改代码）
# Linux / macOS
BBC6_SAVE_DIR=/home/me/BBC6minute python3 scripts/downloader.py
# Windows (PowerShell)
$env:BBC6_SAVE_DIR='D:\BBC6minute'; python scripts\downloader.py

# 方式二：修改 scripts/config.py 中的默认值
```

**输出语言**：终端与日志文案默认为简体中文。两种切换为英文的方式：

```bash
# 方式一：环境变量临时切换（仅本次运行生效）
# Linux / macOS
BBC6_LANG=en python3 scripts/downloader.py
# Windows (PowerShell)
$env:BBC6_LANG='en'; python scripts\downloader.py

# 方式二：修改 scripts/config.py 中的 OUTPUT_LANGUAGE = "en"（持久生效）
```

其余可调项（每次最多处理条数 `MAX_ITEMS`、是否从视频提取音频、是否保留原视频、请求超时与重试次数等）集中在 `scripts/config.py`。

## 媒体下载策略

下载器按以下顺序为每期节目寻找媒体，任一环节成功即停止：

1. 页面下载区的直链，按 URL 真实扩展名识别并保存（音频 `.mp3/.wav/.m4a/.aac`，视频 `.mp4` 等）；
2. 页面 `<audio>/<video>` 标签及 `data-media` 属性中的直链；
3. 均无直链时，扫描页面中的 **mpd 流媒体清单**，交给 `yt-dlp` 下载，再用 `ffmpeg` 提取音频（对应人工流程：F12 找到 mpd → yt-dlp → ffmpeg）。

视频文件默认自动提取为 mp3 音频并删除原视频（可在 `config.py` 关闭或保留）。

## 日志

两个脚本在终端输出的同时，将日志分别写入工作目录下的 `json_generator.log` 与 `downloader.log`，便于事后排查（如 VPN 掉线、个别页面解析失败等）。

## 运行测试

```bash
python3 -m pytest
```

测试全部离线运行（基于 `tests/fixtures/` 中的本地 HTML 样本），不访问 BBC 网络。

## 已知限制

- `json_generator` 目前只抓取栏目主页可见的条目，不自动翻页；
- BBC 页面结构变化可能导致解析失败，此时需更新 `scripts/utils.py` 中的选择器（`tests/fixtures/` 的样本可作为回归参照）；
- mpd 页面依赖 `yt-dlp`，视频转音频依赖 `ffmpeg`，二者缺失时对应功能自动跳过并在日志中说明；
- 项目不内置任何 VPN/代理配置，网络问题请自行解决。

## 改进方向

- [x] 规范代码表述与文件命名（拆分 config/utils，消除重复导入）
- [x] 元数据 JSON 增量更新，不覆盖已生成的下载地址
- [x] 日志输出到文件
- [x] 适配 .wav/.m4a 等音频格式（按真实扩展名保存）
- [x] mpd 页面经 yt-dlp 下载 + ffmpeg 提取
- [x] 跨平台路径（Linux/Windows/macOS）
- [x] 离线单元测试
- [x] 终端输出语言可配置（英文）
- [ ] 通过 RSS/podcast 订阅获取节目（替代爬虫的备选思路）
- [ ] 自动翻页抓取全部历史节目
- [ ] 请求限速与断点续传

## AI 辅助声明

本简易爬虫项目主体代码由 AI 辅助生成（初版：DeepSeek LLM；2026 年 8 月重构：GLM）。人类作者提出了本项目的基本设想，并在 AI 辅助下承担了代码审查和调试工作。

## 开放源代码声明

本项目源代码在 GNU通用公共许可证3.0版本（the GNU General Public License v3.0）下开源。BBC内容，包括音频和文字稿，不是本项目的一部分，因此不适用该许可证。

## 版权声明

本项目不隶属于英国广播公司（BBC），也不由其背书。所有BBC内容均归其各自的权利持有人所有。如果您是权利持有人，并对本项目或其内容分发有任何顾虑，请联系我，我将及时删除或修改相关材料。
