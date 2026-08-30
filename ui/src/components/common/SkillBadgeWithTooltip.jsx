import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { getPassiveMeta } from './PassiveBadge';

export function SkillBadgeWithTooltip({ skill, children }) {
  const [pos, setPos] = useState(null);

  if (!skill) return children;

  const handleMouseMove = (e) => {
    const cardWidth = 320;
    const cardHeight = 140;
    const offset = 12;

    let left = e.clientX + offset;
    let top = e.clientY + offset;

    if (left + cardWidth > window.innerWidth - 12) {
      left = Math.max(12, e.clientX - cardWidth - offset);
    }
    if (top + cardHeight > window.innerHeight - 12) {
      top = Math.max(12, e.clientY - cardHeight - offset);
    }

    setPos({ left, top });
  };

  const handleMouseLeave = () => {
    setPos(null);
  };

  const meta = getPassiveMeta(skill) || {
    name: typeof skill === 'string' ? skill : (skill.name || skill.id || 'Skill'),
    color: 'var(--accent-gold)',
    prefix: '✨',
    badgeClass: 'pal-badge-white',
    label: 'Skill',
    statModifier: typeof skill === 'object' ? (skill.stat_modifier || skill.description || '') : '',
    description: typeof skill === 'object' ? (skill.description || '') : '',
  };

  return (
    <span
      className="skill-tooltip-wrapper"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ display: 'inline-flex', alignItems: 'center' }}
    >
      {children}
      {pos && createPortal(
        <div
          className="pal-tooltip-card"
          style={{
            position: 'fixed',
            left: `${pos.left}px`,
            top: `${pos.top}px`,
            zIndex: 99999999,
            pointerEvents: 'none',
            minWidth: '220px',
            maxWidth: '320px',
            background: 'rgba(15, 23, 42, 0.95)',
            backdropFilter: 'blur(12px)',
            border: `1px solid ${meta.nature === 'negative' ? 'rgba(239, 68, 68, 0.5)' : meta.nature === 'gold' ? 'rgba(245, 158, 11, 0.5)' : meta.nature === 'legend' ? 'rgba(236, 72, 153, 0.5)' : 'var(--border-color)'}`,
            borderRadius: '10px',
            padding: '0.65rem 0.85rem',
            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.6)',
          }}
        >
          <div className="pal-tooltip-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
            <span style={{ fontWeight: 800, color: meta.color, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
              <span>{meta.prefix}</span>
              <span>{meta.name}</span>
            </span>
            {meta.label && (
              <span className={`badge ${meta.badgeClass}`} style={{ fontSize: '0.68rem', padding: '0.05rem 0.35rem', borderRadius: '4px', textTransform: 'none' }}>
                {meta.label}
              </span>
            )}
          </div>
          {meta.statModifier ? (
            <div style={{ fontSize: '0.78rem', color: meta.nature === 'negative' ? '#f87171' : 'var(--accent-green)', fontWeight: 600, marginTop: '0.3rem', lineHeight: 1.35 }}>
              ✨ {meta.statModifier}
            </div>
          ) : meta.description ? (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.3rem', lineHeight: 1.35 }}>
              {meta.description}
            </div>
          ) : null}
        </div>,
        document.body
      )}
    </span>
  );
}

export default SkillBadgeWithTooltip;

