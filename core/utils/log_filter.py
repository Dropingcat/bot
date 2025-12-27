# -*- coding: utf-8 -*-
"""
Фильтр логов — убирает эмодзи и Unicode.
"""

import re
import logging

class EmojiFilter(logging.Filter):
    """
    Фильтр, который убирает эмодзи и Unicode символы из сообщений лога.
    """
    # Регулярное выражение для поиска эмодзи
    EMOJI_PATTERN = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map symbols
        "\U0001f1e0-\U0001f1ff"  # flags (iOS)
        "\U00002500-\U00002bef"  # box drawings
        "\U00002702-\U000027b0"
        "\U000024c2-\U0001f251"
        "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
        "\U0001f018-\U0001f270"  # Various symbols
        "\U0001f30d-\U0001f567"  # Travel and Places
        "]+",
        flags=re.UNICODE
    )
    
    # Регулярное выражение для поиска Unicode символов (включая →)
    UNICODE_PATTERN = re.compile(
        "["
        "\u2190-\u21ff"  # arrows
        "\u2700-\u27bf"  # dingbats
        "\u2600-\u26ff"  # misc symbols
        "]+",
        flags=re.UNICODE
    )

    def filter(self, record):
        """
        Убирает эмодзи и Unicode символы из сообщения.
        """
        if record.msg:
            # Убираем эмодзи
            clean_msg = self.EMOJI_PATTERN.sub('', record.msg)
            # Убираем Unicode символы
            clean_msg = self.UNICODE_PATTERN.sub('', clean_msg)
            # Убираем лишние пробелы
            clean_msg = ' '.join(clean_msg.split())
            record.msg = clean_msg
        return True

class UnicodeSafeFormatter(logging.Formatter):
    """
    Форматтер, который безопасно обрабатывает Unicode.
    """
    def format(self, record):
        """
        Форматирует запись, обрабатывая Unicode.
        """
        try:
            return super().format(record)
        except UnicodeEncodeError:
            # Если ошибка — заменяем символы
            record.msg = str(record.msg).encode('utf-8', errors='replace').decode('utf-8')
            return super().format(record)