"""
Настройки django-log-viewer

Просмотр и скачивание лог-файлов из админки.
Использует LOGS_DIR из base.py.
"""
# Каталог с логами (должен быть задан в base.py как LOGS_DIR)
LOG_VIEWER_FILES_DIR = str(LOGS_DIR)
LOG_VIEWER_FILES_PATTERN = "*.log*"
LOG_VIEWER_PAGE_LENGTH = 25
LOG_VIEWER_MAX_READ_LINES = 1000
LOG_VIEWER_FILE_LIST_MAX_ITEMS_PER_PAGE = 25
LOG_VIEWER_PATTERNS = ["[INFO]", "[DEBUG]", "[WARNING]", "[ERROR]", "[CRITICAL]"]
