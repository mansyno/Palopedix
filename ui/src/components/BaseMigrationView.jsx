import React, { useState, useEffect } from 'react';

export default function BaseMigrationView() {
  const [bases, setBases] = useState([]);
  const [loadingBases, setLoadingBases] = useState(true);
  const [sourceBaseId, setSourceBaseId] = useState('');
  const [targetBaseId, setTargetBaseId] = useState('');
  const [selectedTypes, setSelectedTypes] = useState({});
  const [manifest, setManifest] = useState(null);
  const [loadingManifest, setLoadingManifest] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [migrationResult, setMigrationResult] = useState(null);
  const [error, setError] = useState(null);
  const [expandedCategory, setExpandedCategory] = useState(null);
  const [copiedLabel, setCopiedLabel] = useState(null);

  // Fetch available bases and their container breakdown
  const fetchBases = async () => {
    setLoadingBases(true);
    setError(null);
    try {
      const res = await fetch('/api/migration/bases');
      if (!res.ok) {
        let errMessage = 'Failed to fetch base containers';
        try {
          const err = await res.json();
          errMessage = err.detail || errMessage;
        } catch {
          errMessage = `Server error (${res.status}): ${res.statusText}`;
        }
        throw new Error(errMessage);
      }
      const data = await res.json();
      setBases(data);
      if (data.length >= 2) {
        if (!sourceBaseId) setSourceBaseId(data[0].base_camp_id);
        if (!targetBaseId) setTargetBaseId(data[1].base_camp_id);
      } else if (data.length === 1) {
        if (!sourceBaseId) setSourceBaseId(data[0].base_camp_id);
      }
    } catch (err) {
      console.error('Error fetching migration bases:', err);
      setError(err.message);
    } finally {
      setLoadingBases(false);
    }
  };

  useEffect(() => {
    fetchBases();
  }, []);

  const sourceBase = bases.find(b => b.base_camp_id === sourceBaseId);
  const targetBase = bases.find(b => b.base_camp_id === targetBaseId);

  // When source base changes, reset container type filters (all checked by default)
  useEffect(() => {
    if (sourceBase) {
      const initialTypes = {};
      (sourceBase.container_types || []).forEach(t => {
        initialTypes[t.type_id] = true;
      });
      setSelectedTypes(initialTypes);
    }
  }, [sourceBaseId, bases]);

  const handleToggleType = (typeId) => {
    setSelectedTypes(prev => ({
      ...prev,
      [typeId]: !prev[typeId]
    }));
  };

  // Generate Construction Manifest
  const handleGenerateManifest = async () => {
    if (!sourceBaseId || !targetBaseId) {
      setError('Please select both a Source Base and a Target Base.');
      return;
    }
    if (sourceBaseId === targetBaseId) {
      setError('Source Base and Target Base cannot be the same base.');
      return;
    }

    setLoadingManifest(true);
    setError(null);
    setMigrationResult(null);

    const includedTypes = Object.entries(selectedTypes)
      .filter(([_, isChecked]) => isChecked)
      .map(([typeId]) => typeId);

    try {
      const res = await fetch('/api/migration/manifest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_base_id: sourceBaseId,
          target_base_id: targetBaseId,
          included_types: includedTypes.length > 0 ? includedTypes : null,
        })
      });

      if (!res.ok) {
        let errMessage = 'Failed to generate manifest';
        try {
          const err = await res.json();
          errMessage = err.detail || errMessage;
        } catch {
          errMessage = `Server error (${res.status}): ${res.statusText}`;
        }
        throw new Error(errMessage);
      }

      const data = await res.json();
      setManifest(data);
    } catch (err) {
      console.error('Manifest generation error:', err);
      setError(err.message);
    } finally {
      setLoadingManifest(false);
    }
  };

  // Execute migration
  const handleExecuteMigration = async (force = false) => {
    if (!manifest) return;
    setExecuting(true);
    setError(null);

    const includedTypes = Object.entries(selectedTypes)
      .filter(([_, isChecked]) => isChecked)
      .map(([typeId]) => typeId);

    try {
      const res = await fetch('/api/migration/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_base_id: sourceBaseId,
          target_base_id: targetBaseId,
          included_types: includedTypes.length > 0 ? includedTypes : null,
          force,
        })
      });

      if (!res.ok) {
        let errMessage = 'Migration failed';
        try {
          const err = await res.json();
          errMessage = err.detail || errMessage;
        } catch {
          errMessage = `Server error (${res.status}): ${res.statusText}`;
        }
        throw new Error(errMessage);
      }

      const data = await res.json();
      setMigrationResult(data);
      // Refresh bases list to reflect emptied containers
      fetchBases();
      setManifest(null);
    } catch (err) {
      console.error('Execution error:', err);
      setError(err.message);
    } finally {
      setExecuting(false);
    }
  };
  return (
    <div style={{
      flex: 1,
      height: '100%',
      minHeight: 0,
      overflowY: 'auto',
      padding: '1.5rem 2rem 6rem 2rem',
      maxWidth: '1200px',
      margin: '0 auto',
      width: '100%',
      boxSizing: 'border-box',
      color: 'var(--text-primary)'
    }}>
      {/* Header Banner */}
      <div className="glass-card" style={{ padding: '2rem', borderRadius: '16px', marginBottom: '2rem', background: 'linear-gradient(135deg, rgba(30, 27, 75, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%)', border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.75rem' }}>
          <div style={{ fontSize: '2.5rem' }}>🚚</div>
          <div>
            <h1 style={{ fontSize: '1.8rem', fontWeight: 800, background: 'var(--primary-gradient)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Base Container Migration & Logistics
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '1rem' }}>
              Relocate and auto-organize items from one base to another across 10 core categories with in-game named container matching.
            </p>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="glass-card" style={{ padding: '1.25rem', borderRadius: '12px', marginBottom: '1.5rem', border: '1px solid var(--accent-red)', background: 'rgba(239, 68, 68, 0.1)', color: '#fca5a5' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '1.3rem' }}>⚠️</span>
            <div style={{ flex: 1 }}>{error}</div>
            <button 
              onClick={() => setError(null)} 
              style={{ background: 'transparent', border: 'none', color: '#fca5a5', cursor: 'pointer', fontSize: '1.2rem' }}
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Success Result Alert */}
      {migrationResult && (
        <div className="glass-card" style={{ padding: '1.5rem', borderRadius: '12px', marginBottom: '2rem', border: '1px solid var(--accent-green)', background: 'rgba(16, 185, 129, 0.1)', color: '#a7f3d0' }}>
          <h3 style={{ fontSize: '1.3rem', fontWeight: 700, color: '#34d399', marginBottom: '0.75rem' }}>
            🎉 Container Migration Completed Successfully!
          </h3>
          <p style={{ marginBottom: '0.5rem', lineHeight: '1.6' }}>
            Transferred <strong>{migrationResult.total_item_stacks_moved} item stacks</strong> into <strong>{migrationResult.containers_populated} target containers</strong>.
          </p>
          <p style={{ marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Emptied <strong>{migrationResult.containers_emptied} source containers</strong> (left intact for safe in-game manual disassembly).
          </p>
          <p style={{ fontSize: '0.85rem', color: 'var(--accent-gold)' }}>
            📁 Verified Backup Created: <code>{migrationResult.backup_created}</code>
          </p>
        </div>
      )}

      {/* Step 1: Base Selection & Type Filtering */}
      <div className="glass-card" style={{ padding: '1.75rem', borderRadius: '16px', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '1.25rem', color: 'var(--accent-gold)' }}>
          Step 1: Select Bases & Container Types
        </h2>

        {loadingBases ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1rem' }}>
            <span className="loading-spinner" style={{ width: '20px', height: '20px' }}></span>
            <span>Scanning base camp containers in save file...</span>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
            {/* Source Base */}
            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                📍 SOURCE BASE (Move Items From)
              </label>
              <select
                value={sourceBaseId}
                onChange={(e) => setSourceBaseId(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  borderRadius: '10px',
                  background: 'rgba(0,0,0,0.5)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-primary)',
                  fontSize: '0.95rem',
                  fontWeight: 600,
                }}
              >
                {bases.map(b => (
                  <option key={b.base_camp_id} value={b.base_camp_id}>
                    {b.name} ({b.total_containers} containers, {b.total_items.toLocaleString()} items)
                  </option>
                ))}
              </select>
            </div>

            {/* Target Base */}
            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                🎯 TARGET BASE (Move Items To)
              </label>
              <select
                value={targetBaseId}
                onChange={(e) => setTargetBaseId(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  borderRadius: '10px',
                  background: 'rgba(0,0,0,0.5)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-primary)',
                  fontSize: '0.95rem',
                  fontWeight: 600,
                }}
              >
                {bases.map(b => (
                  <option key={b.base_camp_id} value={b.base_camp_id} disabled={b.base_camp_id === sourceBaseId}>
                    {b.name} ({b.total_containers} containers currently)
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {/* Container Types Filter Checkboxes */}
        {sourceBase && sourceBase.container_types && sourceBase.container_types.length > 0 && (
          <div style={{ marginTop: '1rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border-color)' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.75rem', color: 'var(--text-secondary)' }}>
              📦 SOURCE CONTAINER TYPES TO INCLUDE
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
              {sourceBase.container_types.map(t => {
                const checked = !!selectedTypes[t.type_id];
                return (
                  <div
                    key={t.type_id}
                    onClick={() => handleToggleType(t.type_id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.6rem',
                      padding: '0.5rem 1rem',
                      borderRadius: '8px',
                      background: checked ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255,255,255,0.03)',
                      border: checked ? '1px solid var(--border-color-hover)' : '1px solid rgba(255,255,255,0.08)',
                      cursor: 'pointer',
                      userSelect: 'none',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => {}}
                      style={{ cursor: 'pointer' }}
                    />
                    <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                      {t.name}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--accent-gold)', background: 'rgba(251, 191, 36, 0.1)', padding: '0.15rem 0.45rem', borderRadius: '4px' }}>
                      {t.count} chests
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Loading Sandclock Banner */}
        {loadingManifest && (
          <div style={{
            marginTop: '1.5rem',
            padding: '1.25rem 1.5rem',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(30, 27, 75, 0.3) 100%)',
            border: '1px solid rgba(99, 102, 241, 0.4)',
            display: 'flex',
            alignItems: 'center',
            gap: '1.25rem',
          }}>
            <div style={{ fontSize: '2.5rem' }} className="anim-sandclock">
              ⏳
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '1.05rem', color: 'var(--text-primary)', marginBottom: '0.2rem' }}>
                Analyzing Base Containers & Calculating Slots...
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Reading save file, calculating required container slots, and checking existing Base 2 chests.
              </div>
            </div>
          </div>
        )}

        {/* Generate Manifest Button */}
        <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
          <button
            className="primary-btn"
            onClick={handleGenerateManifest}
            disabled={loadingManifest || !sourceBaseId || !targetBaseId}
            style={{ padding: '0.75rem 1.75rem', fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            {loadingManifest ? (
              <>
                <span className="anim-sandclock">⏳</span> Computing Slots & Manifest...
              </>
            ) : (
              '📋 Calculate Construction Manifest'
            )}
          </button>
        </div>
      </div>

      {/* Step 2 & 3: Manifest Checklist & Relocation */}
      {manifest && (
        <div className="glass-card" style={{ padding: '2rem', borderRadius: '16px', marginBottom: '2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--accent-gold)' }}>
                Step 2: Base 2 Construction Manifest
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
                Build and name the containers below at Base 2 in Palworld. The engine will detect them automatically.
              </p>
            </div>
            <button
              className="secondary-btn"
              onClick={handleGenerateManifest}
              disabled={loadingManifest}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem' }}
            >
              {loadingManifest ? <span className="anim-sandclock">⏳</span> : '🔄'} Refresh Status
            </button>
          </div>

          {/* Quick Metrics Bar: Slots & Container Capacities */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700 }}>SLOTS OCCUPIED</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                {manifest.total_source_slots || manifest.total_slots_needed} <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>slots</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                across {manifest.total_source_containers} source chests
              </div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700 }}>TARGET SLOTS NEEDED</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--accent-gold)' }}>
                {manifest.total_slots_needed} <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>/ {manifest.total_capacity_needed} cap</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                allocated into category chests
              </div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700 }}>CHESTS REQUIRED</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--accent-gold)' }}>
                {manifest.manifest.length} <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>chests</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                based on 1:1 container types
              </div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700 }}>READY AT BASE 2</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: manifest.all_ready_to_migrate ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                {manifest.manifest.filter(c => c.is_ready).length} / {manifest.manifest.length}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                named & matching type
              </div>
            </div>
          </div>

          {/* Category Manifest Cards */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2rem' }}>
            {manifest.category_summaries.map(cat => {
              const isExpanded = expandedCategory === cat.category_id;
              return (
                <div
                  key={cat.category_id}
                  style={{
                    background: 'rgba(15, 23, 42, 0.6)',
                    borderRadius: '12px',
                    border: '1px solid var(--border-color)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      padding: '1rem 1.25rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      background: 'rgba(255,255,255,0.02)',
                    }}
                    onClick={() => setExpandedCategory(isExpanded ? null : cat.category_id)}
                  >
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-primary)' }}>
                        {cat.category_name}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        {cat.total_unique_items} unique items • {cat.total_slots_needed} slots • {cat.containers_needed} containers
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span style={{ fontSize: '0.85rem', color: 'var(--accent-gold)' }}>
                        {isExpanded ? '▲ Hide Items' : '▼ View Items'}
                      </span>
                    </div>
                  </div>

                  {/* Containers List for this category */}
                  <div style={{ padding: '0.75rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', background: 'rgba(0,0,0,0.2)' }}>
                    {cat.containers.map((box, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '0.6rem 0.9rem',
                          borderRadius: '8px',
                          background: box.is_ready ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.05)',
                          border: box.is_ready ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.2)',
                          fontSize: '0.9rem',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                          <span style={{ fontWeight: 800, color: 'var(--accent-gold)', fontFamily: 'monospace', fontSize: '1rem' }}>
                            {box.box_label}
                          </span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigator.clipboard.writeText(box.box_label);
                              setCopiedLabel(box.box_label);
                              setTimeout(() => setCopiedLabel(null), 1500);
                            }}
                            style={{
                              background: copiedLabel === box.box_label ? 'rgba(16, 185, 129, 0.25)' : 'rgba(255,255,255,0.08)',
                              border: copiedLabel === box.box_label ? '1px solid var(--accent-green)' : '1px solid var(--border-color)',
                              color: copiedLabel === box.box_label ? 'var(--accent-green)' : 'var(--text-primary)',
                              borderRadius: '6px',
                              padding: '0.2rem 0.5rem',
                              fontSize: '0.75rem',
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.3rem',
                              fontWeight: 600,
                              transition: 'all 0.15s ease',
                            }}
                            title="Copy chest name to clipboard"
                          >
                            {copiedLabel === box.box_label ? '✓ Copied' : '📋 Copy'}
                          </button>
                          <span style={{ fontSize: '0.72rem', color: box.box_label.length <= 24 ? 'var(--text-secondary)' : '#f87171', background: 'rgba(0,0,0,0.3)', padding: '0.15rem 0.4rem', borderRadius: '4px' }}>
                            {box.box_label.length}/24 chars
                          </span>
                          <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                            Type: <strong>{box.recommended_container_name}</strong> ({box.slots_required}/{box.container_capacity} slots)
                          </span>
                        </div>

                        <div>
                          {box.is_ready ? (
                            <span style={{ color: 'var(--accent-green)', fontWeight: 700, fontSize: '0.85rem' }}>
                              ✅ Detected at Base 2 ({box.matched_target_custom_name})
                            </span>
                          ) : box.type_mismatch ? (
                            <span style={{ color: '#f87171', fontWeight: 600, fontSize: '0.85rem' }}>
                              ⚠️ Found "{box.matched_target_custom_name}", but it is a {box.matched_container_name} ({box.recommended_container_name} required)
                            </span>
                          ) : (
                            <span style={{ color: '#fca5a5', fontSize: '0.85rem' }}>
                              ⏳ Build & name chest <strong>{box.box_label}</strong>
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Expanded Item Breakdown */}
                  {isExpanded && (
                    <div style={{ padding: '1rem 1.25rem', borderTop: '1px solid rgba(255,255,255,0.05)', background: 'rgba(0,0,0,0.3)', maxHeight: '240px', overflowY: 'auto' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '0.5rem', fontSize: '0.85rem' }}>
                        {cat.items.map((item, i) => (
                          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.35rem 0.6rem', background: 'rgba(255,255,255,0.02)', borderRadius: '6px' }}>
                            <span style={{ color: 'var(--text-primary)' }}>{item.item_id}</span>
                            <span style={{ color: 'var(--accent-gold)', fontWeight: 700 }}>
                              {item.count.toLocaleString()} <span style={{ color: 'var(--text-secondary)', fontWeight: 400 }}>({item.stacks} slt)</span>
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Step 3: Execution Section */}
          <div style={{ paddingTop: '1.5rem', borderTop: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '0.75rem', color: 'var(--text-primary)' }}>
              Step 3: Execute Transfer
            </h3>

            {!manifest.all_ready_to_migrate ? (
              <div style={{ padding: '1rem', background: 'rgba(251, 191, 36, 0.1)', border: '1px solid rgba(251, 191, 36, 0.3)', borderRadius: '10px', color: '#fde68a', fontSize: '0.9rem' }}>
                <p style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
                  ⏳ Awaiting Target Container Construction
                </p>
                <p>
                  Build the remaining containers at Base 2 in Palworld and set their names exactly as labeled above (e.g. <code>[Metals 1]</code>). Once placed, click <strong>"🔄 Refresh Status"</strong> to verify.
                </p>
              </div>
            ) : (
              <div>
                <div style={{ padding: '1rem', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '10px', color: '#a7f3d0', marginBottom: '1.25rem', fontSize: '0.9rem' }}>
                  <p style={{ fontWeight: 700, marginBottom: '0.25rem' }}>
                    ✅ All Target Containers Detected & Ready!
                  </p>
                  <p>
                    All required containers are placed and named at Base 2. Please ensure Palworld is <strong>saved and closed completely</strong> before clicking execute to avoid file conflicts.
                  </p>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                  <button
                    className="primary-btn"
                    onClick={() => handleExecuteMigration(false)}
                    disabled={executing}
                    style={{
                      padding: '0.85rem 2rem',
                      fontSize: '1.05rem',
                      fontWeight: 800,
                      background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                      boxShadow: '0 8px 25px rgba(16, 185, 129, 0.35)',
                    }}
                  >
                    {executing ? '⚙️ Transferring Items & Saving...' : '🚀 Execute Transfer & Empty Source Containers'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
