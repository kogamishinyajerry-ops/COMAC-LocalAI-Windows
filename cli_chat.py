#!/usr/bin/env python3
"""
OpenCode TUI — COMAC 离轴线AI文档处理平台
驱动模型: qwen:7b-q4_K_M

用法:
  python cli_chat.py                       # 默认模型 qwen:7b-q4_K_M
  python cli_chat.py --model qwen:7b-q4_K_M  # 指定模型
  python cli_chat.py --system "你是一个..."   # 自定义系统提示词
"""

import sys
import os

# ---------------------------------------------------------------------------
# 路径设置 — 优先从项目根目录加载 config（兼容 .venv 和系统 Python）
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# ---------------------------------------------------------------------------
# 颜色支持（跨平台 ANSI）
# ---------------------------------------------------------------------------
try:
    import ollama
except ImportError:
    print("[错误] 无法导入 ollama Python 包，请先运行 setup.bat 安装依赖。", file=sys.stderr)
    sys.exit(1)

try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init(autoreset=True)
    _HAS_COLOR = True
except ImportError:
    # 降级：无颜色支持
    class _DummyColor:
        RED = YELLOW = CYAN = GREEN = MAGENTA = BLUE = WHITE = RESET = RESET_SIMULATED = ""
        DIM = BRIGHT = ""
    Fore = _DummyColor()
    Style = _DummyColor()
    _HAS_COLOR = False

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
import argparse
from typing import List, Dict, Optional

# 延迟导入 config（避免顶层错误时阻断帮助信息）
_cfg = None

def _load_config():
    global _cfg
    if _cfg is not None:
        return _cfg
    try:
        from config import MODEL_DOC, OLLAMA_HOST, DEFAULT_NUM_CTX, DEFAULT_NUM_PREDICT
        _cfg = {
            "model": MODEL_DOC,
            "host": OLLAMA_HOST,
            "ctx": DEFAULT_NUM_CTX,
            "predict": DEFAULT_NUM_PREDICT,
        }
    except Exception:
        _cfg = {
            "model": os.environ.get("COMAC_MODEL", "qwen:7b-q4_K_M"),
            "host": os.environ.get("OLLAMA_HOST", "127.0.0.1:11435"),
            "ctx": 8192,
            "predict": 2048,
        }
    return _cfg


# ---------------------------------------------------------------------------
# 流式对话
# ---------------------------------------------------------------------------
def chat_stream(
    model: str,
    messages: List[Dict[str, str]],
    system: Optional[str] = None,
    host: str = "127.0.0.1:11435",
):
    """
    通过 ollama API 流式对话（直接使用 ollama Python 包的底层实现，
    不走 OllamaClient wrapper，以支持 stream=True）
    """
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    try:
        response = ollama.chat(
            model=model,
            messages=full_messages,
            stream=True,
            options={
                "temperature": 0.3,
                "num_ctx": _load_config()["ctx"],
            },
        )
        for chunk in response:
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content
    except Exception as e:
        yield f"\n{Fore.RED}[连接错误] {e}{Style.RESET_ALL}"


# ---------------------------------------------------------------------------
# 特殊命令处理
# ---------------------------------------------------------------------------
SPECIAL_COMMANDS = {
    "/exit": "退出",
    "/quit": "退出",
    "/clear": "清屏",
    "/history": "查看历史",
    "/help": "显示帮助",
    "/model": "切换模型",
}


def is_special_cmd(text: str) -> bool:
    return text.strip().lower() in SPECIAL_COMMANDS


def handle_special_cmd(text: str, messages: List[Dict], current_model: str) -> Optional[str]:
    """处理特殊命令，返回 None 表示退出程序，否则返回提示信息"""
    cmd = text.strip().lower()

    if cmd in ("/exit", "/quit"):
        print(f"\n{Fore.YELLOW}再见！{Style.RESET_ALL}\n")
        sys.exit(0)

    elif cmd == "/clear":
        os.system("cls" if os.name == "nt" else "clear")
        return None

    elif cmd == "/history":
        for i, m in enumerate(messages):
            role = m.get("role", "?")
            content = m.get("content", "")
            color = Fore.CYAN if role == "user" else Fore.GREEN if role == "assistant" else Fore.YELLOW
            print(f"{color}[{role}]{Style.RESET_ALL} {content[:200]}")
        return ""

    elif cmd == "/help":
        print(f"""
{Fore.CYAN}╔══════════════════════════════════════════╗
║         OpenCode TUI 帮助                  ║
╚══════════════════════════════════╝{Style.RESET_ALL}

  {Fore.GREEN}/exit{Style.RESET_ALL}, {Fore.GREEN}/quit{Style.RESET_ALL}   — 退出程序
  {Fore.GREEN}/clear{Style.RESET_ALL}       — 清屏
  {Fore.GREEN}/history{Style.RESET_ALL}     — 查看对话历史
  {Fore.GREEN}/help{Style.RESET_ALL}        — 显示帮助
  {Fore.GREEN}/model <m>{Style.RESET_ALL}   — 切换模型（示例: /model qwen:7b-q4_K_M）

  直接输入内容即可对话。
  按 {Fore.YELLOW}Ctrl+C{Style.RESET_ALL} 可随时终止生成。
""")
        return ""

    elif cmd.startswith("/model "):
        new_model = text.strip()[7:].strip()
        if not new_model:
            print(f"{Fore.RED}[错误] 请指定模型名，如: /model qwen:7b-q4_K_M{Style.RESET_ALL}")
            return ""
        print(f"{Fore.GREEN}[模型切换] 当前模型: {new_model}{Style.RESET_ALL}")
        return new_model  # 返回新模型名

    return None


# ---------------------------------------------------------------------------
# 主循环
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="OpenCode TUI — 终端 AI 对话界面",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli_chat.py
  python cli_chat.py --model qwen:7b-q4_K_M
  python cli_chat.py --system "你是一个航空领域专家"
        """,
    )
    parser.add_argument(
        "--model",
        "-m",
        default=None,
        help=f"指定模型（默认: qwen:7b-q4_K_M）",
    )
    parser.add_argument(
        "--system",
        "-s",
        default=None,
        help="系统提示词（可选）",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Ollama 服务地址（默认: 127.0.0.1:11435）",
    )
    args = parser.parse_args()

    cfg = _load_config()
    current_model = args.model or cfg["model"]
    system_prompt = args.system or (
        "你是一个智能助手，专注于文档处理和分析任务。"
        "擅长理解用户需求、生成报告、提炼要点、校对文字。"
        "请用简洁专业的语言回复。"
    )

    if args.host:
        os.environ["OLLAMA_HOST"] = args.host

    # ---------------------------------------------------------------------------
    # 欢迎横幅
    # ---------------------------------------------------------------------------
    print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════╗
║                                                      ║
║   {Fore.WHITE}OpenCode TUI — COMAC 离轴线AI文档处理平台{Fore.CYAN}   ║
║                                                      ║
║   {Fore.YELLOW}模型: {current_model}{Fore.CYAN}                               ║
║   {Fore.YELLOW}Ollama: {cfg['host']}{Fore.CYAN}                          ║
║                                                      ║
║   {Fore.WHITE}输入 /help 查看帮助，输入 /exit 退出{Style.RESET_ALL}            ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
""")

    # ---------------------------------------------------------------------------
    # 预检 Ollama 连接
    # ---------------------------------------------------------------------------
    try:
        ollama.list()
    except Exception as e:
        print(f"{Fore.RED}[错误] 无法连接 Ollama 服务 ({e}){Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[提示] 请确保已运行 start.bat 启动 Ollama 服务，或运行 setup.bat 初始化环境。{Style.RESET_ALL}")
        sys.exit(1)

    messages: List[Dict[str, str]] = []
    history_max = 100  # 最多保留 100 轮

    # ---------------------------------------------------------------------------
    # 主对话循环
    # ---------------------------------------------------------------------------
    while True:
        try:
            try:
                user_input = input(f"{Fore.GREEN}>>> {Style.RESET_ALL}").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{Fore.YELLOW}再见！{Style.RESET_ALL}\n")
                break

            if not user_input:
                continue

            # 特殊命令
            if is_special_cmd(user_input):
                result = handle_special_cmd(user_input, messages, current_model)
                if result is None:
                    continue  # 清屏等命令无返回值
                elif isinstance(result, str) and result != "":
                    # 返回的是新模型名
                    current_model = result
                continue

            # 普通对话
            messages.append({"role": "user", "content": user_input})

            print(f"{Fore.DIM}{'─' * 40}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}[{current_model}]{Style.RESET_ALL} ", end="", flush=True)

            full_response = ""
            try:
                for token in chat_stream(
                    model=current_model,
                    messages=messages,
                    system=system_prompt,
                    host=cfg["host"],
                ):
                    print(token, end="", flush=True)
                    full_response += token
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}[已终止生成]{Style.RESET_ALL}")
                # 保留用户消息，不添加 assistant 响应
                messages.pop()  # 移除刚加入的用户消息，避免历史不完整
                continue

            print()  # 换行
            messages.append({"role": "assistant", "content": full_response})

            # 限制历史长度
            if len(messages) > history_max * 2:
                messages[:] = messages[-(history_max * 2):]

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}[输入已取消]{Style.RESET_ALL}")
            continue
        except EOFError:
            break


if __name__ == "__main__":
    main()
