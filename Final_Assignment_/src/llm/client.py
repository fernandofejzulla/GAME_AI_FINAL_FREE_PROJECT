"""LLM client: generates validated BuildingParams from concept strings."""
import os
import json
import hashlib
from pathlib import Path
from typing import Literal, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types

from src.schema import BuildingParams
from src.llm.prompts import zero_shot_prompt, few_shot_prompt


load_dotenv()

CACHE_DIR = Path("data/llm_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PromptStrategy = Literal["zero_shot", "few_shot"]


class BuildingLLM:
    """Turns a building concept string into a validated BuildingParams via Gemini."""

    def __init__(self, model: str = "gemini-2.5-flash"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not in environment.")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(
        self,
        concept: str,
        strategy: PromptStrategy = "few_shot",
        use_cache: bool = True,
        max_retries: int = 3,
    ) -> BuildingParams:
        cache_key = self._cache_key(concept, strategy)
        if use_cache:
            cached = self._load_cache(cache_key)
            if cached is not None:
                return cached

        prompt = zero_shot_prompt(concept) if strategy == "zero_shot" else few_shot_prompt(concept)
        last_error: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7,
                    ),
                )
                raw = response.text.strip()
                params = BuildingParams.model_validate_json(raw)
                self._save_cache(cache_key, params, concept, strategy, raw)
                return params
            except Exception as e:
                last_error = e
                prompt = (
                    prompt
                    + f"\n\nYour previous attempt failed validation: {e}\n"
                    + "Return only a corrected JSON object that strictly matches the schema."
                )

        raise RuntimeError(
            f"Failed to generate valid BuildingParams for '{concept}' "
            f"after {max_retries} attempts. Last error: {last_error}"
        )

    def _cache_key(self, concept: str, strategy: str) -> str:
        h = hashlib.md5(f"{concept}|{strategy}|{self.model}".encode()).hexdigest()[:12]
        return f"{strategy}_{h}"

    def _load_cache(self, key: str) -> Optional[BuildingParams]:
        path = CACHE_DIR / f"{key}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return BuildingParams.model_validate(data["params"])

    def _save_cache(self, key: str, params: BuildingParams, concept: str, strategy: str, raw: str):
        path = CACHE_DIR / f"{key}.json"
        path.write_text(json.dumps({
            "concept": concept,
            "strategy": strategy,
            "model": self.model,
            "raw_response": raw,
            "params": params.model_dump(mode="json"),
        }, indent=2))