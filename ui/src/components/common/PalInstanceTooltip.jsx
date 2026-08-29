import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { LEGEND_PASSIVES, GOLD_PASSIVES, NEGATIVE_PASSIVES } from '../../constants/gameData';

export function PalInstanceTooltip({ instance, children }) {
  const [pos, setPos] = useState(null);

  if (!instance) return children;

  const handleMouseMove = (e) => {
    const cardWidth = 400;
    const cardHeight = 220;
    const offset = 14;

    let left = e.clientX + offset;
    let top = e.clientY + offset;

    // Flip horizontally if it would overflow the right viewport edge
    if (left + cardWidth > window.innerWidth - 12) {
      left = Math.max(12, e.clientX - cardWidth - offset);
    }
    // Flip vertically if it would overflow the bottom viewport edge
    if (top + cardHeight > window.innerHeight - 12) {
      top = Math.max(12, e.clientY - cardHeight - offset);
    }

    setPos({ left, top });
  };

  const handleMouseLeave = () => {
    setPos(null);
  };

  const displayName = instance.display_name || instance.species || 'Pal';
  const level = instance.level || '?';
  const rawGender = String(instance.gender || '').toLowerCase();
  const genderText = rawGender.startsWith('m') ? '♂ Male' : rawGender.startsWith('f') ? '♀ Female' : (instance.gender || 'Unknown');
  const stars = instance.rank ? '⭐'.repeat(instance.rank) : '';
  const score = instance.score !== undefined ? instance.score : instance.skill_score;
  const location = instance.location_details?.base_camp_name
    ? `Base: ${instance.location_details.base_camp_name}`
    : instance.location === 'party'
    ? 'Active Party'
    : instance.location === 'palbox'
    ? 'Palbox'
    : (instance.location || 'Palbox');

  const ivs = instance.ivs || {};
  const hpIv = ivs.hp !== undefined ? ivs.hp : instance.iv_hp;
  const atkIv = ivs.melee !== undefined ? ivs.melee : instance.iv_melee;
  const defIv = ivs.defense !== undefined ? ivs.defense : instance.iv_defense;

  const passives = instance.passives || instance.passive_names || [];

  return (
    <span 
      className="pal-tooltip-wrapper" 
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
          }}
        >
          <div className="pal-tooltip-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
              <span style={{ fontWeight: 800, color: '#38bdf8' }}>🐾 {displayName}</span>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.78rem' }}>(Lv. {level} {genderText})</span>
              {stars && <span style={{ fontSize: '0.75rem' }}>{stars}</span>}
            </div>
            {score !== undefined && (
              <span className={`badge ${score >= 0 ? 'badge-score-positive' : 'badge-score-negative'}`} style={{ fontSize: '0.7rem', padding: '0.1rem 0.35rem' }}>
                Score: {score > 0 ? `+${score}` : score}
              </span>
            )}
          </div>

          <div className="pal-tooltip-row">
            <span className="pal-tooltip-label">📍 Location:</span>
            <span style={{ color: '#f8fafc', fontWeight: 600 }}>{location}</span>
          </div>

          {passives.length > 0 && (
            <div className="pal-tooltip-row" style={{ alignItems: 'flex-start' }}>
              <span className="pal-tooltip-label">🏷️ Passives:</span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                {passives.map((p, idx) => {
                  const pName = typeof p === 'string' ? p : p.name || p.id || '';
                  const pLower = pName.toLowerCase().trim();
                  const isMatched = instance.matched_passives && instance.matched_passives.some(m => String(m).toLowerCase() === pLower);
                  const isNeg = NEGATIVE_PASSIVES.has(pLower);
                  const isLegend = LEGEND_PASSIVES.has(pLower);
                  const isGold = GOLD_PASSIVES.has(pLower);

                  let badgeClass = 'pal-badge-white';
                  let prefix = '';
                  if (isMatched) {
                    badgeClass = 'pal-badge-target';
                    prefix = '✨ ';
                  } else if (isNeg) {
                    badgeClass = 'pal-badge-negative';
                    prefix = '⛔ ';
                  } else if (isLegend) {
                    badgeClass = 'pal-badge-legend';
                    prefix = '👑 ';
                  } else if (isGold) {
                    badgeClass = 'pal-badge-gold';
                  }

                  return (
                    <span 
                      key={idx} 
                      className={`badge ${badgeClass}`}
                      style={{ fontSize: '0.68rem', padding: '0.08rem 0.35rem', borderRadius: '4px' }}
                    >
                      {prefix}{pName}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          <div className="pal-tooltip-row">
            <span className="pal-tooltip-label">🛡️ IVs (HP/Atk/Def):</span>
            <span style={{ color: '#38bdf8', fontWeight: 700 }}>
              {hpIv !== undefined ? `${hpIv}%` : '?'} / {atkIv !== undefined ? `${atkIv}%` : '?'} / {defIv !== undefined ? `${defIv}%` : '?'}
            </span>
          </div>
        </div>,
        document.body
      )}
    </span>
  );
}

export default PalInstanceTooltip;
