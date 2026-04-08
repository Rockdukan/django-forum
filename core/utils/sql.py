import time
from functools import wraps

from django.conf import settings
from django.db import connection

# ANSI-последовательности
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"


def log_queries(threshold: float = 0.1):
    """
    Декоратор для логирования медленных функций и числа SQL-запросов.

    :param threshold: время (в секундах), выше которого считается медленным
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            if settings.DEBUG:
                connection.queries.clear()

            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start

            if elapsed > threshold:
                total = len(connection.queries)
                print(f"{RED}[{func.__name__}]{RESET} {YELLOW}Slow: {elapsed:.3f}s, {total} SQL queries{RESET}")

                for q in connection.queries:
                    # каждая запись: {'sql': 'SELECT ...', 'time': '0.001'}
                    print(f"{CYAN}SQL ({q['time']}s):{RESET} {q['sql']}")

            return result

        return wrapper

    return decorator
