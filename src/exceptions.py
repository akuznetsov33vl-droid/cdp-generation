"""Иерархия исключений CDP Generation."""


class CDPGenerationError(Exception):
    """Базовое исключение проекта."""


class ConfigError(CDPGenerationError):
    """Ошибка конфигурации (отсутствует ключ, неверный путь)."""


class ScrapeError(CDPGenerationError):
    """Ошибка парсинга сайта клиента."""


class LLMError(CDPGenerationError):
    """Ошибка вызова LLM-провайдера."""


class LLMParseError(LLMError):
    """LLM вернул ответ, который не парсится в ожидаемую модель."""


class ReviewFailedError(CDPGenerationError):
    """Ревьюер забраковал сгенерированное КП."""


class PDFRenderError(CDPGenerationError):
    """Не удалось отрендерить PDF."""
