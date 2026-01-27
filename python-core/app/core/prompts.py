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

For complex questions, explain your reasoning first, then provide the answer.

Structure:
1. Show your step-by-step reasoning
2. Give the final answer

Keep reasoning concise and clear."""

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
