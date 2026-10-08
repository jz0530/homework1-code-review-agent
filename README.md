# 代码审查助手

软件项目实践 Homework 1

姓名：程悠洋  
学号：2412190609

GitHub 仓库：https://github.com/jz0530/homework1-code-review-agent

## 项目介绍

这个项目做的是一个命令行代码审查助手，使用 Python 和 DeepSeek API。输入要审查的文件后，助手可以读取代码、检查 Python 语法，再给出问题分析和修改建议。也可以继续追问，比如某个问题为什么会出现、应该怎么改。

## 运行方法

需要 Python 3.10 或以上版本，不需要安装第三方库。

先进入项目文件夹，在终端运行：

```bash
python configure_deepseek.py
```

按提示输入自己的 DeepSeek API Key，输入时不会显示字符。进入 `你 >` 提示后，可以输入：

```text
请审查 buggy.py，先读取代码并检查语法，再指出问题和修改建议。
```

默认审查 `examples` 文件夹。示例里的 `buggy.py` 有空列表除零、可变默认参数两个问题，`fixed.py` 是修改后的对照代码。得到回答后，可以继续输入：

```text
可变默认参数为什么会出问题？举个例子。
```

输入 `/clear` 清除对话记录，输入 `/exit` 退出。API Key 不会保存到项目文件中。

如果要审查其他文件夹，可以这样启动，然后在问题里填写相对路径：

```bash
python configure_deepseek.py --root "你的代码文件夹路径"
```

## 主要实现

程序的流程是：接收问题，调用模型，执行模型选择的工具，再把工具结果传回模型，最后输出回答。一轮里可以多次调用工具。

目前有三个工具：

- `list_files`：列出目录中的源码文件。
- `read_file`：读取代码，并给每一行标上行号。
- `check_python`：检查 Python 语法，以及裸 except、可变默认参数等简单问题。

程序保留最近三轮成功对话，方便继续追问。网络请求失败时会对部分错误进行重试，每个问题最多调用模型六次，避免一直循环。

## 文件说明

```text
agent.py               主程序、模型调用和工具实现
configure_deepseek.py   输入密钥并启动助手
test_agent.py           自动化测试
examples/buggy.py       有问题的示例代码
examples/fixed.py       修改后的示例代码
Design.md              设计说明
DEMO.md                演示步骤
```

## 测试

运行自动化测试：

```bash
python -m unittest -v
```

测试包括工具调用、文件访问限制、对话记录、错误重试和示例函数的边界情况。接口测试使用模拟响应，不需要密钥，也不会产生 API 费用。

没有密钥时，也可以运行：

```bash
python agent.py --demo
```

这个模式通过固定样例展示工具调用过程，不能代替真实的模型审查。

## 目前的不足

语法检查只支持 Python，复杂的逻辑问题还需要模型分析。程序只读取和分析代码，不会执行代码或直接修改文件。每个文件最多读取 32KB，所以暂时更适合审查小文件。模型给出的建议也需要自己检查。

## 参考资料

[DeepSeek API 文档](https://api-docs.deepseek.com/quick_start)
