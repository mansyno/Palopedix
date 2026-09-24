import React, { useState, useEffect, useMemo } from 'react';
import { useTableSort } from '../hooks/useTableSort';
import PassiveBadge from './common/PassiveBadge';
import { getElementIconUrl } from '../constants/gameData';

const STATUS_COLORS = {
  FAVORED: {
    bg: 'rgba(16, 185, 129, 0.15)',
    border: '#10b981',
    text: '#34d399',
    icon: '🟢',
    badgeBg: '#065f46',
  },
  NEUTRAL: {
    bg: 'rgba(6, 182, 212, 0.15)',
    border: '#06b6d4',
    text: '#38bdf8',
    icon: '🔵',
    badgeBg: '#155e75',
  },
  CHALLENGING: {
    bg: 'rgba(245, 158, 11, 0.15)',
    border: '#f59e0b',
    text: '#fbbf24',
    icon: '🟡',
    badgeBg: '#78350f',
  },
  'HIGH DIFFICULTY': {
    bg: 'rgba(249, 115, 22, 0.15)',
    border: '#f97316',
    text: '#fb923c',
    icon: '🟠',
    badgeBg: '#7c2d12',
  },
  'UNLIKELY / NOT RECOMMENDED': {
    bg: 'rgba(239, 68, 68, 0.15)',
    border: '#ef4444',
    text: '#f87171',
    icon: '🔴',
    badgeBg: '#7f1d1d',
  },
};

const CATEGORY_OPTIONS = [
  { value: 'All', label: 'All Boss Encounters' },
  { value: 'Tower Boss', label: 'Tower Bosses' },
  { value: 'Alpha Legendary', label: 'Alpha Legendaries' },
  { value: 'Alpha Boss', label: 'Field Alpha Bosses' },
  { value: 'Raid Boss', label: 'Raid Bosses' },
];

export default function BossCounterView({ saveLoaded = true, worldId, setSelectedPal }) {
  const [bosses, setBosses] = useState([]);
  const [loadingBosses, setLoadingBosses] = useState(true);
  const [viewMode, setViewMode] = useState('list'); // 'list' | 'detail'
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedBossId, setSelectedBossId] = useState('');
  const [recommendation, setRecommendation] = useState(null);
  const [loadingParty, setLoadingParty] = useState(false);
  const [partyError, setPartyError] = useState(null);
  const [showAllDrops, setShowAllDrops] = useState(false);
  const [selectedDropIdx, setSelectedDropIdx] = useState(0);

  // Reset drop view on boss change
  useEffect(() => {
    setShowAllDrops(false);
    setSelectedDropIdx(0);
  }, [selectedBossId]);

  // Fetch all bosses on mount
  useEffect(() => {
    setLoadingBosses(true);
    fetch('/api/bosses')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch boss registry');
        return res.json();
      })
      .then((data) => {
        setBosses(data);
      })
      .catch((err) => {
        console.error('Error fetching bosses:', err);
      })
      .finally(() => {
        setLoadingBosses(false);
      });
  }, []);

  // Fetch recommendation whenever selectedBossId changes
  useEffect(() => {
    if (!selectedBossId) return;

    setLoadingParty(true);
    setPartyError(null);

    fetch(`/api/bosses/${encodeURIComponent(selectedBossId)}/party`)
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `Server returned ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        setRecommendation(data);
      })
      .catch((err) => {
        console.error('Error fetching boss recommendation:', err);
        setPartyError(err.message);
        setRecommendation(null);
      })
      .finally(() => {
        setLoadingParty(false);
      });
  }, [selectedBossId, worldId]);

  // Category counts
  const categoryCounts = useMemo(() => {
    const counts = { All: bosses.length };
    bosses.forEach((b) => {
      const cat = b.category || 'Alpha Boss';
      counts[cat] = (counts[cat] || 0) + 1;
    });
    return counts;
  }, [bosses]);

  // Filtered bosses list
  const filteredBosses = useMemo(() => {
    return bosses.filter((b) => {
      const matchCat =
        selectedCategory === 'All' || b.category === selectedCategory;
      const q = searchQuery.trim().toLowerCase();
      const matchSearch =
        !q ||
        b.canonical_name?.toLowerCase().includes(q) ||
        b.title?.toLowerCase().includes(q) ||
        b.pal_species?.toLowerCase().includes(q) ||
        (b.elements || []).some((e) => e.toLowerCase().includes(q)) ||
        (b.weaknesses || []).some((w) => w.toLowerCase().includes(q));
      return matchCat && matchSearch;
    });
  }, [bosses, selectedCategory, searchQuery]);

  // Table sorting
  const {
    sortedData: sortedBosses,
    sortCol,
    sortDesc,
    handleSort,
  } = useTableSort(filteredBosses, 'canonical_name', false);

  // Active selected boss profile
  const selectedBossProfile = useMemo(() => {
    return (
      recommendation?.boss_profile ||
      bosses.find(
        (b) =>
          b.id === selectedBossId ||
          b.canonical_name?.toLowerCase() === selectedBossId?.toLowerCase()
      ) ||
      null
    );
  }, [recommendation, bosses, selectedBossId]);

  const readiness = recommendation?.encounter_readiness;
  const statusCfg = readiness
    ? STATUS_COLORS[readiness.status] || STATUS_COLORS.NEUTRAL
    : null;

  const handleSelectBoss = (bossId) => {
    setSelectedBossId(bossId);
    setViewMode('detail');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      {/* Save file warning banner if not loaded */}
      {!saveLoaded && (
        <div
          style={{
            flexShrink: 0,
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid #ef4444',
            borderRadius: '8px',
            padding: '0.65rem 1rem',
            marginBottom: '0.5rem',
            color: '#f87171',
            fontSize: '0.85rem',
            fontWeight: '500',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <span>⚠️</span>
          <span>No world save loaded. Live Palbox roster counter analysis requires a loaded save world.</span>
        </div>
      )}

      {/* VIEW MODE 1: MASTER LIST TABLE */}
      {viewMode === 'list' && (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, gap: '0.75rem', overflow: 'hidden' }}>
          {/* Controls Bar: Category Dropdown & Search Input */}
          <div
            className="filter-bar glass-card"
            style={{
              flexShrink: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '0.75rem',
              padding: '0.85rem 1.15rem',
              borderRadius: '10px',
            }}
          >
            {/* Category Dropdown */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <label style={{ fontSize: '0.82rem', fontWeight: '600', color: 'var(--accent-gold)' }}>
                Boss Category:
              </label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                style={{
                  background: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  color: 'var(--text-primary)',
                  padding: '0.45rem 0.85rem',
                  fontSize: '0.85rem',
                  fontWeight: '600',
                  outline: 'none',
                  cursor: 'pointer',
                  minWidth: '200px',
                }}
              >
                {CATEGORY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label} ({categoryCounts[opt.value] ?? 0})
                  </option>
                ))}
              </select>
            </div>

            {/* Search Box */}
            <div style={{ position: 'relative', minWidth: '260px' }}>
              <input
                type="text"
                placeholder="Search boss, title, or element..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  background: 'rgba(0, 0, 0, 0.35)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  padding: '0.45rem 0.75rem 0.45rem 2rem',
                  color: 'var(--text-primary)',
                  fontSize: '0.85rem',
                  outline: 'none',
                }}
              />
              <span
                style={{
                  position: 'absolute',
                  left: '0.65rem',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  fontSize: '0.85rem',
                  color: 'var(--text-secondary)',
                  pointerEvents: 'none',
                }}
              >
                🔍
              </span>
            </div>

            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Showing <strong>{filteredBosses.length}</strong> of <strong>{bosses.length}</strong> bosses
            </div>
          </div>

          {/* Master Table List */}
          <div
            className="glass-card table-container"
            style={{
              flex: 1,
              minHeight: 0,
              overflowY: 'auto',
              overflowX: 'auto',
              padding: 0,
              borderRadius: '10px',
              marginBottom: '1rem',
            }}
          >
            {loadingBosses ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                Loading Boss Registry...
              </div>
            ) : filteredBosses.length === 0 ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                No bosses match the selected filter.
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0, fontSize: '0.84rem' }}>
                <thead>
                  <tr style={{ textAlign: 'left' }}>
                    <th style={{ padding: '0.65rem 0.85rem', width: '45px', position: 'sticky', top: 0, zIndex: 10, background: '#0f172a' }}>#</th>
                    <th
                      onClick={() => handleSort('canonical_name')}
                      style={{ padding: '0.65rem 0.85rem', cursor: 'pointer', position: 'sticky', top: 0, zIndex: 10, background: '#0f172a', userSelect: 'none' }}
                    >
                      Boss Encounter{sortCol === 'canonical_name' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                    </th>
                    <th
                      onClick={() => handleSort('category')}
                      style={{ padding: '0.65rem 0.85rem', width: '140px', cursor: 'pointer', position: 'sticky', top: 0, zIndex: 10, background: '#0f172a', userSelect: 'none' }}
                    >
                      Category{sortCol === 'category' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                    </th>
                    <th
                      onClick={() => handleSort('level')}
                      style={{ padding: '0.65rem 0.85rem', width: '70px', textAlign: 'center', cursor: 'pointer', position: 'sticky', top: 0, zIndex: 10, background: '#0f172a', userSelect: 'none' }}
                    >
                      Level{sortCol === 'level' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                    </th>
                    <th
                      onClick={() => handleSort('hp')}
                      style={{ padding: '0.65rem 0.85rem', width: '90px', textAlign: 'right', cursor: 'pointer', position: 'sticky', top: 0, zIndex: 10, background: '#0f172a', userSelect: 'none' }}
                    >
                      HP{sortCol === 'hp' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                    </th>
                    <th
                      onClick={() => handleSort('element1')}
                      style={{ padding: '0.65rem 0.85rem', width: '130px', cursor: 'pointer', position: 'sticky', top: 0, zIndex: 10, background: '#0f172a', userSelect: 'none' }}
                    >
                      Elements{sortCol === 'element1' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                    </th>
                    <th style={{ padding: '0.65rem 0.85rem', width: '160px', position: 'sticky', top: 0, zIndex: 10, background: '#0f172a' }}>Weaknesses (2.0x)</th>
                    <th
                      onClick={() => handleSort('location')}
                      style={{ padding: '0.65rem 0.85rem', cursor: 'pointer', position: 'sticky', top: 0, zIndex: 10, background: '#0f172a', userSelect: 'none' }}
                    >
                      Arena / Location{sortCol === 'location' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                    </th>
                    <th style={{ padding: '0.65rem 0.85rem', width: '160px', textAlign: 'center', position: 'sticky', top: 0, zIndex: 10, background: '#0f172a' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedBosses.map((boss, idx) => (
                    <tr
                      key={boss.id}
                      onClick={() => handleSelectBoss(boss.id)}
                      style={{
                        cursor: 'pointer',
                        borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                        transition: 'background 0.12s ease',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(99, 102, 241, 0.1)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                      }}
                    >
                      <td style={{ padding: '0.65rem 0.85rem', color: 'var(--text-secondary)', fontWeight: '600' }}>
                        {idx + 1}
                      </td>

                      {/* Boss Avatar & Title */}
                      <td style={{ padding: '0.65rem 0.85rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                          <div style={{ position: 'relative', width: '38px', height: '38px', flexShrink: 0 }}>
                            <img
                              src={boss.icon_path}
                              alt={boss.canonical_name}
                              style={{
                                width: '38px',
                                height: '38px',
                                borderRadius: '6px',
                                objectFit: 'cover',
                                background: 'rgba(0, 0, 0, 0.35)',
                                border: '1px solid var(--border-color)',
                              }}
                              onError={(e) => {
                                e.target.style.display = 'none';
                              }}
                            />
                            {boss.badge_icon_path && (
                              <img
                                src={boss.badge_icon_path}
                                alt="Alpha Badge"
                                style={{
                                  position: 'absolute',
                                  top: '-4px',
                                  right: '-4px',
                                  width: '16px',
                                  height: '16px',
                                }}
                                onError={(e) => {
                                  e.target.style.display = 'none';
                                }}
                              />
                            )}
                          </div>
                          <div>
                            <div style={{ fontWeight: '700', color: 'var(--text-primary)' }}>
                              {boss.canonical_name}
                            </div>
                            {boss.title && (
                              <div style={{ fontSize: '0.74rem', color: 'var(--accent-gold)' }}>
                                {boss.title}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>

                      {/* Category Badge */}
                      <td style={{ padding: '0.65rem 0.85rem' }}>
                        <span
                          style={{
                            fontSize: '0.72rem',
                            fontWeight: '600',
                            padding: '0.15rem 0.5rem',
                            borderRadius: '4px',
                            background:
                              boss.category === 'Tower Boss'
                                ? 'rgba(168, 85, 247, 0.2)'
                                : boss.category === 'Alpha Legendary'
                                ? 'rgba(234, 179, 8, 0.2)'
                                : boss.category === 'Raid Boss'
                                ? 'rgba(239, 68, 68, 0.2)'
                                : 'rgba(59, 130, 246, 0.2)',
                            color:
                              boss.category === 'Tower Boss'
                                ? '#d8b4fe'
                                : boss.category === 'Alpha Legendary'
                                ? '#fde047'
                                : boss.category === 'Raid Boss'
                                ? '#fca5a5'
                                : '#93c5fd',
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                          }}
                        >
                          {boss.category}
                        </span>
                      </td>

                      {/* Level */}
                      <td style={{ padding: '0.65rem 0.85rem', textAlign: 'center', fontWeight: '700', color: 'var(--accent-gold)' }}>
                        Lv.{boss.level}
                      </td>

                      {/* HP */}
                      <td style={{ padding: '0.65rem 0.85rem', textAlign: 'right', fontWeight: '600', color: 'var(--text-primary)' }}>
                        {boss.hp ? boss.hp.toLocaleString() : 'N/A'}
                      </td>

                      {/* Elements */}
                      <td style={{ padding: '0.65rem 0.85rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}>
                          {(boss.elements || []).map((elem) => (
                            <span
                              key={elem}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.2rem',
                                fontSize: '0.72rem',
                                background: 'rgba(0, 0, 0, 0.35)',
                                padding: '0.1rem 0.35rem',
                                borderRadius: '4px',
                                border: '1px solid rgba(255, 255, 255, 0.08)',
                              }}
                            >
                              <img
                                src={getElementIconUrl(elem)}
                                alt={elem}
                                style={{ width: '12px', height: '12px' }}
                                onError={(e) => {
                                  e.target.style.display = 'none';
                                }}
                              />
                              {elem}
                            </span>
                          ))}
                        </div>
                      </td>

                      {/* Weaknesses */}
                      <td style={{ padding: '0.65rem 0.85rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', flexWrap: 'wrap' }}>
                          {(boss.weaknesses || []).map((w) => (
                            <span
                              key={w}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.2rem',
                                fontSize: '0.7rem',
                                fontWeight: '700',
                                color: '#34d399',
                                background: 'rgba(16, 185, 129, 0.15)',
                                border: '1px solid rgba(16, 185, 129, 0.3)',
                                padding: '0.1rem 0.35rem',
                                borderRadius: '4px',
                              }}
                            >
                              <img
                                src={getElementIconUrl(w)}
                                alt={w}
                                style={{ width: '11px', height: '11px' }}
                                onError={(e) => {
                                  e.target.style.display = 'none';
                                }}
                              />
                              {w}
                            </span>
                          ))}
                        </div>
                      </td>

                      {/* Arena / Location */}
                      <td style={{ padding: '0.65rem 0.85rem', color: 'var(--text-secondary)', fontSize: '0.78rem' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                          <span>📍 {boss.location}</span>
                          {boss.time_limit_sec && (
                            <span style={{ color: '#f59e0b', fontSize: '0.72rem' }}>
                              ⏱️ {boss.time_limit_sec / 60}m Arena Timer
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Action Button */}
                      <td style={{ padding: '0.65rem 0.85rem', textAlign: 'center' }}>
                        <button
                          className="btn btn-primary"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectBoss(boss.id);
                          }}
                          style={{
                            fontSize: '0.75rem',
                            padding: '0.3rem 0.7rem',
                            borderRadius: '6px',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          ⚔️ Counter Party →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* VIEW MODE 2: DEDICATED ENCOUNTER DETAIL PAGE */}
      {viewMode === 'detail' && selectedBossProfile && (
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden', gap: '1rem', paddingRight: '0.35rem', paddingBottom: '2.5rem' }}>
          {/* Detail Navigation Top Bar */}
          <div
            style={{
              position: 'sticky',
              top: 0,
              zIndex: 20,
              backdropFilter: 'blur(12px)',
              background: 'rgba(15, 23, 42, 0.95)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '0.75rem',
              border: '1px solid var(--border-color)',
              borderRadius: '10px',
              padding: '0.75rem 1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setViewMode('list')}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  fontSize: '0.85rem',
                  padding: '0.45rem 0.9rem',
                  fontWeight: '600',
                  borderRadius: '6px',
                }}
              >
                ← Back to Boss List
              </button>

              <div style={{ borderLeft: '1px solid var(--border-color)', paddingLeft: '0.75rem' }}>
                <span style={{ fontSize: '0.92rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                  {selectedBossProfile.canonical_name}
                </span>
                {selectedBossProfile.title && (
                  <span style={{ fontSize: '0.8rem', color: 'var(--accent-gold)', marginLeft: '0.5rem' }}>
                    • {selectedBossProfile.title}
                  </span>
                )}
              </div>
            </div>

            {/* Quick Boss Switcher Dropdown */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Switch Boss:</label>
              <select
                value={selectedBossProfile.id}
                onChange={(e) => setSelectedBossId(e.target.value)}
                style={{
                  background: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  color: 'var(--text-primary)',
                  padding: '0.35rem 0.7rem',
                  fontSize: '0.82rem',
                  outline: 'none',
                  cursor: 'pointer',
                  maxWidth: '220px',
                }}
              >
                {bosses.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.canonical_name} (Lv.{b.level})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Encounter Profile & Readiness Section (Responsive 2-Column Grid) */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
              gap: '1rem',
            }}
          >
            {/* 1. Boss Profile Card */}
            <div
              className="glass-card"
              style={{
                borderRadius: '12px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.85rem',
                border: '1px solid var(--border-color)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
                <div
                  style={{
                    position: 'relative',
                    width: '60px',
                    height: '60px',
                    borderRadius: '12px',
                    overflow: 'hidden',
                    background: 'rgba(0, 0, 0, 0.4)',
                    flexShrink: 0,
                    border: '1px solid var(--border-color-hover)',
                  }}
                >
                  <img
                    src={selectedBossProfile.icon_path}
                    alt={selectedBossProfile.canonical_name}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                  {selectedBossProfile.badge_icon_path && (
                    <img
                      src={selectedBossProfile.badge_icon_path}
                      alt="Alpha Badge"
                      style={{
                        position: 'absolute',
                        top: '2px',
                        right: '2px',
                        width: '20px',
                        height: '20px',
                      }}
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  )}
                </div>

                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap' }}>
                    <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                      {selectedBossProfile.canonical_name}
                    </h3>
                    <span
                      style={{
                        fontSize: '0.72rem',
                        fontWeight: '700',
                        padding: '0.15rem 0.5rem',
                        borderRadius: '4px',
                        background: 'rgba(99, 102, 241, 0.2)',
                        color: '#c7d2fe',
                        border: '1px solid rgba(99, 102, 241, 0.3)',
                      }}
                    >
                      {selectedBossProfile.category}
                    </span>
                  </div>
                  {selectedBossProfile.title && (
                    <div style={{ fontSize: '0.82rem', color: 'var(--accent-gold)', marginTop: '0.15rem', fontStyle: 'italic' }}>
                      "{selectedBossProfile.title}"
                    </div>
                  )}
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                    📍 {selectedBossProfile.location}
                  </div>
                </div>
              </div>

              {/* Stat Metrics Row */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(90px, 1fr))',
                  gap: '0.5rem',
                  background: 'rgba(0, 0, 0, 0.25)',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  border: '1px solid rgba(255, 255, 255, 0.04)',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Level</div>
                  <div style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--accent-gold)' }}>
                    Lv.{selectedBossProfile.level}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Encounter HP</div>
                  <div style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                    {selectedBossProfile.hp ? selectedBossProfile.hp.toLocaleString() : 'N/A'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Arena Limit</div>
                  <div style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                    {selectedBossProfile.time_limit_sec ? `${selectedBossProfile.time_limit_sec / 60}m` : 'Open World'}
                  </div>
                </div>
                {selectedBossProfile.required_dps && (
                  <div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Min Required DPS</div>
                    <div style={{ fontSize: '1.05rem', fontWeight: '700', color: '#f87171' }}>
                      {Math.round(selectedBossProfile.required_dps)} DPS
                    </div>
                  </div>
                )}
              </div>

              {/* Elements & Super-Effective Weaknesses */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', fontSize: '0.82rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span style={{ color: 'var(--text-secondary)', width: '90px' }}>Boss Elements:</span>
                  {(selectedBossProfile.elements || []).map((elem) => (
                    <span
                      key={elem}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        background: 'rgba(255, 255, 255, 0.06)',
                        padding: '0.15rem 0.45rem',
                        borderRadius: '4px',
                        fontSize: '0.78rem',
                      }}
                    >
                      <img
                        src={getElementIconUrl(elem)}
                        alt={elem}
                        style={{ width: '13px', height: '13px' }}
                        onError={(e) => {
                          e.target.style.display = 'none';
                        }}
                      />
                      {elem}
                    </span>
                  ))}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span style={{ color: 'var(--text-secondary)', width: '90px' }}>Super-Effective:</span>
                  {(selectedBossProfile.weaknesses || []).map((w) => (
                    <span
                      key={w}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        background: 'rgba(16, 185, 129, 0.15)',
                        border: '1px solid rgba(16, 185, 129, 0.3)',
                        color: '#34d399',
                        padding: '0.15rem 0.45rem',
                        borderRadius: '4px',
                        fontSize: '0.78rem',
                        fontWeight: '700',
                      }}
                    >
                      <img
                        src={getElementIconUrl(w)}
                        alt={w}
                        style={{ width: '13px', height: '13px' }}
                        onError={(e) => {
                          e.target.style.display = 'none';
                        }}
                      />
                      {w} (2.0x STAB)
                    </span>
                  ))}
                </div>
              </div>

              {/* Guaranteed Boss Drops */}
              {selectedBossProfile.drops?.length > 0 && (
                <div>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: '0.3rem',
                    }}
                  >
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Guaranteed Drops & Farming Materials ({selectedBossProfile.drops.length}):
                    </span>
                    {selectedBossProfile.drops.length > 1 && (
                      <button
                        onClick={() => setShowAllDrops(!showAllDrops)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--accent-gold)',
                          fontSize: '0.72rem',
                          cursor: 'pointer',
                          padding: '0.1rem 0.3rem',
                          textDecoration: 'underline',
                        }}
                      >
                        {showAllDrops ? 'Show dropdown' : `Show all (${selectedBossProfile.drops.length})`}
                      </button>
                    )}
                  </div>

                  {!showAllDrops ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <select
                        value={selectedDropIdx}
                        onChange={(e) => setSelectedDropIdx(Number(e.target.value))}
                        style={{
                          flex: 1,
                          background: 'rgba(234, 179, 8, 0.12)',
                          border: '1px solid rgba(234, 179, 8, 0.3)',
                          borderRadius: '6px',
                          color: '#fef08a',
                          padding: '0.35rem 0.6rem',
                          fontSize: '0.76rem',
                          fontWeight: '600',
                          outline: 'none',
                          cursor: 'pointer',
                        }}
                      >
                        {selectedBossProfile.drops.map((drop, dIdx) => (
                          <option key={dIdx} value={dIdx} style={{ background: '#1e293b', color: '#fef08a' }}>
                            🎁 {drop.item_name} ({drop.drop_rate}% • x{drop.min_qty}-{drop.max_qty})
                          </option>
                        ))}
                      </select>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                      {selectedBossProfile.drops.map((drop, dIdx) => (
                        <span
                          key={dIdx}
                          style={{
                            background: 'rgba(234, 179, 8, 0.12)',
                            border: '1px solid rgba(234, 179, 8, 0.25)',
                            color: '#fef08a',
                            padding: '0.15rem 0.45rem',
                            borderRadius: '4px',
                            fontSize: '0.74rem',
                            fontWeight: '500',
                          }}
                        >
                          🎁 {drop.item_name} ({drop.drop_rate}% • x{drop.min_qty}-{drop.max_qty})
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Arena Tactics */}
              {selectedBossProfile.tactics && (
                <div
                  style={{
                    background: 'rgba(251, 191, 36, 0.08)',
                    borderLeft: '3px solid var(--accent-gold)',
                    borderRadius: '4px',
                    padding: '0.55rem 0.75rem',
                    fontSize: '0.8rem',
                    color: 'var(--text-primary)',
                    lineHeight: '1.4',
                  }}
                >
                  💡 <strong>Arena Tactics:</strong> {selectedBossProfile.tactics}
                </div>
              )}
            </div>

            {/* 2. Encounter Readiness Verdict Card */}
            <div
              className="glass-card"
              style={{
                borderRadius: '12px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.85rem',
                border: `1px solid ${statusCfg ? statusCfg.border : 'var(--border-color)'}`,
                boxShadow: statusCfg ? `0 0 20px ${statusCfg.bg}` : 'none',
                position: 'relative',
              }}
            >
              {loadingParty && (
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    background: 'rgba(9, 13, 22, 0.8)',
                    borderRadius: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 10,
                    fontSize: '0.9rem',
                    color: 'var(--text-secondary)',
                  }}
                >
                  Evaluating Save File Roster...
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '1.25rem' }}>{statusCfg ? statusCfg.icon : '⏱️'}</span>
                  <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                    Encounter Readiness Verdict
                  </h3>
                </div>

                {readiness && (
                  <span
                    style={{
                      background: statusCfg.badgeBg,
                      border: `1px solid ${statusCfg.border}`,
                      color: statusCfg.text,
                      padding: '0.25rem 0.7rem',
                      borderRadius: '6px',
                      fontWeight: '700',
                      fontSize: '0.82rem',
                      letterSpacing: '0.04em',
                    }}
                  >
                    {readiness.status}
                  </span>
                )}
              </div>

              {readiness ? (
                <>
                  {/* Readiness Metrics */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
                      gap: '0.6rem',
                      background: 'rgba(0, 0, 0, 0.25)',
                      padding: '0.75rem',
                      borderRadius: '8px',
                      border: '1px solid rgba(255, 255, 255, 0.04)',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Highest Pal Level</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                        Lv.{readiness.highest_pal_level}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Level Gap</div>
                      <div
                        style={{
                          fontSize: '1.1rem',
                          fontWeight: '700',
                          color: readiness.level_gap >= 0 ? '#34d399' : '#f87171',
                        }}
                      >
                        {readiness.level_gap > 0 ? `+${readiness.level_gap}` : readiness.level_gap}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Avg Party Level</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                        Lv.{readiness.average_party_level}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Super-Effective Counters</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: '700', color: '#a78bfa' }}>
                        {readiness.counter_elements_in_party} / 5
                      </div>
                    </div>
                  </div>

                  {/* Verdict Text Box */}
                  <div
                    style={{
                      background: statusCfg.bg,
                      border: `1px solid ${statusCfg.border}`,
                      borderRadius: '8px',
                      padding: '0.75rem',
                      color: statusCfg.text,
                      fontSize: '0.85rem',
                      lineHeight: '1.45',
                    }}
                  >
                    <strong>Verdict:</strong> {readiness.verdict}
                  </div>

                  {/* Timer Note */}
                  {readiness.timer_note && (
                    <div
                      style={{
                        background: 'rgba(0, 0, 0, 0.3)',
                        borderRadius: '8px',
                        padding: '0.65rem 0.8rem',
                        border: '1px solid var(--border-color)',
                        fontSize: '0.78rem',
                        color: 'var(--text-secondary)',
                        lineHeight: '1.4',
                      }}
                    >
                      ⏱️ <strong>Timer Analysis:</strong> {readiness.timer_note}
                    </div>
                  )}
                </>
              ) : partyError ? (
                <div
                  style={{
                    background: 'rgba(239, 68, 68, 0.15)',
                    border: '1px solid #ef4444',
                    borderRadius: '8px',
                    padding: '1rem',
                    color: '#f87171',
                    fontSize: '0.85rem',
                  }}
                >
                  ⚠️ {partyError}
                </div>
              ) : (
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', padding: '1rem 0' }}>
                  Loading encounter analysis...
                </div>
              )}
            </div>
          </div>

          {/* Recommended 5-Pal Counter Party Section (Comfortable Responsive Layout) */}
          <div
            className="glass-card"
            style={{
              borderRadius: '12px',
              padding: '1.25rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
              border: '1px solid var(--border-color)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                  Recommended 5-Pal Counter Party
                </h3>
                <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Optimally assembled from your saved Palbox, active party, and base camp roster.
                </p>
              </div>

              {recommendation?.recommended_party?.length > 0 && (
                <span
                  style={{
                    fontSize: '0.78rem',
                    color: 'var(--accent-green)',
                    background: 'rgba(16, 185, 129, 0.15)',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    padding: '0.25rem 0.65rem',
                    borderRadius: '6px',
                    fontWeight: '600',
                  }}
                >
                  ✓ Full 5-Slot Counter Party Assembled
                </span>
              )}
            </div>

            {loadingParty ? (
              <div style={{ padding: '3.5rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                Assembling optimal counter team from your live save roster...
              </div>
            ) : !recommendation || !recommendation.recommended_party || recommendation.recommended_party.length === 0 ? (
              <div
                style={{
                  padding: '2.5rem',
                  textAlign: 'center',
                  color: 'var(--text-secondary)',
                  background: 'rgba(0, 0, 0, 0.15)',
                  borderRadius: '8px',
                  border: '1px dashed var(--border-color)',
                }}
              >
                {partyError ? (
                  <span style={{ color: '#f87171' }}>{partyError}</span>
                ) : (
                  'No candidate Pals found in your save file. Catch or level up Pals to form a counter party.'
                )}
              </div>
            ) : (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.75rem',
                }}
              >
                {recommendation.recommended_party.map((pal, idx) => {
                  const elements = (pal.element || '').split('/').filter(Boolean);
                  return (
                    <div
                      key={`${pal.species}-${idx}`}
                      className="glass-card"
                      style={{
                        borderRadius: '10px',
                        padding: '0.85rem 1.15rem',
                        border: idx === 0 ? '1px solid rgba(99, 102, 241, 0.4)' : '1px solid var(--border-color)',
                        background: idx === 0 ? 'rgba(99, 102, 241, 0.05)' : 'rgba(255, 255, 255, 0.02)',
                        boxShadow: idx === 0 ? '0 0 16px rgba(99, 102, 241, 0.12)' : 'none',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.65rem',
                      }}
                    >
                      {/* Horizontal Row: 4 Main Columns */}
                      <div
                        style={{
                          display: 'flex',
                          flexWrap: 'wrap',
                          gap: '1rem',
                          alignItems: 'flex-start',
                        }}
                      >
                        {/* Col 1: Slot & Identity */}
                        <div style={{ flex: '0 0 230px', display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span
                              style={{
                                fontSize: '0.72rem',
                                fontWeight: '700',
                                background: idx === 0 ? 'var(--primary-gradient)' : 'rgba(255, 255, 255, 0.1)',
                                color: '#ffffff',
                                padding: '0.12rem 0.5rem',
                                borderRadius: '4px',
                              }}
                            >
                              Slot #{idx + 1} {idx === 0 ? '• Lead' : ''}
                            </span>
                            <span
                              style={{
                                color: pal.gender === 'Male' ? '#38bdf8' : pal.gender === 'Female' ? '#f472b6' : 'var(--text-secondary)',
                                fontWeight: '700',
                                fontSize: '0.95rem',
                              }}
                              title={`Gender: ${pal.gender}`}
                            >
                              {pal.gender === 'Male' ? '♂' : pal.gender === 'Female' ? '♀' : ''}
                            </span>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                            <div
                              style={{
                                width: '46px',
                                height: '46px',
                                borderRadius: '8px',
                                overflow: 'hidden',
                                background: 'rgba(0, 0, 0, 0.4)',
                                flexShrink: 0,
                                border: '1px solid var(--border-color-hover)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                              }}
                            >
                              {pal.icon_path ? (
                                <img
                                  src={pal.icon_path}
                                  alt={pal.species}
                                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                  onError={(e) => {
                                    e.target.style.display = 'none';
                                  }}
                                />
                              ) : (
                                <span style={{ fontSize: '1.4rem' }}>🐾</span>
                              )}
                            </div>

                            <div style={{ minWidth: 0, flex: 1 }}>
                              <div
                                style={{
                                  fontWeight: '700',
                                  fontSize: '0.95rem',
                                  color: 'var(--text-primary)',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                }}
                              >
                                {pal.species}
                              </div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginTop: '0.15rem', flexWrap: 'wrap' }}>
                                <span style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--accent-gold)' }}>
                                  Lv.{pal.level}
                                </span>
                                <span
                                  style={{
                                    fontSize: '0.68rem',
                                    color: 'var(--text-secondary)',
                                    background: 'rgba(255, 255, 255, 0.05)',
                                    padding: '0.05rem 0.35rem',
                                    borderRadius: '3px',
                                  }}
                                >
                                  {pal.rank}
                                </span>
                                <span
                                  style={{
                                    fontSize: '0.68rem',
                                    color: '#93c5fd',
                                    background: 'rgba(59, 130, 246, 0.15)',
                                    padding: '0.05rem 0.35rem',
                                    borderRadius: '3px',
                                  }}
                                >
                                  {pal.location}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Col 2: Role & Elements / IVs */}
                        <div style={{ flex: '0 0 210px', display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            Combat Role
                          </div>
                          <div
                            style={{
                              fontSize: '0.78rem',
                              fontWeight: '600',
                              color: idx === 0 ? '#a78bfa' : 'var(--text-primary)',
                              background: 'rgba(255, 255, 255, 0.04)',
                              padding: '0.25rem 0.5rem',
                              borderRadius: '4px',
                              border: '1px solid rgba(255, 255, 255, 0.06)',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                            title={pal.role}
                          >
                            {pal.role}
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', marginTop: '0.1rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                              {elements.map((elem) => (
                                <span
                                  key={elem}
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '0.2rem',
                                    fontSize: '0.72rem',
                                    background: 'rgba(255, 255, 255, 0.05)',
                                    padding: '0.1rem 0.35rem',
                                    borderRadius: '3px',
                                  }}
                                >
                                  <img
                                    src={getElementIconUrl(elem)}
                                    alt={elem}
                                    style={{ width: '12px', height: '12px' }}
                                    onError={(e) => {
                                      e.target.style.display = 'none';
                                    }}
                                  />
                                  {elem}
                                </span>
                              ))}
                            </div>

                            <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                              IVs: <strong style={{ color: 'var(--text-primary)' }}>{pal.ivs}</strong>
                            </span>
                          </div>
                        </div>

                        {/* Col 3: Current Passives */}
                        <div style={{ flex: '0 0 240px', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            Current Passives
                          </div>
                          <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                            {(pal.passives || []).map((passName, pIdx) => {
                              const cleanName = typeof passName === 'string' ? passName : passName?.name || 'Passive';
                              if (cleanName === 'None') {
                                return (
                                  <span key={pIdx} style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                                    None
                                  </span>
                                );
                              }
                              return (
                                <PassiveBadge
                                  key={`${cleanName}-${pIdx}`}
                                  skill={cleanName}
                                  size="small"
                                />
                              );
                            })}
                          </div>
                          {pal.optimal_passives?.length > 0 && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', flexWrap: 'wrap', marginTop: '0.2rem' }}>
                              <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Target:</span>
                              {pal.optimal_passives.map((optPass) => (
                                <span
                                  key={optPass}
                                  style={{
                                    fontSize: '0.64rem',
                                    background: 'rgba(255, 255, 255, 0.04)',
                                    border: '1px solid rgba(255, 255, 255, 0.08)',
                                    borderRadius: '3px',
                                    padding: '0.05rem 0.3rem',
                                    color: 'var(--text-secondary)',
                                  }}
                                >
                                  {optPass}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Col 4: Tailored Combat Moveset (3 Wazas) */}
                        <div style={{ flex: '1 1 340px', display: 'flex', flexDirection: 'column', gap: '0.35rem', minWidth: '280px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                              Tailored Moveset (3 Wazas)
                            </span>
                            <span style={{ fontSize: '0.66rem', color: 'var(--accent-gold)' }}>
                              Optimal vs {selectedBossProfile.canonical_name}
                            </span>
                          </div>

                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '0.4rem' }}>
                            {(pal.recommended_waza || []).map((waza, wIdx) => {
                              const isEquipped = waza.status === 'equipped';
                              const isLearned = waza.status === 'learned';
                              const isFruit = waza.status === 'fruit';

                              const badgeBg = isEquipped
                                ? 'rgba(16, 185, 129, 0.15)'
                                : isLearned
                                ? 'rgba(59, 130, 246, 0.15)'
                                : isFruit
                                ? 'rgba(168, 85, 247, 0.18)'
                                : 'rgba(255, 255, 255, 0.05)';

                              const badgeBorder = isEquipped
                                ? '#10b981'
                                : isLearned
                                ? '#3b82f6'
                                : isFruit
                                ? '#a855f7'
                                : 'var(--border-color)';

                              const badgeColor = isEquipped
                                ? '#34d399'
                                : isLearned
                                ? '#93c5fd'
                                : isFruit
                                ? '#d8b4fe'
                                : 'var(--text-secondary)';

                              return (
                                <div
                                  key={`${waza.name}-${wIdx}`}
                                  style={{
                                    display: 'flex',
                                    flexDirection: 'column',
                                    justifyContent: 'space-between',
                                    background: 'rgba(0, 0, 0, 0.35)',
                                    padding: '0.35rem 0.55rem',
                                    borderRadius: '6px',
                                    border: '1px solid rgba(255, 255, 255, 0.05)',
                                    fontSize: '0.75rem',
                                    gap: '0.25rem',
                                  }}
                                >
                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.35rem' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', minWidth: 0 }}>
                                      <img
                                        src={getElementIconUrl(waza.element)}
                                        alt={waza.element}
                                        style={{ width: '12px', height: '12px', flexShrink: 0 }}
                                        onError={(e) => {
                                          e.target.style.display = 'none';
                                        }}
                                      />
                                      <span
                                        style={{
                                          fontWeight: '600',
                                          color: 'var(--text-primary)',
                                          overflow: 'hidden',
                                          textOverflow: 'ellipsis',
                                          whiteSpace: 'nowrap',
                                          fontSize: '0.75rem',
                                        }}
                                        title={waza.name}
                                      >
                                        {waza.name}
                                      </span>
                                    </div>
                                    <span
                                      style={{
                                        fontSize: '0.62rem',
                                        fontWeight: '600',
                                        background: badgeBg,
                                        border: `1px solid ${badgeBorder}`,
                                        color: badgeColor,
                                        padding: '0.08rem 0.35rem',
                                        borderRadius: '3px',
                                        flexShrink: 0,
                                      }}
                                    >
                                      {waza.status_badge}
                                    </span>
                                  </div>

                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-secondary)' }}>
                                    <span>Pwr: <strong style={{ color: 'var(--accent-gold)' }}>{waza.power}</strong></span>
                                    <span>CT: {waza.ct}</span>
                                  </div>
                                </div>
                              );
                            })}
                          </div>

                          {/* Equipped Active Slots Overview */}
                          {pal.equip_waza?.length > 0 && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginTop: '0.15rem', flexWrap: 'wrap' }}>
                              <span style={{ fontSize: '0.64rem', color: 'var(--text-secondary)' }}>Active slots:</span>
                              {pal.equip_waza.map((eq, eqIdx) => (
                                <span
                                  key={eqIdx}
                                  style={{
                                    fontSize: '0.64rem',
                                    color: 'var(--text-primary)',
                                    background: 'rgba(255, 255, 255, 0.05)',
                                    padding: '0.04rem 0.3rem',
                                    borderRadius: '3px',
                                  }}
                                >
                                  {eq.name}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
