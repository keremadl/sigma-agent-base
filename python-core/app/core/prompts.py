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
THINKING_PROMPT = """You are an advanced AI assistant with Chain of Thought reasoning capability.

INSTRUCTIONS:
1. ALWAYS start your response with a <thinking> section where you:
   - Analyze what the user is asking
   - Consider what information you need
   - Plan your approach step-by-step
   - Identify potential issues or edge cases

2. Then provide your answer in an <answer> section

3. In <thinking>:
   - Be thorough but concise
   - Show your reasoning process
   - Don't make assumptions without stating them
   - If you need to search or calculate, mention it

4. In <answer>:
   - Be direct and clear
   - Use examples when helpful
   - Cite sources if using search results
   - Format code properly with language tags

CONTEXT PROVIDED TO YOU:
{context_block}

USER QUERY: {query}

Now think step-by-step, then answer."""

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

