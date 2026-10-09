import re
import json
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.deepseek.client import deepseek_client
from app.services.outreach.prompts import get_prompt, DEFAULT_CLASSIFIER_PROMPT

logger = logging.getLogger("intent_classifier")

PHONE_REGEX = re.compile(r"(?:\+7|8)[\s\-]?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}")


class IntentClassifier:
    """
    Классификатор намерений входящих сообщений на базе DeepSeek с отказоустойчивым
    регулярным/эвристическим Fallback для 100% стабильности.
    """

    @staticmethod
    def _heuristic_classify(text: str) -> Dict[str, Any]:
        """
        Резервный детерминированный классификатор на правилах и ключевых словах.
        """
        t = text.lower().strip()
        phone_match = PHONE_REGEX.search(text)
        extracted_phone = phone_match.group(0) if phone_match else None

        # 1. Жесткий отказ / ненормативная лексика / спам
        hard_reject_words = [
            "спам", "пошел", "нахуй", "на хуй", "заебал", "в суд", "заявление",
            "жалоб", "отписка", "не пишите", "удалите номер", "черный список", "чс"
        ]
        if any(w in t for w in hard_reject_words):
            return {
                "intent": "REJECT_HARD",
                "confidence": 0.95,
                "recommended_response": "Понял вас, извините за беспокойство. Больше не потревожу.",
                "requires_human": False,
                "extracted_phone": None
            }

        # 2. Проверка на бота
        is_bot_words = ["ты бот", "ты робот", "ты ии", "нейросеть", "чатгпт", "chatgpt", "автоответчик", "робот?"]
        if any(w in t for w in is_bot_words):
            return {
                "intent": "IS_BOT",
                "confidence": 0.95,
                "recommended_response": "Да не, руками пишу) Я разработчик из CastleWeb, сайты делаем. Просто с телефона на сайт зашел и увидел косяк в верстке",
                "requires_human": False,
                "extracted_phone": None
            }

        # 3. Вопрос о личности / компании
        identity_words = ["кто вы", "вы кто", "какая компания", "с кем я общаюсь", "агентство", "фрилансер", "организация"]
        if any(w in t for w in identity_words):
            return {
                "intent": "QUESTION_IDENTITY",
                "confidence": 0.92,
                "recommended_response": "Я разработчик из CastleWeb (занимаемся разработкой и доработкой сайтов). Зашел к вам с телефона и заметил, что форма заявки съехала, решил написать",
                "requires_human": False,
                "extracted_phone": None
            }

        # 4. Вопрос об источнике контакта
        source_words = ["откуда номер", "где взяли", "откуда контакт", "откуда у вас", "где нашли"]
        if any(w in t for w in source_words):
            return {
                "intent": "QUESTION_SOURCE",
                "confidence": 0.92,
                "recommended_response": "Искал контакты на Яндекс.Картах / 2ГИС в карточке вашей компании.",
                "requires_human": False,
                "extracted_phone": None
            }

        # 5. Просьба показать пруф / скриншот
        proof_words = ["скинь скрин", "скиньте скрин", "покажи", "покажите", "где именно", "что за ошибка", "какой баг", "пришли скрин", "пришлите"]
        if any(w in t for w in proof_words):
            return {
                "intent": "REQUEST_PROOF",
                "confidence": 0.94,
                "recommended_response": "Да, сейчас пришлю скриншот с телефона, где видно ошибку",
                "requires_human": False,
                "extracted_phone": None
            }

        # 6. Свой программист / штат
        dev_words = ["свой разработчик", "свой программист", "свой спец", "штат", "наш программист", "есть кому делать", "свое агентство"]
        if any(w in t for w in dev_words):
            return {
                "intent": "OBJECTION_DEV",
                "confidence": 0.92,
                "recommended_response": "Отлично! Передайте ему скриншот — пусть поправит форму, а то с мобилок заявки теряются. Денег не нужно, просто хотел помочь.",
                "requires_human": False,
                "extracted_phone": None
            }

        # 7. Скепсис («у нас все работает»)
        skeptic_words = ["все работает", "всё работает", "все нормально", "всё открывается", "проверил, все ок", "у нас ок"]
        if any(w in t for w in skeptic_words):
            return {
                "intent": "SKEPTIC",
                "confidence": 0.90,
                "recommended_response": "На компьютере всё отлично. Ошибка вылезает именно на экранах смартфонов шириной до 390px (iPhone/Android). Сейчас пришлю скриншот.",
                "requires_human": False,
                "extracted_phone": None
            }

        # 8. Отправить на почту
        email_words = ["на почту", "пришлите кп", "скиньте на email", "на мыло", "коммерческое"]
        if any(w in t for w in email_words) or "@" in t:
            return {
                "intent": "SEND_EMAIL",
                "confidence": 0.88,
                "recommended_response": "Шаблонов КП не держу, задача точечная на 1–2 часа работы. Давайте пришлю скриншот сюда или кратко созвонимся на 3 минуты?",
                "requires_human": False,
                "extracted_phone": None
            }

        # 9. Мягкий отказ
        soft_reject_words = ["не интересно", "не нужно", "не актуально", "не надо", "позже", "спасибо, не"]
        if any(w in t for w in soft_reject_words):
            return {
                "intent": "REJECT_SOFT",
                "confidence": 0.85,
                "recommended_response": "Вас понял, хорошего дня! Если будет актуально — пишите.",
                "requires_human": False,
                "extracted_phone": None
            }

        # 10. Прямой интерес / цена / созвон
        interest_words = ["сколько стоит", "цена", "стоимость", "почем", "давайте", "наберите", "позвоните", "созвонимся", "хотим", "готов", "подробнее"]
        if any(w in t for w in interest_words) or extracted_phone:
            return {
                "intent": "INTERESTED",
                "confidence": 0.95,
                "recommended_response": "Отлично! Сейчас свяжусь с вами для согласования деталей.",
                "requires_human": True,
                "extracted_phone": extracted_phone
            }

        # Дефолтный нейтральный разговор
        return {
            "intent": "OTHER_CONVERSATION",
            "confidence": 0.70,
            "recommended_response": "Подсказать детальнее по ошибке или скинуть скриншот?",
            "requires_human": False,
            "extracted_phone": extracted_phone
        }

    async def classify(
        self,
        incoming_message: str,
        dialog_history: List[Dict[str, str]],
        db_session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Классифицирует входящее сообщение клиента по 12 сценариям поведения.
        """
        clean_incoming = incoming_message.strip()

        # Если DeepSeek не доступен — используем эвристический классификатор
        if not deepseek_client.is_configured():
            return self._heuristic_classify(clean_incoming)

        # Форматирование истории сообщений для контекста
        formatted_history = ""
        for m in dialog_history[-6:]:  # Последние 6 реплик
            role = "Мы" if m.get("sender") in ("bot", "manager") else "Клиент"
            formatted_history += f"{role}: {m.get('text', '')}\n"

        try:
            prompt_template = await get_prompt("CLASSIFIER", db_session) or DEFAULT_CLASSIFIER_PROMPT
            prompt = (
                prompt_template
                .replace("{dialog_history}", formatted_history or "Начало диалога")
                .replace("{incoming_message}", clean_incoming)
            )

            messages = [{"role": "user", "content": prompt}]
            data = await deepseek_client.generate_json(messages, temperature=0.1, max_tokens=250)

            # Валидация вывода
            intent = data.get("intent", "OTHER_CONVERSATION")
            confidence = float(data.get("confidence", 0.8))
            requires_human = bool(data.get("requires_human", False))

            # Если нейросеть распознала телефон или высокий интерес — гарантируем requires_human
            extracted_phone = data.get("extracted_phone")
            if not extracted_phone:
                phone_match = PHONE_REGEX.search(clean_incoming)
                if phone_match:
                    extracted_phone = phone_match.group(0)

            if intent == "INTERESTED" or extracted_phone:
                requires_human = True

            return {
                "intent": intent,
                "confidence": confidence,
                "recommended_response": data.get("recommended_response", ""),
                "requires_human": requires_human,
                "extracted_phone": extracted_phone
            }

        except Exception as e:
            logger.warning(f"Сбой нейро-классификатора ({e}). Используется эвристический fallback.")
            return self._heuristic_classify(clean_incoming)


intent_classifier = IntentClassifier()
