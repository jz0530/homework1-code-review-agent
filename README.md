# CodeReview Agent：代码审查助手

Homework 1 课程项目。作者：程悠洋；学号：2412190609。

## 项目说明

本项目选择“代码审查 Agent”方向。用户在命令行提出问题，模型自主选择文件读取或 Python 静态检查工具，程序执行工具并回传结果，模型据此生成中文审查报告。支持追问、最近三轮会话记忆、失败重试和步数限制。

Python 3.10 及以上即可运行，全部使用标准库，无需 pip 安装。实现不依赖 Agent 框架，采用 LLM 原生兼容 HTTP API。

## 快速体验（无需密钥）

在本项目目录打开终端：

```powershell
python agent.py --demo
python -m unittest -v
```

离线演示由固定脚本调用真实的 read_file 和 check_python 工具，并打印工具结果。它只演示 examples/buggy.py 的流程，输出明确标注“非模型审查”，不能作为真实模型接入成功的证据，也不支持任意问题。

## 真实模型模式

默认使用 DeepSeek 官方 API，基础地址为 `https://api.deepseek.com`，模型为 `deepseek-flash`。在 https://platform.deepseek.com 创建 API Key。当前默认值依据2026年10月6日查阅的官方文档，模型可通过环境变量调整。

PowerShell 设置当前窗口环境变量：

```powershell
$env:LLM_API_KEY = Read-Host '输入你自己的 API Key'
$env:LLM_BASE_URL = 'https://api.deepseek.com'
$env:LLM_MODEL = 'deepseek-flash'
python agent.py --root examples --ask '请审查 buggy.py，指出问题、触发条件、行号，并给出修改建议'
```

密钥仅由环境变量读取，不写入代码。`Read-Host` 输入在本地终端可见，请勿录屏这一段。API 调用可能产生费用，发给模型的源码应限于允许上传的作业文件。程序不自动加载 .env 文件。

也可以运行 `python configure_deepseek.py`，按隐藏输入提示粘贴密钥，脚本会在当前进程内完成设置并启动交互模式，无需手写环境变量，密钥不保存到磁盘。

DeepSeek 请求显式关闭思考模式，每次请求输出上限2000 tokens，每个问题最多六次模型请求。此设置用于控制作业测试费用，不是账户金额的硬性限额。最近三轮对话及工具返回会再次计入输入。若50元是官方API账户可用余额，少量样例审查与演示通常足够，实际扣费以控制台账单为准。

连续对话：

```powershell
python agent.py --root examples
```

建议依次输入：

1. `审查 buggy.py，先读取代码并检查 Python 语法。`
2. `刚才可变默认参数的问题会在什么情况下触发？给一个例子。`
3. `读取 fixed.py，比较修改前后的行为。`

`/clear` 清除记忆，`/exit` 退出。审查其他项目时用 `--root` 指定源码目录，问题中使用相对于该目录的路径。

## 功能与边界

| 功能 | 实现 |
| --- | --- |
| Agent 循环 | 用户输入、模型决策、工具执行、结果回传、最终回答 |
| 工具 | list_files、read_file、check_python |
| 交互 | 单次 --ask 或持续命令行会话 |
| 记忆 | 保留最近三轮完整成功对话，退出后不持久化 |
| 容错 | 网络超时、429及部分5xx最多尝试三次；参数错误转为工具结果 |
| 限制 | 每轮最多六次模型请求，每次最多八个工具调用 |

源码读取限制为 UTF-8、单文件32KB；目录最多列出200个文件。仅支持列出的源码扩展名，不读隐藏路径及常见依赖目录，禁止读取根目录外的文件。check_python 仅支持 Python，检测语法、裸 except 和可变默认参数字面量。其他逻辑问题主要依赖模型理解。

本工具不执行用户代码、不写源码、不自动修复。语法通过不代表逻辑无误；模型建议需人工验证。文件路径检查适用于普通本地作业使用，不是对抗恶意并发文件修改的操作系统沙箱。

## 文件结构

```text
agent.py             工具、API客户端、Agent循环、命令行入口
configure_deepseek.py 隐藏输入密钥并启动DeepSeek模式
test_agent.py        离线自动化测试
examples/buggy.py    含问题示例
examples/fixed.py    修复对照示例
README.md            项目说明与运行方式
Design.md            架构及设计说明
DEMO.md              一分钟演示脚本
requirements.txt     无第三方依赖说明
```

## 常见问题

- 提示配置变量：在运行程序的同一个终端配置 LLM_API_KEY 和 LLM_BASE_URL。
- HTTP 401：检查密钥。HTTP 402：检查余额。HTTP 404：检查基础地址和模型名称。HTTP 429：检查限流。
- 不支持 tools：换用支持 function calling 的模型或服务接口。
- Python 找不到：先安装 Python 3.10+，也可以尝试 Windows 的 `py` 命令。
- 文件超限：将需要审查的函数另存到专用源码目录。

## 提交说明

提交压缩包名为 `2412190609程悠洋.zip`（若教师只接收 rar，请自行另存为 rar）。PPT 的备份提交位置为 `001Homework1`，截止时间为2026年10月7日24点，压缩包小于200MB。演示视频可选，时长不超过一分钟。不要将真实密钥打入提交包。

自动化测试使用离线 mock 验证流程与接口配置，不代表真实服务联调通过。运行真实模型模式时需使用自己的 API Key 并检查结果。

## 技术参考

DeepSeek 官方接口、工具调用及计费文档：
https://api-docs.deepseek.com/quick_start
https://api-docs.deepseek.com/guides/tool_calls/
https://api-docs.deepseek.com/quick_start/pricing/

作业范围与提交要求来自用户提供的 Homework 1.pptx 第2—4页。
