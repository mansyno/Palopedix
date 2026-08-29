import React, { useState, useEffect } from 'react';
import { useTableSort } from '../hooks/useTableSort';

export function BuildingsTechView() {
  const [activeSubTab, setActiveSubTab] = useState('buildings');
  const [buildings, setBuildings] = useState([]);
  const [techs, setTechs] = useState([]);
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (activeSubTab === 'buildings') {
      let url = '/api/buildings?';
      if (category) url += `category=${encodeURIComponent(category)}&`;
      if (search) url += `search=${encodeURIComponent(search)}&`;
      fetch(url)
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) setBuildings(data);
        })
        .catch(err => console.error('Error fetching buildings:', err));
    } else {
      let url = '/api/technology?';
      if (search) url += `search=${encodeURIComponent(search)}&`;
      fetch(url)
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) setTechs(data);
        })
        .catch(err => console.error('Error fetching technology:', err));
    }
  }, [activeSubTab, category, search]);

  const {
    sortedData: sortedBuildings,
    sortCol: bSortCol,
    sortDesc: bSortDesc,
    handleSort: handleBSort,
  } = useTableSort(buildings, 'name', false);

  const {
    sortedData: sortedTechs,
    sortCol: tSortCol,
    sortDesc: tSortDesc,
    handleSort: handleTSort,
  } = useTableSort(techs, 'level', false);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      <div style={{ flexShrink: 0, marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <button
            className={`pill-btn ${activeSubTab === 'buildings' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('buildings')}
          >
            🏗️ Base Facilities & Buildings ({buildings.length})
          </button>
          <button
            className={`pill-btn ${activeSubTab === 'technology' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('technology')}
          >
            🔬 Technology Tree Unlocks ({techs.length})
          </button>
        </div>

        <div className="filter-bar glass-card" style={{ marginBottom: '0.5rem' }}>
          {activeSubTab === 'buildings' && (
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Category</label>
              <select value={category} onChange={e => setCategory(e.target.value)}>
                <option value="">All Categories</option>
                <option value="Production">Production & Workbenches</option>
                <option value="Pal">Pal Management & Beds</option>
                <option value="Base">Infrastructure & Storage</option>
                <option value="Defense">Defense & Fortifications</option>
                <option value="Food">Farming & Cooking</option>
                <option value="Lighting">Lighting & Decor</option>
              </select>
            </div>
          )}
          <div style={{ flexGrow: 1 }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Search</label>
            <input
              type="text"
              placeholder={activeSubTab === 'buildings' ? "Search buildings by name or ID..." : "Search technology tree unlocks..."}
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </div>
      </div>

      {activeSubTab === 'buildings' ? (
        <div className="glass-card table-container" style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 0, marginBottom: '1.5rem' }}>
          <table>
            <thead>
              <tr>
                <th onClick={() => handleBSort('name')} style={{ cursor: 'pointer' }}>Facility{bSortCol === 'name' ? (bSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleBSort('category')} style={{ cursor: 'pointer' }}>Category{bSortCol === 'category' ? (bSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th>Energy / Fuel Requirement</th>
                <th>Build Materials</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {sortedBuildings.map(b => (
                <tr key={b.id}>
                  <td style={{ fontWeight: 600 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                      {b.icon_path ? (
                        <img src={b.icon_path} alt={b.name} style={{ width: '28px', height: '28px', objectFit: 'contain', borderRadius: '4px', background: 'rgba(0,0,0,0.2)' }} onError={(e) => { e.target.style.display = 'none'; }} />
                      ) : (
                        <span style={{ fontSize: '1.1rem' }}>🏗️</span>
                      )}
                      <span style={{ color: 'var(--text-primary)' }}>{b.name}</span>
                    </div>
                  </td>
                  <td>
                    <span className="badge" style={{ background: 'rgba(255,255,255,0.08)', fontSize: '0.72rem' }}>
                      {b.category || 'Facility'}
                    </span>
                  </td>
                  <td>
                    {b.energy_type ? (
                      <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.2)', color: 'var(--accent-gold)', fontSize: '0.72rem' }}>
                        ⚡ {b.energy_type} ({b.energy_amount || 1})
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-secondary)' }}>None</span>
                    )}
                  </td>
                  <td style={{ fontSize: '0.8rem' }}>
                    {b.materials ? b.materials : '-'}
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', maxWidth: '360px' }}>
                    {b.description || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="glass-card table-container" style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 0, marginBottom: '1.5rem' }}>
          <table>
            <thead>
              <tr>
                <th onClick={() => handleTSort('level')} style={{ cursor: 'pointer', width: '90px' }}>Level{tSortCol === 'level' ? (tSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleTSort('name')} style={{ cursor: 'pointer' }}>Technology Unlock{tSortCol === 'name' ? (tSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleTSort('tier')} style={{ cursor: 'pointer', width: '120px' }}>Tier{tSortCol === 'tier' ? (tSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleTSort('cost')} style={{ cursor: 'pointer', width: '90px' }}>Cost{tSortCol === 'cost' ? (tSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {sortedTechs.map(t => (
                <tr key={t.id}>
                  <td style={{ fontWeight: 700, color: 'var(--accent-gold)' }}>Lv. {t.level}</td>
                  <td style={{ fontWeight: 600 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                      {t.icon_path ? (
                        <img src={t.icon_path} alt={t.name} style={{ width: '28px', height: '28px', objectFit: 'contain', borderRadius: '4px', background: 'rgba(0,0,0,0.2)' }} onError={(e) => { e.target.style.display = 'none'; }} />
                      ) : (
                        <span style={{ fontSize: '1.1rem' }}>🔬</span>
                      )}
                      <span style={{ color: 'var(--text-primary)' }}>{t.name}</span>
                    </div>
                  </td>
                  <td>
                    <span className="badge" style={{ background: t.tier === 'Ancient' ? 'rgba(168, 85, 247, 0.2)' : 'rgba(255,255,255,0.08)', color: t.tier === 'Ancient' ? '#c084fc' : 'var(--text-primary)', fontSize: '0.72rem' }}>
                      {t.tier || 'Standard'}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{t.cost ? `${t.cost} pts` : 'Free'}</td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', maxWidth: '380px' }}>
                    {t.description || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default BuildingsTechView;
