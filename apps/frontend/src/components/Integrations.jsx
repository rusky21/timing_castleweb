import React from 'react';
import { Server, Database, Send, Cloud, Cpu, Shield, Zap } from 'lucide-react';

const ORBIT_ITEMS = [
  { name: 'FastAPI', icon: Server, angle: 0, distance: 130 },
  { name: 'PostgreSQL', icon: Database, angle: 60, distance: 130 },
  { name: 'Redis', icon: Zap, angle: 120, distance: 130 },
  { name: 'Cloudflare', icon: Cloud, angle: 180, distance: 130 },
  { name: 'Telegram CRM', icon: Send, angle: 240, distance: 130 },
  { name: 'Docker', icon: Cpu, angle: 300, distance: 130 },
];

export default function Integrations() {
  return (
    <section className="integrations-section" id="integrations">
      <div className="container">
        <div className="integrations-head text-center">
          <div className="badge-capsule">
            <span className="badge-icon">⚡</span>
            <span>INTEGRATIONS</span>
          </div>
          <h2 className="integrations-title">
            Seamless integration <br />for enhanced efficiency
          </h2>
          <p className="integrations-sub">
            Синхронизация с вашей экосистемой: корпоративные базы данных, платежные шлюзы, 1C и шифрованные каналы оповещений.
          </p>
        </div>

        {/* Constellation Radial Graphic (Salesrocket style) */}
        <div className="orbit-container">
          <div className="orbit-ring ring-3" />
          <div className="orbit-ring ring-2" />
          <div className="orbit-ring ring-1" />

          {/* Central Glowing Core */}
          <div className="orbit-core">
            <Shield size={28} className="core-icon" />
            <div className="core-glow" />
          </div>

          {/* Orbiting Satellite Nodes */}
          {ORBIT_ITEMS.map((item, idx) => {
            const Icon = item.icon;
            // Calculate X/Y position from angle
            const rad = (item.angle * Math.PI) / 180;
            const x = Math.round(Math.cos(rad) * item.distance);
            const y = Math.round(Math.sin(rad) * item.distance);

            return (
              <div 
                key={idx} 
                className="orbit-node"
                style={{
                  transform: `translate(${x}px, ${y}px)`
                }}
                title={item.name}
              >
                <div className="node-icon-box">
                  <Icon size={18} />
                </div>
                <span className="node-label">{item.name}</span>
              </div>
            );
          })}
        </div>
      </div>

      <style>{`
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
      `}</style>
    </section>
  );
}
