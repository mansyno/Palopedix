import React, { useState } from 'react';
import { PalInstanceTooltip } from './common/PalInstanceTooltip';
import { PassiveBadge } from './common/PassiveBadge';

export function BreedingCenterView({
  pals = [],
  allMasterPals = [],
  ownedSpecies = [],
  palSourceMode = 'global',
  handlePalSourceModeChange,
  setSelectedPal,
  availablePalOptions = [],
  ownedPals,
  setOwnedPals,
}) {
  const [breedingSubTab, setBreedingSubTab] = useState('calculator'); // 'calculator', 'reverse', 'offspring', 'path', 'uncaught'

  // Calculator Sub-tab State
  const [parent1, setParent1] = useState('');
  const [parent2, setParent2] = useState('');
  const [breedResult, setBreedResult] = useState(null);
  const [breedError, setBreedError] = useState('');

  // Reverse Lookup Sub-tab State
  const [reverseChild, setReverseChild] = useState('');
  const [parentCombos, setParentCombos] = useState([]);
  const [reverseLoading, setReverseLoading] = useState(false);
  const [reverseSearched, setReverseSearched] = useState(false);
  const [reverseSearchTerm, setReverseSearchTerm] = useState('');

  // Possible Offspring Sub-tab State
  const [offspringParent, setOffspringParent] = useState('');
  const [offspringResults, setOffspringResults] = useState([]);
  const [offspringLoading, setOffspringLoading] = useState(false);
  const [offspringSearched, setOffspringSearched] = useState(false);
  const [offspringSearchTerm, setOffspringSearchTerm] = useState('');

  // Multi-Step Path Finder Sub-tab State
  const [targetPal, setTargetPal] = useState('');
  const [targetSkills, setTargetSkills] = useState('');
  const [allBreedingPaths, setAllBreedingPaths] = useState([]);
  const [activePathIdx, setActivePathIdx] = useState(0);
  const [pathLoading, setPathLoading] = useState(false);
  const [pathError, setPathError] = useState('');
  const [pathSearched, setPathSearched] = useState(false);

  // Uncaught Species Finder Sub-tab State
  const [uncaughtOpportunities, setUncaughtOpportunities] = useState([]);
  const [uncaughtLoading, setUncaughtLoading] = useState(false);
  const [uncaughtSearchTerm, setUncaughtSearchTerm] = useState('');
  const [expandedUncaughtSpecies, setExpandedUncaughtSpecies] = useState(null);
  const [uncaughtTableSortCol, setUncaughtTableSortCol] = useState('parent1');
  const [uncaughtTableSortDesc, setUncaughtTableSortDesc] = useState(false);
  const [fallbackGlobalOptions, setFallbackGlobalOptions] = useState([]);

  const openPalDetails = (palOrName) => {
    if (!palOrName || !setSelectedPal) return;
    if (typeof palOrName === 'object' && palOrName !== null) {
      const name = palOrName.display_name || palOrName.species || palOrName.name;
      const master = pals.find(p => p.display_name?.toLowerCase() === name?.toLowerCase() || p.id === palOrName.id) ||
                     allMasterPals.find(p => p.display_name?.toLowerCase() === name?.toLowerCase() || p.id === palOrName.id);
      setSelectedPal({
        ...(master || {}),
        ...palOrName,
        display_name: name || master?.display_name,
      });
    } else if (typeof palOrName === 'string') {
      const name = palOrName.trim();
      const master = pals.find(p => p.display_name?.toLowerCase() === name.toLowerCase() || p.id?.toLowerCase() === name.toLowerCase()) ||
                     allMasterPals.find(p => p.display_name?.toLowerCase() === name.toLowerCase() || p.id?.toLowerCase() === name.toLowerCase());
      if (master) {
        setSelectedPal(master);
      } else {
        setSelectedPal({ display_name: name });
      }
    }
  };

  React.useEffect(() => {
    if ((!availablePalOptions || availablePalOptions.length === 0) && palSourceMode === 'global') {
      fetch('/api/pals')
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) {
            setFallbackGlobalOptions(Array.from(new Set(data.map(p => p.display_name).filter(Boolean))).sort());
          }
        })
        .catch(err => console.error('Error fetching fallback breeding options:', err));
    }
  }, [availablePalOptions, palSourceMode]);

  const effectivePalOptions = (availablePalOptions && availablePalOptions.length > 0)
    ? availablePalOptions
    : (palSourceMode === 'global' ? fallbackGlobalOptions : []);

  // Direct Pair Calculation Handler
  const handleCalculateBreed = async () => {
    if (!parent1 || !parent2) return;
    setBreedError('');
    setBreedResult(null);
    try {
      const res = await fetch(`/api/breeding/result?parent1=${encodeURIComponent(parent1)}&parent2=${encodeURIComponent(parent2)}`);
      const data = await res.json();
      if (!res.ok) {
        setBreedError(data.detail || 'Could not calculate breeding result.');
      } else {
        setBreedResult(data);
      }
    } catch (err) {
      setBreedError('Failed to connect to backend server.');
    }
  };

  // Reverse Combos Lookup Handler
  const handleCalculateReverse = async () => {
    if (!reverseChild) return;
    setReverseLoading(true);
    setParentCombos([]);
    setReverseSearched(true);
    setReverseSearchTerm(reverseChild);
    try {
      const ownedMode = palSourceMode === 'global' ? 'all' : 'caught';
      const url = `/api/breeding/parents?child=${encodeURIComponent(reverseChild)}&owned=${encodeURIComponent(ownedMode)}`;
      const res = await fetch(url);
      const data = await res.json();
      if (res.ok && Array.isArray(data)) {
        setParentCombos(data);
      } else {
        setParentCombos([]);
      }
    } catch (err) {
      console.error('Reverse lookup error:', err);
      setParentCombos([]);
    } finally {
      setReverseLoading(false);
    }
  };

  // Possible Offspring Handler
  const handleCalculateOffspring = async () => {
    if (!offspringParent) return;
    setOffspringLoading(true);
    setOffspringResults([]);
    setOffspringSearched(true);
    setOffspringSearchTerm(offspringParent);
    try {
      const ownedMode = palSourceMode === 'global' ? 'all' : 'caught';
      const url = `/api/breeding/offspring?parent=${encodeURIComponent(offspringParent)}&owned=${encodeURIComponent(ownedMode)}`;
      const res = await fetch(url);
      const data = await res.json();
      if (res.ok && Array.isArray(data)) {
        setOffspringResults(data);
      } else {
        setOffspringResults([]);
      }
    } catch (err) {
      console.error('Offspring lookup error:', err);
      setOffspringResults([]);
    } finally {
      setOffspringLoading(false);
    }
  };

  // Multi-Step Path Finding Handler
  const handleFindPath = async () => {
    if (!targetPal) return;
    setPathLoading(true);
    setPathError('');
    setAllBreedingPaths([]);
    setActivePathIdx(0);
    setPathSearched(true);

    try {
      let url = `/api/breeding/path?target=${encodeURIComponent(targetPal)}`;
      if (ownedPals && ownedPals.trim()) {
        url += `&owned=${encodeURIComponent(ownedPals.trim())}`;
      } else {
        url += `&owned=${palSourceMode === 'global' ? 'all' : 'caught'}`;
      }
      if (targetSkills && targetSkills.trim()) {
        url += `&target_skills=${encodeURIComponent(targetSkills.trim())}`;
      }

      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok) {
        setPathError(data.detail || 'Could not find a valid breeding path.');
      } else {
        if (data.paths && Array.isArray(data.paths)) {
          setAllBreedingPaths(data.paths);
        } else if (data.steps) {
          setAllBreedingPaths([{
            title: 'Optimal Shortest Path',
            difficulty: data.steps.length === 1 ? 'Direct Pair (1 Step)' : `${data.steps.length} Steps`,
            steps: data.steps,
          }]);
        }
      }
    } catch (err) {
      setPathError('Failed to connect to backend server.');
    } finally {
      setPathLoading(false);
    }
  };

  // Fetch Uncaught Opportunities
  const fetchUncaughtOpportunities = async () => {
    setUncaughtLoading(true);
    try {
      const ownedMode = palSourceMode === 'global' ? 'all' : 'caught';
      const url = `/api/breeding/uncaught?owned=${encodeURIComponent(ownedMode)}`;
      const res = await fetch(url);
      const data = await res.json();
      if (res.ok && Array.isArray(data)) {
        setUncaughtOpportunities(data);
      } else {
        setUncaughtOpportunities([]);
      }
    } catch (err) {
      console.error('Uncaught opportunities error:', err);
      setUncaughtOpportunities([]);
    } finally {
      setUncaughtLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      {/* Top Fixed Header: Source Selector & Sub-Navigation Tabs */}
      <div style={{ flexShrink: 0, marginBottom: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
        {/* Top Source Switch Bar */}
        <div className="glass-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', padding: '0.75rem 1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.2rem' }}>🐣</span>
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 800, margin: 0 }}>Breeding Center Suite</h3>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                Calculators, reverse lookup, offspring explorer, and BFS multi-step pathfinder
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button 
              className={`btn ${palSourceMode === 'global' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '0.35rem 0.85rem', fontSize: '0.78rem', fontWeight: 600 }}
              onClick={() => handlePalSourceModeChange('global')}
            >
              🌐 All Game Pals ({allMasterPals ? allMasterPals.length : (pals ? pals.length : effectivePalOptions.length)})
            </button>
            <button 
              className={`btn ${palSourceMode === 'caught' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ padding: '0.35rem 0.85rem', fontSize: '0.78rem', fontWeight: 600 }}
              onClick={() => handlePalSourceModeChange('caught')}
            >
              💼 My Caught Pals ({ownedSpecies.length})
            </button>
          </div>
        </div>

        {/* Sub-Navigation Ribbon */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem', width: '100%' }}>
          <button
            className={`btn ${breedingSubTab === 'calculator' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '0.4rem 0.9rem', fontSize: '0.82rem', fontWeight: 700, borderRadius: '8px' }}
            onClick={() => setBreedingSubTab('calculator')}
          >
            🐣 Direct Pair Calculator
          </button>
          <button
            className={`btn ${breedingSubTab === 'reverse' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '0.4rem 0.9rem', fontSize: '0.82rem', fontWeight: 700, borderRadius: '8px' }}
            onClick={() => setBreedingSubTab('reverse')}
          >
            🔍 Reverse Combos Lookup
          </button>
          <button
            className={`btn ${breedingSubTab === 'offspring' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '0.4rem 0.9rem', fontSize: '0.82rem', fontWeight: 700, borderRadius: '8px' }}
            onClick={() => setBreedingSubTab('offspring')}
          >
            🌱 Possible Offspring
          </button>
          <button
            className={`btn ${breedingSubTab === 'path' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '0.4rem 0.9rem', fontSize: '0.82rem', fontWeight: 700, borderRadius: '8px' }}
            onClick={() => setBreedingSubTab('path')}
          >
            🧬 Multi-Step Path Finder
          </button>
          <button
            className={`btn ${breedingSubTab === 'uncaught' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '0.4rem 0.9rem', fontSize: '0.82rem', fontWeight: 700, borderRadius: '8px' }}
            onClick={() => {
              setBreedingSubTab('uncaught');
              fetchUncaughtOpportunities();
            }}
          >
            ✨ Uncaught Species Finder
          </button>
        </div>
      </div>

      {/* 1. DIRECT CALCULATOR SUB-TAB */}
      {breedingSubTab === 'calculator' && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'auto', gap: '1rem' }}>
          <div className="glass-card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto auto', gap: '1rem', alignItems: 'end' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.35rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Parent 1</label>
                <select 
                  style={{ width: '100%', padding: '0.5rem 0.75rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.88rem' }}
                  value={parent1} 
                  onChange={e => setParent1(e.target.value)}
                >
                  <option value="">-- Select Parent 1 --</option>
                  {effectivePalOptions.map((name, idx) => (
                    <option key={idx} value={name}>{name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.35rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Parent 2</label>
                <select 
                  style={{ width: '100%', padding: '0.5rem 0.75rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.88rem' }}
                  value={parent2} 
                  onChange={e => setParent2(e.target.value)}
                >
                  <option value="">-- Select Parent 2 --</option>
                  {effectivePalOptions.map((name, idx) => (
                    <option key={idx} value={name}>{name}</option>
                  ))}
                </select>
              </div>
              <button className="btn btn-primary" onClick={handleCalculateBreed} disabled={!parent1 || !parent2} style={{ padding: '0.5rem 1.25rem', fontSize: '0.88rem' }}>
                Calculate
              </button>
              {(parent1 || parent2 || breedResult || breedError) && (
                <button 
                  className="btn btn-secondary" 
                  onClick={() => { setParent1(''); setParent2(''); setBreedResult(null); setBreedError(''); }}
                  style={{ padding: '0.5rem 0.85rem', fontSize: '0.88rem' }}
                >
                  ✕ Clear
                </button>
              )}
            </div>

            {breedError && (
              <div style={{ marginTop: '1rem', color: '#f87171', padding: '0.75rem 1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)', fontSize: '0.88rem' }}>
                ⚠️ {breedError}
              </div>
            )}
          </div>

          {breedResult && (
            <div 
              className="glass-card" 
              style={{ padding: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(99, 102, 241, 0.15)', borderColor: 'var(--border-color-hover)', borderRadius: '12px', cursor: 'pointer' }}
              onClick={() => openPalDetails(breedResult)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                {breedResult.icon_path ? (
                  <img src={breedResult.icon_path} alt={breedResult.display_name} style={{ width: '64px', height: '64px', borderRadius: '12px', objectFit: 'cover' }} onError={(e) => { e.target.style.display = 'none'; }} />
                ) : (
                  <div style={{ width: '64px', height: '64px', borderRadius: '12px', background: 'var(--primary-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '1.5rem' }}>
                    {breedResult.display_name ? breedResult.display_name[0] : 'P'}
                  </div>
                )}
                <div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Offspring Result (Click for Bio & Stats):</div>
                  <h3 style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0, color: '#34d399' }}>{breedResult.display_name}</h3>
                  <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.35rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    <span>Breeding Power: <strong style={{ color: 'var(--accent-gold)' }}>{breedResult.breeding_power}</strong></span>
                    <span>Food: <strong>🍖 {breedResult.food_requirement || 1}</strong></span>
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
                <div className="badge-container">
                  {breedResult.element_1 && <span className="badge badge-element">{breedResult.element_1}</span>}
                  {breedResult.element_2 && <span className="badge badge-element">{breedResult.element_2}</span>}
                </div>
                <button 
                  className="btn btn-secondary" 
                  style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }} 
                  onClick={(e) => { e.stopPropagation(); openPalDetails(breedResult); }}
                >
                  Inspect Pal in Paldex →
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 2. REVERSE LOOKUP SUB-TAB */}
      {breedingSubTab === 'reverse' && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
          <div className="glass-card" style={{ padding: '1rem 1.25rem', marginBottom: '0.75rem', flexShrink: 0 }}>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'end' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '0.35rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Target Child Pal</label>
                <select 
                  style={{ width: '100%', padding: '0.5rem 0.75rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.88rem' }}
                  value={reverseChild} 
                  onChange={e => setReverseChild(e.target.value)}
                >
                  <option value="">-- Select Target Child Pal --</option>
                  {effectivePalOptions.map((name, idx) => (
                    <option key={idx} value={name}>{name}</option>
                  ))}
                </select>
              </div>
              <button className="btn btn-primary" onClick={handleCalculateReverse} disabled={!reverseChild || reverseLoading} style={{ padding: '0.5rem 1.25rem', fontSize: '0.88rem' }}>
                {reverseLoading ? 'Searching...' : 'Find Combinations'}
              </button>
              {(reverseChild || parentCombos.length > 0 || reverseSearched) && (
                <button 
                  className="btn btn-secondary" 
                  onClick={() => { setReverseChild(''); setParentCombos([]); setReverseSearched(false); setReverseSearchTerm(''); }}
                  style={{ padding: '0.5rem 0.85rem', fontSize: '0.88rem' }}
                >
                  ✕ Clear
                </button>
              )}
            </div>
          </div>

          {reverseSearched && !reverseLoading && (
            parentCombos.length > 0 ? (
              <div className="glass-card table-container" style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 0, marginBottom: '1.5rem' }}>
                <table>
                  <thead>
                    <tr>
                      <th style={{ width: '80px', textAlign: 'center' }}>#</th>
                      <th>Parent 1</th>
                      <th>Parent 2</th>
                      <th style={{ textAlign: 'center', width: '140px' }}>Target Child</th>
                    </tr>
                  </thead>
                  <tbody>
                    {parentCombos.map((combo, idx) => (
                      <tr key={idx}>
                        <td style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{idx + 1}</td>
                        <td style={{ fontWeight: 600, color: 'var(--accent-gold)', cursor: 'pointer' }} onClick={() => openPalDetails(combo[0])}>
                          {combo[0]}
                        </td>
                        <td style={{ fontWeight: 600, color: 'var(--accent-gold)', cursor: 'pointer' }} onClick={() => openPalDetails(combo[1])}>
                          {combo[1]}
                        </td>
                        <td style={{ textAlign: 'center', color: '#34d399', fontWeight: 700, cursor: 'pointer' }} onClick={() => openPalDetails(reverseSearchTerm)}>
                          {reverseSearchTerm}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ color: 'var(--text-secondary)', padding: '2rem', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', textAlign: 'center' }}>
                No breeding combinations found for "{reverseSearchTerm}".
              </div>
            )
          )}
        </div>
      )}

      {/* 3. POSSIBLE OFFSPRING SUB-TAB */}
      {breedingSubTab === 'offspring' && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
          <div className="glass-card" style={{ padding: '1rem 1.25rem', marginBottom: '0.75rem', flexShrink: 0 }}>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'end' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '0.35rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Parent Pal</label>
                <select 
                  style={{ width: '100%', padding: '0.5rem 0.75rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.88rem' }}
                  value={offspringParent} 
                  onChange={e => setOffspringParent(e.target.value)}
                >
                  <option value="">-- Select Parent Pal --</option>
                  {effectivePalOptions.map((name, idx) => (
                    <option key={idx} value={name}>{name}</option>
                  ))}
                </select>
              </div>
              <button className="btn btn-primary" onClick={handleCalculateOffspring} disabled={!offspringParent || offspringLoading} style={{ padding: '0.5rem 1.25rem', fontSize: '0.88rem' }}>
                {offspringLoading ? 'Searching...' : 'Find Offspring'}
              </button>
              {(offspringParent || offspringResults.length > 0 || offspringSearched) && (
                <button 
                  className="btn btn-secondary" 
                  onClick={() => { setOffspringParent(''); setOffspringResults([]); setOffspringSearched(false); setOffspringSearchTerm(''); }}
                  style={{ padding: '0.5rem 0.85rem', fontSize: '0.88rem' }}
                >
                  ✕ Clear
                </button>
              )}
            </div>
          </div>

          {offspringSearched && !offspringLoading && (
            offspringResults.length > 0 ? (
              <div className="glass-card table-container" style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 0, marginBottom: '1.5rem' }}>
                <table>
                  <thead>
                    <tr>
                      <th style={{ width: '50px', textAlign: 'center' }}>#</th>
                      <th style={{ width: '180px' }}>Offspring Pal</th>
                      <th>Required Other Parent ({palSourceMode === 'caught' ? 'From Caught Inventory' : 'All Game Pals'})</th>
                      <th style={{ textAlign: 'center', width: '110px' }}>Breeding Power</th>
                      <th style={{ width: '110px' }}>Elements</th>
                      <th style={{ textAlign: 'center', width: '100px' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {offspringResults.map((pal, idx) => (
                      <tr key={idx} onClick={() => openPalDetails(pal)} style={{ cursor: 'pointer' }}>
                        <td style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{idx + 1}</td>
                        <td style={{ fontWeight: 600 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                            {pal.icon_path ? (
                              <img src={pal.icon_path} alt={pal.display_name} style={{ width: '28px', height: '28px', borderRadius: '6px', objectFit: 'cover' }} onError={(e) => { e.target.style.display = 'none'; }} />
                            ) : (
                              <span style={{ fontSize: '1rem' }}>🐾</span>
                            )}
                            <span style={{ color: 'var(--accent-gold)' }}>{pal.display_name}</span>
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', alignItems: 'center' }} onClick={e => e.stopPropagation()}>
                            {pal.other_parents && pal.other_parents.length > 0 ? (
                              pal.other_parents.map((parentName, pIdx) => (
                                <span 
                                  key={pIdx} 
                                  className="badge" 
                                  style={{ 
                                    fontSize: '0.72rem', 
                                    padding: '0.12rem 0.4rem', 
                                    background: 'rgba(99, 102, 241, 0.15)', 
                                    color: '#a5b4fc', 
                                    border: '1px solid rgba(99, 102, 241, 0.3)',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                  }}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openPalDetails(parentName);
                                  }}
                                >
                                  {parentName}
                                </span>
                              ))
                            ) : (
                              <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', fontStyle: 'italic' }}>None available</span>
                            )}
                          </div>
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 600, color: 'var(--accent-gold)' }}>{pal.breeding_power}</td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.25rem' }}>
                            {pal.element_1 && <span className="badge badge-element" style={{ fontSize: '0.68rem', padding: '0.08rem 0.35rem' }}>{pal.element_1}</span>}
                            {pal.element_2 && <span className="badge badge-element" style={{ fontSize: '0.68rem', padding: '0.08rem 0.35rem' }}>{pal.element_2}</span>}
                          </div>
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <button 
                            className="btn btn-secondary" 
                            style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem', borderRadius: '6px' }}
                            onClick={(e) => {
                              e.stopPropagation();
                              openPalDetails(pal);
                            }}
                          >
                            Paldex →
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ color: 'var(--text-secondary)', padding: '2rem', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', textAlign: 'center' }}>
                No offspring combinations found for "{offspringSearchTerm}".
              </div>
            )
          )}
        </div>
      )}

      {/* 4. MULTI-STEP PATH FINDER SUB-TAB */}
      {breedingSubTab === 'path' && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'auto', gap: '1rem', paddingBottom: '2rem' }}>
          <div className="glass-card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span>Starting Breeding Pool:</span>
                    {palSourceMode === 'global' ? (
                      <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.4)' }}>
                        🌐 All Game Pals (316 species)
                      </span>
                    ) : (
                      <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.2)', color: 'var(--accent-gold)', border: '1px solid rgba(234, 179, 8, 0.4)' }}>
                        💼 My Caught Pals ({ownedSpecies.length} species)
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    (Switch mode using the top bar toggle)
                  </span>
                </div>

                {ownedPals && (
                  <div style={{ marginTop: '0.25rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.25rem', color: 'var(--text-secondary)', fontSize: '0.78rem' }}>Custom Specific Starting Species (Override)</label>
                    <input 
                      type="text" 
                      placeholder="e.g. Lamball, Cattiva, Penking" 
                      value={ownedPals} 
                      onChange={e => setOwnedPals(e.target.value)} 
                    />
                  </div>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto auto', gap: '1rem', alignItems: 'end' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.35rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Target Pal to Breed</label>
                  <select 
                    style={{ width: '100%', padding: '0.5rem 0.75rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.88rem' }}
                    value={targetPal} 
                    onChange={e => setTargetPal(e.target.value)}
                  >
                    <option value="">-- Select Target Pal --</option>
                    {effectivePalOptions.map((name, idx) => (
                      <option key={idx} value={name}>{name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.35rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                    ✨ Prioritize Target Traits / Passives (optional)
                  </label>
                  <input 
                    type="text" 
                    placeholder="e.g. Artisan, Swift, Ferocious, Legend" 
                    value={targetSkills} 
                    onChange={e => setTargetSkills(e.target.value)} 
                  />
                </div>
                <button className="btn btn-primary" onClick={handleFindPath} disabled={!targetPal || pathLoading} style={{ padding: '0.5rem 1.25rem', fontSize: '0.88rem' }}>
                  {pathLoading ? 'Finding Path...' : 'Find Path'}
                </button>
                {(targetPal || targetSkills || allBreedingPaths.length > 0 || pathError || pathSearched) && (
                  <button 
                    className="btn btn-secondary" 
                    onClick={() => { setTargetPal(''); setTargetSkills(''); setAllBreedingPaths([]); setPathSearched(false); setPathError(''); }}
                    style={{ padding: '0.5rem 0.85rem', fontSize: '0.88rem' }}
                  >
                    ✕ Clear
                  </button>
                )}
              </div>
            </div>

            {pathError && (
              <div style={{ marginTop: '1rem', color: '#f87171', padding: '0.75rem 1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)', fontSize: '0.88rem' }}>
                ⚠️ {pathError}
              </div>
            )}
          </div>

          {pathSearched && !pathLoading && allBreedingPaths.length === 0 && !pathError && (
            <div style={{ padding: '1.5rem', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '12px', border: '1px solid var(--border-color)', textAlign: 'center' }}>
              <p style={{ color: 'var(--text-secondary)', margin: 0 }}>No breeding path found to <strong>{targetPal}</strong> with available Pals.</p>
            </div>
          )}

          {pathSearched && !pathLoading && allBreedingPaths.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {allBreedingPaths.length > 1 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {allBreedingPaths.map((pObj, pIdx) => (
                    <button
                      key={pIdx}
                      className={`btn ${activePathIdx === pIdx ? 'btn-primary' : 'btn-secondary'}`}
                      style={{ fontSize: '0.82rem', padding: '0.35rem 0.85rem', borderRadius: '6px' }}
                      onClick={() => setActivePathIdx(pIdx)}
                    >
                      {pObj.title}
                    </button>
                  ))}
                </div>
              )}

              {(() => {
                const currentPathObj = allBreedingPaths[activePathIdx] || allBreedingPaths[0];
                const currentSteps = currentPathObj ? currentPathObj.steps : [];
                return (
                  <div className="glass-card" style={{ padding: '1.25rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <h4 style={{ fontWeight: 800, color: '#38bdf8', margin: 0, fontSize: '1.1rem' }}>
                        🎯 {currentPathObj.title} to breed {targetPal}:
                      </h4>
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        {currentPathObj.total_quality_score !== undefined && (
                          <span style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem', borderRadius: '6px', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.3)', fontWeight: 700 }}>
                            ⭐ Quality Score: {currentPathObj.total_quality_score > 0 ? `+${currentPathObj.total_quality_score}` : currentPathObj.total_quality_score}
                          </span>
                        )}
                        <span style={{ fontSize: '0.78rem', padding: '0.2rem 0.5rem', borderRadius: '6px', background: 'rgba(255,255,255,0.08)', color: 'var(--text-secondary)' }}>
                          {currentPathObj.difficulty}
                        </span>
                      </div>
                    </div>

                    <div className="steps-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                      {currentSteps.map((step, idx) => (
                        <div key={idx} className="step-card" style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', padding: '0.85rem 1rem', background: 'rgba(255,255,255,0.04)', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
                            <div className="step-num" style={{ background: 'var(--accent-gold)', color: '#090d16', fontWeight: 800, width: '28px', height: '28px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: '0.85rem' }}>
                              {idx + 1}
                            </div>
                            <div className="step-details" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', fontSize: '0.95rem', fontWeight: 600, flexWrap: 'wrap', flexGrow: 1 }}>
                              <span 
                                style={{ color: '#a5b4fc', display: 'inline-flex', alignItems: 'center', gap: '0.3rem', cursor: 'pointer' }}
                                onClick={() => openPalDetails(step.parent1)}
                                title="Inspect Pal in Paldex"
                              >
                                <span style={{ textDecoration: 'underline' }}>{step.parent1}</span>
                                {step.parent1_gender === 'Male' && <span style={{ color: '#60a5fa', background: 'rgba(96, 165, 250, 0.15)', padding: '0.05rem 0.35rem', borderRadius: '4px', fontSize: '0.75rem' }}>♂ Male</span>}
                                {step.parent1_gender === 'Female' && <span style={{ color: '#f472b6', background: 'rgba(244, 114, 182, 0.15)', padding: '0.05rem 0.35rem', borderRadius: '4px', fontSize: '0.75rem' }}>♀ Female</span>}
                              </span>
                              <span style={{ color: 'var(--text-secondary)' }}>+</span>
                              <span 
                                style={{ color: '#a5b4fc', display: 'inline-flex', alignItems: 'center', gap: '0.3rem', cursor: 'pointer' }}
                                onClick={() => openPalDetails(step.parent2)}
                                title="Inspect Pal in Paldex"
                              >
                                <span style={{ textDecoration: 'underline' }}>{step.parent2}</span>
                                {step.parent2_gender === 'Male' && <span style={{ color: '#60a5fa', background: 'rgba(96, 165, 250, 0.15)', padding: '0.05rem 0.35rem', borderRadius: '4px', fontSize: '0.75rem' }}>♂ Male</span>}
                                {step.parent2_gender === 'Female' && <span style={{ color: '#f472b6', background: 'rgba(244, 114, 182, 0.15)', padding: '0.05rem 0.35rem', borderRadius: '4px', fontSize: '0.75rem' }}>♀ Female</span>}
                              </span>
                              <span style={{ color: 'var(--text-secondary)' }}>➔</span>
                              <span 
                                style={{ color: '#34d399', fontWeight: 800, cursor: 'pointer', textDecoration: 'underline' }}
                                onClick={() => openPalDetails(step.child)}
                                title="Inspect Pal in Paldex"
                              >
                                {step.child}
                              </span>
                            </div>
                          </div>

                          {(step.parent1_score !== undefined || step.parent2_score !== undefined) && (
                            <div style={{ marginLeft: '2.5rem', background: 'rgba(0,0,0,0.25)', padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                              <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--accent-gold)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                <span>⭐ Recommended Save Parent Candidates (Click to Inspect Full Bio & Passives):</span>
                              </div>
                              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.82rem' }}>
                                <PalInstanceTooltip instance={{
                                  display_name: step.parent1,
                                  gender: step.parent1_gender,
                                  level: step.parent1_level,
                                  rank: step.parent1_rank,
                                  score: step.parent1_score,
                                  passives: step.parent1_passives,
                                  matched_passives: step.parent1_matched_passives,
                                  location: step.parent1_location,
                                  location_details: step.parent1_location_details,
                                  ivs: step.parent1_ivs,
                                }}>
                                  <div 
                                    style={{ background: 'rgba(255,255,255,0.02)', padding: '0.4rem 0.6rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)', cursor: 'pointer', width: '100%' }}
                                    onClick={() => openPalDetails({
                                      display_name: step.parent1,
                                      gender: step.parent1_gender,
                                      level: step.parent1_level,
                                      rank: step.parent1_rank,
                                      passives: step.parent1_passives,
                                      location: step.parent1_location,
                                      ivs: step.parent1_ivs,
                                    })}
                                  >
                                    <div style={{ fontWeight: 600, color: '#a5b4fc', marginBottom: '0.2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.3rem' }}>
                                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                                        <span>{step.parent1}</span>
                                        {step.parent1_level && <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>Lv.{step.parent1_level}</span>}
                                        {step.parent1_rank > 0 && <span style={{ fontSize: '0.7rem' }}>{'⭐'.repeat(step.parent1_rank)}</span>}
                                      </div>
                                      {step.parent1_score !== undefined && (
                                        <span className={`badge ${step.parent1_score >= 0 ? 'badge-score-positive' : 'badge-score-negative'}`} style={{ fontSize: '0.68rem', padding: '0.05rem 0.3rem' }}>
                                          Score: {step.parent1_score > 0 ? `+${step.parent1_score}` : step.parent1_score}
                                        </span>
                                      )}
                                    </div>
                                    <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
                                      📍 {step.parent1_location_details?.base_camp_name ? `Base: ${step.parent1_location_details.base_camp_name}` : (step.parent1_location || 'Palbox')}
                                    </div>
                                    {step.parent1_passives && step.parent1_passives.length > 0 ? (
                                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem', alignItems: 'center' }}>
                                        {step.parent1_passives.map((pName, pIdx) => {
                                          const isMatched = step.parent1_matched_passives && step.parent1_matched_passives.includes(pName);
                                          return (
                                            <PassiveBadge key={pIdx} skill={pName} isMatched={isMatched} size="sm" />
                                          );
                                        })}
                                      </div>
                                    ) : (
                                      <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '0.75rem' }}>No passives recorded</span>
                                    )}
                                  </div>
                                </PalInstanceTooltip>

                                <PalInstanceTooltip instance={{
                                  display_name: step.parent2,
                                  gender: step.parent2_gender,
                                  level: step.parent2_level,
                                  rank: step.parent2_rank,
                                  score: step.parent2_score,
                                  passives: step.parent2_passives,
                                  matched_passives: step.parent2_matched_passives,
                                  location: step.parent2_location,
                                  location_details: step.parent2_location_details,
                                  ivs: step.parent2_ivs,
                                }}>
                                  <div 
                                    style={{ background: 'rgba(255,255,255,0.02)', padding: '0.4rem 0.6rem', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)', cursor: 'pointer', width: '100%' }}
                                    onClick={() => openPalDetails({
                                      display_name: step.parent2,
                                      gender: step.parent2_gender,
                                      level: step.parent2_level,
                                      rank: step.parent2_rank,
                                      passives: step.parent2_passives,
                                      location: step.parent2_location,
                                      ivs: step.parent2_ivs,
                                    })}
                                  >
                                    <div style={{ fontWeight: 600, color: '#a5b4fc', marginBottom: '0.2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.3rem' }}>
                                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                                        <span>{step.parent2}</span>
                                        {step.parent2_level && <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>Lv.{step.parent2_level}</span>}
                                        {step.parent2_rank > 0 && <span style={{ fontSize: '0.7rem' }}>{'⭐'.repeat(step.parent2_rank)}</span>}
                                      </div>
                                      {step.parent2_score !== undefined && (
                                        <span className={`badge ${step.parent2_score >= 0 ? 'badge-score-positive' : 'badge-score-negative'}`} style={{ fontSize: '0.68rem', padding: '0.05rem 0.3rem' }}>
                                          Score: {step.parent2_score > 0 ? `+${step.parent2_score}` : step.parent2_score}
                                        </span>
                                      )}
                                    </div>
                                    <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
                                      📍 {step.parent2_location_details?.base_camp_name ? `Base: ${step.parent2_location_details.base_camp_name}` : (step.parent2_location || 'Palbox')}
                                    </div>
                                    {step.parent2_passives && step.parent2_passives.length > 0 ? (
                                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem', alignItems: 'center' }}>
                                        {step.parent2_passives.map((pName, pIdx) => {
                                          const isMatched = step.parent2_matched_passives && step.parent2_matched_passives.includes(pName);
                                          return (
                                            <PassiveBadge key={pIdx} skill={pName} isMatched={isMatched} size="sm" />
                                          );
                                        })}
                                      </div>
                                    ) : (
                                      <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '0.75rem' }}>No passives recorded</span>
                                    )}
                                  </div>
                                </PalInstanceTooltip>
                              </div>
                            </div>
                          )}

                          {step.gender_note && (
                            <div style={{ marginLeft: '2.5rem', fontSize: '0.78rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                              <span>🎲</span>
                              <span><strong>Hatch Odds for {step.child}:</strong> {step.gender_note}</span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
        </div>
      )}

      {/* 5. UNCAUGHT SPECIES FINDER SUB-TAB */}
      {breedingSubTab === 'uncaught' && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'auto', gap: '0.85rem' }}>
          <div className="glass-card" style={{ padding: '1rem 1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span>✨ Uncaught Species Breeding Opportunities</span>
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', margin: '0.2rem 0 0 0' }}>
                {palSourceMode === 'caught' 
                  ? 'Pal species NOT yet in your save file that you can breed immediately using your current caught roster.'
                  : 'All uncaught Pal species with valid parent combinations across all game Pals.'}
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <input
                type="text"
                placeholder="Filter uncaught species..."
                value={uncaughtSearchTerm}
                onChange={e => setUncaughtSearchTerm(e.target.value)}
                style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem', width: '220px', borderRadius: '6px' }}
              />
              <button
                className="btn btn-secondary"
                onClick={() => fetchUncaughtOpportunities()}
                style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
              >
                🔄 Refresh
              </button>
            </div>
          </div>

          {uncaughtLoading && (
            <div className="glass-card" style={{ textAlign: 'center', padding: '3rem' }}>
              <p style={{ color: 'var(--text-secondary)' }}>Analyzing {palSourceMode === 'caught' ? 'current roster' : 'all game pals'} and finding breedable uncaught species...</p>
            </div>
          )}

          {!uncaughtLoading && (
            (() => {
              const filtered = uncaughtOpportunities.filter(item => 
                !uncaughtSearchTerm || item.species.toLowerCase().includes(uncaughtSearchTerm.toLowerCase()) ||
                (item.element_1 && item.element_1.toLowerCase().includes(uncaughtSearchTerm.toLowerCase())) ||
                (item.element_2 && item.element_2.toLowerCase().includes(uncaughtSearchTerm.toLowerCase()))
              );

              if (filtered.length === 0) {
                return (
                  <div className="glass-card" style={{ textAlign: 'center', padding: '3rem' }}>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '1rem' }}>
                      {uncaughtSearchTerm ? 'No uncaught species match your filter.' : (palSourceMode === 'caught' ? 'No breedable uncaught species found from your current caught roster.' : 'No uncaught species found.')}
                    </p>
                  </div>
                );
              }

              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', paddingBottom: '2rem' }}>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                    Found <strong style={{ color: 'var(--accent-gold)' }}>{filtered.length}</strong> breedable uncaught species ({palSourceMode === 'caught' ? 'Using Caught Pals' : 'All Game Pals'}):
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                    {filtered.map(item => {
                      const isExpanded = expandedUncaughtSpecies === item.species;
                      const samplePair = item.pairs && item.pairs.length > 0 ? item.pairs[0] : null;

                      let sortedPairs = item.pairs ? [...item.pairs] : [];
                      if (isExpanded && sortedPairs.length > 0) {
                        sortedPairs.sort((a, b) => {
                          const valA = (a[uncaughtTableSortCol] || '').toLowerCase();
                          const valB = (b[uncaughtTableSortCol] || '').toLowerCase();
                          if (valA < valB) return uncaughtTableSortDesc ? 1 : -1;
                          if (valA > valB) return uncaughtTableSortDesc ? -1 : 1;
                          return 0;
                        });
                      }

                      return (
                        <div 
                          key={item.species} 
                          className="glass-card" 
                          style={{ 
                            padding: '0.75rem 1rem', 
                            display: 'flex', 
                            flexDirection: 'column', 
                            gap: isExpanded ? '0.75rem' : '0', 
                            border: isExpanded ? '1px solid rgba(56, 189, 248, 0.4)' : '1px solid rgba(255,255,255,0.08)',
                            transition: 'all 0.2s ease',
                          }}
                        >
                          <div 
                            style={{ 
                              display: 'flex', 
                              alignItems: 'center', 
                              justifyContent: 'space-between', 
                              flexWrap: 'wrap', 
                              gap: '0.75rem',
                            }}
                          >
                            <div 
                              style={{ 
                                display: 'flex', 
                                alignItems: 'center', 
                                gap: '0.75rem', 
                                minWidth: '220px',
                                cursor: 'pointer',
                                padding: '0.2rem 0.4rem',
                                borderRadius: '8px',
                              }}
                              title="Click to view full Master Paldex stats, skills, and drops"
                              onClick={(e) => {
                                e.stopPropagation();
                                openPalDetails(item.species);
                              }}
                            >
                              {item.icon_path ? (
                                <img src={item.icon_path} alt={item.species} style={{ width: '38px', height: '38px', borderRadius: '8px', objectFit: 'cover' }} onError={(e) => { e.target.style.display = 'none'; }} />
                              ) : (
                                <div style={{ width: '38px', height: '38px', borderRadius: '8px', background: 'var(--primary-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>
                                  {item.species[0]}
                                </div>
                              )}
                              <div>
                                <div style={{ fontWeight: 800, fontSize: '0.95rem', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                                  <span>{item.species}</span>
                                  <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 400 }}>🔍</span>
                                </div>
                                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                                  #{item.paldex_number ? String(item.paldex_number).padStart(3, '0') : '???'} • {item.element_1}{item.element_2 ? ` / ${item.element_2}` : ''}
                                </div>
                              </div>
                            </div>

                            {samplePair && (
                              <div 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setParent1(samplePair.parent1);
                                  setParent2(samplePair.parent2);
                                  setBreedingSubTab('calculator');
                                }}
                                title="Click to load sample pair into Direct Calculator"
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '0.35rem',
                                  background: 'rgba(255,255,255,0.04)',
                                  border: '1px solid rgba(255,255,255,0.1)',
                                  padding: '0.3rem 0.65rem',
                                  borderRadius: '6px',
                                  fontSize: '0.76rem',
                                  cursor: 'pointer',
                                }}
                              >
                                <span style={{ color: 'var(--text-secondary)', fontSize: '0.7rem' }}>Sample Pair:</span>
                                <span style={{ color: '#a5b4fc', fontWeight: 600 }}>{samplePair.parent1}</span>
                                <span style={{ color: 'var(--text-secondary)' }}>+</span>
                                <span style={{ color: '#a5b4fc', fontWeight: 600 }}>{samplePair.parent2}</span>
                              </div>
                            )}

                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                              <span className="badge badge-matched" style={{ fontSize: '0.74rem', padding: '0.25rem 0.6rem', fontWeight: 700 }}>
                                {item.possible_pairs_count} {palSourceMode === 'caught' ? 'Caught' : 'Total'} Pair{item.possible_pairs_count === 1 ? '' : 's'}
                              </span>
                              <button 
                                className="btn btn-secondary" 
                                style={{ 
                                  padding: '0.25rem 0.6rem', 
                                  fontSize: '0.75rem', 
                                  display: 'inline-flex', 
                                  alignItems: 'center', 
                                  gap: '0.3rem',
                                  background: isExpanded ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255,255,255,0.05)',
                                  borderColor: isExpanded ? 'rgba(56, 189, 248, 0.5)' : 'rgba(255,255,255,0.1)'
                                }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setExpandedUncaughtSpecies(isExpanded ? null : item.species);
                                }}
                              >
                                {isExpanded ? '▴ Hide Table' : `▾ View All ${item.possible_pairs_count} Pairs`}
                              </button>
                            </div>
                          </div>

                          {isExpanded && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                <span>All <strong>{item.possible_pairs_count}</strong> breeding parent combinations for <strong style={{ color: '#38bdf8' }}>{item.species}</strong>:</span>
                                <span style={{ fontSize: '0.7rem', color: 'var(--accent-gold)' }}>Click column headers to sort • Click any row or Load button to test</span>
                              </div>
                              <div style={{ 
                                maxHeight: '300px', 
                                overflowY: 'auto', 
                                borderRadius: '8px', 
                                border: '1px solid rgba(255,255,255,0.1)',
                                background: 'rgba(10, 14, 26, 0.85)',
                              }}>
                                <table className="pals-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.8rem' }}>
                                  <thead style={{ position: 'sticky', top: 0, zIndex: 10, background: '#111827', boxShadow: '0 2px 8px rgba(0,0,0,0.6)' }}>
                                    <tr>
                                      <th 
                                        onClick={() => {
                                          if (uncaughtTableSortCol === 'parent1') setUncaughtTableSortDesc(!uncaughtTableSortDesc);
                                          else { setUncaughtTableSortCol('parent1'); setUncaughtTableSortDesc(false); }
                                        }}
                                        style={{ padding: '0.6rem 1rem', cursor: 'pointer', width: '45%', userSelect: 'none' }}
                                      >
                                        Parent 1 {uncaughtTableSortCol === 'parent1' ? (uncaughtTableSortDesc ? ' ▼' : ' ▲') : ' ↕'}
                                      </th>
                                      <th 
                                        onClick={() => {
                                          if (uncaughtTableSortCol === 'parent2') setUncaughtTableSortDesc(!uncaughtTableSortDesc);
                                          else { setUncaughtTableSortCol('parent2'); setUncaughtTableSortDesc(false); }
                                        }}
                                        style={{ padding: '0.6rem 1rem', cursor: 'pointer', width: '45%', userSelect: 'none' }}
                                      >
                                        Parent 2 {uncaughtTableSortCol === 'parent2' ? (uncaughtTableSortDesc ? ' ▼' : ' ▲') : ' ↕'}
                                      </th>
                                      <th style={{ padding: '0.6rem 1rem', width: '10%', textAlign: 'center' }}>
                                        Action
                                      </th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {sortedPairs.map((p, pIdx) => (
                                      <tr 
                                        key={pIdx} 
                                        style={{ cursor: 'pointer', transition: 'background 0.15s' }}
                                        onClick={() => {
                                          setParent1(p.parent1);
                                          setParent2(p.parent2);
                                          setBreedingSubTab('calculator');
                                        }}
                                        title="Click to load pair into Direct Pair Calculator"
                                      >
                                        <td style={{ padding: '0.55rem 1rem', fontWeight: 600, color: '#e2e8f0' }}>
                                          <span 
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              openPalDetails(p.parent1);
                                            }}
                                            style={{ color: 'var(--accent-gold)', textDecoration: 'underline' }}
                                          >
                                            {p.parent1}
                                          </span>
                                        </td>
                                        <td style={{ padding: '0.55rem 1rem', fontWeight: 600, color: '#e2e8f0' }}>
                                          <span 
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              openPalDetails(p.parent2);
                                            }}
                                            style={{ color: 'var(--accent-gold)', textDecoration: 'underline' }}
                                          >
                                            {p.parent2}
                                          </span>
                                        </td>
                                        <td style={{ padding: '0.4rem 1rem', textAlign: 'center' }}>
                                          <button 
                                            className="btn btn-secondary" 
                                            style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem' }}
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              setParent1(p.parent1);
                                              setParent2(p.parent2);
                                              setBreedingSubTab('calculator');
                                            }}
                                          >
                                            ⚡ Load
                                          </button>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })()
          )}
        </div>
      )}
    </div>
  );
}

export default BreedingCenterView;
