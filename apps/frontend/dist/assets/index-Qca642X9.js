import{n as e}from"./rolldown-runtime-CbXtAM7H.js";import{A as t,C as n,D as r,E as i,M as a,N as o,O as s,S as c,T as l,_ as u,a as d,b as f,c as p,d as m,f as h,g,h as _,i as v,j as y,k as b,l as x,m as S,n as C,o as w,p as T,r as E,s as D,t as O,u as k,v as A,w as j,x as M,y as N}from"./vendor-react-uDFqD63-.js";(function(){let e=document.createElement(`link`).relList;if(e&&e.supports&&e.supports(`modulepreload`))return;for(let e of document.querySelectorAll(`link[rel="modulepreload"]`))n(e);new MutationObserver(e=>{for(let t of e)if(t.type===`childList`)for(let e of t.addedNodes)e.tagName===`LINK`&&e.rel===`modulepreload`&&n(e)}).observe(document,{childList:!0,subtree:!0});function t(e){let t={};return e.integrity&&(t.integrity=e.integrity),e.referrerPolicy&&(t.referrerPolicy=e.referrerPolicy),t.credentials=e.crossOrigin===`use-credentials`?`include`:e.crossOrigin===`anonymous`?`omit`:`same-origin`,t}function n(e){if(e.ep)return;e.ep=!0;let n=t(e);fetch(e.href,n)}})();var P=e(o(),1),F=a(),I=O();function L({onOpenContact:e}){let[t,n]=(0,P.useState)(!1),[r,i]=(0,P.useState)(!1),[a,o]=(0,P.useState)(14);return(0,P.useEffect)(()=>{let e=()=>{n(window.scrollY>20)};return window.addEventListener(`scroll`,e),()=>window.removeEventListener(`scroll`,e)},[]),(0,P.useEffect)(()=>{let e=!0,t=async()=>{if(!document.hidden)try{let t=await fetch(`/api/v1/status`);if(t.ok&&e){let e=await t.json();e.latency_ms!==void 0&&o(typeof e.latency_ms==`number`?e.latency_ms.toFixed(1):e.latency_ms)}}catch{}};t();let n=setInterval(t,1e3);return()=>{e=!1,clearInterval(n)}},[]),(0,I.jsxs)(`header`,{className:`navbar-wrapper ${t?`navbar-scrolled`:``}`,children:[(0,I.jsxs)(`div`,{className:`container`,children:[(0,I.jsxs)(`nav`,{className:`navbar-content`,children:[(0,I.jsxs)(`a`,{href:`#`,className:`brand-logo`,id:`nav-brand`,children:[(0,I.jsx)(`div`,{className:`brand-icon-circ`,children:(0,I.jsx)(w,{size:16})}),(0,I.jsx)(`span`,{className:`brand-name`,children:`Castleweb`})]}),(0,I.jsxs)(`div`,{className:`nav-links`,children:[(0,I.jsx)(`a`,{href:`#hero`,className:`nav-link`,children:`Главная`}),(0,I.jsx)(`a`,{href:`#features`,className:`nav-link`,children:`Преимущества`}),(0,I.jsx)(`a`,{href:`#cases`,className:`nav-link`,children:`Кейсы`}),(0,I.jsx)(`a`,{href:`#calculator`,className:`nav-link`,children:`Калькулятор`}),(0,I.jsx)(`a`,{href:`#architecture`,className:`nav-link`,children:`Архитектура`}),(0,I.jsx)(`a`,{href:`#faq`,className:`nav-link`,children:`FAQ`})]}),(0,I.jsxs)(`div`,{className:`nav-actions`,children:[(0,I.jsxs)(`div`,{className:`nav-telemetry-badge`,title:`Задержка отклика API`,children:[(0,I.jsx)(`span`,{className:`pulse-beacon`}),(0,I.jsxs)(`span`,{children:[a,` ms`]})]}),(0,I.jsxs)(`button`,{className:`btn-primary nav-cta-btn`,onClick:e,id:`nav-btn-discuss`,children:[(0,I.jsx)(`span`,{children:`Обсудить проект`}),(0,I.jsx)(y,{size:14})]}),(0,I.jsx)(`button`,{className:`mobile-toggle-btn`,onClick:()=>i(!r),"aria-label":`Toggle navigation menu`,children:r?(0,I.jsx)(E,{size:22}):(0,I.jsx)(T,{size:22})})]})]}),r&&(0,I.jsxs)(`div`,{className:`mobile-menu`,children:[(0,I.jsx)(`a`,{href:`#features`,onClick:()=>i(!1),className:`mobile-link`,children:`Преимущества`}),(0,I.jsx)(`a`,{href:`#cases`,onClick:()=>i(!1),className:`mobile-link`,children:`Кейсы`}),(0,I.jsx)(`a`,{href:`#calculator`,onClick:()=>i(!1),className:`mobile-link`,children:`Калькулятор`}),(0,I.jsx)(`a`,{href:`#architecture`,onClick:()=>i(!1),className:`mobile-link`,children:`Архитектура`}),(0,I.jsx)(`a`,{href:`#faq`,onClick:()=>i(!1),className:`mobile-link`,children:`FAQ`}),(0,I.jsx)(`button`,{className:`btn-primary w-full`,onClick:()=>{i(!1),e()},children:(0,I.jsx)(`span`,{children:`Обсудить проект`})})]})]}),(0,I.jsx)(`style`,{children:`
        .navbar-wrapper {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          z-index: 100;
          padding: 20px 0;
          transition: all var(--transition-normal);
        }
        .navbar-scrolled {
          padding: 14px 0;
          background: rgba(0, 0, 0, 0.85);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border-bottom: 1px solid var(--border-subtle);
        }
        .navbar-content {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
        }
        .brand-logo {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .brand-icon-circ {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.16);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #ffffff;
        }
        .brand-name {
          font-family: var(--font-display);
          font-size: 1.15rem;
          font-weight: 700;
          color: #ffffff;
          letter-spacing: -0.02em;
        }
        .nav-links {
          display: flex;
          align-items: center;
          gap: 32px;
        }
        .nav-link {
          font-size: 0.88rem;
          font-weight: 500;
          color: var(--text-secondary);
          transition: color var(--transition-fast);
        }
        .nav-link:hover {
          color: #ffffff;
        }
        .nav-actions {
          display: flex;
          align-items: center;
          gap: 14px;
        }
        .nav-telemetry-badge {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid var(--border-subtle);
          border-radius: 9999px;
          font-size: 0.75rem;
          font-family: var(--font-mono);
          color: var(--text-secondary);
        }
        .nav-cta-btn {
          padding: 10px 20px;
          font-size: 0.85rem;
        }
        .mobile-toggle-btn {
          display: none;
          color: #ffffff;
        }
        .mobile-menu {
          display: none;
        }

        @media (max-width: 900px) {
          .nav-links, .nav-telemetry-badge {
            display: none;
          }
          .mobile-toggle-btn {
            display: block;
          }
          .mobile-menu {
            display: flex;
            flex-direction: column;
            gap: 16px;
            margin-top: 16px;
            padding: 24px;
            background: #08090d;
            border: 1px solid var(--border-subtle);
            border-radius: 16px;
          }
          .mobile-link {
            font-size: 1rem;
            color: var(--text-secondary);
          }
        }
      `})]})}var R=[`asana`,`Fidelity`,`CenturyLink`,`coinbase`,`BINANCE`,`Cloudflare`,`FastAPI`,`PostgreSQL`];function z({onOpenContact:e,onExploreCases:t}){return(0,I.jsxs)(`section`,{className:`hero-section`,id:`hero`,children:[(0,I.jsxs)(`div`,{className:`container`,children:[(0,I.jsxs)(`div`,{className:`hero-grid`,children:[(0,I.jsxs)(`div`,{className:`hero-content`,children:[(0,I.jsxs)(`div`,{className:`badge-capsule hero-badge`,children:[(0,I.jsx)(`span`,{className:`badge-icon`,children:(0,I.jsx)(d,{size:11})}),(0,I.jsx)(`span`,{children:`HIGHLOAD & AI-DRIVEN WEB ENGINEERING`})]}),(0,I.jsxs)(`h1`,{className:`hero-title`,children:[`AI-Driven & Highload Solutions `,(0,I.jsx)(`br`,{}),(0,I.jsx)(`span`,{className:`text-highlight`,children:`for Modern Businesses`})]}),(0,I.jsx)(`p`,{className:`hero-description`,children:`Castleweb is engineered with your goals in mind, making architecture and delivery reliable. We build high-concurrency SaaS platforms, interactive 3D WebGL interfaces, and zero-downtime APIs without compromise.`}),(0,I.jsxs)(`div`,{className:`hero-actions`,children:[(0,I.jsxs)(`a`,{href:`#calculator`,className:`btn-primary`,id:`hero-btn-calc`,children:[(0,I.jsx)(`span`,{children:`Рассчитать смету`}),(0,I.jsx)(y,{size:16})]}),(0,I.jsx)(`button`,{onClick:t,className:`btn-secondary`,id:`hero-btn-cases`,children:(0,I.jsx)(`span`,{children:`Смотреть кейсы`})})]})]}),(0,I.jsx)(`div`,{className:`hero-visual`,children:(0,I.jsxs)(`div`,{className:`hero-img-wrap`,children:[(0,I.jsx)(`img`,{src:`/hero_chrome.jpg`,alt:`3D Liquid Chrome Abstract Sculpture`,className:`hero-3d-img`}),(0,I.jsx)(`div`,{className:`hero-img-glow`})]})})]}),(0,I.jsxs)(`div`,{className:`hero-stats-strip`,children:[(0,I.jsxs)(`div`,{className:`stat-unit`,children:[(0,I.jsx)(`span`,{className:`stat-num`,children:`48+`}),(0,I.jsx)(`span`,{className:`stat-desc`,children:`Проектов в проде`})]}),(0,I.jsx)(`div`,{className:`stat-sep`}),(0,I.jsxs)(`div`,{className:`stat-unit`,children:[(0,I.jsx)(`span`,{className:`stat-num`,children:`230+`}),(0,I.jsx)(`span`,{className:`stat-desc`,children:`Клиентов по всему миру`})]}),(0,I.jsx)(`div`,{className:`stat-sep`}),(0,I.jsxs)(`div`,{className:`stat-unit`,children:[(0,I.jsx)(`span`,{className:`stat-num`,children:`99.98%`}),(0,I.jsx)(`span`,{className:`stat-desc`,children:`Гарантированный Uptime`})]}),(0,I.jsx)(`div`,{className:`stat-sep`}),(0,I.jsxs)(`div`,{className:`stat-unit`,children:[(0,I.jsx)(`span`,{className:`stat-num`,children:`< 50ms`}),(0,I.jsx)(`span`,{className:`stat-desc`,children:`Средний отклик API`})]})]}),(0,I.jsx)(`div`,{className:`hero-partners-strip`,children:R.map((e,t)=>(0,I.jsx)(`div`,{className:`partner-logo-item`,children:(0,I.jsx)(`span`,{className:`partner-name`,children:e})},t))})]}),(0,I.jsx)(`style`,{children:`
        .hero-section {
          padding: 140px 0 80px;
          position: relative;
          overflow: hidden;
        }
        .hero-grid {
          display: grid;
          grid-template-columns: 1.15fr 0.85fr;
          gap: 40px;
          align-items: center;
          margin-bottom: 80px;
        }
        .hero-badge {
          margin-bottom: 24px;
        }
        .hero-title {
          font-size: 3.8rem;
          font-weight: 800;
          letter-spacing: -0.035em;
          line-height: 1.1;
          margin-bottom: 22px;
          color: #ffffff;
        }
        .text-highlight {
          color: #ffffff;
        }
        .hero-description {
          font-size: 1.1rem;
          color: var(--text-secondary);
          line-height: 1.65;
          margin-bottom: 34px;
          max-width: 540px;
        }
        .hero-actions {
          display: flex;
          align-items: center;
          gap: 16px;
        }
        .hero-visual {
          position: relative;
          display: flex;
          justify-content: center;
          align-items: center;
        }
        .hero-img-wrap {
          position: relative;
          width: 100%;
          max-width: 480px;
          display: flex;
          justify-content: center;
        }
        .hero-3d-img {
          width: 100%;
          height: auto;
          object-fit: contain;
          filter: drop-shadow(0 20px 40px rgba(0, 0, 0, 0.9));
          animation: floatHero 6s ease-in-out infinite;
        }
        .hero-img-glow {
          position: absolute;
          width: 80%;
          height: 80%;
          background: radial-gradient(circle, rgba(255, 255, 255, 0.08) 0%, transparent 70%);
          top: 10%;
          left: 10%;
          pointer-events: none;
          z-index: -1;
        }
        @keyframes floatHero {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-12px) rotate(1deg); }
        }

        /* Stats Strip */
        .hero-stats-strip {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 34px 44px;
          border-radius: 20px;
          background: rgba(13, 15, 21, 0.7);
          border: 1px solid var(--border-subtle);
          margin-bottom: 60px;
          backdrop-filter: blur(12px);
        }
        .stat-unit {
          display: flex;
          align-items: baseline;
          gap: 12px;
        }
        .stat-num {
          font-family: var(--font-display);
          font-size: 2.2rem;
          font-weight: 800;
          color: #ffffff;
          letter-spacing: -0.02em;
        }
        .stat-desc {
          font-size: 0.85rem;
          color: var(--text-secondary);
          font-weight: 500;
        }
        .stat-sep {
          width: 1px;
          height: 36px;
          background: var(--border-subtle);
        }

        /* Partners Logo Strip */
        .hero-partners-strip {
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 24px;
          padding: 20px 0;
          opacity: 0.6;
          transition: opacity var(--transition-fast);
        }
        .hero-partners-strip:hover {
          opacity: 0.9;
        }
        .partner-name {
          font-family: var(--font-display);
          font-size: 1.1rem;
          font-weight: 700;
          letter-spacing: 0.05em;
          color: var(--text-secondary);
          text-transform: uppercase;
        }

        @media (max-width: 1024px) {
          .hero-grid {
            grid-template-columns: 1fr;
            text-align: center;
          }
          .hero-title {
            font-size: 2.8rem;
          }
          .hero-description {
            margin: 0 auto 30px;
          }
          .hero-actions {
            justify-content: center;
          }
          .hero-stats-strip {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
            padding: 24px;
          }
          .stat-sep {
            display: none;
          }
        }

        @media (max-width: 640px) {
          .hero-title {
            font-size: 2.2rem;
          }
          .hero-stats-strip {
            grid-template-columns: 1fr;
          }
        }
      `})]})}function B({onOpenContact:e}){return(0,I.jsxs)(`section`,{className:`features-section`,id:`features`,children:[(0,I.jsxs)(`div`,{className:`container`,children:[(0,I.jsxs)(`div`,{className:`features-head text-center`,children:[(0,I.jsxs)(`div`,{className:`badge-capsule`,children:[(0,I.jsx)(`span`,{className:`badge-icon`,children:`✦`}),(0,I.jsx)(`span`,{children:`EXPLORE FEATURES`})]}),(0,I.jsxs)(`h2`,{className:`features-title`,children:[`Effortlessly customize `,(0,I.jsx)(`br`,{}),`for your unique projects.`]}),(0,I.jsx)(`p`,{className:`features-sub`,children:`Инженерные решения, которые снимают ограничения платформ и выводят ваш бизнес на уровень глобального масштаба.`})]}),(0,I.jsxs)(`div`,{className:`feature-cards-grid`,children:[(0,I.jsxs)(`div`,{className:`dark-card feature-card`,children:[(0,I.jsx)(`div`,{className:`squircle-icon`,children:(0,I.jsx)(v,{size:22})}),(0,I.jsx)(`h3`,{className:`card-heading`,children:`Масштабируемость & Highload`}),(0,I.jsx)(`p`,{className:`card-paragraph`,children:`Архитектура с пулом соединений asyncpg, шардированием и кэшированием Redis выдерживает пиковые всплески трафика без падений.`})]}),(0,I.jsxs)(`div`,{className:`dark-card feature-card`,children:[(0,I.jsx)(`div`,{className:`squircle-icon`,children:(0,I.jsx)(u,{size:22})}),(0,I.jsx)(`h3`,{className:`card-heading`,children:`Кастомные 3D & WebGL интерфейсы`}),(0,I.jsx)(`p`,{className:`card-paragraph`,children:`Интерактивные конфигураторы товаров, графики данных в реальном времени и плавная анимация 60 FPS на любых устройствах.`})]}),(0,I.jsxs)(`div`,{className:`dark-card feature-card`,children:[(0,I.jsx)(`div`,{className:`squircle-icon`,children:(0,I.jsx)(x,{size:22})}),(0,I.jsx)(`h3`,{className:`card-heading`,children:`Telegram Headless CRM`}),(0,I.jsx)(`p`,{className:`card-paragraph`,children:`Управление заявками и лидами прямо в закрытом чате команды. Полная независимость от дорогих ежемесячных подписок (0 ₽/мес).`})]})]}),(0,I.jsxs)(`div`,{className:`split-feature-row`,children:[(0,I.jsxs)(`div`,{className:`stacked-items`,children:[(0,I.jsxs)(`div`,{className:`dark-card mini-item-card`,children:[(0,I.jsx)(`div`,{className:`mini-icon-wrap`,children:(0,I.jsx)(_,{size:18})}),(0,I.jsxs)(`div`,{children:[(0,I.jsx)(`h4`,{className:`mini-title`,children:`100% Secured`}),(0,I.jsx)(`p`,{className:`mini-desc`,children:`Строгий WAF, Cloudflare Turnstile, шифрование и отсутствие утечек данных.`})]})]}),(0,I.jsxs)(`div`,{className:`dark-card mini-item-card`,children:[(0,I.jsx)(`div`,{className:`mini-icon-wrap`,children:(0,I.jsx)(C,{size:18})}),(0,I.jsxs)(`div`,{children:[(0,I.jsx)(`h4`,{className:`mini-title`,children:`Субсекундный отклик < 50ms`}),(0,I.jsx)(`p`,{className:`mini-desc`,children:`Оптимизированный асинхронный event loop и кэширование на клиенте.`})]})]}),(0,I.jsxs)(`div`,{className:`dark-card mini-item-card`,children:[(0,I.jsx)(`div`,{className:`mini-icon-wrap`,children:(0,I.jsx)(D,{size:18})}),(0,I.jsxs)(`div`,{children:[(0,I.jsx)(`h4`,{className:`mini-title`,children:`Гарантия SLA и Uptime 99.98%`}),(0,I.jsx)(`p`,{className:`mini-desc`,children:`Zero-downtime деплои через изолированные Docker контейнеры.`})]})]})]}),(0,I.jsxs)(`div`,{className:`split-text-content`,children:[(0,I.jsxs)(`div`,{className:`badge-capsule badge-capsule-emerald`,children:[(0,I.jsx)(`span`,{className:`badge-icon`,children:`✓`}),(0,I.jsx)(`span`,{children:`BENEFITS`})]}),(0,I.jsxs)(`h2`,{className:`split-headline`,children:[`Streamline complex `,(0,I.jsx)(`br`,{}),`business processes with Highload`]}),(0,I.jsx)(`p`,{className:`split-desc`,children:`Мы проектируем архитектуру, которая не требует переписывания через год. Чистый код, покрытие автоматическими тестами и детальная документация Swagger API для вашей команды.`}),(0,I.jsxs)(`button`,{className:`btn-primary`,onClick:e,children:[(0,I.jsx)(`span`,{children:`Обсудить задачу`}),(0,I.jsx)(y,{size:16})]})]})]}),(0,I.jsxs)(`div`,{className:`split-feature-row reverse`,children:[(0,I.jsxs)(`div`,{className:`split-text-content`,children:[(0,I.jsxs)(`div`,{className:`badge-capsule`,children:[(0,I.jsx)(`span`,{className:`badge-icon`,children:`⚡`}),(0,I.jsx)(`span`,{children:`FEATURES YOU'LL NEED`})]}),(0,I.jsxs)(`h2`,{className:`split-headline`,children:[`Powerful solutions for `,(0,I.jsx)(`br`,{}),`your high-growth business`]}),(0,I.jsx)(`p`,{className:`split-desc`,children:`Прямой контроль всех модулей и метрик. Мы измеряем производительность каждого эндпоинта и гарантируем стабильную работу базы данных под нагрузкой.`}),(0,I.jsxs)(`div`,{className:`split-proof-strip`,children:[(0,I.jsx)(`button`,{className:`btn-primary`,onClick:e,children:(0,I.jsx)(`span`,{children:`Начать проект`})}),(0,I.jsxs)(`div`,{className:`avatar-proof`,children:[(0,I.jsxs)(`div`,{className:`avatar-group`,children:[(0,I.jsx)(`div`,{className:`avatar-circle`,children:`CTO`}),(0,I.jsx)(`div`,{className:`avatar-circle`,children:`FE`}),(0,I.jsx)(`div`,{className:`avatar-circle`,children:`BE`})]}),(0,I.jsx)(`span`,{className:`avatar-proof-text`,children:`Команда Senior инженеров`})]})]})]}),(0,I.jsxs)(`div`,{className:`dashboard-preview-card dark-card`,children:[(0,I.jsxs)(`div`,{className:`dash-head`,children:[(0,I.jsxs)(`div`,{children:[(0,I.jsx)(`span`,{className:`dash-label`,children:`API Latency (p99)`}),(0,I.jsxs)(`div`,{className:`dash-metric`,children:[`13.5 ms `,(0,I.jsx)(`span`,{className:`dash-delta`,children:`-84%`})]})]}),(0,I.jsx)(`span`,{className:`dash-badge`,children:`Live Telemetry`})]}),(0,I.jsx)(`div`,{className:`dash-chart-wrap`,children:(0,I.jsxs)(`svg`,{viewBox:`0 0 400 120`,className:`dash-chart-svg`,children:[(0,I.jsx)(`defs`,{children:(0,I.jsxs)(`linearGradient`,{id:`chartGrad`,x1:`0`,y1:`0`,x2:`0`,y2:`1`,children:[(0,I.jsx)(`stop`,{offset:`0%`,stopColor:`#ffffff`,stopOpacity:`0.25`}),(0,I.jsx)(`stop`,{offset:`100%`,stopColor:`#ffffff`,stopOpacity:`0`})]})}),(0,I.jsx)(`path`,{d:`M 0 90 Q 60 70 100 45 T 200 30 T 300 15 T 400 10 L 400 120 L 0 120 Z`,fill:`url(#chartGrad)`}),(0,I.jsx)(`path`,{d:`M 0 90 Q 60 70 100 45 T 200 30 T 300 15 T 400 10`,fill:`none`,stroke:`#ffffff`,strokeWidth:`2.5`}),(0,I.jsx)(`circle`,{cx:`400`,cy:`10`,r:`4`,fill:`#ffffff`})]})}),(0,I.jsxs)(`div`,{className:`dash-footer-metrics`,children:[(0,I.jsxs)(`div`,{className:`dash-metric-item`,children:[(0,I.jsx)(`span`,{className:`m-title`,children:`Throughput`}),(0,I.jsx)(`span`,{className:`m-val`,children:`12 500 TPS`})]}),(0,I.jsxs)(`div`,{className:`dash-metric-item`,children:[(0,I.jsx)(`span`,{className:`m-title`,children:`DB Connections`}),(0,I.jsx)(`span`,{className:`m-val`,children:`28 / 30 active`})]}),(0,I.jsxs)(`div`,{className:`dash-metric-item`,children:[(0,I.jsx)(`span`,{className:`m-title`,children:`Exceptions`}),(0,I.jsx)(`span`,{className:`m-val text-emerald`,children:`0 unhandled`})]})]})]})]})]}),(0,I.jsx)(`style`,{children:`
        .features-section {
          padding: 80px 0 100px;
          position: relative;
        }
        .text-center {
          text-align: center;
        }
        .features-head {
          max-width: 680px;
          margin: 0 auto 50px;
        }
        .features-title {
          font-size: 2.8rem;
          margin-top: 18px;
          margin-bottom: 16px;
          line-height: 1.15;
        }
        .features-sub {
          font-size: 1.05rem;
          color: var(--text-secondary);
        }
        .feature-cards-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 24px;
          margin-bottom: 100px;
        }
        .feature-card {
          padding: 36px 30px;
        }
        .card-heading {
          font-size: 1.25rem;
          margin-bottom: 12px;
          color: #ffffff;
        }
        .card-paragraph {
          font-size: 0.92rem;
          color: var(--text-secondary);
          line-height: 1.6;
        }

        /* Split Rows */
        .split-feature-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 60px;
          align-items: center;
          margin-bottom: 110px;
        }
        .stacked-items {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .mini-item-card {
          display: flex;
          align-items: center;
          gap: 20px;
          padding: 22px 26px;
        }
        .mini-icon-wrap {
          width: 44px;
          height: 44px;
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid var(--border-subtle);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          color: #ffffff;
        }
        .mini-title {
          font-size: 1.05rem;
          margin-bottom: 4px;
          color: #ffffff;
        }
        .mini-desc {
          font-size: 0.88rem;
          color: var(--text-secondary);
        }
        .split-text-content {
          padding: 10px 0;
        }
        .split-headline {
          font-size: 2.6rem;
          margin-top: 18px;
          margin-bottom: 18px;
          line-height: 1.2;
        }
        .split-desc {
          font-size: 1.05rem;
          color: var(--text-secondary);
          line-height: 1.65;
          margin-bottom: 28px;
        }
        .split-proof-strip {
          display: flex;
          align-items: center;
          gap: 24px;
        }
        .avatar-proof {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .avatar-group {
          display: flex;
        }
        .avatar-circle {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: #181c26;
          border: 2px solid #000000;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.65rem;
          font-weight: 700;
          color: var(--text-secondary);
          margin-left: -8px;
        }
        .avatar-circle:first-child {
          margin-left: 0;
        }
        .avatar-proof-text {
          font-size: 0.82rem;
          color: var(--text-secondary);
          font-weight: 500;
        }

        /* Dashboard Preview Card */
        .dashboard-preview-card {
          padding: 32px;
        }
        .dash-head {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 24px;
        }
        .dash-label {
          font-size: 0.8rem;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .dash-metric {
          font-family: var(--font-display);
          font-size: 2rem;
          font-weight: 800;
          color: #ffffff;
          margin-top: 4px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .dash-delta {
          font-size: 0.85rem;
          color: var(--accent-emerald);
          font-family: var(--font-body);
          font-weight: 600;
        }
        .dash-badge {
          padding: 4px 10px;
          background: rgba(16, 185, 129, 0.1);
          border: 1px solid rgba(16, 185, 129, 0.3);
          border-radius: 9999px;
          color: var(--accent-emerald);
          font-size: 0.75rem;
          font-family: var(--font-mono);
        }
        .dash-chart-wrap {
          margin: 10px 0 24px;
        }
        .dash-chart-svg {
          width: 100%;
          height: 100px;
        }
        .dash-footer-metrics {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 16px;
          padding-top: 20px;
          border-top: 1px solid var(--border-subtle);
        }
        .dash-metric-item {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .m-title {
          font-size: 0.75rem;
          color: var(--text-muted);
        }
        .m-val {
          font-size: 0.9rem;
          font-weight: 600;
          font-family: var(--font-mono);
          color: #ffffff;
        }
        .text-emerald {
          color: var(--accent-emerald);
        }

        @media (max-width: 960px) {
          .feature-cards-grid {
            grid-template-columns: 1fr;
          }
          .split-feature-row {
            grid-template-columns: 1fr;
            gap: 40px;
          }
          .split-feature-row.reverse {
            display: flex;
            flex-direction: column-reverse;
          }
          .features-title {
            font-size: 2.2rem;
          }
          .split-headline {
            font-size: 2rem;
          }
        }
      `})]})}var V=[{name:`FastAPI`,icon:p,angle:0,distance:130},{name:`PostgreSQL`,icon:f,angle:60,distance:130},{name:`Redis`,icon:C,angle:120,distance:130},{name:`Cloudflare`,icon:j,angle:180,distance:130},{name:`Telegram CRM`,icon:x,angle:240,distance:130},{name:`Docker`,icon:M,angle:300,distance:130}];function H(){return(0,I.jsxs)(`section`,{className:`integrations-section`,id:`integrations`,children:[(0,I.jsxs)(`div`,{className:`container`,children:[(0,I.jsxs)(`div`,{className:`integrations-head text-center`,children:[(0,I.jsxs)(`div`,{className:`badge-capsule`,children:[(0,I.jsx)(`span`,{className:`badge-icon`,children:`⚡`}),(0,I.jsx)(`span`,{children:`INTEGRATIONS`})]}),(0,I.jsxs)(`h2`,{className:`integrations-title`,children:[`Seamless integration `,(0,I.jsx)(`br`,{}),`for enhanced efficiency`]}),(0,I.jsx)(`p`,{className:`integrations-sub`,children:`Синхронизация с вашей экосистемой: корпоративные базы данных, платежные шлюзы, 1C и шифрованные каналы оповещений.`})]}),(0,I.jsxs)(`div`,{className:`orbit-container`,children:[(0,I.jsx)(`div`,{className:`orbit-ring ring-3`}),(0,I.jsx)(`div`,{className:`orbit-ring ring-2`}),(0,I.jsx)(`div`,{className:`orbit-ring ring-1`}),(0,I.jsxs)(`div`,{className:`orbit-core`,children:[(0,I.jsx)(w,{size:28,className:`core-icon`}),(0,I.jsx)(`div`,{className:`core-glow`})]}),V.map((e,t)=>{let n=e.icon,r=e.angle*Math.PI/180,i=Math.round(Math.cos(r)*e.distance),a=Math.round(Math.sin(r)*e.distance);return(0,I.jsxs)(`div`,{className:`orbit-node`,style:{transform:`translate(${i}px, ${a}px)`},title:e.name,children:[(0,I.jsx)(`div`,{className:`node-icon-box`,children:(0,I.jsx)(n,{size:18})}),(0,I.jsx)(`span`,{className:`node-label`,children:e.name})]},t)})]})]}),(0,I.jsx)(`style`,{children:`
        .integrations-section {
          padding: 80px 0 120px;
          position: relative;
          overflow: hidden;
        }
        .text-center {
          text-align: center;
        }
        .integrations-head {
          max-width: 660px;
          margin: 0 auto 60px;
        }
        .integrations-title {
          font-size: 2.8rem;
          margin-top: 18px;
          margin-bottom: 16px;
          line-height: 1.15;
        }
        .integrations-sub {
          font-size: 1.05rem;
          color: var(--text-secondary);
        }

        /* Orbit Radial Visual */
        .orbit-container {
          position: relative;
          width: 440px;
          height: 440px;
          margin: 0 auto;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .orbit-ring {
          position: absolute;
          border-radius: 50%;
          border: 1px dashed rgba(255, 255, 255, 0.12);
          pointer-events: none;
        }
        .ring-1 {
          width: 160px;
          height: 160px;
        }
        .ring-2 {
          width: 280px;
          height: 280px;
        }
        .ring-3 {
          width: 400px;
          height: 400px;
          border-style: solid;
          border-color: rgba(255, 255, 255, 0.05);
        }
        .orbit-core {
          width: 72px;
          height: 72px;
          border-radius: 50%;
          background: #ffffff;
          color: #000000;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          z-index: 10;
          box-shadow: 0 0 40px rgba(255, 255, 255, 0.4);
        }
        .core-glow {
          position: absolute;
          width: 140px;
          height: 140px;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(255, 255, 255, 0.15) 0%, transparent 70%);
          pointer-events: none;
        }
        .orbit-node {
          position: absolute;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
          z-index: 5;
          transition: transform 0.3s ease;
        }
        .node-icon-box {
          width: 44px;
          height: 44px;
          border-radius: 50%;
          background: #0e1118;
          border: 1px solid rgba(255, 255, 255, 0.18);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #ffffff;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.8);
          transition: all 0.2s ease;
        }
        .orbit-node:hover .node-icon-box {
          border-color: #ffffff;
          transform: scale(1.1);
          background: #181d28;
        }
        .node-label {
          font-size: 0.75rem;
          font-weight: 600;
          color: var(--text-secondary);
          background: rgba(0, 0, 0, 0.8);
          padding: 2px 8px;
          border-radius: 6px;
          white-space: nowrap;
        }

        @media (max-width: 640px) {
          .orbit-container {
            width: 320px;
            height: 320px;
            transform: scale(0.8);
          }
          .integrations-title {
            font-size: 2rem;
          }
        }
      `})]})}var U=[{id:1,title:`FinTrack AI — B2B платформа для финтеха`,category:`SAAS`,short_description:`Высоконагруженная система обработки финансовых транзакций в реальном времени с автоматической генерацией отчетности.`,problem:`Клиент терял пользователей из-за медленной отрисовки графиков при загрузке более 1 000 000 строк транзакций.`,solution_fe:`Виртуализированный Canvas/WebGL рендеринг графиков, кэширование на клиенте через IndexedDB, мгновенный отклик.`,solution_be:`Асинхронный бэкенд на FastAPI с пулом asyncpg, шардирование таблиц PostgreSQL, L2 кэш Redis.`,metrics:{speed_up:`75x быстрее`,tps_handled:`12 500 TPS`,latency_p99:`180ms`},cover_image:`/case1.jpg`,author:`Александр Воронов`,author_role:`Lead Architect`},{id:2,title:`Vanguard Living — Премиальный 3D E-commerce`,category:`ECOMMERCE 3D`,short_description:`E-commerce платформа с интерактивным конфигурированием материалов в реальном времени и синхронизацией с 1С.`,problem:`Старый сайт зависал при одновременном открытии 3D-моделей на мобильных устройствах и не справлялся с 5 000 SKU.`,solution_fe:`Гидратация Three.js компонентов только при попадании во вьюпорт, мгновенный поиск с автодополнением.`,solution_be:`Каталог на PostgreSQL с полнотекстовым поиском, фоновая синхронизация с 1C через очереди сообщений.`,metrics:{lighthouse:`97/100`,conversion:`+68%`,sync_speed:`1.2s`},cover_image:`/case2.jpg`,author:`Елена Романова`,author_role:`Creative Director`},{id:3,title:`CyberShield — Центр мониторинга киберинцидентов`,category:`HIGHLOAD`,short_description:`Внутренний портал мониторинга сетевых аномалий и DDoS-атак для аналитиков информационной безопасности.`,problem:`Разрозненные инструменты мониторинга не позволяли оперативно реагировать на всплески трафика.`,solution_fe:`Интерфейс высокой информационной плотности с WebSocket-стримингом событий в реальном времени.`,solution_be:`FastAPI с Redis Pub/Sub шиной данных, асинхронный консьюмер сетевых логов, интеграция с Telegram.`,metrics:{mttr:`-94%`,throughput:`50K msg/sec`,uptime:`100%`},cover_image:`/case3.jpg`,author:`Михаил Краснов`,author_role:`Head of Security`}];function W(){let[e,n]=(0,P.useState)(U),[r,i]=(0,P.useState)(null);return(0,P.useEffect)(()=>{(async()=>{try{let e=await fetch(`/api/v1/cases`);if(e.ok){let t=await e.json();Array.isArray(t)&&t.length>=3&&n(t.map((e,t)=>({...e,cover_image:`/case${t%3+1}.jpg`,author:e.client_author||`Lead Architect`,author_role:`CASTLEWEB Studio`})))}}catch{}})()},[]),(0,I.jsxs)(`section`,{className:`cases-section`,id:`cases`,children:[(0,I.jsxs)(`div`,{className:`container`,children:[(0,I.jsxs)(`div`,{className:`cases-head text-center`,children:[(0,I.jsxs)(`div`,{className:`badge-capsule`,children:[(0,I.jsx)(`span`,{className:`badge-icon`,children:`✦`}),(0,I.jsx)(`span`,{children:`PORTFOLIO & CASES`})]}),(0,I.jsx)(`h2`,{className:`cases-title`,children:`Read our most recent projects`}),(0,I.jsx)(`p`,{className:`cases-sub`,children:`Архитектурные разборы проектов, которые работают под реальной нагрузкой в продакшне.`})]}),(0,I.jsx)(`div`,{className:`cases-grid`,children:e.slice(0,3).map(e=>(0,I.jsxs)(`div`,{className:`dark-card case-card`,onClick:()=>i(e),children:[(0,I.jsxs)(`div`,{className:`case-img-box`,children:[(0,I.jsx)(`img`,{src:e.cover_image,alt:e.title,className:`case-img`}),(0,I.jsx)(`div`,{className:`case-arrow-btn`,children:(0,I.jsx)(t,{size:18})})]}),(0,I.jsxs)(`div`,{className:`case-body`,children:[(0,I.jsx)(`span`,{className:`case-category-pill`,children:e.category}),(0,I.jsx)(`h3`,{className:`case-card-title`,children:e.title}),(0,I.jsx)(`p`,{className:`case-card-desc`,children:e.short_description}),(0,I.jsxs)(`div`,{className:`case-author-strip`,children:[(0,I.jsx)(`div`,{className:`author-avatar-circ`,children:e.author.charAt(0)}),(0,I.jsxs)(`div`,{children:[(0,I.jsx)(`span`,{className:`author-name`,children:e.author}),(0,I.jsx)(`span`,{className:`author-role`,children:e.author_role})]})]})]})]},e.id))}),r&&(0,I.jsx)(`div`,{className:`case-modal-backdrop`,onClick:()=>i(null),children:(0,I.jsxs)(`div`,{className:`case-modal-box dark-card`,onClick:e=>e.stopPropagation(),children:[(0,I.jsx)(`button`,{className:`case-modal-close`,onClick:()=>i(null),children:(0,I.jsx)(E,{size:20})}),(0,I.jsxs)(`div`,{className:`modal-head`,children:[(0,I.jsx)(`span`,{className:`case-category-pill`,children:r.category}),(0,I.jsx)(`h2`,{className:`modal-title`,children:r.title})]}),(0,I.jsxs)(`div`,{className:`modal-grid`,children:[(0,I.jsxs)(`div`,{className:`modal-section`,children:[(0,I.jsx)(`h4`,{className:`modal-sub`,children:`Проблема и вызов:`}),(0,I.jsx)(`p`,{children:r.problem})]}),(0,I.jsxs)(`div`,{className:`modal-section`,children:[(0,I.jsx)(`h4`,{className:`modal-sub`,children:`Инженерное решение (Frontend):`}),(0,I.jsx)(`p`,{children:r.solution_fe})]}),(0,I.jsxs)(`div`,{className:`modal-section`,children:[(0,I.jsx)(`h4`,{className:`modal-sub`,children:`Инженерное решение (Backend):`}),(0,I.jsx)(`p`,{children:r.solution_be})]})]}),r.metrics&&(0,I.jsx)(`div`,{className:`modal-metrics-strip`,children:Object.entries(r.metrics).map(([e,t])=>(0,I.jsxs)(`div`,{className:`metric-pill`,children:[(0,I.jsxs)(`span`,{className:`metric-key`,children:[e,`:`]}),(0,I.jsx)(`span`,{className:`metric-val`,children:t})]},e))})]})})]}),(0,I.jsx)(`style`,{children:`
        .cases-section {
          padding: 80px 0 110px;
          position: relative;
        }
        .text-center {
          text-align: center;
        }
        .cases-head {
          max-width: 660px;
          margin: 0 auto 50px;
        }
        .cases-title {
          font-size: 2.8rem;
          margin-top: 18px;
          margin-bottom: 16px;
        }
        .cases-sub {
          font-size: 1.05rem;
          color: var(--text-secondary);
        }
        .cases-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 24px;
        }
        .case-card {
          padding: 16px;
          cursor: pointer;
        }
        .case-img-box {
          position: relative;
          width: 100%;
          height: 220px;
          border-radius: 14px;
          overflow: hidden;
          margin-bottom: 20px;
          background: #000000;
        }
        .case-img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          transition: transform 0.4s ease;
        }
        .case-card:hover .case-img {
          transform: scale(1.05);
        }
        .case-arrow-btn {
          position: absolute;
          top: 14px;
          right: 14px;
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: rgba(0, 0, 0, 0.6);
          border: 1px solid rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #ffffff;
          backdrop-filter: blur(8px);
          transition: all 0.2s ease;
        }
        .case-card:hover .case-arrow-btn {
          background: #ffffff;
          color: #000000;
          transform: rotate(45deg);
        }
        .case-body {
          padding: 6px 8px 12px;
        }
        .case-category-pill {
          display: inline-block;
          font-size: 0.72rem;
          font-weight: 700;
          color: var(--accent-emerald);
          text-transform: uppercase;
          letter-spacing: 0.08em;
          margin-bottom: 10px;
        }
        .case-card-title {
          font-size: 1.15rem;
          line-height: 1.4;
          margin-bottom: 10px;
          color: #ffffff;
        }
        .case-card-desc {
          font-size: 0.88rem;
          color: var(--text-secondary);
          line-height: 1.55;
          margin-bottom: 20px;
        }
        .case-author-strip {
          display: flex;
          align-items: center;
          gap: 12px;
          padding-top: 16px;
          border-top: 1px solid var(--border-subtle);
        }
        .author-avatar-circ {
          width: 34px;
          height: 34px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid var(--border-subtle);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 0.85rem;
          color: #ffffff;
        }
        .author-name {
          display: block;
          font-size: 0.85rem;
          font-weight: 600;
          color: #ffffff;
        }
        .author-role {
          display: block;
          font-size: 0.75rem;
          color: var(--text-muted);
        }

        /* Modal */
        .case-modal-backdrop {
          position: fixed;
          top: 0;
          left: 0;
          width: 100vw;
          height: 100vh;
          background: rgba(0, 0, 0, 0.85);
          backdrop-filter: blur(14px);
          z-index: 1000;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }
        .case-modal-box {
          max-width: 680px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
          position: relative;
          padding: 40px;
        }
        .case-modal-close {
          position: absolute;
          top: 20px;
          right: 20px;
          color: var(--text-secondary);
          transition: color 0.2s;
        }
        .case-modal-close:hover {
          color: #ffffff;
        }
        .modal-title {
          font-size: 1.8rem;
          margin: 10px 0 24px;
        }
        .modal-grid {
          display: flex;
          flex-direction: column;
          gap: 18px;
          margin-bottom: 24px;
        }
        .modal-sub {
          font-size: 0.95rem;
          color: #ffffff;
          margin-bottom: 6px;
        }
        .modal-metrics-strip {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          padding-top: 20px;
          border-top: 1px solid var(--border-subtle);
        }
        .metric-pill {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid var(--border-subtle);
          padding: 6px 12px;
          border-radius: 8px;
          font-size: 0.8rem;
          font-family: var(--font-mono);
        }
        .metric-val {
          color: var(--accent-emerald);
          font-weight: 600;
          margin-left: 6px;
        }

        @media (max-width: 960px) {
          .cases-grid {
            grid-template-columns: 1fr;
          }
        }
      `})]})}var G=[{id:`mvp`,name:`MVP Sprint`,price:`180 000 ₽`,days:`14 дней`,desc:`Быстрый запуск продукта для проверки гипотез на рынке с чистой архитектурой.`,features:[`React 19 + FastAPI ядро`,`PostgreSQL 16 база данных`,`Telegram CRM оповещения`,`Базовый WAF & SSL`]},{id:`saas`,name:`SaaS Platform`,badge:`ПОПУЛЯРНЫЙ ВЫБОР`,price:`340 000 ₽`,days:`30 дней`,desc:`Полнофункциональная платформа с личными кабинетами, биллингом и L2 кэшем.`,features:[`Всё из MVP Sprint`,`Redis 7 высокоскоростной кэш`,`Прием платежей / подписки`,`Cloudflare R2 хранилище`,`SLA 99.98% гарантия`]},{id:`enterprise`,name:`Highload & 3D Web`,price:`580 000 ₽`,days:`45 дней`,desc:`Премиальные решения с миллионной пропускной способностью и 3D WebGL интерфейсами.`,features:[`Всё из SaaS Platform`,`Интерактивный 3D WebGL / Three.js`,`Шардирование PostgreSQL`,`Очереди брокеров сообщений`,`Выделенный Lead Architect`]}],K=[{id:`tg_bot`,name:`Telegram Headless CRM`,price:35e3,desc:`Управление лидами в закрытом чате команды (0 ₽/мес)`},{id:`redis`,name:`Redis Highload кэширование`,price:25e3,desc:`Снижение нагрузки на базу и отклик < 40ms`},{id:`payments`,name:`Платежный шлюз (ЮKassa / Crypto)`,price:3e4,desc:`Прием платежей, чеки, рекуррентные подписки`},{id:`r2`,name:`Cloudflare R2 S3 хранилище`,price:2e4,desc:`Раздача файлов и фото с 0 ₽ за исходящий трафик`}];function q({onApplyConfig:e}){let[t,n]=(0,P.useState)(`saas`),[r,i]=(0,P.useState)([`tg_bot`,`redis`]),a=e=>{i(t=>t.includes(e)?t.filter(t=>t!==e):[...t,e])},o=G.find(e=>e.id===t)||G[1],c=()=>{let t=r.map(e=>K.find(t=>t.id===e)?.name).filter(Boolean).join(`, `);e({summary:`План: ${o.name} (${o.price})\nСрок реализации: ~${o.days}\nДополнительные модули: ${t||`Базовые`}`,budget:o.price,projectType:o.name})};return(0,I.jsxs)(`section`,{className:`calc-section`,id:`calculator`,children:[(0,I.jsxs)(`div`,{className:`container`,children:[(0,I.jsxs)(`div`,{className:`calc-head text-center`,children:[(0,I.jsxs)(`div`,{className:`badge-capsule`,children:[(0,I.jsx)(`span`,{className:`badge-icon`,children:`✦`}),(0,I.jsx)(`span`,{children:`PRICING & ESTIMATOR`})]}),(0,I.jsx)(`h2`,{className:`calc-title`,children:`Choose your plan & scope`}),(0,I.jsx)(`p`,{className:`calc-sub`,children:`Прозрачная стоимость этапов разработки без скрытых переплат и комиссий.`})]}),(0,I.jsx)(`div`,{className:`tiers-grid`,children:G.map(e=>{let r=t===e.id;return(0,I.jsxs)(`div`,{className:`dark-card tier-card ${r?`selected`:``}`,onClick:()=>n(e.id),children:[e.badge&&(0,I.jsx)(`div`,{className:`tier-popular-badge`,children:e.badge}),(0,I.jsx)(`h3`,{className:`tier-name`,children:e.name}),(0,I.jsxs)(`div`,{className:`tier-price-row`,children:[(0,I.jsx)(`span`,{className:`tier-price`,children:e.price}),(0,I.jsxs)(`span`,{className:`tier-days`,children:[`/ ~`,e.days]})]}),(0,I.jsx)(`p`,{className:`tier-desc`,children:e.desc}),(0,I.jsx)(`div`,{className:`tier-features-list`,children:e.features.map((e,t)=>(0,I.jsxs)(`div`,{className:`tier-feature-item`,children:[(0,I.jsx)(`div`,{className:`feat-check`,children:(0,I.jsx)(s,{size:13})}),(0,I.jsx)(`span`,{children:e})]},t))}),(0,I.jsxs)(`button`,{className:`tier-btn ${r?`btn-primary`:`btn-secondary`} w-full`,onClick:t=>{t.stopPropagation(),n(e.id),c()},children:[(0,I.jsx)(`span`,{children:r?`Выбрать этот план`:`Выбрать`}),(0,I.jsx)(y,{size:14})]})]},e.id)})}),(0,I.jsxs)(`div`,{className:`addons-card dark-card`,children:[(0,I.jsxs)(`div`,{className:`addons-head`,children:[(0,I.jsx)(`h4`,{className:`addons-title`,children:`Дополнительные архитектурные модули:`}),(0,I.jsx)(`span`,{className:`addons-sub`,children:`Кастомизируйте конфигурацию под ваши требования`})]}),(0,I.jsx)(`div`,{className:`addons-grid`,children:K.map(e=>{let t=r.includes(e.id);return(0,I.jsxs)(`div`,{className:`addon-chip ${t?`checked`:``}`,onClick:()=>a(e.id),children:[(0,I.jsx)(`div`,{className:`addon-checkbox ${t?`active`:``}`,children:t&&(0,I.jsx)(s,{size:12})}),(0,I.jsxs)(`div`,{children:[(0,I.jsx)(`span`,{className:`addon-name`,children:e.name}),(0,I.jsxs)(`span`,{className:`addon-price`,children:[`+`,e.price.toLocaleString(`ru-RU`),` ₽`]})]})]},e.id)})}),(0,I.jsx)(`div`,{className:`addons-footer`,children:(0,I.jsxs)(`button`,{className:`btn-primary`,onClick:c,id:`calc-transfer-btn`,children:[(0,I.jsx)(`span`,{children:`Перенести смету в заявку`}),(0,I.jsx)(y,{size:16})]})})]})]}),(0,I.jsx)(`style`,{children:`
        .calc-section {
          padding: 80px 0 100px;
          position: relative;
        }
        .text-center {
          text-align: center;
        }
        .calc-head {
          max-width: 660px;
          margin: 0 auto 50px;
        }
        .calc-title {
          font-size: 2.8rem;
          margin-top: 18px;
          margin-bottom: 16px;
        }
        .calc-sub {
          font-size: 1.05rem;
          color: var(--text-secondary);
        }

        /* 3 Tier Grid */
        .tiers-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 24px;
          margin-bottom: 40px;
        }
        .tier-card {
          padding: 34px 28px;
          display: flex;
          flex-direction: column;
          cursor: pointer;
          position: relative;
        }
        .tier-card.selected {
          border-color: rgba(255, 255, 255, 0.4);
          box-shadow: 0 0 30px rgba(255, 255, 255, 0.1);
          background: #10131b;
        }
        .tier-popular-badge {
          position: absolute;
          top: 18px;
          right: 20px;
          background: #ffffff;
          color: #000000;
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.08em;
          padding: 4px 10px;
          border-radius: 9999px;
        }
        .tier-name {
          font-size: 1.3rem;
          margin-bottom: 14px;
          color: #ffffff;
        }
        .tier-price-row {
          display: flex;
          align-items: baseline;
          gap: 8px;
          margin-bottom: 14px;
        }
        .tier-price {
          font-family: var(--font-display);
          font-size: 2.2rem;
          font-weight: 800;
          color: #ffffff;
        }
        .tier-days {
          font-size: 0.85rem;
          color: var(--text-muted);
        }
        .tier-desc {
          font-size: 0.88rem;
          color: var(--text-secondary);
          line-height: 1.5;
          margin-bottom: 24px;
          min-height: 42px;
        }
        .tier-features-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-bottom: 30px;
          flex-grow: 1;
        }
        .tier-feature-item {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 0.85rem;
          color: var(--text-secondary);
        }
        .feat-check {
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.1);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          color: #ffffff;
        }
        .tier-btn {
          width: 100%;
        }

        /* Addons Card */
        .addons-card {
          padding: 30px;
        }
        .addons-head {
          margin-bottom: 20px;
        }
        .addons-title {
          font-size: 1.15rem;
          color: #ffffff;
          margin-bottom: 4px;
        }
        .addons-sub {
          font-size: 0.85rem;
          color: var(--text-muted);
        }
        .addons-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 14px;
          margin-bottom: 24px;
        }
        .addon-chip {
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 14px 18px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid var(--border-subtle);
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.2s;
        }
        .addon-chip:hover {
          background: rgba(255, 255, 255, 0.06);
        }
        .addon-chip.checked {
          border-color: rgba(255, 255, 255, 0.3);
          background: rgba(255, 255, 255, 0.08);
        }
        .addon-checkbox {
          width: 20px;
          height: 20px;
          border-radius: 6px;
          border: 1px solid rgba(255, 255, 255, 0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          color: #000000;
        }
        .addon-checkbox.active {
          background: #ffffff;
          border-color: #ffffff;
        }
        .addon-name {
          display: block;
          font-size: 0.9rem;
          font-weight: 600;
          color: #ffffff;
        }
        .addon-price {
          font-size: 0.75rem;
          color: var(--accent-emerald);
          font-family: var(--font-mono);
        }
        .addons-footer {
          display: flex;
          justify-content: flex-end;
          padding-top: 16px;
          border-top: 1px solid var(--border-subtle);
        }
        .w-full {
          width: 100%;
        }

        @media (max-width: 960px) {
          .tiers-grid {
            grid-template-columns: 1fr;
          }
          .addons-grid {
            grid-template-columns: 1fr;
          }
        }
      `})]})}var J=[{id:`presentation`,name:`1. Presentation Layer (API & Gateway)`,icon:p,color:`#06b6d4`,desc:`Чистые контроллеры FastAPI, валидация входных данных через Pydantic v2, Swagger/OpenAPI спецификация.`,points:[`Асинхронные роуты без блокировки event loop`,`Встроенный Token Bucket Rate Limiter (защита от спама и парсеров)`,`Автоматическая генерация клиентских SDK через OpenAPI`]},{id:`domain`,name:`2. Domain & Application Core`,icon:u,color:`#8b5cf6`,desc:`Бизнес-логика, изолированная от фреймворков и баз данных. Чистые сущности и DTO.`,points:[`Полная тестируемость (Unit тесты выполняются за миллисекунды)`,`Строгая типизация Python 3.12 (mypy strict)`,`Независимость от поставщиков сторонних решений`]},{id:`infrastructure`,name:`3. Infrastructure & Highload Cache`,icon:f,color:`#10b981`,desc:`Высокоскоростная персистентность на PostgreSQL 16 + Redis 7 L2 кэш.`,points:[`Пул неблокирующих соединений asyncpg (до 15 000 RPS)`,`Асинхронные миграции БД через Alembic с версионированием`,`Redis LRU кэширование горячих выборок с субмиллисекундным пингом`]},{id:`crm`,name:`4. Telegram Headless CRM & Storage`,icon:x,color:`#ec4899`,desc:`Управление лидами прямо в защищенном Telegram-чате команды с нулевой стоимостью лицензий.`,points:[`Асинхронный воркер доставки заявок с автоповторами (exponential backoff)`,`Интерактивные Inline-кнопки для смены статусов (В работе / Завершено)`,`Cloudflare R2 хранилище ТЗ и файлов с 0 ₽ за исходящий трафик`]}],Y=[{metric:`Месячные расходы на SaaS/CRM`,studio:`0 ₽ / мес`,others:`от 12 000 ₽ / мес (Битрикс24 / AmoCRM)`,benefit:`Telegram CRM без абонентской платы`},{metric:`Раздача файлов и медиа (CDN)`,studio:`0 ₽ (Cloudflare R2, 0 egress fee)`,others:`от 3 000 ₽ / мес за каждый терабайт`,benefit:`Бесплатный исходящий трафик`},{metric:`Время холодного старта API`,studio:`< 80 ms (FastAPI + Uvicorn)`,others:`1 500 — 3 000 ms (тяжелые CMS/Django)`,benefit:`Мгновенный отклик для пользователей`},{metric:`Владение кодом и развертывание`,studio:`100% On-Premise Docker на вашем сервере`,others:`Привязка к закрытым конструкторам`,benefit:`Никакой блокировки или привязки`}];function X(){let[e,t]=(0,P.useState)(`presentation`);return(0,I.jsxs)(`section`,{className:`arch-section`,id:`architecture`,children:[(0,I.jsxs)(`div`,{className:`container`,children:[(0,I.jsxs)(`div`,{className:`section-head text-center`,children:[(0,I.jsx)(`div`,{className:`badge badge-glow`,children:`ИНЖЕНЕРНАЯ ФИЛОСОФИЯ`}),(0,I.jsxs)(`h2`,{className:`section-title`,children:[`Архитектура, созданная для `,(0,I.jsx)(`span`,{className:`gradient-text`,children:`Highload & 0 ₽ издержек`})]}),(0,I.jsx)(`p`,{className:`section-desc`,children:`Никаких перегруженных конструкторов или раздутых подписок. Только чистый код, асинхронные микросервисы и серверные технологии мирового класса.`})]}),(0,I.jsxs)(`div`,{className:`arch-interactive-box glass-card`,children:[(0,I.jsx)(`div`,{className:`arch-tabs-nav`,children:J.map(n=>{let r=n.icon,i=e===n.id;return(0,I.jsxs)(`button`,{onClick:()=>t(n.id),className:`arch-tab-btn ${i?`active`:``}`,style:{"--tab-color":n.color},children:[(0,I.jsx)(r,{size:18}),(0,I.jsx)(`span`,{children:n.name.split(` (`)[0]})]},n.id)})}),(0,I.jsx)(`div`,{className:`arch-tab-content`,children:J.map(t=>{if(t.id!==e)return null;let n=t.icon;return(0,I.jsxs)(`div`,{className:`arch-detail-card`,children:[(0,I.jsxs)(`div`,{className:`arch-detail-header`,children:[(0,I.jsx)(`div`,{className:`arch-icon-wrap`,style:{background:`${t.color}15`,borderColor:`${t.color}40`,color:t.color},children:(0,I.jsx)(n,{size:26})}),(0,I.jsxs)(`div`,{children:[(0,I.jsx)(`h3`,{className:`arch-layer-title`,children:t.name}),(0,I.jsx)(`p`,{className:`arch-layer-desc`,children:t.desc})]})]}),(0,I.jsx)(`div`,{className:`arch-points-grid`,children:t.points.map((e,n)=>(0,I.jsxs)(`div`,{className:`arch-point-item`,children:[(0,I.jsx)(i,{size:16,style:{color:t.color},className:`point-icon`}),(0,I.jsx)(`span`,{children:e})]},n))})]},t.id)})})]}),(0,I.jsxs)(`div`,{className:`comparison-wrap`,children:[(0,I.jsxs)(`h3`,{className:`comparison-title text-center`,children:[`Экономика проекта: `,(0,I.jsx)(`span`,{className:`gradient-text-cyan`,children:`CASTLEWEB vs Типовые веб-студии`})]}),(0,I.jsxs)(`div`,{className:`comparison-table-card glass-card`,children:[(0,I.jsxs)(`div`,{className:`table-header-row`,children:[(0,I.jsx)(`div`,{className:`th-cell th-metric`,children:`Параметр архитектуры`}),(0,I.jsx)(`div`,{className:`th-cell th-studio`,children:`CASTLEWEB Architecture`}),(0,I.jsx)(`div`,{className:`th-cell th-others`,children:`Обычные студии / CMS`}),(0,I.jsx)(`div`,{className:`th-cell th-benefit`,children:`Ваша выгода`})]}),(0,I.jsx)(`div`,{className:`table-body`,children:Y.map((e,t)=>(0,I.jsxs)(`div`,{className:`table-row`,children:[(0,I.jsx)(`div`,{className:`td-cell td-metric`,children:(0,I.jsx)(`strong`,{children:e.metric})}),(0,I.jsx)(`div`,{className:`td-cell td-studio`,children:(0,I.jsx)(`span`,{className:`badge-highlight-green`,children:e.studio})}),(0,I.jsx)(`div`,{className:`td-cell td-others`,children:(0,I.jsx)(`span`,{className:`text-muted`,children:e.others})}),(0,I.jsx)(`div`,{className:`td-cell td-benefit`,children:(0,I.jsxs)(`span`,{className:`text-benefit`,children:[(0,I.jsx)(C,{size:13,className:`inline-icon text-cyan`}),` `,e.benefit]})})]},t))})]})]}),(0,I.jsxs)(`div`,{className:`stack-grid`,children:[(0,I.jsxs)(`div`,{className:`stack-card glass-card`,children:[(0,I.jsxs)(`div`,{className:`stack-head`,children:[(0,I.jsx)(p,{size:20,className:`text-cyan`}),(0,I.jsx)(`h4`,{children:`Backend & Data`})]}),(0,I.jsx)(`p`,{className:`stack-desc`,children:`Python 3.12, FastAPI, SQLAlchemy 2.0 Async, PostgreSQL 16, Redis 7, Alembic`}),(0,I.jsxs)(`div`,{className:`stack-tags`,children:[(0,I.jsx)(`span`,{className:`tag`,children:`FastAPI`}),(0,I.jsx)(`span`,{className:`tag`,children:`PostgreSQL 16`}),(0,I.jsx)(`span`,{className:`tag`,children:`Redis 7`}),(0,I.jsx)(`span`,{className:`tag`,children:`Pydantic v2`}),(0,I.jsx)(`span`,{className:`tag`,children:`Asyncpg`})]})]}),(0,I.jsxs)(`div`,{className:`stack-card glass-card`,children:[(0,I.jsxs)(`div`,{className:`stack-head`,children:[(0,I.jsx)(c,{size:20,className:`text-indigo`}),(0,I.jsx)(`h4`,{children:`Frontend & 3D Web`})]}),(0,I.jsx)(`p`,{className:`stack-desc`,children:`React 19, Vite, Three.js / WebGL, CSS Design Tokens, Lucide Icons, Vanilla Architecture`}),(0,I.jsxs)(`div`,{className:`stack-tags`,children:[(0,I.jsx)(`span`,{className:`tag`,children:`React 19`}),(0,I.jsx)(`span`,{className:`tag`,children:`Vite 6`}),(0,I.jsx)(`span`,{className:`tag`,children:`Three.js`}),(0,I.jsx)(`span`,{className:`tag`,children:`Vanilla CSS`}),(0,I.jsx)(`span`,{className:`tag`,children:`Lighthouse 95+`})]})]}),(0,I.jsxs)(`div`,{className:`stack-card glass-card`,children:[(0,I.jsxs)(`div`,{className:`stack-head`,children:[(0,I.jsx)(D,{size:20,className:`text-emerald`}),(0,I.jsx)(`h4`,{children:`DevOps, WAF & Storage`})]}),(0,I.jsx)(`p`,{className:`stack-desc`,children:`Docker Compose, Nginx, Certbot SSL, Cloudflare Turnstile & R2, Telegram Bot API`}),(0,I.jsxs)(`div`,{className:`stack-tags`,children:[(0,I.jsx)(`span`,{className:`tag`,children:`Docker`}),(0,I.jsx)(`span`,{className:`tag`,children:`Nginx`}),(0,I.jsx)(`span`,{className:`tag`,children:`Cloudflare R2`}),(0,I.jsx)(`span`,{className:`tag`,children:`Telegram API`}),(0,I.jsx)(`span`,{className:`tag`,children:`Certbot SSL`})]})]})]})]}),(0,I.jsx)(`style`,{children:`
        .arch-section {
          padding: 100px 0;
          position: relative;
        }
        .text-center {
          text-align: center;
        }
        .section-head {
          max-width: 760px;
          margin: 0 auto 50px;
        }
        .section-title {
          font-size: 2.5rem;
          margin-top: 14px;
          margin-bottom: 16px;
        }
        .section-desc {
          font-size: 1.1rem;
          color: var(--text-secondary);
          line-height: 1.6;
        }
        .arch-interactive-box {
          padding: 30px;
          border-radius: 20px;
          margin-bottom: 70px;
          border: 1px solid var(--border-glow);
        }
        .arch-tabs-nav {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          margin-bottom: 28px;
          padding-bottom: 20px;
          border-bottom: 1px solid var(--border-subtle);
        }
        .arch-tab-btn {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 14px 18px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid var(--border-subtle);
          border-radius: 12px;
          color: var(--text-secondary);
          font-size: 0.9rem;
          font-weight: 600;
          text-align: left;
          transition: all var(--transition-fast);
        }
        .arch-tab-btn:hover {
          background: rgba(255, 255, 255, 0.06);
          color: #ffffff;
        }
        .arch-tab-btn.active {
          background: rgba(99, 102, 241, 0.15);
          border-color: var(--tab-color, var(--accent-indigo));
          color: #ffffff;
          box-shadow: 0 0 20px -5px rgba(99, 102, 241, 0.4);
        }
        .arch-tab-btn.active svg {
          color: var(--tab-color, var(--accent-indigo));
        }
        .arch-detail-header {
          display: flex;
          align-items: flex-start;
          gap: 20px;
          margin-bottom: 24px;
        }
        .arch-icon-wrap {
          width: 56px;
          height: 56px;
          border-radius: 14px;
          border: 1px solid;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .arch-layer-title {
          font-size: 1.4rem;
          margin-bottom: 6px;
        }
        .arch-layer-desc {
          font-size: 0.95rem;
          color: var(--text-secondary);
          line-height: 1.5;
        }
        .arch-points-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 16px;
        }
        .arch-point-item {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          padding: 14px 16px;
          background: rgba(8, 10, 16, 0.6);
          border: 1px solid var(--border-subtle);
          border-radius: 12px;
          font-size: 0.88rem;
          color: var(--text-primary);
          line-height: 1.4;
        }
        .point-icon {
          flex-shrink: 0;
          margin-top: 2px;
        }
        .comparison-wrap {
          margin-bottom: 70px;
        }
        .comparison-title {
          font-size: 1.8rem;
          margin-bottom: 30px;
        }
        .comparison-table-card {
          border-radius: 20px;
          overflow: hidden;
          border: 1px solid var(--border-subtle);
        }
        .table-header-row {
          display: grid;
          grid-template-columns: 1.4fr 1.2fr 1.4fr 1.2fr;
          padding: 16px 24px;
          background: rgba(14, 18, 28, 0.9);
          border-bottom: 1px solid var(--border-subtle);
          font-weight: 700;
          font-size: 0.85rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--text-muted);
        }
        .table-row {
          display: grid;
          grid-template-columns: 1.4fr 1.2fr 1.4fr 1.2fr;
          padding: 18px 24px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.04);
          align-items: center;
          font-size: 0.9rem;
          transition: background var(--transition-fast);
        }
        .table-row:last-child {
          border-bottom: none;
        }
        .table-row:hover {
          background: rgba(255, 255, 255, 0.02);
        }
        .badge-highlight-green {
          font-family: var(--font-mono);
          font-weight: 700;
          color: var(--accent-emerald);
          background: rgba(16, 185, 129, 0.12);
          border: 1px solid rgba(16, 185, 129, 0.3);
          padding: 4px 10px;
          border-radius: 8px;
          display: inline-block;
        }
        .text-benefit {
          color: var(--text-primary);
          font-weight: 500;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .stack-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 24px;
        }
        .stack-card {
          padding: 28px;
          border-radius: 18px;
          border: 1px solid var(--border-subtle);
          transition: transform var(--transition-fast), border-color var(--transition-fast);
        }
        .stack-card:hover {
          transform: translateY(-4px);
          border-color: var(--border-glow);
        }
        .stack-head {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 12px;
        }
        .stack-head h4 {
          font-size: 1.2rem;
          color: #ffffff;
        }
        .stack-desc {
          font-size: 0.88rem;
          color: var(--text-secondary);
          margin-bottom: 18px;
          line-height: 1.5;
        }
        .stack-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        .tag {
          font-size: 0.75rem;
          font-family: var(--font-mono);
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid var(--border-subtle);
          padding: 4px 10px;
          border-radius: 6px;
          color: var(--text-secondary);
        }
        .text-cyan { color: var(--accent-cyan); }
        .text-indigo { color: var(--accent-indigo); }
        .text-emerald { color: var(--accent-emerald); }

        @media (max-width: 1024px) {
          .arch-tabs-nav {
            grid-template-columns: repeat(2, 1fr);
          }
          .arch-points-grid {
            grid-template-columns: 1fr;
          }
          .table-header-row, .table-row {
            grid-template-columns: 1fr 1fr;
            gap: 12px;
          }
          .th-others, .td-others, .th-benefit, .td-benefit {
            display: none;
          }
          .stack-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 640px) {
          .arch-tabs-nav {
            grid-template-columns: 1fr;
          }
          .section-title {
            font-size: 1.8rem;
          }
          .arch-detail-header {
            flex-direction: column;
            gap: 14px;
          }
        }
      `})]})}var Z=[{q:`Как происходит разработка и сдача этапов по спринтам?`,a:`Мы работаем двухнедельными спринтами. В конце каждого спринта вы получаете осязаемый рабочий релиз на тестовом контуре (staging) с автоматическими тестами и демонстрацией функционала.`},{q:`Почему в вашей архитектуре 0 ₽ расходов на CRM и Cloudflare R2?`,a:`Мы исключаем лицензионные подписки на сторонние SaaS-системы: вместо amoCRM/Битрикс24 развертывается Telegram Headless CRM в закрытом канале команды, а Cloudflare R2 предоставляет 10 ГБ хранилища с нулевой стоимостью исходящего трафика.`},{q:`Кому принадлежат права на код и серверную инфраструктуру?`,a:`100% прав на исходный код, репозитории Git, Docker-образы и конфигурационные файлы передаются заказчику по договору сразу после завершения проекта. Никаких привязок к закрытым конструкторам.`},{q:`Какие гарантии производительности и SLA вы фиксируете?`,a:`Мы гарантируем Uptime 99.98% в SLA договоре, среднее время отклика API < 50 миллисекунд и выдерживание пиковых нагрузок свыше 10 000 RPS благодаря пулу asyncpg и кэшированию Redis.`},{q:`Возможна ли интеграция с 1С, ЮKassa и внешними API?`,a:`Да. Мы разрабатываем асинхронные очереди сообщений и брокеры очередей, которые безопасно синхронизируют каталог, остатки, номенклатуру 1С и обрабатывают вебхуки платежей без задержек для клиентов.`}];function ee(){let[e,t]=(0,P.useState)(0),n=n=>{t(e===n?-1:n)};return(0,I.jsxs)(`section`,{className:`faq-section`,id:`faq`,children:[(0,I.jsxs)(`div`,{className:`container`,children:[(0,I.jsxs)(`div`,{className:`faq-head text-center`,children:[(0,I.jsxs)(`div`,{className:`badge-capsule`,children:[(0,I.jsx)(`span`,{className:`badge-icon`,children:`?`}),(0,I.jsx)(`span`,{children:`FAQS`})]}),(0,I.jsx)(`h2`,{className:`faq-title`,children:`Frequently asked questions`}),(0,I.jsx)(`p`,{className:`faq-sub`,children:`Все детали по стеку, процессам разработки и гарантиям надежности.`})]}),(0,I.jsx)(`div`,{className:`faq-list`,children:Z.map((t,r)=>{let i=e===r;return(0,I.jsxs)(`div`,{className:`dark-card faq-card ${i?`open`:``}`,onClick:()=>n(r),children:[(0,I.jsxs)(`div`,{className:`faq-question-row`,children:[(0,I.jsx)(`span`,{className:`faq-q-text`,children:t.q}),(0,I.jsx)(`div`,{className:`faq-toggle-btn`,children:i?(0,I.jsx)(m,{size:16}):(0,I.jsx)(k,{size:16})})]}),i&&(0,I.jsx)(`p`,{className:`faq-a-text`,children:t.a})]},r)})})]}),(0,I.jsx)(`style`,{children:`
        .faq-section {
          padding: 80px 0 110px;
          position: relative;
        }
        .text-center {
          text-align: center;
        }
        .faq-head {
          max-width: 660px;
          margin: 0 auto 50px;
        }
        .faq-title {
          font-size: 2.8rem;
          margin-top: 18px;
          margin-bottom: 16px;
        }
        .faq-sub {
          font-size: 1.05rem;
          color: var(--text-secondary);
        }
        .faq-list {
          max-width: 780px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        .faq-card {
          padding: 22px 28px;
          cursor: pointer;
          transition: all var(--transition-fast);
        }
        .faq-card.open {
          border-color: rgba(255, 255, 255, 0.2);
          background: #11141c;
        }
        .faq-question-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
        }
        .faq-q-text {
          font-size: 1.05rem;
          font-weight: 600;
          color: #ffffff;
        }
        .faq-toggle-btn {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.08);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          color: #ffffff;
        }
        .faq-a-text {
          font-size: 0.95rem;
          color: var(--text-secondary);
          line-height: 1.6;
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px solid var(--border-subtle);
        }

        @media (max-width: 640px) {
          .faq-title {
            font-size: 2.2rem;
          }
          .faq-q-text {
            font-size: 0.95rem;
          }
        }
      `})]})}function Q({prefillBudget:e=``,prefillSummary:t=``,prefillType:a=``,isModal:o=!1,onClose:s=()=>{}}){let[c,u]=(0,P.useState)({name:``,contact:``,task_description:t||``,budget:e||``,hp_website:``}),[f,p]=(0,P.useState)(null),[m,_]=(0,P.useState)(!1),[v,y]=(0,P.useState)(null),[b,S]=(0,P.useState)(!1),[C,w]=(0,P.useState)(null),[T,O]=(0,P.useState)(null),[k,j]=(0,P.useState)(`castleweb_bot`);(0,P.useEffect)(()=>{let e=!0;return fetch(`/api/v1/telegram/bot-info`).then(e=>e.json()).then(t=>{t.ok&&t.username&&e&&j(t.username)}).catch(()=>{}),()=>{e=!1}},[]),(0,P.useEffect)(()=>{t&&u(n=>({...n,task_description:t,budget:e||n.budget}))},[t,e]);let M=e=>{let{name:t,value:n}=e.target;u(e=>({...e,[t]:n})),T&&O(null)};return(0,I.jsxs)(`div`,{className:`lead-form-box ${o?`lead-form-modal`:``}`,children:[o&&(0,I.jsx)(`button`,{className:`modal-close-btn`,onClick:s,"aria-label":`Закрыть окно`,children:(0,I.jsx)(E,{size:20})}),C?(0,I.jsxs)(`div`,{className:`success-state`,children:[(0,I.jsxs)(`div`,{className:`success-icon-box`,children:[(0,I.jsx)(i,{size:48,className:`success-icon`}),(0,I.jsx)(`div`,{className:`success-sparkle`})]}),(0,I.jsxs)(`div`,{className:`badge badge-glow success-badge`,children:[(0,I.jsx)(d,{size:13}),(0,I.jsxs)(`span`,{children:[`ЗАЯВКА #`,C.id||`LIVE`,` ПРИНЯТА В ОБРАБОТКУ`]})]}),(0,I.jsxs)(`h3`,{className:`success-title`,children:[`Прямой контакт `,(0,I.jsx)(`span`,{className:`gradient-text`,children:`установлен`})]}),(0,I.jsxs)(`p`,{className:`success-description`,children:[`Данные по проекту `,(0,I.jsxs)(`strong`,{children:[`«`,c.name,`»`]}),` моментально доставлены в закрытый дежурный канал ведущих архитекторов CASTLEWEB.`]}),(0,I.jsxs)(`div`,{className:`success-telemetry-box`,children:[(0,I.jsxs)(`div`,{className:`success-telemetry-row`,children:[(0,I.jsx)(`span`,{className:`telemetry-label`,children:`Канал связи:`}),(0,I.jsx)(`span`,{className:`telemetry-value font-mono`,children:c.contact})]}),(0,I.jsxs)(`div`,{className:`success-telemetry-row`,children:[(0,I.jsx)(`span`,{className:`telemetry-label`,children:`Статус обработки:`}),(0,I.jsxs)(`span`,{className:`telemetry-value text-emerald flex-center`,children:[(0,I.jsx)(`span`,{className:`pulse-beacon`}),` Ожидает распределения`]})]}),(0,I.jsxs)(`div`,{className:`success-telemetry-row`,children:[(0,I.jsx)(`span`,{className:`telemetry-label`,children:`Среднее время ответа:`}),(0,I.jsxs)(`span`,{className:`telemetry-value text-cyan`,children:[(0,I.jsx)(l,{size:13,className:`inline-icon`}),` ~15 минут`]})]})]}),(0,I.jsxs)(`div`,{className:`success-actions`,children:[(0,I.jsxs)(`a`,{href:`https://t.me/${k||`castleweb_bot`}?start=lead_${C.id||0}`,target:`_blank`,rel:`noopener noreferrer`,className:`btn-primary w-full`,id:`btn-goto-telegram`,children:[(0,I.jsx)(`span`,{children:`Перейти к диалогу в Telegram (@${k||`castleweb_bot`})`}),(0,I.jsx)(x,{size:16})]}),(0,I.jsx)(`button`,{className:`btn-ghost w-full`,onClick:()=>{w(null),u({name:``,contact:``,task_description:``,budget:``,hp_website:``}),p(null),O(null)},children:`Отправить еще одну заявку`})]})]}):(0,I.jsxs)(`form`,{onSubmit:async e=>{if(e.preventDefault(),!b){if(!c.name.trim()||c.name.trim().length<2){O(`Пожалуйста, укажите ваше имя или название компании (мин. 2 символа).`);return}if(!c.contact.trim()||c.contact.trim().length<3){O(`Укажите контакт для связи: Telegram @username, почту или телефон.`);return}if(!c.task_description.trim()||c.task_description.trim().length<5){O(`Пожалуйста, опишите кратко задачу проекта (мин. 5 символов).`);return}S(!0),O(null);try{let e={name:c.name.trim(),contact:c.contact.trim(),task_description:c.task_description.trim(),budget:c.budget.trim()||null,attachment_url:f?f.url:null,hp_website:c.hp_website.trim()||null,turnstile_token:null},t=await fetch(`/api/v1/leads`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify(e)});if(!t.ok){if(t.status===429)throw Error(`Превышен лимит запросов. Пожалуйста, подождите несколько минут перед отправкой следующей заявки.`);let e=await t.json().catch(()=>({}));throw Error(e.detail||`Не удалось отправить заявку. Попробуйте еще раз или напишите напрямую в Telegram.`)}let n=await t.json();w(n)}catch(e){O(e.message||`Сетевая ошибка при отправке заявки.`)}finally{S(!1)}}},className:`lead-form`,noValidate:!0,children:[(0,I.jsxs)(`div`,{className:`form-head`,children:[(0,I.jsxs)(`div`,{className:`badge badge-glow`,children:[(0,I.jsx)(h,{size:13}),(0,I.jsx)(`span`,{children:`ОБСУЖДЕНИЕ ПРОЕКТА БЕЗ МЕНЕДЖЕРОВ-ПОСРЕДНИКОВ`})]}),(0,I.jsxs)(`h3`,{className:`form-title`,children:[`Расскажите о задаче — мы вернемся с `,(0,I.jsx)(`span`,{className:`gradient-text`,children:`архитектурным решением`})]}),(0,I.jsx)(`p`,{className:`form-subtitle`,children:`Разбираем стек, проектируем масштабируемую архитектуру, даем прозрачную оценку по спринтам и фиксируем NDA.`}),(0,I.jsxs)(`div`,{className:`tg-quick-banner`,children:[(0,I.jsx)(`span`,{children:`Предпочитаете Telegram? Напишите нам напрямую:`}),(0,I.jsxs)(`a`,{href:`https://t.me/${k||`castleweb_bot`}`,target:`_blank`,rel:`noopener noreferrer`,className:`tg-quick-link`,children:[(0,I.jsx)(x,{size:13}),(0,I.jsxs)(`span`,{children:[`@`,k||`castleweb_bot`]})]})]})]}),T&&(0,I.jsxs)(`div`,{className:`form-alert form-alert-error`,children:[(0,I.jsx)(r,{size:18,className:`alert-icon`}),(0,I.jsx)(`span`,{children:T})]}),(0,I.jsx)(`div`,{style:{display:`none`,position:`absolute`,left:`-9999px`},"aria-hidden":`true`,children:(0,I.jsx)(`input`,{type:`text`,name:`hp_website`,value:c.hp_website,onChange:M,tabIndex:-1,autoComplete:`off`})}),(0,I.jsxs)(`div`,{className:`form-grid`,children:[(0,I.jsxs)(`div`,{className:`form-field`,children:[(0,I.jsxs)(`label`,{htmlFor:`lead-name`,className:`field-label`,children:[`Ваше имя или компания `,(0,I.jsx)(`span`,{className:`req`,children:`*`})]}),(0,I.jsx)(`input`,{type:`text`,id:`lead-name`,name:`name`,value:c.name,onChange:M,placeholder:`Константин / FinTech Corp`,className:`input-text`,required:!0})]}),(0,I.jsxs)(`div`,{className:`form-field`,children:[(0,I.jsxs)(`label`,{htmlFor:`lead-contact`,className:`field-label`,children:[`Telegram / Почта / Телефон `,(0,I.jsx)(`span`,{className:`req`,children:`*`})]}),(0,I.jsx)(`input`,{type:`text`,id:`lead-contact`,name:`contact`,value:c.contact,onChange:M,placeholder:`@username или ceo@domain.com`,className:`input-text`,required:!0})]})]}),(0,I.jsxs)(`div`,{className:`form-field`,children:[(0,I.jsxs)(`div`,{className:`field-label-row`,children:[(0,I.jsx)(`label`,{htmlFor:`lead-budget`,className:`field-label`,children:`Ориентир бюджета / Формат спринтов`}),a&&(0,I.jsxs)(`span`,{className:`badge-tag`,children:[`Конфигуратор: `,a]})]}),(0,I.jsx)(`input`,{type:`text`,id:`lead-budget`,name:`budget`,value:c.budget,onChange:M,placeholder:`Например: 250 000 — 400 000 ₽ или Открытый бюджет`,className:`input-text`})]}),(0,I.jsxs)(`div`,{className:`form-field`,children:[(0,I.jsxs)(`label`,{htmlFor:`lead-task`,className:`field-label`,children:[`Описание проекта или технические требования `,(0,I.jsx)(`span`,{className:`req`,children:`*`})]}),(0,I.jsx)(`textarea`,{id:`lead-task`,name:`task_description`,value:c.task_description,onChange:M,rows:4,placeholder:`Опишите продукт, целевую аудиторию, ключевые интеграции (1С, платежи, AI) или текущие узкие места в производительности...`,className:`input-textarea`,required:!0})]}),(0,I.jsxs)(`div`,{className:`upload-container`,children:[f?(0,I.jsxs)(`div`,{className:`attached-file-chip`,children:[(0,I.jsx)(A,{size:18,className:`attached-icon`}),(0,I.jsxs)(`div`,{className:`attached-info`,children:[(0,I.jsx)(`span`,{className:`attached-name`,children:f.name}),(0,I.jsxs)(`span`,{className:`attached-size`,children:[f.size,` • Загружено`]})]}),(0,I.jsx)(`button`,{type:`button`,onClick:()=>{p(null),y(null)},className:`attached-remove-btn`,title:`Удалить файл`,children:(0,I.jsx)(E,{size:16})})]}):(0,I.jsxs)(`label`,{className:`upload-dropzone ${m?`uploading`:``}`,children:[(0,I.jsx)(`input`,{type:`file`,onChange:async e=>{let t=e.target.files?.[0];if(t){if(t.size>26214400){y(`Файл превышает лимит 25 МБ`);return}_(!0),y(null);try{let e=new FormData;e.append(`file`,t);let n=await fetch(`/api/v1/uploads/file`,{method:`POST`,body:e});if(!n.ok){let e=await n.json().catch(()=>({}));throw Error(e.detail||`Ошибка загрузки файла`)}let r=await n.json();p({name:t.name,url:r.url,size:(t.size/1048576).toFixed(2)+` МБ`})}catch(e){y(e.message||`Не удалось прикрепить файл`)}finally{_(!1),e.target&&(e.target.value=``)}}},disabled:m,className:`file-input-hidden`,accept:`.pdf,.zip,.rar,.7z,.tar,.gz,.png,.jpg,.jpeg,.webp,.svg,.gif,.docx,.doc,.pptx,.ppt,.odt,.rtf,.fig,.txt,.csv,.xlsx`}),m?(0,I.jsxs)(`div`,{className:`upload-loading-state`,children:[(0,I.jsx)(g,{size:22,className:`spin-icon text-cyan`}),(0,I.jsx)(`span`,{children:`Загрузка файла в защищенное хранилище...`})]}):(0,I.jsxs)(`div`,{className:`upload-idle-state`,children:[(0,I.jsx)(n,{size:20,className:`upload-icon`}),(0,I.jsx)(`span`,{className:`upload-main-text`,children:`Прикрепить ТЗ, бриф, макет или фото`}),(0,I.jsx)(`span`,{className:`upload-sub-text`,children:`PDF, DOCX, ZIP, PNG, JPG, FIG до 25 МБ`})]})]}),v&&(0,I.jsxs)(`div`,{className:`upload-error-msg`,children:[(0,I.jsx)(r,{size:14}),(0,I.jsx)(`span`,{children:v})]})]}),(0,I.jsx)(`div`,{className:`form-footer-meta`,children:(0,I.jsxs)(`div`,{className:`meta-security`,children:[(0,I.jsx)(D,{size:16,className:`text-emerald`}),(0,I.jsx)(`span`,{children:`Строгий NDA по умолчанию. Данные защищены и не передаются третьим лицам.`})]})}),(0,I.jsx)(`button`,{type:`submit`,className:`btn-primary form-submit-btn w-full`,disabled:b,id:`lead-submit-btn`,children:b?(0,I.jsxs)(I.Fragment,{children:[(0,I.jsx)(g,{size:18,className:`spin-icon`}),(0,I.jsx)(`span`,{children:`Шифрование и отправка в Telegram...`})]}):(0,I.jsxs)(I.Fragment,{children:[(0,I.jsx)(`span`,{children:`Отправить заявку архитекторам`}),(0,I.jsx)(x,{size:18})]})})]}),(0,I.jsx)(`style`,{children:`
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
      `})]})}var te=new Date().getFullYear();function ne({size:e=16}){return(0,I.jsxs)(`svg`,{width:e,height:e,viewBox:`0 0 24 24`,fill:`none`,stroke:`currentColor`,strokeWidth:`2`,strokeLinecap:`round`,strokeLinejoin:`round`,children:[(0,I.jsx)(`path`,{d:`M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4`}),(0,I.jsx)(`path`,{d:`M9 18c-4.51 2-5-2-7-2`})]})}function re({onOpenContact:e}){return(0,I.jsxs)(`footer`,{className:`footer-wrap`,children:[(0,I.jsxs)(`div`,{className:`container`,children:[(0,I.jsxs)(`div`,{className:`footer-cta-banner glass-card`,children:[(0,I.jsxs)(`div`,{className:`footer-cta-text`,children:[(0,I.jsx)(`h3`,{children:`Готовы обсудить архитектуру вашего проекта?`}),(0,I.jsx)(`p`,{children:`Дежурный архитектор ответит на вопросы по стеку и подготовит детальный расчет в течение 15 минут.`})]}),(0,I.jsxs)(`button`,{className:`btn-primary`,onClick:e,id:`footer-cta-btn`,children:[(0,I.jsx)(`span`,{children:`Обсудить задачу`}),(0,I.jsx)(x,{size:16})]})]}),(0,I.jsxs)(`div`,{className:`footer-grid`,children:[(0,I.jsxs)(`div`,{className:`footer-col brand-col`,children:[(0,I.jsxs)(`div`,{className:`brand-logo footer-logo`,children:[(0,I.jsx)(`div`,{className:`logo-icon-box`,children:(0,I.jsx)(w,{className:`logo-icon`,size:20})}),(0,I.jsxs)(`div`,{className:`brand-text`,children:[(0,I.jsxs)(`span`,{className:`brand-title`,children:[`CASTLE`,(0,I.jsx)(`span`,{className:`brand-highlight`,children:`WEB`})]}),(0,I.jsx)(`span`,{className:`brand-subtitle`,children:`ENGINEERING STUDIO`})]})]}),(0,I.jsx)(`p`,{className:`footer-bio`,children:`Инженерная разработка высоконагруженных веб-сервисов, 3D E-commerce и B2B платформ. Zero-cost инфраструктура, чистый код и автономность для бизнеса.`}),(0,I.jsxs)(`div`,{className:`footer-socials`,children:[(0,I.jsx)(`a`,{href:`https://t.me`,target:`_blank`,rel:`noopener noreferrer`,className:`social-btn`,title:`Telegram`,children:(0,I.jsx)(x,{size:16})}),(0,I.jsx)(`a`,{href:`https://github.com`,target:`_blank`,rel:`noopener noreferrer`,className:`social-btn`,title:`GitHub`,children:(0,I.jsx)(ne,{size:16})}),(0,I.jsx)(`a`,{href:`mailto:dev@castleweb.ru`,className:`social-btn`,title:`Email`,children:(0,I.jsx)(S,{size:16})})]})]}),(0,I.jsxs)(`div`,{className:`footer-col`,children:[(0,I.jsx)(`h5`,{className:`footer-heading`,children:`Навигация`}),(0,I.jsxs)(`ul`,{className:`footer-links`,children:[(0,I.jsx)(`li`,{children:(0,I.jsx)(`a`,{href:`#hero`,children:`Главная`})}),(0,I.jsx)(`li`,{children:(0,I.jsx)(`a`,{href:`#cases`,children:`Кейсы и проекты`})}),(0,I.jsx)(`li`,{children:(0,I.jsx)(`a`,{href:`#calculator`,children:`Калькулятор сметы`})}),(0,I.jsx)(`li`,{children:(0,I.jsx)(`a`,{href:`#architecture`,children:`Стек & Архитектура`})}),(0,I.jsx)(`li`,{children:(0,I.jsx)(`a`,{href:`#about`,children:`О студии`})})]})]}),(0,I.jsxs)(`div`,{className:`footer-col`,children:[(0,I.jsx)(`h5`,{className:`footer-heading`,children:`Инженерия & API`}),(0,I.jsxs)(`ul`,{className:`footer-links`,children:[(0,I.jsx)(`li`,{children:(0,I.jsxs)(`a`,{href:`/api/v1/status`,target:`_blank`,rel:`noopener noreferrer`,className:`link-with-icon`,children:[(0,I.jsx)(`span`,{children:`Статус систем (JSON)`}),(0,I.jsx)(N,{size:12})]})}),(0,I.jsx)(`li`,{children:(0,I.jsxs)(`a`,{href:`/docs`,target:`_blank`,rel:`noopener noreferrer`,className:`link-with-icon`,children:[(0,I.jsx)(`span`,{children:`Swagger / OpenAPI v3`}),(0,I.jsx)(N,{size:12})]})}),(0,I.jsx)(`li`,{children:(0,I.jsx)(`a`,{href:`#architecture`,children:`Clean Architecture`})}),(0,I.jsx)(`li`,{children:(0,I.jsx)(`a`,{href:`#architecture`,children:`0 ₽ Cloudflare R2`})})]})]}),(0,I.jsxs)(`div`,{className:`footer-col`,children:[(0,I.jsx)(`h5`,{className:`footer-heading`,children:`Прямая связь`}),(0,I.jsxs)(`p`,{className:`contact-line`,children:[(0,I.jsx)(`span`,{className:`text-muted`,children:`Дежурный инженер:`}),(0,I.jsx)(`br`,{}),(0,I.jsx)(`strong`,{className:`text-white`,children:`@castleweb_lead`})]}),(0,I.jsxs)(`p`,{className:`contact-line`,children:[(0,I.jsx)(`span`,{className:`text-muted`,children:`Почта для брифов:`}),(0,I.jsx)(`br`,{}),(0,I.jsx)(`span`,{className:`font-mono text-cyan`,children:`engineering@castleweb.dev`})]}),(0,I.jsxs)(`div`,{className:`footer-badge-online`,children:[(0,I.jsx)(`span`,{className:`pulse-beacon`}),(0,I.jsx)(`span`,{children:`SLA Гарантия доступности 99.98%`})]})]})]}),(0,I.jsxs)(`div`,{className:`footer-bottom`,children:[(0,I.jsxs)(`div`,{className:`footer-copy`,children:[`© `,te,` CASTLEWEB Studio. Все права защищены. Разработано с фокусом на Highload & Security.`]}),(0,I.jsxs)(`button`,{onClick:()=>{window.scrollTo({top:0,behavior:`smooth`})},className:`scroll-top-btn`,title:`Наверх`,children:[(0,I.jsx)(b,{size:16}),(0,I.jsx)(`span`,{children:`Наверх`})]})]})]}),(0,I.jsx)(`style`,{children:`
        .footer-wrap {
          background: #040508;
          border-top: 1px solid var(--border-subtle);
          padding: 60px 0 30px;
          position: relative;
          z-index: 1;
        }
        .footer-cta-banner {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 36px 44px;
          border-radius: 20px;
          margin-bottom: 60px;
          border: 1px solid var(--border-glow);
          gap: 30px;
          background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(14, 18, 28, 0.8) 100%);
        }
        .footer-cta-text h3 {
          font-size: 1.6rem;
          margin-bottom: 8px;
        }
        .footer-cta-text p {
          color: var(--text-secondary);
          font-size: 0.95rem;
          max-width: 600px;
        }
        .footer-grid {
          display: grid;
          grid-template-columns: 1.5fr 1fr 1fr 1fr;
          gap: 40px;
          padding-bottom: 50px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .footer-logo {
          margin-bottom: 16px;
        }
        .footer-bio {
          font-size: 0.88rem;
          color: var(--text-secondary);
          line-height: 1.6;
          margin-bottom: 20px;
          max-width: 320px;
        }
        .footer-socials {
          display: flex;
          gap: 10px;
        }
        .social-btn {
          width: 38px;
          height: 38px;
          border-radius: 10px;
          background: rgba(255, 255, 255, 0.04);
          border: 1px solid var(--border-subtle);
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-secondary);
          transition: all var(--transition-fast);
        }
        .social-btn:hover {
          color: #ffffff;
          background: rgba(99, 102, 241, 0.2);
          border-color: var(--accent-indigo);
          transform: translateY(-2px);
        }
        .footer-heading {
          font-size: 0.95rem;
          color: #ffffff;
          font-weight: 700;
          margin-bottom: 18px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .footer-links {
          list-style: none;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .footer-links a {
          color: var(--text-secondary);
          font-size: 0.88rem;
          transition: color var(--transition-fast);
        }
        .footer-links a:hover {
          color: #ffffff;
        }
        .link-with-icon {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .contact-line {
          font-size: 0.88rem;
          margin-bottom: 14px;
          line-height: 1.4;
        }
        .footer-badge-online {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.78rem;
          color: var(--accent-emerald);
          font-family: var(--font-mono);
          margin-top: 18px;
        }
        .footer-bottom {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding-top: 24px;
          font-size: 0.82rem;
          color: var(--text-muted);
        }
        .scroll-top-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          color: var(--text-secondary);
          font-size: 0.82rem;
          transition: color var(--transition-fast);
        }
        .scroll-top-btn:hover {
          color: #ffffff;
        }

        @media (max-width: 960px) {
          .footer-cta-banner {
            flex-direction: column;
            align-items: flex-start;
            padding: 24px;
          }
          .footer-grid {
            grid-template-columns: 1fr 1fr;
            gap: 30px;
          }
        }
        @media (max-width: 640px) {
          .footer-grid {
            grid-template-columns: 1fr;
          }
          .footer-bottom {
            flex-direction: column;
            gap: 16px;
            text-align: center;
          }
        }
      `})]})}function ie(){let[e,t]=(0,P.useState)({budget:``,summary:``,projectType:``}),[n,r]=(0,P.useState)(!1),i=e=>{t({budget:e.budget,summary:e.summary,projectType:e.projectType});let n=document.getElementById(`contact`);n&&n.scrollIntoView({behavior:`smooth`})},a=()=>{let e=document.getElementById(`contact`);e?e.scrollIntoView({behavior:`smooth`}):r(!0)};return(0,I.jsxs)(`div`,{className:`app-layout`,children:[(0,I.jsx)(L,{onOpenContact:a}),(0,I.jsxs)(`main`,{id:`main-content`,children:[(0,I.jsx)(z,{onOpenContact:a,onExploreCases:()=>{let e=document.getElementById(`cases`);e&&e.scrollIntoView({behavior:`smooth`})}}),(0,I.jsx)(B,{onOpenContact:a}),(0,I.jsx)(H,{}),(0,I.jsx)(W,{}),(0,I.jsx)(q,{onApplyConfig:i}),(0,I.jsx)(X,{}),(0,I.jsx)(ee,{}),(0,I.jsx)(`section`,{className:`contact-section`,id:`contact`,children:(0,I.jsx)(`div`,{className:`container`,children:(0,I.jsx)(`div`,{className:`contact-wrapper`,children:(0,I.jsx)(Q,{prefillBudget:e.budget,prefillSummary:e.summary,prefillType:e.projectType})})})})]}),(0,I.jsx)(re,{onOpenContact:a}),n&&(0,I.jsx)(`div`,{className:`modal-backdrop`,onClick:()=>r(!1),children:(0,I.jsx)(`div`,{className:`modal-inner`,onClick:e=>e.stopPropagation(),children:(0,I.jsx)(Q,{prefillBudget:e.budget,prefillSummary:e.summary,prefillType:e.projectType,isModal:!0,onClose:()=>r(!1)})})}),(0,I.jsx)(`style`,{children:`
        .app-layout {
          position: relative;
          min-height: 100vh;
          background: #000000;
        }
        .contact-section {
          padding: 80px 0 120px;
          position: relative;
        }
        .contact-wrapper {
          max-width: 820px;
          margin: 0 auto;
        }
        .modal-backdrop {
          position: fixed;
          top: 0;
          left: 0;
          width: 100vw;
          height: 100vh;
          background: rgba(0, 0, 0, 0.85);
          backdrop-filter: blur(14px);
          z-index: 1000;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }
        .modal-inner {
          position: relative;
          z-index: 1001;
        }
      `})]})}function $(e){"@babel/helpers - typeof";return $=typeof Symbol==`function`&&typeof Symbol.iterator==`symbol`?function(e){return typeof e}:function(e){return e&&typeof Symbol==`function`&&e.constructor===Symbol&&e!==Symbol.prototype?`symbol`:typeof e},$(e)}function ae(e,t){if($(e)!=`object`||!e)return e;var n=e[Symbol.toPrimitive];if(n!==void 0){var r=n.call(e,t||`default`);if($(r)!=`object`)return r;throw TypeError(`@@toPrimitive must return a primitive value.`)}return(t===`string`?String:Number)(e)}function oe(e){var t=ae(e,`string`);return $(t)==`symbol`?t:t+``}function se(e,t,n){return(t=oe(t))in e?Object.defineProperty(e,t,{value:n,enumerable:!0,configurable:!0,writable:!0}):e[t]=n,e}var ce=class extends P.Component{constructor(e){super(e),se(this,`handleReload`,()=>{window.location.reload()}),this.state={hasError:!1,error:null}}static getDerivedStateFromError(e){return{hasError:!0,error:e}}componentDidCatch(e,t){console.error(`Castleweb ErrorBoundary caught:`,e,t)}render(){return this.state.hasError?(0,I.jsx)(`div`,{style:{minHeight:`100vh`,display:`flex`,alignItems:`center`,justifyContent:`center`,background:`#08090d`,color:`#ffffff`,fontFamily:`'Inter', -apple-system, sans-serif`,padding:`24px`},children:(0,I.jsxs)(`div`,{style:{maxWidth:`520px`,width:`100%`,background:`rgba(255, 255, 255, 0.03)`,border:`1px solid rgba(255, 255, 255, 0.1)`,borderRadius:`16px`,padding:`36px`,textAlign:`center`,backdropFilter:`blur(20px)`},children:[(0,I.jsx)(`div`,{style:{width:`56px`,height:`56px`,borderRadius:`50%`,background:`rgba(239, 68, 68, 0.12)`,border:`1px solid rgba(239, 68, 68, 0.3)`,display:`flex`,alignItems:`center`,justifyContent:`center`,margin:`0 auto 20px`,color:`#ef4444`,fontSize:`24px`},children:`⚠️`}),(0,I.jsx)(`h2`,{style:{fontSize:`1.4rem`,fontWeight:700,marginBottom:`12px`},children:`Интерфейс временно недоступен`}),(0,I.jsx)(`p`,{style:{color:`rgba(255, 255, 255, 0.6)`,fontSize:`0.95rem`,lineHeight:1.6,marginBottom:`24px`},children:`Произошла непредвиденная ошибка при инициализации компонентов. Пожалуйста, обновите страницу.`}),(0,I.jsx)(`button`,{onClick:this.handleReload,style:{display:`inline-flex`,alignItems:`center`,justifyContent:`center`,gap:`8px`,padding:`12px 28px`,borderRadius:`9999px`,background:`#ffffff`,color:`#000000`,fontWeight:600,fontSize:`0.9rem`,border:`none`,cursor:`pointer`,transition:`transform 0.2s ease`},children:`Перезагрузить страницу`})]})}):this.props.children}};(0,F.createRoot)(document.getElementById(`root`)).render((0,I.jsx)(P.StrictMode,{children:(0,I.jsx)(ce,{children:(0,I.jsx)(ie,{})})}));