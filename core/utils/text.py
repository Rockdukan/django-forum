import re


def clean_text(text):
    """
    Очищает текст: заменяет пробелы, дефисы, подчёркивания на дефисы
    и удаляет знаки препинания, включая слэши
    """
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"[\\/]", "", text)
    text = re.sub(r"[^\w\d-]", "", text)
    return text


def transliterate(text: str) -> str:
    """Транслитерация кириллицы в латиницу"""
    slovar = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "yo",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "i",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "c",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "u",
        "я": "ya",
        "А": "A",
        "Б": "B",
        "В": "V",
        "Г": "G",
        "Д": "D",
        "Е": "E",
        "Ё": "YO",
        "Ж": "ZH",
        "З": "Z",
        "И": "I",
        "Й": "I",
        "К": "K",
        "Л": "L",
        "М": "M",
        "Н": "N",
        "О": "O",
        "П": "P",
        "Р": "R",
        "С": "S",
        "Т": "T",
        "У": "U",
        "Ф": "F",
        "Х": "H",
        "Ц": "C",
        "Ч": "CH",
        "Ш": "SH",
        "Щ": "SCH",
        "Ъ": "",
        "Ы": "Y",
        "Ь": "",
        "Э": "E",
        "Ю": "U",
        "Я": "YA",
    }

    # Формируем новую строку, заменяя символы
    transliterated_text = "".join(slovar.get(char, char) for char in text)
    return transliterated_text


def slugify(text: str) -> str:
    """Слагификация"""
    slug = transliterate(clean_text(text.lower()))
    return slug[:70]
