import React from 'react';

export function SettingsView({ savePath, setSavePath, handleLoadSave, loading, errorMsg, successMsg }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '800px' }}>
      {/* Save Loader Box */}
      <div className="glass-card" style={{ padding: '1.75rem' }}>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          💾 Manual Save File Loader
        </h3>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
          Manually specify a custom <code>Level.sav</code> file path to parse and reload instance data into PalEngine.
        </p>

        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="Leave empty to auto-discover local save game path..."
            value={savePath}
            onChange={(e) => setSavePath(e.target.value)}
            style={{ flex: 1 }}
          />
          <button
            className="primary-btn"
            onClick={handleLoadSave}
            disabled={loading}
            style={{ whiteSpace: 'nowrap' }}
          >
            {loading ? 'Parsing Save...' : 'Load & Parse'}
          </button>
        </div>

        {errorMsg && (
          <div style={{ marginTop: '1rem', color: 'var(--accent-red)', background: 'rgba(239,68,68,0.1)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--accent-red)' }}>
            {errorMsg}
          </div>
        )}

        {successMsg && (
          <div style={{ marginTop: '1rem', color: 'var(--accent-green)', background: 'rgba(34,197,94,0.1)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--accent-green)' }}>
            {successMsg}
          </div>
        )}
      </div>
    </div>
  );
}

export default SettingsView;
