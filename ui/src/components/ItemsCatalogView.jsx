import React, { useState, useEffect } from 'react';
import { useTableSort } from '../hooks/useTableSort';

export function ItemsCatalogView() {
  const [items, setItems] = useState([]);
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');
  const [selectedRecipeItem, setSelectedRecipeItem] = useState(null);

  useEffect(() => {
    let url = '/api/items?';
    if (category) url += `category=${encodeURIComponent(category)}&`;
    if (search) url += `search=${encodeURIComponent(search)}&`;
    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setItems(data);
      })
      .catch(err => console.error('Error fetching items:', err));
  }, [category, search]);

  const {
    sortedData: sortedItems,
    sortCol,
    sortDesc,
    handleSort,
  } = useTableSort(items, 'name', false);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: '100%', minHeight: 0, overflow: 'hidden' }}>
      <div style={{ flexShrink: 0, marginBottom: '0.75rem' }}>
        <div className="filter-bar glass-card" style={{ marginBottom: '0.5rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Category</label>
            <select value={category} onChange={e => setCategory(e.target.value)}>
              <option value="">All Categories</option>
              <option value="Weapon">Weapons</option>
              <option value="Armor">Armor & Clothing</option>
              <option value="Sphere">Pal Spheres</option>
              <option value="Accessory">Accessories</option>
              <option value="Material">Crafting Materials</option>
              <option value="Food">Consumable Food</option>
              <option value="Medicine">Medical Supplies</option>
              <option value="Essential">Key / Essential Items</option>
            </select>
          </div>
          <div style={{ flexGrow: 1 }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Search</label>
            <input type="text" placeholder="Search items by name or ID..." value={search} onChange={e => setSearch(e.target.value)} />
          </div>
        </div>
      </div>

      <div className="glass-card table-container" style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: 0, marginBottom: '1.5rem' }}>
        <table>
          <thead>
            <tr>
              <th onClick={() => handleSort('name')} style={{ cursor: 'pointer' }}>Item{sortCol === 'name' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
              <th onClick={() => handleSort('category')} style={{ cursor: 'pointer' }}>Category{sortCol === 'category' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
              <th onClick={() => handleSort('rarity')} style={{ cursor: 'pointer' }}>Rarity{sortCol === 'rarity' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
              <th onClick={() => handleSort('price')} style={{ cursor: 'pointer' }}>Price{sortCol === 'price' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
              <th onClick={() => handleSort('weight')} style={{ cursor: 'pointer' }}>Weight{sortCol === 'weight' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
              <th onClick={() => handleSort('max_stack')} style={{ cursor: 'pointer' }}>Max Stack{sortCol === 'max_stack' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
              <th>Description</th>
              <th style={{ textAlign: 'center' }}>Recipe</th>
            </tr>
          </thead>
          <tbody>
            {sortedItems.map(item => (
              <tr key={item.id}>
                <td style={{ fontWeight: 600 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                    {item.icon_path ? (
                      <img src={item.icon_path} alt={item.name} style={{ width: '28px', height: '28px', objectFit: 'contain', borderRadius: '4px', background: 'rgba(0,0,0,0.2)' }} onError={(e) => { e.target.style.display = 'none'; }} />
                    ) : (
                      <span style={{ fontSize: '1.1rem' }}>📦</span>
                    )}
                    <span style={{ color: 'var(--text-primary)' }}>{item.name}</span>
                  </div>
                </td>
                <td>
                  <span className="badge" style={{ background: 'rgba(255,255,255,0.08)', fontSize: '0.72rem' }}>
                    {item.category || 'Item'}
                  </span>
                </td>
                <td style={{ color: 'var(--accent-gold)', whiteSpace: 'nowrap' }}>
                  {'⭐'.repeat(Math.min(item.rarity || 1, 5))}
                </td>
                <td style={{ color: 'var(--accent-gold)', fontWeight: 600 }}>
                  {item.price ? `${item.price}g` : '-'}
                </td>
                <td>{item.weight || 0}</td>
                <td>{item.max_stack || 9999}</td>
                <td style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', maxWidth: '360px' }}>
                  {item.description || '-'}
                </td>
                <td style={{ textAlign: 'center' }}>
                  <button
                    className="btn btn-secondary"
                    style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem', borderRadius: '6px' }}
                    onClick={() => setSelectedRecipeItem(item.id)}
                  >
                    🛠️ Recipe
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Recipe Modal */}
      {selectedRecipeItem && (
        <RecipeModal itemId={selectedRecipeItem} onClose={() => setSelectedRecipeItem(null)} />
      )}
    </div>
  );
}

function RecipeModal({ itemId, onClose }) {
  const [recipe, setRecipe] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/items/${encodeURIComponent(itemId)}/recipe`)
      .then(res => res.json())
      .then(data => {
        setRecipe(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching recipe:', err);
        setLoading(false);
      });
  }, [itemId]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '500px' }}>
        <button className="modal-close-btn" onClick={onClose}>✕</button>
        {loading ? (
          <p style={{ color: 'var(--text-secondary)' }}>Loading recipe...</p>
        ) : recipe && recipe.ingredients && recipe.ingredients.length > 0 ? (
          <div>
            <h3 style={{ fontWeight: 800, marginBottom: '1rem', color: 'var(--accent-gold)' }}>
              🛠️ Crafting Recipe: {recipe.product_name || itemId}
            </h3>
            {recipe.workbench && (
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                Workbench: <strong>{recipe.workbench}</strong>
              </p>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '1rem' }}>
              {recipe.ingredients.map((ing, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0.8rem', background: 'rgba(255,255,255,0.05)', borderRadius: '6px' }}>
                  <span>{ing.item_name || ing.item_id}</span>
                  <span style={{ fontWeight: 700, color: 'var(--accent-gold)' }}>x{ing.count}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p style={{ color: 'var(--text-secondary)' }}>No crafting recipe found for this item.</p>
        )}
      </div>
    </div>
  );
}

export default ItemsCatalogView;
