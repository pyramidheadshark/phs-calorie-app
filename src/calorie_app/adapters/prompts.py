from __future__ import annotations

ANALYSIS_PROMPT = """Analyze this meal and return ONLY valid JSON with no markdown, no code blocks:
{
  "description": "human-readable meal description in Russian",
  "portion_g": 300,
  "calories": 450,
  "protein_g": 25.5,
  "fat_g": 15.0,
  "carbs_g": 50.0,
  "confidence": "high",
  "notes": "any important observations"
}
confidence must be one of: "high", "medium", "low".
All numeric values must be numbers, not strings."""

TEXT_ANALYSIS_PROMPT = """Estimate nutrition for the meal description below and return ONLY valid JSON.
Use the same schema as below — replace zeros with realistic estimates.
{{
  "description": "meal name in Russian",
  "portion_g": 300,
  "calories": 0,
  "protein_g": 0.0,
  "fat_g": 0.0,
  "carbs_g": 0.0,
  "confidence": "medium",
  "notes": ""
}}
Meal: {description}"""

VOICE_ANALYSIS_PROMPT = ANALYSIS_PROMPT  # same schema, applied to audio transcription

PROFILE_PARSE_PROMPT = """You are a nutrition expert. Parse the user profile text below and extract structured goals.
Return ONLY valid JSON with no markdown:
{{
  "calorie_target": <integer, daily kcal for the stated goal>,
  "protein_target_g": <integer, daily grams>,
  "fat_target_g": <integer, daily grams>,
  "carbs_target_g": <integer, daily grams>,
  "goal_description": "<1-2 sentences in Russian summarising the goal>",
  "kitchen_equipment": ["<list of equipment names in Russian, e.g. аэрогриль>"],
  "food_preferences": "<comma-separated food likes and dislikes in Russian>",
  "body_data": {{
    "weight_kg": <float or null>,
    "height_cm": <integer or null>,
    "muscle_mass_kg": <float or null>,
    "fat_mass_kg": <float or null>
  }}
}}
User profile text:
{profile_text}"""

RECIPE_PROMPT = """You are a nutritionist and chef. Generate a healthy recipe for this user.
Profile:
- Goal: {goal}
- Daily targets: {calories} kcal | protein {protein}g | fat {fat}g | carbs {carbs}g
- Food preferences: {preferences}
- Kitchen equipment available: {equipment}
- Previously liked recipes (include similar ideas): {liked}
- Recipes to AVOID (disliked or already shown recently): {disliked}

Return ONLY valid JSON with no markdown:
{{
  "title": "<recipe title in Russian>",
  "description": "<1-2 sentences in Russian>",
  "ingredients": [{{"name": "<ingredient>", "amount": "<amount>"}}],
  "instructions": ["<step 1>", "<step 2>"],
  "nutrition_estimate": {{
    "calories": <integer per serving>,
    "protein_g": <float>,
    "fat_g": <float>,
    "carbs_g": <float>,
    "portion_g": <integer>
  }},
  "cooking_time_min": <integer>,
  "equipment_used": ["<equipment name>"]
}}"""
