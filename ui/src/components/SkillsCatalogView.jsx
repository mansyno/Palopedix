import React, { useState, useEffect } from 'react';
import { useTableSort } from '../hooks/useTableSort';
import { PassiveBadge } from './common/PassiveBadge';

export function SkillsCatalogView() {
  const [skills, setSkills] = useState([]);
  const [type, setType] = useState('');
  const [element, setElement] = useState('');
  const [source, setSource] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    let url = '/api/skills?';
    if (type) url += `type=${encodeURIComponent(type)}&`;
    if (element) url += `element=${encodeURIComponent(element)}&`;
    if (source) url += `source=${encodeURIComponent(source)}&`;
    if (search) url += `search=${encodeURIComponent(search)}&`;
    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setSkills(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching skills:', err);
        setLoading(false);
      });
  }, [type, element, source, search]);

  const {
    sortedData: sortedSkills,
    sortCol,
    sortDesc,
    handleSort,
  } = useTableSort(skills, 'name', false);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      {/* FIXED TOP HEADER CONTAINER */}
      <div style={{ flexShrink: 0, marginBottom: '0.75rem' }}>
        <div className="filter-bar glass-card" style={{ marginBottom: '0.75rem', flexWrap: 'wrap' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Skill Type</label>
            <select value={type} onChange={e => setType(e.target.value)}>
              <option value="">All Skill Types (Active, Passive, Partner)</option>
              <option value="Active">⚔️ Active Skills</option>
              <option value="Passive">🛡️ Passive Skills</option>
              <option value="Partner">🤝 Partner Skills</option>
            </select>
          </div>

          {(!type || type === 'Passive') && (
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--accent-gold)', fontWeight: 700 }}>Passive Source</label>
              <select value={source} onChange={e => setSource(e.target.value)} style={{ borderColor: 'var(--accent-gold)' }}>
                <option value="">All Passive Sources</option>
                <option value="Pals">🐾 Pals</option>
                <option value="Equipment">🛡️ Equipment</option>
                <option value="World Tree">🌳 World Tree</option>
                <option value="Mutation">🧬 Mutation</option>
                <option value="Legendary">👑 Legendary</option>
              </select>
            </div>
          )}

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Element</label>
            <select value={element} onChange={e => setElement(e.target.value)}>
              <option value="">All Elements</option>
              <option value="Neutral">Neutral / Normal</option>
              <option value="Fire">Fire</option>
              <option value="Water">Water</option>
              <option value="Grass">Grass / Leaf</option>
              <option value="Electric">Electric</option>
              <option value="Ice">Ice</option>
              <option value="Ground">Ground</option>
              <option value="Dark">Dark</option>
              <option value="Dragon">Dragon</option>
            </select>
          </div>
          <div style={{ flexGrow: 1 }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Search</label>
            <input type="text" placeholder="Search skills by name, Pal name, description, or unlock item..." value={search} onChange={e => setSearch(e.target.value)} />
          </div>
        </div>

        {(!type || type === 'Passive') && (
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
            <button className={`btn ${!source ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSource('')} style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem', borderRadius: '6px' }}>
              All Sources
            </button>
            <button className={`btn ${source === 'Pals' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSource('Pals')} style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem', borderRadius: '6px' }}>
              🐾 Pals
            </button>
            <button className={`btn ${source === 'Equipment' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSource('Equipment')} style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem', borderRadius: '6px' }}>
              🛡️ Equipment
            </button>
            <button className={`btn ${source === 'World Tree' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSource('World Tree')} style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem', borderRadius: '6px' }}>
              🌳 World Tree
            </button>
            <button className={`btn ${source === 'Mutation' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSource('Mutation')} style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem', borderRadius: '6px' }}>
              🧬 Mutation
            </button>
            <button className={`btn ${source === 'Legendary' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setSource('Legendary')} style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem', borderRadius: '6px' }}>
              👑 Legendary
            </button>
          </div>
        )}

        <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 600 }}>
          Showing <strong style={{ color: '#38bdf8' }}>{skills.length}</strong> matching skills
        </div>
      </div>

      {/* SCROLLABLE TABLE */}
      <div className="glass-card table-container" style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 0, marginBottom: '1.5rem' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}>
            <p style={{ color: 'var(--text-secondary)' }}>Loading skills database...</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th onClick={() => handleSort('name')} style={{ cursor: 'pointer' }}>
                  Skill{sortCol === 'name' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                </th>
                <th onClick={() => handleSort('type')} style={{ cursor: 'pointer', width: '100px' }}>
                  Type{sortCol === 'type' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                </th>
                <th onClick={() => handleSort('element')} style={{ cursor: 'pointer', width: '100px' }}>
                  Element{sortCol === 'element' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                </th>
                <th onClick={() => handleSort('power')} style={{ cursor: 'pointer', textAlign: 'center', width: '80px' }}>
                  Power{sortCol === 'power' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                </th>
                <th onClick={() => handleSort('cooldown')} style={{ cursor: 'pointer', textAlign: 'center', width: '80px' }}>
                  CD{sortCol === 'cooldown' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                </th>
                <th>Source / Tier / Rank</th>
                <th>Description / Effect</th>
                <th>Associated Pal / Item</th>
              </tr>
            </thead>
            <tbody>
              {sortedSkills.map((sk, idx) => {
                const typeColor = sk.type === 'Passive' ? '#60a5fa' : sk.type === 'Partner' ? 'var(--accent-gold)' : '#f87171';
                const typeBg = sk.type === 'Passive' ? 'rgba(59, 130, 246, 0.2)' : sk.type === 'Partner' ? 'rgba(234, 179, 8, 0.2)' : 'rgba(239, 68, 68, 0.2)';

                return (
                  <tr key={`${sk.id}-${sk.pal_id || idx}`}>
                    <td style={{ fontWeight: 600 }}>
                      {sk.type === 'Passive' ? (
                        <PassiveBadge skill={sk} size="md" />
                      ) : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                          {sk.pal_icon || sk.icon_path ? (
                            <img src={sk.pal_icon || sk.icon_path} alt={sk.pal_name || sk.name} style={{ width: '26px', height: '26px', objectFit: 'contain', borderRadius: '4px', background: 'rgba(0,0,0,0.2)' }} onError={(e) => { e.target.style.display = 'none'; }} />
                          ) : (
                            <span style={{ fontSize: '1rem' }}>⚡</span>
                          )}
                          <span style={{ color: 'var(--text-primary)' }}>{sk.name}</span>
                        </div>
                      )}
                    </td>
                    <td>
                      <span className="badge" style={{ background: typeBg, color: typeColor, fontSize: '0.7rem' }}>
                        {sk.type || 'Skill'}
                      </span>
                    </td>
                    <td>
                      {sk.element ? (
                        <span className="badge badge-element" style={{ fontSize: '0.7rem', padding: '0.1rem 0.35rem' }}>{sk.element}</span>
                      ) : '-'}
                    </td>
                    <td style={{ textAlign: 'center', fontWeight: 600, color: sk.power > 0 ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                      {sk.power > 0 ? sk.power : '-'}
                    </td>
                    <td style={{ textAlign: 'center', color: (sk.cooldown_sec || sk.cooldown) > 0 ? 'var(--accent-gold)' : 'var(--text-secondary)', fontWeight: 600 }}>
                      {(sk.cooldown_sec || sk.cooldown) > 0 ? `${sk.cooldown_sec || sk.cooldown}s` : '-'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                        {sk.source && (
                          <span className="badge" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.3)', fontSize: '0.68rem', padding: '0.05rem 0.3rem' }}>
                            {sk.source === 'Pals' ? '🐾 Pals' : sk.source === 'Equipment' ? '🛡️ Equipment' : sk.source === 'World Tree' ? '🌳 Tree' : sk.source === 'Mutation' ? '🧬 Mutation' : '👑 Legend'}
                          </span>
                        )}
                        {sk.aptitude && (
                          <span 
                            className="badge" 
                            style={{
                              background: 
                                sk.aptitude.color === 'red' ? 'rgba(239, 68, 68, 0.25)' :
                                sk.aptitude.color === 'gold' ? 'rgba(245, 158, 11, 0.25)' :
                                sk.aptitude.color === 'legend' ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.4), rgba(236, 72, 153, 0.4))' :
                                'rgba(255, 255, 255, 0.12)',
                              color: 
                                sk.aptitude.color === 'red' ? '#ef4444' :
                                sk.aptitude.color === 'gold' ? '#fbbf24' :
                                sk.aptitude.color === 'legend' ? '#f472b6' :
                                '#f8fafc',
                              fontWeight: 800,
                              fontSize: '0.68rem',
                              padding: '0.05rem 0.3rem'
                            }}
                          >
                            {sk.aptitude.label}
                          </span>
                        )}
                        {sk.rank !== undefined && sk.rank !== null && sk.rank !== 0 && (
                          <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.15)', color: 'var(--accent-gold)', fontSize: '0.68rem', padding: '0.05rem 0.3rem' }}>
                            Rank {sk.rank}
                          </span>
                        )}
                      </div>
                    </td>
                    <td style={{ fontSize: '0.8rem', maxWidth: '380px' }}>
                      {sk.stat_modifier && sk.stat_modifier !== sk.description && (
                        <div style={{ color: 'var(--accent-green)', fontWeight: 600, marginBottom: '0.15rem' }}>
                          ✨ {sk.stat_modifier}
                        </div>
                      )}
                      <span style={{ color: 'var(--text-secondary)' }}>{sk.description || '-'}</span>
                    </td>
                    <td style={{ fontSize: '0.78rem' }}>
                      {sk.pal_name && (
                        <div style={{ color: '#38bdf8', fontWeight: 600, marginBottom: '0.15rem' }}>
                          🐾 {sk.pal_name} {sk.paldex_number ? `(#${String(sk.paldex_number).padStart(3, '0')})` : ''}
                        </div>
                      )}
                      {sk.unlock_item && (
                        <div style={{ color: 'var(--accent-gold)' }}>
                          🔑 {sk.unlock_item}
                        </div>
                      )}
                      {sk.learned_by_pals && sk.learned_by_pals.length > 0 && !sk.pal_name && (
                        <span style={{ color: 'var(--text-secondary)' }}>
                          {sk.learned_by_pals.slice(0, 3).join(', ')}
                          {sk.learned_by_pals.length > 3 ? ` +${sk.learned_by_pals.length - 3}` : ''}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default SkillsCatalogView;
