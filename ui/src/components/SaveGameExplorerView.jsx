import React, { useState, useMemo } from 'react';
import { useTableSort } from '../hooks/useTableSort';
import { SkillBadgeWithTooltip } from './common/SkillBadgeWithTooltip';

export function SaveGameExplorerView({
  instances = [],
  pals = [],
  saveLoaded,
  loadedPath,
  handleLoadSave,
  loading,
  setSelectedPal,
}) {
  const [instCategoryFilter, setInstCategoryFilter] = useState('');
  const [locFilter, setLocFilter] = useState('');
  const [specFilter, setSpecFilter] = useState('');
  const [genderFilter, setGenderFilter] = useState('');
  const [minLvlFilter, setMinLvlFilter] = useState('');
  const [passiveFilter, setPassiveFilter] = useState('');

  const filteredInstances = useMemo(() => {
    return instances.filter(pi => {
      if (locFilter && pi.location !== locFilter) return false;
      if (genderFilter && pi.gender !== genderFilter) return false;
      if (minLvlFilter && (pi.level || 0) < parseInt(minLvlFilter, 10)) return false;
      if (specFilter && !(pi.display_name || pi.species || '').toLowerCase().includes(specFilter.toLowerCase())) return false;
      if (passiveFilter && !(pi.passives || []).some(p => ((typeof p === 'string' ? p : p.name || p.id) || '').toLowerCase().includes(passiveFilter.toLowerCase()))) return false;
      if (instCategoryFilter) {
        const cats = (pi.partner_skill_categories && pi.partner_skill_categories.length > 0)
          ? pi.partner_skill_categories
          : (pals.find(p => p.display_name?.toLowerCase() === (pi.display_name || '').toLowerCase())?.partner_skill_categories || []);
        if (!cats.some(c => c.id === instCategoryFilter || c.name?.toLowerCase() === instCategoryFilter.toLowerCase())) {
          return false;
        }
      }
      return true;
    });
  }, [instances, locFilter, genderFilter, minLvlFilter, specFilter, passiveFilter, instCategoryFilter, pals]);

  const {
    sortedData: sortedInstances,
    sortCol,
    sortDesc,
    handleSort,
  } = useTableSort(filteredInstances, 'level', true);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      {/* Load Save Section & Filter Bar */}
      <div style={{ flexShrink: 0, marginBottom: '0.75rem' }}>
        <div className="glass-card" style={{ padding: '0.75rem 1.25rem', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div style={{ fontWeight: 700, fontSize: '0.9rem' }}>
            📂 Save File: <span style={{ color: 'var(--text-secondary)', fontWeight: 400, fontSize: '0.8rem' }}>{loadedPath || 'Auto-discovered'}</span>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button className="btn btn-secondary" style={{ padding: '0.3rem 0.75rem', fontSize: '0.78rem' }} onClick={handleLoadSave} disabled={loading}>
              {loading ? 'Parsing...' : '🔄 Reload Save'}
            </button>
          </div>
        </div>

        {saveLoaded && (
          <>
            <div className="filter-bar glass-card" style={{ marginBottom: '0.5rem', flexWrap: 'wrap' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.2rem', color: 'var(--accent-gold)', fontSize: '0.7rem', fontWeight: 700 }}>🤝 Partner Skill Group</label>
                <select value={instCategoryFilter} onChange={e => setInstCategoryFilter(e.target.value)} style={{ borderColor: 'var(--accent-gold)' }}>
                  <option value="">All Partner Groups</option>
                  <option value="flying_mount">🦅 Flying Mounts</option>
                  <option value="ground_mount">🐎 Ground Mounts</option>
                  <option value="swimming_mount">🌊 Swimming Mounts</option>
                  <option value="glider">🪂 Gliders</option>
                  <option value="ranch_producer">🚜 Ranch Producers</option>
                  <option value="player_element_infusion">⚡ Player Element Infusion</option>
                  <option value="player_combat_buffer">⚔️ Player Combat Buffers</option>
                  <option value="party_pal_buffer">🛡️ Pal / Party Combat Buffers</option>
                  <option value="heavy_artillery">💥 Heavy Artillery & Weapons</option>
                  <option value="coop_attacker">👥 Autonomous Co-Op</option>
                  <option value="healer_lifesteal">💖 Healers & Life-Steal</option>
                  <option value="carrying_capacity">🎒 Carrying Capacity</option>
                  <option value="drop_loot_booster">🎁 Drop & Loot Boosters</option>
                  <option value="resource_gathering">⛏️ Resource Gathering</option>
                  <option value="breeding_egg_booster">🥚 Breeding & Egg Boosters</option>
                  <option value="fishing_helper">🎣 Fishing & Helpers</option>
                  <option value="exploration_survival">🧭 Exploration & Survival</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.2rem', color: 'var(--text-secondary)', fontSize: '0.7rem' }}>Location</label>
                <select value={locFilter} onChange={e => setLocFilter(e.target.value)}>
                  <option value="">All Locations</option>
                  <option value="party">Player Party</option>
                  <option value="palbox">Palbox Storage</option>
                  <option value="base">Base Camp Workers</option>
                  <option value="dps">Dimensional Storage</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.2rem', color: 'var(--text-secondary)', fontSize: '0.7rem' }}>Species</label>
                <input type="text" placeholder="Filter by species..." value={specFilter} onChange={e => setSpecFilter(e.target.value)} />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.2rem', color: 'var(--text-secondary)', fontSize: '0.7rem' }}>Gender</label>
                <select value={genderFilter} onChange={e => setGenderFilter(e.target.value)}>
                  <option value="">All Genders</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.2rem', color: 'var(--text-secondary)', fontSize: '0.7rem' }}>Min Level</label>
                <input type="text" placeholder="Min level..." value={minLvlFilter} onChange={e => setMinLvlFilter(e.target.value)} />
              </div>
            </div>

            {/* Quick Category Filter Pills for Caught Save Pals */}
            <div style={{ display: 'flex', gap: '0.4rem', overflowX: 'auto', paddingBottom: '0.35rem', marginBottom: '0.5rem', scrollbarWidth: 'thin' }}>
              <button
                className={`btn ${!instCategoryFilter ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setInstCategoryFilter('')}
                style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem', borderRadius: '6px', whiteSpace: 'nowrap' }}
              >
                All ({instances.length})
              </button>
              {[
                { id: 'flying_mount', icon: '🦅', name: 'Flying Mounts' },
                { id: 'ground_mount', icon: '🐎', name: 'Ground Mounts' },
                { id: 'ranch_producer', icon: '🚜', name: 'Ranch Producers' },
                { id: 'player_element_infusion', icon: '⚡', name: 'Infusions' },
                { id: 'player_combat_buffer', icon: '⚔️', name: 'Player Buffs' },
                { id: 'heavy_artillery', icon: '💥', name: 'Artillery' },
                { id: 'healer_lifesteal', icon: '💖', name: 'Healers' },
                { id: 'carrying_capacity', icon: '🎒', name: 'Weight' },
                { id: 'resource_gathering', icon: '⛏️', name: 'Gatherers' },
              ].map(c => (
                <button
                  key={c.id}
                  className={`btn ${instCategoryFilter === c.id ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setInstCategoryFilter(instCategoryFilter === c.id ? '' : c.id)}
                  style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem', borderRadius: '6px', whiteSpace: 'nowrap' }}
                >
                  {c.icon} {c.name}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Scrollable Table Area */}
      {saveLoaded ? (
        <div className="glass-card table-container" style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 0, marginBottom: '1.5rem' }}>
          <table>
            <thead>
              <tr>
                <th onClick={() => handleSort('display_name')} style={{ cursor: 'pointer' }}>Species{sortCol === 'display_name' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleSort('level')} style={{ cursor: 'pointer' }}>Level{sortCol === 'level' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleSort('gender')} style={{ cursor: 'pointer' }}>Gender{sortCol === 'gender' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleSort('rank')} style={{ cursor: 'pointer' }}>Rank{sortCol === 'rank' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th>Partner Groups</th>
                <th onClick={() => handleSort('current_speed')} style={{ cursor: 'pointer' }}>Speed (Cur/Base){sortCol === 'current_speed' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th>IVs (HP/Melee/Defense)</th>
                <th onClick={() => handleSort('location')} style={{ cursor: 'pointer' }}>Location{sortCol === 'location' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th>Passives</th>
              </tr>
            </thead>
            <tbody>
              {sortedInstances.map((pi) => {
                const handleRowClick = () => {
                  const masterPal = pals.find(p => 
                    (p.internal_name && (p.internal_name === pi.character_id || p.internal_name === pi.character_id_raw || p.internal_name === pi.species)) ||
                    (p.id && (p.id === pi.character_id || p.id === pi.character_id_raw || p.id === pi.species)) ||
                    (p.display_name && p.display_name.toLowerCase() === (pi.display_name || '').toLowerCase())
                  );
                  setSelectedPal({
                    ...(masterPal || {}),
                    ...pi,
                    isInstance: true,
                    display_name: pi.display_name,
                    paldex_number: masterPal?.paldex_number || pi.paldex_number,
                    partner_skill: masterPal?.partner_skill || pi.partner_skill,
                    partner_skill_categories: (pi.partner_skill_categories && pi.partner_skill_categories.length > 0) ? pi.partner_skill_categories : (masterPal?.partner_skill_categories || []),
                    passives: pi.passives || [],
                    equip_waza: pi.equip_waza || [],
                  });
                };

                const displayCats = (pi.partner_skill_categories && pi.partner_skill_categories.length > 0)
                  ? pi.partner_skill_categories
                  : (pals.find(p => p.display_name?.toLowerCase() === (pi.display_name || '').toLowerCase())?.partner_skill_categories || []);

                return (
                  <tr key={pi.instance_id} onClick={handleRowClick} style={{ cursor: 'pointer' }}>
                    <td style={{ fontWeight: 600 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                        {pi.icon_path ? (
                          <img src={pi.icon_path} alt={pi.display_name} style={{ width: '28px', height: '28px', borderRadius: '6px', objectFit: 'cover', background: 'rgba(0,0,0,0.3)' }} onError={(e) => { e.target.style.display = 'none'; }} />
                        ) : (
                          <div style={{ width: '28px', height: '28px', borderRadius: '6px', background: 'var(--primary-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '0.8rem' }}>
                            {pi.display_name ? pi.display_name[0] : 'P'}
                          </div>
                        )}
                        <span style={{ color: 'var(--accent-gold)' }}>{pi.display_name}</span>
                        {pi.nickname && pi.nickname !== pi.display_name && (
                          <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>"{pi.nickname}"</span>
                        )}
                      </div>
                    </td>
                    <td style={{ fontWeight: 700, color: 'var(--accent-gold)' }}>Lv. {pi.level}</td>
                    <td>
                      <span className="badge" style={{
                        background: pi.gender === 'Male' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(236, 72, 153, 0.2)',
                        color: pi.gender === 'Male' ? '#60a5fa' : '#f472b6',
                        border: `1px solid ${pi.gender === 'Male' ? 'rgba(59, 130, 246, 0.4)' : 'rgba(236, 72, 153, 0.4)'}`,
                        fontSize: '0.75rem'
                      }}>
                        {pi.gender === 'Male' ? '♂ Male' : pi.gender === 'Female' ? '♀ Female' : pi.gender || 'Unknown'}
                      </span>
                    </td>
                    <td style={{ color: 'var(--accent-gold)', whiteSpace: 'nowrap' }}>
                      {pi.rank ? '⭐'.repeat(pi.rank) : '-'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem' }}>
                        {displayCats.map(cat => (
                          <span
                            key={cat.id}
                            className="badge"
                            style={{
                              background: 'rgba(99, 102, 241, 0.15)',
                              color: '#a5b4fc',
                              border: '1px solid rgba(99, 102, 241, 0.3)',
                              fontSize: '0.68rem',
                              padding: '0.05rem 0.3rem',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.15rem'
                            }}
                          >
                            <span>{cat.icon}</span>
                            <span>{cat.name}</span>
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      {pi.current_speed || pi.base_speed ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.1rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                            <span style={{ fontWeight: 700, color: (pi.speed_modifier_pct > 0) ? '#34d399' : 'var(--text-primary)' }}>
                              💨 {pi.current_speed || pi.base_speed}
                            </span>
                            {pi.speed_modifier_pct > 0 && (
                              <span className="badge" style={{ background: 'rgba(52, 211, 153, 0.2)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.4)', fontSize: '0.68rem', padding: '0.05rem 0.3rem' }}>
                                +{pi.speed_modifier_pct}%
                              </span>
                            )}
                          </div>
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                            Base: {pi.base_speed}
                          </span>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>-</span>
                      )}
                    </td>
                    <td>{pi.iv_hp} / {pi.iv_melee} / {pi.iv_defense}</td>
                    <td>
                      <span className="badge" style={{
                        background: pi.location === 'party' ? 'rgba(59, 130, 246, 0.2)' :
                                    pi.location === 'dps' ? 'rgba(168, 85, 247, 0.2)' :
                                    pi.location === 'base' ? 'rgba(245, 158, 11, 0.2)' :
                                    'rgba(255, 255, 255, 0.1)',
                        color: pi.location === 'party' ? '#60a5fa' :
                               pi.location === 'dps' ? '#c084fc' :
                               pi.location === 'base' ? '#fbbf24' :
                               '#e2e8f0',
                        border: pi.location === 'dps' ? '1px solid rgba(168, 85, 247, 0.4)' : '1px solid var(--border-color)',
                        fontSize: '0.75rem'
                      }}>
                        {pi.location === 'dps' ? '🔮 Dimensional Storage' :
                         pi.location === 'palbox' ? '📦 Palbox' :
                         pi.location === 'party' ? '⚔️ Party' :
                         pi.location === 'base' ? `🏰 Base${pi.location_details_base_camp_name ? ` (${pi.location_details_base_camp_name})` : ''}` :
                         (pi.location || 'STORAGE').toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <div className="badge-container" onClick={e => e.stopPropagation()}>
                        {(pi.passives || []).map((pass, pIdx) => {
                          const passObj = typeof pass === 'string' ? { id: pass, name: pass } : pass;
                          return (
                            <SkillBadgeWithTooltip key={passObj.id || pIdx} skill={passObj}>
                              <span className="badge badge-element" style={{ cursor: 'pointer' }}>
                                {passObj.name || passObj.id}
                              </span>
                            </SkillBadgeWithTooltip>
                          );
                        })}
                        {(!pi.passives || pi.passives.length === 0) && <span style={{ color: 'var(--text-secondary)' }}>None</span>}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="glass-card" style={{ textAlign: 'center', padding: '4rem' }}>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.25rem' }}>No save file loaded. Please click "Load & Parse" to view save game details.</p>
        </div>
      )}
    </div>
  );
}

export default SaveGameExplorerView;
