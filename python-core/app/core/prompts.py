from typing import Literal

QueryType = Literal["simple", "factual", "complex"]

# Router prompt: Classify user query
ROUTER_PROMPT = """Analyze the following user query and classify it into ONE category:

Categories:
- simple: Greetings, acknowledgments, small talk. No information lookup needed.
  Examples: "Hello", "Thanks", "OK", "Goodbye"
  
- factual: Requires current/external information or web search.
  Examples: "What's the weather today?", "Dollar exchange rate?", "Latest news about X"
  
- complex: Requires reasoning, coding, math, multi-step analysis, or explanation.
  Examples: "Explain quantum entanglement", "Write a Python function to...", "Solve this equation"

User Query: {query}

Respond with ONLY ONE WORD: simple OR factual OR complex"""

# Chain of Thought prompt for complex queries
THINKING_PROMPT = """You are a helpful AI assistant.

IMPORTANT: You MUST structure your response using XML tags:

1. Wrap your reasoning/thought process in <thinking>...</thinking> tags
2. Wrap your final answer in <answer>...</answer> tags

Example format:
<thinking>
First, I need to analyze the problem...
Step by step reasoning here...
</thinking>
<answer>
The final answer is...
</answer>

Always use these tags. Do not include reasoning outside the <thinking> tags."""

# Simple query prompt (no thinking needed)
SIMPLE_PROMPT = """You are a friendly, helpful AI assistant. 
Keep your response brief, warm, and natural.

User: {query}
Assistant:"""

# Context block template
CONTEXT_TEMPLATE = """
Memory Context (from past conversations):
{memory_context}

Search Results (if applicable):
{search_results}
"""
