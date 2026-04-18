import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

# Импорты для Dockling
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    logging.warning("Docling не установлен. Установите: pip install docling")

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logging.warning("EasyOCR не установлен. Установите: pip install easyocr")

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("Tesseract не установлен. Установите: pip install pytesseract Pillow")


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OCRPDFProcessor:
    """
    Продвинутый процессор PDF с OCR поддержкой через Dockling.
    
    Возможности:
    - Автоматическое определение сканированных страниц
    - OCR для текста на изображениях
    - Извлечение таблиц из сканов
    - Поддержка множества языков
    - Два OCR движка: EasyOCR (нейросетевой) и Tesseract (классический)
    """
    
    def __init__(
        self, 
        pdf_path: str,
        ocr_engine: str = "easyocr",
        languages: List[str] = ['en'],
        enable_table_extraction: bool = True,
        enable_image_extraction: bool = True
    ):
        """
        Инициализация процессора.
        
        Args:
            pdf_path: Путь к PDF файлу
            ocr_engine: "easyocr" (нейросеть, точнее) или "tesseract" (быстрее)
            languages: Список языков для OCR, например ['en', 'ru', 'zh']
            enable_table_extraction: Извлекать таблицы
            enable_image_extraction: Извлекать изображения
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF файл не найден: {pdf_path}")
        
        if not DOCLING_AVAILABLE:
            raise ImportError("Docling не установлен. Установите: pip install docling")
        
        self.pdf_path = pdf_path
        self.ocr_engine = ocr_engine.lower()
        self.languages = languages
        self.enable_table_extraction = enable_table_extraction
        self.enable_image_extraction = enable_image_extraction
        
        # Инициализация OCR движка
        self._init_ocr_engine()
        
        # Инициализация Dockling конвертера
        self._init_docling_converter()
        
        logger.info(f"OCRPDFProcessor инициализирован для файла: {pdf_path}")
        logger.info(f"OCR движок: {self.ocr_engine}, языки: {self.languages}")
    
    def _init_ocr_engine(self):
        """Инициализация выбранного OCR движка"""
        if self.ocr_engine == "easyocr":
            if not EASYOCR_AVAILABLE:
                raise ImportError("EasyOCR не установлен. Установите: pip install easyocr")
            logger.info("Инициализация EasyOCR... (может занять время при первом запуске)")
            self.ocr_reader = easyocr.Reader(self.languages, gpu=False)
            logger.info("EasyOCR готов к работе")
            
        elif self.ocr_engine == "tesseract":
            if not TESSERACT_AVAILABLE:
                raise ImportError("Tesseract не установлен. Установите: pip install pytesseract Pillow")
            # Проверка установки tesseract
            try:
                pytesseract.get_tesseract_version()
                logger.info(f"Tesseract версия: {pytesseract.get_tesseract_version()}")
            except Exception as e:
                raise RuntimeError(f"Tesseract не установлен в системе: {e}")
        else:
            raise ValueError(f"Неизвестный OCR движок: {self.ocr_engine}. Используйте 'easyocr' или 'tesseract'")
    
    def _init_docling_converter(self):
        """Инициализация Dockling Document Converter"""
        # Настройка pipeline для OCR
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = self.enable_table_extraction
        
        # Создание конвертера
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: pipeline_options,
            }
        )
        logger.info("Docling Document Converter инициализирован")
    
    def process_all_pages(self) -> Dict:
        """
        Обрабатывает все страницы PDF с применением OCR.
        
        Returns:
            dict: Структурированные данные со всех страниц
        """
        logger.info("Начинаем обработку PDF с OCR...")
        
        try:
            # Конвертация документа через Docling
            result = self.converter.convert(self.pdf_path)
            
            # Извлечение структурированных данных
            all_pages_data = {}
            
            # Получаем документ
            doc = result.document
            
            # Обработка каждой страницы
            for page_num, page in enumerate(doc.pages, start=1):
                page_data = self._process_page(page, page_num)
                all_pages_data[f"Page_{page_num}"] = page_data
            
            logger.info(f"Обработано страниц: {len(all_pages_data)}")
            return all_pages_data
            
        except Exception as e:
            logger.error(f"Ошибка при обработке PDF: {e}", exc_info=True)
            raise
    
    def _process_page(self, page, page_num: int) -> List[Dict]:
        """
        Обрабатывает одну страницу.
        
        Args:
            page: Объект страницы из Docling
            page_num: Номер страницы
            
        Returns:
            list: Список элементов страницы (текст, таблицы, изображения)
        """
        page_content = []
        
        logger.info(f"Обработка страницы {page_num}...")
        
        # Извлечение текстовых блоков
        for text_block in page.text_blocks:
            page_content.append({
                "type": "text",
                "content": text_block.text,
                "bbox": text_block.bbox if hasattr(text_block, 'bbox') else None,
                "confidence": getattr(text_block, 'confidence', None)
            })
        
        # Извлечение таблиц (если включено)
        if self.enable_table_extraction and hasattr(page, 'tables'):
            for table in page.tables:
                table_data = self._extract_table(table)
                page_content.append({
                    "type": "table",
                    "content": table_data,
                    "bbox": table.bbox if hasattr(table, 'bbox') else None
                })
        
        # Извлечение изображений (если включено)
        if self.enable_image_extraction and hasattr(page, 'images'):
            for img in page.images:
                # Применяем OCR к изображению, если оно содержит текст
                ocr_text = self._ocr_image(img) if hasattr(img, 'image_data') else None
                
                page_content.append({
                    "type": "image",
                    "bbox": img.bbox if hasattr(img, 'bbox') else None,
                    "ocr_text": ocr_text,
                    "description": getattr(img, 'description', None)
                })
        
        return page_content
    
    def _extract_table(self, table) -> str:
        """
        Извлекает таблицу в markdown формат.
        
        Args:
            table: Объект таблицы из Docling
            
        Returns:
            str: Таблица в markdown формате
        """
        try:
            if hasattr(table, 'to_markdown'):
                return table.to_markdown()
            elif hasattr(table, 'data'):
                # Ручная конвертация в markdown
                table_string = ''
                for row in table.data:
                    cleaned_row = [str(cell).replace('\n', ' ') if cell is not None else '' for cell in row]
                    table_string += '| ' + ' | '.join(cleaned_row) + ' |\n'
                return table_string.strip()
            else:
                return str(table)
        except Exception as e:
            logger.warning(f"Не удалось извлечь таблицу: {e}")
            return "[Таблица не извлечена]"
    
    def _ocr_image(self, image) -> Optional[str]:
        """
        Применяет OCR к изображению.
        
        Args:
            image: Объект изображения
            
        Returns:
            str: Распознанный текст или None
        """
        try:
            if self.ocr_engine == "easyocr":
                # EasyOCR принимает путь к файлу или numpy array
                if hasattr(image, 'image_data'):
                    result = self.ocr_reader.readtext(image.image_data, detail=0)
                    return ' '.join(result)
                    
            elif self.ocr_engine == "tesseract":
                # Tesseract через PIL Image
                if hasattr(image, 'image_data'):
                    pil_image = Image.fromarray(image.image_data)
                    lang = '+'.join(self.languages)
                    return pytesseract.image_to_string(pil_image, lang=lang)
            
            return None
            
        except Exception as e:
            logger.warning(f"Ошибка OCR для изображения: {e}")
            return None
    
    def is_scanned_pdf(self) -> bool:
        """
        Определяет, является ли PDF сканированным документом.
        
        Returns:
            bool: True если документ сканированный
        """
        try:
            result = self.converter.convert(self.pdf_path)
            doc = result.document
            
            # Проверяем первые 3 страницы
            text_ratio = 0
            pages_checked = 0
            
            for page in doc.pages[:3]:
                pages_checked += 1
                if hasattr(page, 'text_blocks') and len(page.text_blocks) > 0:
                    text_ratio += 1
            
            # Если меньше 30% страниц содержат текст - это скан
            is_scanned = (text_ratio / pages_checked) < 0.3
            
            logger.info(f"PDF {'сканированный' if is_scanned else 'текстовый'} документ")
            return is_scanned
            
        except Exception as e:
            logger.error(f"Ошибка определения типа PDF: {e}")
            return False
    
    def save_to_txt(self, data: dict, output_path: str = "output.txt"):
        """
        Сохраняет извлеченные данные в текстовый файл.
        
        Args:
            data: Словарь с данными страниц
            output_path: Путь для сохранения
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for page_name, content_list in data.items():
                f.write(f"--- {page_name.replace('_', ' ')} ---\n\n")
                
                for item in content_list:
                    if item['type'] == 'text':
                        f.write(item['content'])
                        if item.get('confidence'):
                            f.write(f" [confidence: {item['confidence']:.2f}]")
                        f.write("\n\n")
                        
                    elif item['type'] == 'table':
                        f.write(item['content'])
                        f.write("\n\n")
                        
                    elif item['type'] == 'image':
                        if item.get('ocr_text'):
                            f.write(f"[IMAGE with text: {item['ocr_text']}]\n\n")
                        else:
                            f.write("[IMAGE]\n\n")
        
        logger.info(f"Данные сохранены в: {output_path}")
    
    def save_to_json(self, data: dict, output_path: str = "output.json"):
        """
        Сохраняет извлеченные данные в JSON формат.
        
        Args:
            data: Словарь с данными страниц
            output_path: Путь для сохранения
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Данные сохранены в JSON: {output_path}")


# Вспомогательные функции для интеграции

def process_pdf_with_ocr(
    pdf_path: str,
    output_txt: Optional[str] = None,
    ocr_engine: str = "easyocr",
    languages: List[str] = ['en', 'ru']
) -> Dict:
    """
    Упрощенная функция для обработки PDF с OCR.
    
    Args:
        pdf_path: Путь к PDF файлу
        output_txt: Путь для сохранения текста (опционально)
        ocr_engine: OCR движок ("easyocr" или "tesseract")
        languages: Языки для распознавания
    
    Returns:
        dict: Извлеченные данные
    
    Example:
        >>> data = process_pdf_with_ocr("scan.pdf", "output.txt", "easyocr", ['en', 'ru'])
        >>> print(data.keys())  # dict_keys(['Page_1', 'Page_2', ...])
    """
    processor = OCRPDFProcessor(
        pdf_path=pdf_path,
        ocr_engine=ocr_engine,
        languages=languages
    )
    
    data = processor.process_all_pages()
    
    if output_txt:
        processor.save_to_txt(data, output_txt)
    
    return data


def auto_detect_and_process(pdf_path: str, output_txt: Optional[str] = None) -> Dict:
    """
    Автоматически определяет тип PDF и выбирает метод обработки.
    
    Args:
        pdf_path: Путь к PDF файлу
        output_txt: Путь для сохранения текста (опционально)
    
    Returns:
        dict: Извлеченные данные
    """
    # Пытаемся определить тип документа
    try:
        processor = OCRPDFProcessor(pdf_path=pdf_path, ocr_engine="easyocr")
        
        if processor.is_scanned_pdf():
            logger.info("Обнаружен сканированный PDF, используем OCR")
            data = processor.process_all_pages()
        else:
            logger.info("Обнаружен текстовый PDF, используем обычное извлечение")
            # Используем стандартный PDFProcessor из pdf_reader.py
            from src.parsers.pdf_reader import PDFProcessor, save_to_txt
            standard_processor = PDFProcessor(pdf_path)
            data = standard_processor.process_all_pages()
        
        if output_txt:
            processor.save_to_txt(data, output_txt)
        
        return data
        
    except Exception as e:
        logger.error(f"Ошибка авто-определения: {e}")
        raise



if __name__ == '__main__':

    
    # Базовая обработка с EasyOCR
    print("\n" + "="*60)
    print("Пример 1: Обработка сканированного PDF с EasyOCR")
    print("="*60)
    
    try:
        processor = OCRPDFProcessor(
            pdf_path="scan_example.pdf",
            ocr_engine="easyocr",
            languages=['en', 'ru']  # Английский и русский
        )
        
        # Проверка типа документа
        if processor.is_scanned_pdf():
            print("Документ определен как сканированный")
        
        # Обработка
        data = processor.process_all_pages()
        
        # Сохранение
        processor.save_to_txt(data, "output_easyocr.txt")
        processor.save_to_json(data, "output_easyocr.json")
        
        print(f"Обработано страниц: {len(data)}")
        
    except FileNotFoundError:
        print(" Файл scan_example.pdf не найден (это нормально для примера)")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    
    # Обработка с Tesseract (быстрее)
    print("\n" + "="*60)
    print("Пример 2: Обработка с Tesseract")
    print("="*60)
    
    try:
        data = process_pdf_with_ocr(
            pdf_path="scan_example.pdf",
            output_txt="output_tesseract.txt",
            ocr_engine="tesseract",
            languages=['eng', 'rus']  # Tesseract использует другие коды
        )
        print(f"Обработано страниц: {len(data)}")
        
    except FileNotFoundError:
        print("Файл scan_example.pdf не найден (это нормально для примера)")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    
    # Автоматическое определение типа PDF
    print("\n" + "="*60)
    print("Пример 3: Автоматическое определение")
    print("="*60)
    
    try:
        data = auto_detect_and_process(
            pdf_path="any_document.pdf",
            output_txt="output_auto.txt"
        )
        print(f"Обработано страниц: {len(data)}")
        
    except FileNotFoundError:
        print(" Файл any_document.pdf не найден (это нормально для примера)")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    
    #  Обработка только таблиц
    print("\n" + "="*60)
    print("Пример 4: Извлечение только таблиц")
    print("="*60)
    
    try:
        processor = OCRPDFProcessor(
            pdf_path="tables_scan.pdf",
            ocr_engine="easyocr",
            languages=['en'],
            enable_table_extraction=True,
            enable_image_extraction=False  # Отключаем изображения
        )
        
        data = processor.process_all_pages()
        
        # Фильтруем только таблицы
        tables_only = {}
        for page, items in data.items():
            tables = [item for item in items if item['type'] == 'table']
            if tables:
                tables_only[page] = tables
        
        print(f"Найдено таблиц на страницах: {len(tables_only)}")
        
    except FileNotFoundError:
        print(" Файл tables_scan.pdf не найден (это нормально для примера)")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    
    print("\n" + "="*60)
    print("Примеры завершены!")
    print("="*60)