import React, { useState, useEffect } from 'react';
import { PalInstanceTooltip } from './common/PalInstanceTooltip';
import { PassiveBadge } from './common/PassiveBadge';

export function CondenserView() {
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterSpecies, setFilterSpecies] = useState('');

  useEffect(() => {
    setLoading(true);
    fetch('/api/save/condense')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setCandidates(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching condenser candidates:', err);
        setLoading(false);
      });
  }, []);

  const filteredCandidates = candidates.filter(c => {
    if (filterSpecies && !(c.species || '').toLowerCase().includes(filterSpecies.toLowerCase())) return false;
    return true;
  });

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-secondary)' }}>Calculating condenser candidates...</p>
      </div>
    );
  }

  if (!candidates || candidates.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-secondary)' }}>No save file loaded or no duplicate Pals found.</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      {/* Header & Filter */}
      <div style={{ flexShrink: 0, marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.5rem' }}>
          <div>
            <h2 style={{ marginBottom: '0.2rem', fontWeight: 800, fontSize: '1.4rem' }}>⭐ Condenser Recommendations</h2>
            <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.82rem' }}>
              Based on duplicates, passives, and IVs. Max rank calculates exact fodder threshold (4, 16, 32, or 64 sacrifices).
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <input
              type="text"
              placeholder="Filter species..."
              value={filterSpecies}
              onChange={e => setFilterSpecies(e.target.value)}
              style={{ padding: '0.4rem 0.8rem', borderRadius: '6px', background: 'rgba(10, 15, 30, 0.6)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', fontSize: '0.82rem' }}
            />
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 600 }}>
              Tracking <strong style={{ color: 'var(--accent-gold)' }}>{filteredCandidates.length}</strong> upgradeable species
            </div>
          </div>
        </div>
      </div>

      {/* Main Candidates Cards List */}
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0, paddingRight: '0.4rem', paddingBottom: '2rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
        {filteredCandidates.map((c, i) => {
          const candPal = {
            ...c,
            display_name: c.species,
            level: c.base_level,
            location: c.best_location,
            rank: c.attainable_stars || 0,
            ivs: { hp: c.iv_hp, melee: c.iv_attack, defense: c.iv_defense },
          };
          return (
            <div key={`${c.species}-${i}`} className="glass-card" style={{ display: 'flex', gap: '1rem', padding: '0.75rem 1.1rem', alignItems: 'center' }}>
              <div style={{ flex: '0 0 76px', textAlign: 'center' }}>
                <PalInstanceTooltip instance={candPal}>
                  <div style={{ cursor: 'help' }}>
                    {c.icon_path ? (
                      <img src={c.icon_path} alt={c.species} style={{ width: '56px', height: '56px', borderRadius: '10px', objectFit: 'cover' }} onError={(e) => { e.target.style.display = 'none'; }} />
                    ) : (
                      <div style={{ width: '56px', height: '56px', borderRadius: '10px', background: 'var(--primary-gradient)', margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.4rem', fontWeight: 800 }}>
                        {c.species ? c.species[0] : '⭐'}
                      </div>
                    )}
                    <div style={{ marginTop: '0.25rem', fontSize: '0.85rem', fontWeight: 700, lineHeight: 1.2, wordBreak: 'break-word' }}>{c.species}</div>
                  </div>
                </PalInstanceTooltip>
                <div style={{ color: 'var(--accent-gold)', fontWeight: 700, fontSize: '0.82rem', marginTop: '0.1rem' }}>
                  {c.attainable_stars > 0 ? '⭐'.repeat(c.attainable_stars) : '0 ⭐'}
                </div>
              </div>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.35rem', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                      Total Owned: <strong style={{ color: 'var(--accent-gold)' }}>{c.total_owned}</strong> (1 Base + {c.sacrifices_available} Sacrifices)
                    </span>
                    {c.best_location && (
                      <span className="badge" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.3)', fontSize: '0.72rem' }}>
                        📍 Base Pal: {c.best_location}
                      </span>
                    )}
                  </div>
                  <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--accent-gold)', background: 'rgba(251, 191, 36, 0.1)', padding: '0.15rem 0.5rem', borderRadius: '4px', border: '1px solid rgba(251, 191, 36, 0.25)' }}>
                    Lv. {c.base_level}
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                  <div style={{ flex: '1 1 200px', minWidth: 0 }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>
                      Passives & Partner Groups:
                    </div>
                    <div className="badge-container" style={{ margin: 0, marginBottom: '0.3rem', flexWrap: 'wrap', gap: '0.3rem', alignItems: 'center' }}>
                      {c.passives && c.passives.length > 0 ? c.passives.map((p, idx) => (
                        <PassiveBadge key={idx} skill={p} size="sm" />
                      )) : <span style={{ color: 'var(--text-secondary)', fontSize: '0.78rem' }}>None</span>}
                      {c.partner_skill_categories && c.partner_skill_categories.map(cat => (
                        <span key={cat.id} className="badge" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#a5b4fc', border: '1px solid rgba(99, 102, 241, 0.3)', fontSize: '0.72rem', padding: '0.15rem 0.45rem', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                          <span>{cat.icon}</span>
                          <span>{cat.name}</span>
                        </span>
                      ))}
                    </div>
                    {c.locations_breakdown && (
                      <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                        {Object.entries(c.locations_breakdown).map(([locName, count]) => (
                          <span key={locName} style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.05)', padding: '0.1rem 0.4rem', borderRadius: '4px' }}>
                            {locName}: {count}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div style={{ flexShrink: 0 }}>
                    <div style={{ display: 'flex', gap: '0.4rem', background: 'rgba(0,0,0,0.25)', padding: '0.35rem 0.6rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)' }}>
                      <div style={{ textAlign: 'center', minWidth: '46px' }}>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '0.68rem', textTransform: 'uppercase' }}>HP</div>
                        <div style={{ fontWeight: 700, fontSize: '0.8rem', color: 'var(--text-primary)' }}>{c.hp}</div>
                        <div style={{ color: 'var(--accent-gold)', fontSize: '0.7rem', fontWeight: 600 }}>IV {c.iv_hp}</div>
                      </div>
                      <div style={{ width: '1px', background: 'rgba(255,255,255,0.08)' }}></div>
                      <div style={{ textAlign: 'center', minWidth: '46px' }}>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '0.68rem', textTransform: 'uppercase' }}>Atk</div>
                        <div style={{ fontWeight: 700, fontSize: '0.8rem', color: 'var(--text-primary)' }}>{c.attack}</div>
                        <div style={{ color: 'var(--accent-gold)', fontSize: '0.7rem', fontWeight: 600 }}>IV {c.iv_attack}</div>
                      </div>
                      <div style={{ width: '1px', background: 'rgba(255,255,255,0.08)' }}></div>
                      <div style={{ textAlign: 'center', minWidth: '46px' }}>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '0.68rem', textTransform: 'uppercase' }}>Def</div>
                        <div style={{ fontWeight: 700, fontSize: '0.8rem', color: 'var(--text-primary)' }}>{c.defense}</div>
                        <div style={{ color: 'var(--accent-gold)', fontSize: '0.7rem', fontWeight: 600 }}>IV {c.iv_defense}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default CondenserView;
