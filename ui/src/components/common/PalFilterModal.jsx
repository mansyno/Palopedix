import React, { useState, useEffect, useMemo } from 'react';
import { CustomSelect } from './CustomSelect';

export const OFFICIAL_ELEMENTS = [
  { name: 'Neutral', label: 'Neutral', emoji: '⚪', color: '#cbd5e1', bg: 'rgba(148, 163, 184, 0.15)', border: 'rgba(148, 163, 184, 0.4)' },
  { name: 'Fire', label: 'Fire', emoji: '🔥', color: '#f87171', bg: 'rgba(239, 68, 68, 0.15)', border: 'rgba(239, 68, 68, 0.4)' },
  { name: 'Water', label: 'Water', emoji: '💧', color: '#60a5fa', bg: 'rgba(59, 130, 246, 0.15)', border: 'rgba(59, 130, 246, 0.4)' },
  { name: 'Grass', label: 'Grass', emoji: '🍃', color: '#4ade80', bg: 'rgba(34, 197, 94, 0.15)', border: 'rgba(34, 197, 94, 0.4)' },
  { name: 'Electric', label: 'Electric', emoji: '⚡', color: '#facc15', bg: 'rgba(234, 179, 8, 0.15)', border: 'rgba(234, 179, 8, 0.4)' },
  { name: 'Ice', label: 'Ice', emoji: '❄️', color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.15)', border: 'rgba(56, 189, 248, 0.4)' },
  { name: 'Ground', label: 'Ground', emoji: '⛰️', color: '#fb923c', bg: 'rgba(249, 115, 22, 0.15)', border: 'rgba(249, 115, 22, 0.4)' },
  { name: 'Dark', label: 'Dark', emoji: '🌑', color: '#c084fc', bg: 'rgba(168, 85, 247, 0.15)', border: 'rgba(168, 85, 247, 0.4)' },
  { name: 'Dragon', label: 'Dragon', emoji: '🐉', color: '#a78bfa', bg: 'rgba(139, 92, 246, 0.15)', border: 'rgba(139, 92, 246, 0.4)' },
];

export const PARTNER_GROUP_OPTIONS = [
  { value: '', label: 'All Partner Groups' },
  { value: 'flying_mount', label: '🦅 Flying Mounts' },
  { value: 'ground_mount', label: '🐎 Ground Mounts' },
  { value: 'swimming_mount', label: '🌊 Swimming Mounts' },
  { value: 'glider', label: '🪂 Gliders' },
  { value: 'ranch_producer', label: '🚜 Ranch Producers' },
  { value: 'player_element_infusion', label: '⚡ Player Element Infusion' },
  { value: 'player_combat_buffer', label: '⚔️ Player Combat Buffers' },
  { value: 'party_pal_buffer', label: '🛡️ Pal / Party Combat Buffers' },
  { value: 'heavy_artillery', label: '💥 Heavy Artillery & Weapons' },
  { value: 'coop_attacker', label: '👥 Autonomous Co-Op' },
  { value: 'healer_lifesteal', label: '💖 Healers & Life-Steal' },
  { value: 'carrying_capacity', label: '🎒 Carrying Capacity' },
  { value: 'drop_loot_booster', label: '🎁 Drop & Loot Boosters' },
  { value: 'resource_gathering', label: '⛏️ Resource Gathering' },
  { value: 'breeding_egg_booster', label: '🥚 Breeding & Egg Boosters' },
  { value: 'fishing_helper', label: '🎣 Fishing & Helpers' },
  { value: 'exploration_survival', label: '🧭 Exploration & Survival' },
];

export const LOCATION_OPTIONS = [
  { value: '', label: 'All Locations' },
  { value: 'party', label: 'Player Party' },
  { value: 'palbox', label: 'Palbox Storage' },
  { value: 'base', label: 'Base Workers' },
  { value: 'dps', label: 'Dimensional Storage' },
];

export const GENDER_OPTIONS = [
  { value: '', label: 'All Genders' },
  { value: 'Male', label: 'Male' },
  { value: 'Female', label: 'Female' },
];

export const RARITY_OPTIONS = [
  { value: '', label: 'All Rarities' },
  { value: 'legendary', label: '👑 Legendary (Tier 20)' },
  { value: 'boss', label: '🔥 Alpha / Boss (Tier 10)' },
  { value: 'rare', label: '⭐ Rare (Tier 7–9)' },
  { value: 'mid', label: '🔷 Mid-Tier (Tier 4–6)' },
  { value: 'common', label: '⚪ Common (Tier 1–3)' },
  { value: '20', label: 'Tier 20' },
  { value: '10', label: 'Tier 10' },
  { value: '9', label: 'Tier 9' },
  { value: '8', label: 'Tier 8' },
  { value: '7', label: 'Tier 7' },
  { value: '6', label: 'Tier 6' },
  { value: '5', label: 'Tier 5' },
  { value: '4', label: 'Tier 4' },
  { value: '3', label: 'Tier 3' },
  { value: '2', label: 'Tier 2' },
  { value: '1', label: 'Tier 1' },
];

export function PalFilterModal({
  isOpen,
  onClose,
  initialFilters = {
    partnerGroup: '',
    location: '',
    species: '',
    gender: '',
    minLevel: '',
    rarity: '',
    passives: [],
    elements: [],
  },
  speciesOptions = [],
  onApply,
  totalMatchingCount = null,
}) {
  // General Attribute Filters
  const [partnerGroup, setPartnerGroup] = useState(initialFilters.partnerGroup || '');
  const [location, setLocation] = useState(initialFilters.location || '');
  const [species, setSpecies] = useState(initialFilters.species || '');
  const [gender, setGender] = useState(initialFilters.gender || '');
  const [minLevel, setMinLevel] = useState(initialFilters.minLevel || '');
  const [rarity, setRarity] = useState(initialFilters.rarity || '');

  // 4 discrete passive skill slots
  const [slot1, setSlot1] = useState('');
  const [slot2, setSlot2] = useState('');
  const [slot3, setSlot3] = useState('');
  const [slot4, setSlot4] = useState('');

  // Elements
  const [selectedElements, setSelectedElements] = useState(initialFilters.elements || []);
  const [allPassives, setAllPassives] = useState([]);
  const [loadingPassives, setLoadingPassives] = useState(false);

  // Sync state whenever modal opens
  useEffect(() => {
    if (isOpen) {
      setPartnerGroup(initialFilters.partnerGroup || '');
      setLocation(initialFilters.location || '');
      setSpecies(initialFilters.species || '');
      setGender(initialFilters.gender || '');
      setMinLevel(initialFilters.minLevel || '');
      setRarity(initialFilters.rarity || '');

      const pList = initialFilters.passives || [];
      setSlot1(pList[0] ? (typeof pList[0] === 'string' ? pList[0] : (pList[0].name || pList[0].id || '')) : '');
      setSlot2(pList[1] ? (typeof pList[1] === 'string' ? pList[1] : (pList[1].name || pList[1].id || '')) : '');
      setSlot3(pList[2] ? (typeof pList[2] === 'string' ? pList[2] : (pList[2].name || pList[2].id || '')) : '');
      setSlot4(pList[3] ? (typeof pList[3] === 'string' ? pList[3] : (pList[3].name || pList[3].id || '')) : '');
      setSelectedElements(initialFilters.elements || []);
    }
  }, [isOpen, initialFilters]);

  // Fetch all passive skills dynamically from database
  useEffect(() => {
    if (isOpen && allPassives.length === 0) {
      setLoadingPassives(true);
      fetch('/api/skills?type=Passive')
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) {
            // Deduplicate by name
            const seen = new Set();
            const unique = [];
            for (const item of data) {
              const key = (item.name || item.id || '').trim().toLowerCase();
              if (key && !seen.has(key)) {
                seen.add(key);
                unique.push(item);
              }
            }
            // Sort alphabetically by in-game skill name
            unique.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
            setAllPassives(unique);
          }
        })
        .catch(err => console.error('Error fetching passive skills for filter modal:', err))
        .finally(() => setLoadingPassives(false));
    }
  }, [isOpen, allPassives.length]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Active passives list (filtered non-empty)
  const activeSelectedPassives = useMemo(() => {
    return [slot1, slot2, slot3, slot4].filter(s => s && s.trim() !== '');
  }, [slot1, slot2, slot3, slot4]);

  // Format species options for CustomSelect
  const formattedSpeciesOptions = useMemo(() => {
    return [
      { value: '', label: 'All Species' },
      ...speciesOptions.map(s => ({ value: s.name, label: s.name })),
    ];
  }, [speciesOptions]);

  // Format passive options for CustomSelect
  const formattedPassiveOptions = useMemo(() => {
    return [
      { value: '', label: '-- None --' },
      ...allPassives.map(p => ({ value: p.name || p.id, label: p.name || p.id })),
    ];
  }, [allPassives]);

  // Element Selection Handlers
  const handleToggleElement = (elementName) => {
    const exists = selectedElements.includes(elementName);
    if (exists) {
      setSelectedElements(selectedElements.filter(e => e !== elementName));
    } else {
      if (selectedElements.length >= 2) {
        return; // Max 2 elements
      }
      setSelectedElements([...selectedElements, elementName]);
    }
  };

  const handleReset = () => {
    setPartnerGroup('');
    setLocation('');
    setSpecies('');
    setGender('');
    setMinLevel('');
    setRarity('');
    setSlot1('');
    setSlot2('');
    setSlot3('');
    setSlot4('');
    setSelectedElements([]);
  };

  const handleApply = () => {
    onApply({
      partnerGroup,
      location,
      species,
      gender,
      minLevel,
      rarity,
      passives: activeSelectedPassives,
      elements: selectedElements,
    });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1100 }}>
      <div 
        className="modal-content" 
        onClick={e => e.stopPropagation()} 
        style={{ 
          maxWidth: '1200px', 
          width: '96%',
          display: 'flex', 
          flexDirection: 'column', 
          padding: '1.4rem 1.6rem',
          borderRadius: '20px',
          background: 'rgba(15, 23, 42, 0.97)',
          boxShadow: '0 25px 60px rgba(0, 0, 0, 0.7)',
          border: '1px solid rgba(99, 102, 241, 0.3)',
          maxHeight: '90vh',
          overflowY: 'auto'
        }}
      >
        <button className="modal-close-btn" onClick={onClose} title="Close (Esc)">✕</button>

        {/* Modal Header */}
        <div style={{ marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.6rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.3rem' }}>⚡</span>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800, background: 'linear-gradient(135deg, #fff, #a5b4fc)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0 }}>
              Filter Pals
            </h2>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', marginTop: '0.2rem', marginBottom: 0 }}>
            Configure any combination of general attributes, passive skills, and elemental types. All active filters are cumulative.
          </p>
        </div>

        {/* Filter Body */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          
          {/* ========================================================================= */}
          {/* SECTION 1: GENERAL ATTRIBUTES (PARTNER GROUP, LOCATION, SPECIES, GENDER, MIN LV, RARITY) */}
          {/* ========================================================================= */}
          <div className="filter-modal-section" style={{ background: 'rgba(255,255,255,0.02)', padding: '0.85rem 1rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
              <h3 style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--accent-gold)', display: 'flex', alignItems: 'center', gap: '0.35rem', margin: 0 }}>
                <span>📋</span> General Attributes
              </h3>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '0.5rem' }}>
              {/* Partner Group */}
              <div>
                <label style={{ display: 'block', marginBottom: '0.2rem', color: partnerGroup ? 'var(--accent-gold)' : 'var(--text-secondary)', fontSize: '0.7rem', fontWeight: 700 }}>
                  🤝 Partner Group
                </label>
                <CustomSelect
                  value={partnerGroup}
                  onChange={setPartnerGroup}
                  options={PARTNER_GROUP_OPTIONS}
                  placeholder="All Partner Groups"
                  accentColor="var(--accent-gold)"
                />
              </div>

              {/* Location */}
              <div>
                <label style={{ display: 'block', marginBottom: '0.2rem', color: location ? 'var(--accent-gold)' : 'var(--text-secondary)', fontSize: '0.7rem', fontWeight: 700 }}>
                  📍 Location
                </label>
                <CustomSelect
                  value={location}
                  onChange={setLocation}
                  options={LOCATION_OPTIONS}
                  placeholder="All Locations"
                  accentColor="var(--accent-gold)"
                />
              </div>

              {/* Species (Searchable) */}
              <div>
                <label style={{ display: 'block', marginBottom: '0.2rem', color: species ? 'var(--accent-gold)' : 'var(--text-secondary)', fontSize: '0.7rem', fontWeight: 700 }}>
                  🐾 Species
                </label>
                <CustomSelect
                  value={species}
                  onChange={setSpecies}
                  options={formattedSpeciesOptions}
                  placeholder="All Species"
                  searchable={true}
                  accentColor="var(--accent-gold)"
                />
              </div>

              {/* Gender */}
              <div>
                <label style={{ display: 'block', marginBottom: '0.2rem', color: gender ? 'var(--accent-gold)' : 'var(--text-secondary)', fontSize: '0.7rem', fontWeight: 700 }}>
                  ⚧ Gender
                </label>
                <CustomSelect
                  value={gender}
                  onChange={setGender}
                  options={GENDER_OPTIONS}
                  placeholder="All Genders"
                  accentColor="var(--accent-gold)"
                />
              </div>

              {/* Min Level */}
              <div>
                <label style={{ display: 'block', marginBottom: '0.2rem', color: minLevel ? 'var(--accent-gold)' : 'var(--text-secondary)', fontSize: '0.7rem', fontWeight: 700 }}>
                  ⭐ Min Level
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  placeholder="Min Lv"
                  value={minLevel}
                  onChange={e => setMinLevel(e.target.value)}
                  style={{
                    width: '100%',
                    fontSize: '0.78rem',
                    padding: '0.32rem 0.5rem',
                    background: 'rgba(15, 23, 42, 0.95)',
                    border: minLevel ? '1px solid #818cf8' : '1px solid var(--border-color)',
                    borderRadius: '6px',
                    color: 'var(--text-primary)',
                    minHeight: '30px',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              {/* Rarity Tier */}
              <div>
                <label style={{ display: 'block', marginBottom: '0.2rem', color: rarity ? 'var(--accent-gold)' : 'var(--text-secondary)', fontSize: '0.7rem', fontWeight: 700 }}>
                  👑 Rarity Tier
                </label>
                <CustomSelect
                  value={rarity}
                  onChange={setRarity}
                  options={RARITY_OPTIONS}
                  placeholder="All Rarities"
                  accentColor="var(--accent-gold)"
                />
              </div>
            </div>
          </div>

          {/* ========================================================================= */}
          {/* SECTION 2: PASSIVE SKILLS (4 COMPACT DROPDOWNS IN ONE ROW - SEARCHABLE) */}
          {/* ========================================================================= */}
          <div className="filter-modal-section" style={{ background: 'rgba(255,255,255,0.02)', padding: '0.85rem 1rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <h3 style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--accent-gold)', display: 'flex', alignItems: 'center', gap: '0.35rem', margin: 0 }}>
                <span>🛡️</span> Passive Skills Combination
                <span style={{ fontSize: '0.72rem', fontWeight: 600, color: activeSelectedPassives.length > 0 ? '#34d399' : 'var(--text-secondary)', marginLeft: '0.2rem' }}>
                  ({activeSelectedPassives.length}/4 Selected)
                </span>
              </h3>
              {activeSelectedPassives.length > 0 && (
                <button 
                  onClick={() => { setSlot1(''); setSlot2(''); setSlot3(''); setSlot4(''); }} 
                  style={{ background: 'transparent', border: 'none', color: '#f87171', fontSize: '0.72rem', cursor: 'pointer', fontWeight: 600 }}
                >
                  Clear Skills
                </button>
              )}
            </div>

            {/* 4 Searchable Custom Selectors in a Single Horizontal Row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem' }}>
              
              {/* Dropdown 1 */}
              <div>
                <label style={{ display: 'block', fontSize: '0.68rem', fontWeight: 700, color: slot1 ? 'var(--accent-gold)' : 'var(--text-secondary)', marginBottom: '0.2rem' }}>
                  Skill 1
                </label>
                <CustomSelect
                  value={slot1}
                  onChange={setSlot1}
                  options={formattedPassiveOptions}
                  placeholder="-- None --"
                  searchable={true}
                  disabled={loadingPassives}
                  accentColor="#818cf8"
                />
              </div>

              {/* Dropdown 2 */}
              <div>
                <label style={{ display: 'block', fontSize: '0.68rem', fontWeight: 700, color: slot2 ? 'var(--accent-gold)' : 'var(--text-secondary)', marginBottom: '0.2rem' }}>
                  Skill 2
                </label>
                <CustomSelect
                  value={slot2}
                  onChange={setSlot2}
                  options={formattedPassiveOptions}
                  placeholder="-- None --"
                  searchable={true}
                  disabled={loadingPassives}
                  accentColor="#818cf8"
                />
              </div>

              {/* Dropdown 3 */}
              <div>
                <label style={{ display: 'block', fontSize: '0.68rem', fontWeight: 700, color: slot3 ? 'var(--accent-gold)' : 'var(--text-secondary)', marginBottom: '0.2rem' }}>
                  Skill 3
                </label>
                <CustomSelect
                  value={slot3}
                  onChange={setSlot3}
                  options={formattedPassiveOptions}
                  placeholder="-- None --"
                  searchable={true}
                  disabled={loadingPassives}
                  accentColor="#818cf8"
                />
              </div>

              {/* Dropdown 4 */}
              <div>
                <label style={{ display: 'block', fontSize: '0.68rem', fontWeight: 700, color: slot4 ? 'var(--accent-gold)' : 'var(--text-secondary)', marginBottom: '0.2rem' }}>
                  Skill 4
                </label>
                <CustomSelect
                  value={slot4}
                  onChange={setSlot4}
                  options={formattedPassiveOptions}
                  placeholder="-- None --"
                  searchable={true}
                  disabled={loadingPassives}
                  accentColor="#818cf8"
                />
              </div>

            </div>
          </div>

          {/* ========================================================================= */}
          {/* SECTION 3: ELEMENTAL TYPES (UP TO 2) */}
          {/* ========================================================================= */}
          <div className="filter-modal-section" style={{ background: 'rgba(255,255,255,0.02)', padding: '0.85rem 1rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <div>
                <h3 style={{ fontSize: '0.88rem', fontWeight: 700, color: '#60a5fa', display: 'flex', alignItems: 'center', gap: '0.35rem', margin: 0 }}>
                  <span>🔥</span> Elemental Types
                  <span style={{ fontSize: '0.72rem', fontWeight: 600, color: selectedElements.length === 2 ? '#34d399' : 'var(--text-secondary)', marginLeft: '0.2rem' }}>
                    ({selectedElements.length}/2 Selected)
                  </span>
                </h3>
              </div>
              {selectedElements.length > 0 && (
                <button 
                  onClick={() => setSelectedElements([])} 
                  style={{ background: 'transparent', border: 'none', color: '#f87171', fontSize: '0.72rem', cursor: 'pointer', fontWeight: 600 }}
                >
                  Clear Elements
                </button>
              )}
            </div>

            {/* Elements Grid (9 Official Elements) */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '0.45rem' }}>
              {OFFICIAL_ELEMENTS.map(elem => {
                const isSelected = selectedElements.includes(elem.name);
                const isMaxReached = !isSelected && selectedElements.length >= 2;

                return (
                  <button
                    key={elem.name}
                    onClick={() => handleToggleElement(elem.name)}
                    disabled={isMaxReached}
                    style={{
                      background: isSelected ? elem.bg : 'rgba(0, 0, 0, 0.3)',
                      border: isSelected ? `2px solid ${elem.color}` : '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '8px',
                      padding: '0.4rem 0.65rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: isMaxReached ? 'not-allowed' : 'pointer',
                      opacity: isMaxReached ? 0.35 : 1,
                      boxShadow: isSelected ? `0 0 10px ${elem.border}` : 'none',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <img
                        src={`/assets/elements/${elem.name}.png`}
                        alt={elem.name}
                        style={{ width: '18px', height: '18px', objectFit: 'contain' }}
                        onError={(e) => { e.target.style.display = 'none'; }}
                      />
                      <span style={{ fontSize: '0.8rem', fontWeight: 700, color: isSelected ? elem.color : 'var(--text-primary)' }}>
                        {elem.name}
                      </span>
                    </div>
                    {isSelected && (
                      <span style={{ color: '#34d399', fontWeight: 900, fontSize: '0.8rem' }}>✓</span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

        </div>

        {/* Modal Footer */}
        <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <button
              className="btn btn-secondary"
              onClick={handleReset}
              style={{ fontSize: '0.78rem', padding: '0.35rem 0.75rem' }}
            >
              🔄 Reset All Filters
            </button>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button
              className="btn btn-secondary"
              onClick={onClose}
              style={{ fontSize: '0.78rem', padding: '0.35rem 0.75rem' }}
            >
              Cancel
            </button>
            <button
              className="btn btn-primary"
              onClick={handleApply}
              style={{
                fontSize: '0.8rem',
                padding: '0.4rem 1.15rem',
                fontWeight: 700,
                background: 'var(--primary-gradient)',
                boxShadow: '0 4px 15px rgba(99, 102, 241, 0.4)'
              }}
            >
              Apply Filters {totalMatchingCount !== null ? `(${totalMatchingCount} Pals)` : ''}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PalFilterModal;
