# Папка для результатов анализа

В эту папку автоматически сохраняются результаты работы системы:

## Структура файлов

### results/results_links/
Результаты поиска статей:
- `<тема_поиска>.csv` - список найденных статей с названиями и ссылками

**Формат:**
```csv
title,url
"Article Title","https://..."
```

### results/
Результаты анализа PDF:
- `<название_папки>_analysis.csv` - извлеченные данные из PDF

**Формат (широкий):**
```csv
source_file,Признак1,Признак2,Признак3,...
article1.pdf,значение1,значение2,значение3,...
article2.pdf,значение1,значение2,значение3,...
```

## Примеры использования результатов

### Python/Pandas
```python
import pandas as pd

# Загрузка результатов
df = pd.read_csv('results/my_analysis.csv')

# Базовая статистика
print(df.describe())

# Фильтрация
recent = df[df['Year'] > 2020]

# Экспорт в Excel
df.to_excel('analysis.xlsx', index=False)
```

### Excel
Файлы сохранены с кодировкой UTF-8-BOM и корректно открываются в Excel.

### R
```r
library(readr)
data <- read_csv("results/my_analysis.csv")
summary(data)
```

## Очистка

Для очистки результатов:
```bash
# Удалить все результаты
rm -rf results/*

# Или выборочно
rm results/old_analysis.csv
```

**Примечание:** Эта папка создается автоматически при первом запуске.
