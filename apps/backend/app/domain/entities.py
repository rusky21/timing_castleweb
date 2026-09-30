import enum


class LeadStatus(str, enum.Enum):
    PENDING = "pending"          # Только пришел с сайта, обрабатывается
    DELIVERED = "delivered"      # Отправлен в Telegram бот
    IN_PROGRESS = "in_progress"  # Инженер нажал "Взять в работу"
    CONTACTED = "contacted"      # Инженер связался с клиентом
    SPAM = "spam"                # Отклонен как спам (IP отправлен в бан)
    ARCHIVED = "archived"        # Завершен / закрыт


class CaseCategory(str, enum.Enum):
    SAAS = "saas"                # Веб-сервисы и SaaS
    LANDING = "landing"          # Продуктовые промо и лендинги
    ECOMMERCE = "ecommerce"      # E-commerce и маркетплейсы
    API = "api"                  # Highload API и интеграции
