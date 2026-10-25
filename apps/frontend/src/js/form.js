// Форма заявки → POST /api/v1/leads (FastAPI). Бэкенд сохраняет заявку в БД
// и отправляет её в Telegram-канал. Лимиты полей совпадают со схемой LeadCreate.

const ENDPOINT = '/api/v1/leads';
const FALLBACK = 'Напишите нам напрямую в Telegram: @kupidon996 или @Ya_emildjan.';

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

async function send(fields) {
  const res = await fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: fields.name,
      contact: fields.contact,
      task_description: `[Направление: ${fields.direction}]\n${fields.task}`,
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
      await send(fields);
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
