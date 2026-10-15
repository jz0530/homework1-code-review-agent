"""输入 DeepSeek 密钥后启动助手，密钥不保存到文件。"""
import getpass
import os

from agent import main


if __name__ == '__main__':
    try:
        key = getpass.getpass('请输入 DeepSeek API Key（输入不显示）：').strip()
    except (EOFError, KeyboardInterrupt):
        raise SystemExit('\n已取消')
    if not key:
        raise SystemExit('密钥不能为空')
    os.environ['LLM_API_KEY'] = key
    os.environ['LLM_BASE_URL'] = 'https://api.deepseek.com'
    os.environ['LLM_MODEL'] = 'deepseek-flash'
    raise SystemExit(main())
