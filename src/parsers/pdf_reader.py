import os
import pdfplumber
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTFigure


class PDFProcessor:
    """
    Улучшенный класс для извлечения структурированного контента из PDF.
    Он обрабатывает текст, таблицы и определяет местоположение изображений.
    """
    def __init__(self, pdf_path):
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Файл не найден: {pdf_path}")
        self.pdf_path = pdf_path
        self.pdf = pdfplumber.open(pdf_path)
        print(f"PDF-файл '{pdf_path}' успешно открыт. Всего страниц: {len(self.pdf.pages)}")

    def __del__(self):
        """Закрывает PDF-файл при уничтожении объекта."""
        if hasattr(self, 'pdf'):
            self.pdf.close()
            print("PDF-файл закрыт.")

    def process_all_pages(self) -> dict:
        """Обрабатывает все страницы PDF и возвращает структурированные данные."""
        all_pages_data = {}
        for page_num in range(len(self.pdf.pages)):
            all_pages_data[f"Page_{page_num + 1}"] = self._process_page(page_num)
        return all_pages_data

    def _process_page(self, page_num: int) -> list:
        """Обрабатывает одну страницу, извлекая текст, таблицы и изображения."""
        page_content = []
        page_miner = list(extract_pages(self.pdf_path, page_numbers=[page_num]))[0]
        page_plumber = self.pdf.pages[page_num]

        # 1. Сначала находим все таблицы и их координаты с помощью pdfplumber
        tables = page_plumber.find_tables()
        table_bboxes = [table.bbox for table in tables]
        
        # 2. Извлекаем и конвертируем таблицы
        extracted_tables = [self._table_converter(table.extract()) for table in tables]

        # 3. Обходим все элементы на странице с помощью pdfminer
        page_elements = [(element.y1, element) for element in page_miner._objs]
        page_elements.sort(key=lambda a: a[0], reverse=True)

        for component in page_elements:
            element = component[1]

            # Проверяем, не находится ли элемент внутри уже найденной таблицы
            element_bbox = (element.x0, element.y0, element.x1, element.y1)
            is_in_table = any(self._is_within_bbox(element_bbox, table_bbox) for table_bbox in table_bboxes)
            
            if is_in_table:
                continue # Пропускаем, так как этот контент уже обработан как часть таблицы

            if isinstance(element, LTTextContainer):
                text, formats = self._extract_text_and_format(element)
                page_content.append({"type": "text", "content": text, "formats": formats})

            if isinstance(element, LTFigure):
                # Вместо реальной обработки просто помечаем наличие изображения
                page_content.append({"type": "image", "bbox": element.bbox})

        # 4. Добавляем таблицы в контент страницы, сохраняя порядок
        # (Это упрощенная вставка в конец, для точного позиционирования нужна более сложная логика)
        for table_str in extracted_tables:
            page_content.append({"type": "table", "content": table_str})
            
        return page_content

    def _is_within_bbox(self, inner_bbox, outer_bbox):
        """Проверяет, находится ли один bounding box внутри другого."""
        x0, y0, x1, y1 = inner_bbox
        X0, Y0, X1, Y1 = outer_bbox
        # Добавляем небольшой допуск (2px)
        return x0 >= X0 - 2 and y0 >= Y0 - 2 and x1 <= X1 + 2 and y1 <= Y1 + 2

    def _extract_text_and_format(self, element: LTTextContainer) -> tuple:
        """Извлекает текст и уникальные форматы (шрифт, размер) из текстового элемента."""
        line_text = element.get_text().strip()
        
        formats = []
        for text_line in element:
            if isinstance(text_line, LTTextContainer):
                for character in text_line:
                    if isinstance(character, LTChar):
                        formats.append(f"{character.fontname}-{character.size:.2f}")
        
        unique_formats = list(set(formats))
        return (line_text, unique_formats)

    def _table_converter(self, table: list) -> str:
        """Преобразует извлеченную таблицу в Markdown-подобную строку."""
        table_string = ''
        for row in table:
            cleaned_row = [str(item).replace('\n', ' ') if item is not None else '' for item in row]
            table_string += '| ' + ' | '.join(cleaned_row) + ' |\n'
        return table_string.strip()


def save_to_txt(data: dict, output_path: str = "output.txt"):
    """
    Сохраняет извлеченные из PDF данные в текстовый файл.

    Args:
        data (dict): Словарь с данными, где ключи - названия страниц, 
                     а значения - список извлеченных элементов.
        output_filename (str): Имя файла для сохранения.
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        # Итерируемся по каждой странице в наших данных
        for page_name, content_list in data.items():
            # Записываем красивый заголовок для каждой страницы
            f.write(f"--- {page_name.replace('_', ' ')} ---\n\n")
            
            # Итерируемся по каждому элементу контента на странице
            for item in content_list:
                # Изображения не содержат текста, поэтому мы их пропускаем
                # Но можно было бы записать их координаты: f.write(f"[IMAGE AT {item['bbox']}]\n\n")
                if item['type'] != 'image':
                    # Записываем содержимое текстового блока или таблицы
                    f.write(item['content'])
                    # Добавляем два переноса строки для разделения блоков
                    f.write("\n\n")
    
    print(f"Данные были успешно сохранены в файл: {output_path}")


# --- Пример использования ---
# if __name__ == '__main__':
#     try:
#         pdf_path = 'three.pdf' # Укажите путь к вашему PDF
#         processor = PDFProcessor(pdf_path)
#         all_data = processor.process_all_pages()

#         output_file = f"{pdf_path.split('.')[0]}_extracted_content.txt"
#         save_to_txt(all_data, output_file)

#     except FileNotFoundError as e:
#         print(e)
#     except Exception as e:
#         print(f"Произошла непредвиденная ошибка: {e}")