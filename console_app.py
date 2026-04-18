import sys
import logging
from pathlib import Path

# Импортируем нашу исправленную логику
from core_logic import run_links, run_analyzing

# --- 1. Настройка логирования для вывода в консоль ---
# Направляем логи в консоль для наглядности
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    stream=sys.stdout  # Вывод логов прямо в терминал
)
# Получаем корневой логгер, который будут использовать наши функции
logger = logging.getLogger()


def step_1_find_articles():
    """
    Шаг 1: Запрашивает у пользователя тему, ищет статьи и сохраняет их в CSV.
    """
    logger.info("--- ШАГ 1: ПОИСК СТАТЕЙ ---")
    
    try:
        topic = input("Введите тему для поиска статей: ")
        if not topic:
            logger.error("Тема не может быть пустой. Завершение работы.")
            return

        # Вызываем нашу основную функцию из core_logic
        run_links(topic=topic, logger=logger)

    except Exception as e:
        logger.error(f"Произошла критическая ошибка на Шаге 1: {e}")


def step_2_analyze_pdfs():
    """
    Шаг 2: Запрашивает путь к папке с PDF, анализирует их и сохраняет результат.
    """
    logger.info("\n" + "---" * 20)
    logger.info("--- ШАГ 2: АНАЛИЗ СКАЧАННЫХ PDF-ФАЙЛОВ ---")
    
    while True:
        pdf_folder_path_str = input("Введите ПОЛНЫЙ путь к папке с вашими PDF-файлами: ")
        pdf_folder_path = Path(pdf_folder_path_str)
        
        if pdf_folder_path.is_dir():
            logger.info(f"Папка найдена: {pdf_folder_path}")
            break
        else:
            logger.error("Указанный путь не существует или не является папкой. Попробуйте еще раз.")

    try:
        # Вызываем нашу основную функцию из core_logic
        run_analyzing(pdf_folder_path_str, logger=logger)
    except Exception as e:
        logger.error(f"Произошла критическая ошибка на Шаге 2: {e}")


def main():
    """
    Основная функция, запускающая приложение.
    """
    print("\n" + "="*60)
    print("      Добро пожаловать в консольное приложение для анализа статей!")
    print("="*60 + "\n")

    # --- ЗАПУСК ШАГА 1 ---
    step_1_find_articles()

    # --- ПЕРЕХОД К ШАГУ 2 ---
    print("\n" + "*"*60)
    print("Шаг 1 завершен. Пожалуйста, скачайте нужные статьи в формате PDF")
    print("в отдельную папку на вашем компьютере.")
    print("*"*60 + "\n")
    
    input("Нажмите Enter, когда будете готовы продолжить и указать путь к папке...")

    # --- ЗАПУСК ШАГА 2 ---
    step_2_analyze_pdfs()

    print("\n" + "="*60)
    print("                  Работа приложения завершена!")
    print("         Все результаты сохранены в папке 'results'.")
    print("="*60 + "\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nРабота приложения прервана пользователем.")
    except Exception as e:
        logger.critical(f"Произошла непредвиденная ошибка, приложение будет закрыто: {e}")