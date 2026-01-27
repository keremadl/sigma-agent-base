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

1. <thinking>...</thinking> tags: ONLY for brief planning, scratchpad notes, or quick reasoning steps.
   - Keep thinking SHORT and concise (2-3 sentences max).
   - This is your internal planning, NOT the detailed explanation.
   - Example: "I need to explain X. Let me break it down into steps."

2. <answer>...</answer> tags: This is where your ACTUAL detailed response goes.
   - Put ALL explanations, detailed content, code examples, and final answers here.
   - This is what the user will see as your response.
   - Be thorough and complete in the <answer> section.

CRITICAL: The <thinking> section is NOT for your main response. It's only for quick planning.
The <answer> section must contain your complete, detailed response to the user.

Example format:
<thinking>
I need to explain how quicksort works. I'll cover the algorithm, time complexity, and provide an example.
</thinking>
<answer>
Quicksort is a divide-and-conquer sorting algorithm. Here's how it works:

1. Choose a pivot element from the array
2. Partition the array so elements smaller than pivot are on the left, larger on the right
3. Recursively sort the sub-arrays

Time complexity: O(n log n) average case, O(n²) worst case.

Here's a Python implementation:
[code example here]

The key advantage is its efficiency in practice, though worst-case performance can be poor.
</answer>

Always use these tags. The <answer> section must contain your complete response."""

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
