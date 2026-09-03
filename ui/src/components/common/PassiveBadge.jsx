import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import passiveSkillCards from '../../constants/passiveSkillCards.json';

export function getPassiveMeta(skill, isMatched = false) {
  if (!skill) return null;

  let id = '';
  let name = '';
  let iconPath = '';
  let description = '';
  let statModifier = '';
  let category = '';

  if (typeof skill === 'object') {
    id = skill.id || '';
    name = skill.name || '';
    iconPath = skill.icon_path || '';
    description = skill.description || '';
    statModifier = skill.stat_modifier || skill.description || '';
    category = skill.category || '';
  } else if (typeof skill === 'string') {
    name = skill.trim();
  }

  // Lookup candidates in passiveSkillCards
  const candidates = [
    id ? id.toLowerCase() : '',
    name ? name.toLowerCase() : '',
    name ? name.replace(/^EPalPassiveSkillEffectType::/i, '').replace(/^Passive_/i, '').trim().toLowerCase() : '',
    name ? name.replace(/_/g, ' ').trim().toLowerCase() : '',
    id ? id.replace(/^Passive_/i, '').trim().toLowerCase() : '',
  ].filter(Boolean);

  let matchedCard = null;
  for (const c of candidates) {
    if (passiveSkillCards[c]) {
      matchedCard = passiveSkillCards[c];
      break;
    }
  }

  if (matchedCard) {
    iconPath = iconPath || matchedCard.icon_path;
    name = name || matchedCard.name;
    description = description || matchedCard.description;
    statModifier = statModifier || matchedCard.stat_modifier;
    category = category || matchedCard.category;
    id = id || matchedCard.id;
  }

  if (!iconPath && id) {
    iconPath = `/assets/passives/${id}.png`;
  }

  return {
    id,
    name: name || id || '',
    iconPath: iconPath || null,
    description: description !== statModifier ? description : '',
    statModifier: statModifier || '',
    category: category || '',
    isMatched,
  };
}

export function PassiveBadge({
  skill,
  passive,
  isMatched = false,
  size = 'sm',
  className = '',
  style = {},
  onClick,
}) {
  const [pos, setPos] = useState(null);

  const activeSkill = skill || passive;
  if (!activeSkill) return null;

  const meta = getPassiveMeta(activeSkill, isMatched);
  if (!meta) return null;

  const handleMouseMove = (e) => {
    const cardWidth = 300;
    const cardHeight = 120;
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

  const isSmall = size === 'sm';
  const isLarge = size === 'lg' || size === 'modal';
  const cardHeight = isSmall ? '23px' : isLarge ? '36px' : '28px';

  return (
    <span
      className={`passive-badge-wrapper ${className}`}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        cursor: onClick ? 'pointer' : 'default',
        verticalAlign: 'middle',
        lineHeight: 1,
        ...style,
      }}
    >
      {meta.iconPath ? (
        <>
          <img
            src={meta.iconPath}
            alt={meta.name || 'Passive Skill'}
            style={{
              height: cardHeight,
              width: 'auto',
              maxWidth: isSmall ? '160px' : '284px',
              objectFit: 'contain',
              borderRadius: '3px',
              display: 'inline-block',
              imageRendering: '-webkit-optimize-contrast',
              boxShadow: isMatched ? '0 0 8px rgba(52, 211, 153, 0.95)' : undefined,
              border: isMatched ? '1.5px solid #34d399' : undefined,
            }}
            onError={(e) => {
              e.currentTarget.style.display = 'none';
              const naSpan = e.currentTarget.nextElementSibling;
              if (naSpan) naSpan.style.display = 'inline-block';
            }}
          />
          <span
            style={{
              display: 'none',
              color: '#94a3b8',
              fontSize: '0.68rem',
              padding: '0.08rem 0.35rem',
              background: 'rgba(255,255,255,0.06)',
              borderRadius: '4px',
              border: '1px solid rgba(255,255,255,0.1)',
            }}
          >
            N/A
          </span>
        </>
      ) : (
        <span
          style={{
            color: '#94a3b8',
            fontSize: '0.68rem',
            padding: '0.08rem 0.35rem',
            background: 'rgba(255,255,255,0.06)',
            borderRadius: '4px',
            border: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          N/A
        </span>
      )}

      {pos && (meta.statModifier || meta.description) && createPortal(
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
            border: '1px solid rgba(255, 255, 255, 0.15)',
            borderRadius: '10px',
            padding: '0.65rem 0.85rem',
            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.6)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
            {meta.iconPath ? (
              <img
                src={meta.iconPath}
                alt={meta.name}
                style={{ height: '24px', width: 'auto', borderRadius: '3px' }}
                onError={(e) => { e.currentTarget.style.display = 'none'; }}
              />
            ) : (
              <span style={{ fontWeight: 800, fontSize: '0.88rem', color: '#fbbf24' }}>
                {meta.name || 'N/A'}
              </span>
            )}
          </div>

          {meta.statModifier ? (
            <div style={{ fontSize: '0.78rem', color: 'var(--accent-green)', fontWeight: 600, lineHeight: 1.35 }}>
              ✨ {meta.statModifier}
            </div>
          ) : meta.description ? (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.35 }}>
              {meta.description}
            </div>
          ) : null}
        </div>,
        document.body
      )}
    </span>
  );
}

export default PassiveBadge;
