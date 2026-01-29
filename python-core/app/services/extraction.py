import litellm
import json
import logging
from app.services.profile import profile

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a memory extraction AI. Your job is to identify if the user revealed PERSONAL INFORMATION that should be saved.

SAVE IF:
- Personal details (name, age, family, location)
- Preferences (favorite tools, habits, tone)
- Technical info (devices, projects, skills, languages)
- Work/education details

DO NOT SAVE:
- Small talk ("I'm tired", "nice weather")
- General questions ("How does X work?")
- Temporary states ("I'm working on Y today")

CONVERSATION:
User: {user_message}
AI: {ai_response}

OUTPUT (JSON only, no explanation):
{{
  "memories": [
    {{
      "category": "personal/family/tech/work/preferences",
      "key": "brief_identifier",
      "value": "the actual information",
      "importance": 1-10
    }}
  ]
}}

If nothing to save: {{"memories": []}}
"""


async def auto_extract_memory(user_message: str, ai_response: str, api_key: str) -> bool:
    """
    Automatically extract and save memory from conversation
    
    Returns True if memory was saved
    """
    try:
        prompt = EXTRACTION_PROMPT.format(
            user_message=user_message,
            ai_response=ai_response
        )
        
        response = await litellm.acompletion(
            model="gemini/gemini-2.0-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            custom_llm_provider="gemini",
            max_tokens=500,
        )
        
        result_text = response.choices[0].message.content
        if not result_text:
            return False
        
        result_text = result_text.strip()
        
        # Try to extract JSON from the response
        try:
            # Handle markdown code blocks
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(result_text)
        except json.JSONDecodeError:
            # Fallback: try to find start and end of JSON object
            start_idx = result_text.find("{")
            end_idx = result_text.rfind("}")
            if start_idx != -1 and end_idx != -1:
                json_str = result_text[start_idx:end_idx+1]
                data = json.loads(json_str)
            else:
                return False
        
        memories = data.get("memories", [])
        if not memories:
            return False
            
        saved_count = 0
        for item in memories:
            if item.get("key") and item.get("value"):
                profile.add_entry(
                    category=item.get("category", "personal"),
                    key=item.get("key"),
                    value=item.get("value"),
                    source="auto_extracted",
                    importance=item.get("importance", 5)
                )
                logger.info(f"Auto-saved memory: {item.get('key')}")
                saved_count += 1
                
        return saved_count > 0
    
    except Exception as e:
        logger.error(f"Memory extraction failed: {e}")
        return False
    
    except json.JSONDecodeError as e:
        logger.warning(f"Memory extraction JSON parse failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Memory extraction failed: {e}")
        return False
