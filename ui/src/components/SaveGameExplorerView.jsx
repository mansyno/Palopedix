import React, { useState, useMemo } from 'react';
import { useTableSort } from '../hooks/useTableSort';
import { PassiveBadge } from './common/PassiveBadge';
import { PalInstanceTooltip } from './common/PalInstanceTooltip';
import {
  PalFilterModal,
  PARTNER_GROUP_OPTIONS,
  LOCATION_OPTIONS,
  GENDER_OPTIONS,
  RARITY_OPTIONS,
  GEAR_STATUS_OPTIONS,
} from './common/PalFilterModal';

const SHORT_CATEGORY_NAMES = {
  flying_mount: 'Fly',
  ground_mount: 'Mount',
  swimming_mount: 'Swim',
  glider: 'Glider',
  ranch_producer: 'Ranch',
  player_element_infusion: 'Infuse',
  player_combat_buffer: 'Buff',
  party_pal_buffer: 'Party',
  heavy_artillery: 'Cannon',
  coop_attacker: 'Co-Op',
  healer_lifesteal: 'Heal',
  carrying_capacity: 'Weight',
  drop_loot_booster: 'Loot',
  resource_gathering: 'Gather',
  breeding_egg_booster: 'Breed',
  fishing_helper: 'Fish',
  exploration_survival: 'Radar',
  no_active_skill: '',
};

const ELEMENT_ICON_MAP = {
  Neutral: '/assets/elements/Normal.png',
  Normal: '/assets/elements/Normal.png',
  Fire: '/assets/elements/Fire.png',
  Water: '/assets/elements/Water.png',
  Grass: '/assets/elements/Grass.png',
  Leaf: '/assets/elements/Grass.png',
  Electric: '/assets/elements/Electric.png',
  Electricity: '/assets/elements/Electric.png',
  Ice: '/assets/elements/Ice.png',
  Ground: '/assets/elements/Ground.png',
  Earth: '/assets/elements/Ground.png',
  Dark: '/assets/elements/Dark.png',
  Dragon: '/assets/elements/Dragon.png',
};

const DEFAULT_FILTERS = {
  partnerGroup: '',
  location: '',
  species: '',
  gender: '',
  minLevel: '',
  rarity: '',
  gearStatus: '',
  passives: [],
  elements: [],
};

export function SaveGameExplorerView({
  instances = [],
  pals = [],
  saveLoaded,
  setSelectedPal,
}) {
  // Advanced Filter Modal State
  const [isFilterModalOpen, setIsFilterModalOpen] = useState(false);

  // 2-Tier Species Grouping State
  const [isGroupedBySpecies, setIsGroupedBySpecies] = useState(true);
  const [expandedSpecies, setExpandedSpecies] = useState(new Set());

  // Undo / Redo Filter History Stack
  const [filterHistory, setFilterHistory] = useState([DEFAULT_FILTERS]);
  const [historyIndex, setHistoryIndex] = useState(0);

  // Current active filter state from history
  const activeFilters = filterHistory[historyIndex] || DEFAULT_FILTERS;

  // Push new filter state snapshot to history (capped to 50 states)
  const MAX_HISTORY = 50;
  const pushFilterState = (newFilters) => {
    const currentSerialized = JSON.stringify(activeFilters);
    const newSerialized = JSON.stringify(newFilters);
    if (currentSerialized === newSerialized) return;

    setFilterHistory(prev => {
      let nextHistory = prev.slice(0, historyIndex + 1).concat([newFilters]);
      if (nextHistory.length > MAX_HISTORY) {
        nextHistory = nextHistory.slice(nextHistory.length - MAX_HISTORY);
      }
      return nextHistory;
    });
    setHistoryIndex(prev => Math.min(prev + 1, MAX_HISTORY - 1));
  };

  const handleUndo = () => {
    if (historyIndex > 0) {
      setHistoryIndex(prev => prev - 1);
    }
  };

  const handleRedo = () => {
    if (historyIndex < filterHistory.length - 1) {
      setHistoryIndex(prev => prev + 1);
    }
  };

  const handleClearHistory = () => {
    setFilterHistory([activeFilters]);
    setHistoryIndex(0);
  };

  const toggleSpecies = (speciesName) => {
    setExpandedSpecies(prev => {
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
    const allSpecies = new Set(groupedSpeciesData.map(g => g.speciesName));
    setExpandedSpecies(allSpecies);
  };

  const collapseAll = () => {
    setExpandedSpecies(new Set());
  };

  const activeModalFiltersCount = useMemo(() => {
    return (
      (activeFilters.partnerGroup ? 1 : 0) +
      (activeFilters.location ? 1 : 0) +
      (activeFilters.species ? 1 : 0) +
      (activeFilters.gender ? 1 : 0) +
      (activeFilters.minLevel ? 1 : 0) +
      (activeFilters.rarity ? 1 : 0) +
      (activeFilters.gearStatus ? 1 : 0) +
      (activeFilters.passives?.length || 0) +
      (activeFilters.elements?.length || 0)
    );
  }, [activeFilters]);

  const speciesOptions = useMemo(() => {
    const counts = new Map();
    instances.forEach(inst => {
      const name = inst.display_name || inst.species;
      if (name) {
        counts.set(name, (counts.get(name) || 0) + 1);
      }
    });
    return Array.from(counts.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([name, count]) => ({ name, count }));
  }, [instances]);

  const filteredInstances = useMemo(() => {
    return instances.filter(pi => {
      // Location
      if (activeFilters.location && pi.location !== activeFilters.location) return false;

      // Gender
      if (activeFilters.gender && pi.gender !== activeFilters.gender) return false;

      // Min Level
      if (activeFilters.minLevel && (pi.level || 0) < parseInt(activeFilters.minLevel, 10)) return false;

      // Species
      if (activeFilters.species && (pi.display_name || pi.species || '').toLowerCase() !== activeFilters.species.toLowerCase()) return false;

      // Partner Group
      if (activeFilters.partnerGroup) {
        const cats = (pi.partner_skill_categories && pi.partner_skill_categories.length > 0)
          ? pi.partner_skill_categories
          : (pals.find(p => p.display_name?.toLowerCase() === (pi.display_name || '').toLowerCase())?.partner_skill_categories || []);
        if (!cats.some(c => c.id === activeFilters.partnerGroup || c.name?.toLowerCase() === activeFilters.partnerGroup.toLowerCase())) {
          return false;
        }
      }

      // Rarity Tier
      if (activeFilters.rarity) {
        const palRarity = pi.rarity ?? (pals.find(p => p.display_name?.toLowerCase() === (pi.display_name || '').toLowerCase())?.rarity);
        if (activeFilters.rarity === 'legendary' && palRarity !== 20) return false;
        if (activeFilters.rarity === 'boss' && palRarity !== 10) return false;
        if (activeFilters.rarity === 'rare' && (palRarity < 7 || palRarity > 9)) return false;
        if (activeFilters.rarity === 'mid' && (palRarity < 4 || palRarity > 6)) return false;
        if (activeFilters.rarity === 'common' && (palRarity < 1 || palRarity > 3)) return false;
        if (!isNaN(parseInt(activeFilters.rarity, 10)) && palRarity !== parseInt(activeFilters.rarity, 10)) return false;
      }

      // Pal Gear Status Filter
      if (activeFilters.gearStatus) {
        const g = pi.gear || pi.partner_skill?.gear;
        if (activeFilters.gearStatus === 'crafted') {
          if (!g || !g.requires_gear || !g.is_crafted) return false;
        } else if (activeFilters.gearStatus === 'not_crafted') {
          if (!g || !g.requires_gear || g.is_crafted) return false;
        } else if (activeFilters.gearStatus === 'no_gear') {
          if (g && g.requires_gear) return false;
        } else if (activeFilters.gearStatus === 'requires_gear') {
          if (!g || !g.requires_gear) return false;
        }
      }

      // Elemental Type Filter (Order-agnostic: matches Type1 or Type2 dynamically)
      if (activeFilters.elements && activeFilters.elements.length > 0) {
        const masterPal = pals.find(p => 
          (p.internal_name && (p.internal_name === pi.character_id || p.internal_name === pi.character_id_raw || p.internal_name === pi.species)) ||
          (p.id && (p.id === pi.character_id || p.id === pi.character_id_raw || p.id === pi.species)) ||
          (p.display_name && p.display_name.toLowerCase() === (pi.display_name || '').toLowerCase())
        );
        const pElem1 = (pi.element_1 || masterPal?.element_1 || '').toLowerCase().trim();
        const pElem2 = (pi.element_2 || masterPal?.element_2 || '').toLowerCase().trim();
        const palElemSet = new Set([pElem1, pElem2].filter(Boolean));

        if (activeFilters.elements.length === 1) {
          const target = activeFilters.elements[0].toLowerCase().trim();
          if (!palElemSet.has(target)) return false;
        } else if (activeFilters.elements.length === 2) {
          const target1 = activeFilters.elements[0].toLowerCase().trim();
          const target2 = activeFilters.elements[1].toLowerCase().trim();
          if (!palElemSet.has(target1) || !palElemSet.has(target2)) return false;
        }
      }

      // Passive Skills Combination Filter (Must possess ALL selected passives in any slot order)
      if (activeFilters.passives && activeFilters.passives.length > 0) {
        const palPassives = pi.passives || [];
        const palPassiveIdentifiers = new Set();
        palPassives.forEach(p => {
          if (typeof p === 'string') {
            palPassiveIdentifiers.add(p.toLowerCase().trim());
          } else if (p && typeof p === 'object') {
            if (p.name) palPassiveIdentifiers.add(p.name.toLowerCase().trim());
            if (p.id) palPassiveIdentifiers.add(p.id.toLowerCase().trim());
            if (p.id) palPassiveIdentifiers.add(p.id.replace(/^Passive_/i, '').replace(/_/g, ' ').toLowerCase().trim());
          }
        });

        const hasAllSelectedPassives = activeFilters.passives.every(sel => {
          const sName = (typeof sel === 'string' ? sel : (sel.name || sel.id || '')).toLowerCase().trim();
          const sId = (typeof sel === 'object' && sel.id ? sel.id : '').toLowerCase().trim();
          const sClean = sId ? sId.replace(/^Passive_/i, '').replace(/_/g, ' ').toLowerCase().trim() : '';
          return palPassiveIdentifiers.has(sName) || (sId && palPassiveIdentifiers.has(sId)) || (sClean && palPassiveIdentifiers.has(sClean));
        });

        if (!hasAllSelectedPassives) return false;
      }

      return true;
    });
  }, [instances, activeFilters, pals]);

  const {
    sortedData: sortedInstances,
    sortCol,
    sortDesc,
    handleSort,
  } = useTableSort(filteredInstances, 'level', true);

  // Group instances by species
  const groupedSpeciesData = useMemo(() => {
    const groups = new Map();
    for (const inst of filteredInstances) {
      const name = inst.display_name || inst.species || 'Unknown Pal';
      if (!groups.has(name)) {
        const masterPal = pals.find(p => 
          (p.internal_name && (p.internal_name === inst.character_id || p.internal_name === inst.character_id_raw || p.internal_name === inst.species)) ||
          (p.id && (p.id === inst.character_id || p.id === inst.character_id_raw || p.id === inst.species)) ||
          (p.display_name && p.display_name.toLowerCase() === name.toLowerCase())
        );

        const palIcon = inst.icon_url || masterPal?.icon_url || (name ? `/assets/pals/icons/${name.toLowerCase().replace(/ /g, '_')}.png` : null);
        const cats = (inst.partner_skill_categories && inst.partner_skill_categories.length > 0)
          ? inst.partner_skill_categories
          : (masterPal?.partner_skill_categories || []);

        groups.set(name, {
          speciesName: name,
          masterPal,
          palIcon,
          paldex_number: masterPal?.paldex_number || inst.paldex_number || 9999,
          elements: [inst.element_1 || masterPal?.element_1, inst.element_2 || masterPal?.element_2].filter(Boolean),
          partnerCategories: cats,
          gear: inst.gear || inst.partner_skill?.gear || masterPal?.gear,
          instances: [],
        });
      }
      groups.get(name).instances.push(inst);
    }

    // Sort grouped species
    const sorted = Array.from(groups.values()).sort((a, b) => {
      if (sortCol === 'display_name') {
        return sortDesc ? b.speciesName.localeCompare(a.speciesName) : a.speciesName.localeCompare(b.speciesName);
      }
      if (sortCol === 'level') {
        const maxA = Math.max(...a.instances.map(i => i.level || 0), 0);
        const maxB = Math.max(...b.instances.map(i => i.level || 0), 0);
        return sortDesc ? maxB - maxA : maxA - maxB;
      }
      if (sortCol === 'rank') {
        const maxA = Math.max(...a.instances.map(i => i.rank || 0), 0);
        const maxB = Math.max(...b.instances.map(i => i.rank || 0), 0);
        return sortDesc ? maxB - maxA : maxA - maxB;
      }
      return a.paldex_number - b.paldex_number;
    });

    return sorted;
  }, [filteredInstances, pals, sortCol, sortDesc]);

  const chipBadgeStyle = {
    fontSize: '0.7rem',
    padding: '0.12rem 0.45rem',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.35rem',
    borderRadius: '6px',
    fontWeight: 600,
  };

  const chipCloseBtnStyle = {
    background: 'transparent',
    border: 'none',
    color: '#fca5a5',
    cursor: 'pointer',
    padding: 0,
    fontSize: '0.72rem',
    fontWeight: 700,
    lineHeight: 1,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      {/* Top Filter Bar & Active Filter Chips */}
      {saveLoaded && (
        <div style={{ flexShrink: 0, marginBottom: '0.35rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap', marginBottom: activeModalFiltersCount > 0 ? '0.3rem' : 0 }}>
            <button
              className="btn"
              onClick={() => setIsFilterModalOpen(true)}
              style={{
                fontSize: '0.78rem',
                padding: '0.3rem 0.75rem',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                background: activeModalFiltersCount > 0 ? 'rgba(99, 102, 241, 0.3)' : 'rgba(255, 255, 255, 0.08)',
                border: activeModalFiltersCount > 0 ? '1px solid #818cf8' : '1px solid var(--border-color)',
                color: activeModalFiltersCount > 0 ? '#f8fafc' : 'var(--text-primary)',
                fontWeight: 700,
                borderRadius: '8px',
                boxShadow: activeModalFiltersCount > 0 ? '0 0 10px rgba(99, 102, 241, 0.3)' : 'none',
                cursor: 'pointer'
              }}
            >
              <span>⚡ Filter</span>
              {activeModalFiltersCount > 0 && (
                <span style={{ background: '#34d399', color: '#064e3b', fontWeight: 800, fontSize: '0.68rem', padding: '0.02rem 0.35rem', borderRadius: '10px' }}>
                  {activeModalFiltersCount}
                </span>
              )}
            </button>

            {/* ↶ Undo / Back Button */}
            <button
              className="btn"
              onClick={handleUndo}
              disabled={historyIndex <= 0}
              style={{
                fontSize: '0.76rem',
                padding: '0.3rem 0.55rem',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem',
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid var(--border-color)',
                color: historyIndex > 0 ? 'var(--text-primary)' : 'var(--text-muted)',
                opacity: historyIndex > 0 ? 1 : 0.35,
                cursor: historyIndex > 0 ? 'pointer' : 'not-allowed',
                borderRadius: '8px',
                transition: 'all 0.15s ease'
              }}
              title="Previous Filter (Undo)"
            >
              <span>↶</span>
              <span>Back</span>
            </button>

            {/* ↷ Redo / Forward Button */}
            <button
              className="btn"
              onClick={handleRedo}
              disabled={historyIndex >= filterHistory.length - 1}
              style={{
                fontSize: '0.76rem',
                padding: '0.3rem 0.55rem',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem',
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid var(--border-color)',
                color: historyIndex < filterHistory.length - 1 ? 'var(--text-primary)' : 'var(--text-muted)',
                opacity: historyIndex < filterHistory.length - 1 ? 1 : 0.35,
                cursor: historyIndex < filterHistory.length - 1 ? 'pointer' : 'not-allowed',
                borderRadius: '8px',
                transition: 'all 0.15s ease'
              }}
              title="Next Filter (Redo)"
            >
              <span>Forward</span>
              <span>↷</span>
            </button>

            {/* Clear History Button */}
            {filterHistory.length > 1 && (
              <button
                className="btn"
                onClick={handleClearHistory}
                style={{
                  fontSize: '0.74rem',
                  padding: '0.3rem 0.5rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.25)',
                  color: '#fca5a5',
                  cursor: 'pointer',
                  borderRadius: '8px',
                  transition: 'all 0.15s ease'
                }}
                title="Clear filter history stack (retains current selection)"
              >
                <span>🗑️</span>
                <span>Clear History</span>
              </button>
            )}

            {/* View Mode & Grouping Controls */}
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              {isGroupedBySpecies && (
                <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'center' }}>
                  <button
                    className="btn"
                    onClick={expandAll}
                    style={{
                      fontSize: '0.72rem',
                      padding: '0.25rem 0.5rem',
                      background: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid var(--border-color)',
                      color: 'var(--text-secondary)',
                      borderRadius: '6px',
                      cursor: 'pointer'
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
                      padding: '0.25rem 0.5rem',
                      background: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid var(--border-color)',
                      color: 'var(--text-secondary)',
                      borderRadius: '6px',
                      cursor: 'pointer'
                    }}
                    title="Collapse all species groups"
                  >
                    ➖ Collapse All
                  </button>
                </div>
              )}

              {/* Group / Flat Toggle */}
              <div style={{ display: 'inline-flex', background: 'rgba(0, 0, 0, 0.4)', borderRadius: '8px', padding: '2px', border: '1px solid var(--border-color)' }}>
                <button
                  onClick={() => setIsGroupedBySpecies(true)}
                  style={{
                    fontSize: '0.74rem',
                    padding: '0.25rem 0.6rem',
                    background: isGroupedBySpecies ? 'rgba(99, 102, 241, 0.4)' : 'transparent',
                    border: 'none',
                    color: isGroupedBySpecies ? '#fff' : 'var(--text-secondary)',
                    fontWeight: isGroupedBySpecies ? 700 : 500,
                    borderRadius: '6px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  📁 Grouped ({groupedSpeciesData.length})
                </button>
                <button
                  onClick={() => setIsGroupedBySpecies(false)}
                  style={{
                    fontSize: '0.74rem',
                    padding: '0.25rem 0.6rem',
                    background: !isGroupedBySpecies ? 'rgba(99, 102, 241, 0.4)' : 'transparent',
                    border: 'none',
                    color: !isGroupedBySpecies ? '#fff' : 'var(--text-secondary)',
                    fontWeight: !isGroupedBySpecies ? 700 : 500,
                    borderRadius: '6px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  📄 Flat ({filteredInstances.length})
                </button>
              </div>
            </div>
          </div>

          {/* Active Filters Removable Chips Bar */}
          {activeModalFiltersCount > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', alignItems: 'center', padding: '0.3rem 0.65rem', background: 'rgba(99, 102, 241, 0.08)', borderRadius: '8px', border: '1px solid rgba(99, 102, 241, 0.2)' }}>
              <span style={{ fontSize: '0.72rem', color: 'var(--accent-gold)', fontWeight: 700, marginRight: '0.2rem' }}>
                Active Filters ({filteredInstances.length} matching):
              </span>

              {/* Partner Group Chip */}
              {activeFilters.partnerGroup && (
                <span className="badge" style={{ ...chipBadgeStyle, background: 'rgba(234, 179, 8, 0.2)', border: '1px solid rgba(234, 179, 8, 0.4)', color: '#fef08a' }}>
                  <span>{PARTNER_GROUP_OPTIONS.find(o => o.value === activeFilters.partnerGroup)?.label || `Group: ${activeFilters.partnerGroup}`}</span>
                  <button onClick={() => pushFilterState({ ...activeFilters, partnerGroup: '' })} style={chipCloseBtnStyle} title="Remove filter">✕</button>
                </span>
              )}

              {/* Location Chip */}
              {activeFilters.location && (
                <span className="badge" style={{ ...chipBadgeStyle, background: 'rgba(56, 189, 248, 0.2)', border: '1px solid rgba(56, 189, 248, 0.4)', color: '#bae6fd' }}>
                  <span>📍 {LOCATION_OPTIONS.find(o => o.value === activeFilters.location)?.label || activeFilters.location}</span>
                  <button onClick={() => pushFilterState({ ...activeFilters, location: '' })} style={chipCloseBtnStyle} title="Remove filter">✕</button>
                </span>
              )}

              {/* Species Chip */}
              {activeFilters.species && (
                <span className="badge" style={{ ...chipBadgeStyle, background: 'rgba(168, 85, 247, 0.2)', border: '1px solid rgba(168, 85, 247, 0.4)', color: '#e9d5ff' }}>
                  <span>🐾 {activeFilters.species}</span>
                  <button onClick={() => pushFilterState({ ...activeFilters, species: '' })} style={chipCloseBtnStyle} title="Remove filter">✕</button>
                </span>
              )}

              {/* Gender Chip */}
              {activeFilters.gender && (
                <span className="badge" style={{ ...chipBadgeStyle, background: 'rgba(236, 72, 153, 0.2)', border: '1px solid rgba(236, 72, 153, 0.4)', color: '#fbcfe8' }}>
                  <span>{activeFilters.gender === 'Male' ? '♂️ Male' : '♀️ Female'}</span>
                  <button onClick={() => pushFilterState({ ...activeFilters, gender: '' })} style={chipCloseBtnStyle} title="Remove filter">✕</button>
                </span>
              )}

              {/* Min Level Chip */}
              {activeFilters.minLevel && (
                <span className="badge" style={{ ...chipBadgeStyle, background: 'rgba(34, 197, 94, 0.2)', border: '1px solid rgba(34, 197, 94, 0.4)', color: '#bbf7d0' }}>
                  <span>⭐ Min Lv.{activeFilters.minLevel}</span>
                  <button onClick={() => pushFilterState({ ...activeFilters, minLevel: '' })} style={chipCloseBtnStyle} title="Remove filter">✕</button>
                </span>
              )}

              {/* Rarity Chip */}
              {activeFilters.rarity && (
                <span className="badge" style={{ ...chipBadgeStyle, background: 'rgba(245, 158, 11, 0.2)', border: '1px solid rgba(245, 158, 11, 0.4)', color: '#fde68a' }}>
                  <span>{RARITY_OPTIONS.find(o => o.value === activeFilters.rarity)?.label || `Rarity: ${activeFilters.rarity}`}</span>
                  <button onClick={() => pushFilterState({ ...activeFilters, rarity: '' })} style={chipCloseBtnStyle} title="Remove filter">✕</button>
                </span>
              )}

              {/* Pal Gear Status Chip */}
              {activeFilters.gearStatus && (
                <span className="badge" style={{ ...chipBadgeStyle, background: 'rgba(16, 185, 129, 0.2)', border: '1px solid rgba(16, 185, 129, 0.4)', color: '#a7f3d0' }}>
                  <span>🪖 {
                    activeFilters.gearStatus === 'crafted' ? 'Gear: Crafted (Active)' :
                    activeFilters.gearStatus === 'not_crafted' ? 'Gear: Not Crafted' :
                    activeFilters.gearStatus === 'no_gear' ? 'Gear: Inherent (No Gear)' :
                    'Gear: Requires Gear'
                  }</span>
                  <button onClick={() => pushFilterState({ ...activeFilters, gearStatus: '' })} style={chipCloseBtnStyle} title="Remove filter">✕</button>
                </span>
              )}

              {/* Passive Skills Chips */}
              {activeFilters.passives.map((pass, pIdx) => {
                const pName = typeof pass === 'string' ? pass : (pass.name || pass.id);
                return (
                  <span
                    key={pIdx}
                    className="badge"
                    style={{
                      ...chipBadgeStyle,
                      background: 'rgba(99, 102, 241, 0.25)',
                      border: '1px solid rgba(99, 102, 241, 0.5)',
                      color: '#c7d2fe',
                    }}
                  >
                    <span>🛡️ {pName}</span>
                    <button
                      onClick={() => {
                        pushFilterState({
                          ...activeFilters,
                          passives: activeFilters.passives.filter((_, idx) => idx !== pIdx)
                        });
                      }}
                      style={chipCloseBtnStyle}
                      title="Remove filter"
                    >
                      ✕
                    </button>
                  </span>
                );
              })}

              {/* Elements Chips */}
              {activeFilters.elements.map((elem, eIdx) => (
                <span
                  key={eIdx}
                  className="badge"
                  style={{
                    ...chipBadgeStyle,
                    background: 'rgba(59, 130, 246, 0.25)',
                    border: '1px solid rgba(59, 130, 246, 0.5)',
                    color: '#bfdbfe',
                  }}
                >
                  <span>🔥 {elem}</span>
                  <button
                    onClick={() => {
                      pushFilterState({
                        ...activeFilters,
                        elements: activeFilters.elements.filter(e => e !== elem)
                      });
                    }}
                    style={chipCloseBtnStyle}
                    title="Remove filter"
                  >
                    ✕
                  </button>
                </span>
              ))}

              {/* Clear All Button */}
              <button
                onClick={() => pushFilterState(DEFAULT_FILTERS)}
                style={{ background: 'transparent', border: 'none', color: '#f87171', fontSize: '0.72rem', cursor: 'pointer', fontWeight: 600, marginLeft: 'auto', textDecoration: 'underline' }}
              >
                Clear All
              </button>
            </div>
          )}
        </div>
      )}

      {/* Advanced Pal Filter Modal */}
      <PalFilterModal
        isOpen={isFilterModalOpen}
        onClose={() => setIsFilterModalOpen(false)}
        initialFilters={activeFilters}
        speciesOptions={speciesOptions}
        onApply={(newFilters) => pushFilterState(newFilters)}
        totalMatchingCount={filteredInstances.length}
      />

      {/* Scrollable Table Area */}
      {saveLoaded ? (
        <div className="glass-card table-container" style={{ flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden', padding: 0, marginBottom: '1.5rem' }}>
          <table style={{ width: '100%', tableLayout: 'fixed' }}>
            <thead>
              <tr>
                <th onClick={() => handleSort('display_name')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.35rem 0.4rem', width: '14%' }}>Species{sortCol === 'display_name' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleSort('level')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.35rem 0.25rem', width: '5%' }}>Level{sortCol === 'level' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleSort('gender')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.35rem 0.25rem', width: '4%' }}>Sex{sortCol === 'gender' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th onClick={() => handleSort('rank')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.35rem 0.25rem', width: '4%' }}>Rank{sortCol === 'rank' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th style={{ whiteSpace: 'nowrap', padding: '0.35rem 0.35rem', width: '15%' }}>Partner Groups</th>
                <th onClick={() => handleSort('current_speed')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.35rem 0.25rem', width: '6%' }}>Speed{sortCol === 'current_speed' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th style={{ whiteSpace: 'nowrap', padding: '0.35rem 0.25rem', width: '8%' }}>IVs (H/A/D)</th>
                <th onClick={() => handleSort('location')} style={{ cursor: 'pointer', whiteSpace: 'nowrap', padding: '0.35rem 0.35rem', width: '8%' }}>Location{sortCol === 'location' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                <th style={{ padding: '0.35rem 0.4rem', width: '30%' }}>Passives</th>
                <th style={{ whiteSpace: 'nowrap', padding: '0.35rem 0.25rem', width: '6%', textAlign: 'center' }}>Element</th>
              </tr>
            </thead>
            <tbody>
              {isGroupedBySpecies ? (
                /* ========================================================================= */
                /* 2-TIER GROUPED BY SPECIES VIEW */
                /* ========================================================================= */
                groupedSpeciesData.map(group => {
                  const isExpanded = expandedSpecies.has(group.speciesName);
                  const count = group.instances.length;
                  const palName = group.speciesName;
                  const masterPal = group.masterPal;
                  const palIcon = group.palIcon;

                  // Instance children sorted by table sort
                  const sortedChildren = [...group.instances].sort((a, b) => {
                    if (sortCol === 'level') return sortDesc ? (b.level || 0) - (a.level || 0) : (a.level || 0) - (b.level || 0);
                    if (sortCol === 'gender') return sortDesc ? (b.gender || '').localeCompare(a.gender || '') : (a.gender || '').localeCompare(b.gender || '');
                    if (sortCol === 'rank') return sortDesc ? (b.rank || 0) - (a.rank || 0) : (a.rank || 0) - (b.rank || 0);
                    if (sortCol === 'current_speed') return sortDesc ? (b.current_speed || 0) - (a.current_speed || 0) : (a.current_speed || 0) - (b.current_speed || 0);
                    if (sortCol === 'location') return sortDesc ? (b.location || '').localeCompare(a.location || '') : (a.location || '').localeCompare(b.location || '');
                    return 0;
                  });

                  return (
                    <React.Fragment key={`group-${palName}`}>
                      {/* Tier 1: Species Group Header Row */}
                      <tr
                        onClick={() => toggleSpecies(palName)}
                        style={{
                          background: isExpanded ? 'rgba(99, 102, 241, 0.16)' : 'rgba(15, 23, 42, 0.65)',
                          borderBottom: isExpanded ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid rgba(255,255,255,0.06)',
                          borderLeft: isExpanded ? '4px solid #818cf8' : '4px solid transparent',
                          cursor: 'pointer',
                          userSelect: 'none',
                          transition: 'background 0.15s ease'
                        }}
                      >
                        {/* Species & Expand Indicator */}
                        <td style={{ padding: '0.45rem 0.5rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                            <span style={{
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
                              flexShrink: 0
                            }}>
                              {isExpanded ? '▼' : '▶'}
                            </span>
                            {palIcon && (
                              <img
                                src={palIcon}
                                alt={palName}
                                style={{ width: '24px', height: '24px', borderRadius: '4px', objectFit: 'contain', flexShrink: 0 }}
                                onError={(e) => { e.target.style.display = 'none'; }}
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
                          <span style={{ color: '#60a5fa', fontWeight: 700 }}>♂{group.instances.filter(i => i.gender === 'Male').length}</span>
                          {' / '}
                          <span style={{ color: '#f472b6', fontWeight: 700 }}>♀{group.instances.filter(i => i.gender === 'Female').length}</span>
                        </td>

                        {/* Top Rank */}
                        <td style={{ padding: '0.45rem 0.25rem', textAlign: 'center', color: '#fbbf24', fontSize: '0.74rem' }}>
                          {(() => {
                            const maxRank = Math.max(...group.instances.map(i => i.rank || 0), 0);
                            return maxRank > 0 ? `${'★'.repeat(maxRank)}` : '-';
                          })()}
                        </td>

                        {/* Partner Groups */}
                        <td style={{ padding: '0.45rem 0.35rem' }}>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem' }}>
                            {group.partnerCategories.length > 0 ? (
                              group.partnerCategories.map(cat => (
                                <span key={cat.id} className="badge" style={{ fontSize: '0.62rem', padding: '0.05rem 0.25rem', background: 'rgba(234, 179, 8, 0.15)', color: 'var(--accent-gold)', border: '1px solid rgba(234, 179, 8, 0.3)', borderRadius: '4px', whiteSpace: 'nowrap' }}>
                                  {cat.icon} {(SHORT_CATEGORY_NAMES[cat.id] || cat.name).toUpperCase()}
                                </span>
                              ))
                            ) : (
                              <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>-</span>
                            )}
                          </div>
                        </td>

                        {/* Base Speed */}
                        <td style={{ padding: '0.45rem 0.25rem', fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                          {group.masterPal?.run_speed || group.masterPal?.speed || group.instances[0]?.base_speed || '-'}
                        </td>

                        {/* IVs Best */}
                        <td style={{ padding: '0.45rem 0.25rem', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                          {(() => {
                            const maxHp = Math.max(...group.instances.map(i => i.iv_hp || 0), 0);
                            const maxAtk = Math.max(...group.instances.map(i => i.iv_melee || i.iv_attack || 0), 0);
                            const maxDef = Math.max(...group.instances.map(i => i.iv_defense || 0), 0);
                            return `Best: ${maxHp}/${maxAtk}/${maxDef}%`;
                          })()}
                        </td>

                        {/* Location summary */}
                        <td style={{ padding: '0.45rem 0.35rem' }}>
                          <div style={{ display: 'flex', gap: '0.2rem', flexWrap: 'wrap' }}>
                            {group.instances.some(i => i.location === 'party') && (
                              <span className="badge badge-party" style={{ fontSize: '0.58rem', padding: '0.04rem 0.25rem' }}>Party</span>
                            )}
                            {group.instances.some(i => i.location === 'base') && (
                              <span className="badge badge-base" style={{ fontSize: '0.58rem', padding: '0.04rem 0.25rem' }}>Base</span>
                            )}
                            {group.instances.some(i => i.location === 'palbox' || !i.location) && (
                              <span className="badge badge-palbox" style={{ fontSize: '0.58rem', padding: '0.04rem 0.25rem' }}>Box</span>
                            )}
                          </div>
                        </td>

                        {/* Pal Gear Status (under Passives column) */}
                        <td style={{ padding: '0.45rem 0.4rem' }}>
                          {group.gear?.requires_gear ? (
                            group.gear.is_crafted ? (
                              <span style={{ fontSize: '0.68rem', color: '#86efac', background: 'rgba(34, 197, 94, 0.15)', border: '1px solid rgba(34, 197, 94, 0.35)', padding: '0.05rem 0.35rem', borderRadius: '4px', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.2rem', whiteSpace: 'nowrap' }}>
                                <span>🪖</span> <span>{group.gear.name}: <strong>Crafted</strong></span>
                              </span>
                            ) : (
                              <span style={{ fontSize: '0.68rem', color: '#fca5a5', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.35)', padding: '0.05rem 0.35rem', borderRadius: '4px', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.2rem', whiteSpace: 'nowrap' }}>
                                <span>🔒</span> <span>{group.gear.name}: <strong>Not Crafted</strong></span>
                              </span>
                            )
                          ) : (
                            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>✨ Inherent Skill</span>
                          )}
                        </td>

                        {/* Dedicated Element Column */}
                        <td style={{ padding: '0.45rem 0.25rem', textAlign: 'center' }}>
                          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem' }}>
                            {group.elements.map(el => (
                              <img
                                key={el}
                                src={ELEMENT_ICON_MAP[el] || `/assets/elements/${el}.png`}
                                alt=""
                                style={{ width: '18px', height: '18px', objectFit: 'contain' }}
                                onError={(e) => { e.target.style.display = 'none'; }}
                              />
                            ))}
                          </div>
                        </td>
                      </tr>

                      {/* Tier 2: Child Pal Instance Rows */}
                      {isExpanded && sortedChildren.map((pi, childIdx) => {
                        const locClass = pi.location === 'party' ? 'badge-party' : (pi.location === 'base' ? 'badge-base' : (pi.location === 'dps' ? 'badge-dps' : 'badge-palbox'));
                        const locLabel = pi.location === 'party' ? 'PARTY' : (pi.location === 'base' ? 'BASE' : (pi.location === 'dps' ? 'STORAGE' : 'PALBOX'));
                        const locIcon = pi.location === 'party' ? '⚔️' : (pi.location === 'base' ? '🏠' : (pi.location === 'dps' ? '🔮' : '📦'));
                        
                        const rankStars = (pi.rank && pi.rank > 0) ? '★'.repeat(pi.rank) : '-';
                        const genderIcon = pi.gender === 'Female' ? '♀' : (pi.gender === 'Male' ? '♂' : '?');
                        const genderColor = pi.gender === 'Female' ? '#f472b6' : (pi.gender === 'Male' ? '#60a5fa' : '#94a3b8');
                        const speedVal = pi.current_speed || masterPal?.ride_sprint_speed || masterPal?.walk_speed || '-';
                        const ivDisplay = `${pi.iv_hp ?? '-'}/${pi.iv_attack ?? '-'}/${pi.iv_defense ?? '-'}`;
                        
                        const categories = (pi.partner_skill_categories && pi.partner_skill_categories.length > 0)
                          ? pi.partner_skill_categories
                          : (masterPal?.partner_skill_categories || []);

                        const childElements = [pi.element_1 || masterPal?.element_1, pi.element_2 || masterPal?.element_2].filter(Boolean);

                        return (
                          <tr key={pi.instance_id || `child-${childIdx}`} style={{ background: 'rgba(0, 0, 0, 0.25)', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                            {/* Nested Pal Instance Name / Tooltip */}
                            <td style={{ padding: '0.3rem 0.4rem 0.3rem 1.6rem' }}>
                              <PalInstanceTooltip instance={pi} masterPal={masterPal}>
                                <span
                                  style={{ fontWeight: 600, color: '#f8fafc', cursor: 'pointer', fontSize: '0.78rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                                  onClick={() => setSelectedPal && masterPal && setSelectedPal(masterPal)}
                                >
                                  <span style={{ color: 'var(--text-secondary)', fontSize: '0.68rem' }}>└</span>
                                  <span>{pi.display_name || palName}</span>
                                </span>
                              </PalInstanceTooltip>
                            </td>

                            {/* Level */}
                            <td style={{ padding: '0.3rem 0.25rem', fontSize: '0.78rem' }}>
                              Lv.{pi.level || 1}
                            </td>

                            {/* Sex */}
                            <td style={{ padding: '0.3rem 0.25rem', textAlign: 'center' }}>
                              <span style={{ 
                                display: 'inline-flex', 
                                alignItems: 'center', 
                                justifyContent: 'center', 
                                width: '18px', 
                                height: '18px', 
                                borderRadius: '50%', 
                                border: `1px solid ${genderColor}`, 
                                color: genderColor, 
                                fontSize: '0.75rem', 
                                fontWeight: 700 
                              }}>
                                {genderIcon}
                              </span>
                            </td>

                            {/* Rank */}
                            <td style={{ padding: '0.3rem 0.25rem', textAlign: 'center', color: '#fbbf24', fontSize: '0.75rem', letterSpacing: '1px' }}>
                              {rankStars}
                            </td>

                            {/* Partner Groups */}
                            <td style={{ padding: '0.3rem 0.35rem' }}>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem' }}>
                                {categories.length > 0 ? (
                                  categories.map(cat => {
                                    const shortName = SHORT_CATEGORY_NAMES[cat.id] || cat.name;
                                    return (
                                      <span 
                                        key={cat.id} 
                                        className="badge" 
                                        style={{ 
                                          fontSize: '0.62rem', 
                                          padding: '0.05rem 0.25rem', 
                                          background: 'rgba(234, 179, 8, 0.15)', 
                                          color: 'var(--accent-gold)', 
                                          border: '1px solid rgba(234, 179, 8, 0.3)',
                                          borderRadius: '4px',
                                          whiteSpace: 'nowrap'
                                        }}
                                        title={cat.name}
                                      >
                                        {cat.icon} {shortName.toUpperCase()}
                                      </span>
                                    );
                                  })
                                ) : (
                                  <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>-</span>
                                )}
                              </div>
                            </td>

                            {/* Speed */}
                            <td style={{ padding: '0.3rem 0.25rem', fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                              {speedVal !== '-' ? `➔ ${speedVal}` : '-'}
                            </td>

                            {/* IVs */}
                            <td style={{ padding: '0.3rem 0.25rem', fontSize: '0.72rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                              {ivDisplay}
                            </td>

                            {/* Location */}
                            <td style={{ padding: '0.3rem 0.35rem' }}>
                              <span className={`badge ${locClass}`} style={{ fontSize: '0.62rem', padding: '0.1rem 0.35rem', borderRadius: '4px', whiteSpace: 'nowrap' }}>
                                {locIcon} {locLabel}
                              </span>
                            </td>

                            {/* Passives */}
                            <td style={{ padding: '0.3rem 0.4rem' }}>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                                {(pi.passives || []).length > 0 ? (
                                  (pi.passives || []).map((pass, pIdx) => {
                                    const pName = typeof pass === 'string' ? pass : (pass.name || pass.id);
                                    return (
                                      <PassiveBadge 
                                        key={pIdx} 
                                        skill={pName} 
                                        isMatched={activeFilters.passives.some(f => {
                                          const fName = typeof f === 'string' ? f : (f.name || f.id || '');
                                          return fName.toLowerCase() === pName.toLowerCase();
                                        })}
                                      />
                                    );
                                  })
                                ) : (
                                  <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>No Passives</span>
                                )}
                              </div>
                            </td>

                            {/* Dedicated Element Column */}
                            <td style={{ padding: '0.3rem 0.25rem', textAlign: 'center' }}>
                              <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.2rem' }}>
                                {childElements.map(el => (
                                  <img
                                    key={el}
                                    src={ELEMENT_ICON_MAP[el] || `/assets/elements/${el}.png`}
                                    alt=""
                                    style={{ width: '16px', height: '16px', objectFit: 'contain' }}
                                    onError={(e) => { e.target.style.display = 'none'; }}
                                  />
                                ))}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </React.Fragment>
                  );
                })
              ) : (
                /* ========================================================================= */
                /* FLAT LIST VIEW */
                /* ========================================================================= */
                sortedInstances.map((pi, idx) => {
                  const masterPal = pals.find(p => 
                    (p.internal_name && (p.internal_name === pi.character_id || p.internal_name === pi.character_id_raw || p.internal_name === pi.species)) ||
                    (p.id && (p.id === pi.character_id || p.id === pi.character_id_raw || p.id === pi.species)) ||
                    (p.display_name && p.display_name.toLowerCase() === (pi.display_name || '').toLowerCase())
                  );
                  const palName = pi.display_name || pi.species;
                  const palIcon = pi.icon_url || masterPal?.icon_url || (palName ? `/assets/pals/icons/${palName.toLowerCase().replace(/ /g, '_')}.png` : null);
                  
                  const locClass = pi.location === 'party' ? 'badge-party' : (pi.location === 'base' ? 'badge-base' : (pi.location === 'dps' ? 'badge-dps' : 'badge-palbox'));
                  const locLabel = pi.location === 'party' ? 'PARTY' : (pi.location === 'base' ? 'BASE' : (pi.location === 'dps' ? 'STORAGE' : 'PALBOX'));
                  const locIcon = pi.location === 'party' ? '⚔️' : (pi.location === 'base' ? '🏠' : (pi.location === 'dps' ? '🔮' : '📦'));
                  
                  const rankStars = (pi.rank && pi.rank > 0) ? '★'.repeat(pi.rank) : '-';
                  const genderIcon = pi.gender === 'Female' ? '♀' : (pi.gender === 'Male' ? '♂' : '?');
                  const genderColor = pi.gender === 'Female' ? '#f472b6' : (pi.gender === 'Male' ? '#60a5fa' : '#94a3b8');
                  const speedVal = pi.current_speed || masterPal?.ride_sprint_speed || masterPal?.walk_speed || '-';
                  const ivDisplay = `${pi.iv_hp ?? '-'}/${pi.iv_attack ?? '-'}/${pi.iv_defense ?? '-'}`;
                  
                  const categories = (pi.partner_skill_categories && pi.partner_skill_categories.length > 0)
                    ? pi.partner_skill_categories
                    : (masterPal?.partner_skill_categories || []);

                  const flatElements = [pi.element_1 || masterPal?.element_1, pi.element_2 || masterPal?.element_2].filter(Boolean);

                  return (
                    <tr key={pi.instance_id || idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      {/* Species + Icon */}
                      <td style={{ padding: '0.3rem 0.4rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                          {palIcon && (
                            <img 
                              src={palIcon} 
                              alt={palName} 
                              style={{ width: '22px', height: '22px', borderRadius: '4px', objectFit: 'contain' }}
                              onError={(e) => { e.target.style.display = 'none'; }}
                            />
                          )}
                          <PalInstanceTooltip instance={pi} masterPal={masterPal}>
                            <span 
                              style={{ fontWeight: 600, color: 'var(--accent-gold)', cursor: 'pointer', fontSize: '0.8rem' }}
                              onClick={() => setSelectedPal && masterPal && setSelectedPal(masterPal)}
                            >
                              {palName}
                            </span>
                          </PalInstanceTooltip>
                        </div>
                      </td>

                      {/* Level */}
                      <td style={{ padding: '0.3rem 0.25rem', fontSize: '0.78rem' }}>
                        Lv.{pi.level || 1}
                      </td>

                      {/* Sex */}
                      <td style={{ padding: '0.3rem 0.25rem', textAlign: 'center' }}>
                        <span style={{ 
                          display: 'inline-flex', 
                          alignItems: 'center', 
                          justifyContent: 'center', 
                          width: '18px', 
                          height: '18px', 
                          borderRadius: '50%', 
                          border: `1px solid ${genderColor}`, 
                          color: genderColor, 
                          fontSize: '0.75rem', 
                          fontWeight: 700 
                        }}>
                          {genderIcon}
                        </span>
                      </td>

                      {/* Rank */}
                      <td style={{ padding: '0.3rem 0.25rem', textAlign: 'center', color: '#fbbf24', fontSize: '0.75rem', letterSpacing: '1px' }}>
                        {rankStars}
                      </td>

                      {/* Partner Groups */}
                      <td style={{ padding: '0.3rem 0.35rem' }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.2rem' }}>
                          {categories.length > 0 ? (
                            categories.map(cat => {
                              const shortName = SHORT_CATEGORY_NAMES[cat.id] || cat.name;
                              return (
                                <span 
                                  key={cat.id} 
                                  className="badge" 
                                  style={{ 
                                    fontSize: '0.62rem', 
                                    padding: '0.05rem 0.25rem', 
                                    background: 'rgba(234, 179, 8, 0.15)', 
                                    color: 'var(--accent-gold)', 
                                    border: '1px solid rgba(234, 179, 8, 0.3)',
                                    borderRadius: '4px',
                                    whiteSpace: 'nowrap'
                                  }}
                                  title={cat.name}
                                >
                                  {cat.icon} {shortName.toUpperCase()}
                                </span>
                              );
                            })
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>-</span>
                          )}
                        </div>
                      </td>

                      {/* Speed */}
                      <td style={{ padding: '0.3rem 0.25rem', fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                        {speedVal !== '-' ? `➔ ${speedVal}` : '-'}
                      </td>

                      {/* IVs */}
                      <td style={{ padding: '0.3rem 0.25rem', fontSize: '0.72rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                        {ivDisplay}
                      </td>

                      {/* Location */}
                      <td style={{ padding: '0.3rem 0.35rem' }}>
                        <span className={`badge ${locClass}`} style={{ fontSize: '0.62rem', padding: '0.1rem 0.35rem', borderRadius: '4px', whiteSpace: 'nowrap' }}>
                          {locIcon} {locLabel}
                        </span>
                      </td>

                      {/* Passives */}
                      <td style={{ padding: '0.3rem 0.4rem' }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                          {(pi.passives || []).length > 0 ? (
                            (pi.passives || []).map((pass, pIdx) => {
                              const pName = typeof pass === 'string' ? pass : (pass.name || pass.id);
                              return (
                                <PassiveBadge 
                                  key={pIdx} 
                                  skill={pName} 
                                  isMatched={activeFilters.passives.some(f => {
                                    const fName = typeof f === 'string' ? f : (f.name || f.id || '');
                                    return fName.toLowerCase() === pName.toLowerCase();
                                  })}
                                />
                              );
                            })
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>No Passives</span>
                          )}
                        </div>
                      </td>

                      {/* Dedicated Element Column */}
                      <td style={{ padding: '0.3rem 0.25rem', textAlign: 'center' }}>
                        <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.2rem' }}>
                          {flatElements.map(el => (
                            <img
                              key={el}
                              src={ELEMENT_ICON_MAP[el] || `/assets/elements/${el}.png`}
                              alt=""
                              style={{ width: '16px', height: '16px', objectFit: 'contain' }}
                              onError={(e) => { e.target.style.display = 'none'; }}
                            />
                          ))}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}

              {filteredInstances.length === 0 && (
                <tr>
                  <td colSpan="10" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No captured Pals match the selected filter criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="glass-card" style={{ padding: '3rem', textAlign: 'center', maxWidth: '500px' }}>
            <span style={{ fontSize: '3rem', display: 'block', marginBottom: '1rem' }}>📁</span>
            <h3 style={{ marginBottom: '0.5rem' }}>No Save Game Loaded</h3>
            <p style={{ fontSize: '0.85rem' }}>Please select or upload a Palworld save file in Settings to explore your caught Pals.</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default SaveGameExplorerView;
