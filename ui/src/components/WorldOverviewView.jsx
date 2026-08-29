import React from 'react';

export function WorldOverviewView({ currentWorld, instancesCount, basesCount, inventoryCount, onNavigate }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div className="glass-card" style={{ padding: '2rem', borderRadius: '16px', border: '1px solid var(--border-color-hover)' }}>
        <h2 style={{ fontSize: '1.8rem', fontWeight: 800, marginBottom: '0.5rem', color: '#38bdf8' }}>
          🌍 {currentWorld ? currentWorld.display_name : 'World Overview'}
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          {currentWorld ? `Save File Path: ${currentWorld.sav_path}` : 'No active save file loaded.'}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.25rem' }}>
        <div className="glass-card table-row-hover" onClick={() => onNavigate('save_game')} style={{ padding: '1.5rem', borderRadius: '12px', cursor: 'pointer' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🐾</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Captured Pals</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#38bdf8' }}>{instancesCount}</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--accent-gold)', marginTop: '0.5rem' }}>Inspect Pals →</div>
        </div>

        <div className="glass-card table-row-hover" onClick={() => onNavigate('inventory')} style={{ padding: '1.5rem', borderRadius: '12px', cursor: 'pointer' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🎒</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Item Stacks</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#38bdf8' }}>{inventoryCount}</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--accent-gold)', marginTop: '0.5rem' }}>View Storage →</div>
        </div>

        <div className="glass-card table-row-hover" onClick={() => onNavigate('bases')} style={{ padding: '1.5rem', borderRadius: '12px', cursor: 'pointer' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🏰</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Base Camps</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#38bdf8' }}>{basesCount}</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--accent-gold)', marginTop: '0.5rem' }}>Audit Bases →</div>
        </div>

        <div className="glass-card table-row-hover" onClick={() => onNavigate('base_optimizer')} style={{ padding: '1.5rem', borderRadius: '12px', cursor: 'pointer' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>⚡</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Pal Base Optimizer</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#fbbf24' }}>Auto-Match</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--accent-gold)', marginTop: '0.5rem' }}>Optimize Base Pals →</div>
        </div>

        <div className="glass-card table-row-hover" onClick={() => onNavigate('condenser')} style={{ padding: '1.5rem', borderRadius: '12px', cursor: 'pointer' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>⭐</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Condenser Candidates</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#38bdf8' }}>Active</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--accent-gold)', marginTop: '0.5rem' }}>Find Candidates →</div>
        </div>

        <div className="glass-card table-row-hover" onClick={() => onNavigate('missions')} style={{ padding: '1.5rem', borderRadius: '12px', cursor: 'pointer' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📜</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Sub-Missions</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#38bdf8' }}>Quests</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--accent-gold)', marginTop: '0.5rem' }}>Track Quests →</div>
        </div>
      </div>
    </div>
  );
}

export function WelcomeView({ onNavigate, currentWorld, instancesCount, basesCount, inventoryCount }) {
  function round(val, dec) {
    return Number(Math.round(val + 'e' + dec) + 'e-' + dec);
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div className="hero-banner glass-card" style={{ padding: '2.5rem', borderRadius: '16px', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%)', border: '1px solid var(--border-color-hover)' }}>
        <h2 style={{ fontSize: '2.2rem', fontWeight: 800, marginBottom: '0.75rem', background: 'var(--primary-gradient)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Welcome to Palopedix
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem', maxWidth: '750px', lineHeight: 1.6 }}>
          Your ultimate companion dashboard for Palworld. Seamlessly explore game data, inspect save files across multiple worlds, analyze captured Pals & stats, and track storage inventories.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem' }}>
        {/* Global Game Data Card */}
        <div className="glass-card" style={{ padding: '1.75rem', borderRadius: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '1.8rem' }}>🌐</span>
            <div>
              <h3 style={{ fontSize: '1.3rem', fontWeight: 800 }}>Global Game Data</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Static database extracted directly from game files</p>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', margin: '1.5rem 0' }}>
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '1rem', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Master Pals</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent-gold)' }}>138+</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '1rem', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Items & Recipes</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent-gold)' }}>1,891</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '1rem', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Facilities & Tech</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent-gold)' }}>552</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '1rem', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Breeding Combos</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--accent-gold)' }}>18,700+</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button className="primary-btn" onClick={() => onNavigate('paldex')} style={{ flex: 1 }}>📚 Open Paldex</button>
            <button className="secondary-btn" onClick={() => onNavigate('items')} style={{ flex: 1 }}>📦 Browse Items</button>
          </div>
        </div>

        {/* Active World Overview Card */}
        <div className="glass-card" style={{ padding: '1.75rem', borderRadius: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <span style={{ fontSize: '1.8rem' }}>🌍</span>
            <div>
              <h3 style={{ fontSize: '1.3rem', fontWeight: 800 }}>Active World Overview</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--accent-gold)' }}>
                {currentWorld ? currentWorld.display_name : 'No World Selected'}
              </p>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', margin: '1.5rem 0' }}>
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '1rem', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Captured Pals</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#38bdf8' }}>{instancesCount}</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '1rem', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Base Camps</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#38bdf8' }}>{basesCount}</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '1rem', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Item Stacks</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#38bdf8' }}>{inventoryCount}</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: '1rem', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Save Size</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#38bdf8' }}>
                {currentWorld ? `${round(currentWorld.size_bytes / 1024, 1)} KB` : 'N/A'}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button className="primary-btn" onClick={() => onNavigate('save_game')} style={{ flex: 1 }}>🐾 View World Pals</button>
            <button className="secondary-btn" onClick={() => onNavigate('inventory')} style={{ flex: 1 }}>🎒 View Storage</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default WorldOverviewView;
