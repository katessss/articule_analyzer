import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def analysis_workflow(model, schema, num_batch, path_to_text):
    batch_results  = []

    with open(path_to_text, 'r', encoding='utf-8') as f:
        content  = f.read()

    logger.info(f'\n\nОбработка файла {path_to_text}, батч #{num_batch}')        
    gemini_response = model.generate(
        text_to_analyze=content,
        schema=schema
        )
        
    name = Path(path_to_text).name.removesuffix('_extracted_content.txt')
    if isinstance(gemini_response, dict):
        batch_results.append({
            "source_file":  f"{name}", 
            "num_batch": num_batch,      
            "data": gemini_response    
        })
        logger.info("Данные успешно извлечены.")
    else:
        batch_results.append({
                "source_file":  f"{name}", 
                "num_batch": num_batch,      
                "data": "Не удалось извлечь структурированные данные"    
            })
        logger.warning(f"Не удалось извлечь структурированные данные из {path_to_text}.")

    return batch_results