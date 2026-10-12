import React, { useState, useEffect, useMemo } from 'react';
import { PalInstanceTooltip } from './common/PalInstanceTooltip';
import { PassiveBadge } from './common/PassiveBadge';
import { getElementIconUrl } from '../constants/gameData';
import { exportToJson } from '../utils/exportJson';

const ACTION_CONFIGS = {
  keep_core: {
    bg: 'rgba(59, 130, 246, 0.2)',
    color: '#60a5fa',
    border: 'rgba(59, 130, 246, 0.45)',
    label: '🛡️ KEEP (CORE)',
  },
  keep_breeding: {
    bg: 'rgba(168, 85, 247, 0.2)',
    color: '#c084fc',
    border: 'rgba(168, 85, 247, 0.45)',
    label: '🧬 BREEDING',
  },
  condense: {
    bg: 'rgba(251, 191, 36, 0.2)',
    color: '#fbbf24',
    border: 'rgba(251, 191, 36, 0.45)',
    label: '⭐ CONDENSE',
  },
  butcher_sell: {
    bg: 'rgba(239, 68, 68, 0.2)',
    color: '#f87171',
    border: 'rgba(239, 68, 68, 0.45)',
    label: '🥩 BUTCHER',
  },
};

export default function PalboxCleanerView({ pals = [], setSelectedPal, worldId, saveLoaded }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters & Controls
  const [actionFilter, setActionFilter] = useState('all'); // 'all' | 'keep_core' | 'keep_breeding' | 'condense' | 'butcher_sell'
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTargetSpecies, setSelectedTargetSpecies] = useState('');
  const [isGroupedBySpecies, setIsGroupedBySpecies] = useState(true);
  const [expandedSpecies, setExpandedSpecies] = useState(new Set());
  const [sortCol, setSortCol] = useState('score');
  const [sortDesc, setSortDesc] = useState(true);
  const [displayLimit, setDisplayLimit] = useState(80);

  const fetchCleanupData = () => {
    setLoading(true);
    setError(null);
    fetch('/api/save/palbox-cleanup')
      .then(async (res) => {
        if (!res.ok) {
          let msg = `Server returned status ${res.status}`;
          try {
            const errData = await res.json();
            if (errData?.detail) msg = errData.detail;
            else if (errData?.error) msg = errData.error;
          } catch {
            // ignore
          }
          throw new Error(msg);
        }
        return res.json();
      })
      .then((json) => {
        setData(json);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching palbox cleanup data:', err);
        setError(err.message || 'Failed to fetch palbox cleanup recommendations.');
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchCleanupData();
  }, [worldId, saveLoaded]);

  // Master pal lookup map for quick access
  const masterPalMap = useMemo(() => {
    const map = new Map();
    (pals || []).forEach((p) => {
      if (p.internal_name) map.set(p.internal_name.toLowerCase(), p);
      if (p.id) map.set(p.id.toLowerCase(), p);
      if (p.display_name) map.set(p.display_name.toLowerCase(), p);
    });
    return map;
  }, [pals]);

  const resolveMasterPal = (inst) => {
    const key = (inst.display_name || inst.species || inst.character_id || '').toLowerCase();
    return masterPalMap.get(key) || null;
  };

  // Filter and sort roster
  const filteredRoster = useMemo(() => {
    if (!data?.roster) return [];
    let list = [...data.roster];

    // Filter by action
    if (actionFilter !== 'all') {
      list = list.filter((p) => p.audit_action === actionFilter);
    }

    // Filter by target species (e.g. from selecting a Condense Target)
    if (selectedTargetSpecies) {
      list = list.filter(
        (p) => (p.display_name || p.species || '').toLowerCase() === selectedTargetSpecies.toLowerCase()
      );
    }

    // Filter by search query (species name or passive skill name or reason)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter((p) => {
        const sp = (p.display_name || p.species || '').toLowerCase();
        const pNames = (p.passives || []).map((t) => (t.name || t.id || t || '').toLowerCase());
        const reason = (p.audit_reason || '').toLowerCase();
        return sp.includes(q) || pNames.some((pn) => pn.includes(q)) || reason.includes(q);
      });
    }

    // Sorting
    list.sort((a, b) => {
      let diff = 0;
      if (sortCol === 'score') diff = (b.audit_score || 0) - (a.audit_score || 0);
      else if (sortCol === 'level') diff = (b.level || 1) - (a.level || 1);
      else if (sortCol === 'rank') diff = (b.rank || 0) - (a.rank || 0);
      else if (sortCol === 'current_speed') diff = (b.current_speed || 0) - (a.current_speed || 0);
      else if (sortCol === 'gender') diff = (a.gender || '').localeCompare(b.gender || '');
      else if (sortCol === 'audit_action') {
        const order = { keep_core: 0, keep_breeding: 1, condense: 2, butcher_sell: 3 };
        diff = (order[a.audit_action] ?? 4) - (order[b.audit_action] ?? 4);
      } else if (sortCol === 'display_name') {
        const nameA = a.display_name || a.species || '';
        const nameB = b.display_name || b.species || '';
        diff = nameA.localeCompare(nameB);
      }
      return sortDesc ? diff : -diff;
    });

    return list;
  }, [data, actionFilter, selectedTargetSpecies, searchQuery, sortCol, sortDesc]);

  // Grouped data structure by species (matching World Pals Explorer grouped view)
  const groupedSpeciesData = useMemo(() => {
    if (!isGroupedBySpecies) return [];
    const groups = new Map();
    filteredRoster.forEach((pal) => {
      const sp = pal.display_name || pal.species || 'Unknown';
      if (!groups.has(sp)) {
        groups.set(sp, []);
      }
      groups.get(sp).push(pal);
    });

    return Array.from(groups.entries()).map(([speciesName, instances]) => {
      const masterPal = masterPalMap.get(speciesName.toLowerCase());
      const palIcon =
        instances[0]?.icon_path ||
        instances[0]?.icon_url ||
        masterPal?.icon_path ||
        masterPal?.icon_url ||
        `/assets/pals/icons/${speciesName.toLowerCase().replace(/ /g, '_')}.png`;

      const elements = [
        instances[0]?.element_1 || masterPal?.element_1,
        instances[0]?.element_2 || masterPal?.element_2,
      ].filter(Boolean);

      const keepCoreCount = instances.filter((i) => i.audit_action === 'keep_core').length;
      const keepBreedingCount = instances.filter((i) => i.audit_action === 'keep_breeding').length;
      const condenseCount = instances.filter((i) => i.audit_action === 'condense').length;
      const butcherCount = instances.filter((i) => i.audit_action === 'butcher_sell').length;

      const maxRank = Math.max(...instances.map((i) => i.rank || 0), 0);
      const maxHp = Math.max(...instances.map((i) => i.ivs?.hp ?? i.iv_hp ?? 0), 0);
      const maxAtk = Math.max(...instances.map((i) => i.ivs?.melee ?? i.iv_melee ?? i.iv_attack ?? 0), 0);
      const maxDef = Math.max(...instances.map((i) => i.ivs?.defense ?? i.iv_defense ?? 0), 0);

      const maleCount = instances.filter((i) => i.gender === 'Male').length;
      const femaleCount = instances.filter((i) => i.gender === 'Female').length;

      return {
        speciesName,
        instances,
        masterPal,
        palIcon,
        elements,
        keepCoreCount,
        keepBreedingCount,
        condenseCount,
        butcherCount,
        maxRank,
        maxHp,
        maxAtk,
        maxDef,
        maleCount,
        femaleCount,
      };
    });
  }, [filteredRoster, isGroupedBySpecies, masterPalMap]);

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDesc(!sortDesc);
    } else {
      setSortCol(col);
      setSortDesc(true);
    }
  };

  const toggleSpecies = (speciesName) => {
    setExpandedSpecies((prev) => {
      const next = new Set(prev);
      if (next.has(speciesName)) {
        next.delete(speciesName);
      } else {
        next.add(speciesName);
      }
      return next;
    });
  };

  const expandAll = () => {
    setExpandedSpecies(new Set(groupedSpeciesData.map((g) => g.speciesName)));
  };

  const collapseAll = () => {
    setExpandedSpecies(new Set());
  };

  const handleExportChecklist = () => {
    if (!data?.roster) return;
    const discardList = data.roster
      .filter((p) => p.audit_action === 'condense' || p.audit_action === 'butcher_sell')
      .map((p) => ({
        instance_id: p.instance_id,
        species: p.display_name || p.species,
        level: p.level,
        gender: p.gender,
        action: p.audit_action_label,
        reason: p.audit_reason,
        passives: (p.passives || []).map((t) => t.name || t.id || t),
      }));

    exportToJson(discardList, `palbox_cleanup_fodder_${new Date().toISOString().slice(0, 10)}.json`);
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
        <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>🧹</div>
        <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.4rem', fontSize: '1.1rem' }}>Auditing Palbox Instances...</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
          Evaluating 2+2 breeding synergies, investment floors, trait deduplication, and species preservation.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: '2.5rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
        <div style={{ color: 'var(--accent-red, #ef4444)', fontSize: '1rem', fontWeight: 600 }}>⚠️ {error}</div>
        <button onClick={fetchCleanupData} className="btn btn-primary" style={{ padding: '0.4rem 1rem', fontSize: '0.82rem' }}>
          🔄 Retry Palbox Audit
        </button>
      </div>
    );
  }

  if (!data || data.total_evaluated === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-secondary)' }}>No Palbox instances found in the active world save.</p>
        <button onClick={fetchCleanupData} className="btn btn-secondary" style={{ marginTop: '0.75rem', padding: '0.4rem 1rem' }}>
          🔄 Check Again
        </button>
      </div>
    );
  }

  const {
    total_evaluated,
    keep_core_count,
    keep_breeding_count,
    condense_fodder_count,
    butcher_sell_count,
    freeable_slots,
    condense_targets = [],
  } = data;

  const palboxCapacity = 960;

  // Render a single Pal table row (shared between Flat and Grouped Tier 2 view)
  const renderPalRow = (pi, isNested = false, masterPalOverride = null) => {
    const masterPal = masterPalOverride || resolveMasterPal(pi);
    const palName = pi.display_name || pi.species || 'Unknown';
    const palIcon =
      pi.icon_path ||
      pi.icon_url ||
      masterPal?.icon_path ||
      masterPal?.icon_url ||
      (palName ? `/assets/pals/icons/${palName.toLowerCase().replace(/ /g, '_')}.png` : null);

    const rankStars = pi.rank && pi.rank > 0 ? '★'.repeat(pi.rank) : '-';
    const genderIcon = pi.gender === 'Female' ? '♀' : pi.gender === 'Male' ? '♂' : '?';
    const genderColor = pi.gender === 'Female' ? '#f472b6' : pi.gender === 'Male' ? '#60a5fa' : '#94a3b8';
    const speedVal = pi.current_speed || masterPal?.ride_sprint_speed || masterPal?.walk_speed || '-';

    const ivHp = pi.ivs?.hp ?? pi.iv_hp ?? '-';
    const ivAtk = pi.ivs?.melee ?? pi.iv_melee ?? pi.iv_attack ?? '-';
    const ivDef = pi.ivs?.defense ?? pi.iv_defense ?? '-';
    const ivDisplay = `${ivHp}/${ivAtk}/${ivDef}`;

    const elements = [pi.element_1 || masterPal?.element_1, pi.element_2 || masterPal?.element_2].filter(Boolean);
    const actCfg = ACTION_CONFIGS[pi.audit_action] || ACTION_CONFIGS.condense;

    return (
      <tr
        key={pi.instance_id}
        className={isNested ? 'instance-sub-row' : ''}
        style={{
          borderBottom: '1px solid rgba(255,255,255,0.04)',
          transition: 'background 0.12s ease',
        }}
      >
        {/* 1. Species + Thumbnail */}
        <td
          style={{
            padding: isNested ? '0.35rem 0.4rem 0.35rem 1.4rem' : '0.35rem 0.4rem',
            borderLeft: isNested ? '4px solid rgba(129, 140, 248, 0.5)' : undefined,
            overflow: 'hidden',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', minWidth: 0, overflow: 'hidden' }}>
            {isNested && <span style={{ color: 'var(--text-secondary)', fontSize: '0.68rem', flexShrink: 0 }}>└</span>}
            {palIcon ? (
              <img
                src={palIcon}
                alt={palName}
                style={{ width: '22px', height: '22px', borderRadius: '4px', objectFit: 'contain', background: 'rgba(0,0,0,0.3)', flexShrink: 0 }}
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
            ) : (
              <span style={{ fontSize: '0.9rem', flexShrink: 0 }}>🐾</span>
            )}
            <PalInstanceTooltip instance={pi} masterPal={masterPal}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', minWidth: 0, overflow: 'hidden' }}>
                <span
                  style={{
                    fontWeight: 600,
                    color: 'var(--accent-gold)',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    minWidth: 0,
                    flexShrink: 1,
                  }}
                  onClick={() => setSelectedPal && masterPal && setSelectedPal(masterPal)}
                >
                  {palName}
                </span>
                {pi.is_species_keeper && (
                  <span
                    style={{
                      fontSize: '0.58rem',
                      background: 'rgba(99, 102, 241, 0.3)',
                      color: '#a5b4fc',
                      border: '1px solid rgba(129, 140, 248, 0.4)',
                      padding: '0.02rem 0.22rem',
                      borderRadius: '3px',
                      fontWeight: 700,
                      whiteSpace: 'nowrap',
                      flexShrink: 0,
                    }}
                    title="Guaranteed species floor: Best preserved specimen of this species"
                  >
                    👑 Keeper
                  </span>
                )}
              </div>
            </PalInstanceTooltip>
          </div>
        </td>

        {/* 2. Level */}
        <td style={{ padding: '0.35rem 0.25rem', fontSize: '0.78rem', color: 'var(--text-primary)' }}>
          Lv.{pi.level || 1}
        </td>

        {/* 3. Sex */}
        <td style={{ padding: '0.35rem 0.25rem', textAlign: 'center' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '18px',
              height: '18px',
              borderRadius: '50%',
              border: `1px solid ${genderColor}`,
              color: genderColor,
              fontSize: '0.75rem',
              fontWeight: 700,
            }}
          >
            {genderIcon}
          </span>
        </td>

        {/* 4. Rank */}
        <td style={{ padding: '0.35rem 0.25rem', textAlign: 'center', color: '#fbbf24', fontSize: '0.75rem', letterSpacing: '1px' }}>
          {rankStars}
        </td>

        {/* 5. Recommended Action */}
        <td style={{ padding: '0.35rem 0.35rem' }}>
          <span
            className="badge"
            style={{
              background: actCfg.bg,
              color: actCfg.color,
              border: `1px solid ${actCfg.border}`,
              fontSize: '0.64rem',
              padding: '0.12rem 0.42rem',
              borderRadius: '4px',
              fontWeight: 700,
              whiteSpace: 'nowrap',
              cursor: 'help',
            }}
            title={pi.audit_reason ? `Action: ${actCfg.label}\nReason: ${pi.audit_reason}` : actCfg.label}
          >
            {actCfg.label}
          </span>
        </td>

        {/* 7. Speed */}
        <td style={{ padding: '0.35rem 0.25rem', fontSize: '0.75rem', whiteSpace: 'nowrap', color: 'var(--text-primary)' }}>
          {speedVal !== '-' ? `➔ ${speedVal}` : '-'}
        </td>

        {/* 8. IVs (H/A/D) */}
        <td style={{ padding: '0.35rem 0.25rem', fontSize: '0.72rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
          <span style={{ color: ivHp === 100 ? 'var(--accent-gold)' : 'inherit', fontWeight: ivHp === 100 ? 700 : 500 }}>
            {ivHp}
          </span>
          /
          <span style={{ color: ivAtk === 100 ? 'var(--accent-gold)' : 'inherit', fontWeight: ivAtk === 100 ? 700 : 500 }}>
            {ivAtk}
          </span>
          /
          <span style={{ color: ivDef === 100 ? 'var(--accent-gold)' : 'inherit', fontWeight: ivDef === 100 ? 700 : 500 }}>
            {ivDef}
          </span>
        </td>

        {/* 9. Location */}
        <td style={{ padding: '0.35rem 0.25rem', textAlign: 'center' }}>
          <span className="badge badge-palbox" style={{ fontSize: '0.6rem', padding: '0.08rem 0.3rem', borderRadius: '4px', whiteSpace: 'nowrap' }}>
            📦 Box
          </span>
        </td>

        {/* 10. Passives */}
        <td style={{ padding: '0.35rem 0.4rem' }}>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '0.15rem 0.3rem',
              alignItems: 'center',
            }}
          >
            {(pi.passives || []).length > 0 ? (
              (pi.passives || []).map((pass, pIdx) => {
                const pName = typeof pass === 'string' ? pass : pass.name || pass.id;
                return <PassiveBadge key={pIdx} skill={pName} size="xs" />;
              })
            ) : (
              <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>No Passives</span>
            )}
          </div>
        </td>

        {/* 11. Element */}
        <td style={{ padding: '0.35rem 0.25rem', textAlign: 'center' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.2rem' }}>
            {elements.map((el) => (
              <img
                key={el}
                src={getElementIconUrl(el)}
                alt={el}
                title={el}
                style={{ width: '18px', height: '18px', objectFit: 'contain' }}
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
            ))}
          </div>
        </td>
      </tr>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      {/* ── Compact Controls & KPI Toolbar (Matching Image 1 Density) ── */}
      <div style={{ flexShrink: 0, marginBottom: '0.45rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        
        {/* Row 1: KPI Action Filter Pills + Export & Refresh */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.4rem' }}>
          {/* Action Filter Pills with embedded counts */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', flexWrap: 'wrap' }}>
            {/* Palbox Load Badge */}
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.3rem',
                background: 'rgba(0,0,0,0.4)',
                border: '1px solid var(--border-color)',
                padding: '0.25rem 0.55rem',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 600,
                color: 'var(--text-secondary)',
              }}
              title="Current Palbox capacity load"
            >
              <span>📦 Palbox:</span>
              <span style={{ color: total_evaluated >= 950 ? 'var(--accent-red)' : 'var(--text-primary)', fontWeight: 700 }}>
                {total_evaluated}/{palboxCapacity}
              </span>
            </div>

            {/* Freeable Slots Highlight Badge */}
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.3rem',
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.4)',
                padding: '0.25rem 0.55rem',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 700,
                color: '#34d399',
              }}
              title="Total slots safe to reclaim via condensing or butchering"
            >
              <span>🧹 Freeable:</span>
              <span>+{freeable_slots} ({Math.round((freeable_slots / total_evaluated) * 100)}%)</span>
            </div>

            <span style={{ color: 'rgba(255,255,255,0.15)', margin: '0 0.1rem' }}>|</span>

            {/* Interactive Action Tabs */}
            {[
              {
                id: 'all',
                label: 'All',
                count: total_evaluated,
                color: 'var(--text-primary)',
                tooltip: 'All Palbox instances across all triage categories',
              },
              {
                id: 'keep_core',
                label: '🛡️ Core Keepers',
                count: keep_core_count,
                color: '#60a5fa',
                tooltip: 'Investment Protected & Living Paldex: 1★–4★ condensed, soul-boosted, high-level (Lv15+), and guaranteed best specimen of every caught species (👑 Keeper)',
              },
              {
                id: 'keep_breeding',
                label: '🧬 Breeding Stock',
                count: keep_breeding_count,
                color: '#c084fc',
                tooltip: 'Breeding Heritage: Clean 2+2 synergistic pairs (e.g. Musclehead + Heavyweight, Artisan + Work Slave), rare single-trait carriers, and power-tier gender bridges',
              },
              {
                id: 'condense',
                label: '⭐ Condense Fodder',
                count: condense_fodder_count,
                color: 'var(--accent-gold)',
                tooltip: 'Safe Sacrifice Pool: Surplus duplicate Pals carrying no unique traits or investments, designated for star condensation into your Keepers',
              },
              {
                id: 'butcher_sell',
                label: '🥩 Butcher / Sell',
                count: butcher_sell_count,
                color: '#f87171',
                tooltip: 'Surplus Discard: Low-IV duplicates with negative traits (Slacker, Coward) or cluttered passive pools beyond condensation requirements',
              },
            ].map((tab) => {
              const active = actionFilter === tab.id && !selectedTargetSpecies;
              return (
                <button
                  key={tab.id}
                  title={tab.tooltip}
                  onClick={() => {
                    setActionFilter(tab.id);
                    setSelectedTargetSpecies('');
                  }}
                  style={{
                    background: active ? 'var(--primary-gradient)' : 'rgba(255,255,255,0.06)',
                    color: active ? '#fff' : tab.color,
                    border: '1px solid ' + (active ? 'transparent' : 'rgba(255,255,255,0.1)'),
                    padding: '0.25rem 0.55rem',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    fontWeight: active ? 700 : 600,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                  }}
                >
                  <span>{tab.label}</span>
                  <span
                    style={{
                      background: active ? 'rgba(0,0,0,0.25)' : 'rgba(0,0,0,0.3)',
                      padding: '0.05rem 0.3rem',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                    }}
                  >
                    {tab.count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Action Buttons (Right) */}
          <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
            <button
              onClick={handleExportChecklist}
              className="btn btn-secondary"
              title="Download JSON list of all Pals marked for condensing or butchering"
              style={{ fontSize: '0.74rem', padding: '0.25rem 0.6rem' }}
            >
              📥 Export Fodder
            </button>
            <button
              onClick={fetchCleanupData}
              className="btn btn-primary"
              style={{ fontSize: '0.74rem', padding: '0.25rem 0.6rem' }}
            >
              🔄 Refresh
            </button>
          </div>
        </div>

        {/* Row 2: Top Condensation Candidate Buttons (Cleanly wrapped, zero horizontal scrollbar) */}
        {condense_targets.length > 0 && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              flexWrap: 'wrap',
              background: 'rgba(0,0,0,0.25)',
              borderRadius: '6px',
              padding: '0.3rem 0.55rem',
              border: '1px solid rgba(251, 191, 36, 0.25)',
            }}
          >
            <span style={{ fontSize: '0.73rem', fontWeight: 700, color: 'var(--accent-gold)', whiteSpace: 'nowrap' }}>
              ⭐ Condense Targets:
            </span>
            {condense_targets.slice(0, 12).map((ct) => {
              const isSelected = selectedTargetSpecies.toLowerCase() === ct.species.toLowerCase();
              return (
                <button
                  key={ct.species}
                  onClick={() => {
                    if (isSelected) {
                      setSelectedTargetSpecies('');
                    } else {
                      setSelectedTargetSpecies(ct.species);
                      setActionFilter('all');
                      setExpandedSpecies((prev) => new Set([...prev, ct.species]));
                    }
                  }}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                    background: isSelected ? 'var(--accent-gold)' : 'rgba(255,255,255,0.06)',
                    color: isSelected ? '#000' : 'var(--text-primary)',
                    border: '1px solid ' + (isSelected ? 'var(--accent-gold)' : 'rgba(251, 191, 36, 0.35)'),
                    padding: '0.15rem 0.45rem',
                    borderRadius: '12px',
                    fontSize: '0.73rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  title={`Safe sacrifice pool: 1 Keeper is preserved and ${ct.fodder_available} duplicates are ready to condense`}
                >
                  <span>{ct.species}</span>
                  <span
                    style={{
                      background: isSelected ? 'rgba(0,0,0,0.25)' : 'rgba(251, 191, 36, 0.25)',
                      color: isSelected ? '#000' : 'var(--accent-gold)',
                      padding: '0.02rem 0.28rem',
                      borderRadius: '8px',
                      fontSize: '0.67rem',
                      fontWeight: 700,
                    }}
                  >
                    +{ct.fodder_available}
                  </span>
                </button>
              );
            })}
            {selectedTargetSpecies && (
              <button
                onClick={() => setSelectedTargetSpecies('')}
                style={{
                  background: 'rgba(255,255,255,0.12)',
                  border: '1px solid rgba(255,255,255,0.2)',
                  color: 'var(--text-primary)',
                  borderRadius: '12px',
                  padding: '0.15rem 0.45rem',
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                ✕ Clear ({selectedTargetSpecies})
              </button>
            )}
          </div>
        )}

        {/* Row 3: Search Bar + Group/Flat View Toggle + Expand/Collapse + Sorter */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.4rem' }}>
          {/* Search bar */}
          <input
            type="text"
            placeholder="🔍 Search Pal, species, trait, or reason..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: '0.28rem 0.65rem',
              fontSize: '0.78rem',
              flex: 1,
              maxWidth: '340px',
              borderRadius: '6px',
              background: 'rgba(0,0,0,0.35)',
              border: '1px solid var(--border-color)',
            }}
          />

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
            {/* Expand / Collapse All (Grouped Mode Only) */}
            {isGroupedBySpecies && (
              <div style={{ display: 'inline-flex', gap: '0.25rem' }}>
                <button
                  className="btn"
                  onClick={expandAll}
                  style={{
                    fontSize: '0.72rem',
                    padding: '0.22rem 0.45rem',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-color)',
                    color: 'var(--text-secondary)',
                    borderRadius: '6px',
                    cursor: 'pointer',
                  }}
                  title="Expand all species groups"
                >
                  ➕ Expand All
                </button>
                <button
                  className="btn"
                  onClick={collapseAll}
                  style={{
                    fontSize: '0.72rem',
                    padding: '0.22rem 0.45rem',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-color)',
                    color: 'var(--text-secondary)',
                    borderRadius: '6px',
                    cursor: 'pointer',
                  }}
                  title="Collapse all species groups"
                >
                  ➖ Collapse All
                </button>
              </div>
            )}

            {/* Grouped / Flat View Toggle (Matching World Pals Explorer) */}
            <div style={{ display: 'inline-flex', background: 'rgba(0, 0, 0, 0.4)', borderRadius: '8px', padding: '2px', border: '1px solid var(--border-color)' }}>
              <button
                onClick={() => setIsGroupedBySpecies(true)}
                style={{
                  fontSize: '0.74rem',
                  padding: '0.22rem 0.55rem',
                  background: isGroupedBySpecies ? 'rgba(99, 102, 241, 0.4)' : 'transparent',
                  border: 'none',
                  color: isGroupedBySpecies ? '#fff' : 'var(--text-secondary)',
                  fontWeight: isGroupedBySpecies ? 700 : 500,
                  borderRadius: '6px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                📁 Grouped ({groupedSpeciesData.length})
              </button>
              <button
                onClick={() => setIsGroupedBySpecies(false)}
                style={{
                  fontSize: '0.74rem',
                  padding: '0.22rem 0.55rem',
                  background: !isGroupedBySpecies ? 'rgba(99, 102, 241, 0.4)' : 'transparent',
                  border: 'none',
                  color: !isGroupedBySpecies ? '#fff' : 'var(--text-secondary)',
                  fontWeight: !isGroupedBySpecies ? 700 : 500,
                  borderRadius: '6px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                📄 Flat ({filteredRoster.length})
              </button>
            </div>

            {/* Sort Dropdown */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Sort:</span>
              <select
                value={sortCol}
                onChange={(e) => {
                  setSortCol(e.target.value);
                  setSortDesc(true);
                }}
                style={{
                  padding: '0.22rem 0.5rem',
                  fontSize: '0.74rem',
                  borderRadius: '6px',
                  background: 'rgba(0,0,0,0.35)',
                  border: '1px solid var(--border-color)',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  width: 'auto',
                }}
              >
                <option value="score">Score (High → Low)</option>
                <option value="level">Level</option>
                <option value="rank">Rank</option>
                <option value="audit_action">Action Priority</option>
                <option value="display_name">Species (A-Z)</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* ── Main Table View (Exact World Pals Table Layout & Styles) ── */}
      <div
        className="glass-card table-container"
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          overflowX: 'hidden',
          padding: 0,
          marginBottom: '0.5rem',
        }}
      >
        <table style={{ width: '100%', tableLayout: 'fixed' }}>
          <thead>
            <tr>
              <th onClick={() => handleSort('display_name')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.35rem 0.4rem', width: '17%' }}>
                Species{sortCol === 'display_name' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
              <th onClick={() => handleSort('level')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.35rem 0.25rem', width: '5%' }}>
                Level{sortCol === 'level' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
              <th onClick={() => handleSort('gender')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.35rem 0.25rem', width: '3.5%' }}>
                Sex{sortCol === 'gender' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
              <th onClick={() => handleSort('rank')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.35rem 0.25rem', width: '4%' }}>
                Rank{sortCol === 'rank' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
              <th onClick={() => handleSort('audit_action')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.35rem 0.35rem', width: '11%' }}>
                Action{sortCol === 'audit_action' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
              <th onClick={() => handleSort('current_speed')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.35rem 0.25rem', width: '5.5%' }}>
                Speed{sortCol === 'current_speed' ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
              <th style={{ whiteSpace: 'nowrap', padding: '0.35rem 0.25rem', width: '8.5%' }}>
                IVs (H/A/D)
              </th>
              <th style={{ whiteSpace: 'nowrap', padding: '0.35rem 0.25rem', width: '6.5%', textAlign: 'center' }}>
                Location
              </th>
              <th style={{ padding: '0.35rem 0.4rem', width: '33%' }}>
                Passives
              </th>
              <th style={{ whiteSpace: 'nowrap', padding: '0.35rem 0.25rem', width: '6%', textAlign: 'center' }}>
                Element
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredRoster.length === 0 ? (
              <tr>
                <td colSpan={10} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  No Pals match the active filter criteria.
                </td>
              </tr>
            ) : isGroupedBySpecies ? (
              /* ========================================================================= */
              /* 2-TIER GROUPED BY SPECIES VIEW (Exact Match to Image 1)                   */
              /* ========================================================================= */
              groupedSpeciesData.map((group) => {
                const isExpanded = expandedSpecies.has(group.speciesName);
                const count = group.instances.length;
                const palName = group.speciesName;
                const masterPal = group.masterPal;
                const palIcon = group.palIcon;

                return (
                  <React.Fragment key={`group-${palName}`}>
                    {/* Tier 1: Species Group Header Row */}
                    <tr
                      onClick={() => toggleSpecies(palName)}
                      className={`species-group-row ${isExpanded ? 'expanded' : ''}`}
                      style={{
                        background: isExpanded ? 'rgba(99, 102, 241, 0.16)' : 'rgba(15, 23, 42, 0.65)',
                        cursor: 'pointer',
                        userSelect: 'none',
                        transition: 'background 0.15s ease',
                      }}
                    >
                      {/* Species & Expand Indicator */}
                      <td style={{ padding: '0.45rem 0.5rem', borderLeft: isExpanded ? '4px solid #818cf8' : '4px solid transparent' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              width: '18px',
                              height: '18px',
                              borderRadius: '4px',
                              background: isExpanded ? '#818cf8' : 'rgba(255,255,255,0.08)',
                              color: isExpanded ? '#0f172a' : 'var(--text-secondary)',
                              fontSize: '0.7rem',
                              fontWeight: 900,
                              flexShrink: 0,
                            }}
                          >
                            {isExpanded ? '▼' : '▶'}
                          </span>
                          {palIcon && (
                            <img
                              src={palIcon}
                              alt={palName}
                              style={{ width: '24px', height: '24px', borderRadius: '4px', objectFit: 'contain', flexShrink: 0 }}
                              onError={(e) => {
                                e.target.style.display = 'none';
                              }}
                            />
                          )}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', overflow: 'hidden' }}>
                            <span
                              style={{ fontWeight: 800, color: 'var(--accent-gold)', fontSize: '0.84rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
                              onClick={(e) => {
                                if (setSelectedPal && masterPal) {
                                  e.stopPropagation();
                                  setSelectedPal(masterPal);
                                }
                              }}
                            >
                              {palName}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Count Badge */}
                      <td style={{ padding: '0.45rem 0.25rem' }}>
                        <span style={{ background: 'rgba(56, 189, 248, 0.2)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.4)', padding: '0.1rem 0.4rem', borderRadius: '10px', fontWeight: 800, fontSize: '0.72rem', whiteSpace: 'nowrap' }}>
                          {count} {count === 1 ? 'Pal' : 'Pals'}
                        </span>
                      </td>

                      {/* Sex summary */}
                      <td style={{ padding: '0.45rem 0.25rem', textAlign: 'center', fontSize: '0.72rem', whiteSpace: 'nowrap' }}>
                        <span style={{ color: '#60a5fa', fontWeight: 700 }}>♂{group.maleCount}</span>
                        {' / '}
                        <span style={{ color: '#f472b6', fontWeight: 700 }}>♀{group.femaleCount}</span>
                      </td>

                      {/* Top Rank */}
                      <td style={{ padding: '0.45rem 0.25rem', textAlign: 'center', color: '#fbbf24', fontSize: '0.74rem' }}>
                        {group.maxRank > 0 ? '★'.repeat(group.maxRank) : '-'}
                      </td>

                      {/* Triage Summary */}
                      <td style={{ padding: '0.45rem 0.35rem' }}>
                        <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                          {group.keepCoreCount + group.keepBreedingCount > 0 && (
                            <span style={{ fontSize: '0.62rem', padding: '0.04rem 0.25rem', background: 'rgba(59, 130, 246, 0.2)', color: '#93c5fd', border: '1px solid rgba(59, 130, 246, 0.35)', borderRadius: '4px', fontWeight: 700 }}>
                              🛡️ {group.keepCoreCount + group.keepBreedingCount} Keep
                            </span>
                          )}
                          {group.condenseCount > 0 && (
                            <span style={{ fontSize: '0.62rem', padding: '0.04rem 0.25rem', background: 'rgba(251, 191, 36, 0.2)', color: '#fbbf24', border: '1px solid rgba(251, 191, 36, 0.35)', borderRadius: '4px', fontWeight: 700 }}>
                              ⭐ {group.condenseCount} Fodder
                            </span>
                          )}
                          {group.butcherCount > 0 && (
                            <span style={{ fontSize: '0.62rem', padding: '0.04rem 0.25rem', background: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5', border: '1px solid rgba(239, 68, 68, 0.35)', borderRadius: '4px', fontWeight: 700 }}>
                              🥩 {group.butcherCount} Discard
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Base Speed */}
                      <td style={{ padding: '0.45rem 0.25rem', fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                        {masterPal?.run_speed || masterPal?.speed || group.instances[0]?.base_speed || '-'}
                      </td>

                      {/* IVs Best */}
                      <td style={{ padding: '0.45rem 0.25rem', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                        Best: {group.maxHp}/{group.maxAtk}/{group.maxDef}%
                      </td>

                      {/* Location summary */}
                      <td style={{ padding: '0.45rem 0.35rem' }}>
                        <span className="badge badge-palbox" style={{ fontSize: '0.58rem', padding: '0.04rem 0.25rem' }}>
                          Box
                        </span>
                      </td>

                      {/* Top Passives / Inherent Skill Preview */}
                      <td style={{ padding: '0.45rem 0.4rem' }}>
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                          ✨ Inherent Skill ({count} instances in Palbox)
                        </span>
                      </td>

                      {/* Elements */}
                      <td style={{ padding: '0.45rem 0.25rem', textAlign: 'center' }}>
                        <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem' }}>
                          {group.elements.map((el) => (
                            <img
                              key={el}
                              src={getElementIconUrl(el)}
                              alt={el}
                              title={el}
                              style={{ width: '18px', height: '18px', objectFit: 'contain' }}
                              onError={(e) => {
                                e.target.style.display = 'none';
                              }}
                            />
                          ))}
                        </div>
                      </td>
                    </tr>

                    {/* Tier 2: Child Pal Instance Rows */}
                    {isExpanded &&
                      group.instances.map((pi) => renderPalRow(pi, true, masterPal))}
                  </React.Fragment>
                );
              })
            ) : (
              /* ========================================================================= */
              /* FLAT LIST VIEW (Identical Dense Rows)                                     */
              /* ========================================================================= */
              filteredRoster.slice(0, displayLimit).map((pi) => renderPalRow(pi, false))
            )}
          </tbody>
        </table>

        {/* Flat List Pagination Button */}
        {!isGroupedBySpecies && filteredRoster.length > displayLimit && (
          <div style={{ textAlign: 'center', padding: '0.75rem' }}>
            <button
              onClick={() => setDisplayLimit((prev) => prev + 80)}
              className="btn btn-secondary"
              style={{ fontSize: '0.75rem', padding: '0.35rem 1rem' }}
            >
              Show More (+80 Pals)
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
