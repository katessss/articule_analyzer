import os
from pathlib import Path
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


from src.ai_services.get_articules import PplxSearch
from src.ai_services.analyze_articules import GeminiLM
from src.parsers.answer_parser import ANALYSIS_parse_and_save_to_csv, LINKS_parse_and_save_to_csv
from src.parsers.pdf_reader import PDFProcessor, save_to_txt
from src.ai_services.utils import analysis_workflow

# Настройка путей
BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
TEMP_PDF_DIR = BASE_DIR / "temp"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_PDF_DIR.mkdir(parents=True, exist_ok=True)


def run_links(TOPIC: str,  total_iterations: int = 3,  logger=logging.getLogger()):
    pplx_client = PplxSearch()
    
    final_results = pplx_client.find_unique_articles_iteratively(topic=TOPIC, total_iterations=total_iterations)

    if not final_results:
        logger.warning("Не удалось найти статьи.")
        return None
    
    output_path = LINKS_parse_and_save_to_csv(final_results, TOPIC, result_folder=RESULTS_DIR / "results_links")
    logger.info(f"Результаты поиска сохранены в: {output_path}")
    return output_path


def run_analyzing(pdf_folder_path, features, batch_size = 2, logger=logging.getLogger()):
    logger.info(f"Начинаю анализ PDF из папки: {pdf_folder_path}")

    for filename in sorted(os.listdir(pdf_folder_path)):
        if not filename.endswith('pdf'):
            continue
        pdf_path = os.path.join(pdf_folder_path, filename)
        processor = PDFProcessor(pdf_path)
        all_data = processor.process_all_pages()    
        # save_to_txt(all_data, os.path.join(TEMP_PDF_DIR, f"{filename.split('.')[0]}_extracted_content.txt"))
        file_stem = Path(filename).stem
        save_to_txt(all_data, TEMP_PDF_DIR / f"{file_stem}_extracted_content.txt")


    logger.info("Анализ текста с помощью LLM...")
    # Разделение призанков (по 10 за раз) 
    feature_items = list(features.items())
    batches = [dict(feature_items[i:i+batch_size]) for i in range(0, len(feature_items), batch_size)]
    logger.info(f"Всего батчей: {len(batches)} (по {batch_size} признаков, последний может быть меньше)")

    # Подача в модель
    gemini_client= GeminiLM()

    
    for filename in sorted(os.listdir(TEMP_PDF_DIR)):
        path_to_text = os.path.join(TEMP_PDF_DIR, filename)
        for i, batch in enumerate(batches):
            batch_results = analysis_workflow(
                model=gemini_client,
                schema=batch,
                num_batch=i,
                path_to_text=path_to_text
            )

            if batch_results:
                ANALYSIS_parse_and_save_to_csv(
                    results=batch_results,
                    filename=f"{Path(pdf_folder_path).name}_analysis",
                    result_folder=RESULTS_DIR
                )
            else:
                logger.warning(f"Батч #{i+1} не дал результатов.")






# -------------------------------------------------------------------------------------------------------

def main():
    import logging
    logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
    logger = logging.getLogger()

    print("\n" + "="*60)
    print("      Запуск автоматического конвейера анализа статей")
    print("="*60 + "\n")

    # --- ПАРАМЕТРЫ ДЛЯ ЗАПУСКА ---

    # Параметры для Шага 1: Поиск ссылок
    SEARCH_TOPIC = "Анализ данных в России 2025"
    
    # Параметры для Шага 2: Анализ PDF
    # ВАЖНО: Укажите здесь РЕАЛЬНЫЙ путь к вашей папке с PDF-файлами
    PDF_FOLDER_PATH = r"D:\work\tsu\НИИББ\articule_analyzer\biocharm"
    
    # Схема (признаки), которые мы хотим извлечь из PDF
    extraction_schema = {
    "Название статьи": "Название статьи",
    "Ссылка в адресной строке": "URL статьи (вставить из адресной строки)",
    "Библиографическая ссылка": "Полная ссылка для цитирования статьи",
    "Год выпуска статьи": "Год выпуска статьи (только число)",
    "Язык": "Язык статьи (например, русский, английский, китайский)",
    "Журнал": "Название журнала, в котором опубликована статья",
    "Квартиль": "Квартиль журнала (например, Q1, Q2, Q3)",
    "Страна публикации": "Страна, в которой был опубликован журнал",
    "Страна исследования": "Страна, на территории которой проводилось исследование. Зачастую, отражено в главе 'Методы' (Methods).",
    "Регион исследования": "Регион, область или штат, где проводилось исследование. Зачастую, отражено в главе 'Методы' (Methods).",
    "Координаты участка исследований": "Географические координаты места исследования. Зачастую, отражено в главе 'Методы' (Methods).",
    "Cрок эксперимента": "Длительность или период проведения эксперимента. Зачастую, отражено в главе 'Методы' (Methods).",
    "Тип почв": "Тип почв на исследуемом участке. Например: Чернозем, Лугово-черноземные мерзлотные, дерново-подзолистые. Если классификация почв американская - вставлять полностью.",
    "Гранулометрический состав": "Содержание физической глины, илистой фракции, песка (частиц <), %, в почвах.",
    "Тип и вид луга": "Полное название луга. Например: заливной, пойменный луг, субальпийский луг. Если характеристика по ботаническому описанию, то тоже вставляем (например: мятликово-осоковый луг).",
    "Растения (культуры)-доминанты луга": "Преобладающий или изучаемый вид растений на исследуемом участке. Ключевые слова: Species, Dominant species.",
    "Урожайность/продуктивность до начала эксперимента": "Урожайность или продуктивность до начала эксперимента. Ключевые слова: Dry matter (DM); Dry matter yield; Yield (t ha–1; g m-2).",
    "Урожайность/продуктивность под конец эксперимента": "Урожайность или продуктивность в конце эксперимента. Ключевые слова: Dry matter (DM); Dry matter yield; Yield (t ha–1; g m-2).",
    "Единица измерения урожайности/продуктивности": "Единица измерения, в которой указана урожайность (например, t ha–1, g m-2).",
    "Сырье, использованное при пиролизе": "Сырье, которое использовалось для создания биочара. Зачастую, отражено в главе 'Методы' (Methods).",
    "Температура пиролиза": "Температура, при которой проводился пиролиз. Зачастую, отражено в главе 'Методы' (Methods). Ключевые слова: pyrolysis, slow pyrolysis, high/low-temperature.",
    "Время пиролизации": "Время, в течение которого проводился пиролиз. Зачастую, отражено в главе 'Методы' (Methods).",
    "Физико-химические характеристики биочара": "Основные физико-химические характеристики биочара (например, pH; С,%; N,%; С/N).",
    "Вариация применения": "Способ применения биочара: в одиночном виде или в комбинации с удобрениями/мелиоративными мероприятиями.",
    "Доза биочара, вносимая в почву": "Количество биочара, которое вносилось в почву.",
    "Содержание углерода в почвах в начале эксперимента": "Начальное содержание углерода в почве.",
    "эмиссия углерода (С, СО2) в начале (1 год) эксперимента": "Выделение CO2 из почвы в начале эксперимента. Ключевые слова: поток, дыхание почвы, fluxes, emission rate.",
    "эмиссия азота (N; N2O) в начале (1 год) эксперимента": "Выделение N2O из почвы в начале эксперимента. Ключевые слова: поток, fluxes, emission rate.",
    "эмиссия метана (CH4) в начале (1 год) эксперимента": "Выделение CH4 из почвы в начале эксперимента. Ключевые слова: поток, fluxes, emission rate.",
    "эмиссия углерода (C; CO2) в конце эксперимента": "Выделение CO2 из почвы в конце эксперимента.",
    "эмиссия азота (N; N2O) в конце эксперимента": "Выделение N2O из почвы в конце эксперимента.",
    "эмиссия метана (CH4) в конце эксперимента": "Выделение CH4 из почвы в конце эксперимента.",
    "Единица измерения углерода в почвах": "Единица измерения, в которой указано содержание углерода в почвах.",
    "Единица измерения эмиссии СО2": "Единица измерения эмиссии CO2 (например, ppm, kg CO2 ha–1 d–1, µg m-2 d-1). Важно отметить.",
    "Единица измерения эмиссии N2O": "Единица измерения эмиссии N2O. Важно отметить.",
    "Единица измерения эмиссии CH4": "Единица измерения эмиссии CH4. Важно отметить."
}
    # --- ЗАПУСК КОНВЕЙЕРА ---

    try:

        # --- ВЫЗОВ ШАГА 2 ---
        logger.info("--- ЗАПУСК: Шаг 2 (Анализ PDF) ---")
        run_analyzing(
            pdf_folder_path=PDF_FOLDER_PATH,
            features=extraction_schema,
            batch_size=4,
            logger=logger
        )
        logger.info("--- ЗАВЕРШЕНИЕ: Шаг 2 ---")

    except Exception as e:
        logger.critical(f"Произошла критическая ошибка в главном процессе: {e}", exc_info=True)

    print("\n" + "="*60)
    print("                  Работа конвейера завершена!")
    print("="*60 + "\n")


# --- Точка входа в программу ---
if __name__ == '__main__':
    main()