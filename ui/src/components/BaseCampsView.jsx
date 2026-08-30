import React, { useState, useEffect } from 'react';
import { BASE_CATEGORY_MAP } from '../constants/gameData';
import { useTableSort } from '../hooks/useTableSort';
import { PassiveBadge } from './common/PassiveBadge';

export function BaseCampsView({ bases = [], saveLoaded, fetchBases, fetchInstances }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0, paddingRight: '0.4rem', paddingBottom: '2rem' }}>
        {!saveLoaded ? (
          <div className="glass-card" style={{ textAlign: 'center', padding: '4rem' }}>
            <p style={{ color: 'var(--text-secondary)', fontSize: '1.25rem' }}>No save file loaded. Please load a save file in the Save Game tab first.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {bases.map(base => (
              <BaseCampCard
                key={base.base_camp_id}
                base={base}
                onBaseRenamed={() => {
                  fetchBases();
                  fetchInstances();
                }}
              />
            ))}
            {bases.length === 0 && <p style={{ color: 'var(--text-secondary)' }}>No base camps found in save file.</p>}
          </div>
        )}
      </div>
    </div>
  );
}

export function BaseCampCard({ base = {}, onBaseRenamed }) {
  const [workerSearch, setWorkerSearch] = useState('');
  const [structSearch, setStructSearch] = useState('');

  const [isEditing, setIsEditing] = useState(false);
  const initialName = base.custom_name || base.display_name || base.name || 'Unnamed Base';
  const [customName, setCustomName] = useState(initialName);
  const [displayName, setDisplayName] = useState(initialName);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const updated = base.custom_name || base.display_name || base.name || 'Unnamed Base';
    setDisplayName(updated);
    setCustomName(updated);
  }, [base.custom_name, base.display_name, base.name]);

  const handleSaveName = async () => {
    const trimmed = customName.trim();
    if (!trimmed || trimmed === displayName) {
      setIsEditing(false);
      return;
    }
    setIsSaving(true);
    try {
      const res = await fetch(`/api/base_camps/${encodeURIComponent(base.base_camp_id)}/name`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ custom_name: trimmed }),
      });
      if (res.ok) {
        setDisplayName(trimmed);
        if (onBaseRenamed) onBaseRenamed(base.base_camp_id, trimmed);
      }
    } catch (err) {
      console.error('Failed to rename base camp:', err);
    } finally {
      setIsSaving(false);
      setIsEditing(false);
    }
  };

  const workersList = Array.isArray(base.workers) ? base.workers : [];
  const filteredWorkers = workersList.filter(w => (w.display_name || w.species || '').toLowerCase().includes(workerSearch.toLowerCase()));
  const {
    sortedData: sortedWorkers,
    sortCol: workerSortCol,
    sortDesc: workerSortDesc,
    handleSort: handleWorkerSort,
  } = useTableSort(filteredWorkers, 'level', true);

  const structsList = Array.isArray(base.structures) ? base.structures : [];
  const filteredStructs = structsList.filter(s => (s.display_name || s.structure_name || '').toLowerCase().includes(structSearch.toLowerCase()));
  const {
    sortedData: sortedStructs,
    sortCol: structSortCol,
    sortDesc: structSortDesc,
    handleSort: handleStructSort,
  } = useTableSort(filteredStructs, 'count', true);

  const catInfo = BASE_CATEGORY_MAP[base.base_category] || BASE_CATEGORY_MAP['Balanced'];

  return (
    <div className="glass-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem', flexWrap: 'wrap', gap: '0.6rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span style={{ fontSize: '1.35rem' }}>🏰</span>
          {isEditing ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <input
                type="text"
                autoFocus
                value={customName}
                onChange={e => setCustomName(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') handleSaveName();
                  if (e.key === 'Escape') {
                    setCustomName(displayName);
                    setIsEditing(false);
                  }
                }}
                onBlur={handleSaveName}
                disabled={isSaving}
                placeholder="Enter base camp name..."
                style={{
                  fontSize: '1.15rem',
                  fontWeight: 800,
                  padding: '0.25rem 0.6rem',
                  borderRadius: '6px',
                  background: 'rgba(15, 23, 42, 0.85)',
                  border: '1px solid var(--accent-gold)',
                  color: 'var(--text-primary)',
                  width: '240px',
                }}
              />
              <button
                className="btn btn-primary"
                onClick={handleSaveName}
                disabled={isSaving}
                style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem', fontWeight: 700 }}
              >
                {isSaving ? '...' : 'Save'}
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => { setCustomName(displayName); setIsEditing(false); }}
                disabled={isSaving}
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
              >
                ✕
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <h2 style={{ margin: 0, fontWeight: 800, fontSize: '1.3rem' }}>
                {displayName}
              </h2>
              <button
                title="Rename this base camp in Palopedix"
                onClick={() => {
                  setCustomName(displayName);
                  setIsEditing(true);
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '0.95rem',
                  padding: '0.2rem 0.4rem',
                  borderRadius: '4px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={e => e.currentTarget.style.color = 'var(--accent-gold)'}
                onMouseLeave={e => e.currentTarget.style.color = 'var(--text-secondary)'}
              >
                ✏️
              </button>
            </div>
          )}
        </div>

        {/* Focus Category Badge */}
        {catInfo && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: catInfo.color, border: `1px solid ${catInfo.border}`, padding: '0.25rem 0.65rem', borderRadius: '8px', fontSize: '0.78rem', fontWeight: 700, color: catInfo.text }}>
            <span>{catInfo.emoji}</span>
            <span>{base.base_category || 'Balanced'} Focus</span>
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* Worker summary */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ color: 'var(--text-secondary)' }}>Workers ({workersList.length})</h3>
            <input type="text" placeholder="Search pals..." value={workerSearch} onChange={e => setWorkerSearch(e.target.value)} style={{ padding: '0.4rem 0.8rem', width: '150px' }} />
          </div>
          <div className="glass-card table-container" style={{ padding: '0', background: 'rgba(0,0,0,0.2)', maxHeight: '320px', overflow: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th onClick={() => handleWorkerSort('display_name')} style={{cursor:'pointer'}}>Species{workerSortCol === 'display_name' ? (workerSortDesc ? ' ▼' : ' ▲') : ''}</th>
                  <th onClick={() => handleWorkerSort('level')} style={{cursor:'pointer'}}>Level{workerSortCol === 'level' ? (workerSortDesc ? ' ▼' : ' ▲') : ''}</th>
                  <th onClick={() => handleWorkerSort('gender')} style={{cursor:'pointer'}}>Gender{workerSortCol === 'gender' ? (workerSortDesc ? ' ▼' : ' ▲') : ''}</th>
                  <th onClick={() => handleWorkerSort('rank')} style={{cursor:'pointer'}}>Rank{workerSortCol === 'rank' ? (workerSortDesc ? ' ▼' : ' ▲') : ''}</th>
                  <th>Passives</th>
                </tr>
              </thead>
              <tbody>
                {sortedWorkers.map((w, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600 }}>{w.display_name || w.species}</td>
                    <td>Lv. {w.level}</td>
                    <td>{w.gender}</td>
                    <td>{w.rank ? '⭐'.repeat(w.rank) : '-'}</td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', alignItems: 'center' }}>
                        {(w.passives || []).map((pass, pIdx) => (
                          <PassiveBadge key={pIdx} skill={pass} size="sm" />
                        ))}
                        {(!w.passives || w.passives.length === 0) && <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>None</span>}
                      </div>
                    </td>
                  </tr>
                ))}
                {sortedWorkers.length === 0 && (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '1rem' }}>No workers assigned.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Structure summary */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ color: 'var(--text-secondary)' }}>Placed Structures ({structsList.length})</h3>
            <input type="text" placeholder="Search facilities..." value={structSearch} onChange={e => setStructSearch(e.target.value)} style={{ padding: '0.4rem 0.8rem', width: '150px' }} />
          </div>
          <div className="glass-card table-container" style={{ padding: '0', background: 'rgba(0,0,0,0.2)', maxHeight: '320px', overflow: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th onClick={() => handleStructSort('display_name')} style={{cursor:'pointer'}}>Facility Name{structSortCol === 'display_name' ? (structSortDesc ? ' ▼' : ' ▲') : ''}</th>
                  <th onClick={() => handleStructSort('count')} style={{cursor:'pointer', width: '80px', textAlign: 'center'}}>Count{structSortCol === 'count' ? (structSortDesc ? ' ▼' : ' ▲') : ''}</th>
                  <th>Category</th>
                </tr>
              </thead>
              <tbody>
                {sortedStructs.map((s, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600 }}>{s.display_name || s.structure_name}</td>
                    <td style={{ textAlign: 'center', fontWeight: 800, color: 'var(--accent-gold)' }}>x{s.count}</td>
                    <td>
                      <span className="badge" style={{ background: 'rgba(255,255,255,0.08)', fontSize: '0.72rem' }}>
                        {s.category || 'Facility'}
                      </span>
                    </td>
                  </tr>
                ))}
                {sortedStructs.length === 0 && (
                  <tr>
                    <td colSpan="3" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '1rem' }}>No structures found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BaseCampsView;
