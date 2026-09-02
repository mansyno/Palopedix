import React, { useState, useEffect, useMemo, useRef } from 'react';
import { PalInstanceTooltip } from './common/PalInstanceTooltip';
import { PassiveBadge } from './common/PassiveBadge';
import { WORK_TYPE_ASSET_MAP, CATEGORY_STYLES } from '../constants/gameData';

export default function BaseOptimizerView({ pals = [], setSelectedPal }) {
  const [baseCamps, setBaseCamps] = useState([]);
  const [selectedBaseId, setSelectedBaseId] = useState('');
  const [targetTeamSize, setTargetTeamSize] = useState('max'); // 'max', 'current', or custom number
  const [reservedBreeding, setReservedBreeding] = useState('auto'); // 'auto', '0', '2', '4', '6', '8'
  const [recommendation, setRecommendation] = useState(null);
  const recsCache = useRef({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Sorting state
  const [sortCol, setSortCol] = useState('#');
  const [sortDesc, setSortDesc] = useState(false);

  useEffect(() => {
    fetch('/api/base_camps')
      .then(res => res.json())
      .then(data => {
        const arr = Array.isArray(data) ? data : [];
        setBaseCamps(arr);
        if (arr.length > 0) {
          setSelectedBaseId(arr[0].base_camp_id);
        }
      })
      .catch(err => setError(err.message));
  }, []);

  const activeBase = baseCamps.find(bc => bc.base_camp_id === selectedBaseId) || null;

  // Build query parameters
  const queryParams = useMemo(() => {
    const params = new URLSearchParams();
    if (activeBase) {
      if (targetTeamSize === 'current') {
        params.set('max_team_size', String(activeBase.assigned_pals_count || 1));
      } else if (targetTeamSize !== 'max' && !isNaN(parseInt(targetTeamSize))) {
        params.set('max_team_size', targetTeamSize);
      }
    }
    if (reservedBreeding !== 'auto' && !isNaN(parseInt(reservedBreeding))) {
      params.set('reserved_breeding', reservedBreeding);
    }
    const qStr = params.toString();
    return qStr ? `?${qStr}` : '';
  }, [activeBase, targetTeamSize, reservedBreeding]);

  const cacheKey = `${selectedBaseId}_${targetTeamSize}_${reservedBreeding}`;

  useEffect(() => {
    if (!selectedBaseId) return;
    if (recsCache.current[cacheKey]) {
      setRecommendation(recsCache.current[cacheKey]);
      return;
    }
    setLoading(true);
    setError(null);
    fetch(`/api/base_camps/${encodeURIComponent(selectedBaseId)}/recommendations${queryParams}`)
      .then(res => res.json())
      .then(data => {
        recsCache.current[cacheKey] = data;
        setRecommendation(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [selectedBaseId, queryParams, cacheKey]);

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDesc(prev => !prev);
    } else {
      setSortCol(col);
      setSortDesc(false);
    }
  };

  // Sorted team list
  const sortedTeam = useMemo(() => {
    if (!recommendation || !recommendation.recommended_team) return [];
    const list = [...recommendation.recommended_team].map((p, origIdx) => ({ ...p, _origRank: origIdx + 1 }));

    list.sort((a, b) => {
      let valA, valB;
      switch (sortCol) {
        case '#':
          valA = a._origRank;
          valB = b._origRank;
          break;
        case 'name':
          valA = (a.display_name || a.species || '').toLowerCase();
          valB = (b.display_name || b.species || '').toLowerCase();
          break;
        case 'level':
          valA = a.level || 0;
          valB = b.level || 0;
          break;
        case 'cycle':
          valA = a.nocturnal ? 1 : 0;
          valB = b.nocturnal ? 1 : 0;
          break;
        case 'location':
          valA = (a.location_details_base_camp_name || a.location_details?.base_camp_name || a.location || 'palbox').toLowerCase();
          valB = (b.location_details_base_camp_name || b.location_details?.base_camp_name || b.location || 'palbox').toLowerCase();
          break;
        default:
          valA = a._origRank;
          valB = b._origRank;
      }
      if (valA < valB) return sortDesc ? 1 : -1;
      if (valA > valB) return sortDesc ? -1 : 1;
      return 0;
    });

    return list;
  }, [recommendation, sortCol, sortDesc]);

  const catStyle = recommendation ? (CATEGORY_STYLES[recommendation.base_category] || CATEGORY_STYLES['Balanced']) : null;

  // Practical food calculations:
  // 1 in-game day (day + night) = ~30 minutes (0.5 hr).
  // Baked Berries = 21 satiety, Salad = 84 satiety.
  const hourlyFoodDrain = recommendation?.food_and_san_summary?.total_hourly_satiety_drain || 0;
  const dailyFoodDrain = hourlyFoodDrain * 0.5;
  const dailyBakedBerries = Math.ceil(dailyFoodDrain / 21);
  const dailySalads = Math.ceil(dailyFoodDrain / 84);
  const hourlyBakedBerries = Math.ceil(hourlyFoodDrain / 21);

  // Demand entries for requirements bar
  const demandEntries = recommendation?.demand_summary ? Object.entries(recommendation.demand_summary) : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      {/* Top Toolbar & Summary Stat Bar */}
      <div style={{ flexShrink: 0, marginBottom: '0.4rem' }}>
        <div className="glass-card" style={{ padding: '0.55rem 0.85rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.6rem' }}>
          
          {/* Base Selector, Target Capacity & Breeding Reservation */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            {baseCamps.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <label style={{ fontWeight: 700, color: 'var(--text-secondary)', fontSize: '0.78rem', whiteSpace: 'nowrap' }}>🏰 Base:</label>
                <select
                  value={selectedBaseId}
                  onChange={e => setSelectedBaseId(e.target.value)}
                  style={{ padding: '0.3rem 0.6rem', borderRadius: '6px', background: 'rgba(10, 15, 30, 0.6)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', fontWeight: 600, fontSize: '0.8rem', width: 'auto' }}
                >
                  {baseCamps.map(bc => {
                    const bName = bc.custom_name || bc.display_name || bc.name || `Base Camp ${bc.base_camp_id.slice(0, 8)}`;
                    return (
                      <option key={bc.base_camp_id} value={bc.base_camp_id}>
                        {bName} ({bc.assigned_pals_count}/{bc.max_pals} Pals)
                      </option>
                    );
                  })}
                </select>
              </div>
            )}

            {activeBase && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <label style={{ fontWeight: 700, color: 'var(--text-secondary)', fontSize: '0.78rem', whiteSpace: 'nowrap' }}>🎯 Target Size:</label>
                <select
                  value={targetTeamSize}
                  onChange={e => setTargetTeamSize(e.target.value)}
                  style={{ padding: '0.3rem 0.6rem', borderRadius: '6px', background: 'rgba(10, 15, 30, 0.6)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', fontWeight: 600, fontSize: '0.78rem', width: 'auto' }}
                >
                  <option value="max">Full Max ({activeBase.max_pals} Pals)</option>
                  {activeBase.assigned_pals_count !== activeBase.max_pals && (
                    <option value="current">Current Crew ({activeBase.assigned_pals_count} Pals)</option>
                  )}
                  <option value="10">10 Pals (Compact)</option>
                  <option value="15">15 Pals (Standard)</option>
                  <option value="20">20 Pals (Max World)</option>
                </select>
              </div>
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <label style={{ fontWeight: 700, color: 'var(--text-secondary)', fontSize: '0.78rem', whiteSpace: 'nowrap' }}>🐣 Breeding Slots:</label>
              <select
                value={reservedBreeding}
                onChange={e => setReservedBreeding(e.target.value)}
                style={{ padding: '0.3rem 0.6rem', borderRadius: '6px', background: 'rgba(10, 15, 30, 0.6)', color: 'var(--text-primary)', border: '1px solid var(--border-color)', fontWeight: 600, fontSize: '0.78rem', width: 'auto' }}
              >
                <option value="auto">Auto ({recommendation?.reserved_breeding_slots !== undefined ? recommendation.reserved_breeding_slots : 2} default)</option>
                <option value="0">0 (No Breeding)</option>
                <option value="2">2 (1 Pair)</option>
                <option value="4">4 (2 Pairs)</option>
                <option value="6">6 (3 Pairs)</option>
                <option value="8">8 (4 Pairs)</option>
              </select>
            </div>
          </div>

          {/* Real-Time Stats & Practical Food Units */}
          {recommendation && !loading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap' }}>
              {catStyle && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: catStyle.bg, border: `1px solid ${catStyle.border}`, padding: '0.25rem 0.55rem', borderRadius: '6px', fontSize: '0.75rem' }}>
                  <span>{catStyle.emoji}</span>
                  <span style={{ color: 'var(--text-secondary)' }}>Focus:</span>
                  <strong style={{ color: catStyle.color }}>{recommendation.base_category}</strong>
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.25)', padding: '0.25rem 0.55rem', borderRadius: '6px', fontSize: '0.75rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Team:</span>
                <strong style={{ color: '#60a5fa' }}>{recommendation.team_size} / {recommendation.effective_capacity || recommendation.max_capacity}</strong>
              </div>

              {recommendation.reserved_breeding_slots > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', background: 'rgba(236, 72, 153, 0.12)', border: '1px solid rgba(236, 72, 153, 0.3)', padding: '0.25rem 0.55rem', borderRadius: '6px', fontSize: '0.75rem' }} title={`${recommendation.reserved_breeding_slots} slots reserved for breeding pairs`}>
                  <span>🐣</span>
                  <span style={{ color: '#f472b6', fontWeight: 600 }}>{recommendation.reserved_breeding_slots} Reserved</span>
                </div>
              )}

              {/* Practical Food Calculation Tooltip */}
              <div 
                style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.25)', padding: '0.25rem 0.55rem', borderRadius: '6px', fontSize: '0.75rem', cursor: 'help' }}
                title={`Drain Rate: ${hourlyFoodDrain} pts/hr\n• Baked Berries (21 satiety): ~${dailyBakedBerries} / in-game day (~${hourlyBakedBerries} / real hr)\n• Salads (84 satiety): ~${dailySalads} / in-game day`}
              >
                <span>🍖</span>
                <span style={{ color: 'var(--text-secondary)' }}>Food:</span>
                <strong style={{ color: '#34d399' }}>~{dailyBakedBerries} Baked Berries/day</strong>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.7rem' }}>({dailySalads} Salad)</span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: recommendation.food_and_san_summary?.san_stability_status === 'Warning' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(139, 92, 246, 0.12)', border: recommendation.food_and_san_summary?.san_stability_status === 'Warning' ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(139, 92, 246, 0.25)', padding: '0.25rem 0.55rem', borderRadius: '6px', fontSize: '0.75rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>SAN:</span>
                <strong style={{ color: recommendation.food_and_san_summary?.san_stability_status === 'Warning' ? '#ef4444' : '#a78bfa' }}>{recommendation.food_and_san_summary?.san_stability_status}</strong>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Required Base Work Suitabilities Bar */}
      {recommendation && !loading && demandEntries.length > 0 && (
        <div className="glass-card" style={{ flexShrink: 0, marginBottom: '0.4rem', padding: '0.4rem 0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', background: 'rgba(15, 23, 42, 0.4)' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>🛠️ Required Camp Roles:</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}>
            {demandEntries.map(([wsKey, dInfo]) => {
              const asset = WORK_TYPE_ASSET_MAP[wsKey] || { emoji: '⚡', label: wsKey };
              const isCovered = !recommendation.uncovered_suitabilities?.includes(wsKey);
              return (
                <span 
                  key={wsKey}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                    padding: '0.15rem 0.45rem',
                    borderRadius: '5px',
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    background: isCovered ? 'rgba(59, 130, 246, 0.12)' : 'rgba(239, 68, 68, 0.15)',
                    border: `1px solid ${isCovered ? 'rgba(59, 130, 246, 0.25)' : 'rgba(239, 68, 68, 0.35)'}`,
                    color: isCovered ? 'var(--text-primary)' : '#f87171',
                  }}
                  title={`Facilities: ${dInfo.facility_count}x | Urgency: ${dInfo.urgency_weight}x | Automated: ${dInfo.is_automated ? 'Yes' : 'Manual'}`}
                >
                  {asset.icon ? (
                    <img src={asset.icon} alt={wsKey} style={{ width: '13px', height: '13px', objectFit: 'contain' }} onError={(e) => { e.target.style.display = 'none'; }} />
                  ) : (
                    <span>{asset.emoji}</span>
                  )}
                  <span>{asset.label || wsKey}</span>
                  <span style={{ color: 'var(--accent-gold)', fontWeight: 700 }}>({dInfo.facility_count}x)</span>
                  {!isCovered && <span style={{ color: '#ef4444', fontSize: '0.68rem', fontWeight: 700 }}>[UNCOVERED]</span>}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Focus Strategy Banner */}
      {recommendation && !loading && catStyle && (
        <div style={{ flexShrink: 0, marginBottom: '0.4rem', background: catStyle.bg, border: `1px solid ${catStyle.border}`, borderRadius: '8px', padding: '0.35rem 0.75rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1rem' }}>{catStyle.emoji}</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{catStyle.desc}</span>
          </div>
          {recommendation.uncovered_suitabilities && recommendation.uncovered_suitabilities.length > 0 && (
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem' }}>
              Uncovered roles: <span style={{ color: '#fbbf24' }}>{recommendation.uncovered_suitabilities.join(', ')}</span>
            </div>
          )}
        </div>
      )}

      {/* Main Table Area */}
      {loading && (
        <div className="glass-card" style={{ textAlign: 'center', padding: '2rem' }}>
          <p style={{ fontSize: '1rem', color: 'var(--text-secondary)' }}>Evaluating work suitabilities, urgency tiers & scoring owned Pals...</p>
        </div>
      )}

      {error && (
        <div className="glass-card" style={{ padding: '1rem', borderLeft: '4px solid #ef4444' }}>
          <p style={{ color: '#ef4444', margin: 0, fontSize: '0.85rem' }}>Error loading recommendations: {error}</p>
        </div>
      )}

      {recommendation && !loading && (
        sortedTeam.length === 0 ? (
          <div className="glass-card" style={{ textAlign: 'center', padding: '2rem' }}>
            <p style={{ color: 'var(--text-secondary)' }}>No recommended Pals found for this base camp.</p>
          </div>
        ) : (
          <div className="glass-card table-container" style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 0, margin: 0, marginBottom: '1.25rem' }}>
            <table>
              <thead>
                <tr>
                  <th onClick={() => handleSort('#')} style={{ width: '40px', textAlign: 'center', cursor: 'pointer' }}>
                    #{sortCol === '#' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                  </th>
                  <th onClick={() => handleSort('name')} style={{ cursor: 'pointer' }}>
                    Pal{sortCol === 'name' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                  </th>
                  <th onClick={() => handleSort('level')} style={{ cursor: 'pointer' }}>
                    Level{sortCol === 'level' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                  </th>
                  <th onClick={() => handleSort('cycle')} style={{ cursor: 'pointer' }}>
                    Cycle{sortCol === 'cycle' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                  </th>
                  <th>Work Suitability Roles</th>
                  <th>Passives</th>
                  <th onClick={() => handleSort('location')} style={{ cursor: 'pointer', whiteSpace: 'nowrap' }}>
                    Location{sortCol === 'location' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedTeam.map((pal) => {
                  const handlePalClick = () => {
                    if (!setSelectedPal) return;
                    const masterPal = pals.find(p => 
                      (p.internal_name && (p.internal_name === pal.character_id || p.internal_name === pal.character_id_raw || p.internal_name === pal.species)) ||
                      (p.id && (p.id === pal.character_id || p.id === pal.character_id_raw || p.id === pal.species)) ||
                      (p.display_name && p.display_name.toLowerCase() === (pal.display_name || pal.species || '').toLowerCase())
                    );
                    setSelectedPal({
                      ...(masterPal || {}),
                      ...pal,
                      isInstance: true,
                      display_name: pal.display_name || pal.species || masterPal?.display_name,
                      paldex_number: masterPal?.paldex_number || pal.paldex_number,
                      partner_skill: masterPal?.partner_skill || pal.partner_skill,
                      partner_skill_categories: (pal.partner_skill_categories && pal.partner_skill_categories.length > 0) ? pal.partner_skill_categories : (masterPal?.partner_skill_categories || []),
                      passives: pal.passives || [],
                      equip_waza: pal.equip_waza || [],
                    });
                  };

                  return (
                    <tr key={pal.instance_id || pal._origRank} onClick={handlePalClick} style={{ cursor: setSelectedPal ? 'pointer' : 'default' }}>
                      <td style={{ textAlign: 'center', fontWeight: 700, color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                        {pal._origRank}
                      </td>
                      <td>
                        <PalInstanceTooltip instance={pal}>
                          <div className="pal-avatar-container">
                            {pal.icon_path && (
                              <img src={pal.icon_path} alt={pal.display_name} className="pal-avatar-small" onError={(e) => { e.target.style.display = 'none'; }} />
                            )}
                            <span style={{ fontWeight: 600, color: 'var(--accent-gold)' }}>{pal.display_name}</span>
                          </div>
                        </PalInstanceTooltip>
                      </td>
                    <td style={{ whiteSpace: 'nowrap' }}>Lv. {pal.level}</td>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {pal.nocturnal ? (
                        <span style={{ background: 'rgba(139, 92, 246, 0.2)', color: '#a78bfa', padding: '0.12rem 0.45rem', borderRadius: '6px', fontSize: '0.72rem', fontWeight: 700, border: '1px solid rgba(139, 92, 246, 0.3)' }}>
                          🌙 24/7
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>☀️ Day</span>
                      )}
                    </td>

                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                        {pal.matching_roles.map(r => {
                          const assetData = WORK_TYPE_ASSET_MAP[r.work_type] || {};
                          return (
                            <span key={r.work_type} style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', padding: '0.12rem 0.4rem', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.25rem', border: '1px solid rgba(59, 130, 246, 0.25)' }}>
                              {assetData.icon ? (
                                <img 
                                  src={assetData.icon} 
                                  alt={r.work_type} 
                                  style={{ width: '13px', height: '13px', objectFit: 'contain' }} 
                                  onError={(e) => { e.target.style.display = 'none'; }} 
                                />
                              ) : (
                                <span style={{ fontSize: '0.72rem' }}>{assetData.emoji || '⚡'}</span>
                              )}
                              <span>{r.work_type}</span>
                              <strong style={{ color: 'var(--accent-gold)' }}>Lv.{r.level}</strong>
                            </span>
                          );
                        })}
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', alignItems: 'center' }}>
                        {pal.passives && pal.passives.map((p, pIdx) => (
                          <PassiveBadge key={p.id || p.name || pIdx} skill={p} size="sm" />
                        ))}
                        {(!pal.passives || pal.passives.length === 0) && <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>None</span>}
                      </div>
                    </td>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {(() => {
                        const loc = pal.location || 'palbox';
                        const baseName = pal.location_details_base_camp_name || pal.location_details?.base_camp_name;
                        const isParty = loc === 'party';
                        const isBase = loc === 'base' || !!baseName;
                        const isDps = loc === 'dps';

                        let bg = 'rgba(100, 116, 139, 0.2)';
                        let color = 'var(--text-secondary)';
                        let border = '1px solid var(--border-color)';
                        let label = '📦 Palbox';

                        if (isParty) {
                          bg = 'rgba(59, 130, 246, 0.2)';
                          color = '#60a5fa';
                          border = '1px solid rgba(59, 130, 246, 0.4)';
                          label = '⚔️ Party';
                        } else if (isBase) {
                          bg = 'rgba(245, 158, 11, 0.2)';
                          color = '#fbbf24';
                          border = '1px solid rgba(245, 158, 11, 0.4)';
                          label = baseName ? `🏰 ${baseName}` : '🏰 Base';
                        } else if (isDps) {
                          bg = 'rgba(168, 85, 247, 0.2)';
                          color = '#c084fc';
                          border = '1px solid rgba(168, 85, 247, 0.4)';
                          label = baseName ? `🔮 Storage (${baseName})` : '🔮 Storage';
                        }

                        return (
                          <span 
                            className="badge" 
                            style={{ background: bg, color: color, border: border, padding: '0.15rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600 }}
                            title={baseName ? `Base: ${baseName}` : `Location: ${loc}`}
                          >
                            {label}
                          </span>
                        );
                      })()}
                    </td>
                  </tr>
                );
              })}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}
