"""
命令行交互界面
"""
import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from chatbot import AIAssistant

app = typer.Typer()
console = Console()


def print_welcome():
    """打印欢迎信息"""
    welcome_text = """
# 🤖 智能聊天助手

**功能特性：**
- ✅ 实时网络搜索
- ✅ 上下文对话记忆
- ✅ 智能问答

**可用命令：**
- `/help` - 显示帮助信息
- `/clear` - 清除对话历史
- `/exit` 或 `/quit` - 退出程序

**提示：** 询问最新信息时，我会自动搜索网络！
    """
    console.print(Panel(Markdown(welcome_text), title="欢迎", border_style="green"))


def print_help():
    """打印帮助信息"""
    help_text = """
## 📚 使用指南

### 基本对话
直接输入你的问题即可，例如：
- "什么是人工智能？"
- "今天的天气怎么样？"

### 网络搜索
询问最新信息时会自动触发搜索：
- "2024年世界杯冠军是谁？"
- "最新的 iPhone 有什么新功能？"
- "今天的热门新闻有哪些？"

### 命令列表
- `/help` - 显示此帮助信息
- `/clear` - 清除对话历史，开始新对话
- `/exit` 或 `/quit` - 退出程序

### 技巧
- 问题越具体，回答越准确
- 可以追问和深入讨论话题
- 对话会保持上下文记忆
    """
    console.print(Panel(Markdown(help_text), title="帮助", border_style="blue"))


@app.command()
def chat():
    """
    启动聊天机器人
    """
    print_welcome()
    
    try:
        # 初始化 AI 助手
        with console.status("[bold green]正在初始化 AI 助手...", spinner="dots"):
            bot = AIAssistant()
        
        console.print("\n✨ 初始化完成！开始对话吧！\n", style="bold green")
        
        # 主循环
        while True:
            try:
                # 获取用户输入
                user_input = Prompt.ask("\n[bold cyan]你[/bold cyan]")
                
                if not user_input.strip():
                    continue
                
                # 处理命令
                if user_input.lower() in ['/exit', '/quit']:
                    console.print("\n👋 再见！", style="bold yellow")
                    break
                elif user_input.lower() == '/help':
                    print_help()
                    continue
                elif user_input.lower() == '/clear':
                    bot.reset_memory()
                    continue
                
                # 获取回复
                with console.status("[bold green]思考中...", spinner="dots"):
                    response = bot.chat(user_input)
                
                # 显示回复
                console.print(f"\n[bold green]Christina[/bold green]")
                console.print(Panel(Markdown(response), border_style="green"))
                
            except KeyboardInterrupt:
                console.print("\n\n👋 再见！", style="bold yellow")
                break
            except Exception as e:
                console.print(f"\n❌ 出错了：{str(e)}", style="bold red")
                console.print("提示：输入 /help 查看帮助", style="yellow")
    
    except ValueError as e:
        console.print(f"\n❌ 配置错误：{str(e)}", style="bold red")
        console.print("\n💡 请按照以下步骤配置：", style="yellow")
        console.print("1. 复制 .env.example 为 .env")
        console.print("2. 在 .env 中填入你的 API Key")
        console.print("3. 重新运行程序")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n❌ 初始化失败：{str(e)}", style="bold red")
        raise typer.Exit(1)


@app.command()
def version():
    """显示版本信息"""
    console.print("📦 智能聊天助手 v1.0.0", style="bold blue")
    console.print("基于 LangChain 构建", style="dim")


if __name__ == "__main__":
    app()

