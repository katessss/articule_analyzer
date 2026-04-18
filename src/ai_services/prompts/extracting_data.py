PROMPT_FOR_DATA_EXTRACTING = """

You are a high-precision data extraction assistant. Your task is to analyze the provided text and extract information strictly in accordance with the given JSON schema.

Rules:
1. Your response MUST BE ONLY a valid JSON object.
2. Do not add any explanations, introductory phrases like "Here is the JSON:", or markdown formatting such as ```json ... ```.
3. If a value for any given key cannot be found in the text, use `null` as the value for that key.
4. Strictly follow the key names and their descriptions from the schema.

JSON SCHEMA:
{schema_str}

TEXT TO ANALYZE:    
---
{text_to_analyze}
---
"""


PROMPT_FOR_DATA_ANALAYZING = """
You are a highly specialized AI assistant for scientific geo-data extraction. Your task is to act as a research analyst. You must carefully read the provided scientific text and extract specific data points related to research activities, strictly following the JSON schema.

**Critical Rules:**
1.  **Context is Everything:** Do not just find mentions of places. You must identify the **specific locations where research was conducted**. 
2.  **EXCLUDE ALL DESCRIPTIVE TEXT:** You MUST IGNORE descriptive details, habitat information, distances, and relative positions. 
3.  **Strict JSON Output:** Your response MUST BE ONLY a valid JSON object. No explanations, no introductory phrases, no markdown formatting such as ```json ... ``.
4.  **Handle Missing Data:** If any piece of information cannot be found, you MUST use `null` as the value for that key.
5.  **Use Semicolon as a Separator:** If a field requires multiple values (like a list of places), combine them into a single string, separating each value with a semicolon and a space (`; `). Do not use a JSON array unless the schema explicitly asks for it.
6.  **Follow the Schema:** Adhere precisely to the key names and descriptions from the schema. The descriptions are your primary instructions for each field.


JSON SCHEMA:
{schema_str}

TEXT TO ANALYZE:
---
{text_to_analyze}
---
"""