import React, { useState, useEffect } from 'react';
import { 
  Send, 
  UploadCloud, 
  CheckCircle2, 
  AlertCircle, 
  FileText, 
  X, 
  Loader2, 
  ShieldCheck, 
  MessageSquare,
  Sparkles,
  Clock
} from 'lucide-react';

export default function ContactForm({ 
  prefillBudget = '', 
  prefillSummary = '', 
  prefillType = '',
  isModal = false,
  onClose = () => {}
}) {
  const [formData, setFormData] = useState({
    name: '',
    contact: '',
    task_description: prefillSummary || '',
    budget: prefillBudget || '',
    hp_website: '', // Honeypot
  });

  const [attachment, setAttachment] = useState(null); // { name, url, size }
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  const [submitting, setSubmitting] = useState(false);
  const [submittedLead, setSubmittedLead] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [botUsername, setBotUsername] = useState('castleweb_bot');

  // Fetch Telegram bot username for direct linking
  useEffect(() => {
    let isMounted = true;
    fetch('/api/v1/telegram/bot-info')
      .then(res => res.json())
      .then(data => {
        if (data.ok && data.username && isMounted) {
          setBotUsername(data.username);
        }
      })
      .catch(() => {});
    return () => { isMounted = false; };
  }, []);

  // Sync props if calculator sends an estimate
  useEffect(() => {
    if (prefillSummary) {
      setFormData(prev => ({
        ...prev,
        task_description: prefillSummary,
        budget: prefillBudget || prev.budget
      }));
    }
  }, [prefillSummary, prefillBudget]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (submitError) setSubmitError(null);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Check size limit: 25MB
    if (file.size > 25 * 1024 * 1024) {
      setUploadError('Файл превышает лимит 25 МБ');
      return;
    }

    setUploading(true);
    setUploadError(null);

    try {
      // Step 1: Request presigned url or direct file endpoint
      const formPayload = new FormData();
      formPayload.append('file', file);

      const res = await fetch('/api/v1/uploads/file', {
        method: 'POST',
        body: formPayload
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Ошибка загрузки файла');
      }

      const data = await res.json();
      setAttachment({
        name: file.name,
        url: data.url,
        size: (file.size / (1024 * 1024)).toFixed(2) + ' МБ'
      });
    } catch (err) {
      setUploadError(err.message || 'Не удалось прикрепить файл');
    } finally {
      setUploading(false);
      if (e.target) e.target.value = '';
    }
  };

  const handleRemoveAttachment = () => {
    setAttachment(null);
    setUploadError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;

    // Form validations
    if (!formData.name.trim() || formData.name.trim().length < 2) {
      setSubmitError('Пожалуйста, укажите ваше имя или название компании (мин. 2 символа).');
      return;
    }
    if (!formData.contact.trim() || formData.contact.trim().length < 3) {
      setSubmitError('Укажите контакт для связи: Telegram @username, почту или телефон.');
      return;
    }
    if (!formData.task_description.trim() || formData.task_description.trim().length < 5) {
      setSubmitError('Пожалуйста, опишите кратко задачу проекта (мин. 5 символов).');
      return;
    }

    setSubmitting(true);
    setSubmitError(null);

    try {
      const payload = {
        name: formData.name.trim(),
        contact: formData.contact.trim(),
        task_description: formData.task_description.trim(),
        budget: formData.budget.trim() || null,
        attachment_url: attachment ? attachment.url : null,
        hp_website: formData.hp_website.trim() || null,
        turnstile_token: null
      };

      const res = await fetch('/api/v1/leads', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        if (res.status === 429) {
          throw new Error('Превышен лимит запросов. Пожалуйста, подождите несколько минут перед отправкой следующей заявки.');
        }
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Не удалось отправить заявку. Попробуйте еще раз или напишите напрямую в Telegram.');
      }

      const data = await res.json();
      setSubmittedLead(data);
    } catch (err) {
      setSubmitError(err.message || 'Сетевая ошибка при отправке заявки.');
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setSubmittedLead(null);
    setFormData({
      name: '',
      contact: '',
      task_description: '',
      budget: '',
      hp_website: ''
    });
    setAttachment(null);
    setSubmitError(null);
  };

  const formContent = (
    <div className={`lead-form-box ${isModal ? 'lead-form-modal' : ''}`}>
      {isModal && (
        <button 
          className="modal-close-btn" 
          onClick={onClose}
          aria-label="Закрыть окно"
        >
          <X size={20} />
        </button>
      )}

      {submittedLead ? (
        /* Success Screen */
        <div className="success-state">
          <div className="success-icon-box">
            <CheckCircle2 size={48} className="success-icon" />
            <div className="success-sparkle" />
          </div>

          <div className="badge badge-glow success-badge">
            <Sparkles size={13} />
            <span>ЗАЯВКА #{submittedLead.id || 'LIVE'} ПРИНЯТА В ОБРАБОТКУ</span>
          </div>

          <h3 className="success-title">
            Прямой контакт <span className="gradient-text">установлен</span>
          </h3>

          <p className="success-description">
            Данные по проекту <strong>«{formData.name}»</strong> моментально доставлены 
            в закрытый дежурный канал ведущих архитекторов CASTLEWEB.
          </p>

          <div className="success-telemetry-box">
            <div className="success-telemetry-row">
              <span className="telemetry-label">Канал связи:</span>
              <span className="telemetry-value font-mono">{formData.contact}</span>
            </div>
            <div className="success-telemetry-row">
              <span className="telemetry-label">Статус обработки:</span>
              <span className="telemetry-value text-emerald flex-center">
                <span className="pulse-beacon" /> Ожидает распределения
              </span>
            </div>
            <div className="success-telemetry-row">
              <span className="telemetry-label">Среднее время ответа:</span>
              <span className="telemetry-value text-cyan">
                <Clock size={13} className="inline-icon" /> ~15 минут
              </span>
            </div>
          </div>

          <div className="success-actions">
            <a 
              href={`https://t.me/${botUsername || 'castleweb_bot'}?start=lead_${submittedLead.id || 0}`} 
              target="_blank" 
              rel="noopener noreferrer" 
              className="btn-primary w-full"
              id="btn-goto-telegram"
            >
              <span>{`Перейти к диалогу в Telegram (@${botUsername || 'castleweb_bot'})`}</span>
              <Send size={16} />
            </a>

            <button 
              className="btn-ghost w-full" 
              onClick={resetForm}
            >
              Отправить еще одну заявку
            </button>
          </div>
        </div>
      ) : (
        /* Regular Form */
        <form onSubmit={handleSubmit} className="lead-form" noValidate>
          <div className="form-head">
            <div className="badge badge-glow">
              <MessageSquare size={13} />
              <span>ОБСУЖДЕНИЕ ПРОЕКТА БЕЗ МЕНЕДЖЕРОВ-ПОСРЕДНИКОВ</span>
            </div>
            <h3 className="form-title">
              Расскажите о задаче — мы вернемся с <span className="gradient-text">архитектурным решением</span>
            </h3>
            <p className="form-subtitle">
              Разбираем стек, проектируем масштабируемую архитектуру, даем прозрачную оценку по спринтам и фиксируем NDA.
            </p>
            <div className="tg-quick-banner">
              <span>Предпочитаете Telegram? Напишите нам напрямую:</span>
              <a 
                href={`https://t.me/${botUsername || 'castleweb_bot'}`} 
                target="_blank" 
                rel="noopener noreferrer"
                className="tg-quick-link"
              >
                <Send size={13} />
                <span>@{botUsername || 'castleweb_bot'}</span>
              </a>
            </div>
          </div>

          {submitError && (
            <div className="form-alert form-alert-error">
              <AlertCircle size={18} className="alert-icon" />
              <span>{submitError}</span>
            </div>
          )}

          {/* Honeypot field (hidden from real users) */}
          <div style={{ display: 'none', position: 'absolute', left: '-9999px' }} aria-hidden="true">
            <input 
              type="text" 
              name="hp_website" 
              value={formData.hp_website} 
              onChange={handleInputChange} 
              tabIndex={-1} 
              autoComplete="off" 
            />
          </div>

          <div className="form-grid">
            <div className="form-field">
              <label htmlFor="lead-name" className="field-label">
                Ваше имя или компания <span className="req">*</span>
              </label>
              <input 
                type="text" 
                id="lead-name"
                name="name" 
                value={formData.name} 
                onChange={handleInputChange} 
                placeholder="Константин / FinTech Corp" 
                className="input-text"
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="lead-contact" className="field-label">
                Telegram / Почта / Телефон <span className="req">*</span>
              </label>
              <input 
                type="text" 
                id="lead-contact"
                name="contact" 
                value={formData.contact} 
                onChange={handleInputChange} 
                placeholder="@username или ceo@domain.com" 
                className="input-text"
                required
              />
            </div>
          </div>

          <div className="form-field">
            <div className="field-label-row">
              <label htmlFor="lead-budget" className="field-label">
                Ориентир бюджета / Формат спринтов
              </label>
              {prefillType && (
                <span className="badge-tag">Конфигуратор: {prefillType}</span>
              )}
            </div>
            <input 
              type="text" 
              id="lead-budget"
              name="budget" 
              value={formData.budget} 
              onChange={handleInputChange} 
              placeholder="Например: 250 000 — 400 000 ₽ или Открытый бюджет" 
              className="input-text"
            />
          </div>

          <div className="form-field">
            <label htmlFor="lead-task" className="field-label">
              Описание проекта или технические требования <span className="req">*</span>
            </label>
            <textarea 
              id="lead-task"
              name="task_description" 
              value={formData.task_description} 
              onChange={handleInputChange} 
              rows={4}
              placeholder="Опишите продукт, целевую аудиторию, ключевые интеграции (1С, платежи, AI) или текущие узкие места в производительности..." 
              className="input-textarea"
              required
            />
          </div>

          {/* File Upload Box */}
          <div className="upload-container">
            {attachment ? (
              <div className="attached-file-chip">
                <FileText size={18} className="attached-icon" />
                <div className="attached-info">
                  <span className="attached-name">{attachment.name}</span>
                  <span className="attached-size">{attachment.size} • Загружено</span>
                </div>
                <button 
                  type="button" 
                  onClick={handleRemoveAttachment} 
                  className="attached-remove-btn"
                  title="Удалить файл"
                >
                  <X size={16} />
                </button>
              </div>
            ) : (
              <label className={`upload-dropzone ${uploading ? 'uploading' : ''}`}>
                <input 
                  type="file" 
                  onChange={handleFileUpload}
                  disabled={uploading}
                  className="file-input-hidden" 
                  accept=".pdf,.zip,.rar,.7z,.tar,.gz,.png,.jpg,.jpeg,.webp,.svg,.gif,.docx,.doc,.pptx,.ppt,.odt,.rtf,.fig,.txt,.csv,.xlsx"
                />
                {uploading ? (
                  <div className="upload-loading-state">
                    <Loader2 size={22} className="spin-icon text-cyan" />
                    <span>Загрузка файла в защищенное хранилище...</span>
                  </div>
                ) : (
                  <div className="upload-idle-state">
                    <UploadCloud size={20} className="upload-icon" />
                    <span className="upload-main-text">
                      Прикрепить ТЗ, бриф, макет или фото
                    </span>
                    <span className="upload-sub-text">
                      PDF, DOCX, ZIP, PNG, JPG, FIG до 25 МБ
                    </span>
                  </div>
                )}
              </label>
            )}

            {uploadError && (
              <div className="upload-error-msg">
                <AlertCircle size={14} />
                <span>{uploadError}</span>
              </div>
            )}
          </div>

          {/* Privacy & Trust Badge */}
          <div className="form-footer-meta">
            <div className="meta-security">
              <ShieldCheck size={16} className="text-emerald" />
              <span>Строгий NDA по умолчанию. Данные защищены и не передаются третьим лицам.</span>
            </div>
          </div>

          {/* Submit Button */}
          <button 
            type="submit" 
            className="btn-primary form-submit-btn w-full"
            disabled={submitting}
            id="lead-submit-btn"
          >
            {submitting ? (
              <>
                <Loader2 size={18} className="spin-icon" />
                <span>Шифрование и отправка в Telegram...</span>
              </>
            ) : (
              <>
                <span>Отправить заявку архитекторам</span>
                <Send size={18} />
              </>
            )}
          </button>
        </form>
      )}

      <style>{`
        .lead-form-box {
          background: rgba(14, 18, 28, 0.85);
          border: 1px solid var(--border-glow);
          border-radius: 24px;
          padding: 40px;
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          box-shadow: 0 30px 60px -15px rgba(0, 0, 0, 0.7), 0 0 40px -10px rgba(99, 102, 241, 0.2);
          position: relative;
          transition: all var(--transition-normal);
        }
        .lead-form-modal {
          max-width: 680px;
          width: 90vw;
          max-height: 90vh;
          overflow-y: auto;
          margin: auto;
        }
        .modal-close-btn {
          position: absolute;
          top: 20px;
          right: 20px;
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid var(--border-subtle);
          color: var(--text-secondary);
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all var(--transition-fast);
        }
        .modal-close-btn:hover {
          background: rgba(239, 68, 68, 0.2);
          color: #ef4444;
          border-color: rgba(239, 68, 68, 0.4);
        }
        .form-head {
          margin-bottom: 28px;
        }
        .form-title {
          font-size: 1.75rem;
          margin-top: 14px;
          margin-bottom: 8px;
          line-height: 1.25;
        }
        .form-subtitle {
          font-size: 0.95rem;
          color: var(--text-secondary);
          line-height: 1.6;
        }
        .tg-quick-banner {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          margin-top: 14px;
          padding: 8px 16px;
          background: rgba(99, 102, 241, 0.08);
          border: 1px solid rgba(99, 102, 241, 0.25);
          border-radius: 9999px;
          font-size: 0.85rem;
          color: var(--text-secondary);
        }
        .tg-quick-link {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          color: #818cf8;
          font-weight: 600;
          text-decoration: none;
          transition: color var(--transition-fast);
        }
        .tg-quick-link:hover {
          color: #a5b4fc;
          text-decoration: underline;
        }
        .form-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 18px;
          margin-bottom: 18px;
        }
        .form-field {
          margin-bottom: 18px;
        }
        .field-label {
          display: block;
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-primary);
          margin-bottom: 8px;
        }
        .field-label-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }
        .field-label-row .field-label {
          margin-bottom: 0;
        }
        .badge-tag {
          font-size: 0.72rem;
          font-family: var(--font-mono);
          color: var(--accent-cyan);
          background: rgba(6, 182, 212, 0.12);
          padding: 2px 8px;
          border-radius: 6px;
          border: 1px solid rgba(6, 182, 212, 0.25);
        }
        .req {
          color: #ef4444;
        }
        .input-text, .input-textarea {
          width: 100%;
          background: rgba(8, 10, 16, 0.8);
          border: 1px solid rgba(255, 255, 255, 0.12);
          border-radius: 12px;
          padding: 14px 16px;
          color: var(--text-primary);
          font-size: 0.95rem;
          font-family: inherit;
          transition: all var(--transition-fast);
          outline: none;
        }
        .input-text:focus, .input-textarea:focus {
          border-color: var(--accent-indigo);
          box-shadow: 0 0 16px -2px rgba(99, 102, 241, 0.4);
          background: rgba(11, 15, 26, 0.95);
        }
        .input-textarea {
          resize: vertical;
          min-height: 100px;
        }
        .upload-container {
          margin-bottom: 22px;
        }
        .upload-dropzone {
          display: block;
          border: 1px dashed rgba(255, 255, 255, 0.18);
          border-radius: 14px;
          padding: 16px;
          background: rgba(255, 255, 255, 0.02);
          cursor: pointer;
          transition: all var(--transition-fast);
          text-align: center;
        }
        .upload-dropzone:hover {
          border-color: var(--accent-cyan);
          background: rgba(6, 182, 212, 0.05);
        }
        .upload-dropzone.uploading {
          border-color: var(--accent-cyan);
          background: rgba(6, 182, 212, 0.08);
          cursor: wait;
        }
        .file-input-hidden {
          display: none;
        }
        .upload-idle-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
        }
        .upload-icon {
          color: var(--accent-cyan);
        }
        .upload-main-text {
          font-size: 0.88rem;
          font-weight: 500;
          color: var(--text-primary);
        }
        .upload-sub-text {
          font-size: 0.75rem;
          color: var(--text-muted);
        }
        .upload-loading-state {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          font-size: 0.88rem;
          color: var(--text-secondary);
        }
        .attached-file-chip {
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: rgba(16, 185, 129, 0.1);
          border: 1px solid rgba(16, 185, 129, 0.3);
          border-radius: 12px;
          padding: 12px 16px;
        }
        .attached-icon {
          color: var(--accent-emerald);
          margin-right: 12px;
        }
        .attached-info {
          display: flex;
          flex-direction: column;
          flex-grow: 1;
        }
        .attached-name {
          font-size: 0.9rem;
          font-weight: 600;
          color: #ffffff;
        }
        .attached-size {
          font-size: 0.75rem;
          color: var(--accent-emerald);
          font-family: var(--font-mono);
        }
        .attached-remove-btn {
          color: var(--text-muted);
          padding: 4px;
          border-radius: 6px;
          transition: all var(--transition-fast);
        }
        .attached-remove-btn:hover {
          color: #ef4444;
          background: rgba(239, 68, 68, 0.15);
        }
        .upload-error-msg {
          display: flex;
          align-items: center;
          gap: 6px;
          color: #ef4444;
          font-size: 0.8rem;
          margin-top: 8px;
        }
        .form-footer-meta {
          margin-bottom: 22px;
        }
        .meta-security {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.8rem;
          color: var(--text-secondary);
        }
        .form-submit-btn {
          padding: 16px 28px;
          font-size: 1.05rem;
          font-weight: 700;
          box-shadow: 0 10px 30px -5px rgba(99, 102, 241, 0.5);
        }
        .form-alert {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 14px 18px;
          border-radius: 12px;
          font-size: 0.9rem;
          margin-bottom: 20px;
        }
        .form-alert-error {
          background: rgba(239, 68, 68, 0.12);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #fca5a5;
        }
        .alert-icon {
          color: #ef4444;
          flex-shrink: 0;
        }

        /* Success Screen */
        .success-state {
          text-align: center;
          padding: 20px 10px;
        }
        .success-icon-box {
          width: 80px;
          height: 80px;
          border-radius: 24px;
          background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(6, 182, 212, 0.2) 100%);
          border: 1px solid rgba(16, 185, 129, 0.4);
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 20px;
          color: var(--accent-emerald);
          box-shadow: 0 0 35px -5px rgba(16, 185, 129, 0.4);
        }
        .success-badge {
          margin-bottom: 16px;
        }
        .success-title {
          font-size: 2rem;
          margin-bottom: 12px;
        }
        .success-description {
          font-size: 1rem;
          color: var(--text-secondary);
          max-width: 480px;
          margin: 0 auto 28px;
          line-height: 1.6;
        }
        .success-telemetry-box {
          background: rgba(8, 10, 16, 0.7);
          border: 1px solid var(--border-subtle);
          border-radius: 16px;
          padding: 18px 24px;
          margin-bottom: 30px;
          text-align: left;
        }
        .success-telemetry-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 0;
          font-size: 0.9rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .success-telemetry-row:last-child {
          border-bottom: none;
        }
        .telemetry-label {
          color: var(--text-muted);
        }
        .telemetry-value {
          font-weight: 600;
          color: var(--text-primary);
        }
        .text-emerald {
          color: var(--accent-emerald);
        }
        .text-cyan {
          color: var(--accent-cyan);
        }
        .flex-center {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .success-actions {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .btn-ghost {
          padding: 12px;
          color: var(--text-secondary);
          font-size: 0.9rem;
          transition: color var(--transition-fast);
        }
        .btn-ghost:hover {
          color: #ffffff;
        }
        .spin-icon {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .w-full {
          width: 100%;
        }

        @media (max-width: 640px) {
          .lead-form-box {
            padding: 24px 18px;
          }
          .form-grid {
            grid-template-columns: 1fr;
            gap: 14px;
          }
          .form-title {
            font-size: 1.4rem;
          }
          .success-title {
            font-size: 1.5rem;
          }
        }
      `}</style>
    </div>
  );

  return formContent;
}
