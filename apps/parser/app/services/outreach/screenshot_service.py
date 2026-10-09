import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright

from app.config import SCREENSHOTS_DIR, HEADLESS

logger = logging.getLogger("screenshot_service")


class ScreenshotService:
    """
    Микросервис захвата доказательств (пруфов) дефектов мобильной верстки через Playwright.
    Эмулирует экран iPhone 13 (390x844) и подсвечивает проблемную область красным маркером.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or SCREENSHOTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def capture_mobile_defect(
        self,
        url: str,
        defect_selector: Optional[str] = None,
        highlight_box: bool = True,
        timeout_ms: int = 25000
    ) -> Optional[str]:
        """
        Открывает страницу в мобильном вьюпорте iPhone 13,
        находит проблемный узел или форму, при необходимости обводит красной рамкой
        и сохраняет легкий оптимизированный JPEG для Telegram.
        """
        if not url:
            return None

        # Нормализация URL
        target_url = url.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = f"https://{target_url}"

        # Детерминированное имя файла на основе URL и селектора
        hash_key = hashlib.md5(f"{target_url}_{defect_selector or ''}".encode()).hexdigest()[:12]
        file_path = self.output_dir / f"proof_{hash_key}.jpg"

        # Если свежий скриншот уже существует — возвращаем его
        if file_path.exists() and file_path.stat().st_size > 1024:
            return str(file_path.resolve())

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=HEADLESS,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
                context = await browser.new_context(
                    viewport={"width": 390, "height": 844},  # iPhone 13/14
                    user_agent=(
                        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
                    ),
                    device_scale_factor=2,
                    is_mobile=True,
                    has_touch=True,
                    ignore_https_errors=True
                )
                page = await context.new_page()

                try:
                    # Переход с мягким ожиданием
                    try:
                        await page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
                        # Дополнительное ожидание сетевого затишья до 3 сек
                        try:
                            await page.wait_for_load_state("networkidle", timeout=3000)
                        except Exception:
                            pass
                    except Exception as nav_err:
                        logger.warning(f"Навигация на {target_url} завершилась с предупреждением: {nav_err}")

                    # Поиск и подсветка проблемной зоны
                    selector_to_highlight = defect_selector
                    if not selector_to_highlight:
                        # Попытка обнаружить интерактивные элементы формы/заявки/кнопки
                        common_selectors = [
                            "form button[type='submit']",
                            "button.order-btn",
                            "button.callback-btn",
                            ".popup-form",
                            "form",
                            "header",
                            ".navbar",
                            "a[href^='tel:']"
                        ]
                        for cand in common_selectors:
                            try:
                                el = await page.query_selector(cand)
                                if el and await el.is_visible():
                                    selector_to_highlight = cand
                                    break
                            except Exception:
                                continue

                    if selector_to_highlight and highlight_box:
                        try:
                            await page.evaluate(f"""() => {{
                                const el = document.querySelector("{selector_to_highlight}");
                                if (el) {{
                                    el.style.outline = '4px solid #FF0055';
                                    el.style.outlineOffset = '2px';
                                    el.style.boxShadow = '0 0 20px rgba(255, 0, 85, 0.8)';
                                    el.scrollIntoView({{behavior: 'instant', block: 'center'}});
                                }}
                            }}""")
                        except Exception as eval_err:
                            logger.debug(f"Не удалось подсветить селектор {selector_to_highlight}: {eval_err}")

                    # Даем отрисоваться анимациям и эффекту подсветки
                    await asyncio.sleep(1.2)

                    # Скриншот видимой области экрана телефона
                    await page.screenshot(
                        path=str(file_path),
                        type="jpeg",
                        quality=85,
                        full_page=False
                    )
                    logger.info(f"📸 Скриншот дефекта успешно сохранен: {file_path}")
                    return str(file_path.resolve())

                finally:
                    await browser.close()

        except Exception as e:
            logger.error(f"Ошибка при захвате скриншота для {target_url}: {e}")
            return None


screenshot_service = ScreenshotService()
