import React, { useState, useEffect } from 'react';
import { useTableSort } from '../hooks/useTableSort';

export function InventoryView() {
  const [inventory, setInventory] = useState([]);
  const [containerFilter, setContainerFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

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
    if (categoryFilter && (item.category || '').toLowerCase() !== categoryFilter.toLowerCase()) return false;
    if (search) {
      const q = search.toLowerCase();
      const matchName = (item.item_name || item.name || '').toLowerCase().includes(q);
      const matchLoc = (item.container_type || '').toLowerCase().includes(q);
      if (!matchName && !matchLoc) return false;
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
      <div style={{ flexShrink: 0, marginBottom: '0.75rem' }}>
        <div className="filter-bar glass-card" style={{ marginBottom: '0.5rem', flexWrap: 'wrap' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Storage Location</label>
            <select value={containerFilter} onChange={e => setContainerFilter(e.target.value)}>
              <option value="">All Storage Locations</option>
              <option value="PlayerInventory">🎒 Player Inventory</option>
              <option value="PlayerWeapon">⚔️ Equipped Weapons</option>
              <option value="PlayerArmor">🛡️ Equipped Armor</option>
              <option value="PlayerAccessory">💍 Equipped Accessories</option>
              <option value="BaseCampChest">📦 Base Camp Chests</option>
              <option value="BaseCampFeedBox">🍳 Feed Boxes</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Item Category</label>
            <select value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}>
              <option value="">All Categories</option>
              <option value="Material">Crafting Materials</option>
              <option value="Food">Food & Consumables</option>
              <option value="Sphere">Pal Spheres</option>
              <option value="Weapon">Weapons & Ammo</option>
              <option value="Armor">Armor & Clothing</option>
              <option value="Accessory">Accessories</option>
              <option value="Medicine">Medicine & Supplies</option>
              <option value="Essential">Key Items</option>
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
                <th onClick={() => handleSort('container_type')} style={{ cursor: 'pointer' }}>
                  Storage Container{sortCol === 'container_type' ? (sortDesc ? ' ▼' : ' ▲') : ''}
                </th>
                <th>Base / Location</th>
              </tr>
            </thead>
            <tbody>
              {sortedInventory.map((item, idx) => (
                <tr key={`${item.item_id || item.item_name}-${idx}`}>
                  <td style={{ fontWeight: 600 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                      {item.icon_path ? (
                        <img src={item.icon_path} alt={item.item_name} style={{ width: '28px', height: '28px', objectFit: 'contain', borderRadius: '4px', background: 'rgba(0,0,0,0.2)' }} onError={(e) => { e.target.style.display = 'none'; }} />
                      ) : (
                        <span style={{ fontSize: '1.1rem' }}>📦</span>
                      )}
                      <span style={{ color: 'var(--text-primary)' }}>{item.item_name || item.name}</span>
                    </div>
                  </td>
                  <td>
                    <span className="badge" style={{ background: 'rgba(255,255,255,0.08)', fontSize: '0.72rem' }}>
                      {item.category || 'Material'}
                    </span>
                  </td>
                  <td style={{ textAlign: 'center', fontWeight: 800, color: 'var(--accent-gold)' }}>
                    x{item.count ? item.count.toLocaleString() : 1}
                  </td>
                  <td>
                    <span className="badge" style={{
                      background: item.container_type?.includes('Player') ? 'rgba(59, 130, 246, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                      color: item.container_type?.includes('Player') ? '#60a5fa' : '#fbbf24',
                      fontSize: '0.75rem'
                    }}>
                      {item.container_type || 'Inventory'}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    {item.base_camp_name ? `🏰 ${item.base_camp_name}` : 'Player Character'}
                  </td>
                </tr>
              ))}
              {sortedInventory.length === 0 && (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                    No items found matching the selected storage criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default InventoryView;
