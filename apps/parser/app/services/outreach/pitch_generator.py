import logging
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.deepseek.client import deepseek_client
from app.services.outreach.prompts import get_prompt, DEFAULT_PITCH_PROMPT

logger = logging.getLogger("pitch_generator")


class PitchGenerator:
    """
    Генератор персонализированных первых сообщений (питчей) для холодного контакта в Telegram.
    Использует DeepSeek API с предохранителем (Circuit Breaker) на детерминированные шаблоны.
    """

    @staticmethod
    def _fallback_pitch(
        company_name: str,
        audit_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Отказоустойчивый резервный шаблон на случай недоступности нейросети.
        Не содержит ссылок и шаблонных спам-клише.
        """
        audit = audit_data or {}
        issue_type = audit.get("status_badge", "")
        is_adaptive = audit.get("is_adaptive", True)
        has_ssl = audit.get("has_ssl", True)

        if not has_ssl or issue_type == "NO_SSL":
            issue_summary = "Предупреждение безопасности и отсутствие SSL на мобильных"
            pitch_text = (
                f"Добрый день! Пытался открыть ваш сайт с телефона, но браузер выдает "
                f"красное предупреждение «Не защищено». Многие клиенты сразу закрывают страницу "
                f"из-за этого. Подсказать детальнее или скинуть скриншот ошибки?"
            )
        elif not is_adaptive or issue_type == "NOT_RESPONSIVE":
            issue_summary = "Элементы верстки и кнопка заявки съезжают на экранах смартфонов"
            pitch_text = (
                f"Добрый день! Зашел к вам на сайт со смартфона, заметил что верстка "
                f"кнопки заявки съезжает вбок и перекрывается меню, нажать сложно. "
                f"Сайтом сейчас кто-то занимается, или скинуть скриншот ошибки?"
            )
        else:
            issue_summary = "Кнопка быстрой связи перекрывается и не нажимается со смартфона"
            pitch_text = (
                f"Добрый день! Зашел к вам на сайт с телефона, заметил что форма заявки "
                f"в мобильной версии сдвинута и не отправляется при первом нажатии. "
                f"Сайтом сейчас кто-то занимается, или прислать скриншот ошибки?"
            )

        return pitch_text, issue_summary

    async def generate(
        self,
        company_name: str,
        city: str,
        website_url: str,
        audit_data: Optional[Dict[str, Any]] = None,
        db_session: Optional[AsyncSession] = None
    ) -> Tuple[str, str]:
        """
        Генерирует первое персонализированное сообщение.
        Возвращает кортеж: (текст_питча, краткое_описание_бага).
        """
        clean_company = (company_name or "компании").strip()
        clean_city = (city or "").strip()
        clean_url = (website_url or "").strip()

        audit = audit_data or {}
        issue_desc = audit.get("pitch_pain") or audit.get("status_badge") or "Кнопка связи не срабатывает"
        symptom = audit.get("pitch_solution") or "Сдвиг верстки на мобильном экране до 390px"

        # Если DeepSeek не настроен — сразу используем проверенный детерминированный шаблон
        if not deepseek_client.is_configured():
            logger.info("DeepSeek не сконфигурирован. Применяется отказоустойчивый шаблон CastleWeb.")
            return self._fallback_pitch(clean_company, audit)

        try:
            prompt_template = await get_prompt("PITCH", db_session) or DEFAULT_PITCH_PROMPT
            prompt = prompt_template
            for ph, val in (
                ("{company_name}", clean_company),
                ("{city}", clean_city),
                ("{website_url}", clean_url),
                ("{audit_issue_description}", issue_desc),
                ("{audit_symptom}", symptom),
            ):
                prompt = prompt.replace(ph, str(val))

            messages = [
                {"role": "user", "content": prompt}
            ]

            data = await deepseek_client.generate_json(messages, temperature=0.4, max_tokens=300)
            pitch_text = data.get("pitch_text", "").strip()
            issue_summary = data.get("issue_summary", "").strip() or issue_desc

            # Санитарная проверка ответа нейросети: удаление возможных случайных ссылок
            for proto in ("http://", "https://", "t.me/", "www."):
                if proto in pitch_text:
                    logger.warning(f"Питч содержал запрещенную ссылку ({proto}). Выполнен откат к шаблону.")
                    return self._fallback_pitch(clean_company, audit)

            if len(pitch_text.split()) < 10:
                logger.warning("Сгенерированный питч слишком короткий. Выполнен откат.")
                return self._fallback_pitch(clean_company, audit)

            logger.info(f"✨ Сгенерирован персонализированный питч для {clean_company} ({len(pitch_text)} симв.)")
            return pitch_text, issue_summary

        except Exception as e:
            logger.warning(f"Сбой генерации питча через DeepSeek ({e}). Применяется Circuit Breaker fallback.")
            return self._fallback_pitch(clean_company, audit)


pitch_generator = PitchGenerator()
