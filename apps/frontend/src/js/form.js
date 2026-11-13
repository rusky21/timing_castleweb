// Форма заявки → POST /api/v1/leads (FastAPI). Бэкенд сохраняет заявку в БД
// и отправляет её в Telegram-канал. Лимиты полей совпадают со схемой LeadCreate.
//
// Настройки через data-атрибуты формы:
//   data-tag="Площадка"      — подпись выбранного варианта в тексте заявки (по умолчанию «Направление»)
//   data-source="Чат-боты"   — с какой страницы пришла заявка (для лендингов)
//   data-thanks="/spasibo"   — куда перейти после отправки; без него показываем сообщение на месте
//   data-extra="Связь"       — на полях и вариантах выбора: их значение добавляется в текст заявки
import { reachGoal } from './analytics.js';

const ENDPOINT = '/api/v1/leads';
const FALLBACK = 'Напишите нам напрямую в Telegram: @kupidon996 или @Ya_emildjan.';
const TASK_MAX = 5000;

const LIMITS = {
  name: { min: 2, msg: 'Имя — минимум 2 символа.' },
  contact: { min: 3, msg: 'Контакт — минимум 3 символа.' },
  task: { min: 5, msg: 'Опишите задачу чуть подробнее, хотя бы в паре слов.' },
};

// FastAPI отдаёт detail строкой (наши ошибки) или массивом (ошибки валидации 422)
const errorText = (res, data) => {
  if (typeof data?.detail === 'string') return data.detail;
  if (res.status === 422) return 'Проверьте, правильно ли заполнены поля.';
  return `Сервер ответил ошибкой (${res.status}).`;
};

// Метки рекламной кампании из адреса страницы: по ним видно, какое объявление привело заявку
// Посетитель может уйти с лендинга на другие страницы и оставить заявку там, поэтому метки
// запоминаются до закрытия вкладки.
const AD_KEY = 'cw-ad';
function adMarks() {
  const marks = [];
  new URLSearchParams(location.search).forEach((value, key) => {
    if (/^utm_/.test(key) || key === 'yclid') marks.push(`${key}=${value}`);
  });
  const fresh = marks.join(', ').slice(0, 400);
  try {
    if (fresh) sessionStorage.setItem(AD_KEY, fresh);
    return fresh || sessionStorage.getItem(AD_KEY) || '';
  } catch {
    return fresh;
  }
}
adMarks();

function describe(form, fields) {
  const lines = [];
  if (form.dataset.source) lines.push(`[Страница: ${form.dataset.source}]`);
  if (fields.direction) lines.push(`[${form.dataset.tag || 'Направление'}: ${fields.direction}]`);
  // Дополнительные ответы формы: data-extra="Подпись" на поле или на вариантах выбора
  form.querySelectorAll('[data-extra]').forEach((el) => {
    const choice = el.type === 'radio' || el.type === 'checkbox';
    if ((choice && !el.checked) || !el.value.trim()) return;
    lines.push(`[${el.dataset.extra}: ${el.value.trim()}]`);
  });
  lines.push(fields.task);
  const marks = adMarks();
  if (marks) lines.push(`[Реклама: ${marks}]`);
  return lines.join('\n').slice(0, TASK_MAX);
}

async function send(form, fields) {
  const res = await fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: fields.name,
      contact: fields.contact,
      task_description: describe(form, fields),
      budget: fields.budget || null,
      hp_website: fields.hp || null,
    }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(errorText(res, data));
  }
}

export function initForm(form) {
  if (!form) return;
  const status = form.querySelector('[data-form-status]');
  const button = form.querySelector('[type="submit"]');
  const budget = form.querySelector('[data-budget]');
  const required = [...form.querySelectorAll('[required]')];
  let sending = false;

  const say = (text, state = '') => {
    status.textContent = text;
    if (state) status.dataset.state = state;
    else delete status.dataset.state;
  };

  required.forEach((el) => el.addEventListener(el.type === 'checkbox' ? 'change' : 'input', () => el.removeAttribute('aria-invalid')));

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (sending) return;
    const empty = required.filter((el) => (el.type === 'checkbox' ? !el.checked : !el.value.trim()));
    required.forEach((el) => {
      if (empty.includes(el)) el.setAttribute('aria-invalid', 'true');
      else el.removeAttribute('aria-invalid');
    });
    if (empty.length) {
      say(empty.some((el) => el.type === 'checkbox') && empty.length === 1
        ? 'Отметьте согласие на обработку персональных данных.'
        : 'Заполните, пожалуйста, все поля и отметьте согласие.', 'error');
      empty[0].focus();
      return;
    }

    const data = new FormData(form);
    const fields = {
      direction: data.get('direction'),
      name: data.get('name').trim(),
      task: data.get('task').trim(),
      contact: data.get('contact').trim(),
      budget: (data.get('budget') || '').trim(),
      hp: (data.get('website') || '').trim(),
    };

    const short = Object.keys(LIMITS).find((k) => fields[k].length < LIMITS[k].min);
    if (short) {
      const el = form.elements[short];
      el.setAttribute('aria-invalid', 'true');
      say(LIMITS[short].msg, 'error');
      el.focus();
      return;
    }

    sending = true;
    button.disabled = true;
    form.setAttribute('aria-busy', 'true');
    say('Отправляем заявку…');
    try {
      await send(form, fields);
      if (form.dataset.thanks) {
        // Цель «заявка» отправит страница «спасибо»: так она не теряется при переходе
        try { sessionStorage.setItem('cw-lead', form.dataset.source || 'Сайт'); } catch { /* без хранилища цель не отправится */ }
        location.assign(form.dataset.thanks);
        return;
      }
      reachGoal('lead', { page: 'Главная' });
      form.reset();
      if (budget) budget.value = '';
      say('Заявка у нас. Ответим лично в течение одного-двух часов.', 'ok');
    } catch (err) {
      const offline = err instanceof TypeError;
      say(`${offline ? 'Не получилось связаться с сервером.' : err.message} ${FALLBACK}`, 'error');
    } finally {
      sending = false;
      button.disabled = false;
      form.removeAttribute('aria-busy');
    }
  });
}
