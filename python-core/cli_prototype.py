import asyncio
import time
from typing import List

import typer
from rich.console import Console, Group
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.align import Align
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich import box

console = Console()
app = typer.Typer()

# --- THEME COLORS ---
COLOR_PRIMARY = "cyan"
COLOR_SECONDARY = "green"
COLOR_THINKING = "grey50"
COLOR_USER = "bright_white"
COLOR_SYSTEM = "yellow"

def clear_screen():
    console.clear()

def print_header():
    header = Text("SIGMA AGENT CLI", style=f"bold {COLOR_PRIMARY}")
    subtitle = Text("Advanced Reasoning Terminal", style=f"italic {COLOR_SECONDARY}")
    
    grid = Align.center(Group(header, subtitle))
    console.print(Panel(grid, border_style=COLOR_PRIMARY, box=box.ROUNDED))

def select_model() -> str:
    """Simulates a model selection menu"""
    console.print(f"\n[{COLOR_SYSTEM}]Select Reasoning Model:[/{COLOR_SYSTEM}]")
    console.print("1. [bold]Gemini 3 Pro Preview[/bold] (Best Reasoning)")
    console.print("2. [bold]Gemini 3 Flash Preview[/bold] (Fastest)")
    console.print("3. [bold]DeepSeek R1[/bold] (Open Source Reasoning)")
    
    choice = Prompt.ask("Choose", choices=["1", "2", "3"], default="1")
    
    models = {
        "1": "gemini/gemini-3-pro-preview",
        "2": "gemini/gemini-3-flash-preview",
        "3": "deepseek/deepseek-reasoner"
    }
    return models[choice]

async def simulate_streaming_response():
    """Simulates the UI flow of a thinking model"""
    
    # Fake thinking content chunks
    thinking_steps = [
        "Analyzing user request...",
        "Identifying key constraints...",
        "Retrieving context from memory...",
        "Formulating step-by-step plan...",
        "Validating logic against safety guidelines...",
        "Drafting final response..."
    ]
    
    # Fake answer chunks
    answer_content = """Here is a Python function to calculate Fibonacci numbers:

```python
def fib(n):
    if n <= 1: return n
    return fib(n-1) + fib(n-2)
```

This is a recursive implementation. For better performance, consider using memoization.
"""

    # 1. THINKING PHASE
    # We use a Live display that updates the spinner and the thinking log
    
    thinking_log = Text()
    
    with Live(refresh_per_second=10) as live:
        for step in thinking_steps:
            # Update thinking log
            thinking_log.append(f"• {step}\n", style=f"italic {COLOR_THINKING}")
            
            # Create a group with Spinner + Log
            spinner = Spinner("dots", text=Text(" Thinking...", style=COLOR_SECONDARY))
            
            panel = Panel(
                Group(spinner, Text("", ""), thinking_log),
                title="[Reasoning Process]",
                title_align="left",
                border_style=COLOR_THINKING,
                box=box.MINIMAL
            )
            
            live.update(panel)
            await asyncio.sleep(0.8) # Simulate processing time

    # 2. ANSWER PHASE
    # Once thinking is done, we can either:
    # A. Clear the thinking panel and show just the answer
    # B. Collapse the thinking panel
    # C. Leave it as is
    
    # Let's try "Collapsing" effect by just printing a summary line instead of the full log
    console.print(f"[{COLOR_THINKING}]└─ Thought for 4.2 seconds.[/{COLOR_THINKING}]\n")
    
    # Stream the answer
    live_markdown = ""
    with Live(refresh_per_second=15) as live:
        for char in answer_content:
            live_markdown += char
            live.update(Markdown(live_markdown))
            await asyncio.sleep(0.02) # Simulate typing speed

@app.command()
def main():
    clear_screen()
    print_header()
    
    model = select_model()
    console.print(f"\n[{COLOR_SYSTEM}]Loaded Model:[/{COLOR_SYSTEM}] [bold]{model}[/bold]\n")
    
    while True:
        try:
            user_input = Prompt.ask(f"\n[{COLOR_USER}]User[/{COLOR_USER}]")
            
            if user_input.lower() in ["exit", "quit"]:
                break
                
            console.print(f"\n[{COLOR_PRIMARY}]Sigma[/{COLOR_PRIMARY}]")
            asyncio.run(simulate_streaming_response())
            
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    app()
