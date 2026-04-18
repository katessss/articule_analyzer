import os
import logging
import google.generativeai as genai
from openai import OpenAI
import json
from typing import Dict, Optional
import re

from src.ai_services.prompts.extracting_data import PROMPT_FOR_DATA_EXTRACTING, PROMPT_FOR_DATA_ANALAYZING

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GeminiLM():
    def __init__(self, model: str = 'gemini-2.5-flash'):
        self.llm = None
        try:
            GOOGLE_AI_KEY = os.getenv("GOOGLE_API_KEY")
            genai.configure(api_key=GOOGLE_AI_KEY)
            self.llm = genai.GenerativeModel(model_name=model, generation_config={"temperature": 0.3})
            # logger.info("Модель инициа")
        except Exception as e:
            logger.error(f"Ошибка инициализации модели. Текст ошибки: {e}") 

    
    def _create_prompt(self, text_to_analyze: str, schema: dict) -> str:
        try:
            schema_str = json.dumps(schema, indent=2, ensure_ascii=False)
            prompt = PROMPT_FOR_DATA_ANALAYZING.format(
                schema_str=schema_str,
                text_to_analyze=text_to_analyze
            )
            return prompt
        except Exception as e:
            logger.error(f'Ошибка {e}')
            return ""
        
    def _count_tokens(self, prompt_template, response_text):
        try:
            prompt_tokens = self.llm.count_tokens(prompt_template).total_tokens
            response_tokens = self.llm.count_tokens(response_text).total_tokens
            logger.info(f"Отправлено токенов: {prompt_tokens}. Получено токенов: {response_tokens}")

        except Exception as e:
            logger.error(f"Ошибка при генерации ответа от Gemini: {e}")
        


    def generate(self, text_to_analyze: str, schema: Dict, retries: int = 3):
        if not self.llm:
            return
        
        prompt_template = self._create_prompt(text_to_analyze, schema)
        
        for attempt in range(retries):
            logger.info(f"Попытка извлечения данных #{attempt + 1}/{retries}...")
            try:
                llm_output =  self.llm.generate_content(prompt_template)
                llm_output = llm_output.text
                self._count_tokens(prompt_template, llm_output)

                if llm_output.startswith("```json"):
                    logger.info("Обнаружен markdown-блок JSON. Производится очистка.")
                    # Убираем начальный ```json и конечный ```
                    llm_output = llm_output.strip("```json").strip("```").strip()
                parsed_json = json.loads(llm_output)
                logger.info("Данные успешно извлечены и распарсены.")
                print(f'\n\n=====================\n{llm_output}\n======================\n\n')
                return parsed_json # return llm_output

            except json.JSONDecodeError:
                logger.warning(
                    f"Не удалось распарсить JSON на попытке {attempt + 1}"
                    f"Ответ от LLM: '{llm_output[:200]}......'"
                )


        logger.error(f"Не удалось извлечь данные после {retries} попыток.")
        return None
        
    
            
    

class OpenAIML:
    def __init__(self, model: str = 'gpt-3.5-turbo-0125'):
        self.llm = None
        try:
            # OpenAI автоматически ищет ключ в переменной окружения OPENAI_API_KEY
            self.llm = OpenAI()
            self.model = model
            logger.info(f"OpenAI Client инициализирован с моделью: {self.model}")
        except Exception as e:
            logger.error(f"Ошибка инициализации OpenAI клиента. Текст ошибки: {e}") 

    def _create_messages(self, text_to_analyze: str, schema: Dict) -> list:
        """
        Формирует список сообщений в формате Chat Completions API для OpenAI
        """
        try:
            schema_str = json.dumps(schema, indent=2, ensure_ascii=False)
            
            # В OpenAI схема и инструкции передаются в системном сообщении
            system_prompt = PROMPT_FOR_DATA_ANALAYZING.format(
                schema_str=schema_str,
                text_to_analyze="PLACEHOLDER_FOR_TEXT" # Убрать текст из системного промпта
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Проанализируй следующий текст:\n\n{text_to_analyze}"}
            ]
            return messages
        except Exception as e:
            logger.error(f'Ошибка при формировании сообщений: {e}')
            return []

    # (Пропустим _count_tokens, так как это чуть сложнее в OpenAI)
    
    def generate(self, text_to_analyze: str, schema: Dict, retries: int = 3):
        if not self.llm:
            return None
        
        messages = self._create_messages(text_to_analyze, schema)

        for attempt in range(retries):
            logger.info(f"Попытка извлечения данных с OpenAI #{attempt + 1}/{retries}...")
            try:
                response = self.llm.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    # Включаем принудительный вывод JSON
                    response_format={"type": "json_object"} 
                )
                
                llm_output = response.choices.message.content
                
                # В современных моделях OpenAI с response_format="json_object"
                # очистка от ```json не требуется, но можно оставить для надежности.
                
                parsed_json = json.loads(llm_output)
                logger.info("Данные успешно извлечены и распарсены (OpenAI).")
                return parsed_json 

            except json.JSONDecodeError:
                logger.warning(f"Не удалось распарсить JSON на попытке {attempt + 1}. Ответ от LLM: '{llm_output[:200]}......'")
            except Exception as e:
                 logger.error(f"Ошибка при запросе к OpenAI: {e}")
                 
        logger.error(f"Не удалось извлечь данные после {retries} попыток.")
        return None