import React, { useState, useEffect, useMemo } from 'react';
import { useTableSort } from '../hooks/useTableSort';

export function PaldexMasterView({
  pals = [],
  setSelectedPal,
  elementFilter,
  setElementFilter,
  sizeFilter,
  setSizeFilter,
  nocturnalFilter,
  setNocturnalFilter,
  suitabilityFilter,
  setSuitabilityFilter,
  partnerCategoryFilter,
  setPartnerCategoryFilter,
}) {
  const [categories, setCategories] = useState([]);
  const [speciesFilter, setSpeciesFilter] = useState('');
  const [localPals, setLocalPals] = useState([]);

  useEffect(() => {
    fetch('/api/pals/partner-skill-categories')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setCategories(data);
      })
      .catch(err => console.error('Error fetching partner skill categories:', err));
  }, []);

  useEffect(() => {
    if (!pals || pals.length === 0) {
      let url = '/api/pals?';
      if (elementFilter) url += `element=${elementFilter}&`;
      if (sizeFilter) url += `size=${sizeFilter}&`;
      if (nocturnalFilter) url += `nocturnal=${nocturnalFilter === 'true'}&`;
      if (suitabilityFilter) url += `suitability=${suitabilityFilter}&`;
      if (partnerCategoryFilter) url += `partner_category=${encodeURIComponent(partnerCategoryFilter)}&`;

      fetch(url)
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) setLocalPals(data);
        })
        .catch(err => console.error('Error fetching fallback pals:', err));
    }
  }, [pals, elementFilter, sizeFilter, nocturnalFilter, suitabilityFilter, partnerCategoryFilter]);

  const activePals = (pals && pals.length > 0) ? pals : localPals;

  const filteredPals = useMemo(() => {
    const palList = Array.isArray(activePals) ? activePals : [];
    if (!speciesFilter) return palList;
    return palList.filter(p => (p.display_name || '').toLowerCase() === speciesFilter.toLowerCase());
  }, [activePals, speciesFilter]);

  const {
    sortedData: sortedPals,
    sortCol,
    sortDesc,
    handleSort,
  } = useTableSort(filteredPals, 'paldex_number', false);

  const safePals = Array.isArray(activePals) ? activePals : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      <div style={{ flexShrink: 0, marginBottom: '0.75rem' }}>
        <div className="filter-bar glass-card" style={{ marginBottom: '0.5rem', flexWrap: 'wrap' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Species</label>
            <select
              value={speciesFilter}
              onChange={e => setSpeciesFilter(e.target.value)}
              style={{ minWidth: '180px' }}
            >
              <option value="">All Species ({safePals.length})</option>
              {safePals.slice().sort((a, b) => (a.paldex_number || 0) - (b.paldex_number || 0) || (a.display_name || '').localeCompare(b.display_name || '')).map(p => (
                <option key={p.internal_name || p.id} value={p.display_name}>
                  #{String(p.paldex_number || 0).padStart(3, '0')} {p.display_name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--accent-gold)', fontWeight: 700 }}>
              🤝 Partner Skill Group
            </label>
            <select
              value={partnerCategoryFilter}
              onChange={e => setPartnerCategoryFilter(e.target.value)}
              style={{ borderColor: 'var(--accent-gold)' }}
            >
              <option value="">All Partner Groups</option>
              {categories.map(c => (
                <option key={c.category_id} value={c.category_id}>
                  {c.icon} {c.name} ({c.pal_count})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Element</label>
            <select value={elementFilter} onChange={e => setElementFilter(e.target.value)}>
              <option value="">All Elements</option>
              <option value="Neutral">Neutral / Normal</option>
              <option value="Fire">Fire</option>
              <option value="Water">Water</option>
              <option value="Grass">Grass / Leaf</option>
              <option value="Electric">Electric / Electricity</option>
              <option value="Ice">Ice</option>
              <option value="Ground">Ground / Earth</option>
              <option value="Dark">Dark</option>
              <option value="Dragon">Dragon</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Size</label>
            <select value={sizeFilter} onChange={e => setSizeFilter(e.target.value)}>
              <option value="">All Sizes</option>
              <option value="XS">Extra Small (XS)</option>
              <option value="S">Small (S)</option>
              <option value="M">Medium (M)</option>
              <option value="L">Large (L)</option>
              <option value="XL">Extra Large (XL)</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Nocturnal</label>
            <select value={nocturnalFilter} onChange={e => setNocturnalFilter(e.target.value)}>
              <option value="">All Habits</option>
              <option value="true">Nocturnal Only</option>
              <option value="false">Diurnal Only</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Work Suitability</label>
            <select value={suitabilityFilter} onChange={e => setSuitabilityFilter(e.target.value)}>
              <option value="">All Suitabilities</option>
              <option value="Kindling">Kindling / EmitFlame</option>
              <option value="Watering">Watering</option>
              <option value="Planting">Planting / Seeding</option>
              <option value="GenerateElectricity">Generating Electricity</option>
              <option value="Handcraft">Handiwork / Handcraft</option>
              <option value="Gathering">Gathering / Collection</option>
              <option value="Lumbering">Lumbering / Deforest</option>
              <option value="Mining">Mining</option>
              <option value="Medicine">Medicine Production</option>
              <option value="Cool">Cooling</option>
              <option value="Transport">Transporting</option>
              <option value="MonsterFarm">Farming / Ranch</option>
              <option value="OilExtraction">Oil Extraction</option>
            </select>
          </div>
        </div>

        {/* Quick Category Filter Pills */}
        {categories.length > 0 && (
          <div style={{ display: 'flex', gap: '0.4rem', overflowX: 'auto', paddingBottom: '0.35rem', scrollbarWidth: 'thin' }}>
            <button
              className={`btn ${!partnerCategoryFilter ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setPartnerCategoryFilter('')}
              style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem', borderRadius: '6px', whiteSpace: 'nowrap' }}
            >
              All Groups ({safePals.length})
            </button>
            {categories.map(c => (
              <button
                key={c.category_id}
                className={`btn ${partnerCategoryFilter === c.category_id ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setPartnerCategoryFilter(partnerCategoryFilter === c.category_id ? '' : c.category_id)}
                style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem', borderRadius: '6px', whiteSpace: 'nowrap' }}
              >
                {c.icon} {c.name} ({c.pal_count})
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="glass-card table-container" style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 0, marginBottom: '1.5rem' }}>
        <table>
          <thead>
            <tr>
              <th onClick={() => handleSort('paldex_number')} style={{ cursor: 'pointer', width: '60px' }}>
                #{sortCol === 'paldex_number' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
              <th onClick={() => handleSort('display_name')} style={{ cursor: 'pointer' }}>
                Pal{sortCol === 'display_name' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
              <th onClick={() => handleSort('element_1')} style={{ cursor: 'pointer', width: '130px' }}>
                Elements{sortCol === 'element_1' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
              <th>Partner Groups & Skill</th>
              <th onClick={() => handleSort('hp')} style={{ cursor: 'pointer', textAlign: 'center' }}>
                HP{sortCol === 'hp' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
              <th onClick={() => handleSort('attack_melee')} style={{ cursor: 'pointer', textAlign: 'center' }}>
                ATK{sortCol === 'attack_melee' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
              <th onClick={() => handleSort('defense')} style={{ cursor: 'pointer', textAlign: 'center' }}>
                DEF{sortCol === 'defense' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
              <th onClick={() => handleSort('base_speed')} style={{ cursor: 'pointer', textAlign: 'center' }}>
                SPD{sortCol === 'base_speed' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
              <th>Work Suitabilities</th>
              <th onClick={() => handleSort('food_requirement')} style={{ cursor: 'pointer', textAlign: 'center', width: '70px' }}>
                Food{sortCol === 'food_requirement' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
              <th onClick={() => handleSort('breeding_power')} style={{ cursor: 'pointer', textAlign: 'center', width: '80px' }}>
                Power{sortCol === 'breeding_power' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedPals.map(p => (
              <tr key={p.internal_name || p.id} onClick={() => setSelectedPal(p)} style={{ cursor: 'pointer' }}>
                <td style={{ color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.8rem' }}>
                  #{String(p.paldex_number || 0).padStart(3, '0')}
                </td>
                <td style={{ fontWeight: 600 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    {p.icon_path ? (
                      <img src={p.icon_path} alt={p.display_name} style={{ width: '28px', height: '28px', borderRadius: '6px', objectFit: 'cover', background: 'rgba(0,0,0,0.3)' }} onError={(e) => { e.target.style.display = 'none'; }} />
                    ) : (
                      <div style={{ width: '28px', height: '28px', borderRadius: '6px', background: 'var(--primary-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '0.8rem' }}>
                        {p.display_name ? p.display_name[0] : 'P'}
                      </div>
                    )}
                    <span style={{ color: 'var(--accent-gold)' }}>{p.display_name}</span>
                  </div>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                    {p.element_1 && (
                      <span className="badge badge-element" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.2rem', padding: '0.1rem 0.35rem', fontSize: '0.7rem' }}>
                        <img src={`/assets/elements/${p.element_1}.png`} alt={p.element_1} style={{ width: '12px', height: '12px' }} onError={(e) => { e.target.style.display = 'none'; }} />
                        {p.element_1}
                      </span>
                    )}
                    {p.element_2 && (
                      <span className="badge badge-element" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.2rem', padding: '0.1rem 0.35rem', fontSize: '0.7rem' }}>
                        <img src={`/assets/elements/${p.element_2}.png`} alt={p.element_2} style={{ width: '12px', height: '12px' }} onError={(e) => { e.target.style.display = 'none'; }} />
                        {p.element_2}
                      </span>
                    )}
                  </div>
                </td>
                <td>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                    {p.partner_skill && (
                      <div style={{ fontSize: '0.75rem', color: 'var(--accent-gold)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                        <span>🤝 {p.partner_skill.name}</span>
                      </div>
                    )}
                    {p.partner_skill_categories && p.partner_skill_categories.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem' }}>
                        {p.partner_skill_categories.map(cat => (
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
                    )}
                  </div>
                </td>
                <td style={{ textAlign: 'center', fontWeight: 600 }}>{p.hp || 70}</td>
                <td style={{ textAlign: 'center', fontWeight: 600, color: '#f87171' }}>{p.attack_melee || 70}</td>
                <td style={{ textAlign: 'center', fontWeight: 600, color: '#60a5fa' }}>{p.defense || 70}</td>
                <td style={{ textAlign: 'center', fontWeight: 700, color: '#38bdf8' }}>💨 {p.base_speed || p.run_speed || '-'}</td>
                <td>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                    {p.work_suitability_details && p.work_suitability_details.length > 0 ? (
                      p.work_suitability_details.map(wsd => (
                        <span key={wsd.id} className="suitability-pill" style={{ fontSize: '0.7rem', padding: '0.08rem 0.35rem', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                          {wsd.icon_path && (
                            <img src={wsd.icon_path} alt={wsd.name} className="work-hud-icon" onError={(e) => { e.target.style.display = 'none'; }} />
                          )}
                          <span>{wsd.name}</span>
                          <strong style={{ color: 'var(--accent-gold)' }}>L{wsd.level}</strong>
                        </span>
                      ))
                    ) : (
                      <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>-</span>
                    )}
                  </div>
                </td>
                <td style={{ textAlign: 'center', fontSize: '0.8rem' }}>🍖 {p.food_requirement || 1}</td>
                <td style={{ textAlign: 'center', fontWeight: 600, color: 'var(--accent-gold)' }}>{p.breeding_power}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default PaldexMasterView;
