// Калькулятор стоимости: тип проекта + опции → ориентир по бюджету и сроку.
// Цена крутится барабаном (одометром), список «Что входит» меняется под тип проекта.

const DIRECTION = {
  devops: 'Серверы и бэкенд',
  bot: 'Telegram-бот',
  site: 'Сайт или лендинг',
  service: 'Веб-сервис или SaaS',
};

const plural = (n, one, few, many) => {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
};

// Рабочие дни → «3–5 дней» или «2–3 недели»
export function formatTerm(lo, hi) {
  if (lo >= 10) {
    const wl = Math.round(lo / 5);
    const wh = Math.max(wl, Math.round(hi / 5));
    return wl === wh ? `${wl} ${plural(wl, 'неделя', 'недели', 'недель')}` : `${wl}–${wh} ${plural(wh, 'неделя', 'недели', 'недель')}`;
  }
  return `${lo}–${hi} ${plural(hi, 'день', 'дня', 'дней')}`;
}

const money = (n) => n.toLocaleString('ru-RU');
const DIGITS = '0123456789'.split('').map((d) => `<span>${d}</span>`).join('');

function renderOdometer(el, value) {
  const chars = [...money(value)];
  if (el.dataset.len !== String(chars.length)) {
    el.innerHTML = chars
      .map((c) => (/\d/.test(c) ? `<span class="odo__d"><span class="odo__col">${DIGITS}</span></span>` : '<span class="odo__sp"></span>'))
      .join('');
    el.dataset.len = String(chars.length);
    void el.offsetWidth;
  }
  const cols = el.querySelectorAll('.odo__col');
  let k = 0;
  chars.forEach((c) => {
    if (!/\d/.test(c)) return;
    cols[k].style.transitionDelay = `${k * 45}ms`;
    cols[k].style.transform = `translateY(${-Number(c) * 10}%)`;
    k++;
  });
}

export function initCalculator(form) {
  if (!form) return;
  const priceEl = form.querySelector('[data-calc-price]');
  const priceSr = form.querySelector('[data-calc-price-sr]');
  const daysEl = form.querySelector('[data-calc-days]');
  const descEl = form.querySelector('[data-calc-desc]');
  const incEl = form.querySelector('[data-calc-includes]');
  const cta = form.querySelector('[data-calc-cta]');
  let lastType = null;

  const read = () => {
    const type = form.querySelector('input[name="type"]:checked');
    let price = +type.dataset.price;
    let lo = +type.dataset.days;
    let hi = +type.dataset.daysMax;
    const opts = [];
    form.querySelectorAll('input[name="opt"]:checked').forEach((o) => {
      price += +o.dataset.price;
      lo += +o.dataset.days;
      hi += +o.dataset.days;
      opts.push(o.dataset.name);
    });
    return { type, price, lo, hi, opts };
  };

  const update = () => {
    const { type, price, lo, hi } = read();
    renderOdometer(priceEl, price);
    priceSr.textContent = `от ${money(price)} ₽`;
    daysEl.textContent = formatTerm(lo, hi);
    if (type !== lastType) {
      lastType = type;
      descEl.textContent = type.dataset.desc;
      incEl.innerHTML = type.dataset.includes.split('|').map((t) => `<li>${t}</li>`).join('');
    }
  };

  form.addEventListener('change', update);
  form.addEventListener('submit', (e) => e.preventDefault());

  // Переносим выбор в форму заявки
  cta.addEventListener('click', () => {
    const { type, price, lo, hi, opts } = read();
    const radio = document.querySelector(`.form input[name="direction"][value="${DIRECTION[type.value]}"]`);
    if (radio) radio.checked = true;
    const budget = document.querySelector('.form [data-budget]');
    if (budget) budget.value = `от ${money(price)} ₽, ${formatTerm(lo, hi)} (калькулятор)`;
    const task = document.querySelector('[data-task]');
    if (task && !task.value.trim()) {
      task.value = `${type.dataset.name}${opts.length ? `, опции: ${opts.join(', ')}` : ''}. Ориентир из калькулятора: от ${money(price)} ₽, ${formatTerm(lo, hi)}.\n`;
    }
  });

  update();
}
