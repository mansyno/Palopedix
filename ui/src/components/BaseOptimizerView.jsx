import React, { useState, useEffect } from 'react';

const WORK_TYPE_ASSET_MAP = {
  Kindling: { icon: '/assets/work/Kindling.png', label: 'Kindling' },
  EmitFlame: { icon: '/assets/work/Kindling.png', label: 'Kindling' },
  Watering: { icon: '/assets/work/Watering.png', label: 'Watering' },
  Planting: { icon: '/assets/work/Planting.png', label: 'Planting' },
  Seeding: { icon: '/assets/work/Planting.png', label: 'Planting' },
  GeneratingElectricity: { icon: '/assets/work/GeneratingElectricity.png', label: 'Generating Electricity' },
  Electricity: { icon: '/assets/work/GeneratingElectricity.png', label: 'Generating Electricity' },
  Handcraft: { icon: '/assets/work/Handcraft.png', label: 'Handcraft' },
  Handiwork: { icon: '/assets/work/Handcraft.png', label: 'Handiwork' },
  Gathering: { icon: '/assets/work/Gathering.png', label: 'Gathering' },
  Collection: { icon: '/assets/work/Gathering.png', label: 'Gathering' },
  Lumbering: { icon: '/assets/work/Lumbering.png', label: 'Lumbering' },
  Deforest: { icon: '/assets/work/Lumbering.png', label: 'Lumbering' },
  Mining: { icon: '/assets/work/Mining.png', label: 'Mining' },
  Mine: { icon: '/assets/work/Mining.png', label: 'Mining' },
  Medicine: { icon: '/assets/work/Medicine.png', label: 'Medicine' },
  MedicineProduction: { icon: '/assets/work/Medicine.png', label: 'Medicine' },
  ProductMedicine: { icon: '/assets/work/Medicine.png', label: 'Medicine' },
  Cooling: { icon: '/assets/work/Cooling.png', label: 'Cooling' },
  Cool: { icon: '/assets/work/Cooling.png', label: 'Cooling' },
  Transporting: { icon: '/assets/work/Transport.png', label: 'Transporting' },
  Transport: { icon: '/assets/work/Transport.png', label: 'Transporting' },
  Farming: { icon: '/assets/work/MonsterFarm.png', label: 'Farming' },
  MonsterFarm: { icon: '/assets/work/MonsterFarm.png', label: 'Farming' },
};

export default function BaseOptimizerView() {
  const [baseCamps, setBaseCamps] = useState([]);
  const [selectedBaseId, setSelectedBaseId] = useState('');
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/base_camps')
      .then(res => res.json())
      .then(data => {
        setBaseCamps(data);
        if (data && data.length > 0) {
          setSelectedBaseId(data[0].base_camp_id);
        }
      })
      .catch(err => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selectedBaseId) return;
    setLoading(true);
    setError(null);
    fetch(`/api/base_camps/${encodeURIComponent(selectedBaseId)}/recommendations`)
      .then(res => res.json())
      .then(data => {
        setRecommendation(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [selectedBaseId]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      {/* Fixed Header & Base Camp Selector */}
      <div style={{ flexShrink: 0, marginBottom: '0.75rem' }}>
        <div className="glass-card" style={{ padding: '1rem 1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 800, margin: 0 }}>🏰 Base Optimizer</h2>
            <p style={{ color: 'var(--text-secondary)', margin: '0.2rem 0 0 0', fontSize: '0.85rem' }}>
              Automated work suitability demand matching, nocturnal 24/7 duty cycle bonuses, and food satiety balance.
            </p>
          </div>
          {baseCamps.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <label style={{ fontWeight: 600, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Select Base Camp:</label>
              <select
                value={selectedBaseId}
                onChange={e => setSelectedBaseId(e.target.value)}
                style={{ padding: '0.4rem 0.8rem', borderRadius: '8px', background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', fontWeight: 700, fontSize: '0.85rem' }}
              >
                {baseCamps.map(bc => (
                  <option key={bc.base_camp_id} value={bc.base_camp_id}>
                    {bc.name || `Base Camp ${bc.base_camp_id.slice(0, 8)}`} ({bc.assigned_pals_count}/{bc.max_pals} Pals)
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Scrollable Optimization Results Content */}
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0, paddingRight: '0.4rem', paddingBottom: '2rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

      {loading && (
        <div className="glass-card" style={{ textAlign: 'center', padding: '3rem' }}>
          <p style={{ fontSize: '1.2rem', color: 'var(--text-secondary)' }}>Evaluating work suitabilities & scoring owned Pals...</p>
        </div>
      )}

      {error && (
        <div className="glass-card" style={{ padding: '2rem', borderLeft: '4px solid #ef4444' }}>
          <p style={{ color: '#ef4444', margin: 0 }}>Error loading recommendations: {error}</p>
        </div>
      )}

      {recommendation && !loading && (
        <>
          {/* Summary Dashboard Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem' }}>
            <div className="glass-card" style={{ padding: '1.5rem', textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem', fontWeight: 900, color: 'var(--accent-gold)' }}>
                {recommendation.base_category}
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.25rem' }}>Primary Focus Category</div>
            </div>

            <div className="glass-card" style={{ padding: '1.5rem', textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem', fontWeight: 900, color: '#3b82f6' }}>
                {recommendation.team_size} / {recommendation.max_capacity}
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.25rem' }}>Recommended Team Capacity</div>
            </div>

            <div className="glass-card" style={{ padding: '1.5rem', textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem', fontWeight: 900, color: '#10b981' }}>
                {recommendation.food_and_san_summary?.total_hourly_satiety_drain} pts/hr
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.25rem' }}>Est. Hourly Food Satiety Drain</div>
            </div>

            <div className="glass-card" style={{ padding: '1.5rem', textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem', fontWeight: 900, color: recommendation.food_and_san_summary?.san_stability_status === 'Warning' ? '#ef4444' : '#8b5cf6' }}>
                {recommendation.food_and_san_summary?.san_stability_status}
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.25rem' }}>SAN Stability Rating</div>
            </div>
          </div>

          {/* Recommended Team Table */}
          <div className="glass-card" style={{ padding: '2rem' }}>
            <h3 style={{ fontSize: '1.3rem', fontWeight: 800, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              ⭐ Recommended Base Pal Deployment Team
            </h3>

            {recommendation.recommended_team.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>No recommended Pals found for this base camp.</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                      <th style={{ padding: '0.75rem' }}>#</th>
                      <th style={{ padding: '0.75rem' }}>Pal</th>
                      <th style={{ padding: '0.75rem' }}>Level</th>
                      <th style={{ padding: '0.75rem' }}>24/7 Nocturnal</th>
                      <th style={{ padding: '0.75rem' }}>Work Suitability Roles</th>
                      <th style={{ padding: '0.75rem' }}>Passives</th>
                      <th style={{ padding: '0.75rem' }}>Match Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recommendation.recommended_team.map((pal, idx) => (
                      <tr key={pal.instance_id || idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '1rem 0.75rem', fontWeight: 700 }}>{idx + 1}</td>
                        <td style={{ padding: '1rem 0.75rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                          {pal.icon_path && (
                            <img src={pal.icon_path} alt={pal.display_name} style={{ width: '40px', height: '40px', objectFit: 'contain' }} />
                          )}
                          <span style={{ fontWeight: 700, fontSize: '1.05rem' }}>{pal.display_name}</span>
                        </td>
                        <td style={{ padding: '1rem 0.75rem' }}>Lv. {pal.level}</td>
                        <td style={{ padding: '1rem 0.75rem' }}>
                          {pal.nocturnal ? (
                            <span style={{ background: 'rgba(139, 92, 246, 0.2)', color: '#a78bfa', padding: '0.25rem 0.6rem', borderRadius: '12px', fontSize: '0.85rem', fontWeight: 700 }}>
                              🌙 24/7 Nocturnal
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>☀️ Diurnal</span>
                          )}
                        </td>

                        <td style={{ padding: '1rem 0.75rem' }}>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                            {pal.matching_roles.map(r => {
                              const assetData = WORK_TYPE_ASSET_MAP[r.work_type] || {};
                              return (
                                <span key={r.work_type} style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', padding: '0.25rem 0.6rem', borderRadius: '6px', fontSize: '0.82rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.35rem', border: '1px solid rgba(59, 130, 246, 0.25)' }}>
                                  {assetData.icon ? (
                                    <img 
                                      src={assetData.icon} 
                                      alt={r.work_type} 
                                      style={{ width: '16px', height: '16px', objectFit: 'contain' }} 
                                      onError={(e) => { e.target.style.display = 'none'; }} 
                                    />
                                  ) : (
                                    <span>{assetData.emoji || '⚡'}</span>
                                  )}
                                  <span>{r.work_type}</span>
                                  <strong style={{ color: 'var(--accent-gold)' }}>Lv.{r.level}</strong>
                                </span>
                              );
                            })}
                          </div>
                        </td>
                        <td style={{ padding: '1rem 0.75rem' }}>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                            {pal.passives.map(p => (
                              <span key={p} style={{ background: 'rgba(255, 255, 255, 0.08)', padding: '0.15rem 0.5rem', borderRadius: '4px', fontSize: '0.8rem' }}>
                                {p}
                              </span>
                            ))}
                            {pal.passives.length === 0 && <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>None</span>}
                          </div>
                        </td>
                        <td style={{ padding: '1rem 0.75rem', fontWeight: 800, color: 'var(--accent-gold)' }}>
                          {pal.total_score} pts
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
      </div>
    </div>
  );
}
