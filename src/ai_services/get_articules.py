import os
import re
import requests
from dotenv import load_dotenv
import logging

from src.ai_services.prompts.extracting_links import PROMPT_FOR_GETTING_LINKS

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)




class PplxSearch:
    """
    Класс для итеративного поиска уникальных ссылок на статьи.
    """
    BASE_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(self, model: str = "sonar"):
        self.model = model
        self.api_key = os.getenv("PPLX_API_KEY")
        if not self.api_key:
            raise ValueError("API-ключ PPLX_API_KEY не найден.")
        
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        logger.info(f"Клиент PplxSearch инициализирован с моделью: {self.model}")

    def _generate(self, messages: list):
        payload = {"model": self.model, "messages": messages, "temperature": 0.4}
        try:
            response = requests.post(self.BASE_URL, json=payload, headers=self.headers)
            response.raise_for_status()
            response_json = response.json()
            return response_json['choices'][0]['message']['content']
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка: {e}. Ответ сервера: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Непредвиденная ошибка: {e}")
            return None


    def find_unique_articles_iteratively(self, topic: str, amount_per_iteration: int = 5, total_iterations: int = 4) -> list:
 
        found_links = set()
        all_results = []

        for i in range(total_iterations):
            logger.info(f"\n--- Итерация поиска #{i + 1}/{total_iterations} ---")
            
            # Формируем список уже найденных ссылок для исключения
            excluded_links_str = "\n".join(f"- {link}" for link in found_links)
            if not excluded_links_str:
                excluded_links_str = "None"

            system_prompt = PROMPT_FOR_GETTING_LINKS
            user_prompt = f"""
                Topic: "{topic}"
                Previously found URLs to exclude:
                {excluded_links_str}
                """
            # print(f'\n\n====================================================================')
            # print(excluded_links_str)
            # print(f'====================================================================\n\n')
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            answer_text = self._generate(messages)
            
            if answer_text:
                all_results.append(answer_text)
                # Парсим новые ссылки и добавляем их в наш set
                new_links = re.findall(r'https?://[^\s)]+', answer_text)
                if new_links:
                    logger.info(f"Найдено {len(new_links)} новых ссылок.")
                    found_links.update(new_links)
                else:
                    logger.warning("В ответе модели не найдено ссылок.")
            else:
                logger.error("Не удалось получить ответ от модели на этой итерации.")
        
        return all_results


# if __name__ == '__main__':
    
#     pplx_client = PplxSearch(model='sonar')
    
#     final_results = pplx_client.find_unique_articles_iteratively(
#         topic="Водная растительность России",
#         amount_per_iteration=5,
#         total_iterations=4
#     )
    
#     print("\n\n" + "="*20 + " Все полученные ответы " + "="*20)
#     for i, result_text in enumerate(final_results):
#         print(f"\n--- Ответ #{i+1} ---")
#         print(result_text)
    
#     print("="*65)