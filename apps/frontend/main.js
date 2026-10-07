/**
 * CASTLEWEB STUDIO — CORE LOGIC & INTERACTIONS
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Fullscreen Toggle
  const fsBtn = document.getElementById('fullscreen-toggle');
  if (fsBtn) {
    fsBtn.addEventListener('click', () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => {
          console.warn(`Error attempting to enable fullscreen: ${err.message}`);
        });
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen();
        }
      }
    });
  }

  // 2. Radio Options selection highlight
  const radioLabels = document.querySelectorAll('.radio-option');
  radioLabels.forEach(label => {
    const input = label.querySelector('input[type="radio"]');
    if (input) {
      input.addEventListener('change', () => {
        const name = input.getAttribute('name');
        document.querySelectorAll(`input[name="${name}"]`).forEach(sibling => {
          sibling.closest('.radio-option')?.classList.remove('selected');
        });
        if (input.checked) {
          label.classList.add('selected');
        }
      });
      if (input.checked) {
        label.classList.add('selected');
      }
    }
  });

  // 3. Case Details Modal logic
  const modalOverlay = document.getElementById('case-modal');
  const modalClose = document.getElementById('case-modal-close');
  const modalTitle = document.getElementById('modal-case-title');
  const modalDesc = document.getElementById('modal-case-desc');
  const modalImg = document.getElementById('modal-case-img');

  const caseData = {
    'mintina': {
      title: 'Mintina Jewellery',
      number: '[09]',
      desc: 'Разработать сайт для ювелирной студии ручной работы, который подчеркнет индивидуальный подход, передаст ценности бренда и выстроит доверие.',
      img: 'assets/post.png'
    },
    'gtl': {
      title: 'GlobalTrans Logistic',
      number: '[08]',
      desc: 'Цифровая трансформация международной логистической компании. Интуитивный расчет ставок, отслеживание грузов и строгий корпоративный стиль.',
      img: 'assets/case_cover-2.png'
    },
    'marina-mate': {
      title: 'Marina Mate',
      number: '[07]',
      desc: 'Премиальный консьерж-сервис путешествий. Эстетичный мобильный интерфейс, атмосферная типографика и захватывающий сторителлинг.',
      img: 'assets/case_cover-3.png'
    },
    'event-platform': {
      title: 'Event Platform',
      number: '[06]',
      desc: 'Платформа интерактивных офлайн-квестов и мероприятий с интеграцией планшетов и синхронизацией команд в реальном времени.',
      img: 'assets/post-2.png'
    },
    'quest-platform': {
      title: 'Quest Platform',
      number: '[05]',
      desc: 'Высоконагруженный сервис интерактивного вовлечения участников с геймификацией и моментальной аналитикой результатов.',
      img: 'assets/case_cover-4.png'
    },
    'sparkflair': {
      title: 'Sparkflair',
      number: '[04]',
      desc: 'Fashion e-commerce платформа для независимого бренда одежды. Минималистичный каталог, быстрая корзина и микроанимации.',
      img: 'assets/post.png'
    },
    'silushka': {
      title: 'Silushka',
      number: '[03]',
      desc: 'Производственный B2B-портал и оптовый каталог с автоматическим формированием спецификаций.',
      img: 'assets/Rectangle_329.png'
    },
    'evi-studio': {
      title: 'Evi Studio',
      number: '[02]',
      desc: 'Сайт-портфолио для архитектурного бюро с акцентом на полноэкранную фотосъемку интерьеров и архитектуры.',
      img: 'assets/case_cover-4.png'
    },
    'yah': {
      title: 'Yah Production',
      number: '[01]',
      desc: 'Сайт креативного видеопродакшна и рекламного агентства со стримингом шоурилов без задержек.',
      img: 'assets/Rectangle_329-2.png'
    }
  };

  document.querySelectorAll('[data-case-id]').forEach(trigger => {
    trigger.addEventListener('click', (e) => {
      const caseId = trigger.getAttribute('data-case-id');
      const item = caseData[caseId];
      if (item && modalOverlay) {
        e.preventDefault();
        if (modalTitle) modalTitle.textContent = `${item.number} ${item.title}`;
        if (modalDesc) modalDesc.textContent = item.desc;
        if (modalImg) modalImg.src = item.img;
        modalOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
      }
    });
  });

  if (modalClose && modalOverlay) {
    modalClose.addEventListener('click', () => {
      modalOverlay.classList.remove('active');
      document.body.style.overflow = '';
    });
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) {
        modalOverlay.classList.remove('active');
        document.body.style.overflow = '';
      }
    });
  }

  // 4. Fade out pinned brand title when footer screen is reached
  const brandBlock = document.getElementById('pinned-brand-block');
  const footerScreen = document.getElementById('links') || document.getElementById('contact');
  if (brandBlock && footerScreen) {
    const footerObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          brandBlock.classList.add('brand-hidden');
        } else {
          brandBlock.classList.remove('brand-hidden');
        }
      });
    }, { threshold: 0.15 });
    footerObserver.observe(footerScreen);
  }

  // 5. Brief Form Submission via Backend API (/api/v1/leads)
  const briefForm = document.getElementById('project-brief-form');
  if (briefForm) {
    briefForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitBtn = briefForm.querySelector('button[type="submit"]');
      const submitBtnText = submitBtn ? (submitBtn.querySelector('span') || submitBtn) : null;
      if (!submitBtn || !submitBtnText) return;

      const originalText = submitBtnText.textContent;

      const formData = new FormData(briefForm);
      const name = (formData.get('name') || '').toString().trim();
      const contact = (formData.get('contact') || '').toString().trim();
      const details = (formData.get('details') || '').toString().trim();
      const siteType = (formData.get('site_type') || '').toString();
      const timeline = (formData.get('timeline') || '').toString();
      const hpWebsite = (formData.get('hp_website') || '').toString().trim();

      const typeMap = {
        website: 'Веб-сайт',
        service: 'Веб-сервис / SaaS',
        parser: 'Парсер данных',
        telegram: 'Telegram-бот / мини-приложение',
        software: 'Кастомный софт',
        other: 'Другое'
      };

      const timelineMap = {
        now: 'Прямо сейчас',
        weeks: 'В течение 1-2 недель',
        month: 'Через месяц'
      };

      const taskParts = [
        `📋 Тип проекта: ${typeMap[siteType] || siteType}`,
        `⏱ Сроки: ${timelineMap[timeline] || timeline}`
      ];
      if (details) {
        taskParts.push(`📝 Детали: ${details}`);
      }
      const taskDescription = taskParts.join('\n');

      submitBtn.disabled = true;
      submitBtnText.textContent = 'ОТПРАВКА...';

      try {
        const res = await fetch('/api/v1/leads', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            name: name,
            contact: contact,
            task_description: taskDescription,
            budget: null,
            hp_website: hpWebsite || null
          })
        });

        if (!res.ok) {
          const errJson = await res.json().catch(() => ({}));
          throw new Error(errJson.detail || `HTTP ${res.status}`);
        }

        submitBtnText.textContent = '✓ ОТПРАВЛЕНО! СКОРО СВЯЖЕМСЯ';
        briefForm.reset();
        document.querySelectorAll('.radio-option').forEach(l => l.classList.remove('selected'));

        setTimeout(() => {
          submitBtnText.textContent = originalText;
          submitBtn.disabled = false;
        }, 5000);
      } catch (err) {
        console.error('Ошибка отправки заявки:', err);
        submitBtnText.textContent = 'ОШИБКА. НАПИШИТЕ В TG';
        setTimeout(() => {
          submitBtnText.textContent = originalText;
          submitBtn.disabled = false;
        }, 4000);
      }
    });
  }

  // 6. Scroll Reveal Observer for smooth entrance animations
  const revealElements = document.querySelectorAll('.reveal-item');
  if (revealElements.length > 0) {
    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          observer.unobserve(entry.target);
        }
      });
    }, {
      root: null,
      rootMargin: '0px 0px -6% 0px',
      threshold: 0.08
    });

    revealElements.forEach(el => revealObserver.observe(el));
  }
});
