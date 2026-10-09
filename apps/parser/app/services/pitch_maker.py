import datetime
from typing import Dict, Any, Tuple

class PitchMaker:
    """Движок генерации офферов, скриптов продаж и расчета LeadScore"""

    @classmethod
    def calculate_score_and_pitch(
        cls,
        name: str,
        category: str,
        city: str,
        website: str,
        status: str,
        has_ssl: bool,
        is_adaptive: bool,
        has_analytics: bool,
        detected_cms: str,
        last_updated_year: int
    ) -> Tuple[int, str, Dict[str, str]]:
        """
        Возвращает:
        (lead_score, status_badge, pitch_dict)
        где pitch_dict содержит: pain, solution, opening_phrase, full_text
        """
        current_year = datetime.datetime.now().year
        category_clean = category if category else "бизнес"
        city_clean = f"в г. {city}" if city else ""

        # Кейс 1: Сайта нет совсем
        if status in ("NO_SITE", "SITE_DOWN"):
            score = 95 if status == "NO_SITE" else 90
            badge = "NO_WEBSITE" if status == "NO_SITE" else "SITE_DOWN"
            
            pain = (
                f"У компании «{name}» отсутствует рабочий сайт. Все клиенты, которые ищут {category_clean} "
                f"на картах или в поиске, сразу уходят к конкурентам с готовым онлайн-заказом и ценами."
            )
            solution = (
                "Разработка конверсионного лендинга или квиз-сайта с каталогом услуг, "
                "онлайн-записью и подключением Яндекс.Метрики за 3–5 дней."
            )
            opening = (
                f"«Здравствуйте! Нашел вашу организацию «{name}» на картах {city_clean}. "
                f"Обратил внимание, что у вас не указан сайт — клиенты не могут посмотреть прайс и услуги, "
                f"из-за чего вы теряете до половины горячих заявок. Мы как раз разрабатываем быстрые сайты под ключ для сферы {category_clean}...»"
            )
            full_text = f"БОЛЬ: {pain}\n\nРЕШЕНИЕ: {solution}\n\nСКРИПТ ЗВОНКА:\n{opening}"
            return score, badge, {
                "pain": pain,
                "solution": solution,
                "opening_phrase": opening,
                "full_text": full_text
            }

        # Кейс 2: Только соцсеть (VK, Telegram, Taplink)
        if status == "ONLY_SOCIAL":
            score = 85
            badge = "NO_WEBSITE"
            pain = (
                f"Вместо собственного сайта используется страница в соцсети. "
                "Теряется бесплатный поисковый SEO-трафик Яндекс и Google, невозможно настроить сквозную аналитику рекламы."
            )
            solution = (
                "Создание полноценного автономного сайта компании, который будет привлекать клиентов из поиска "
                "и собирать заявки 24/7 без риска блокировки соцсетей."
            )
            opening = (
                f"«Здравствуйте! Увидел вашу компанию «{name}» на картах. "
                f"Заметил, что вместо сайта у вас стоит ссылка на соцсеть. Из-за этого вы недополучаете клиентов из поиска Яндекс. "
                f"Подскажите, с кем можно обсудить запуск простого сайта для увеличения заказов?»"
            )
            full_text = f"БОЛЬ: {pain}\n\nРЕШЕНИЕ: {solution}\n\nСКРИПТ ЗВОНКА:\n{opening}"
            return score, badge, {
                "pain": pain,
                "solution": solution,
                "opening_phrase": opening,
                "full_text": full_text
            }

        # Кейс 3: Сайт есть, анализируем дефекты
        score = 20  # Базовый скор
        pains = []
        solutions = []
        primary_badge = "HTTPS_OK"

        if not has_ssl:
            score += 35
            primary_badge = "NO_SSL"
            pains.append("Браузеры помечают сайт как «Опасный» из-за отсутствия SSL-сертификата (HTTPS), отпугивая до 60% посетителей.")
            solutions.append("Установка и настройка бесплатного бессрочного SSL-сертификата Let's Encrypt и настройка редиректа на HTTPS.")

        if not is_adaptive:
            score += 30
            if primary_badge == "HTTPS_OK":
                primary_badge = "NOT_RESPONSIVE"
            pains.append("Сайт не оптимизирован под смартфоны — текст и кнопки мелкие, формы не нажимаются, мобильный трафик сливается впустую.")
            solutions.append("Адаптация верстки под мобильные экраны или редизайн на современный адаптивный движок.")

        if not has_analytics:
            score += 20
            if primary_badge == "HTTPS_OK":
                primary_badge = "NO_ANALYTICS"
            pains.append("Не установлена система аналитики (Яндекс.Метрика / Google Analytics). Непонятно, откуда приходят клиенты и окупается ли реклама.")
            solutions.append("Установка Яндекс.Метрики, настройка целей на звонки и отправку заявок с сайта.")

        if last_updated_year and last_updated_year < (current_year - 2):
            score += 15
            pains.append(f"Сайт визуально заброшен (копирайт {last_updated_year} года). Создается впечатление, что компания закрылась.")
            solutions.append("Актуализация информации, редизайн шапки и подвала.")

        # Ограничиваем скор до 100
        score = min(score, 100)

        if not pains:
            pain = "Критических технических ошибок на главной странице не обнаружено."
            solution = "Предложить аудит конверсии, контекстную рекламу или продвижение на картах."
            opening = (
                f"«Здравствуйте! Меня зовут ... Нашел «{name}» на картах. Изучил ваш сайт {website} — "
                f"выглядит аккуратно. Мы специализируемся на привлечении новых клиентов для ниши {category_clean} {city_clean}. "
                f"Подскажите, открыты ли к увеличению потока заявок?»"
            )
        else:
            pain = " ".join(pains)
            solution = " ".join(solutions)
            # Формируем персонализированную первую фразу
            lead_problem = ""
            if not has_ssl:
                lead_problem = f"при переходе на ваш сайт {website} браузер пишет «Подключение не защищено» и пугает посетителей красным экраном"
            elif not is_adaptive:
                lead_problem = f"ваш сайт {website} открывается со смартфонов в десктопном мелком виде, посетителям неудобно звонить"
            elif not has_analytics:
                lead_problem = f"на вашем сайте {website} не установлена Яндекс.Метрика, сложно отслеживать заявки с карт"
            else:
                lead_problem = f"информация на вашем сайте {website} давно не обновлялась"

            opening = (
                f"«Здравствуйте! Меня зовут ... Звоню по поводу вашей компании «{name}» на картах {city_clean}. "
                f"Обратил внимание, что {lead_problem}. Из-за этого вы прямо сейчас теряете потенциальных клиентов. "
                f"Мы можем быстро это устранить за 1–2 дня. С кем у вас можно переговорить по технической части?»"
            )

        full_text = f"БОЛЬ: {pain}\n\nРЕШЕНИЕ: {solution}\n\nСКРИПТ ЗВОНКА:\n{opening}"

        return score, primary_badge, {
            "pain": pain,
            "solution": solution,
            "opening_phrase": opening,
            "full_text": full_text
        }
