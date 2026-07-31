import React, { useState, useEffect } from 'react'

function BaseCampCard({ base }) {
  const [workerSortCol, setWorkerSortCol] = useState('level');
  const [workerSortDesc, setWorkerSortDesc] = useState(true);
  const [workerSearch, setWorkerSearch] = useState('');

  const [structSortCol, setStructSortCol] = useState('count');
  const [structSortDesc, setStructSortDesc] = useState(true);
  const [structSearch, setStructSearch] = useState('');

  const handleWorkerSort = (col) => {
    if (workerSortCol === col) setWorkerSortDesc(!workerSortDesc);
    else { setWorkerSortCol(col); setWorkerSortDesc(true); }
  };

  const handleStructSort = (col) => {
    if (structSortCol === col) setStructSortDesc(!structSortDesc);
    else { setStructSortCol(col); setStructSortDesc(true); }
  };

  const filteredWorkers = base.workers.filter(w => w.display_name.toLowerCase().includes(workerSearch.toLowerCase()));
  const sortedWorkers = [...filteredWorkers].sort((a, b) => {
    let valA = a[workerSortCol];
    let valB = b[workerSortCol];
    if (valA < valB) return workerSortDesc ? 1 : -1;
    if (valA > valB) return workerSortDesc ? -1 : 1;
    return 0;
  });

  const filteredStructs = base.structures.filter(s => (s.display_name || s.structure_name).toLowerCase().includes(structSearch.toLowerCase()));
  const sortedStructs = [...filteredStructs].sort((a, b) => {
    let nameA = a.display_name || a.structure_name;
    let nameB = b.display_name || b.structure_name;
    let valA = structSortCol === 'name' ? nameA : a[structSortCol];
    let valB = structSortCol === 'name' ? nameB : b[structSortCol];
    if (valA < valB) return structSortDesc ? 1 : -1;
    if (valA > valB) return structSortDesc ? -1 : 1;
    return 0;
  });

  return (
    <div className="glass-card">
      <h2 style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem', fontWeight: 800 }}>
        🏰 {base.name}
      </h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        
        {/* Worker summary */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ color: 'var(--text-secondary)' }}>Workers ({base.workers.length})</h3>
            <input type="text" placeholder="Search pals..." value={workerSearch} onChange={e => setWorkerSearch(e.target.value)} style={{ padding: '0.4rem 0.8rem', width: '150px' }} />
          </div>
          <div className="glass-card table-container" style={{ padding: '0', background: 'rgba(0,0,0,0.2)' }}>
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
                    <td style={{ fontWeight: 600 }}>{w.display_name}</td>
                    <td>Lv. {w.level}</td>
                    <td>{w.gender}</td>
                    <td>{w.rank} ⭐</td>
                    <td>
                      <div className="badge-container">
                        {w.passives && w.passives.map(pass => (
                          <span key={pass.id} className="badge badge-element" title={pass.description}>{pass.name}</span>
                        ))}
                        {(!w.passives || w.passives.length === 0) && <span style={{ color: 'var(--text-secondary)' }}>None</span>}
                      </div>
                    </td>
                  </tr>
                ))}
                {sortedWorkers.length === 0 && (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>No workers match search.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        
        {/* Structure inventories */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ color: 'var(--text-secondary)' }}>Camp Structures</h3>
            <input type="text" placeholder="Search structures..." value={structSearch} onChange={e => setStructSearch(e.target.value)} style={{ padding: '0.4rem 0.8rem', width: '150px' }} />
          </div>
          <div className="glass-card table-container" style={{ padding: '0', background: 'rgba(0,0,0,0.2)' }}>
            <table>
              <thead>
                <tr>
                  <th onClick={() => handleStructSort('count')} style={{cursor:'pointer'}}>Count{structSortCol === 'count' ? (structSortDesc ? ' ▼' : ' ▲') : ''}</th>
                  <th onClick={() => handleStructSort('name')} style={{cursor:'pointer'}}>Structure Name{structSortCol === 'name' ? (structSortDesc ? ' ▼' : ' ▲') : ''}</th>
                </tr>
              </thead>
              <tbody>
                {sortedStructs.map((s, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 700, color: 'var(--accent-gold)' }}>{s.count}x</td>
                    <td>{s.display_name || s.structure_name}</td>
                  </tr>
                ))}
                {sortedStructs.length === 0 && (
                  <tr>
                    <td colSpan="2" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>No structures match search.</td>
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

function App() {
  const [activeTab, setActiveTab] = useState('paldex')
  const [savePath, setSavePath] = useState('')
  const [saveLoaded, setSaveLoaded] = useState(false)
  const [loadedPath, setLoadedPath] = useState('')
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  // Pals Tab States
  const [pals, setPals] = useState([])
  const [elementFilter, setElementFilter] = useState('')
  const [sizeFilter, setSizeFilter] = useState('')
  const [nocturnalFilter, setNocturnalFilter] = useState('')
  const [suitabilityFilter, setSuitabilityFilter] = useState('')

  // Save Game Tab States
  const [instances, setInstances] = useState([])
  const [locFilter, setLocFilter] = useState('')
  const [specFilter, setSpecFilter] = useState('')
  const [genderFilter, setGenderFilter] = useState('')
  const [minLvlFilter, setMinLvlFilter] = useState('')
  const [passiveFilter, setPassiveFilter] = useState('')
  const [sortCol, setSortCol] = useState('level')
  const [sortDesc, setSortDesc] = useState(true)

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDesc(!sortDesc)
    } else {
      setSortCol(col)
      setSortDesc(true)
    }
  }

  const sortedInstances = [...instances].sort((a, b) => {
    let valA = a[sortCol]
    let valB = b[sortCol]
    if (valA < valB) return sortDesc ? 1 : -1
    if (valA > valB) return sortDesc ? -1 : 1
    return 0
  })
  // Bases Tab States
  const [bases, setBases] = useState([])

  // Breeding Tab States
  const [parent1, setParent1] = useState('')
  const [parent2, setParent2] = useState('')
  const [breedResult, setBreedResult] = useState(null)
  
  const [reverseChild, setReverseChild] = useState('')
  const [parentCombos, setParentCombos] = useState([])

  const [ownedPals, setOwnedPals] = useState('')
  const [targetPal, setTargetPal] = useState('')
  const [breedingPath, setBreedingPath] = useState([])

  // Fetch Pals on startup
  useEffect(() => {
    fetchPals()
  }, [elementFilter, sizeFilter, nocturnalFilter, suitabilityFilter])

  // Check save status on mount
  useEffect(() => {
    fetch('/api/save/status')
      .then(res => res.json())
      .then(data => {
        if (data.loaded) {
          setSaveLoaded(true)
          setLoadedPath(data.path || 'Previous Session')
        }
      })
      .catch(err => console.error("Error checking save status:", err))
  }, [])

  const fetchPals = async () => {
    try {
      let url = '/api/pals?'
      if (elementFilter) url += `element=${elementFilter}&`
      if (sizeFilter) url += `size=${sizeFilter}&`
      if (nocturnalFilter) url += `nocturnal=${nocturnalFilter === 'true'}&`
      if (suitabilityFilter) url += `suitability=${suitabilityFilter}&`
      
      const res = await fetch(url)
      const data = await res.json()
      setPals(data)
    } catch (e) {
      console.error("Error fetching pals", e)
    }
  }

  // Handle Loading save
  const handleLoadSave = async () => {
    setLoading(true)
    setErrorMsg('')
    setSuccessMsg('')
    try {
      const res = await fetch('/api/save/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ save_path: savePath || null })
      })
      const data = await res.json()
      if (res.ok) {
        setSaveLoaded(true)
        setLoadedPath(data.path)
        setSuccessMsg(data.message)
        fetchInstances()
        fetchBases()
      } else {
        setErrorMsg(data.detail || "Failed to load save file.")
      }
    } catch (e) {
      setErrorMsg("Error making request to backend.")
    } finally {
      setLoading(false)
    }
  }

  // Fetch Dynamic instances
  const fetchInstances = async () => {
    try {
      let url = '/api/save/instances?'
      if (locFilter) url += `location=${locFilter}&`
      if (specFilter) url += `species=${specFilter}&`
      if (genderFilter) url += `gender=${genderFilter}&`
      if (minLvlFilter) url += `min_level=${minLvlFilter}&`
      if (passiveFilter) url += `passive=${passiveFilter}&`

      const res = await fetch(url)
      const data = await res.json()
      setInstances(data)
    } catch (e) {
      console.error("Error fetching instances", e)
    }
  }

  useEffect(() => {
    if (saveLoaded) {
      fetchInstances()
    }
  }, [locFilter, specFilter, genderFilter, minLvlFilter, passiveFilter, saveLoaded])

  // Fetch Bases
  const fetchBases = async () => {
    try {
      const res = await fetch('/api/bases')
      const data = await res.json()
      setBases(data)
    } catch (e) {
      console.error("Error fetching bases", e)
    }
  }

  // Calculate Breed Result
  const handleCalculateBreed = async () => {
    if (!parent1 || !parent2) return
    try {
      const res = await fetch(`/api/breeding/result?parent1=${parent1}&parent2=${parent2}`)
      const data = await res.json()
      if (res.ok) {
        setBreedResult(data)
      } else {
        setBreedResult(null)
      }
    } catch (e) {
      console.error("Error calculating breeding result", e)
    }
  }

  // Calculate Reverse Parents
  const handleCalculateReverse = async () => {
    if (!reverseChild) return
    try {
      const res = await fetch(`/api/breeding/parents?child=${reverseChild}`)
      const data = await res.json()
      setParentCombos(data)
    } catch (e) {
      console.error("Error finding parents", e)
    }
  }

  // Find Breed Path
  const handleFindPath = async () => {
    if (!ownedPals || !targetPal) return
    try {
      const res = await fetch(`/api/breeding/path?owned=${ownedPals}&target=${targetPal}`)
      const data = await res.json()
      setBreedingPath(data)
    } catch (e) {
      console.error("Error finding breeding path", e)
    }
  }

  return (
    <div className="dashboard-container">
      {/* Sidebar navigation */}
      <aside className="sidebar">
        <div className="logo-area">
          <div className="logo-icon">P</div>
          <div className="logo-text">Palopedix</div>
        </div>
        <nav className="nav-links">
          <div 
            className={`nav-item ${activeTab === 'paldex' ? 'active' : ''}`}
            onClick={() => setActiveTab('paldex')}
          >
            📚 Static Paldex
          </div>
          <div 
            className={`nav-item ${activeTab === 'save_game' ? 'active' : ''}`}
            onClick={() => setActiveTab('save_game')}
          >
            💾 Save Game Viewer
          </div>
          <div 
            className={`nav-item ${activeTab === 'bases' ? 'active' : ''}`}
            onClick={() => setActiveTab('bases')}
          >
            🏰 Base Camps
          </div>
          <div 
            className={`nav-item ${activeTab === 'breeding' ? 'active' : ''}`}
            onClick={() => setActiveTab('breeding')}
          >
            🐣 Breeding Center
          </div>
        </nav>
      </aside>

      {/* Main Panel */}
      <main className="main-content">
        <header>
          <h1>{
            activeTab === 'paldex' ? 'Static Paldex' :
            activeTab === 'save_game' ? 'Save Game Explorer' :
            activeTab === 'bases' ? 'Base Camp Overview' : 'Breeding Center'
          }</h1>
          <p>{
            activeTab === 'paldex' ? 'Browse all Pal species, stats, elements, and work capabilities.' :
            activeTab === 'save_game' ? 'View and filter Pals currently in your party, Palbox, or bases.' :
            activeTab === 'bases' ? 'Audit placed infrastructure and active base camp workers.' :
            'Calculate offspring, reverse lookups, or find optimal breeding paths.'
          }</p>
        </header>

        {/* 📚 Paldex Tab */}
        {activeTab === 'paldex' && (
          <div>
            <div className="filter-bar glass-card">
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Element</label>
                <select value={elementFilter} onChange={e => setElementFilter(e.target.value)}>
                  <option value="">All Elements</option>
                  <option value="Neutral">Neutral</option>
                  <option value="Fire">Fire</option>
                  <option value="Water">Water</option>
                  <option value="Grass">Grass</option>
                  <option value="Electric">Electric</option>
                  <option value="Ice">Ice</option>
                  <option value="Ground">Ground</option>
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
                  <option value="kindling">Kindling</option>
                  <option value="watering">Watering</option>
                  <option value="planting">Planting</option>
                  <option value="generating_electricity">Electricity Generation</option>
                  <option value="handiwork">Handiwork</option>
                  <option value="gathering">Gathering</option>
                  <option value="lumbering">Lumbering</option>
                  <option value="mining">Mining</option>
                  <option value="medicine_production">Medicine Production</option>
                  <option value="cooling">Cooling</option>
                  <option value="transporting">Transporting</option>
                  <option value="farming">Farming</option>
                </select>
              </div>
            </div>

            <div className="pals-grid">
              {pals.map(p => (
                <div key={p.internal_name} className="glass-card pal-card">
                  <div className="pal-card-header">
                    <span className="pal-number">#{String(p.paldex_number).padStart(3, '0')}</span>
                    <div className="badge-container">
                      {p.element_1 && <span className="badge badge-element">{p.element_1}</span>}
                      {p.element_2 && <span className="badge badge-element">{p.element_2}</span>}
                    </div>
                  </div>
                  <h3 className="pal-name">{p.display_name}</h3>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                    <p>Size: {p.size}</p>
                    <p>Nocturnal: {p.nocturnal ? 'Yes' : 'No'}</p>
                  </div>
                  <div className="pal-card-footer">
                    <span>Power: {p.breeding_power}</span>
                    <span>Food: 🍖 {p.food_requirement}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 💾 Save Game Explorer Tab */}
        {activeTab === 'save_game' && (
          <div>
            {/* Load Save Section */}
            <div className="glass-card" style={{ marginBottom: '2.5rem' }}>
              <h2 style={{ marginBottom: '1rem', fontWeight: 700 }}>Load Save File (Level.sav)</h2>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <input 
                  type="text" 
                  placeholder="Leave empty to auto-discover local save game path..." 
                  value={savePath} 
                  onChange={e => setSavePath(e.target.value)} 
                />
                <button className="btn btn-primary" onClick={handleLoadSave} disabled={loading}>
                  {loading ? 'Parsing...' : 'Load & Parse'}
                </button>
              </div>
              {errorMsg && <p style={{ color: 'var(--accent-red)', marginTop: '1rem', fontWeight: 500 }}>⚠️ {errorMsg}</p>}
              {successMsg && <p style={{ color: 'var(--accent-green)', marginTop: '1rem', fontWeight: 500 }}>✅ {successMsg}</p>}
              {saveLoaded && <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem', fontSize: '0.875rem' }}>Active save path: {loadedPath}</p>}
            </div>

            {saveLoaded ? (
              <div>
                <div className="filter-bar glass-card" style={{ marginBottom: '2rem' }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Location</label>
                    <select value={locFilter} onChange={e => setLocFilter(e.target.value)}>
                      <option value="">All Locations</option>
                      <option value="party">Player Party</option>
                      <option value="palbox">Palbox Storage</option>
                      <option value="base">Base Camp Workers</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Species</label>
                    <input type="text" placeholder="Filter by species..." value={specFilter} onChange={e => setSpecFilter(e.target.value)} />
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Gender</label>
                    <select value={genderFilter} onChange={e => setGenderFilter(e.target.value)}>
                      <option value="">All Genders</option>
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Min Level</label>
                    <input type="text" placeholder="Min level..." value={minLvlFilter} onChange={e => setMinLvlFilter(e.target.value)} />
                  </div>
                </div>

                <div className="glass-card table-container">
                  <table>
                    <thead>
                      <tr>
                        <th onClick={() => handleSort('display_name')} style={{cursor:'pointer'}}>Species{sortCol === 'display_name' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                        <th onClick={() => handleSort('level')} style={{cursor:'pointer'}}>Level{sortCol === 'level' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                        <th onClick={() => handleSort('gender')} style={{cursor:'pointer'}}>Gender{sortCol === 'gender' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                        <th onClick={() => handleSort('rank')} style={{cursor:'pointer'}}>Rank{sortCol === 'rank' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                        <th>IVs (HP/Melee/Defense)</th>
                        <th onClick={() => handleSort('location')} style={{cursor:'pointer'}}>Location{sortCol === 'location' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                        <th>Passives</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedInstances.map((pi, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 600 }}>{pi.display_name}</td>
                          <td>Lv. {pi.level}</td>
                          <td>{pi.gender}</td>
                          <td>{pi.rank} ⭐</td>
                          <td>{pi.iv_hp} / {pi.iv_melee} / {pi.iv_defense}</td>
                          <td>{pi.location.toUpperCase()} {pi.location_details_base_camp_name && `(${pi.location_details_base_camp_name})`}</td>
                          <td>
                            <div className="badge-container">
                              {pi.passives.map(pass => (
                                <span key={pass.id} className="badge badge-element" title={pass.description}>
                                  {pass.name}
                                </span>
                              ))}
                              {pi.passives.length === 0 && <span style={{ color: 'var(--text-secondary)' }}>None</span>}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="glass-card" style={{ textAlign: 'center', padding: '4rem' }}>
                <p style={{ color: 'var(--text-secondary)', fontSize: '1.25rem' }}>No save file loaded. Please click "Load & Parse" to view save game details.</p>
              </div>
            )}
          </div>
        )}

        {/* 🏰 Base Camps Tab */}
        {activeTab === 'bases' && (
          <div>
            {!saveLoaded ? (
              <div className="glass-card" style={{ textAlign: 'center', padding: '4rem' }}>
                <p style={{ color: 'var(--text-secondary)', fontSize: '1.25rem' }}>No save file loaded. Please load a save file in the Save Game tab first.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                {bases.map(base => (
                  <BaseCampCard key={base.base_camp_id} base={base} />
                ))}
                {bases.length === 0 && <p style={{ color: 'var(--text-secondary)' }}>No base camps found in save file.</p>}
              </div>
            )}
          </div>
        )}

        {/* 🐣 Breeding Center Tab */}
        {activeTab === 'breeding' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>
            {/* 1. Calculator Card */}
            <div className="glass-card">
              <h2 style={{ marginBottom: '1.5rem', fontWeight: 800 }}>🐣 Breeding Calculator</h2>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '1.5rem', alignItems: 'end' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Parent 1</label>
                  <input type="text" placeholder="e.g. Relaxaurus" value={parent1} onChange={e => setParent1(e.target.value)} />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Parent 2</label>
                  <input type="text" placeholder="e.g. Sparkit" value={parent2} onChange={e => setParent2(e.target.value)} />
                </div>
                <button className="btn btn-primary" onClick={handleCalculateBreed}>Calculate</button>
              </div>

              {breedResult && (
                <div className="glass-card" style={{ marginTop: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(99, 102, 241, 0.15)', borderColor: 'var(--border-color-hover)' }}>
                  <div>
                    <h3 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Child: {breedResult.display_name}</h3>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>Breeding Power: {breedResult.breeding_power}</p>
                  </div>
                  <div className="badge-container">
                    {breedResult.element_1 && <span className="badge badge-element">{breedResult.element_1}</span>}
                    {breedResult.element_2 && <span className="badge badge-element">{breedResult.element_2}</span>}
                  </div>
                </div>
              )}
            </div>

            {/* 2. Reverse Lookup Card */}
            <div className="glass-card">
              <h2 style={{ marginBottom: '1.5rem', fontWeight: 800 }}>🔍 Reverse Breeding Lookup</h2>
              <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'end', marginBottom: '1.5rem' }}>
                <div style={{ flexGrow: 1 }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Target Child</label>
                  <input type="text" placeholder="e.g. Relaxaurus Lux" value={reverseChild} onChange={e => setReverseChild(e.target.value)} />
                </div>
                <button className="btn btn-primary" onClick={handleCalculateReverse}>Find Combinations</button>
              </div>

              {parentCombos.length > 0 && (
                <div className="table-container" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Parent 1</th>
                        <th>Parent 2</th>
                      </tr>
                    </thead>
                    <tbody>
                      {parentCombos.map((combo, idx) => (
                        <tr key={idx}>
                          <td>{combo[0]}</td>
                          <td>{combo[1]}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* 3. Breeding Path Finder Card */}
            <div className="glass-card">
              <h2 style={{ marginBottom: '1.5rem', fontWeight: 800 }}>🧬 BFS Breeding Path Finder</h2>
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr auto', gap: '1.5rem', alignItems: 'end', marginBottom: '1.5rem' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Owned Pal Species (comma-separated)</label>
                  <input type="text" placeholder="e.g. Lamball, Cattiva, Penking" value={ownedPals} onChange={e => setOwnedPals(e.target.value)} />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Target Pal</label>
                  <input type="text" placeholder="e.g. Anubis" value={targetPal} onChange={e => setTargetPal(e.target.value)} />
                </div>
                <button className="btn btn-primary" onClick={handleFindPath}>Find Path</button>
              </div>

              {breedingPath.length > 0 ? (
                <div className="steps-list">
                  {breedingPath.map((step, idx) => (
                    <div key={idx} className="step-card">
                      <div className="step-num">Step {idx + 1}</div>
                      <div className="step-details">
                        <div className="parent-node">{step.parent1}</div>
                        <div className="arrow-node">+</div>
                        <div className="parent-node">{step.parent2}</div>
                        <div className="arrow-node">➔</div>
                        <div className="child-node">{step.child}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                ownedPals && targetPal && <p style={{ color: 'var(--text-secondary)', marginTop: '1rem' }}>No path found yet.</p>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
