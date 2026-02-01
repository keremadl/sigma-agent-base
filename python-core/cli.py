import asyncio
import os
import sys
import time
from typing import Optional
from dotenv import load_dotenv

# Load env vars immediately
load_dotenv()

import typer
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.style import Style
from rich.live import Live
from rich.spinner import Spinner
from rich.align import Align
from rich.padding import Padding
from rich.table import Table
from rich import box

# Add app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.llm import generate_with_thinking
from app.services.router import classify_query
from app.services.tools import tools
from app.core.config import settings, MODEL_TIERS
from app.core.prompts import THINKING_PROMPT, CONTEXT_TEMPLATE

# Initialize Typer and Console
console = Console()
app = typer.Typer(help="Sigma Agent CLI", add_completion=False)

# --- THEME CONFIGURATION ---
COLOR_PRIMARY = "cyan"
COLOR_SECONDARY = "green"
COLOR_THINKING = "grey50"
COLOR_USER = "bright_white"
COLOR_SYSTEM = "yellow"
COLOR_ERROR = "red"

ICON_USER = "◆"
ICON_BOT = "◇"

def print_header():
    """Prints the startup header"""
    console.clear()
    header_text = """
   ██████  ██  ██████  ███    ███  █████ 
  ██       ██ ██       ████  ████ ██   ██
  ███████  ██ ██   ███ ██ ████ ██ ███████
       ██  ██ ██    ██ ██  ██  ██ ██   ██
  ███████  ██  ██████  ██      ██ ██   ██
    """
    console.print(Panel(
        Align.center(
            f"{header_text}\n"
            f"[bold {COLOR_SECONDARY}]SIGMA AGENT[/bold {COLOR_SECONDARY}]\n"
            f"[italic {COLOR_THINKING}]Advanced Reasoning Terminal[/italic {COLOR_THINKING}]"
        ),
        border_style=COLOR_PRIMARY,
        box=box.ROUNDED,
        subtitle=f"[{COLOR_THINKING}]Type 'exit' to quit, '/clear' to reset context[/{COLOR_THINKING}]"
    ))

def select_model() -> str:
    """Interactive model selection menu"""
    console.print(f"\n[{COLOR_SYSTEM}]Select Reasoning Model:[/{COLOR_SYSTEM}]")
    console.print("1. [bold]Gemini 3 Pro Preview[/bold] (Best Reasoning)")
    console.print("2. [bold]Gemini 3 Flash Preview[/bold] (Fastest)")
    console.print("3. [bold]Auto Mode (Smart)[/bold] (Dynamic Switching)")
    
    choice = Prompt.ask("Choose", choices=["1", "2", "3"], default="3")
    
    models = {
        "1": "gemini/gemini-3-pro-preview",
        "2": "gemini/gemini-3-flash-preview",
        "3": "auto"
    }
    return models[choice]

async def get_api_key_from_env_or_config(model: str) -> str:
    """Helper to get API key"""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        console.print(f"[{COLOR_ERROR}]Error: No API key found. Set GEMINI_API_KEY in .env[/{COLOR_ERROR}]")
        sys.exit(1)
    return key

async def chat_loop(model: str = None, ask: str = None):
    """Main chat loop"""
    # Only print header if interactive
    if not ask:
        print_header()
    
    if not model:
        if ask:
            model = "auto"
        else:
            model = select_model()
    
    if not ask:
        console.print(f"\n[{COLOR_SYSTEM}]Loaded Model:[/{COLOR_SYSTEM}] [bold]{model}[/bold]")
        console.print(f"[{COLOR_THINKING}]Type 'exit' to quit, '/clear' to reset context[/{COLOR_THINKING}]\n")
    
    history = []
    api_key = await get_api_key_from_env_or_config(model)

    # One-off run logic
    first_run = True if ask else False

    while True:
        try:
            if first_run:
                user_input = ask
            else:
                # 1. Get User Input with Icon
                console.print(f"\n[{COLOR_USER}]{ICON_USER} User[/] ", end="")
                user_input = input() 
            
            if user_input.lower() in ["exit", "quit"]:
                if not first_run:
                    console.print(f"[{COLOR_PRIMARY}]Shutting down...[/{COLOR_PRIMARY}]")
                break
            
            if user_input.lower() == "/clear":
                history = []
                if not first_run:
                    print_header()
                    console.print(f"[{COLOR_THINKING}]Context memory wiped.[/{COLOR_THINKING}]")
                continue

            if not user_input.strip():
                continue

            # 2. Prepare Context & Strategy
            history.append({"role": "user", "content": user_input})
            
            # --- INTELLIGENCE LAYER: Classification & Search ---
            query_type = "complex" # Default
            search_context = ""
            
            # Create a status spinner for pre-computation
            with console.status(f"[{COLOR_SECONDARY}]Analyzing request...[/{COLOR_SECONDARY}]", spinner="dots") as status:
                try:
                    # Classify query
                    query_type = await classify_query(user_input, api_key)
                    
                    if query_type == "factual":
                        status.update(f"[{COLOR_SECONDARY}]Searching web...[/{COLOR_SECONDARY}]")
                        # Run search in thread
                        tools._initialize_client() 
                        search_results = await asyncio.to_thread(tools.search_web, user_input)
                        
                        if search_results and "unavailable" not in search_results:
                            search_context = f"\n\nWEB SEARCH RESULTS:\n{search_results}\n"
                            
                except Exception as e:
                    # Fail silently on router/search errors, proceed to chat
                    pass

            # --- DYNAMIC MODEL SELECTION (Auto Mode) ---
            if model == "auto":
                if query_type == "complex":
                    current_model = MODEL_TIERS["pro"]
                else:
                    current_model = MODEL_TIERS["fast"]
            else:
                current_model = model

            # Strategy based on CURRENT model:
            is_deepseek = "deepseek" in current_model.lower() or "r1" in current_model.lower()
            is_flash = "flash" in current_model.lower()
            
            if is_deepseek or is_flash:
                system_prompt = "You are a helpful AI assistant."
            else:
                system_prompt = THINKING_PROMPT # Force Gemini Pro to think

            # Inject search context if available
            if search_context:
                system_prompt += f"\n{search_context}\nUse these search results to answer the user's question accurately."

            # Determine if we expect thinking chunks
            expect_thinking = is_deepseek or (not is_flash)

            messages = [
                {"role": "system", "content": system_prompt},
                *history[-10:] 
            ]

            # 3. Stream Response with LIVE MARKDOWN rendering
            current_answer = ""
            thinking_buffer = ""
            start_time = time.time()
            
            # START LIVE DISPLAY (Instant Feedback)
            
            # Initial view placeholder
            header_grid = Table.grid(padding=(0, 1))
            
            if expect_thinking:
                header_grid.add_row(
                    Text(f"{ICON_BOT} Sigma", style=COLOR_PRIMARY),
                    Spinner("dots", style=COLOR_SECONDARY),
                    Text("Thinking...", style=COLOR_SECONDARY)
                )
            else:
                header_grid.add_row(Text(f"{ICON_BOT} Sigma", style=COLOR_PRIMARY))
            
            # Use Live display
            with Live(Padding(header_grid, (1, 0, 0, 0)), refresh_per_second=8, vertical_overflow="ellipsis") as live:
                is_thinking_phase = True
                final_thinking_panel = None
                
                async for chunk in generate_with_thinking(
                    messages,
                    model=current_model,
                    api_key=api_key,
                    include_thinking=expect_thinking,
                    temperature=0.6 if expect_thinking else 0.7
                ):
                    section = chunk.get("section")
                    content = chunk.get("content")
                    
                    if section == "thinking":
                        thinking_buffer += content
                        
                    elif section == "answer":
                        if is_thinking_phase:
                            is_thinking_phase = False
                            # Create static thinking panel
                            if thinking_buffer.strip():
                                duration = time.time() - start_time
                                final_thinking_panel = Panel(
                                    Text(thinking_buffer.strip(), style=f"italic {COLOR_THINKING}"),
                                    title=f"[Reasoning: {duration:.1f}s]",
                                    title_align="left",
                                    border_style=COLOR_THINKING,
                                    box=box.MINIMAL,
                                    expand=False
                                )
                        
                        current_answer += content
                    
                    elif section == "error":
                        live.stop()
                        console.print(f"[{COLOR_ERROR}]{content}[/{COLOR_ERROR}]")
                        break

                    # --- COMPOSING THE VIEW ---
                    view_group = []
                    
                    # 1. Header
                    header_grid = Table.grid(padding=(0, 1))
                    
                    if is_thinking_phase and expect_thinking:
                        header_grid.add_row(
                            Text(f"{ICON_BOT} Sigma", style=COLOR_PRIMARY),
                            Spinner("dots", style=COLOR_SECONDARY),
                            Text("Thinking...", style=COLOR_SECONDARY)
                        )
                    else:
                        header_grid.add_row(Text(f"{ICON_BOT} Sigma", style=COLOR_PRIMARY))
                    
                    view_group.append(Padding(header_grid, (1, 0, 0, 0)))
                    
                    # 2. Thinking Panel
                    if expect_thinking:
                        if is_thinking_phase:
                            if thinking_buffer:
                                visible_thinking = thinking_buffer[-800:]
                                active_panel = Panel(
                                    Text(visible_thinking, style=f"italic {COLOR_THINKING}"),
                                    title="[Reasoning Process]",
                                    title_align="left",
                                    border_style=COLOR_THINKING,
                                    box=box.MINIMAL
                                )
                                view_group.append(Padding(active_panel, (1, 0, 0, 2))) 
                        else:
                            if final_thinking_panel:
                                view_group.append(Padding(final_thinking_panel, (1, 0, 0, 2)))
                    
                    # 3. Answer
                    if current_answer:
                        md = Markdown(current_answer)
                        pad_top = 1 if (expect_thinking and (is_thinking_phase or final_thinking_panel)) else 1
                        view_group.append(Padding(md, (pad_top, 0, 0, 2)))
                    
                    live.update(Group(*view_group))
            
            console.print() # Newline
            history.append({"role": "assistant", "content": current_answer})
            
            if first_run:
                break
            
        except KeyboardInterrupt:
            if not first_run:
                console.print(f"\n[{COLOR_SYSTEM}]Interrupted. Type 'exit' to quit.[/{COLOR_SYSTEM}]")
            break
        except Exception as e:
            console.print(f"\n[{COLOR_ERROR}]System Error: {e}[/{COLOR_ERROR}]")
            break

@app.command()
def main(
    model: str = typer.Option(None, help="Model ID to use (optional)"),
    key: str = typer.Option(None, help="API Key (optional override)"),
    ask: str = typer.Option(None, help="One-off question to ask (non-interactive mode)")
):
    """
    Start the Sigma Agent CLI.
    """
    if key:
        os.environ["GEMINI_API_KEY"] = key
        
    asyncio.run(chat_loop(model, ask))

if __name__ == "__main__":
    app()