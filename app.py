import streamlit as st
import logging
from pathlib import Path

# Импортируем нашу основную логику
from core_logic import run_links, run_analyzing, RESULTS_DIR

# --- Настройка логирования для вывода в UI ---
# Создаем кастомный обработчик логов, который будет писать в элемент Streamlit
class StreamlitLogHandler(logging.Handler):
    def __init__(self, container):
        super().__init__()
        self.container = container
        self.buffer = []

    def emit(self, record):
        # Добавляем отформатированное сообщение в буфер
        self.buffer.append(self.format(record))
        # Обновляем текст в контейнере
        self.container.markdown("\n".join(f"`{msg}`" for msg in self.buffer[-2:]))
        
# --- Настройка UI ---
st.set_page_config(page_title="Анализатор Статей", layout="wide") 
st.title("👨‍🔬 Приложение для анализа научных статей")

# Создаем контейнер для логов в UI
log_container = st.empty()
# Настраиваем логгер, чтобы он писал в наш контейнер
logger = logging.getLogger()
handler = StreamlitLogHandler(log_container)
handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --- Управление состоянием между шагами ---
# st.session_state - это "память" приложения
if 'step' not in st.session_state:
    st.session_state.step = 1

if 'features' not in st.session_state:
    st.session_state.features = []

# === ШАГ 1: Поиск статей ===
if st.session_state.step == 1:
    st.header("Шаг 1: Поиск статей по теме")
    
    # Поле для ввода темы
    topic_input = st.text_input("Введите тему для поиска:", "Анализ данных в России")
    
    col1, col2 = st.columns([3, 2]) # Кнопка "Найти" будет шире

    with col1:
        if st.button("🔍 Найти статьи", use_container_width=True):
            if topic_input:
                with st.spinner("Идет поиск... Это может занять несколько минут..."):
                    try:
                        result_file_path = run_links(
                            TOPIC=topic_input,
                            total_iterations=3,
                            logger=logger
                        )
                        
                        if result_file_path:
                            st.session_state.step = 2
                            st.session_state.links_file = result_file_path
                            st.rerun()
                        else:
                            st.error("Поиск завершился, но не удалось найти статьи. Попробуйте другую тему.")
                    except Exception as e:
                        st.error(f"Произошла критическая ошибка: {e}")
            else:
                st.warning("Пожалуйста, введите тему.")

    with col2:
        # --- КНОПКА ДЛЯ ПРОПУСКА ---
        if st.button("Пропустить и загрузить свои PDF", use_container_width=True):
            logger.info("Шаг 1 пропущен. Переход к анализу PDF.")
            st.session_state.step = 2
            # Убедимся, что переменная для файла ссылок пустая
            st.session_state.links_file = None 
            st.rerun()


# === ШАГ 2: Анализ PDF ===
if st.session_state.step == 2:
    st.header("Шаг 2: Анализ скачанных PDF")
    
    if st.session_state.get('links_file'):
        st.success(f"Шаг 1 завершен! Ссылки сохранены в файл: `{st.session_state.links_file}`")
        st.info("Пожалуйста, скачайте нужные статьи в отдельную папку и укажите путь к ней ниже.")
    else:
        # Сообщение для тех, кто пропустил Шаг 1
        st.info("Пожалуйста, укажите путь к папке с вашими PDF-файлами для анализа.")

    pdf_folder_input = st.text_input("Введите полный путь к папке с PDF файлами:")

    st.markdown("---")
    st.subheader("Настройте признаки для извлечения:")

    # ---Динамическая форма для ввода признаков ---
    
    # Создаем контейнер для формы
    form_container = st.container()
    
    with form_container:
        # Отрисовываем поля для каждого признака в памяти
        for i, feature in enumerate(st.session_state.features):
            col1, col2, col3 = st.columns([3, 6, 1])
            with col1:
                # `key` - это уникальный идентификатор для каждого виджета
                st.session_state.features[i]['name'] = st.text_input(
                    "Имя признака (ключ)", 
                    value=feature['name'], 
                    key=f"name_{i}"
                )
            with col2:
                st.session_state.features[i]['description'] = st.text_input(
                    "Описание (инструкция для AI)", 
                    value=feature['description'], 
                    key=f"desc_{i}"
                )
            with col3:
                # Добавляем немного пустого пространства для выравнивания кнопки
                st.write("") 
                st.write("")
                if st.button("❌", key=f"del_{i}", help="Удалить этот признак"):
                    st.session_state.features.pop(i)
                    st.rerun() # Перезапускаем, чтобы форма перерисовалась

    # Кнопка для добавления нового пустого признака
    if st.button("➕ Добавить признак"):
        st.session_state.features.append({"name": "", "description": ""})
        st.rerun()

    st.markdown("---")

    # Основная кнопка для запуска анализа
    if st.button("🔬 Проанализировать PDF", type="primary"):
        # Преобразуем список словарей в единый словарь-схему
        final_schema = {feature['name']: feature['description'] for feature in st.session_state.features if feature['name']}
        
        if not final_schema:
            st.warning("Пожалуйста, добавьте хотя бы один признак для извлечения.")
        elif pdf_folder_input and Path(pdf_folder_input).is_dir():
            with st.spinner("Идет анализ PDF... Это очень ресурсоемкий процесс..."):
                try:
                    # Передаем собранную схему в нашу функцию
                    analysis_result_path = run_analyzing(
                        pdf_folder_path=pdf_folder_input,
                        features=final_schema,
                        logger=logger
                    )
                    
                    if analysis_result_path:
                        st.session_state.step = 3
                        st.session_state.analysis_file = analysis_result_path
                        st.rerun()
                    else:
                        st.error("Анализ завершился, но не удалось извлечь данные.")
                except Exception as e:
                    st.error(f"Произошла критическая ошибка: {e}")
        else:
            st.warning("Пожалуйста, введите корректный путь к папке.")
    

# === ШАГ 3: Завершение ===
if st.session_state.step == 3:
    st.header("✅ Работа завершена!")
    st.balloons()
    st.success(f"Результаты анализа сохранены в файл: `{st.session_state.analysis_file}`")
    st.info(f"Все итоговые файлы вы найдете в папке: `{RESULTS_DIR}`")
    
    # Кнопка для начала нового анализа
    if st.button("Начать заново"):
        st.session_state.step = 1
        st.rerun()