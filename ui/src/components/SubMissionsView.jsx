import React, { useState, useEffect } from 'react';

export function SubMissionsView() {
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterMode, setFilterMode] = useState('all'); // 'all', 'ready', 'missing'
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    setLoading(true);
    fetch('/api/save/missions')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setLocations(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching sub-missions:', err);
        setLoading(false);
      });
  }, []);

  if (loading && (!locations || locations.length === 0)) return <p style={{ color: 'var(--text-secondary)' }}>Evaluating active sub-missions...</p>;
  if (!loading && (!locations || locations.length === 0)) return <p style={{ color: 'var(--text-secondary)' }}>No active sub-missions found in your save file.</p>;

  const totalMissionsCount = locations.reduce((sum, loc) => sum + loc.total_missions, 0);
  const totalReadyCount = locations.reduce((sum, loc) => sum + loc.ready_missions, 0);
  const totalMissingCount = totalMissionsCount - totalReadyCount;

  // Filter locations & missions based on filterMode and searchQuery
  const filteredLocations = locations.map(loc => {
    const filteredMissions = loc.missions.filter(m => {
      if (filterMode === 'ready' && !m.is_ready) return false;
      if (filterMode === 'missing' && m.is_ready) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchName = m.name?.toLowerCase().includes(q);
        const matchNpc = m.npc_name?.toLowerCase().includes(q);
        const matchLoc = loc.location?.toLowerCase().includes(q);
        const matchItem = m.required_items?.some(it => it.name?.toLowerCase().includes(q));
        const matchPal = m.required_pals?.some(pl => pl.name?.toLowerCase().includes(q));
        if (!matchName && !matchNpc && !matchLoc && !matchItem && !matchPal) return false;
      }
      return true;
    });
    return {
      ...loc,
      missions: filteredMissions,
      visible_count: filteredMissions.length
    };
  }).filter(loc => loc.visible_count > 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      {/* Top Controls Bar */}
      <div style={{ flexShrink: 0, marginBottom: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          <h2 style={{ margin: 0, fontWeight: 800, fontSize: '1.25rem', marginRight: '0.5rem' }}>📜 Active NPC Sub-Missions</h2>
          <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
            <button
              className={`pill-btn ${filterMode === 'all' ? 'active' : ''}`}
              onClick={() => setFilterMode('all')}
              style={{ fontSize: '0.8rem', padding: '0.3rem 0.75rem', fontWeight: 700 }}
            >
              📋 All Missions ({totalMissionsCount})
            </button>
            <button
              className={`pill-btn ${filterMode === 'ready' ? 'active' : ''}`}
              onClick={() => setFilterMode('ready')}
              style={{
                fontSize: '0.8rem',
                padding: '0.3rem 0.75rem',
                fontWeight: 700,
                background: filterMode === 'ready' ? '#10b981' : undefined,
                color: filterMode === 'ready' ? '#fff' : undefined,
                border: filterMode === 'ready' ? '1px solid #059669' : undefined
              }}
            >
              🟢 Ready to Turn In ({totalReadyCount})
            </button>
            <button
              className={`pill-btn ${filterMode === 'missing' ? 'active' : ''}`}
              onClick={() => setFilterMode('missing')}
              style={{
                fontSize: '0.8rem',
                padding: '0.3rem 0.75rem',
                fontWeight: 700,
                background: filterMode === 'missing' ? 'rgba(239, 68, 68, 0.25)' : undefined,
                color: filterMode === 'missing' ? '#f87171' : undefined,
                border: filterMode === 'missing' ? '1px solid rgba(239, 68, 68, 0.5)' : undefined
              }}
            >
              🔴 Incomplete Only ({totalMissingCount})
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input
            type="text"
            placeholder="Search mission, NPC, or item..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: '0.35rem 0.75rem',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              background: 'rgba(0,0,0,0.25)',
              color: 'var(--text-primary)',
              fontSize: '0.82rem',
              width: '230px'
            }}
          />
        </div>
      </div>

      {/* Grouped Location List */}
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0, paddingRight: '0.4rem', paddingBottom: '2.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {filteredLocations.length === 0 ? (
          <p style={{ color: 'var(--text-secondary)', padding: '1.5rem 0', textAlign: 'center' }}>
            {filterMode === 'ready' ? 'No missions are currently ready to turn in.' : filterMode === 'missing' ? 'All active missions have requirements fulfilled!' : 'No missions matched your search criteria.'}
          </p>
        ) : (
          filteredLocations.map((loc, lIdx) => (
            <div key={lIdx} style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
              {/* Distinct Settlement Banner Header */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.5rem 0.85rem',
                background: 'linear-gradient(90deg, rgba(59, 130, 246, 0.2) 0%, rgba(59, 130, 246, 0.03) 100%)',
                borderLeft: '4px solid #3b82f6',
                borderRadius: '6px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                  <span style={{ fontSize: '1.05rem', fontWeight: 800, color: '#93c5fd' }}>📍 {loc.location}</span>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.3)', padding: '0.1rem 0.5rem', borderRadius: '4px' }}>
                    {loc.ready_missions} / {loc.total_missions} Ready
                  </span>
                </div>
                {loc.has_batch_turnin && (
                  <span style={{ fontSize: '0.72rem', fontWeight: 800, padding: '0.18rem 0.55rem', borderRadius: '4px', background: 'rgba(99, 102, 241, 0.25)', color: '#a5b4fc', border: '1px solid rgba(99, 102, 241, 0.5)' }}>
                    ✨ BATCH TURN-IN ({loc.ready_missions} Quests Ready)
                  </span>
                )}
              </div>

              {/* 2-Line Structured Mission Cards */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                {loc.missions.map((m, mIdx) => {
                  const isReady = m.is_ready;
                  const isGivePal = m.requires_giving_pal;
                  return (
                    <div
                      key={mIdx}
                      className="glass-card table-row-hover"
                      style={{
                        padding: '0.65rem 0.95rem',
                        borderRadius: '8px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.4rem',
                        border: isReady ? '1.5px solid rgba(16, 185, 129, 0.55)' : '1.5px solid rgba(239, 68, 68, 0.4)',
                        background: isReady ? 'rgba(16, 185, 129, 0.04)' : 'rgba(239, 68, 68, 0.03)'
                      }}
                    >
                      {/* Line 1: Quest Title | NPC | Surrender Alert <---> Prominent Gold Reward */}
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
                          <span style={{ fontWeight: 800, fontSize: '0.98rem', color: 'var(--text-primary)' }}>
                            {m.name}
                          </span>
                          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                            • NPC: <strong style={{ color: 'var(--text-primary)' }}>{m.npc_name}</strong>
                          </span>
                          {isGivePal && (
                            <span style={{ fontSize: '0.68rem', fontWeight: 800, padding: '0.12rem 0.45rem', borderRadius: '4px', background: 'rgba(239, 68, 68, 0.25)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.5)' }}>
                              ⚠️ GIVES PAL (SURRENDER)
                            </span>
                          )}
                        </div>

                        {/* Prominent Gold Reward */}
                        {m.rewards && (
                          <div style={{
                            fontSize: '0.86rem',
                            fontWeight: 700,
                            color: '#fbbf24',
                            background: 'rgba(251, 191, 36, 0.12)',
                            border: '1px solid rgba(251, 191, 36, 0.3)',
                            padding: '0.2rem 0.6rem',
                            borderRadius: '5px',
                            whiteSpace: 'nowrap',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.35rem'
                          }}>
                            <span>🎁 <strong>Reward:</strong> {m.rewards}</span>
                          </div>
                        )}
                      </div>

                      {/* Line 2: Clean, Compact Requirements Bar */}
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        fontSize: '0.8rem',
                        background: 'rgba(0,0,0,0.22)',
                        padding: '0.3rem 0.6rem',
                        borderRadius: '5px',
                        flexWrap: 'wrap'
                      }}>
                        <span style={{ color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Target:
                        </span>
                        {m.required_items && m.required_items.map((it, idx) => (
                          <span
                            key={idx}
                            style={{
                              color: it.is_met ? '#34d399' : '#f87171',
                              fontWeight: 500,
                              background: it.is_met ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                              padding: '0.1rem 0.4rem',
                              borderRadius: '4px',
                              border: `1px solid ${it.is_met ? 'rgba(52, 211, 153, 0.25)' : 'rgba(239, 68, 68, 0.25)'}`
                            }}
                          >
                            📦 {it.name}: <strong>{it.count_have}</strong> / {it.count_required} {it.is_met ? '✓' : '✗'}
                          </span>
                        ))}
                        {m.required_pals && m.required_pals.map((pl, idx) => (
                          <span
                            key={idx}
                            style={{
                              color: pl.is_met ? '#34d399' : '#f87171',
                              fontWeight: 500,
                              background: pl.is_met ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                              padding: '0.1rem 0.4rem',
                              borderRadius: '4px',
                              border: `1px solid ${pl.is_met ? 'rgba(52, 211, 153, 0.25)' : 'rgba(239, 68, 68, 0.25)'}`,
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.4rem'
                            }}
                          >
                            <span>🐾 {pl.name}: <strong>{pl.count_have}</strong> / {pl.count_required} {pl.is_met ? '✓' : '✗'}</span>
                            {pl.locations && pl.locations.length > 0 && (
                              <span style={{
                                fontSize: '0.68rem',
                                padding: '0.05rem 0.35rem',
                                borderRadius: '3px',
                                background: 'rgba(59, 130, 246, 0.2)',
                                color: '#93c5fd',
                                border: '1px solid rgba(59, 130, 246, 0.4)',
                                fontWeight: 700,
                                letterSpacing: '0.3px'
                              }}>
                                📍 {pl.locations.join(', ')}
                              </span>
                            )}
                          </span>
                        ))}
                        {(!m.required_items || m.required_items.length === 0) && (!m.required_pals || m.required_pals.length === 0) && (
                          <span style={{ color: 'var(--text-secondary)' }}>
                            🎯 {m.type === 'hunt' ? 'Defeat Field Boss' : m.type === 'milestone' ? 'Paldex Catch Milestone' : 'Speak to NPC'}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default SubMissionsView;
