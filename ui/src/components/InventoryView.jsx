import React, { useState, useEffect } from 'react';
import { useTableSort } from '../hooks/useTableSort';

const SOUL_ICONS = {
  small: '/assets/items/PalUpgradeStone.png',
  medium: '/assets/items/PalUpgradeStone2.png',
  large: '/assets/items/PalUpgradeStone3.png',
  giant: '/assets/items/PalUpgradeStone4.png',
};

const SOUL_TIER_NAMES = {
  small: 'Small Pal Soul',
  medium: 'Medium Pal Soul',
  large: 'Large Pal Soul',
  giant: 'Giant Pal Soul',
};

const RARITY_COLORS = {
  0: { label: 'Common', border: 'rgba(255,255,255,0.15)', text: '#94a3b8', bg: 'rgba(255,255,255,0.05)' },
  1: { label: 'Uncommon', border: 'rgba(52, 211, 153, 0.4)', text: '#34d399', bg: 'rgba(16, 185, 129, 0.12)' },
  2: { label: 'Rare', border: 'rgba(96, 165, 250, 0.4)', text: '#60a5fa', bg: 'rgba(59, 130, 246, 0.12)' },
  3: { label: 'Epic', border: 'rgba(192, 132, 252, 0.4)', text: '#c084fc', bg: 'rgba(139, 92, 246, 0.15)' },
  4: { label: 'Legendary', border: 'rgba(251, 191, 36, 0.5)', text: '#fbbf24', bg: 'rgba(245, 158, 11, 0.2)' },
};

export function InventoryView() {
  const [subView, setSubView] = useState('inventory');
  const [inventory, setInventory] = useState([]);
  const [containerFilter, setContainerFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [soulData, setSoulData] = useState(null);
  const [soulLoading, setSoulLoading] = useState(true);

  useEffect(() => {
    fetch('/api/save/soul-optimizer')
      .then(res => res.json())
      .then(data => {
        setSoulData(data);
        setSoulLoading(false);
      })
      .catch(err => {
        console.error('Error fetching soul optimizer data:', err);
        setSoulLoading(false);
      });
  }, []);

  useEffect(() => {
    setLoading(true);
    let url = '/api/save/inventory?';
    if (containerFilter) url += `container_type=${encodeURIComponent(containerFilter)}&`;
    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setInventory(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching inventory:', err);
        setLoading(false);
      });
  }, [containerFilter]);

  const filteredInventory = inventory.filter(item => {
    if (categoryFilter) {
      const itemCat = (item.category || '').toLowerCase();
      const filterCat = categoryFilter.toLowerCase();
      if (filterCat === 'sphere' || filterCat === 'specialweapon') {
        if (itemCat !== 'sphere' && itemCat !== 'specialweapon') return false;
      } else if (itemCat !== filterCat) {
        return false;
      }
    }
    if (search) {
      const q = search.toLowerCase();
      const matchName = (item.item_name || item.name || item.display_name || '').toLowerCase().includes(q);
      const matchLoc = (item.container_type || '').toLowerCase().includes(q);
      const matchBase = (item.base_camp_name || '').toLowerCase().includes(q);
      const matchDesc = (item.description || '').toLowerCase().includes(q);
      if (!matchName && !matchLoc && !matchBase && !matchDesc) return false;
    }
    return true;
  });

  const {
    sortedData: sortedInventory,
    sortCol,
    sortDesc,
    handleSort,
  } = useTableSort(filteredInventory, 'count', true);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      {/* Top View Selector Tabs */}
      <div style={{ display: 'flex', gap: '0.6rem', marginBottom: '0.85rem', flexShrink: 0 }}>
        <button
          type="button"
          onClick={() => setSubView('inventory')}
          style={{
            padding: '0.5rem 1.1rem',
            borderRadius: '8px',
            border: subView === 'inventory' ? '1px solid var(--accent-gold)' : '1px solid rgba(255, 255, 255, 0.1)',
            background: subView === 'inventory' ? 'rgba(251, 191, 36, 0.15)' : 'rgba(255, 255, 255, 0.04)',
            color: subView === 'inventory' ? 'var(--accent-gold)' : 'var(--text-secondary)',
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            fontSize: '0.85rem',
            transition: 'all 0.15s ease'
          }}
        >
          <span>📦</span> Storage Inventory
        </button>
        <button
          type="button"
          onClick={() => setSubView('souls')}
          style={{
            padding: '0.5rem 1.1rem',
            borderRadius: '8px',
            border: subView === 'souls' ? '1px solid #8b5cf6' : '1px solid rgba(255, 255, 255, 0.1)',
            background: subView === 'souls' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(255, 255, 255, 0.04)',
            color: subView === 'souls' ? '#c084fc' : 'var(--text-secondary)',
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            fontSize: '0.85rem',
            transition: 'all 0.15s ease'
          }}
        >
          <span>💎</span> Pal Soul Crusher Optimizer
        </button>
      </div>

      {/* VIEW 1: PAL SOUL CRUSHER OPTIMIZER */}
      {subView === 'souls' && (
        <div style={{ flex: 1, minHeight: 0, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem', paddingBottom: '1.5rem' }}>
          {soulLoading ? (
            <div className="glass-card" style={{ textAlign: 'center', padding: '3rem' }}>
              <p style={{ color: 'var(--text-secondary)' }}>Analyzing Pal Soul inventory and Crusher combinations...</p>
            </div>
          ) : !soulData ? (
            <div className="glass-card" style={{ textAlign: 'center', padding: '3rem' }}>
              <p style={{ color: 'var(--text-secondary)' }}>No save data available.</p>
            </div>
          ) : (
            <>
              {/* Header Metric Card */}
              <div className="glass-card" style={{
                padding: '1.15rem 1.4rem',
                background: 'linear-gradient(135deg, rgba(30, 27, 75, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)',
                border: '1px solid rgba(139, 92, 246, 0.35)',
                borderRadius: '12px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '1rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '10px',
                    background: 'linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.3rem'
                  }}>
                    💎
                  </div>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: '1.1rem', color: '#f8fafc' }}>
                      Pal Soul Crusher Optimizer
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
                      Statue of Power (Ranks 1-20: 10 Small, 6 Medium, 6 Large, 30 Giant per stat)
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
                  <div style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    padding: '0.45rem 0.8rem',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    fontSize: '0.82rem'
                  }}>
                    <span style={{ color: 'var(--text-secondary)', marginRight: '0.35rem' }}>Direct Maxable:</span>
                    <strong style={{ color: '#f8fafc' }}>{soulData.direct_maxable_stats} stats</strong>
                    <span style={{ color: 'var(--text-secondary)', fontSize: '0.72rem', marginLeft: '0.35rem' }}>
                      ({Math.floor(soulData.direct_maxable_stats / 4)} Pals)
                    </span>
                  </div>

                  <div style={{
                    background: 'rgba(16, 185, 129, 0.15)',
                    padding: '0.45rem 0.8rem',
                    borderRadius: '8px',
                    border: '1px solid rgba(16, 185, 129, 0.4)',
                    fontSize: '0.82rem'
                  }}>
                    <span style={{ color: '#6ee7b7', marginRight: '0.35rem' }}>Crusher Optimized:</span>
                    <strong style={{ color: '#34d399', fontSize: '0.9rem' }}>{soulData.optimal_maxable_stats} stats</strong>
                    <span style={{ color: '#a7f3d0', fontSize: '0.72rem', marginLeft: '0.35rem' }}>
                      ({Math.floor(soulData.optimal_maxable_stats / 4)} Pals)
                    </span>
                  </div>

                  {soulData.stats_gained_via_crusher > 0 && (
                    <div style={{
                      background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.25) 0%, rgba(234, 88, 12, 0.25) 100%)',
                      padding: '0.45rem 0.8rem',
                      borderRadius: '8px',
                      border: '1px solid rgba(245, 158, 11, 0.45)',
                      fontSize: '0.82rem',
                      fontWeight: 700,
                      color: 'var(--accent-gold)'
                    }}>
                      +{soulData.stats_gained_via_crusher} Stats Gained (+{Math.floor(soulData.optimal_maxable_stats / 4) - Math.floor(soulData.direct_maxable_stats / 4)} Full Pals)
                    </div>
                  )}
                </div>
              </div>

              {/* 4 Soul Inventory Cards */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
                gap: '0.75rem'
              }}>
                {[
                  { key: 'small', title: 'Small Pal Soul', ranks: 'Ranks 1-4 (Cost: 10/stat)', icon: SOUL_ICONS.small },
                  { key: 'medium', title: 'Medium Pal Soul', ranks: 'Ranks 5-7 (Cost: 6/stat)', icon: SOUL_ICONS.medium },
                  { key: 'large', title: 'Large Pal Soul', ranks: 'Ranks 8-10 (Cost: 6/stat)', icon: SOUL_ICONS.large },
                  { key: 'giant', title: 'Giant Pal Soul', ranks: 'Ranks 11-20 (Cost: 30/stat)', icon: SOUL_ICONS.giant },
                ].map(tier => {
                  const count = soulData.current_inventory?.[tier.key] ?? 0;
                  const needed = soulData.required_for_optimal?.[tier.key] ?? 0;
                  const leftover = soulData.remainder_after_optimal?.[tier.key] ?? 0;
                  return (
                    <div
                      key={tier.key}
                      className="glass-card"
                      style={{
                        padding: '0.85rem 1rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.85rem',
                        borderRadius: '10px',
                        background: 'rgba(20, 28, 47, 0.65)'
                      }}
                    >
                      <img
                        src={tier.icon}
                        alt={tier.title}
                        style={{
                          width: '38px',
                          height: '38px',
                          objectFit: 'contain',
                          filter: 'drop-shadow(0 2px 5px rgba(0,0,0,0.5))'
                        }}
                      />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                          {tier.title}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                          {tier.ranks}
                        </div>
                        <div style={{ marginTop: '0.25rem', display: 'flex', alignItems: 'baseline', gap: '0.4rem', flexWrap: 'wrap' }}>
                          <span style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--accent-gold)' }}>
                            {count.toLocaleString()}
                          </span>
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                            (Need: {needed} | Leftover: {leftover})
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Recommended Crusher Transformations with Icons & Arrows */}
              <div className="glass-card" style={{ padding: '1.15rem 1.35rem', borderRadius: '12px' }}>
                <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--accent-gold)', marginBottom: '0.75rem' }}>
                  ⚙️ Recommended Crusher Transformations (Execute in Order):
                </div>

                {soulData.crusher_steps && soulData.crusher_steps.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
                    {soulData.crusher_steps.map((step, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.85rem',
                          background: 'rgba(255, 255, 255, 0.03)',
                          border: '1px solid rgba(255, 255, 255, 0.07)',
                          padding: '0.6rem 0.9rem',
                          borderRadius: '8px'
                        }}
                      >
                        {/* Step Order Badge */}
                        <div style={{
                          width: '26px',
                          height: '26px',
                          borderRadius: '6px',
                          background: 'rgba(251, 191, 36, 0.15)',
                          border: '1px solid rgba(251, 191, 36, 0.35)',
                          color: 'var(--accent-gold)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 800,
                          fontSize: '0.82rem',
                          flexShrink: 0
                        }}>
                          {idx + 1}
                        </div>

                        {/* Input Tier with Count & Icon */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', minWidth: '170px' }}>
                          <span style={{ fontWeight: 800, fontSize: '0.95rem', color: '#f8fafc' }}>
                            {step.input_count}
                          </span>
                          <img
                            src={SOUL_ICONS[step.from_tier]}
                            alt={step.from_name}
                            style={{ width: '26px', height: '26px', objectFit: 'contain' }}
                          />
                          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                            {SOUL_TIER_NAMES[step.from_tier] || step.from_name}
                          </span>
                        </div>

                        {/* Arrow */}
                        <span style={{ color: 'var(--accent-gold)', fontWeight: 800, fontSize: '1.2rem', padding: '0 0.25rem' }}>
                          ➔
                        </span>

                        {/* Output Tier with Count & Icon */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', minWidth: '170px' }}>
                          <span style={{ fontWeight: 800, fontSize: '0.95rem', color: '#34d399' }}>
                            {step.output_count}
                          </span>
                          <img
                            src={SOUL_ICONS[step.to_tier]}
                            alt={step.to_name}
                            style={{ width: '26px', height: '26px', objectFit: 'contain' }}
                          />
                          <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                            {SOUL_TIER_NAMES[step.to_tier] || step.to_name}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontStyle: 'italic', padding: '0.5rem 0' }}>
                    {soulData.optimal_maxable_stats === 0
                      ? 'Not enough Pal Souls in storage to complete a full 0-20 stat upgrade (requires 10 Small, 6 Medium, 6 Large, 30 Giant, or 286 Small equivalents).'
                      : 'Your Pal Soul inventory is already at optimal ratio. No Crusher conversions required!'}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* VIEW 2: ALL STORAGE INVENTORY TABLE */}
      {subView === 'inventory' && (
        <>
          <div style={{ flexShrink: 0, marginBottom: '0.75rem' }}>
            <div className="filter-bar glass-card" style={{ marginBottom: '0.5rem', flexWrap: 'wrap' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Storage Location</label>
                <select value={containerFilter} onChange={e => setContainerFilter(e.target.value)}>
                  <option value="">All Storage Locations</option>
                  <option value="Inventory">🎒 Player Inventory</option>
                  <option value="Base Chest">📦 Base Camp Chests</option>
                  <option value="Weapon Loadout">⚔️ Weapon Loadout</option>
                  <option value="Equipped Armor">🛡️ Equipped Armor</option>
                  <option value="Food Equip">🍱 Food Bag</option>
                  <option value="Key Items">🔑 Key Items</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Item Category</label>
                <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}>
                  <option value="">All Categories</option>
                  <option value="Material">🧱 Crafting Materials</option>
                  <option value="Food">🍖 Food & Nutrition</option>
                  <option value="Consume">🧪 Medicine & Consumables</option>
                  <option value="SpecialWeapon">🔮 Pal Spheres</option>
                  <option value="Weapon">⚔️ Weapons</option>
                  <option value="Ammo">🎯 Ammunition</option>
                  <option value="Armor">🛡️ Armor & Clothing</option>
                  <option value="Accessory">💍 Accessories</option>
                  <option value="Blueprint">📜 Schematics & Blueprints</option>
                  <option value="Essential">🔑 Key Items</option>
                  <option value="Glider">🪂 Gliders</option>
                </select>
              </div>
              <div style={{ flexGrow: 1 }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Search Items</label>
                <input type="text" placeholder="Search item name, container, or base camp..." value={search} onChange={e => setSearch(e.target.value)} />
              </div>
            </div>
          </div>

          <div className="glass-card table-container" style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 0, marginBottom: '1.5rem' }}>
            {loading ? (
              <div style={{ textAlign: 'center', padding: '3rem' }}>
                <p style={{ color: 'var(--text-secondary)' }}>Loading save storage inventory...</p>
              </div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th onClick={() => handleSort('item_name')} style={{ cursor: 'pointer' }}>
                      Item{sortCol === 'item_name' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                    </th>
                    <th onClick={() => handleSort('category')} style={{ cursor: 'pointer', width: '130px' }}>
                      Category{sortCol === 'category' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                    </th>
                    <th onClick={() => handleSort('count')} style={{ cursor: 'pointer', textAlign: 'center', width: '100px' }}>
                      Quantity{sortCol === 'count' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                    </th>
                    <th onClick={() => handleSort('container_type')} style={{ cursor: 'pointer', width: '150px' }}>
                      Storage Container{sortCol === 'container_type' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                    </th>
                    <th onClick={() => handleSort('base_camp_name')} style={{ cursor: 'pointer' }}>
                      Base / Location{sortCol === 'base_camp_name' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sortedInventory.map((item, idx) => {
                    const rarityInfo = item.rarity !== undefined && item.rarity !== null ? RARITY_COLORS[item.rarity] : null;
                    return (
                      <tr key={`${item.item_id || item.item_name}-${idx}`}>
                        <td style={{ fontWeight: 600 }}>
                          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', padding: '0.2rem 0' }}>
                            {item.icon_path ? (
                              <img
                                src={item.icon_path}
                                alt={item.item_name}
                                style={{
                                  width: '36px',
                                  height: '36px',
                                  objectFit: 'contain',
                                  borderRadius: '6px',
                                  background: 'rgba(0,0,0,0.25)',
                                  border: rarityInfo && item.rarity > 0 ? `1px solid ${rarityInfo.border}` : '1px solid rgba(255,255,255,0.08)',
                                  flexShrink: 0,
                                }}
                                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                              />
                            ) : (
                              <span style={{ fontSize: '1.3rem', flexShrink: 0 }}>📦</span>
                            )}
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                <span style={{ color: rarityInfo && item.rarity >= 3 ? rarityInfo.text : 'var(--text-primary)', fontSize: '0.9rem' }}>
                                  {item.item_name || item.name || item.display_name}
                                </span>
                                {rarityInfo && item.rarity > 0 && (
                                  <span style={{
                                    fontSize: '0.66rem',
                                    fontWeight: 700,
                                    padding: '0.05rem 0.35rem',
                                    borderRadius: '4px',
                                    border: `1px solid ${rarityInfo.border}`,
                                    color: rarityInfo.text,
                                    background: rarityInfo.bg,
                                  }}>
                                    {rarityInfo.label}
                                  </span>
                                )}
                              </div>
                              {item.description && (
                                <div
                                  style={{
                                    fontSize: '0.74rem',
                                    color: 'var(--text-secondary)',
                                    marginTop: '0.2rem',
                                    whiteSpace: 'normal',
                                    maxWidth: '420px',
                                    lineHeight: '1.25',
                                  }}
                                  title={item.description}
                                >
                                  {item.description}
                                </div>
                              )}
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginTop: '0.25rem', fontSize: '0.7rem' }}>
                                {item.weight !== undefined && item.weight !== null && (
                                  <span style={{ color: 'rgba(255,255,255,0.45)' }} title="Weight (Encumbrance)">
                                    ⚖️ {item.weight}
                                  </span>
                                )}
                                {item.price !== undefined && item.price !== null && item.price > 0 && (
                                  <span style={{ color: 'rgba(251, 191, 36, 0.75)' }} title="Sell Price (Gold)">
                                    💰 {item.price.toLocaleString()}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td>
                          <span className="badge" style={{ background: 'rgba(255,255,255,0.08)', fontSize: '0.74rem' }}>
                            {item.category || 'Material'}
                          </span>
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 800, color: 'var(--accent-gold)', fontSize: '0.95rem' }}>
                          x{item.count ? item.count.toLocaleString() : 1}
                        </td>
                        <td>
                          <span className="badge" style={{
                            background: item.container_type === 'Base Chest' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                            color: item.container_type === 'Base Chest' ? '#fbbf24' : '#60a5fa',
                            border: item.container_type === 'Base Chest' ? '1px solid rgba(245, 158, 11, 0.3)' : '1px solid rgba(59, 130, 246, 0.3)',
                            fontSize: '0.74rem',
                          }}>
                            {item.container_type || 'Inventory'}
                          </span>
                        </td>
                        <td style={{ fontSize: '0.82rem' }}>
                          {item.base_camp_name?.startsWith('Base') || item.base_camp_name?.includes('Guild') ? (
                            <span style={{ color: '#fbbf24', fontWeight: 600 }}>
                              🏰 {item.base_camp_name}
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-secondary)' }}>
                              {item.base_camp_name ? `🎒 ${item.base_camp_name}` : 'Player Character'}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  {sortedInventory.length === 0 && (
                    <tr>
                      <td colSpan="5" style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-secondary)' }}>
                        No items found matching the selected storage criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default InventoryView;
