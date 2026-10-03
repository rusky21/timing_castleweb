import React, { useState, useRef, useEffect } from 'react';
import './FinalCta.css';

interface StepItem {
  id: number;
  line1: string;
  line2: string;
}

const STEPS: StepItem[] = [
  { id: 1, line1: 'Заполните бриф', line2: 'о проекте' },
  { id: 2, line1: 'Обсудим концепт', line2: 'и оценку' },
  { id: 3, line1: 'Запустим разработку', line2: 'в срок' },
];

type MessengerType = 'Telegram' | 'WhatsApp' | 'Instagram';

export const FinalCta: React.FC = () => {
  const [activeStep, setActiveStep] = useState<number>(1);
  const [name, setName] = useState('');
  const [contact, setContact] = useState('');
  const [email, setEmail] = useState('');
  const [messenger, setMessenger] = useState<MessengerType>('Telegram');
  const [isMessengerOpen, setIsMessengerOpen] = useState(false);
  const [description, setDescription] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [hpWebsite, setHpWebsite] = useState('');
  const [botUsername, setBotUsername] = useState('castleweb_bot');

  const messengerDropdownRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch Telegram bot info for direct link
  useEffect(() => {
    let isMounted = true;
    fetch('/api/v1/telegram/bot-info')
      .then((res) => res.json())
      .then((data) => {
        if (data.ok && data.username && isMounted) {
          setBotUsername(data.username);
        }
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, []);

  // Close messenger dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        messengerDropdownRef.current &&
        !messengerDropdownRef.current.contains(event.target as Node)
      ) {
        setIsMessengerOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.size > 25 * 1024 * 1024) {
        setSubmitError('Размер файла превышает лимит 25 МБ.');
        return;
      }
      setSubmitError(null);
      setFile(selectedFile);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.size > 25 * 1024 * 1024) {
        setSubmitError('Размер файла превышает лимит 25 МБ.');
        return;
      }
      setSubmitError(null);
      setFile(droppedFile);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const removeFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const resetForm = () => {
    setIsSubmitted(false);
    setName('');
    setContact('');
    setEmail('');
    setDescription('');
    setFile(null);
    setSubmitError(null);
    setHpWebsite('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    if (!name.trim() || name.trim().length < 2) {
      setSubmitError('Пожалуйста, укажите ваше имя (минимум 2 символа).');
      return;
    }
    if (!contact.trim() || contact.trim().length < 3) {
      setSubmitError('Укажите контакт для связи (@username в Telegram, WhatsApp или телефон).');
      return;
    }
    if (!description.trim() || description.trim().length < 5) {
      setSubmitError('Пожалуйста, опишите задачу или задумку проекта (минимум 5 символов).');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      let attachmentUrl: string | null = null;

      // 1. Загрузка файла при наличии
      if (file) {
        const fileData = new FormData();
        fileData.append('file', file);

        const uploadRes = await fetch('/api/v1/uploads/file', {
          method: 'POST',
          body: fileData,
        });

        if (!uploadRes.ok) {
          const errData = await uploadRes.json().catch(() => ({}));
          throw new Error(errData.detail || 'Не удалось прикрепить файл. Попробуйте еще раз.');
        }

        const uploadJson = await uploadRes.json();
        attachmentUrl = uploadJson.url || uploadJson.public_url || null;
      }

      // 2. Формирование структурированного контакта
      const contactDetail = `${messenger}: ${contact.trim()}${email.trim() ? ` (Email: ${email.trim()})` : ''}`;

      const payload = {
        name: name.trim(),
        contact: contactDetail,
        task_description: description.trim(),
        budget: null,
        attachment_url: attachmentUrl,
        hp_website: hpWebsite.trim() || null,
        turnstile_token: null,
      };

      // 3. Отправка в FastAPI бэкенд
      const res = await fetch('/api/v1/leads', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        if (res.status === 429) {
          throw new Error('Слишком много запросов. Пожалуйста, подождите пару минут перед повторной отправкой.');
        }
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Не удалось отправить заявку. Попробуйте снова или напишите в Telegram.');
      }

      setIsSubmitted(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Сетевая ошибка при отправке заявки.';
      setSubmitError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="final-cta-section" id="contact">
      {/* --- Left Column (55vw): Emerald Canvas with sharp corners --- */}
      <div className="signup-emerald-screen">
        <div className="emerald-glow-ambient" aria-hidden="true" />
        <div className="emerald-glow-core" aria-hidden="true" />

        {/* Top spacious atmosphere */}
        <div className="emerald-top-spacer" aria-hidden="true" />

        {/* Lower content zone */}
        <div className="emerald-lower-content reveal-void">
          <div className="emerald-title-row">
            <h2 className="emerald-main-heading">
              Get Started
              <br />
              with Us
            </h2>
            <p className="emerald-step-hint">
              Сделайте первый шаг
              <br />к запуску вашего проекта.
            </p>
          </div>

          {/* 3 Step Cards */}
          <div className="emerald-steps-row reveal-void delay-150" role="tablist" aria-label="Этапы работы">
            {STEPS.map((step) => {
              const isActive = step.id === activeStep;
              return (
                <div
                  key={step.id}
                  className={`step-tile-card ${isActive ? 'is-active' : ''}`}
                  onClick={() => setActiveStep(step.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      setActiveStep(step.id);
                    }
                  }}
                  aria-label={`Шаг ${step.id}: ${step.line1} ${step.line2}`}
                >
                  <div className="step-num-circle">{step.id}</div>
                  <div className="step-label-lines">
                    <span>{step.line1}</span>
                    <span>{step.line2}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* --- Right Column (45vw): Application Request Form --- */}
      <div className="signup-form-screen">
        <div className="signup-form-inner">
          {/* Header */}
          <div className="form-header-group reveal-void">
            <h3 className="form-title-text">Оставить заявку</h3>
            <p className="form-subtitle-text">
              Заполните данные для начала работы над вашим проектом.
            </p>
          </div>

          {isSubmitted ? (
            <div className="form-success-card reveal-void">
              <div className="success-icon-badge" aria-hidden="true">✓</div>
              <h4 className="success-card-title">Заявка успешно принята!</h4>
              <p className="success-card-text">
                Спасибо, {name || 'партнер'}! Мы уже получили вашу задачу и свяжемся с вами в течение 15 минут в {messenger}.
              </p>
              {botUsername && (
                <a
                  href={`https://t.me/${botUsername}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="success-telegram-link"
                >
                  Перейти в наш Telegram-бот (@{botUsername}) →
                </a>
              )}
              <button
                type="button"
                className="submit-white-action-btn"
                style={{ marginTop: '24px', width: 'auto', minWidth: '220px' }}
                onClick={resetForm}
              >
                Отправить еще одну заявку
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="form-fields-stack reveal-void delay-150">
              {/* Invisible Honeypot Anti-Spam */}
              <input
                type="text"
                name="hp_website"
                value={hpWebsite}
                onChange={(e) => setHpWebsite(e.target.value)}
                style={{ display: 'none' }}
                tabIndex={-1}
                autoComplete="off"
                aria-hidden="true"
              />
            {/* 1. Имя & 2. Контакт */}
            <div className="fields-row-2col">
              <div className="form-input-field">
                <label htmlFor="clientName" className="input-field-label">
                  Имя
                </label>
                <input
                  id="clientName"
                  type="text"
                  className="input-box-control"
                  placeholder="Константин*"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>

              <div className="form-input-field">
                <label htmlFor="clientContact" className="input-field-label">
                  Контакт
                </label>
                <input
                  id="clientContact"
                  type="text"
                  className="input-box-control"
                  placeholder="@username*"
                  value={contact}
                  onChange={(e) => setContact(e.target.value)}
                  required
                />
              </div>
            </div>

            {/* 3. Почта & 4. Как вам ответить? * */}
            <div className="fields-row-2col">
              <div className="form-input-field">
                <label htmlFor="clientEmail" className="input-field-label">
                  Почта
                </label>
                <input
                  id="clientEmail"
                  type="email"
                  className="input-box-control"
                  placeholder="mail@bk.ru"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              {/* Plashka with messenger options */}
              <div className="form-input-field messenger-select-container" ref={messengerDropdownRef}>
                <label className="input-field-label" id="messenger-label">
                  Как вам ответить? *
                </label>
                <div
                  className={`messenger-picker-button ${isMessengerOpen ? 'is-open' : ''}`}
                  onClick={() => setIsMessengerOpen(!isMessengerOpen)}
                  role="button"
                  tabIndex={0}
                  aria-haspopup="listbox"
                  aria-expanded={isMessengerOpen}
                  aria-labelledby="messenger-label"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      setIsMessengerOpen(!isMessengerOpen);
                    }
                  }}
                >
                  <div className="messenger-selected-display">
                    {messenger === 'Telegram' && (
                      <svg className="messenger-icon" viewBox="0 0 24 24" width="18" height="18" fill="none">
                        <path
                          d="M21.5 3.5L2 11.5L9.5 14.5L18 8L11.5 16L18.5 21L21.5 3.5Z"
                          stroke="#2AABEE"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    )}
                    {messenger === 'WhatsApp' && (
                      <svg className="messenger-icon" viewBox="0 0 24 24" width="18" height="18" fill="none">
                        <path
                          d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
                          stroke="#25D366"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    )}
                    {messenger === 'Instagram' && (
                      <svg className="messenger-icon" viewBox="0 0 24 24" width="18" height="18" fill="none">
                        <rect x="2" y="2" width="20" height="20" rx="5" stroke="#E1306C" strokeWidth="2" />
                        <circle cx="12" cy="12" r="4" stroke="#E1306C" strokeWidth="2" />
                        <line x1="17.5" y1="6.5" x2="17.51" y2="6.5" stroke="#E1306C" strokeWidth="2.5" strokeLinecap="round" />
                      </svg>
                    )}
                    <span className="messenger-name-label">{messenger}</span>
                  </div>

                  <svg
                    className={`dropdown-chevron-arrow ${isMessengerOpen ? 'chevron-rotated' : ''}`}
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.2"
                  >
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </div>

                {/* Dropdown Options Plashka */}
                {isMessengerOpen && (
                  <div className="messenger-options-dropdown" role="listbox">
                    <div
                      className={`messenger-option-item ${messenger === 'Telegram' ? 'is-selected' : ''}`}
                      onClick={() => {
                        setMessenger('Telegram');
                        setIsMessengerOpen(false);
                      }}
                      role="option"
                      aria-selected={messenger === 'Telegram'}
                    >
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
                        <path
                          d="M21.5 3.5L2 11.5L9.5 14.5L18 8L11.5 16L18.5 21L21.5 3.5Z"
                          stroke="#2AABEE"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      <span>Telegram</span>
                    </div>

                    <div
                      className={`messenger-option-item ${messenger === 'WhatsApp' ? 'is-selected' : ''}`}
                      onClick={() => {
                        setMessenger('WhatsApp');
                        setIsMessengerOpen(false);
                      }}
                      role="option"
                      aria-selected={messenger === 'WhatsApp'}
                    >
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
                        <path
                          d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
                          stroke="#25D366"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      <span>WhatsApp</span>
                    </div>

                    <div
                      className={`messenger-option-item ${messenger === 'Instagram' ? 'is-selected' : ''}`}
                      onClick={() => {
                        setMessenger('Instagram');
                        setIsMessengerOpen(false);
                      }}
                      role="option"
                      aria-selected={messenger === 'Instagram'}
                    >
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
                        <rect x="2" y="2" width="20" height="20" rx="5" stroke="#E1306C" strokeWidth="2" />
                        <circle cx="12" cy="12" r="4" stroke="#E1306C" strokeWidth="2" />
                        <line x1="17.5" y1="6.5" x2="17.51" y2="6.5" stroke="#E1306C" strokeWidth="2.5" strokeLinecap="round" />
                      </svg>
                      <span>Instagram</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* 5. Описание проекта или технические требования* */}
            <div className="form-input-field">
              <label htmlFor="clientDescription" className="input-field-label">
                Описание проекта или технические требования *
              </label>
              <textarea
                id="clientDescription"
                className="input-box-control textarea-field-control"
                placeholder="опишите что хотите получить,  какой проект задумали?"
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                required
              />
            </div>

            {/* 6. Окно загрузки файла & 7. Подпись до 25МБ */}
            <div className="form-input-field file-upload-wrapper">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                className="file-hidden-input"
                id="briefFileInput"
                accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.zip,.rar,.fig"
              />

              <div
                className={`file-dropzone-box ${isDragging ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
                onClick={() => fileInputRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    fileInputRef.current?.click();
                  }
                }}
              >
                {!file ? (
                  <div className="file-dropzone-empty-state">
                    <svg
                      className="upload-cloud-icon"
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                    >
                      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                    </svg>
                    <span className="file-dropzone-primary-text">
                      Прикрепить ТЗ, бриф, макет или фото.
                    </span>
                  </div>
                ) : (
                  <div className="file-attached-info-row">
                    <svg
                      className="attached-paperclip-icon"
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="2"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    <div className="attached-filename-details">
                      <span className="attached-filename-text">{file.name}</span>
                      <span className="attached-filesize-text">
                        ({(file.size / (1024 * 1024)).toFixed(2)} МБ)
                      </span>
                    </div>
                    <button
                      type="button"
                      className="remove-attached-file-btn"
                      onClick={removeFile}
                      aria-label="Удалить файл"
                    >
                      ✕
                    </button>
                  </div>
                )}
              </div>

              {/* 7. Подпись до 25МБ */}
              <span className="file-size-limit-notice">до 25МБ</span>
            </div>

            {/* Error banner if submission or upload failed */}
            {submitError && (
              <div className="form-submit-error-banner" role="alert">
                <span className="error-icon" aria-hidden="true">⚠️</span>
                <span>{submitError}</span>
              </div>
            )}

            {/* 8. Кнопка отправки заявки */}
            <button
              type="submit"
              className="submit-white-action-btn"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Отправка...' : 'отправить заявку'}
            </button>
          </form>
          )}
        </div>
      </div>
    </section>
  );
};

export default FinalCta;
