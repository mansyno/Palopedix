import React, { useState } from 'react';
import { createPortal } from 'react-dom';

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

  const skillName = typeof skill === 'string' ? skill : (skill.name || skill.id || 'Skill');
  const skillDesc = typeof skill === 'object' ? (skill.stat_modifier || skill.description || '') : '';
  const skillRank = typeof skill === 'object' && skill.rank !== undefined ? skill.rank : null;

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
          }}
        >
          <div className="pal-tooltip-header">
            <span style={{ fontWeight: 800, color: 'var(--accent-gold)' }}>✨ {skillName}</span>
            {skillRank !== null && (
              <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.2)', color: 'var(--accent-gold)', fontSize: '0.7rem' }}>
                Rank {skillRank}
              </span>
            )}
          </div>
          {skillDesc && (
            <div style={{ fontSize: '0.78rem', color: 'var(--text-primary)', marginTop: '0.4rem', lineHeight: 1.4 }}>
              {skillDesc}
            </div>
          )}
        </div>,
        document.body
      )}
    </span>
  );
}

export default SkillBadgeWithTooltip;
