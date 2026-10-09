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
  const modalTabs = document.getElementById('modal-case-tabs');
  const modalGallery = document.getElementById('modal-case-gallery');

  const caseData = {
    'mintina': {
      title: 'Mintina Jewellery',
      number: '[09]',
      desc: 'Разработать сайт для ювелирной студии ручной работы, который подчеркнет индивидуальный подход, передаст ценности бренда и выстроит доверие.',
      img: 'assets/post.png'
    },
    'onyx-os': {
      title: 'Onyx OS — Шелл для ПК-клуба',
      number: '[01]',
      desc: '', // Без текста по запросу
      img: 'assets/onyx-launcher.jpg',
      images: [
        {
          src: 'assets/onyx-launcher.jpg',
          title: 'Игровой лаунчер ПК-клуба',
          tag: 'Onyx OS',
          aspect: '16:9'
        },
        {
          src: 'assets/onyx-racing.png',
          title: 'Сим-рейсинг Huracán GT3',
          tag: 'Onyx Racing Center',
          aspect: '16:9'
        },
        {
          src: 'assets/onyx-settings.png',
          title: 'Параметры системы и звук',
          tag: 'Аппаратная конфигурация',
          aspect: '16:9'
        }
      ]
    },
    'gtl': {
      title: 'Onyx OS — Шелл для ПК-клуба',
      number: '[01]',
      desc: '',
      img: 'assets/onyx-launcher.jpg',
      images: [
        {
          src: 'assets/onyx-launcher.jpg',
          title: 'Игровой лаунчер ПК-клуба',
          tag: 'Onyx OS',
          aspect: '16:9'
        },
        {
          src: 'assets/onyx-racing.png',
          title: 'Сим-рейсинг Huracán GT3',
          tag: 'Onyx Racing Center',
          aspect: '16:9'
        },
        {
          src: 'assets/onyx-settings.png',
          title: 'Параметры системы и звук',
          tag: 'Аппаратная конфигурация',
          aspect: '16:9'
        }
      ]
    },
    'onyx-racing': {
      title: 'Onyx OS — Шелл для ПК-клуба',
      number: '[01]',
      desc: '',
      img: 'assets/onyx-racing.png',
      images: [
        {
          src: 'assets/onyx-launcher.jpg',
          title: 'Игровой лаунчер ПК-клуба',
          tag: 'Onyx OS',
          aspect: '16:9'
        },
        {
          src: 'assets/onyx-racing.png',
          title: 'Сим-рейсинг Huracán GT3',
          tag: 'Onyx Racing Center',
          aspect: '16:9'
        },
        {
          src: 'assets/onyx-settings.png',
          title: 'Параметры системы и звук',
          tag: 'Аппаратная конфигурация',
          aspect: '16:9'
        }
      ]
    },
    'marina-mate': {
      title: 'Marina Mate',
      number: '[07]',
      desc: 'Премиальный консьерж-сервис путешествий. Эстетичный мобильный интерфейс, атмосферная типографика и захватывающий сторителлинг.',
      img: 'assets/case_cover-3.png'
    },
    'event-platform': {
      title: 'Skog Chalet & Hytte Control',
      number: '[02]',
      desc: '', // Текста не пишем по запросу пользователя
      img: 'assets/post-2.png',
      images: [
        {
          src: 'assets/post-2.png',
          title: 'Личный кабинет гостя',
          tag: 'Мобильный интерфейс'
        },
        {
          src: 'assets/post-2-bonuses.png',
          title: 'Финансы и бонусы',
          tag: 'Программа лояльности'
        },
        {
          src: 'assets/post-2-dashboard.png',
          title: 'Hytte Control — Сводка и бронирования',
          tag: 'Панель управления'
        }
      ]
    },
    'leadhunter': {
      title: 'LeadHunter — Парсер Яндекс.Карт',
      number: '[03]',
      desc: 'Автономный сервис парсинга организаций из Яндекс.Карт. Автоматический сбор базы компаний по выбранным городам и нишам: прямые телефоны, сайты, адреса и Telegram-контакты. Доступна тестовая демо-версия через Telegram-бота студии.',
      demoUrl: 'https://t.me/castleweb_bot?start=demo',
      img: 'assets/leadhunter-dashboard.png',
      images: [
        {
          src: 'assets/leadhunter-dashboard.png',
          title: 'База собранных организаций из Яндекс.Карт',
          tag: 'Яндекс.Карты',
          aspect: '16:9'
        },
        {
          src: 'assets/leadhunter-search.png',
          title: 'Параметры сбора: город и ниша бизнеса',
          tag: 'Поиск Яндекс.Карт',
          aspect: '16:9'
        }
      ]
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

  function createImageCard(imgObj, isDesktop = false) {
    const card = document.createElement('div');
    card.className = `case-gallery-card ${isDesktop ? 'case-gallery-desktop-card' : ''}`;

    const header = document.createElement('div');
    header.className = 'case-gallery-card-header';
    header.innerHTML = `
      <span class="case-gallery-card-title">${imgObj.title || 'Экран'}</span>
      <span class="case-gallery-card-tag">${imgObj.tag || 'Castleweb Studio'}</span>
    `;

    const imgWrapper = document.createElement('div');
    imgWrapper.className = 'case-gallery-img-wrapper';

    const img = document.createElement('img');
    img.className = 'case-gallery-img';
    img.src = imgObj.src;
    img.alt = imgObj.title || 'Screen';
    img.loading = 'lazy';

    imgWrapper.appendChild(img);
    card.appendChild(header);
    card.appendChild(imgWrapper);
    return card;
  }

  function renderGallery(images, activeFilter) {
    if (!modalGallery) return;
    modalGallery.innerHTML = '';

    if (activeFilter === 'all') {
      const mobileScreens = images.filter(img => img.aspect === '4:5' || (!img.aspect && !img.src.includes('dashboard') && !img.src.includes('onyx')));
      const desktopScreens = images.filter(img => img.aspect === '16:9' || img.src.includes('dashboard') || img.src.includes('onyx'));

      if (mobileScreens.length > 0) {
        const grid = document.createElement('div');
        grid.className = 'case-gallery-mobile-grid';
        mobileScreens.forEach(imgObj => {
          grid.appendChild(createImageCard(imgObj, false));
        });
        modalGallery.appendChild(grid);
      }

      desktopScreens.forEach(imgObj => {
        modalGallery.appendChild(createImageCard(imgObj, true));
      });
    } else {
      const targetImg = images[activeFilter];
      if (targetImg) {
        const isDesktop = targetImg.aspect === '16:9' || targetImg.src.includes('dashboard') || targetImg.src.includes('onyx');
        modalGallery.appendChild(createImageCard(targetImg, isDesktop));
      }
    }
  }

  function openCase(item) {
    if (!item || !modalOverlay) return;

    if (modalTitle) {
      modalTitle.textContent = `${item.number} ${item.title}`;
    }

    if (modalDesc) {
      if (item.desc && item.desc.trim().length > 0) {
        modalDesc.textContent = item.desc;
        modalDesc.style.display = 'block';
      } else {
        modalDesc.textContent = '';
        modalDesc.style.display = 'none';
      }
    }

    if (modalGallery) {
      modalGallery.innerHTML = '';

      if (item.images && item.images.length > 1) {
        if (modalTabs) {
          modalTabs.innerHTML = '';
          modalTabs.style.display = 'flex';

          const allBtn = document.createElement('button');
          allBtn.className = 'case-modal-tab-btn active';
          allBtn.type = 'button';
          allBtn.textContent = `Все экраны (${item.images.length})`;
          modalTabs.appendChild(allBtn);

          item.images.forEach((imgObj, idx) => {
            const tabBtn = document.createElement('button');
            tabBtn.className = 'case-modal-tab-btn';
            tabBtn.type = 'button';
            tabBtn.textContent = `0${idx + 1}. ${imgObj.title || 'Экран'}`;
            modalTabs.appendChild(tabBtn);

            tabBtn.addEventListener('click', () => {
              modalTabs.querySelectorAll('.case-modal-tab-btn').forEach(b => b.classList.remove('active'));
              tabBtn.classList.add('active');
              renderGallery(item.images, idx);
            });
          });

          allBtn.addEventListener('click', () => {
            modalTabs.querySelectorAll('.case-modal-tab-btn').forEach(b => b.classList.remove('active'));
            allBtn.classList.add('active');
            renderGallery(item.images, 'all');
          });
        }

        renderGallery(item.images, 'all');
      } else {
        if (modalTabs) {
          modalTabs.style.display = 'none';
          modalTabs.innerHTML = '';
        }
        const singleImg = document.createElement('img');
        singleImg.className = 'case-modal-single-img';
        singleImg.src = item.img || (item.images && item.images[0]?.src) || '';
        singleImg.alt = item.title || 'Кейс';
        modalGallery.appendChild(singleImg);
      }
    }

    const demoBtn = document.getElementById('modal-demo-btn');
    if (demoBtn) {
      if (item.demoUrl) {
        demoBtn.style.display = 'inline-flex';
        demoBtn.href = item.demoUrl;
      } else {
        demoBtn.style.display = 'none';
      }
    }

    modalOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  // Динамически получаем актуальный юзернейм бота студии для демо-ссылки
  fetch('/api/v1/telegram/bot-info')
    .then(r => r.json())
    .then(data => {
      if (data && data.username) {
        if (caseData['leadhunter']) {
          caseData['leadhunter'].demoUrl = `https://t.me/${data.username}?start=demo`;
        }
      }
    })
    .catch(() => {});

  document.querySelectorAll('[data-case-id]').forEach(trigger => {
    trigger.addEventListener('click', (e) => {
      const caseId = trigger.getAttribute('data-case-id');
      const item = caseData[caseId];
      if (item) {
        e.preventDefault();
        openCase(item);
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

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modalOverlay && modalOverlay.classList.contains('active')) {
      modalOverlay.classList.remove('active');
      document.body.style.overflow = '';
    }
  });

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
