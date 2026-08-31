import React, { useState, useMemo } from 'react';
import { useTableSort } from '../hooks/useTableSort';
import { PassiveBadge } from './common/PassiveBadge';

const SHORT_CATEGORY_NAMES = {
  flying_mount: 'Fly',
  ground_mount: 'Mount',
  swimming_mount: 'Swim',
  glider: 'Glider',
  ranch_producer: 'Ranch',
  player_element_infusion: 'Infuse',
  player_combat_buffer: 'Buff',
  party_pal_buffer: 'Party',
  heavy_artillery: 'Cannon',
  coop_attacker: 'Co-Op',
  healer_lifesteal: 'Heal',
  carrying_capacity: 'Weight',
  drop_loot_booster: 'Loot',
  resource_gathering: 'Gather',
  breeding_egg_booster: 'Breed',
  fishing_helper: 'Fish',
  exploration_survival: 'Radar',
  no_active_skill: '',
};

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
  const [rarityFilter, setRarityFilter] = useState('');
  const [passiveFilter, setPassiveFilter] = useState('');

  const speciesOptions = useMemo(() => {
    const counts = new Map();
    instances.forEach(inst => {
      const name = inst.display_name || inst.species;
      if (name) {
        counts.set(name, (counts.get(name) || 0) + 1);
      }
    });
    return Array.from(counts.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([name, count]) => ({ name, count }));
  }, [instances]);

  const filteredInstances = useMemo(() => {
    return instances.filter(pi => {
      if (locFilter && pi.location !== locFilter) return false;
      if (genderFilter && pi.gender !== genderFilter) return false;
      if (minLvlFilter && (pi.level || 0) < parseInt(minLvlFilter, 10)) return false;
      if (specFilter && (pi.display_name || pi.species || '').toLowerCase() !== specFilter.toLowerCase()) return false;
      if (passiveFilter && !(pi.passives || []).some(p => ((typeof p === 'string' ? p : p.name || p.id) || '').toLowerCase().includes(passiveFilter.toLowerCase()))) return false;
      if (instCategoryFilter) {
        const cats = (pi.partner_skill_categories && pi.partner_skill_categories.length > 0)
          ? pi.partner_skill_categories
          : (pals.find(p => p.display_name?.toLowerCase() === (pi.display_name || '').toLowerCase())?.partner_skill_categories || []);
        if (!cats.some(c => c.id === instCategoryFilter || c.name?.toLowerCase() === instCategoryFilter.toLowerCase())) {
          return false;
        }
      }
      if (rarityFilter) {
        const palRarity = pi.rarity ?? (pals.find(p => p.display_name?.toLowerCase() === (pi.display_name || '').toLowerCase())?.rarity);
        if (rarityFilter === 'legendary' && palRarity !== 20) return false;
        if (rarityFilter === 'boss' && palRarity !== 10) return false;
        if (rarityFilter === 'rare' && (palRarity < 7 || palRarity > 9)) return false;
        if (rarityFilter === 'mid' && (palRarity < 4 || palRarity > 6)) return false;
        if (rarityFilter === 'common' && (palRarity < 1 || palRarity > 3)) return false;
        if (!isNaN(parseInt(rarityFilter, 10)) && palRarity !== parseInt(rarityFilter, 10)) return false;
      }
      return true;
    });
  }, [instances, locFilter, genderFilter, minLvlFilter, specFilter, passiveFilter, instCategoryFilter, rarityFilter, pals]);

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
          <div className="filter-bar glass-card" style={{ marginBottom: '0.5rem', display: 'flex', flexWrap: 'nowrap', gap: '0.5rem', alignItems: 'flex-end', overflowX: 'auto', padding: '0.6rem 0.85rem' }}>
            <div style={{ flex: '1 1 auto', minWidth: '135px' }}>
              <label style={{ display: 'block', marginBottom: '0.2rem', color: 'var(--accent-gold)', fontSize: '0.7rem', fontWeight: 700 }}>🤝 Partner Group</label>
              <select value={instCategoryFilter} onChange={e => setInstCategoryFilter(e.target.value)} style={{ borderColor: 'var(--accent-gold)', width: '100%', fontSize: '0.78rem', padding: '0.25rem 0.4rem' }}>
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
            <div style={{ flex: '0 0 auto', minWidth: '105px' }}>
              <label style={{ display: 'block', marginBottom: '0.2rem', color: 'var(--text-secondary)', fontSize: '0.7rem' }}>Location</label>
              <select value={locFilter} onChange={e => setLocFilter(e.target.value)} style={{ width: '100%', fontSize: '0.78rem', padding: '0.25rem 0.4rem' }}>
                <option value="">All Locations</option>
                <option value="party">Player Party</option>
                <option value="palbox">Palbox Storage</option>
                <option value="base">Base Workers</option>
                <option value="dps">Dimensional Storage</option>
              </select>
            </div>

            {/* Species Dropdown List */}
            <div style={{ flex: '1 1 auto', minWidth: '135px' }}>
              <label style={{ display: 'block', marginBottom: '0.2rem', color: 'var(--text-secondary)', fontSize: '0.7rem' }}>Species</label>
              <select
                value={specFilter}
                onChange={e => setSpecFilter(e.target.value)}
                style={{ width: '100%', fontSize: '0.78rem', padding: '0.25rem 0.4rem' }}
              >
                <option value="">All Species ({instances.length})</option>
                {speciesOptions.map(s => (
                  <option key={s.name} value={s.name}>
                    {s.name} ({s.count})
                  </option>
                ))}
              </select>
            </div>

            <div style={{ flex: '0 0 auto', minWidth: '95px' }}>
              <label style={{ display: 'block', marginBottom: '0.2rem', color: 'var(--text-secondary)', fontSize: '0.7rem' }}>Gender</label>
              <select value={genderFilter} onChange={e => setGenderFilter(e.target.value)} style={{ width: '100%', fontSize: '0.78rem', padding: '0.25rem 0.4rem' }}>
                <option value="">All Genders</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
              </select>
            </div>
            <div style={{ flex: '0 0 auto', width: '70px' }}>
              <label style={{ display: 'block', marginBottom: '0.2rem', color: 'var(--text-secondary)', fontSize: '0.7rem' }}>Min Level</label>
              <input type="text" placeholder="Min Lv" value={minLvlFilter} onChange={e => setMinLvlFilter(e.target.value)} style={{ width: '100%', fontSize: '0.78rem', padding: '0.25rem 0.35rem' }} />
            </div>
            <div style={{ flex: '0 0 auto', minWidth: '115px' }}>
              <label style={{ display: 'block', marginBottom: '0.2rem', color: 'var(--text-secondary)', fontSize: '0.7rem' }}>Rarity Tier</label>
              <select value={rarityFilter} onChange={e => setRarityFilter(e.target.value)} style={{ width: '100%', fontSize: '0.78rem', padding: '0.25rem 0.4rem' }}>
                <option value="">All Rarities</option>
                <option value="legendary">👑 Legendary (Tier 20)</option>
                <option value="boss">🔥 Alpha / Boss (Tier 10)</option>
                <option value="rare">⭐ Rare (Tier 7–9)</option>
                <option value="mid">🔷 Mid-Tier (Tier 4–6)</option>
                <option value="common">⚪ Common (Tier 1–3)</option>
                <option value="20">Tier 20</option>
                <option value="10">Tier 10</option>
                <option value="9">Tier 9</option>
                <option value="8">Tier 8</option>
                <option value="7">Tier 7</option>
                <option value="6">Tier 6</option>
                <option value="5">Tier 5</option>
                <option value="4">Tier 4</option>
                <option value="3">Tier 3</option>
                <option value="2">Tier 2</option>
                <option value="1">Tier 1</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Scrollable Table Area */}
      {saveLoaded ? (
        <div className="glass-card table-container" style={{ flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden', padding: 0, marginBottom: '1.5rem' }}>
          <table style={{ width: '100%', tableLayout: 'auto' }}>
            <thead>
              <tr>
                <th onClick={() => handleSort('display_name')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.3rem 0.4rem', width: '130px' }}>Species{sortCol === 'display_name' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleSort('level')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.3rem 0.25rem', width: '45px' }}>Level{sortCol === 'level' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleSort('gender')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.3rem 0.25rem', width: '35px' }}>Sex{sortCol === 'gender' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleSort('rank')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.3rem 0.25rem', width: '35px' }}>Rank{sortCol === 'rank' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th style={{ whiteSpace: 'nowrap', padding: '0.3rem 0.35rem', width: '110px' }}>Partner Groups</th>
                <th onClick={() => handleSort('current_speed')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.3rem 0.25rem', width: '55px' }}>Speed{sortCol === 'current_speed' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th style={{ whiteSpace: 'nowrap', padding: '0.3rem 0.25rem', width: '65px' }}>IVs (H/A/D)</th>
                <th onClick={() => handleSort('location')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.3rem 0.35rem', width: '70px' }}>Location{sortCol === 'location' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th style={{ padding: '0.3rem 0.4rem' }}>Passives</th>
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

                const validCats = displayCats.filter(c => c.id !== 'no_active_skill');

                return (
                  <tr key={pi.instance_id} onClick={handleRowClick} style={{ cursor: 'pointer' }}>
                    <td style={{ fontWeight: 600, whiteSpace: 'nowrap', padding: '0.25rem 0.4rem' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                        {pi.icon_path ? (
                          <img src={pi.icon_path} alt={pi.display_name} style={{ width: '22px', height: '22px', borderRadius: '4px', objectFit: 'cover', background: 'rgba(0,0,0,0.3)', flexShrink: 0 }} onError={(e) => { e.target.style.display = 'none'; }} />
                        ) : (
                          <div style={{ width: '22px', height: '22px', borderRadius: '4px', background: 'var(--primary-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '0.7rem', flexShrink: 0 }}>
                            {pi.display_name ? pi.display_name[0] : 'P'}
                          </div>
                        )}
                        <span title={pi.nickname && pi.nickname !== pi.display_name ? `${pi.display_name} ("${pi.nickname}")` : pi.display_name} style={{ color: 'var(--accent-gold)', fontSize: '0.82rem', whiteSpace: 'nowrap' }}>
                          {pi.display_name}
                        </span>
                      </div>
                    </td>
                    <td style={{ fontWeight: 700, color: 'var(--accent-gold)', whiteSpace: 'nowrap', padding: '0.25rem 0.25rem', fontSize: '0.78rem' }}>Lv.{pi.level}</td>
                    <td style={{ whiteSpace: 'nowrap', padding: '0.25rem 0.25rem' }}>
                      <span className="badge" style={{
                        background: pi.gender === 'Male' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(236, 72, 153, 0.2)',
                        color: pi.gender === 'Male' ? '#60a5fa' : '#f472b6',
                        border: `1px solid ${pi.gender === 'Male' ? 'rgba(59, 130, 246, 0.4)' : 'rgba(236, 72, 153, 0.4)'}`,
                        fontSize: '0.68rem',
                        padding: '0.05rem 0.25rem',
                      }}>
                        {pi.gender === 'Male' ? '♂ M' : pi.gender === 'Female' ? '♀ F' : pi.gender || '?'}
                      </span>
                    </td>
                    <td style={{ color: 'var(--accent-gold)', whiteSpace: 'nowrap', padding: '0.25rem 0.25rem', fontSize: '0.72rem' }}>
                      {pi.rank ? '⭐'.repeat(pi.rank) : '-'}
                    </td>
                    <td style={{ padding: '0.25rem 0.35rem' }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.15rem', maxWidth: '110px' }}>
                        {validCats.map(cat => {
                          const shortName = SHORT_CATEGORY_NAMES[cat.id] || cat.name?.replace(/ Boosters| & Environmental Protection| & Weapons| & Life-Steal| Capacity| & Helpers| & Egg/g, '') || cat.name;
                          return (
                            <span
                              key={cat.id}
                              className="badge"
                              title={cat.description ? `${cat.name}: ${cat.description}` : cat.name}
                              style={{
                                background: 'rgba(99, 102, 241, 0.15)',
                                color: '#a5b4fc',
                                border: '1px solid rgba(99, 102, 241, 0.3)',
                                fontSize: '0.62rem',
                                padding: '0.02rem 0.22rem',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.1rem',
                                whiteSpace: 'nowrap',
                                cursor: 'help'
                              }}
                            >
                              <span>{cat.icon}</span>
                              <span>{shortName}</span>
                            </span>
                          );
                        })}
                        {validCats.length === 0 && (
                          <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>-</span>
                        )}
                      </div>
                    </td>
                    <td style={{ whiteSpace: 'nowrap', padding: '0.25rem 0.25rem' }}>
                      {pi.current_speed || pi.base_speed ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                          <span style={{ fontWeight: 700, fontSize: '0.78rem', color: (pi.speed_modifier_pct > 0) ? '#34d399' : 'var(--text-primary)' }}>
                            💨 {pi.current_speed || pi.base_speed}
                          </span>
                          {pi.speed_modifier_pct > 0 && (
                            <span className="badge" style={{ background: 'rgba(52, 211, 153, 0.2)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.4)', fontSize: '0.6rem', padding: '0.01rem 0.2rem' }}>
                              +{pi.speed_modifier_pct}%
                            </span>
                          )}
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>-</span>
                      )}
                    </td>
                    <td style={{ whiteSpace: 'nowrap', padding: '0.25rem 0.25rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      <span style={{ color: '#f8fafc', fontWeight: 600 }}>{pi.iv_hp ?? '-'}</span>/<span style={{ color: '#f8fafc', fontWeight: 600 }}>{pi.iv_melee ?? '-'}</span>/<span style={{ color: '#f8fafc', fontWeight: 600 }}>{pi.iv_defense ?? '-'}</span>
                    </td>
                    <td style={{ whiteSpace: 'nowrap', padding: '0.25rem 0.35rem' }}>
                      <span className="badge" title={pi.location_details_base_camp_name ? `Base: ${pi.location_details_base_camp_name}` : ''} style={{
                        background: pi.location === 'party' ? 'rgba(59, 130, 246, 0.2)' :
                                    pi.location === 'dps' ? 'rgba(168, 85, 247, 0.2)' :
                                    pi.location === 'base' ? 'rgba(245, 158, 11, 0.2)' :
                                    'rgba(255, 255, 255, 0.1)',
                        color: pi.location === 'party' ? '#60a5fa' :
                               pi.location === 'dps' ? '#c084fc' :
                               pi.location === 'base' ? '#fbbf24' :
                               '#e2e8f0',
                        border: pi.location === 'dps' ? '1px solid rgba(168, 85, 247, 0.4)' : '1px solid var(--border-color)',
                        fontSize: '0.68rem',
                        padding: '0.08rem 0.35rem',
                      }}>
                        {pi.location === 'dps' ? '🔮 Storage' :
                         pi.location === 'palbox' ? '📦 Palbox' :
                         pi.location === 'party' ? '⚔️ Party' :
                         pi.location === 'base' ? '🏰 Base' :
                         (pi.location || 'STORAGE').toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '0.25rem 0.35rem' }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem', alignItems: 'center' }} onClick={e => e.stopPropagation()}>
                        {(pi.passives || []).map((pass, pIdx) => (
                          <PassiveBadge key={pIdx} skill={pass} size="sm" />
                        ))}
                        {(!pi.passives || pi.passives.length === 0) && <span style={{ color: 'var(--text-secondary)', fontSize: '0.72rem' }}>None</span>}
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

