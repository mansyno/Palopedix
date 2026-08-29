import React, { useState, useEffect, useMemo } from 'react';
import BaseOptimizerView from './components/BaseOptimizerView';
import PaldexMasterView from './components/PaldexMasterView';
import SkillsCatalogView from './components/SkillsCatalogView';
import ItemsCatalogView from './components/ItemsCatalogView';
import BuildingsTechView from './components/BuildingsTechView';
import InventoryView from './components/InventoryView';
import SaveGameExplorerView from './components/SaveGameExplorerView';
import BaseCampsView from './components/BaseCampsView';
import CondenserView from './components/CondenserView';
import SubMissionsView from './components/SubMissionsView';
import BreedingCenterView from './components/BreedingCenterView';
import SettingsView from './components/SettingsView';
import HomepageView from './components/HomepageView';
import { WorldOverviewView, WelcomeView } from './components/WorldOverviewView';
import PalDetailModal from './components/common/PalDetailModal';

function App() {
  // Navigation & World Modes
  const [mode, setMode] = useState('home'); // 'home', 'global', 'world', 'settings'
  const [activeTab, setActiveTab] = useState('paldex');
  const [worlds, setWorlds] = useState([]);
  const [selectedWorldId, setSelectedWorldId] = useState('');
  const [worldLoading, setWorldLoading] = useState(false);
  const [isEngineReady, setIsEngineReady] = useState(false);
  const [engineInitError, setEngineInitError] = useState('');
  const [initAttempts, setInitAttempts] = useState(0);

  // Save Game Loading
  const [savePath, setSavePath] = useState('');
  const [saveLoaded, setSaveLoaded] = useState(false);
  const [loadedPath, setLoadedPath] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Master Data State
  const [pals, setPals] = useState([]);
  const [allMasterPals, setAllMasterPals] = useState([]);
  const [selectedPal, setSelectedPal] = useState(null);

  // Master Paldex Filters
  const [elementFilter, setElementFilter] = useState('');
  const [sizeFilter, setSizeFilter] = useState('');
  const [nocturnalFilter, setNocturnalFilter] = useState('');
  const [suitabilityFilter, setSuitabilityFilter] = useState('');
  const [partnerCategoryFilter, setPartnerCategoryFilter] = useState('');

  // Save Game State
  const [instances, setInstances] = useState([]);
  const [bases, setBases] = useState([]);
  const [ownedSpecies, setOwnedSpecies] = useState([]);
  const [palSourceMode, setPalSourceMode] = useState('global');
  const [ownedPals, setOwnedPals] = useState('');

  // --- Fetch Helper Functions ---
  const fetchPals = async () => {
    try {
      let url = '/api/pals?';
      if (elementFilter) url += `element=${elementFilter}&`;
      if (sizeFilter) url += `size=${sizeFilter}&`;
      if (nocturnalFilter) url += `nocturnal=${nocturnalFilter === 'true'}&`;
      if (suitabilityFilter) url += `suitability=${suitabilityFilter}&`;
      if (partnerCategoryFilter) url += `partner_category=${encodeURIComponent(partnerCategoryFilter)}&`;
      
      const res = await fetch(url);
      const data = await res.json();
      if (Array.isArray(data)) setPals(data);
    } catch (e) {
      console.error("Error fetching pals", e);
    }
  };

  const fetchInstances = async () => {
    try {
      const res = await fetch('/api/save/instances');
      const data = await res.json();
      if (Array.isArray(data)) setInstances(data);
    } catch (e) {
      console.error("Error fetching instances", e);
    }
  };

  const fetchBases = async () => {
    try {
      const res = await fetch('/api/bases');
      const data = await res.json();
      if (Array.isArray(data)) setBases(data);
    } catch (e) {
      console.error("Error fetching bases", e);
    }
  };

  const fetchOwnedSpecies = async () => {
    try {
      const res = await fetch('/api/save/owned-species');
      const data = await res.json();
      if (Array.isArray(data)) setOwnedSpecies(data);
    } catch (e) {
      console.error("Error fetching owned species", e);
    }
  };

  const fetchWorlds = async () => {
    try {
      const res = await fetch('/api/worlds');
      const data = await res.json();
      setWorlds(data.worlds || []);
      if (data.current_world_id) {
        setSelectedWorldId(data.current_world_id);
        setSaveLoaded(true);
        fetchInstances();
        fetchBases();
        fetchOwnedSpecies();
      }
    } catch (e) {
      console.error("Error fetching worlds", e);
    }
  };

  const initEngine = async () => {
    setEngineInitError('');
    let attempts = 0;
    while (attempts < 30) {
      try {
        const res = await fetch('/api/config');
        if (res.ok) {
          setIsEngineReady(true);
          setEngineInitError('');
          await fetchWorlds();
          await fetchPals();
          fetch('/api/pals')
            .then(r => r.json())
            .then(data => {
              if (Array.isArray(data)) setAllMasterPals(data);
            })
            .catch(e => console.error("Error fetching master pals list", e));
          return;
        }
      } catch (e) {
        // Backend still initializing
      }
      attempts++;
      setInitAttempts(attempts);
      await new Promise(r => setTimeout(r, 1000));
    }
    setEngineInitError("Could not connect to Palopedix Backend Server (http://127.0.0.1:8000). Please ensure the backend server is running.");
  };

  // --- Handlers ---
  const handleSelectMode = (newMode, defaultTab) => {
    setMode(newMode);
    if (defaultTab) setActiveTab(defaultTab);
  };

  const handleSelectWorld = async (worldId) => {
    if (!worldId || worldId === selectedWorldId) return;
    setWorldLoading(true);
    try {
      const res = await fetch('/api/worlds/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ world_id: worldId })
      });
      const data = await res.json();
      if (res.ok) {
        setSelectedWorldId(data.world_id);
        setSaveLoaded(true);
        fetchInstances();
        fetchBases();
        fetchOwnedSpecies();
      }
    } catch (e) {
      console.error("Error selecting world", e);
    } finally {
      setWorldLoading(false);
    }
  };

  const handleLoadSave = async () => {
    setLoading(true);
    setErrorMsg('');
    setSuccessMsg('');
    try {
      const res = await fetch('/api/save/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ save_path: savePath || null })
      });
      const data = await res.json();
      if (res.ok) {
        setSaveLoaded(true);
        setLoadedPath(data.path);
        setSuccessMsg(data.message);
        fetchInstances();
        fetchBases();
        fetchOwnedSpecies();
      } else {
        setErrorMsg(data.detail || "Failed to load save file.");
      }
    } catch (e) {
      setErrorMsg("Error making request to backend.");
    } finally {
      setLoading(false);
    }
  };

  const handlePalSourceModeChange = (newMode) => {
    if (newMode === 'caught' && !saveLoaded) {
      alert("Please load a save file in Settings first to filter by your caught Pals!");
      return;
    }
    setPalSourceMode(newMode);
  };

  const availablePalOptions = useMemo(() => {
    if (palSourceMode === 'caught' && ownedSpecies && ownedSpecies.length > 0) {
      return Array.from(new Set(ownedSpecies)).sort();
    }
    const palList = (allMasterPals && allMasterPals.length > 0) ? allMasterPals : pals;
    if (palList && palList.length > 0) {
      return Array.from(new Set(palList.map(p => p.display_name).filter(Boolean))).sort();
    }
    return [];
  }, [palSourceMode, ownedSpecies, allMasterPals, pals]);

  // --- Effects ---
  useEffect(() => {
    initEngine();
  }, []);

  useEffect(() => {
    if (isEngineReady) {
      fetchPals();
    }
  }, [isEngineReady, elementFilter, sizeFilter, nocturnalFilter, suitabilityFilter, partnerCategoryFilter]);

  useEffect(() => {
    if (isEngineReady) {
      fetch('/api/pals')
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) setAllMasterPals(data);
        })
        .catch(e => console.error("Error fetching master pals list", e));
    }
  }, [isEngineReady]);

  useEffect(() => {
    fetch('/api/save/status')
      .then(res => res.json())
      .then(data => {
        if (data.loaded) {
          setSaveLoaded(true);
          setLoadedPath(data.path || 'Previous Session');
          fetchOwnedSpecies();
        }
      })
      .catch(err => console.error("Error checking save status:", err));
  }, []);

  useEffect(() => {
    if (saveLoaded) {
      fetchInstances();
      fetchOwnedSpecies();
    }
  }, [saveLoaded]);

  if (!isEngineReady) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'radial-gradient(ellipse at center, #1e1b4b 0%, #0f172a 100%)', color: 'var(--text-primary)', padding: '2rem', textAlign: 'center' }}>
        <div style={{ width: '80px', height: '80px', borderRadius: '24px', background: 'linear-gradient(135deg, #6366f1, #a855f7)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '3rem', fontWeight: 900, boxShadow: '0 12px 35px rgba(99,102,241,0.5)', marginBottom: '1.5rem' }}>
          P
        </div>
        <h1 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '0.5rem', background: 'linear-gradient(135deg, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Palopedix
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.05rem', maxWidth: '440px', lineHeight: 1.5, marginBottom: '2rem' }}>
          Initializing Palworld 1.0+ database engine & discovering active saves...
        </p>

        {engineInitError ? (
          <div className="glass-card" style={{ border: '1px solid #ef4444', background: 'rgba(239, 68, 68, 0.1)', color: '#fca5a5', padding: '1.5rem', maxWidth: '420px', borderRadius: '16px' }}>
            <p style={{ fontWeight: 600, marginBottom: '1rem' }}>{engineInitError}</p>
            <button className="primary-btn" onClick={initEngine} style={{ width: '100%' }}>
              🔄 Retry Connection
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'rgba(255,255,255,0.05)', padding: '0.75rem 1.5rem', borderRadius: '30px', border: '1px solid rgba(255,255,255,0.1)' }}>
            <span className="loading-spinner" style={{ width: '18px', height: '18px', borderWidth: '2px' }}></span>
            <span style={{ fontSize: '0.9rem', color: 'var(--accent-gold)', fontWeight: 600 }}>Connecting to engine...</span>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Sidebar navigation */}
      {mode !== 'home' && (
        <aside className="sidebar">
          <div className="logo-area" onClick={() => setMode('home')} style={{ cursor: 'pointer' }}>
            <div className="logo-icon">P</div>
            <div className="logo-text">Palopedix</div>
          </div>

          <nav className="nav-links">
            <div 
              className="nav-item" 
              onClick={() => setMode('home')}
              style={{ background: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.3)', marginBottom: '1rem', fontWeight: 700 }}
            >
              🏠 Return to Homepage
            </div>

            {mode === 'global' && (
              <>
                <div className="nav-section-header">GLOBAL GAME DATA</div>
                <div className={`nav-item ${activeTab === 'paldex' ? 'active' : ''}`} onClick={() => setActiveTab('paldex')}>
                  📚 Master Paldex
                </div>
                <div className={`nav-item ${activeTab === 'skills' ? 'active' : ''}`} onClick={() => setActiveTab('skills')}>
                  ⚡ Skills Catalog
                </div>
                <div className={`nav-item ${activeTab === 'items' ? 'active' : ''}`} onClick={() => setActiveTab('items')}>
                  📦 Items & Recipes
                </div>
                <div className={`nav-item ${activeTab === 'buildings' ? 'active' : ''}`} onClick={() => setActiveTab('buildings')}>
                  🏗️ Facilities & Tech
                </div>
              </>
            )}

            {mode === 'world' && (
              <>
                <div className="nav-section-header">ACTIVE WORLD DATA</div>
                <div className="world-selector-container" style={{ padding: '0.4rem 0.65rem', marginBottom: '0.4rem' }}>
                  <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.2rem', fontWeight: 700 }}>
                    🌍 ACTIVE WORLD
                  </label>
                  <select
                    value={selectedWorldId}
                    onChange={(e) => handleSelectWorld(e.target.value)}
                    disabled={worldLoading}
                    style={{
                      width: '100%',
                      padding: '0.35rem 0.5rem',
                      fontSize: '0.8rem',
                      background: 'rgba(0,0,0,0.4)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '6px',
                      color: 'var(--text-primary)',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    {worlds.length === 0 && <option value="">No worlds found</option>}
                    {worlds.map(w => (
                      <option key={w.world_id} value={w.world_id}>
                        {w.display_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className={`nav-item ${activeTab === 'world_overview' ? 'active' : ''}`} onClick={() => setActiveTab('world_overview')}>
                  📊 World Overview
                </div>
                <div className={`nav-item ${activeTab === 'save_game' ? 'active' : ''}`} onClick={() => setActiveTab('save_game')}>
                  🐾 World Pals
                </div>
                <div className={`nav-item ${activeTab === 'inventory' ? 'active' : ''}`} onClick={() => setActiveTab('inventory')}>
                  🎒 Save Inventory
                </div>
                <div className={`nav-item ${activeTab === 'bases' ? 'active' : ''}`} onClick={() => setActiveTab('bases')}>
                  🏰 Base Camps
                </div>
                <div className={`nav-item ${activeTab === 'base_optimizer' ? 'active' : ''}`} onClick={() => setActiveTab('base_optimizer')}>
                  🏰 Base Optimizer
                </div>
                <div className={`nav-item ${activeTab === 'condenser' ? 'active' : ''}`} onClick={() => setActiveTab('condenser')}>
                  ⭐ Condenser
                </div>
                <div className={`nav-item ${activeTab === 'missions' ? 'active' : ''}`} onClick={() => setActiveTab('missions')}>
                  📜 Sub-Missions
                </div>
                <div className={`nav-item ${activeTab === 'breeding' ? 'active' : ''}`} onClick={() => setActiveTab('breeding')}>
                  🐣 Breeding Center
                </div>
              </>
            )}

            {mode === 'settings' && (
              <>
                <div className="nav-section-header">SYSTEM SETTINGS</div>
                <div className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>
                  ⚙️ Settings & Loader
                </div>
              </>
            )}
          </nav>
        </aside>
      )}

      {/* Main Panel */}
      <main className={`main-content ${mode === 'home' ? 'main-home' : ''}`}>
        {mode !== 'home' && (
          <header>
            <h1>{
              activeTab === 'welcome' ? 'Palopedix Dashboard' :
              activeTab === 'paldex' ? 'Palworld 1.0+ Master Paldex' :
              activeTab === 'skills' ? 'Skills Database Catalog' :
              activeTab === 'items' ? 'Items & Crafting Catalog' :
              activeTab === 'buildings' ? 'Base Facilities & Technology Tree' :
              activeTab === 'inventory' ? 'Save Inventory & Chest Storage' :
              activeTab === 'save_game' ? 'World Pals Explorer' :
              activeTab === 'bases' ? 'Base Camp Overview' :
              activeTab === 'base_optimizer' ? 'Base Camp Pal Recommendation & Optimizer Engine' :
              activeTab === 'condenser' ? 'Condenser Recommendations' :
              activeTab === 'missions' ? 'Active NPC Sub-Missions' :
              activeTab === 'settings' ? 'System Settings' : 'Breeding Center'
            }</h1>
            <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>{
              activeTab === 'welcome' ? 'Welcome overview and active save file statistics.' :
              activeTab === 'paldex' ? 'Browse all Pal species, base stats, elements, work capabilities, learned skills, and drops.' :
              activeTab === 'skills' ? 'Explore active combat skills, passive traits, and partner abilities.' :
              activeTab === 'items' ? 'Search items, equipment, and crafting recipe ingredients.' :
              activeTab === 'buildings' ? 'Explore base buildings and technology tree unlocks.' :
              activeTab === 'inventory' ? 'Inspect items in your personal inventory, equipped loadouts, and base chests.' :
              activeTab === 'save_game' ? 'Click any captured Pal to view its full Paldex bio, element, skills, and stats.' :
              activeTab === 'bases' ? 'Audit placed infrastructure and active base camp workers.' :
              activeTab === 'base_optimizer' ? 'Automated work suitability demand matching, nocturnal 24/7 duty cycle bonuses, and food satiety balance.' :
              activeTab === 'condenser' ? 'View the absolute best Pals to condense based on your duplicates, IVs, and passives.' :
              activeTab === 'missions' ? 'Track and fulfill NPC quest requirements using your personal inventory, base chests, and caught Pals.' :
              activeTab === 'settings' ? 'Manage save file loading and database source settings.' :
              'Calculate offspring results or find parent breeding pairs for any Pal.'
            }</p>
          </header>
        )}

        {/* 🏠 Homepage Landing */}
        {mode === 'home' && (
          <HomepageView
            onSelectMode={handleSelectMode}
            currentWorld={worlds.find(w => w.world_id === selectedWorldId)}
            instancesCount={instances.length}
            basesCount={bases.length}
            inventoryCount={199}
          />
        )}

        {/* All Section Views (Only when mode !== 'home') */}
        {mode !== 'home' && (
          <>
            {mode === 'world' && activeTab === 'world_overview' && (
              <WorldOverviewView
                currentWorld={worlds.find(w => w.world_id === selectedWorldId)}
                instancesCount={instances.length}
                basesCount={bases.length}
                inventoryCount={199}
                onNavigate={(tab) => setActiveTab(tab)}
              />
            )}
            {activeTab === 'welcome' && (
              <WelcomeView
                onNavigate={(tab) => setActiveTab(tab)}
                currentWorld={worlds.find(w => w.world_id === selectedWorldId)}
                instancesCount={instances.length}
                basesCount={bases.length}
                inventoryCount={199}
              />
            )}

            {/* 📚 Paldex Tab */}
            {activeTab === 'paldex' && (
              <PaldexMasterView
                pals={pals}
                setSelectedPal={setSelectedPal}
                elementFilter={elementFilter}
                setElementFilter={setElementFilter}
                sizeFilter={sizeFilter}
                setSizeFilter={setSizeFilter}
                nocturnalFilter={nocturnalFilter}
                setNocturnalFilter={setNocturnalFilter}
                suitabilityFilter={suitabilityFilter}
                setSuitabilityFilter={setSuitabilityFilter}
                partnerCategoryFilter={partnerCategoryFilter}
                setPartnerCategoryFilter={setPartnerCategoryFilter}
              />
            )}

            {/* ⚡ Skills Database Catalog Tab */}
            {activeTab === 'skills' && <SkillsCatalogView />}

            {/* 📦 Items & Recipes Catalog Tab */}
            {activeTab === 'items' && <ItemsCatalogView />}

            {/* 🏗️ Base Facilities & Tech Tree Tab */}
            {activeTab === 'buildings' && <BuildingsTechView />}

            {/* Selected Pal Detail Modal */}
            {selectedPal && (
              <PalDetailModal pal={selectedPal} onClose={() => setSelectedPal(null)} />
            )}

            {/* 🎒 Save Inventory Tab */}
            {activeTab === 'inventory' && <InventoryView />}

            {/* 💾 Save Game Explorer Tab */}
            {activeTab === 'save_game' && (
              <SaveGameExplorerView
                instances={instances}
                pals={pals}
                saveLoaded={saveLoaded}
                loadedPath={loadedPath}
                handleLoadSave={handleLoadSave}
                loading={loading}
                setSelectedPal={setSelectedPal}
              />
            )}

            {/* 🏰 Base Camps Tab */}
            {activeTab === 'bases' && (
              <BaseCampsView
                bases={bases}
                saveLoaded={saveLoaded}
                fetchBases={fetchBases}
                fetchInstances={fetchInstances}
              />
            )}

            {/* ⚡ Base Pal Optimizer Tab */}
            {activeTab === 'base_optimizer' && <BaseOptimizerView />}

            {/* ⭐ Condenser Tab */}
            {activeTab === 'condenser' && <CondenserView />}

            {/* 📜 Sub-Missions Tab */}
            {activeTab === 'missions' && <SubMissionsView />}

            {/* ⚙️ Settings Tab */}
            {activeTab === 'settings' && (
              <SettingsView
                savePath={savePath}
                setSavePath={setSavePath}
                handleLoadSave={handleLoadSave}
                loading={loading}
                errorMsg={errorMsg}
                successMsg={successMsg}
              />
            )}

            {/* 🐣 Breeding Center Tab */}
            {activeTab === 'breeding' && (
              <BreedingCenterView
                pals={pals}
                allMasterPals={allMasterPals}
                ownedSpecies={ownedSpecies}
                palSourceMode={palSourceMode}
                handlePalSourceModeChange={handlePalSourceModeChange}
                setSelectedPal={setSelectedPal}
                availablePalOptions={availablePalOptions}
                ownedPals={ownedPals}
                setOwnedPals={setOwnedPals}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
