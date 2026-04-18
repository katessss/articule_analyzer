import re
import os 
import csv
from pathlib import Path 
import pandas as pd
import logging
logger = logging.getLogger(__name__)

def LINKS_parse_and_save_to_csv(results: list, topic: str, result_folder):
    """
    Парсит список текстовых ответов с markdown-разметкой,
    извлекает уникальные названия и URL, и сохраняет их в CSV-файл.

    Args:
        results (list): Список строк, полученных от LLM.
        topic (str): Тема поиска, используется для имени файла.
    """
    # Регулярное выражение для поиска markdown-ссылок с опциональным номером в начале
    # Оно найдет: [Название статьи](https://...)
    # Группа 1: (.*?) -> Название статьи
    # Группа 2: (https?://[^\s)]+) -> URL
    markdown_link_regex = re.compile(r'\[(.*?)\]\((https?://[^\s)]+)\)')
    
    # Используем set для автоматического хранения только уникальных пар (название, url)
    unique_articles = set()

    # Итерируемся по каждому текстовому блоку из `final_results`
    for text_block in results:
        # Находим все совпадения в текущем блоке
        found_articles = markdown_link_regex.findall(text_block)
        for title, url in found_articles:
            # Добавляем кортеж (название, url) в наш set.
            # .strip() убирает лишние пробелы.
            unique_articles.add((title.strip(), url.strip()))

    if not unique_articles:
        print("Не найдено ни одной статьи для сохранения.")
        return

    # --- ЗАПИСЬ В CSV-ФАЙЛ ---
    
    # Создаем безопасное имя файла из темы
    # Заменяем пробелы на '_' и убираем недопустимые символы
    safe_filename = re.sub(r'[\\/*?:"<>|]', "", topic).replace(" ", "_")[:40]
    output_filename = result_folder / f"{safe_filename}.csv"
    
    print(f"\nНайдено {len(unique_articles)} уникальных статей. Сохранение в файл: {output_filename}...")

    try:
        # 'w' - режим записи, newline='' - для правильной обработки строк в csv
        # encoding='utf-8-sig' - лучшая кодировка для CSV с кириллицей, чтобы Excel ее правильно открывал
        with open(output_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            # Создаем объект для записи в CSV
            csv_writer = csv.writer(csvfile)
            
            # Записываем заголовок (header)
            csv_writer.writerow(['title', 'url'])
            
            # Записываем все найденные уникальные статьи
            # Сортируем для предсказуемого порядка в файле
            for title, url in sorted(list(unique_articles)):
                csv_writer.writerow([title, url])
                
        print("Сохранение в CSV успешно завершено.")
        return str(output_filename)

    except Exception as e:
        print(f"Ошибка при записи в CSV-файл: {e}")
        return None




def process_value(value) -> str:
    """Вспомогательная функция для обработки значений перед записью."""
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v).strip() for v in value)
    if isinstance(value, str):
        # Заменяем точку с запятой и убираем лишние пробелы
        return ", ".join(v.strip() for v in value.split(';'))
    return str(value)

def ANALYSIS_parse_and_save_to_csv(results: list, filename: str, result_folder: Path):
    """
    УНИВЕРСАЛЬНЫЙ ИТЕРАТИВНЫЙ ПАРСЕР для "широкого" формата CSV.
    Создает или обновляет CSV-файл на основе новых данных.
    """
    if not results:
        logger.warning("Нет данных для обработки в текущем батче.")
        return None

    # --- ШАГ 1: Преобразование результатов текущего батча в DataFrame ---
    
    # Сначала преобразуем "длинный" список результатов в "широкий" формат
    wide_results = {}
    for item in results:
        source_file = item.get('source_file')
        data_dict = item.get('data')
        if not source_file or not isinstance(data_dict, dict):
            continue
        
        if source_file not in wide_results:
            wide_results[source_file] = {}
        
        # Обрабатываем и добавляем данные из текущего батча
        for key, value in data_dict.items():
            wide_results[source_file][key] = process_value(value)

    # Создаем DataFrame из данных текущего батча
    # index_col='source_file' сделает имена файлов индексом
    new_df = pd.DataFrame.from_dict(wide_results, orient='index')
    new_df.index.name = 'source_file'

    if new_df.empty:
        logger.warning("Не удалось создать DataFrame из результатов батча.")
        return None

    # --- ШАГ 2: Создание или обновление CSV-файла ---
    
    output_path = result_folder / f"{filename}.csv"
    logger.info(f"Обновление/создание файла: {output_path}")

    try:
        # Если файл уже существует, читаем его и объединяем
        if output_path.exists():
            logger.info("Файл уже существует. Чтение и объединение данных...")
            
            # Читаем существующий CSV, указывая, что первая колонка - это индекс
            existing_df = pd.read_csv(output_path, index_col='source_file')
            
            # Объединяем DataFrame'ы. `how='outer'` сохранит все строки из обоих.
            # `on='source_file'` указывает колонку для объединения.
            combined_df = existing_df.merge(new_df, how='outer', on='source_file', suffixes=('', '_new'))

            # Обработка конфликтов: если колонка уже была, но в новом батче есть новое значение
            for col in combined_df.columns:
                if col.endswith('_new'):
                    base_col = col.removesuffix('_new')
                    # Обновляем старую колонку, заполняя пропуски новыми значениями
                    combined_df[base_col].fillna(combined_df[col], inplace=True)
                    # Удаляем временную новую колонку
                    combined_df.drop(columns=[col], inplace=True)
            
            # Заполняем возможные пропуски (NaN) пустыми строками для чистоты
            final_df = combined_df.fillna("")

        # Если файла еще нет, то DataFrame этого батча и есть наш итоговый
        else:
            logger.info("Новый файл. Создание с нуля...")
            final_df = new_df.fillna("")

        # --- ШАГ 3: Запись в CSV ---
        # `index=True` сохранит колонку 'source_file'
        final_df.to_csv(output_path, index=True, encoding='utf-8-sig')

        logger.info(f"Файл '{output_path}' успешно обновлен.")
        return str(output_path)

    except Exception as e:
        logger.error(f"Критическая ошибка при работе с CSV-файлом: {e}")
        return None