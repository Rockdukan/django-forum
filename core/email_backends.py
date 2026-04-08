"""Почтовые бэкенды проекта."""

from __future__ import annotations

import re

from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend

# Ключ allauth: один сегмент пути; в нём допустимы «:», «-», буквы и цифры (без «/»).
# Ищем полный http(s) URL до конца строки/кавычки.
_CONFIRM_URL_RE = re.compile(
    r"https?://[^\s<>\")']+/accounts/confirm-email/[^\s<>\")']+",
    re.IGNORECASE,
)


def _trim_trailing_junk(url: str) -> str:
    return url.rstrip(").,]}>'\"")


def _confirmation_urls(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in _CONFIRM_URL_RE.finditer(text):
        url = _trim_trailing_junk(m.group(0))
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def _collect_searchable_text(message) -> str:
    """Текст письма до MIME и все части после decode (в т.ч. base64 text/plain)."""
    chunks: list[str] = []
    body = getattr(message, "body", None) or ""
    if body:
        chunks.append(body)
    for alt in getattr(message, "alternatives", None) or ():
        if isinstance(alt, (list, tuple)) and alt and isinstance(alt[0], str):
            chunks.append(alt[0])
    try:
        mime = message.message()
        for part in mime.walk():
            if part.get_content_maintype() == "multipart":
                continue
            payload = part.get_payload(decode=True)
            if not payload or not isinstance(payload, (bytes, bytearray)):
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                chunks.append(payload.decode(charset, errors="replace"))
            except Exception:
                chunks.append(payload.decode("utf-8", errors="replace"))
    except Exception:
        pass
    return "\n".join(chunks)


class DevConsoleEmailBackend(ConsoleEmailBackend):
    """
    Как console backend (полный MIME в консоль), но перед MIME выводится блок
    с готовой ссылкой подтверждения — без копирования base64 из тела письма.
    """

    def _write_confirmation_banner(self, message) -> None:
        urls = _confirmation_urls(_collect_searchable_text(message))
        if not urls:
            return
        line = "=" * 72 + "\n"
        self.stream.write("\n" + line)
        self.stream.write(
            "[EMAIL DEV] Подтверждение email — вставьте в адресную строку браузера "
            "(одна строка, целиком, без пробелов и переносов):\n"
        )
        for url in urls:
            self.stream.write(url + "\n")
        self.stream.write(line)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        msg_count = 0
        with self._lock:
            try:
                stream_created = self.open()
                for message in email_messages:
                    self._write_confirmation_banner(message)
                    self.write_message(message)
                    self.stream.flush()
                    msg_count += 1
                if stream_created:
                    self.close()
            except Exception:
                if not self.fail_silently:
                    raise
        return msg_count
