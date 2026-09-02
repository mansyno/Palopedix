import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { PassiveBadge } from './PassiveBadge';

export function PalInstanceTooltip({ instance, children }) {
  const [pos, setPos] = useState(null);

  if (!instance) return children;

  const updatePosition = (e) => {
    const cardWidth = 400;
    const cardHeight = 240;
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

  const handleMouseEnter = (e) => {
    updatePosition(e);
  };

  const handleMouseMove = (e) => {
    updatePosition(e);
  };

  const handleMouseLeave = () => {
    setPos(null);
  };

  const displayName = instance.display_name || instance.species || instance.name || 'Pal';
  
  // Safe rank parsing
  let rankNum = 0;
  if (typeof instance.rank === 'number') {
    rankNum = instance.rank;
  } else if (typeof instance.rank === 'string') {
    rankNum = parseInt(instance.rank, 10) || 0;
  }
  const stars = rankNum > 0 && rankNum <= 5 ? '⭐'.repeat(rankNum) : '';

  const isInstance = Boolean(
    instance.instance_id ||
    instance.isInstance ||
    instance.level !== undefined ||
    instance.location ||
    instance.iv_hp !== undefined ||
    instance.ivs
  );

  const rawGender = String(instance.gender || '').toLowerCase();
  const genderText = rawGender.startsWith('m') ? '♂ Male' : rawGender.startsWith('f') ? '♀ Female' : (instance.gender || '');
  const level = instance.level !== undefined ? instance.level : '?';
  const score = instance.score !== undefined ? instance.score : instance.skill_score;
  const location = instance.location_details?.base_camp_name
    ? `Base: ${instance.location_details.base_camp_name}`
    : instance.location === 'party'
    ? 'Active Party'
    : instance.location === 'palbox'
    ? 'Palbox'
    : (instance.location || (isInstance ? 'Palbox' : null));

  const ivs = instance.ivs || {};
  const hpIv = ivs.hp !== undefined ? ivs.hp : instance.iv_hp;
  const atkIv = ivs.melee !== undefined ? ivs.melee : instance.iv_melee;
  const defIv = ivs.defense !== undefined ? ivs.defense : instance.iv_defense;

  const passives = instance.passives || instance.passive_names || [];
  const elem1 = instance.element_1 || instance.element1 || instance.element;
  const elem2 = instance.element_2 || instance.element2;

  return (
    <span 
      className="pal-tooltip-wrapper" 
      onMouseEnter={handleMouseEnter}
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
              {instance.paldex_number && (
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.76rem' }}>
                  #{String(instance.paldex_number).padStart(3, '0')}
                </span>
              )}
              {isInstance && (
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.78rem' }}>
                  (Lv. {level} {genderText})
                </span>
              )}
              {stars && <span style={{ fontSize: '0.75rem' }}>{stars}</span>}
            </div>
            {score !== undefined && (
              <span className={`badge ${score >= 0 ? 'badge-score-positive' : 'badge-score-negative'}`} style={{ fontSize: '0.7rem', padding: '0.1rem 0.35rem' }}>
                Score: {score > 0 ? `+${score}` : score}
              </span>
            )}
          </div>

          {(elem1 || elem2) && (
            <div className="pal-tooltip-row">
              <span className="pal-tooltip-label">⚡ Elements:</span>
              <div style={{ display: 'flex', gap: '0.3rem', alignItems: 'center' }}>
                {elem1 && (
                  <span className="badge badge-element" style={{ fontSize: '0.7rem', padding: '0.1rem 0.35rem', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}>
                    <img src={`/assets/elements/${elem1}.png`} alt={elem1} style={{ width: '12px', height: '12px' }} onError={(e) => { e.target.style.display = 'none'; }} />
                    {elem1}
                  </span>
                )}
                {elem2 && (
                  <span className="badge badge-element" style={{ fontSize: '0.7rem', padding: '0.1rem 0.35rem', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}>
                    <img src={`/assets/elements/${elem2}.png`} alt={elem2} style={{ width: '12px', height: '12px' }} onError={(e) => { e.target.style.display = 'none'; }} />
                    {elem2}
                  </span>
                )}
              </div>
            </div>
          )}

          {location && (
            <div className="pal-tooltip-row">
              <span className="pal-tooltip-label">📍 Location:</span>
              <span style={{ color: '#f8fafc', fontWeight: 600 }}>{location}</span>
            </div>
          )}

          {instance.partner_skill && (
            <div className="pal-tooltip-row">
              <span className="pal-tooltip-label">🤝 Partner:</span>
              <span style={{ color: 'var(--accent-gold)', fontWeight: 600, fontSize: '0.78rem' }}>
                {instance.partner_skill.name || instance.partner_skill}
              </span>
            </div>
          )}

          {passives.length > 0 && (
            <div className="pal-tooltip-row" style={{ alignItems: 'flex-start' }}>
              <span className="pal-tooltip-label">🏷️ Passives:</span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                {passives.map((p, idx) => {
                  const pName = typeof p === 'string' ? p : p.name || p.id || '';
                  const pLower = pName.toLowerCase().trim();
                  const isMatched = instance.matched_passives && instance.matched_passives.some(m => String(m).toLowerCase() === pLower);

                  return (
                    <PassiveBadge key={idx} skill={p} isMatched={isMatched} size="sm" />
                  );
                })}
              </div>
            </div>
          )}

          {(hpIv !== undefined || atkIv !== undefined || defIv !== undefined) && (
            <div className="pal-tooltip-row">
              <span className="pal-tooltip-label">🛡️ IVs (HP/Atk/Def):</span>
              <span style={{ color: '#38bdf8', fontWeight: 700 }}>
                {hpIv !== undefined ? `${hpIv}%` : '?'} / {atkIv !== undefined ? `${atkIv}%` : '?'} / {defIv !== undefined ? `${defIv}%` : '?'}
              </span>
            </div>
          )}

          {!isInstance && (instance.hp !== undefined || instance.attack_melee !== undefined || instance.defense !== undefined) && (
            <div className="pal-tooltip-row">
              <span className="pal-tooltip-label">📊 Base Stats:</span>
              <span style={{ color: '#94a3b8', fontSize: '0.76rem' }}>
                HP: <strong style={{ color: '#f8fafc' }}>{instance.hp}</strong> | Atk: <strong style={{ color: '#f8fafc' }}>{instance.attack_melee || instance.attack}</strong> | Def: <strong style={{ color: '#f8fafc' }}>{instance.defense}</strong>
              </span>
            </div>
          )}
        </div>,
        document.body
      )}
    </span>
  );
}

export default PalInstanceTooltip;

