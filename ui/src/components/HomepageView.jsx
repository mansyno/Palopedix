import React from 'react';

export function HomepageView({ onSelectMode, currentWorld, instancesCount, basesCount, inventoryCount }) {
  return (
    <div style={{ width: '100%', maxWidth: '1200px', margin: '0 auto', padding: '0.25rem 1rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.35rem' }}>
        <h1 style={{ fontSize: '2.5rem', fontWeight: 800, background: 'var(--primary-gradient)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0 }}>
          Palopedix
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.05rem', maxWidth: '600px', margin: 0 }}>
          Palworld Master Database & Save Game Analytics
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.25rem' }}>
        {/* Card 1: Global Data */}
        <div 
          className="glass-card table-row-hover" 
          onClick={() => onSelectMode('global', 'paldex')}
          style={{ padding: '1.5rem', borderRadius: '16px', cursor: 'pointer', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '280px', border: '1px solid var(--border-color-hover)' }}
        >
          <div>
            <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'rgba(99, 102, 241, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.75rem', marginBottom: '1rem', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
              🌐
            </div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 800, marginBottom: '0.4rem' }}>Global Game Data</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.5, marginBottom: '1rem' }}>
              Explore master Pal specifications, item recipes, technology trees, and breeding combinations directly from game files.
            </p>
          </div>
          <div>
            <button className="primary-btn" style={{ width: '100%', padding: '0.75rem', fontSize: '0.9rem' }}>
              Explore Global Data →
            </button>
          </div>
        </div>

        {/* Card 2: Active World Data */}
        <div 
          className="glass-card table-row-hover" 
          onClick={() => onSelectMode('world', 'world_overview')}
          style={{ padding: '1.5rem', borderRadius: '16px', cursor: 'pointer', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '280px', border: '1px solid rgba(56, 189, 248, 0.3)' }}
        >
          <div>
            <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'rgba(56, 189, 248, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.75rem', marginBottom: '1rem', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
              🌍
            </div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 800, marginBottom: '0.4rem' }}>Active World Data</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.5, marginBottom: '1rem' }}>
              Inspect live save file analytics for your selected active world. Audit captured Pals & IVs, personal inventory, storage chests, and condenser candidates.
            </p>
          </div>
          <div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.5rem 0.75rem', borderRadius: '8px', marginBottom: '1rem', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Selected Active World:</div>
              <strong style={{ color: '#38bdf8', fontSize: '0.85rem' }}>{currentWorld ? currentWorld.display_name : 'No World Loaded'}</strong>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <button className="primary-btn" style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem', background: 'linear-gradient(135deg, #0284c7 0%, #06b6d4 100%)' }}>
                World Data →
              </button>
              <button 
                className="btn btn-secondary" 
                onClick={(e) => { e.stopPropagation(); onSelectMode('world', 'base_optimizer'); }}
                style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem', background: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.4)', fontWeight: 700 }}
              >
                ⚡ Optimizer →
              </button>
            </div>
            <button
              className="btn btn-secondary"
              onClick={(e) => { e.stopPropagation(); onSelectMode('world', 'base_migration'); }}
              style={{ width: '100%', padding: '0.65rem', fontSize: '0.85rem', background: 'rgba(99, 102, 241, 0.15)', color: '#a5b4fc', border: '1px solid rgba(99, 102, 241, 0.3)', fontWeight: 700 }}
            >
              🚚 Moving Van (Container Migration) →
            </button>
          </div>
        </div>

        {/* Card 3: Settings */}
        <div 
          className="glass-card table-row-hover" 
          onClick={() => onSelectMode('settings', 'settings')}
          style={{ padding: '1.5rem', borderRadius: '16px', cursor: 'pointer', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '280px', border: '1px solid var(--border-color)' }}
        >
          <div>
            <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'rgba(148, 163, 184, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.75rem', marginBottom: '1rem', border: '1px solid rgba(148, 163, 184, 0.3)' }}>
              ⚙️
            </div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 800, marginBottom: '0.4rem' }}>Settings & System</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.5, marginBottom: '1rem' }}>
              Configure manual Level.sav file paths and manage system save file loading for PalEngine.
            </p>
          </div>
          <div>
            <button className="secondary-btn" style={{ width: '100%', padding: '0.75rem', fontSize: '0.9rem' }}>
              Open Settings →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default HomepageView;
