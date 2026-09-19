import React, { useState } from 'react';
import { createPortal } from 'react-dom';

const ROLE_CONFIGS = {
  work: {
    key: 'work',
    label: 'Work',
    short: 'Work',
    icon: '🔨',
    color: '#fcd34d',
    bg: 'rgba(245, 158, 11, 0.18)',
    border: 'rgba(245, 158, 11, 0.45)',
  },
  attack: {
    key: 'attack',
    label: 'Attack',
    short: 'Atk',
    icon: '⚔️',
    color: '#fca5a5',
    bg: 'rgba(239, 68, 68, 0.18)',
    border: 'rgba(239, 68, 68, 0.45)',
  },
  defense: {
    key: 'defense',
    label: 'Defense',
    short: 'Def',
    icon: '🛡️',
    color: '#93c5fd',
    bg: 'rgba(59, 130, 246, 0.18)',
    border: 'rgba(59, 130, 246, 0.45)',
  },
  movement: {
    key: 'movement',
    label: 'Movement',
    short: 'Spd',
    icon: '⚡',
    color: '#6ee7b7',
    bg: 'rgba(16, 185, 129, 0.18)',
    border: 'rgba(16, 185, 129, 0.45)',
  },
};

export function PassiveRoleBadge({ instance, activeRole = '', style = {} }) {
  const [pos, setPos] = useState(null);

  if (!instance) return null;

  const roleScores = instance.role_scores || {
    work: instance.score_work ?? 0,
    attack: instance.score_attack ?? 0,
    defense: instance.score_defense ?? 0,
    movement: instance.score_movement ?? 0,
  };

  const roleBreakdown = instance.role_breakdown || {};
  const bestRoleKey = instance.best_role || 'work';

  // Determine which role to emphasize on the badge
  let targetRoleKey = 'work';
  if (activeRole === 'score_work') targetRoleKey = 'work';
  else if (activeRole === 'score_attack') targetRoleKey = 'attack';
  else if (activeRole === 'score_defense') targetRoleKey = 'defense';
  else if (activeRole === 'score_movement') targetRoleKey = 'movement';
  else targetRoleKey = bestRoleKey;

  const roleCfg = ROLE_CONFIGS[targetRoleKey] || ROLE_CONFIGS.work;
  const scoreVal = roleScores[targetRoleKey] ?? 0;
  const bestScore = instance.score_best ?? Math.max(...Object.values(roleScores));

  // If no role sort is active and pal has 0 score across all roles, hide or keep minimal
  const hasAnyScore = Object.values(roleScores).some((s) => s !== 0);
  if (!activeRole && !hasAnyScore) {
    return null;
  }

  const handleMouseMove = (e) => {
    const cardWidth = 320;
    const cardHeight = 260;
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

  const scoreFormatted = scoreVal > 0 ? `+${scoreVal}` : `${scoreVal}`;

  return (
    <>
      <span
        onMouseEnter={handleMouseMove}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setPos(null)}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.25rem',
          padding: '0.12rem 0.45rem',
          borderRadius: '5px',
          fontSize: '0.68rem',
          fontWeight: 700,
          background: roleCfg.bg,
          border: `1px solid ${roleCfg.border}`,
          color: roleCfg.color,
          cursor: 'pointer',
          whiteSpace: 'nowrap',
          userSelect: 'none',
          boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
          transition: 'all 0.12s ease',
          ...style,
        }}
        title="Hover to view 4-Aspect Passive Role breakdown"
      >
        <span>{roleCfg.icon}</span>
        <span>{roleCfg.short}</span>
        <span style={{ fontWeight: 800 }}>{scoreFormatted}</span>
      </span>

      {pos &&
        createPortal(
          <div
            style={{
              position: 'fixed',
              top: `${pos.top}px`,
              left: `${pos.left}px`,
              width: '320px',
              backgroundColor: '#0f172a',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              boxShadow: '0 12px 30px rgba(0, 0, 0, 0.65)',
              borderRadius: '8px',
              padding: '0.65rem 0.75rem',
              zIndex: 99999,
              pointerEvents: 'none',
              fontFamily: 'inherit',
              color: '#f8fafc',
            }}
          >
            {/* Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                paddingBottom: '0.4rem',
                marginBottom: '0.5rem',
              }}
            >
              <span style={{ fontWeight: 800, fontSize: '0.78rem', color: 'var(--accent-gold, #fbbf24)' }}>
                🎯 Passive Role Evaluation
              </span>
              <span
                style={{
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  color: ROLE_CONFIGS[bestRoleKey]?.color || '#fff',
                  background: ROLE_CONFIGS[bestRoleKey]?.bg || 'rgba(255,255,255,0.1)',
                  border: `1px solid ${ROLE_CONFIGS[bestRoleKey]?.border || 'transparent'}`,
                  padding: '0.05rem 0.3rem',
                  borderRadius: '4px',
                }}
              >
                Best: {ROLE_CONFIGS[bestRoleKey]?.label} ({bestScore > 0 ? `+${bestScore}` : bestScore})
              </span>
            </div>

            {/* 4 Roles List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
              {Object.entries(ROLE_CONFIGS).map(([key, cfg]) => {
                const s = roleScores[key] ?? 0;
                const breakdownList = roleBreakdown[key] || [];
                const isTarget = key === targetRoleKey;

                return (
                  <div
                    key={key}
                    style={{
                      background: isTarget ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.25)',
                      border: isTarget ? `1px solid ${cfg.border}` : '1px solid rgba(255,255,255,0.05)',
                      borderRadius: '5px',
                      padding: '0.3rem 0.45rem',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        color: cfg.color,
                      }}
                    >
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <span>{cfg.icon}</span>
                        <span>{cfg.label}</span>
                      </span>
                      <span style={{ fontWeight: 800 }}>
                        {s > 0 ? `+${s}` : s} pts
                      </span>
                    </div>

                    {breakdownList.length > 0 ? (
                      <div
                        style={{
                          marginTop: '0.2rem',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.1rem',
                          fontSize: '0.65rem',
                          color: '#cbd5e1',
                          paddingLeft: '0.35rem',
                        }}
                      >
                        {breakdownList.map(([pName, pts], pIdx) => (
                          <div key={pIdx} style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span>• {pName}</span>
                            <span
                              style={{
                                color: pts > 0 ? '#86efac' : '#fca5a5',
                                fontWeight: 700,
                              }}
                            >
                              {pts > 0 ? `+${pts}` : pts}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div
                        style={{
                          marginTop: '0.15rem',
                          fontSize: '0.63rem',
                          color: 'var(--text-muted, #64748b)',
                          fontStyle: 'italic',
                          paddingLeft: '0.35rem',
                        }}
                      >
                        No modifiers
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>,
          document.body
        )}
    </>
  );
}
