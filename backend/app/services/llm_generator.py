import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from duckduckgo_search import DDGS

from app.config import settings

logger = logging.getLogger(__name__)

# --- Provider Interface ---
class LLMProvider(ABC):
    @abstractmethod
    async def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        pass

    @abstractmethod
    async def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> dict:
        pass

# --- Concrete Providers ---
class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature
        )
        return response.choices[0].message.content

    async def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> dict:
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=temperature
        )
        return json.loads(response.choices[0].message.content)

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import google.generativeai as genai

class GeminiProvider(LLMProvider):
    def __init__(self, project_id: str = None, api_key: str = None):
        self.use_vertex = False
        self.model = None

        # 1. Try Vertex AI (Identity) first
        if project_id:
            try:
                vertexai.init(project=project_id, location="us-central1")
                temp_model = GenerativeModel("gemini-1.5-flash")
                # Warmup removed to prevent startup timeout
                self.model = temp_model
                self.use_vertex = True
                logger.info("GeminiProvider initialized with Vertex AI.")
            except Exception as e:
                logger.warning(f"Vertex AI validation failed (Permissions/Quota): {e}. Falling back...")
                self.use_vertex = False

        # 2. Fallback to API Key
        if not self.use_vertex and api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                logger.info("GeminiProvider initialized with API Key.")
            except Exception as e:
                logger.error(f"GenAI Init failed: {e}")
        
        if not self.model:
            raise ValueError("Failed to initialize GeminiProvider with either Identity or API Key.")

    async def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        if self.use_vertex:
             # Vertex AI Logic
            response = await self.model.generate_content_async(
                contents=user_prompt,
                system_instruction=system_prompt,
                generation_config=GenerationConfig(temperature=temperature)
            )
            return response.text
        else:
            # GenAI Logic (Legacy)
            full_prompt = f"{system_prompt}\n\nUser Question: {user_prompt}"
            response = await self.model.generate_content_async(
                full_prompt,
                generation_config=genai.types.GenerationConfig(temperature=temperature)
            )
            return response.text

    async def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> dict:
        if self.use_vertex:
            # Vertex JSON
            response = await self.model.generate_content_async(
                contents=user_prompt,
                system_instruction=system_prompt,
                generation_config=GenerationConfig(
                    temperature=temperature,
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        else:
            # GenAI JSON (Markdown Cleanup)
            full_prompt = f"{system_prompt}\n\nPlease output valid JSON only.\n\nQuestion: {user_prompt}"
            response = await self.model.generate_content_async(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    response_mime_type="application/json"
                )
            )
            content = response.text.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            return json.loads(content)

class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)

    async def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        response = await self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature
        )
        return response.content[0].text

    async def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> dict:
        updated_system = f"{system_prompt}\nYou must output pure JSON."
        response = await self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system=updated_system,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature
        )
        content = response.content[0].text
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end != -1:
            content = content[start:end]
        return json.loads(content)

# --- Main Service ---
class LLMGenerator:
    def __init__(self):
        self.provider: Optional[LLMProvider] = None
        self.ddgs = DDGS()
        self._setup_provider()

    def _setup_provider(self):
        """Prioritize: Vertex (Identity) -> Gemini (Key) -> OpenAI -> Anthropic"""
        
        # 1. Try Gemini (Hybrid: Vertex or Key)
        if settings.google_cloud_project or settings.gemini_api_key:
             try:
                 # Pass both; provider decides preference
                 self.provider = GeminiProvider(
                     project_id=settings.google_cloud_project, 
                     api_key=settings.gemini_api_key
                 )
                 return
             except Exception as e:
                 logger.warning(f"GeminiProvider Init failed: {e}")

        # 2. Fallback to OpenAI
        if settings.openai_api_key:
            logger.info("Using OpenAI Provider")
            self.provider = OpenAIProvider(settings.openai_api_key)
            return

        # 3. Fallback to Anthropic
        if settings.anthropic_api_key:
             logger.info("Using Anthropic Provider")
             self.provider = AnthropicProvider(settings.anthropic_api_key) 
             return
            
        logger.warning("No AI Provider configured!")

    async def generate_mermaid(self, topic: str) -> str:
        if not self.provider:
            return "graph TD; A[Error] --> B[No AI Key Configured];"

        system = """
        You are a visualization expert. 
        Create a Mermaid.js diagram to explain concepts simply to students.
        Return ONLY the Mermaid code block. No markdown backticks.
        """
        prompt = f"Create a diagram for: {topic}"

        try:
            content = await self.provider.generate_text(system, prompt, temperature=0.2)
            content = content.replace("```mermaid", "").replace("```", "").strip()
            return content
        except Exception as e:
            logger.error(f"Mermaid generation failed: {e}")
            return f"graph TD; A[Error] --> B[{str(e)}];"

    async def generate_tuition(self, question: str, topic: str) -> dict:
        if not self.provider:
             return {
                "mermaid": "graph TD; A[Error] --> B[No AI Key];",
                "explanation": "Please ensure your AI credentials (Vertex AI or API Keys) are configured correctly."
            }

        # 1. Search (Provider agnostic)
        search_query = f"how to explain {topic} visually to 10 year old: {question[:100]}"
        try:
            results = self.ddgs.text(search_query, max_results=3)
            context = "\n".join([f"- {r['title']}: {r['body']}" for r in results])
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            context = "No external context available."

        # 2. Generate
        system = """
        You are an expert tutor for 10-year-olds.
        Your task is to provide a visual explanation (Mermaid.js) and a simple text explanation.
        Return JSON ONLY: { "mermaid": "...", "explanation": "..." }
        """
        prompt = f"""
        Question: "{question}"
        Topic: "{topic}"
        Context: {context}
        
        Generate the JSON response.
        """
        
        try:
            return await self.provider.generate_json(system, prompt, temperature=0.3)
        except Exception as e:
            logger.error(f"Tuition generation failed: {e}")
            # Mock Fallback for robustness
            return {
                "mermaid": """graph TD
    A[Question Problem] --> B{Key Concept}
    B --> C[Step 1: Identify Pattern]
    B --> D[Step 2: Apply Logic]
    C --> E[Solution]
    D --> E
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style E fill:#90EE90,stroke:#333,stroke-width:2px""",
                "explanation": f"""
                <p><strong>AI Generation Unavailable (Using Demo Content)</strong></p>
                <p>We couldn't reach the AI provider ({settings.gemini_api_key[:4] if settings.gemini_api_key else 'No Key'}...).</p>
                <p><strong>How to solve this type of question:</strong></p>
                <ol>
                    <li>Break the problem down into smaller parts.</li>
                    <li>Look for patterns or key information.</li>
                    <li>Eliminate obviously wrong answers.</li>
                </ol>
                <p><em>Check backend logs for API error details.</em></p>
                """
            }
            
    # Keep other methods (synthesize_research, generate_quiz) integrated with self.provider similarly...
    # For brevity in this diff, assuming they are either migrated or we focus on tuition first.
    # Re-implementing them below for completeness to avoid breaking app.

    async def synthesize_research(self, query: str, context: list[dict]) -> str:
        if not self.provider:
            return "Error: No AI Key configured."

        context_str = "\n".join([f"- [{i+1}] {item['title']}: {item['snippet']}" for i, item in enumerate(context)])
        system = "You are a research assistant. Answer comprehensively using the provided search results. Cite sources [1]."
        prompt = f"Question: {query}\n\nResults:\n{context_str}"

        try:
            return await self.provider.generate_text(system, prompt, temperature=0.4)
        except Exception as e:
             return f"Error synthesizing research: {str(e)}"

    async def generate_quiz(self, topic: str, difficulty: str) -> list[dict]:
        if not self.provider:
            return [{"question": "Error: No AI Key", "options": ["OK"], "correct_answer": "OK", "explanation": "Config missing"}]

        system = "Generate 5 multiple-choice questions for 11+ exams. Return JSON array of objects."
        prompt = f"Topic: {topic}, Difficulty: {difficulty}. Schema: [{{question, options, correct_answer, explanation}}]"

        try:
            data = await self.provider.generate_json(system, prompt, temperature=0.7)
            if isinstance(data, dict) and "questions" in data:
                return data["questions"]
            return data if isinstance(data, list) else []
        except Exception as e:
             logger.error(f"Quiz generation failed: {e}")
             return []

llm_service = LLMGenerator()
