import React, { useState, useEffect } from 'react';
import { useTableSort } from '../hooks/useTableSort';

export function BuildingsTechView({
  activeSubTab = 'facilities',
  onSubTabChange,
  saveLoaded = true,
  showSubTabButtons = false,
}) {
  const currentTab = (activeSubTab === 'buildings' || activeSubTab === 'facilities') ? 'facilities' : 'technology';
  
  const [buildings, setBuildings] = useState([]);
  const [techs, setTechs] = useState([]);
  
  // Facilities filters
  const [category, setCategory] = useState('');
  const [facilitySearch, setFacilitySearch] = useState('');
  const [facilityUnlockStatus, setFacilityUnlockStatus] = useState('');
  const [facilityBuiltStatus, setFacilityBuiltStatus] = useState('');
  const [facilityMethod, setFacilityMethod] = useState('');

  // Tech Tree filters
  const [techSearch, setTechSearch] = useState('');
  const [techTier, setTechTier] = useState('');
  const [techStatus, setTechStatus] = useState('');
  const [techBuiltStatus, setTechBuiltStatus] = useState('');

  useEffect(() => {
    if (currentTab === 'facilities') {
      let url = '/api/buildings?';
      if (category) url += `category=${encodeURIComponent(category)}&`;
      if (facilitySearch) url += `search=${encodeURIComponent(facilitySearch)}&`;
      if (facilityUnlockStatus === 'unlocked') url += 'is_unlocked=true&';
      if (facilityUnlockStatus === 'locked') url += 'is_unlocked=false&';
      if (facilityBuiltStatus === 'built') url += 'is_built=true&';
      if (facilityBuiltStatus === 'unbuilt') url += 'is_built=false&';
      if (facilityMethod) url += `unlock_method=${encodeURIComponent(facilityMethod)}&`;

      fetch(url)
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) setBuildings(data);
        })
        .catch(err => console.error('Error fetching buildings:', err));
    } else {
      let url = '/api/tech_tree?';
      if (techSearch) url += `search=${encodeURIComponent(techSearch)}&`;
      if (techTier === 'ancient') url += 'is_ancient=true&';
      if (techTier === 'standard') url += 'is_ancient=false&';
      if (techStatus === 'unlocked') url += 'is_unlocked=true&';
      if (techStatus === 'locked') url += 'is_unlocked=false&';
      if (techBuiltStatus === 'built') url += 'is_built=true&';
      if (techBuiltStatus === 'unbuilt') url += 'is_built=false&';

      fetch(url)
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) setTechs(data);
        })
        .catch(err => console.error('Error fetching technology:', err));
    }
  }, [currentTab, category, facilitySearch, facilityUnlockStatus, facilityBuiltStatus, facilityMethod, techSearch, techTier, techStatus, techBuiltStatus]);

  const {
    sortedData: sortedBuildings,
    sortCol: bSortCol,
    sortDesc: bSortDesc,
    handleSort: handleBSort,
  } = useTableSort(buildings, 'tech_level', false);

  const {
    sortedData: sortedTechs,
    sortCol: tSortCol,
    sortDesc: tSortDesc,
    handleSort: handleTSort,
  } = useTableSort(techs, 'level', false);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      <div style={{ flexShrink: 0, marginBottom: '0.75rem' }}>
        {showSubTabButtons && (
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <button
              className={`pill-btn ${currentTab === 'facilities' ? 'active' : ''}`}
              onClick={() => onSubTabChange ? onSubTabChange('facilities') : null}
            >
              🏗️ Base Facilities ({buildings.length})
            </button>
            <button
              className={`pill-btn ${currentTab === 'technology' ? 'active' : ''}`}
              onClick={() => onSubTabChange ? onSubTabChange('technology') : null}
            >
              🔬 Technology Tree ({techs.length})
            </button>
          </div>
        )}

        {/* Filter Bar */}
        <div className="filter-bar glass-card" style={{ marginBottom: '0.5rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          {currentTab === 'facilities' ? (
            <>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Category</label>
                <select value={category} onChange={e => setCategory(e.target.value)} style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}>
                  <option value="">All Categories</option>
                  <option value="Production">Production & Workbenches</option>
                  <option value="Pal">Pal Management & Beds</option>
                  <option value="Base">Infrastructure & Storage</option>
                  <option value="Defense">Defense & Fortifications</option>
                  <option value="Food">Farming & Cooking</option>
                  <option value="Lighting">Lighting & Decor</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Unlock Source</label>
                <select value={facilityMethod} onChange={e => setFacilityMethod(e.target.value)} style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}>
                  <option value="">All Sources</option>
                  <option value="Standard Tech">Standard Tech</option>
                  <option value="Ancient Tech">Ancient Tech</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Unlock Status</label>
                <select value={facilityUnlockStatus} onChange={e => setFacilityUnlockStatus(e.target.value)} style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}>
                  <option value="">All Statuses</option>
                  <option value="unlocked">✓ Unlocked</option>
                  <option value="locked">🔒 Locked</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>World Built Status</label>
                <select value={facilityBuiltStatus} onChange={e => setFacilityBuiltStatus(e.target.value)} style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}>
                  <option value="">All Build States</option>
                  <option value="built">🔨 Built in World</option>
                  <option value="unbuilt">Unbuilt (0)</option>
                </select>
              </div>

              <div style={{ flexGrow: 1, minWidth: '200px' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Search Facilities</label>
                <input
                  type="text"
                  placeholder="Search facilities by name or ID..."
                  value={facilitySearch}
                  onChange={e => setFacilitySearch(e.target.value)}
                  style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}
                />
              </div>
            </>
          ) : (
            <>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Technology Tier</label>
                <select value={techTier} onChange={e => setTechTier(e.target.value)} style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}>
                  <option value="">All Tiers</option>
                  <option value="standard">Standard Tech (Blue)</option>
                  <option value="ancient">Ancient Tech (Purple)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Unlock Status</label>
                <select value={techStatus} onChange={e => setTechStatus(e.target.value)} style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}>
                  <option value="">All Statuses</option>
                  <option value="unlocked">✓ Unlocked</option>
                  <option value="locked">🔒 Locked</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>World Built Status</label>
                <select value={techBuiltStatus} onChange={e => setTechBuiltStatus(e.target.value)} style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}>
                  <option value="">All Build States</option>
                  <option value="built">🔨 Built in World</option>
                  <option value="unbuilt">Not Built (0)</option>
                </select>
              </div>

              <div style={{ flexGrow: 1, minWidth: '220px' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Search Technology</label>
                <input
                  type="text"
                  placeholder="Search technology tree nodes..."
                  value={techSearch}
                  onChange={e => setTechSearch(e.target.value)}
                  style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Content Tables */}
      {currentTab === 'facilities' ? (
        <div className="glass-card table-container" style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 0, marginBottom: '1.5rem' }}>
          <table>
            <thead>
              <tr>
                <th onClick={() => handleBSort('name')} style={{ cursor: 'pointer' }}>Facility{bSortCol === 'name' ? (bSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleBSort('category')} style={{ cursor: 'pointer', width: '140px' }}>Category{bSortCol === 'category' ? (bSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleBSort('unlock_method')} style={{ cursor: 'pointer', width: '220px' }}>Unlock Source{bSortCol === 'unlock_method' ? (bSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleBSort('is_unlocked')} style={{ cursor: 'pointer', width: '120px' }}>Unlock Status{bSortCol === 'is_unlocked' ? (bSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleBSort('built_count')} style={{ cursor: 'pointer', width: '130px' }}>Built in World{bSortCol === 'built_count' ? (bSortDesc ? ' ▼' : ' ▲') : ''}</th>
              </tr>
            </thead>
            <tbody>
              {sortedBuildings.map(b => {
                const displayName = (b.name === 'en Text' || !b.name) ? `${b.id} (Unlocalized)` : b.name;
                return (
                  <tr key={b.id}>
                    <td style={{ fontWeight: 600 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                        {b.icon_path ? (
                          <img src={b.icon_path} alt={displayName} style={{ width: '28px', height: '28px', objectFit: 'contain', borderRadius: '4px', background: 'rgba(0,0,0,0.2)' }} onError={(e) => { e.target.style.display = 'none'; }} />
                        ) : (
                          <span style={{ fontSize: '1.1rem' }}>🏗️</span>
                        )}
                        <div>
                          <div style={{ color: 'var(--text-primary)' }}>{displayName}</div>
                          {b.id !== displayName && (
                            <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>ID: {b.id}</div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="badge" style={{ background: 'rgba(255,255,255,0.08)', fontSize: '0.72rem' }}>
                        {b.category || 'Facility'}
                      </span>
                    </td>
                    <td>
                      {b.unlock_method === 'Ancient Tech' ? (
                        <span className="badge" style={{ background: 'rgba(168, 85, 247, 0.18)', color: '#c084fc', fontSize: '0.72rem' }} title={`Tech ID: ${b.required_tech_id}`}>
                          🏛️ Ancient: {b.required_tech_name || b.required_tech_id}
                        </span>
                      ) : b.unlock_method === 'Standard Tech' ? (
                        <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', fontSize: '0.72rem' }} title={`Tech ID: ${b.required_tech_id}`}>
                          🔬 Tech: {b.required_tech_name || b.required_tech_id}
                        </span>
                      ) : (
                        <span className="badge" style={{ background: 'rgba(148, 163, 184, 0.12)', color: '#94a3b8', fontSize: '0.72rem' }}>
                          Internal / Unlinked
                        </span>
                      )}
                    </td>
                    <td>
                      <span className="badge" style={{
                        background: b.is_unlocked ? 'rgba(34, 197, 94, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                        color: b.is_unlocked ? '#4ade80' : 'var(--text-secondary)',
                        fontSize: '0.72rem',
                      }}>
                        {b.is_unlocked ? '✓ Unlocked' : '🔒 Locked'}
                      </span>
                    </td>
                    <td>
                      {b.is_built ? (
                        <span className="badge" style={{ background: 'rgba(245, 158, 11, 0.22)', color: '#fbbf24', fontSize: '0.72rem', fontWeight: 700 }}>
                          🔨 Built ({b.built_count})
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.78rem' }}>Unbuilt (0)</span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {sortedBuildings.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                    No base facilities matching the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="glass-card table-container" style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 0, marginBottom: '1.5rem' }}>
          <table>
            <thead>
              <tr>
                <th onClick={() => handleTSort('level')} style={{ cursor: 'pointer', width: '80px' }}>Level{tSortCol === 'level' ? (tSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleTSort('name')} style={{ cursor: 'pointer' }}>Technology Unlock{tSortCol === 'name' ? (tSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleTSort('tier')} style={{ cursor: 'pointer', width: '100px' }}>Tier{tSortCol === 'tier' ? (tSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleTSort('cost')} style={{ cursor: 'pointer', width: '80px' }}>Cost{tSortCol === 'cost' ? (tSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleTSort('is_unlocked')} style={{ cursor: 'pointer', width: '110px' }}>Status{tSortCol === 'is_unlocked' ? (tSortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleTSort('built_count')} style={{ cursor: 'pointer', width: '130px' }}>Built in World{tSortCol === 'built_count' ? (tSortDesc ? ' ▼' : ' ▲') : ''}</th>
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
                        <span style={{ fontSize: '1.1rem' }}>{t.is_ancient ? '🏛️' : '🔬'}</span>
                      )}
                      <div>
                        <div style={{ color: 'var(--text-primary)' }}>{t.name}</div>
                        {t.require_technology && (
                          <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>
                            Requires: {t.require_technology}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className="badge" style={{ background: t.is_ancient ? 'rgba(168, 85, 247, 0.2)' : 'rgba(59, 130, 246, 0.15)', color: t.is_ancient ? '#c084fc' : '#60a5fa', fontSize: '0.72rem' }}>
                      {t.tier || (t.is_ancient ? 'Ancient' : 'Standard')}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{t.cost || t.tech_point_cost ? `${t.cost || t.tech_point_cost} pts` : 'Free'}</td>
                  <td>
                    <span className="badge" style={{
                      background: t.is_unlocked ? 'rgba(34, 197, 94, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                      color: t.is_unlocked ? '#4ade80' : 'var(--text-secondary)',
                      fontSize: '0.72rem',
                    }}>
                      {t.is_unlocked ? '✓ Unlocked' : '🔒 Locked'}
                    </span>
                  </td>
                  <td>
                    {t.has_buildings ? (
                      t.is_built ? (
                        <span className="badge" style={{ background: 'rgba(245, 158, 11, 0.22)', color: '#fbbf24', fontSize: '0.72rem', fontWeight: 700 }}>
                          🔨 Built ({t.built_count})
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.78rem' }}>Not Built (0)</span>
                      )
                    ) : (
                      <span style={{ color: 'var(--text-secondary)', fontSize: '0.78rem' }}>📦 Recipe Only</span>
                    )}
                  </td>
                </tr>
              ))}
              {sortedTechs.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                    No technology tree nodes matching the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default BuildingsTechView;
