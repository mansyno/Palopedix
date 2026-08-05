import React, { useState, useEffect, useMemo } from 'react'

const WORK_SUITABILITY_MAP = {
  EmitFlame: 'Kindling',
  Watering: 'Watering',
  Seeding: 'Planting',
  GenerateElectricity: 'Generating Electricity',
  Electricity: 'Generating Electricity',
  Handcraft: 'Handiwork',
  Collection: 'Gathering',
  Deforest: 'Lumbering',
  Wood: 'Lumbering',
  Mining: 'Mining',
  Mine: 'Mining',
  ProductMedicine: 'Medicine Production',
  Medicine: 'Medicine Production',
  Cool: 'Cooling',
  Cooling: 'Cooling',
  Transport: 'Transporting',
  MonsterFarm: 'Farming',
  OilExtraction: 'Oil Extraction',
};

function RecipeModal({ itemId, onClose }) {
  const [recipe, setRecipe] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/items/${encodeURIComponent(itemId)}/recipe`)
      .then(res => res.json())
      .then(data => { setRecipe(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [itemId]);

  if (!itemId) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content recipe-modal-content" onClick={e => e.stopPropagation()}>
        <button className="modal-close-btn" onClick={onClose}>✕</button>
        {loading ? (
          <p style={{ textAlign: 'center', padding: '2rem' }}>Loading crafting recipe...</p>
        ) : recipe && !recipe.detail ? (
          <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: '0.5rem' }}>🛠️ Crafting Recipe: {recipe.item_name}</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
              Work Amount: <strong style={{ color: 'var(--accent-gold)' }}>{recipe.work_amount}</strong> | Facility: {recipe.facility_name || recipe.facility_id || 'Handicraft Table'}
            </p>
            
            <h3 style={{ fontWeight: 700, marginBottom: '1rem' }}>Required Ingredients</h3>
            {recipe.ingredients && recipe.ingredients.map(ing => (
              <div key={ing.material_item_id} className="ingredient-row">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  {ing.icon_path && (
                    <img src={ing.icon_path} alt={ing.material_name} className="item-icon-small" onError={(e) => { e.target.style.display = 'none'; }} />
                  )}
                  <span style={{ fontWeight: 600 }}>{ing.material_name}</span>
                </div>
                <span style={{ fontWeight: 800, color: 'var(--accent-gold)' }}>x{ing.count}</span>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>No crafting recipe available for this item.</p>
        )}
      </div>
    </div>
  );
}

function ItemsCatalogView() {
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
      .then(data => setItems(data))
      .catch(err => console.error("Error fetching items:", err));
  }, [category, search]);

  return (
    <div>
      <div className="filter-bar glass-card">
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
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Search</label>
          <input type="text" placeholder="Search items by name or ID..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1.25rem' }}>
        {items.map(item => (
          <div key={item.id} className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '1.25rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.75rem' }}>
                {item.icon_path ? (
                  <img src={item.icon_path} alt={item.name} className="item-icon-thumb" onError={(e) => { e.target.style.display = 'none'; }} />
                ) : (
                  <div className="item-icon-thumb" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>📦</div>
                )}
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>{item.name}</h3>
                  <span style={{ fontSize: '0.75rem', color: 'var(--accent-gold)' }}>{'⭐'.repeat(Math.min(item.rarity || 1, 5))} ({item.category || 'Item'})</span>
                </div>
              </div>
              {item.description && (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem', lineHeight: 1.4 }}>{item.description}</p>
              )}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.2)', padding: '0.5rem', borderRadius: '8px' }}>
                <div>Price: <strong style={{ color: 'var(--text-primary)' }}>{item.price || 0}g</strong></div>
                <div>Weight: <strong style={{ color: 'var(--text-primary)' }}>{item.weight || 0}</strong></div>
                <div>Max Stack: <strong style={{ color: 'var(--text-primary)' }}>{item.max_stack || 9999}</strong></div>
                {item.defense > 0 && <div>Defense: <strong style={{ color: 'var(--accent-gold)' }}>+{item.defense}</strong></div>}
              </div>
            </div>

            <button className="btn btn-primary" style={{ marginTop: '1rem', width: '100%', fontSize: '0.85rem', padding: '0.5rem' }} onClick={() => setSelectedRecipeItem(item.id)}>
              🛠️ View Crafting Recipe
            </button>
          </div>
        ))}
      </div>

      {selectedRecipeItem && (
        <RecipeModal itemId={selectedRecipeItem} onClose={() => setSelectedRecipeItem(null)} />
      )}
    </div>
  );
}

function BuildingsTechView() {
  const [subTab, setSubTab] = useState('buildings');
  const [buildings, setBuildings] = useState([]);
  const [techTree, setTechTree] = useState([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (subTab === 'buildings') {
      fetch(`/api/buildings?search=${encodeURIComponent(search)}`)
        .then(res => res.json())
        .then(data => setBuildings(data));
    } else {
      fetch(`/api/tech_tree`)
        .then(res => res.json())
        .then(data => setTechTree(data));
    }
  }, [subTab, search]);

  return (
    <div>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
        <button className={`btn ${subTab === 'buildings' ? 'btn-primary' : ''}`} onClick={() => setSubTab('buildings')}>
          🏗️ Base Buildings ({buildings.length})
        </button>
        <button className={`btn ${subTab === 'tech' ? 'btn-primary' : ''}`} onClick={() => setSubTab('tech')}>
          ⚡ Technology Tree ({techTree.length})
        </button>
      </div>

      {subTab === 'buildings' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1.25rem' }}>
          {buildings.map(b => (
            <div key={b.id} className="glass-card" style={{ padding: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.75rem' }}>
                {b.icon_path ? (
                  <img src={b.icon_path} alt={b.name} className="item-icon-thumb" onError={(e) => { e.target.style.display = 'none'; }} />
                ) : (
                  <div className="item-icon-thumb" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>🏰</div>
                )}
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>{b.name}</h3>
                  <span style={{ fontSize: '0.75rem', color: 'var(--accent-gold)' }}>Tech Level: Lv. {b.tech_level} ({b.category || 'Facility'})</span>
                </div>
              </div>
              {b.description && (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>{b.description}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {subTab === 'tech' && (
        <div className="glass-card table-container">
          <table>
            <thead>
              <tr>
                <th>Level</th>
                <th>Technology Node Name</th>
                <th>Points Cost</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {techTree.map(t => (
                <tr key={t.id}>
                  <td style={{ fontWeight: 800, color: 'var(--accent-gold)' }}>Lv. {t.level}</td>
                  <td style={{ fontWeight: 600 }}>{t.name}</td>
                  <td>{t.tech_point_cost} pts</td>
                  <td>
                    {t.is_ancient ? (
                      <span className="badge" style={{ background: 'linear-gradient(135deg, #a855f7, #ec4899)', color: '#fff' }}>⚡ Ancient Technology</span>
                    ) : (
                      <span className="badge" style={{ background: 'rgba(255,255,255,0.1)' }}>Standard</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SkillBadgeWithTooltip({ skill, children, className, style }) {
  const [show, setShow] = useState(false);

  if (!skill) return children || null;

  const typeColor = skill.type === 'Passive' ? '#60a5fa' : skill.type === 'Partner' ? 'var(--accent-gold)' : '#f87171';
  const typeBg = skill.type === 'Passive' ? 'rgba(59, 130, 246, 0.2)' : skill.type === 'Partner' ? 'rgba(234, 179, 8, 0.2)' : 'rgba(239, 68, 68, 0.2)';

  return (
    <div
      className={`skill-tooltip-container ${className || ''}`}
      style={{ position: 'relative', display: 'inline-block', ...style }}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children || (
        <span className="badge badge-element" style={{ cursor: 'pointer' }}>
          {skill.name}
        </span>
      )}

      {show && (
        <div className="skill-tooltip-overlay glass-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
            {skill.icon_path ? (
              <img src={skill.icon_path} alt={skill.name} className="skill-icon-small" onError={(e) => { e.target.style.display = 'none'; }} />
            ) : (
              <div className="skill-icon-small" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, background: 'rgba(255,255,255,0.1)', borderRadius: '6px', width: '24px', height: '24px' }}>⚡</div>
            )}
            <div style={{ textAlign: 'left' }}>
              <strong style={{ fontSize: '0.95rem', color: 'var(--text-primary)', display: 'block', lineHeight: 1.2 }}>{skill.name}</strong>
              <div style={{ display: 'flex', gap: '0.35rem', marginTop: '0.25rem', flexWrap: 'wrap' }}>
                <span className="badge" style={{ background: typeBg, color: typeColor, fontSize: '0.68rem', padding: '0.1rem 0.35rem' }}>{skill.type || 'Skill'}</span>
                {skill.element && <span className="badge badge-element" style={{ fontSize: '0.68rem', padding: '0.1rem 0.35rem' }}>{skill.element}</span>}
                {skill.category && <span className="badge" style={{ background: 'rgba(255,255,255,0.1)', fontSize: '0.68rem', padding: '0.1rem 0.35rem' }}>{skill.category}</span>}
                {skill.rank !== undefined && skill.rank !== null && skill.rank !== 0 && (
                  <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.15)', color: 'var(--accent-gold)', fontSize: '0.68rem', padding: '0.1rem 0.35rem' }}>Rank {skill.rank}</span>
                )}
              </div>
            </div>
          </div>

          {(skill.power > 0 || skill.cooldown_sec > 0 || skill.cooldown > 0) && (
            <div style={{ display: 'flex', gap: '1rem', fontSize: '0.78rem', color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.3)', padding: '0.35rem 0.5rem', borderRadius: '6px', marginBottom: '0.5rem' }}>
              {skill.power > 0 && <span>⚔️ Power: <strong style={{ color: 'var(--text-primary)' }}>{skill.power}</strong></span>}
              {(skill.cooldown_sec || skill.cooldown) > 0 && <span>⏳ Cooldown: <strong style={{ color: 'var(--accent-gold)' }}>{skill.cooldown_sec || skill.cooldown}s</strong></span>}
            </div>
          )}

          {skill.stat_modifier && (
            <p style={{ fontSize: '0.8rem', color: 'var(--accent-green)', fontWeight: 600, margin: '0 0 0.4rem 0', textAlign: 'left' }}>
              ✨ {skill.stat_modifier}
            </p>
          )}

          {skill.unlock_item && (
            <p style={{ fontSize: '0.78rem', color: 'var(--accent-gold)', margin: '0 0 0.4rem 0', textAlign: 'left' }}>
              🔑 Requires: {skill.unlock_item}
            </p>
          )}

          {skill.description ? (
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.35, textAlign: 'left' }}>
              {skill.description}
            </p>
          ) : (
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontStyle: 'italic', margin: 0, textAlign: 'left' }}>
              No detailed description available.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function SkillsCatalogView() {
  const [skills, setSkills] = useState([]);
  const [type, setType] = useState('');
  const [element, setElement] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    let url = '/api/skills?';
    if (type) url += `type=${encodeURIComponent(type)}&`;
    if (element) url += `element=${encodeURIComponent(element)}&`;
    if (search) url += `search=${encodeURIComponent(search)}&`;
    fetch(url)
      .then(res => res.json())
      .then(data => { setSkills(data); setLoading(false); })
      .catch(err => { console.error("Error fetching skills:", err); setLoading(false); });
  }, [type, element, search]);

  return (
    <div>
      <div className="filter-bar glass-card" style={{ marginBottom: '1.5rem' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Skill Type</label>
          <select value={type} onChange={e => setType(e.target.value)}>
            <option value="">All Skill Types (Active, Passive, Partner)</option>
            <option value="Active">⚔️ Active Skills (324)</option>
            <option value="Passive">🛡️ Passive Skills (420)</option>
            <option value="Partner">🤝 Partner Skills (408)</option>
          </select>
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Element</label>
          <select value={element} onChange={e => setElement(e.target.value)}>
            <option value="">All Elements</option>
            <option value="Neutral">Neutral / Normal</option>
            <option value="Fire">Fire</option>
            <option value="Water">Water</option>
            <option value="Grass">Grass / Leaf</option>
            <option value="Electric">Electric</option>
            <option value="Ice">Ice</option>
            <option value="Ground">Ground</option>
            <option value="Dark">Dark</option>
            <option value="Dragon">Dragon</option>
          </select>
        </div>
        <div style={{ flexGrow: 1 }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Search</label>
          <input type="text" placeholder="Search skills by name, description, or ID..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      </div>

      <div style={{ marginBottom: '1rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
        Showing <strong>{skills.length}</strong> matching skills
      </div>

      {loading ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '3rem' }}>
          <p style={{ color: 'var(--text-secondary)' }}>Loading skills database...</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.25rem' }}>
          {skills.map(sk => {
            const typeColor = sk.type === 'Passive' ? '#60a5fa' : sk.type === 'Partner' ? 'var(--accent-gold)' : '#f87171';
            const typeBg = sk.type === 'Passive' ? 'rgba(59, 130, 246, 0.2)' : sk.type === 'Partner' ? 'rgba(234, 179, 8, 0.2)' : 'rgba(239, 68, 68, 0.2)';
            
            return (
              <SkillBadgeWithTooltip key={sk.id} skill={sk} style={{ display: 'block' }}>
                <div className="glass-card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', cursor: 'pointer' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', marginBottom: '0.75rem' }}>
                      {sk.icon_path ? (
                        <img src={sk.icon_path} alt={sk.name} className="skill-icon-large" onError={(e) => { e.target.style.display = 'none'; }} />
                      ) : (
                        <div className="skill-icon-large" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, background: 'rgba(255,255,255,0.1)' }}>⚡</div>
                      )}
                      <div>
                        <h3 style={{ fontSize: '1.15rem', fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>{sk.name}</h3>
                        <div style={{ display: 'flex', gap: '0.35rem', marginTop: '0.3rem', flexWrap: 'wrap' }}>
                          <span className="badge" style={{ background: typeBg, color: typeColor }}>{sk.type || 'Skill'}</span>
                          {sk.element && <span className="badge badge-element">{sk.element}</span>}
                          {sk.category && <span className="badge" style={{ background: 'rgba(255,255,255,0.1)' }}>{sk.category}</span>}
                          {sk.rank !== undefined && sk.rank !== null && sk.rank !== 0 && (
                            <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.15)', color: 'var(--accent-gold)' }}>Rank {sk.rank}</span>
                          )}
                        </div>
                      </div>
                    </div>

                    {(sk.power > 0 || sk.cooldown_sec > 0 || sk.cooldown > 0) && (
                      <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.2)', padding: '0.5rem 0.75rem', borderRadius: '8px', marginBottom: '0.75rem' }}>
                        {sk.power > 0 && <div>⚔️ Power: <strong style={{ color: 'var(--text-primary)' }}>{sk.power}</strong></div>}
                        {(sk.cooldown_sec || sk.cooldown) > 0 && <div>⏳ Cooldown: <strong style={{ color: 'var(--accent-gold)' }}>{sk.cooldown_sec || sk.cooldown}s</strong></div>}
                      </div>
                    )}

                    {sk.stat_modifier && (
                      <p style={{ fontSize: '0.85rem', color: 'var(--accent-green)', fontWeight: 600, marginBottom: '0.5rem' }}>
                        ✨ {sk.stat_modifier}
                      </p>
                    )}

                    {sk.unlock_item && (
                      <p style={{ fontSize: '0.8rem', color: 'var(--accent-gold)', marginBottom: '0.5rem' }}>
                        🔑 Requires: {sk.unlock_item}
                      </p>
                    )}

                    {sk.description ? (
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.4, margin: 0 }}>{sk.description}</p>
                    ) : (
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontStyle: 'italic', margin: 0 }}>No description available.</p>
                    )}
                  </div>
                </div>
              </SkillBadgeWithTooltip>
            );
          })}
        </div>
      )}
    </div>
  );
}

function BaseCampCard({ base }) {
  const [workerSortCol, setWorkerSortCol] = useState('level');
  const [workerSortDesc, setWorkerSortDesc] = useState(true);
  const [workerSearch, setWorkerSearch] = useState('');

  const [structSortCol, setStructSortCol] = useState('count');
  const [structSortDesc, setStructSortDesc] = useState(true);
  const [structSearch, setStructSearch] = useState('');

  const handleWorkerSort = (col) => {
    if (workerSortCol === col) setWorkerSortDesc(!workerSortDesc);
    else { setWorkerSortCol(col); setWorkerSortDesc(true); }
  };

  const handleStructSort = (col) => {
    if (structSortCol === col) setStructSortDesc(!structSortDesc);
    else { setStructSortCol(col); setStructSortDesc(true); }
  };

  const filteredWorkers = base.workers.filter(w => w.display_name.toLowerCase().includes(workerSearch.toLowerCase()));
  const sortedWorkers = [...filteredWorkers].sort((a, b) => {
    let valA = a[workerSortCol];
    let valB = b[workerSortCol];
    if (valA < valB) return workerSortDesc ? 1 : -1;
    if (valA > valB) return workerSortDesc ? -1 : 1;
    return 0;
  });

  const filteredStructs = base.structures.filter(s => (s.display_name || s.structure_name).toLowerCase().includes(structSearch.toLowerCase()));
  const sortedStructs = [...filteredStructs].sort((a, b) => {
    let nameA = a.display_name || a.structure_name;
    let nameB = b.display_name || b.structure_name;
    let valA = structSortCol === 'name' ? nameA : a[structSortCol];
    let valB = structSortCol === 'name' ? nameB : b[structSortCol];
    if (valA < valB) return structSortDesc ? 1 : -1;
    if (valA > valB) return structSortDesc ? -1 : 1;
    return 0;
  });

  return (
    <div className="glass-card">
      <h2 style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem', fontWeight: 800 }}>
        🏰 {base.name}
      </h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        
        {/* Worker summary */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ color: 'var(--text-secondary)' }}>Workers ({base.workers.length})</h3>
            <input type="text" placeholder="Search pals..." value={workerSearch} onChange={e => setWorkerSearch(e.target.value)} style={{ padding: '0.4rem 0.8rem', width: '150px' }} />
          </div>
          <div className="glass-card table-container" style={{ padding: '0', background: 'rgba(0,0,0,0.2)' }}>
            <table>
              <thead>
                <tr>
                  <th onClick={() => handleWorkerSort('display_name')} style={{cursor:'pointer'}}>Species{workerSortCol === 'display_name' ? (workerSortDesc ? ' ▼' : ' ▲') : ''}</th>
                  <th onClick={() => handleWorkerSort('level')} style={{cursor:'pointer'}}>Level{workerSortCol === 'level' ? (workerSortDesc ? ' ▼' : ' ▲') : ''}</th>
                  <th onClick={() => handleWorkerSort('gender')} style={{cursor:'pointer'}}>Gender{workerSortCol === 'gender' ? (workerSortDesc ? ' ▼' : ' ▲') : ''}</th>
                  <th onClick={() => handleWorkerSort('rank')} style={{cursor:'pointer'}}>Rank{workerSortCol === 'rank' ? (workerSortDesc ? ' ▼' : ' ▲') : ''}</th>
                  <th>Passives</th>
                </tr>
              </thead>
              <tbody>
                {sortedWorkers.map((w, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600 }}>
                      <div className="pal-avatar-container">
                        {w.icon_path && (
                          <img src={w.icon_path} alt={w.display_name} className="pal-avatar-small" onError={(e) => { e.target.style.display = 'none'; }} />
                        )}
                        <span>{w.display_name}</span>
                      </div>
                    </td>
                    <td>Lv. {w.level}</td>
                    <td>{w.gender}</td>
                    <td>{w.rank} ⭐</td>
                    <td>
                      <div className="badge-container">
                        {w.passives && w.passives.map(pass => (
                          <span key={pass.id} className="badge badge-element" title={pass.description}>{pass.name}</span>
                        ))}
                        {(!w.passives || w.passives.length === 0) && <span style={{ color: 'var(--text-secondary)' }}>None</span>}
                      </div>
                    </td>
                  </tr>
                ))}
                {sortedWorkers.length === 0 && (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>No workers match search.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        
        {/* Structure inventories */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ color: 'var(--text-secondary)' }}>Camp Structures</h3>
            <input type="text" placeholder="Search structures..." value={structSearch} onChange={e => setStructSearch(e.target.value)} style={{ padding: '0.4rem 0.8rem', width: '150px' }} />
          </div>
          <div className="glass-card table-container" style={{ padding: '0', background: 'rgba(0,0,0,0.2)' }}>
            <table>
              <thead>
                <tr>
                  <th onClick={() => handleStructSort('count')} style={{cursor:'pointer'}}>Count{structSortCol === 'count' ? (structSortDesc ? ' ▼' : ' ▲') : ''}</th>
                  <th onClick={() => handleStructSort('name')} style={{cursor:'pointer'}}>Structure Name{structSortCol === 'name' ? (structSortDesc ? ' ▼' : ' ▲') : ''}</th>
                </tr>
              </thead>
              <tbody>
                {sortedStructs.map((s, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 700, color: 'var(--accent-gold)' }}>{s.count}x</td>
                    <td>{s.display_name || s.structure_name}</td>
                  </tr>
                ))}
                {sortedStructs.length === 0 && (
                  <tr>
                    <td colSpan="2" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>No structures match search.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}



function InventoryView() {
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    let url = '/api/save/inventory';
    if (filterType) url += `?container_type=${encodeURIComponent(filterType)}`;
    fetch(url)
      .then(res => res.json())
      .then(data => { setInventory(data); setLoading(false); })
      .catch(err => { console.error(err); setLoading(false); });
  }, [filterType]);

  if (loading) return <p style={{ color: 'var(--text-secondary)' }}>Loading inventory from save game...</p>;

  const filteredItems = inventory.filter(item => 
    (item.display_name && item.display_name.toLowerCase().includes(search.toLowerCase())) ||
    (item.item_id && item.item_id.toLowerCase().includes(search.toLowerCase()))
  );

  // Group by container type
  const grouped = filteredItems.reduce((acc, item) => {
    const type = item.container_type || 'Other';
    if (!acc[type]) acc[type] = [];
    acc[type].push(item);
    return acc;
  }, {});

  return (
    <div>
      <div className="filter-bar glass-card" style={{ marginBottom: '1.5rem' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Container Type</label>
          <select value={filterType} onChange={e => setFilterType(e.target.value)}>
            <option value="">All Storage / Inventories</option>
            <option value="Inventory">Personal Inventory</option>
            <option value="Key Items">Key Items</option>
            <option value="Weapon Loadout">Weapon Loadout</option>
            <option value="Equipped Armor">Equipped Armor</option>
            <option value="Food Equip">Food Equip</option>
            <option value="Base Chest">Base Chests</option>
          </select>
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Search</label>
          <input type="text" placeholder="Search items in save file..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      </div>

      {Object.keys(grouped).length === 0 ? (
        <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>No inventory items found. Make sure a save game is loaded.</p>
      ) : (
        Object.entries(grouped).map(([type, items]) => (
          <div key={type} className="glass-card" style={{ marginBottom: '1.5rem', padding: '1.25rem' }}>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
              📦 {type} ({items.length} stack{items.length !== 1 ? 's' : ''})
            </h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '1rem' }}>
              {items.map((item, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
                  {item.icon_path ? (
                    <img src={item.icon_path} alt={item.display_name} className="item-icon-thumb" onError={(e) => { e.target.style.display = 'none'; }} />
                  ) : (
                    <div className="item-icon-thumb" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>📦</div>
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: '0.95rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.display_name}</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                      <span>Slot {item.slot_index + 1}</span>
                      <strong style={{ color: 'var(--accent-gold)' }}>x{item.count.toLocaleString()}</strong>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}


function WelcomeView({ onNavigate, currentWorld, instancesCount, basesCount, inventoryCount }) {
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

  function round(val, dec) {
    return Number(Math.round(val + 'e' + dec) + 'e-' + dec);
  }
}




function HomepageView({ onSelectMode, currentWorld, instancesCount, basesCount, inventoryCount }) {
  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '3rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '3rem' }}>
      <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
        <div className="logo-icon" style={{ width: '64px', height: '64px', fontSize: '2rem', borderRadius: '18px' }}>P</div>
        <h1 style={{ fontSize: '3.2rem', fontWeight: 800, background: 'var(--primary-gradient)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Palopedix
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem', maxWidth: '600px' }}>
          Palworld Master Database & Save Game Analytics
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '2rem' }}>
        {/* Card 1: Global Data */}
        <div 
          className="glass-card table-row-hover" 
          onClick={() => onSelectMode('global', 'paldex')}
          style={{ padding: '2rem', borderRadius: '18px', cursor: 'pointer', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '340px', border: '1px solid var(--border-color-hover)' }}
        >
          <div>
            <div style={{ width: '56px', height: '56px', borderRadius: '14px', background: 'rgba(99, 102, 241, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '2rem', marginBottom: '1.25rem', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
              🌐
            </div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: '0.5rem' }}>Global Game Data</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: '1.5rem' }}>
              Explore master Pal specifications, item recipes, technology trees, and breeding combinations directly from game files.
            </p>
          </div>
          <div>
            <button className="primary-btn" style={{ width: '100%', padding: '0.85rem', fontSize: '0.95rem' }}>
              Explore Global Data →
            </button>
          </div>
        </div>

        {/* Card 2: Active World Data */}
        <div 
          className="glass-card table-row-hover" 
          onClick={() => onSelectMode('world', 'world_overview')}
          style={{ padding: '2rem', borderRadius: '18px', cursor: 'pointer', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '340px', border: '1px solid rgba(56, 189, 248, 0.3)' }}
        >
          <div>
            <div style={{ width: '56px', height: '56px', borderRadius: '14px', background: 'rgba(56, 189, 248, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '2rem', marginBottom: '1.25rem', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
              🌍
            </div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: '0.5rem' }}>Active World Data</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: '1.5rem' }}>
              Inspect live save file analytics for your selected active world. Audit captured Pals & IVs, personal inventory, storage chests, and condenser candidates.
            </p>
          </div>
          <div>
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '0.65rem 0.85rem', borderRadius: '8px', marginBottom: '1.25rem', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Selected Active World:</div>
              <strong style={{ color: '#38bdf8', fontSize: '0.95rem' }}>{currentWorld ? currentWorld.display_name : 'No World Loaded'}</strong>
            </div>
            <button className="primary-btn" style={{ width: '100%', padding: '0.85rem', fontSize: '0.95rem', background: 'linear-gradient(135deg, #0284c7 0%, #06b6d4 100%)' }}>
              Explore World Data →
            </button>
          </div>
        </div>

        {/* Card 3: Settings */}
        <div 
          className="glass-card table-row-hover" 
          onClick={() => onSelectMode('settings', 'settings')}
          style={{ padding: '2rem', borderRadius: '18px', cursor: 'pointer', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '340px', border: '1px solid var(--border-color)' }}
        >
          <div>
            <div style={{ width: '56px', height: '56px', borderRadius: '14px', background: 'rgba(148, 163, 184, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '2rem', marginBottom: '1.25rem', border: '1px solid rgba(148, 163, 184, 0.3)' }}>
              ⚙️
            </div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: '0.5rem' }}>Settings & System</h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: '1.5rem' }}>
              Configure manual Level.sav file paths, scan local Steam save directories, and select database sources for PalEngine.
            </p>
          </div>
          <div>
            <button className="secondary-btn" style={{ width: '100%', padding: '0.85rem', fontSize: '0.95rem' }}>
              Open Settings →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function WorldOverviewView({ currentWorld, instancesCount, basesCount, inventoryCount, onNavigate }) {
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

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
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

        <div className="glass-card table-row-hover" onClick={() => onNavigate('condenser')} style={{ padding: '1.5rem', borderRadius: '12px', cursor: 'pointer' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>⭐</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Condenser Candidates</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#38bdf8' }}>Active</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--accent-gold)', marginTop: '0.5rem' }}>Find Candidates →</div>
        </div>
      </div>
    </div>
  );
}


function SettingsView({ savePath, setSavePath, handleLoadSave, loading, errorMsg, successMsg }) {
  const [staticSource, setStaticSource] = useState('palworld_db');

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
          <div style={{ marginTop: '1rem', color: 'var(--accent-green)', background: 'rgba(16,185,129,0.1)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--accent-green)' }}>
            {successMsg}
          </div>
        )}
      </div>

      {/* Static Engine Source Box */}
      <div className="glass-card" style={{ padding: '1.75rem' }}>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          ⚙️ Static Database Source
        </h3>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
          Choose the data source used for master Pal specs, skill data, and item definitions.
        </p>

        <div style={{ display: 'flex', gap: '1.5rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
            <input
              type="radio"
              name="staticSource"
              value="palworld_db"
              checked={staticSource === 'palworld_db'}
              onChange={(e) => setStaticSource(e.target.value)}
            />
            <span><strong>Master SQLite Database (Recommended)</strong> — palworld.db (1.0+ Game Data)</span>
          </label>
        </div>
      </div>
    </div>
  );
}


function CondenserView() {
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/save/condense')
      .then(res => res.json())
      .then(data => { setCandidates(data); setLoading(false); })
      .catch(err => { console.error(err); setLoading(false); });
  }, []);

  if (loading) return <p style={{ color: 'var(--text-secondary)' }}>Calculating condenser candidates...</p>;
  if (!candidates || candidates.length === 0) return <p style={{ color: 'var(--text-secondary)' }}>No save file loaded or no duplicate Pals found.</p>;

  return (
    <div style={{ display: 'grid', gap: '1.5rem' }}>
      <h2 style={{ marginBottom: '0.5rem', fontWeight: 800 }}>⭐ Condenser Recommendations</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>Based on duplicates, passives, and IVs. The max rank is calculated based on exactly 5, 13, 25, or 49 total Pals needed.</p>
      
      {candidates.map((c, i) => (
        <div key={i} className="glass-card" style={{ display: 'flex', gap: '2rem', padding: '1.5rem' }}>
          <div style={{ flex: '0 0 120px', textAlign: 'center' }}>
            {c.icon_path ? (
              <img src={c.icon_path} alt={c.species} style={{ width: '100px', height: '100px', borderRadius: '15px', objectFit: 'cover' }} />
            ) : (
              <div style={{ width: '100px', height: '100px', borderRadius: '15px', background: 'var(--primary-gradient)', margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '2rem', fontWeight: 800 }}>{c.species[0]}</div>
            )}
            <h3 style={{ marginTop: '0.5rem', fontSize: '1.1rem', fontWeight: 700 }}>{c.species}</h3>
            <div style={{ color: 'var(--accent-gold)', fontWeight: 800, fontSize: '1.2rem', marginTop: '0.2rem' }}>
              {c.attainable_stars > 0 ? '⭐'.repeat(c.attainable_stars) : '0 ⭐'}
            </div>
          </div>
          
          <div style={{ flex: 1 }}>
            <h4 style={{ fontWeight: 800, borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
              Total Owned: {c.total_owned} (1 Base + {c.sacrifices_available} Sacrifices)
            </h4>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Best Base Level</p>
                <p style={{ fontWeight: 700, fontSize: '1.1rem' }}>Lv. {c.base_level}</p>
                
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.75rem' }}>Passives</p>
                <div className="badge-container" style={{ marginTop: '0.25rem' }}>
                  {c.passives && c.passives.length > 0 ? c.passives.map((p, idx) => (
                    <span key={idx} className="badge badge-element">{p}</span>
                  )) : <span style={{ color: 'var(--text-secondary)' }}>None</span>}
                </div>
              </div>
              
              <div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '8px' }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>HP</div>
                    <div style={{ fontWeight: 800, color: 'var(--text-primary)' }}>{c.hp}</div>
                    <div style={{ color: 'var(--accent-gold)', fontSize: '0.8rem' }}>IV {c.iv_hp}</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Attack</div>
                    <div style={{ fontWeight: 800, color: 'var(--text-primary)' }}>{c.attack}</div>
                    <div style={{ color: 'var(--accent-gold)', fontSize: '0.8rem' }}>IV {c.iv_attack}</div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Defense</div>
                    <div style={{ fontWeight: 800, color: 'var(--text-primary)' }}>{c.defense}</div>
                    <div style={{ color: 'var(--accent-gold)', fontSize: '0.8rem' }}>IV {c.iv_defense}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}


function PalDetailModal({ pal, onClose }) {
  if (!pal) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <button className="modal-close-btn" onClick={onClose}>✕</button>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem' }}>
          {/* Left Column: Image & Bio */}
          <div>
            <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
              {pal.icon_path ? (
                <img src={pal.icon_path} alt={pal.display_name} style={{ width: '128px', height: '128px', borderRadius: '20px', border: '2px solid var(--border-color-hover)', objectFit: 'cover', background: 'rgba(0,0,0,0.3)', boxShadow: '0 8px 25px rgba(0,0,0,0.5)' }} />
              ) : (
                <div style={{ width: '128px', height: '128px', borderRadius: '20px', background: 'var(--primary-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto', fontSize: '3rem', fontWeight: 800 }}>
                  {pal.display_name ? pal.display_name[0] : 'P'}
                </div>
              )}
              <h2 style={{ fontSize: '1.75rem', fontWeight: 800, marginTop: '1rem' }}>{pal.display_name}</h2>
              <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>#{String(pal.paldex_number || 0).padStart(3, '0')}</span>
              
              <div className="badge-container" style={{ justifyContent: 'center', marginTop: '0.5rem' }}>
                {pal.element_1 && (
                  <span className="badge badge-element" style={{ display: 'inline-flex', alignItems: 'center' }}>
                    <img src={`/assets/elements/${pal.element_1}.png`} alt={pal.element_1} className="element-icon-badge" onError={(e) => { e.target.style.display = 'none'; }} />
                    {pal.element_1}
                  </span>
                )}
                {pal.element_2 && (
                  <span className="badge badge-element" style={{ display: 'inline-flex', alignItems: 'center' }}>
                    <img src={`/assets/elements/${pal.element_2}.png`} alt={pal.element_2} className="element-icon-badge" onError={(e) => { e.target.style.display = 'none'; }} />
                    {pal.element_2}
                  </span>
                )}
              </div>
            </div>

            {pal.description && (
              <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '0.95rem', marginBottom: '1.5rem', lineHeight: 1.5, background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '12px' }}>
                "{pal.description}"
              </p>
            )}

            <div className="glass-card" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.9rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Size</span>
                <span style={{ fontWeight: 600 }}>{pal.size || 'M'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Habit</span>
                <span style={{ fontWeight: 600 }}>{pal.nocturnal ? '🌙 Nocturnal' : '☀️ Diurnal'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Food Need</span>
                <span style={{ fontWeight: 600 }}>🍖 {pal.food_requirement || 1}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Breeding Power</span>
                <span style={{ fontWeight: 600, color: 'var(--accent-gold)' }}>{pal.breeding_power}</span>
              </div>
              {pal.rarity && (
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Rarity</span>
                  <span style={{ fontWeight: 600, color: 'var(--accent-gold)' }}>{'⭐'.repeat(Math.min(pal.rarity, 5))} ({pal.rarity})</span>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Base Stats, Suitabilities, Skills & Drops */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Base Stats */}
            <div>
              <h3 style={{ fontWeight: 700, marginBottom: '0.75rem', color: 'var(--text-primary)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
                📊 Base Stats
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <div className="stat-label"><span>HP</span><span style={{fontWeight:700}}>{pal.hp || pal.attack_melee || 'N/A'}</span></div>
                  <div className="stat-bar"><div className="stat-fill" style={{ width: `${Math.min(((pal.hp || 70)/150)*100, 100)}%` }}></div></div>
                </div>
                <div>
                  <div className="stat-label"><span>Attack</span><span style={{fontWeight:700}}>{pal.attack_melee || 'N/A'}</span></div>
                  <div className="stat-bar"><div className="stat-fill" style={{ width: `${Math.min(((pal.attack_melee || 70)/150)*100, 100)}%`, background: 'linear-gradient(135deg, #ef4444, #f97316)' }}></div></div>
                </div>
                <div>
                  <div className="stat-label"><span>Defense</span><span style={{fontWeight:700}}>{pal.defense || 'N/A'}</span></div>
                  <div className="stat-bar"><div className="stat-fill" style={{ width: `${Math.min(((pal.defense || 70)/150)*100, 100)}%`, background: 'linear-gradient(135deg, #3b82f6, #06b6d4)' }}></div></div>
                </div>
                <div>
                  <div className="stat-label"><span>Work / Run Speed</span><span style={{fontWeight:700}}>{pal.work_speed || pal.run_speed || 'N/A'}</span></div>
                  <div className="stat-bar"><div className="stat-fill" style={{ width: `${Math.min(((pal.work_speed || 400)/700)*100, 100)}%`, background: 'linear-gradient(135deg, #10b981, #34d399)' }}></div></div>
                </div>
              </div>
            </div>

            {/* Work Suitabilities */}
            {(pal.work_suitability_details && pal.work_suitability_details.length > 0) ? (
              <div>
                <h3 style={{ fontWeight: 700, marginBottom: '0.75rem', color: 'var(--text-primary)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
                  🛠️ Work Suitabilities
                </h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {pal.work_suitability_details.map(wsd => (
                    <span key={wsd.id} className="suitability-pill" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
                      {wsd.icon_path && (
                        <img src={wsd.icon_path} alt={wsd.name} className="work-hud-icon" onError={(e) => { e.target.style.display = 'none'; }} />
                      )}
                      <span>{wsd.name}</span>
                      <span style={{ color: 'var(--accent-gold)', fontWeight: 800 }}>Lv. {wsd.level}</span>
                    </span>
                  ))}
                </div>
              </div>
            ) : (pal.work_suitabilities && Object.keys(pal.work_suitabilities).length > 0) && (
              <div>
                <h3 style={{ fontWeight: 700, marginBottom: '0.75rem', color: 'var(--text-primary)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
                  🛠️ Work Suitabilities
                </h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {Object.entries(pal.work_suitabilities).map(([work, level]) => (
                    <span key={work} className="suitability-pill">
                      <span>{WORK_SUITABILITY_MAP[work] || work}</span>
                      <span style={{ color: 'var(--accent-gold)', fontWeight: 800 }}>Lv. {level}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Partner Skill */}
            {pal.partner_skill && (
              <SkillBadgeWithTooltip skill={pal.partner_skill} style={{ display: 'block', width: '100%' }}>
                <div style={{ background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.15), rgba(168, 85, 247, 0.15))', border: '1px solid var(--accent-gold)', borderRadius: '12px', padding: '1rem', marginBottom: '0.5rem', cursor: 'pointer' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                    <h4 style={{ fontWeight: 800, color: 'var(--accent-gold)', margin: 0, fontSize: '1rem' }}>🤝 Partner Skill: {pal.partner_skill.name}</h4>
                    {pal.partner_skill.unlock_item && (
                      <span className="badge" style={{ background: 'rgba(255,255,255,0.1)' }}>Req: {pal.partner_skill.unlock_item}</span>
                    )}
                  </div>
                  {pal.partner_skill.description && (
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', margin: 0, lineHeight: 1.4 }}>{pal.partner_skill.description}</p>
                  )}
                </div>
              </SkillBadgeWithTooltip>
            )}

            {/* Species Default Active & Passive Skills */}
            {pal.skills && pal.skills.filter(sk => sk.type !== 'Partner' && sk.category !== 'Partner').length > 0 && (
              <div>
                <h3 style={{ fontWeight: 700, marginBottom: '0.75rem', color: 'var(--text-primary)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
                  ⚔️ Active & Passive Skills ({pal.skills.filter(sk => sk.type !== 'Partner' && sk.category !== 'Partner').length})
                </h3>
                <div style={{ maxHeight: '250px', overflowY: 'auto', paddingRight: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {pal.skills.filter(sk => sk.type !== 'Partner' && sk.category !== 'Partner').map(sk => (
                    <SkillBadgeWithTooltip key={sk.id} skill={sk} style={{ display: 'block', width: '100%' }}>
                      <div className="skill-row" style={{ cursor: 'pointer' }}>
                        {sk.icon_path ? (
                          <img src={sk.icon_path} alt={sk.name} className="skill-icon-large" onError={(e) => { e.target.style.display = 'none'; }} />
                        ) : (
                          <div className="skill-icon-large" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>⚡</div>
                        )}
                        <div style={{ flexGrow: 1 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <span style={{ fontWeight: 700 }}>{sk.name}</span>
                              {sk.is_guaranteed === 1 && (
                                <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.2)', color: 'var(--accent-gold)', fontSize: '0.7rem' }}>Guaranteed</span>
                              )}
                            </div>
                            <div className="badge-container">
                              {sk.element && <span className="badge badge-element">{sk.element}</span>}
                              <span className="badge" style={{ background: sk.type === 'Passive' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(239, 68, 68, 0.2)', color: sk.type === 'Passive' ? '#60a5fa' : '#f87171' }}>{sk.type}</span>
                            </div>
                          </div>
                          {sk.description && <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>{sk.description}</p>}
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.35rem', display: 'flex', gap: '1rem' }}>
                            {sk.stat_modifier && <span style={{ color: 'var(--accent-green)', fontWeight: 700 }}>Modifier: {sk.stat_modifier}</span>}
                            {sk.power > 0 && <span>Power: <strong style={{color: 'var(--accent-gold)'}}>{sk.power}</strong></span>}
                            {sk.cooldown > 0 && <span>CD: <strong style={{color: 'var(--text-primary)'}}>{sk.cooldown}s</strong></span>}
                            <span>Level Learned: <strong>Lv. {sk.level_learned || 1}</strong></span>
                          </div>
                        </div>
                      </div>
                    </SkillBadgeWithTooltip>
                  ))}
                </div>
              </div>
            )}

            {/* Item Drops */}
            {pal.drops && pal.drops.length > 0 && (
              <div>
                <h3 style={{ fontWeight: 700, marginBottom: '0.75rem', color: 'var(--text-primary)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
                  🎁 Possible Item Drops
                </h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
                  {pal.drops.map((d, idx) => (
                    <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 0.85rem', background: 'rgba(255,255,255,0.05)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', fontSize: '0.875rem' }}>
                      {d.icon_path && (
                        <img src={d.icon_path} alt={d.item_name} className="item-icon-small" onError={(e) => { e.target.style.display = 'none'; }} />
                      )}
                      <span style={{ fontWeight: 600 }}>{d.item_name}</span>
                      <span style={{ color: 'var(--text-secondary)' }}>({d.min_quantity}-{d.max_quantity}x @ {(d.drop_rate * 100).toFixed(0)}%)</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
    const [mode, setMode] = useState('home') // 'home', 'global', 'world', 'settings'
  const [activeTab, setActiveTab] = useState('paldex')
  const [worlds, setWorlds] = useState([])
  const [selectedWorldId, setSelectedWorldId] = useState('')
  const [worldLoading, setWorldLoading] = useState(false)

  // Fetch discovered active worlds
  const fetchWorlds = async () => {
    try {
      const res = await fetch('/api/worlds')
      const data = await res.json()
      setWorlds(data.worlds || [])
      if (data.current_world_id) {
        setSelectedWorldId(data.current_world_id)
      }
    } catch (e) {
      console.error("Error fetching worlds", e)
    }
  }

  useEffect(() => {
    fetchWorlds()
  }, [])

    const handleSelectMode = (newMode, defaultTab) => {
    setMode(newMode);
    if (defaultTab) setActiveTab(defaultTab);
  };

  const handleSelectWorld = async (worldId) => {
    if (!worldId || worldId === selectedWorldId) return
    setWorldLoading(true)
    try {
      const res = await fetch('/api/worlds/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ world_id: worldId })
      })
      const data = await res.json()
      if (res.ok) {
        setSelectedWorldId(data.world_id)
        setSaveLoaded(true)
        fetchInstances()
        fetchBases()
      }
    } catch (e) {
      console.error("Error selecting world", e)
    } finally {
      setWorldLoading(false)
    }
  }

  const [savePath, setSavePath] = useState('')
  const [saveLoaded, setSaveLoaded] = useState(false)
  const [loadedPath, setLoadedPath] = useState('')
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  // Pals Tab States
  const [pals, setPals] = useState([])
  const [selectedPal, setSelectedPal] = useState(null)
  const [elementFilter, setElementFilter] = useState('')
  const [sizeFilter, setSizeFilter] = useState('')
  const [nocturnalFilter, setNocturnalFilter] = useState('')
  const [suitabilityFilter, setSuitabilityFilter] = useState('')

  // Save Game Tab States
  const [instances, setInstances] = useState([])
  const [locFilter, setLocFilter] = useState('')
  const [specFilter, setSpecFilter] = useState('')
  const [genderFilter, setGenderFilter] = useState('')
  const [minLvlFilter, setMinLvlFilter] = useState('')
  const [passiveFilter, setPassiveFilter] = useState('')
  const [sortCol, setSortCol] = useState('level')
  const [sortDesc, setSortDesc] = useState(true)

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDesc(!sortDesc)
    } else {
      setSortCol(col)
      setSortDesc(true)
    }
  }

  const sortedInstances = [...instances].sort((a, b) => {
    let valA = a[sortCol]
    let valB = b[sortCol]
    if (valA < valB) return sortDesc ? 1 : -1
    if (valA > valB) return sortDesc ? -1 : 1
    return 0
  })
  // Bases Tab States
  const [bases, setBases] = useState([])

  // Breeding Tab States
  const [parent1, setParent1] = useState('')
  const [parent2, setParent2] = useState('')
  const [breedResult, setBreedResult] = useState(null)
  const [breedError, setBreedError] = useState('')

  const [reverseChild, setReverseChild] = useState('')
  const [parentCombos, setParentCombos] = useState([])
  const [reverseLoading, setReverseLoading] = useState(false)
  const [reverseSearched, setReverseSearched] = useState(false)
  const [reverseSearchTerm, setReverseSearchTerm] = useState('')

  const [ownedPals, setOwnedPals] = useState('')
  const [targetPal, setTargetPal] = useState('')
  const [breedingPath, setBreedingPath] = useState([])
  const [pathLoading, setPathLoading] = useState(false)
  const [pathSearched, setPathSearched] = useState(false)
  const [pathError, setPathError] = useState('')
  const [useSaveOwned, setUseSaveOwned] = useState(true)

  const [ownedSpecies, setOwnedSpecies] = useState([])
  const [palSourceMode, setPalSourceMode] = useState('global')

  const availablePalOptions = useMemo(() => {
    if (palSourceMode === 'caught' && saveLoaded && ownedSpecies.length > 0) {
      return ownedSpecies
    }
    if (pals && pals.length > 0) {
      return Array.from(new Set(pals.map(p => p.display_name))).sort()
    }
    return []
  }, [palSourceMode, saveLoaded, ownedSpecies, pals])

  // Fetch Pals on startup
  useEffect(() => {
    fetchPals()
  }, [elementFilter, sizeFilter, nocturnalFilter, suitabilityFilter])

  // Check save status on mount
  useEffect(() => {
    fetch('/api/save/status')
      .then(res => res.json())
      .then(data => {
        if (data.loaded) {
          setSaveLoaded(true)
          setLoadedPath(data.path || 'Previous Session')
          fetchOwnedSpecies()
        }
      })
      .catch(err => console.error("Error checking save status:", err))
  }, [])

  const fetchOwnedSpecies = async () => {
    try {
      const res = await fetch('/api/save/owned-species')
      const data = await res.json()
      if (res.ok && Array.isArray(data)) {
        setOwnedSpecies(data)
      }
    } catch (e) {
      console.error("Error fetching owned species", e)
    }
  }

  const fetchPals = async () => {
    try {
      let url = '/api/pals?'
      if (elementFilter) url += `element=${elementFilter}&`
      if (sizeFilter) url += `size=${sizeFilter}&`
      if (nocturnalFilter) url += `nocturnal=${nocturnalFilter === 'true'}&`
      if (suitabilityFilter) url += `suitability=${suitabilityFilter}&`
      
      const res = await fetch(url)
      const data = await res.json()
      setPals(data)
    } catch (e) {
      console.error("Error fetching pals", e)
    }
  }

  // Handle Loading save
  const handleLoadSave = async () => {
    setLoading(true)
    setErrorMsg('')
    setSuccessMsg('')
    try {
      const res = await fetch('/api/save/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ save_path: savePath || null })
      })
      const data = await res.json()
      if (res.ok) {
        setSaveLoaded(true)
        setLoadedPath(data.path)
        setSuccessMsg(data.message)
        fetchInstances()
        fetchBases()
        fetchOwnedSpecies()
      } else {
        setErrorMsg(data.detail || "Failed to load save file.")
      }
    } catch (e) {
      setErrorMsg("Error making request to backend.")
    } finally {
      setLoading(false)
    }
  }

  // Fetch Dynamic instances
  const fetchInstances = async () => {
    try {
      let url = '/api/save/instances?'
      if (locFilter) url += `location=${locFilter}&`
      if (specFilter) url += `species=${specFilter}&`
      if (genderFilter) url += `gender=${genderFilter}&`
      if (minLvlFilter) url += `min_level=${minLvlFilter}&`
      if (passiveFilter) url += `passive=${passiveFilter}&`

      const res = await fetch(url)
      const data = await res.json()
      setInstances(data)
    } catch (e) {
      console.error("Error fetching instances", e)
    }
  }

  useEffect(() => {
    if (saveLoaded) {
      fetchInstances()
      fetchOwnedSpecies()
    }
  }, [locFilter, specFilter, genderFilter, minLvlFilter, passiveFilter, saveLoaded])

  // Fetch Bases
  const fetchBases = async () => {
    try {
      const res = await fetch('/api/bases')
      const data = await res.json()
      setBases(data)
    } catch (e) {
      console.error("Error fetching bases", e)
    }
  }

  // Calculate Breed Result
  const handleCalculateBreed = async () => {
    if (!parent1 || !parent2) return
    setBreedError('')
    try {
      const res = await fetch(`/api/breeding/result?parent1=${encodeURIComponent(parent1)}&parent2=${encodeURIComponent(parent2)}`)
      const data = await res.json()
      if (res.ok) {
        setBreedResult(data)
      } else {
        setBreedResult(null)
        setBreedError(data.detail || "Could not calculate breeding result.")
      }
    } catch (e) {
      console.error("Error calculating breeding result", e)
      setBreedError("Failed to calculate breeding result.")
    }
  }

  // Calculate Reverse Parents
  const handleCalculateReverse = async () => {
    if (!reverseChild) return
    setReverseLoading(true)
    setReverseSearched(true)
    setReverseSearchTerm(reverseChild)
    try {
      const res = await fetch(`/api/breeding/parents?child=${encodeURIComponent(reverseChild)}`)
      const data = await res.json()
      if (res.ok) {
        setParentCombos(data)
      } else {
        setParentCombos([])
      }
    } catch (e) {
      console.error("Error finding parents", e)
      setParentCombos([])
    } finally {
      setReverseLoading(false)
    }
  }

  const [allBreedingPaths, setAllBreedingPaths] = useState([])
  const [activePathIdx, setActivePathIdx] = useState(0)

  // Find Breed Path
  const handleFindPath = async () => {
    if (!targetPal) return
    setPathLoading(true)
    setPathSearched(true)
    setPathError('')
    setActivePathIdx(0)
    try {
      let url = `/api/breeding/path?target=${encodeURIComponent(targetPal)}`
      if (useSaveOwned && saveLoaded) {
        url += '&owned=auto'
      } else if (ownedPals) {
        url += `&owned=${encodeURIComponent(ownedPals)}`
      } else {
        url += '&owned=auto'
      }
      const res = await fetch(url)
      const data = await res.json()
      if (res.ok) {
        const paths = data.paths || []
        setAllBreedingPaths(paths)
        if (paths.length > 0) {
          setBreedingPath(paths[0].steps || [])
        } else {
          setBreedingPath([])
          setPathError(`No multi-generation breeding path found to ${targetPal} with available Pals.`)
        }
      } else {
        setAllBreedingPaths([])
        setBreedingPath([])
        setPathError(data.detail || "Error finding breeding path.")
      }
    } catch (e) {
      console.error("Error finding breeding path", e)
      setPathError("Failed to communicate with backend.")
    } finally {
      setPathLoading(false)
    }
  }

  return (
    <div className="dashboard-container" style={{ paddingLeft: mode === 'home' ? 0 : '280px' }}>
      {/* Sidebar navigation */}
      {mode !== 'home' && (
        <aside className="sidebar">
          <div className="logo-area" onClick={() => setMode('home')} style={{ cursor: 'pointer' }}>
            <div className="logo-icon">P</div>
            <div className="logo-text">Palopedix</div>
          </div>

          <nav className="nav-links">
            <div 
              className="nav-item" 
              onClick={() => setMode('home')}
              style={{ background: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.3)', marginBottom: '1rem', fontWeight: 700 }}
            >
              🏠 Return to Homepage
            </div>

            {mode === 'global' && (
              <>
                <div className="nav-section-header">GLOBAL GAME DATA</div>
                <div className={`nav-item ${activeTab === 'paldex' ? 'active' : ''}`} onClick={() => setActiveTab('paldex')}>
                  📚 Master Paldex
                </div>
                <div className={`nav-item ${activeTab === 'skills' ? 'active' : ''}`} onClick={() => setActiveTab('skills')}>
                  ⚡ Skills Catalog
                </div>
                <div className={`nav-item ${activeTab === 'items' ? 'active' : ''}`} onClick={() => setActiveTab('items')}>
                  📦 Items & Recipes
                </div>
                <div className={`nav-item ${activeTab === 'buildings' ? 'active' : ''}`} onClick={() => setActiveTab('buildings')}>
                  🏗️ Facilities & Tech
                </div>
                <div className={`nav-item ${activeTab === 'breeding' ? 'active' : ''}`} onClick={() => setActiveTab('breeding')}>
                  🐣 Breeding Center
                </div>
              </>
            )}

            {mode === 'world' && (
              <>
                <div className="nav-section-header">ACTIVE WORLD DATA</div>
                <div className="world-selector-container" style={{ padding: '0.4rem 0.65rem', marginBottom: '0.4rem' }}>
                  <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.2rem', fontWeight: 700 }}>
                    🌍 ACTIVE WORLD
                  </label>
                  <select
                    value={selectedWorldId}
                    onChange={(e) => handleSelectWorld(e.target.value)}
                    disabled={worldLoading}
                    style={{
                      width: '100%',
                      padding: '0.35rem 0.5rem',
                      fontSize: '0.8rem',
                      background: 'rgba(0,0,0,0.4)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '6px',
                      color: 'var(--text-primary)',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    {worlds.length === 0 && <option value="">No worlds found</option>}
                    {worlds.map(w => (
                      <option key={w.world_id} value={w.world_id}>
                        {w.display_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className={`nav-item ${activeTab === 'world_overview' ? 'active' : ''}`} onClick={() => setActiveTab('world_overview')}>
                  📊 World Overview
                </div>
                <div className={`nav-item ${activeTab === 'save_game' ? 'active' : ''}`} onClick={() => setActiveTab('save_game')}>
                  🐾 World Pals
                </div>
                <div className={`nav-item ${activeTab === 'inventory' ? 'active' : ''}`} onClick={() => setActiveTab('inventory')}>
                  🎒 Save Inventory
                </div>
                <div className={`nav-item ${activeTab === 'bases' ? 'active' : ''}`} onClick={() => setActiveTab('bases')}>
                  🏰 Base Camps
                </div>
                <div className={`nav-item ${activeTab === 'condenser' ? 'active' : ''}`} onClick={() => setActiveTab('condenser')}>
                  ⭐ Condenser
                </div>
              </>
            )}

            {mode === 'settings' && (
              <>
                <div className="nav-section-header">SYSTEM SETTINGS</div>
                <div className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>
                  ⚙️ Settings & Loader
                </div>
              </>
            )}
          </nav>
        </aside>
      )}

      {/* Main Panel */}
      <main className="main-content">
        <h1>{
            activeTab === 'welcome' ? 'Palopedix Dashboard' :
            activeTab === 'paldex' ? 'Palworld 1.0+ Master Paldex' :
            activeTab === 'skills' ? 'Skills Database Catalog' :
            activeTab === 'items' ? 'Items & Crafting Catalog' :
            activeTab === 'buildings' ? 'Base Facilities & Technology Tree' :
            activeTab === 'inventory' ? 'Save Inventory & Chest Storage' :
            activeTab === 'save_game' ? 'World Pals Explorer' :
            activeTab === 'bases' ? 'Base Camp Overview' :
            activeTab === 'condenser' ? 'Condenser Recommendations' :
            activeTab === 'settings' ? 'System Settings' : 'Breeding Center'
          }</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>{
            activeTab === 'welcome' ? 'Welcome overview and active save file statistics.' :
            activeTab === 'paldex' ? 'Browse all Pal species, base stats, elements, work capabilities, learned skills, and drops.' :
            activeTab === 'skills' ? 'Explore 1,152 active combat skills, passive traits, and partner abilities.' :
            activeTab === 'items' ? 'Search 1,891 items, equipment, and crafting recipe ingredients.' :
            activeTab === 'buildings' ? 'Explore 552 base buildings and 839 technology tree unlocks.' :
            activeTab === 'inventory' ? 'Inspect items in your personal inventory, equipped loadouts, and base chests.' :
            activeTab === 'save_game' ? 'Click any captured Pal to view its full Paldex bio, element, skills, and stats.' :
            activeTab === 'bases' ? 'Audit placed infrastructure and active base camp workers.' :
            activeTab === 'condenser' ? 'View the absolute best Pals to condense based on your duplicates, IVs, and passives.' :
            activeTab === 'settings' ? 'Manage save file loading and database source settings.' :
            'Calculate offspring results or find parent breeding pairs for any Pal.'
          }</p>

                        {/* 🏠 Homepage Landing */}
        {mode === 'home' && (
          <HomepageView
            onSelectMode={handleSelectMode}
            currentWorld={worlds.find(w => w.world_id === selectedWorldId)}
            instancesCount={instances.length}
            basesCount={bases.length}
            inventoryCount={199}
          />
        )}

        {/* 📊 World Overview Tab */}
        {mode === 'world' && activeTab === 'world_overview' && (
          <WorldOverviewView
            currentWorld={worlds.find(w => w.world_id === selectedWorldId)}
            instancesCount={instances.length}
            basesCount={bases.length}
            inventoryCount={199}
            onNavigate={(tab) => setActiveTab(tab)}
          />
        )}
        {activeTab === 'welcome' && (
          <WelcomeView
            onNavigate={(tab) => setActiveTab(tab)}
            currentWorld={worlds.find(w => w.world_id === selectedWorldId)}
            instancesCount={instances.length}
            basesCount={bases.length}
            inventoryCount={199}
          />
        )}

        {/* 📚 Paldex Tab */}
        {activeTab === 'paldex' && (
          <div>
            <div className="filter-bar glass-card">
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Element</label>
                <select value={elementFilter} onChange={e => setElementFilter(e.target.value)}>
                  <option value="">All Elements</option>
                  <option value="Neutral">Neutral / Normal</option>
                  <option value="Fire">Fire</option>
                  <option value="Water">Water</option>
                  <option value="Grass">Grass / Leaf</option>
                  <option value="Electric">Electric / Electricity</option>
                  <option value="Ice">Ice</option>
                  <option value="Ground">Ground / Earth</option>
                  <option value="Dark">Dark</option>
                  <option value="Dragon">Dragon</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Size</label>
                <select value={sizeFilter} onChange={e => setSizeFilter(e.target.value)}>
                  <option value="">All Sizes</option>
                  <option value="XS">Extra Small (XS)</option>
                  <option value="S">Small (S)</option>
                  <option value="M">Medium (M)</option>
                  <option value="L">Large (L)</option>
                  <option value="XL">Extra Large (XL)</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Nocturnal</label>
                <select value={nocturnalFilter} onChange={e => setNocturnalFilter(e.target.value)}>
                  <option value="">All Habits</option>
                  <option value="true">Nocturnal Only</option>
                  <option value="false">Diurnal Only</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Work Suitability</label>
                <select value={suitabilityFilter} onChange={e => setSuitabilityFilter(e.target.value)}>
                  <option value="">All Suitabilities</option>
                  <option value="kindling">Kindling</option>
                  <option value="watering">Watering</option>
                  <option value="planting">Planting</option>
                  <option value="generating_electricity">Electricity Generation</option>
                  <option value="handiwork">Handiwork / Handcraft</option>
                  <option value="gathering">Gathering</option>
                  <option value="lumbering">Lumbering</option>
                  <option value="mining">Mining</option>
                  <option value="medicine_production">Medicine Production</option>
                  <option value="cooling">Cooling</option>
                  <option value="transporting">Transporting</option>
                  <option value="farming">Farming / Monster Farm</option>
                </select>
              </div>
            </div>

            <div className="pals-grid">
              {pals.map(p => (
                <div key={p.internal_name || p.id} className="glass-card pal-card" onClick={() => setSelectedPal(p)}>
                  <div className="pal-card-header">
                    <span className="pal-number">#{String(p.paldex_number || 0).padStart(3, '0')}</span>
                    <div className="badge-container">
                      {p.element_1 && (
                        <span className="badge badge-element" style={{ display: 'inline-flex', alignItems: 'center' }}>
                          <img src={`/assets/elements/${p.element_1}.png`} alt={p.element_1} className="element-icon-badge" onError={(e) => { e.target.style.display = 'none'; }} />
                          {p.element_1}
                        </span>
                      )}
                      {p.element_2 && (
                        <span className="badge badge-element" style={{ display: 'inline-flex', alignItems: 'center' }}>
                          <img src={`/assets/elements/${p.element_2}.png`} alt={p.element_2} className="element-icon-badge" onError={(e) => { e.target.style.display = 'none'; }} />
                          {p.element_2}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', margin: '0.75rem 0' }}>
                    {p.icon_path ? (
                      <img src={p.icon_path} alt={p.display_name} className="pal-card-avatar" onError={(e) => { e.target.style.display = 'none'; }} />
                    ) : (
                      <div className="pal-card-avatar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '1.5rem', background: 'var(--primary-gradient)' }}>
                        {p.display_name ? p.display_name[0] : 'P'}
                      </div>
                    )}
                    <div>
                      <h3 className="pal-name" style={{ margin: 0, fontSize: '1.25rem' }}>{p.display_name}</h3>
                      {p.code && p.code !== p.display_name && (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>ID: {p.code}</span>
                      )}
                    </div>
                  </div>

                  {/* Base Stats Summary */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', background: 'rgba(0,0,0,0.2)', padding: '0.5rem', borderRadius: '8px', marginBottom: '0.75rem', fontSize: '0.8rem', textAlign: 'center' }}>
                    <div><span style={{color: 'var(--text-secondary)'}}>HP:</span> <strong>{p.hp || 70}</strong></div>
                    <div><span style={{color: 'var(--text-secondary)'}}>ATK:</span> <strong>{p.attack_melee || 70}</strong></div>
                    <div><span style={{color: 'var(--text-secondary)'}}>DEF:</span> <strong>{p.defense || 70}</strong></div>
                  </div>

                  {/* Partner Skill preview */}
                  {p.partner_skill && (
                    <div style={{ fontSize: '0.78rem', color: 'var(--accent-gold)', background: 'rgba(234, 179, 8, 0.1)', border: '1px solid rgba(234, 179, 8, 0.25)', padding: '0.3rem 0.5rem', borderRadius: '6px', marginBottom: '0.75rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <span>🤝</span>
                      <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.partner_skill.name}</span>
                    </div>
                  )}

                  {/* Work Suitabilities preview with HUD icons */}
                  {p.work_suitability_details && p.work_suitability_details.length > 0 ? (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginBottom: '0.75rem' }}>
                      {p.work_suitability_details.slice(0, 3).map(wsd => (
                        <span key={wsd.id} className="suitability-pill" style={{ fontSize: '0.75rem', padding: '0.15rem 0.4rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                          {wsd.icon_path && (
                            <img src={wsd.icon_path} alt={wsd.name} className="work-hud-icon" onError={(e) => { e.target.style.display = 'none'; }} />
                          )}
                          <span>{wsd.name}</span>
                          <strong style={{ color: 'var(--accent-gold)' }}>L{wsd.level}</strong>
                        </span>
                      ))}
                      {p.work_suitability_details.length > 3 && (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', alignSelf: 'center' }}>+{p.work_suitability_details.length - 3} more</span>
                      )}
                    </div>
                  ) : (p.work_suitabilities && Object.keys(p.work_suitabilities).length > 0) && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginBottom: '0.75rem' }}>
                      {Object.entries(p.work_suitabilities).slice(0, 3).map(([work, level]) => (
                        <span key={work} className="suitability-pill" style={{ fontSize: '0.75rem', padding: '0.15rem 0.4rem' }}>
                          {WORK_SUITABILITY_MAP[work] || work} <strong style={{ color: 'var(--accent-gold)' }}>L{level}</strong>
                        </span>
                      ))}
                      {Object.keys(p.work_suitabilities).length > 3 && (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', alignSelf: 'center' }}>+{Object.keys(p.work_suitabilities).length - 3} more</span>
                      )}
                    </div>
                  )}

                  <div className="pal-card-footer">
                    <span>Power: {p.breeding_power}</span>
                    <span>Food: 🍖 {p.food_requirement}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ⚡ Skills Database Catalog Tab */}
        {activeTab === 'skills' && <SkillsCatalogView />}

        {/* 📦 Items & Recipes Catalog Tab */}
        {activeTab === 'items' && <ItemsCatalogView />}

        {/* 🏗️ Base Facilities & Tech Tree Tab */}
        {activeTab === 'buildings' && <BuildingsTechView />}

        {/* Selected Pal Detail Modal */}
        {selectedPal && (
          <PalDetailModal pal={selectedPal} onClose={() => setSelectedPal(null)} />
        )}

                {/* 🎒 Save Inventory Tab */}
        {activeTab === 'inventory' && <InventoryView />}

        {/* 💾 Save Game Explorer Tab */}
        {activeTab === 'save_game' && (
          <div>
            {/* Load Save Section */}
            <div className="glass-card" style={{ marginBottom: '2.5rem' }}>
              <h2 style={{ marginBottom: '1rem', fontWeight: 700 }}>Load Save File (Level.sav)</h2>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <input 
                  type="text" 
                  placeholder="Leave empty to auto-discover local save game path..." 
                  value={savePath} 
                  onChange={e => setSavePath(e.target.value)} 
                />
                <button className="btn btn-primary" onClick={handleLoadSave} disabled={loading}>
                  {loading ? 'Parsing...' : 'Load & Parse'}
                </button>
              </div>
              {errorMsg && <p style={{ color: 'var(--accent-red)', marginTop: '1rem', fontWeight: 500 }}>⚠️ {errorMsg}</p>}
              {successMsg && <p style={{ color: 'var(--accent-green)', marginTop: '1rem', fontWeight: 500 }}>✅ {successMsg}</p>}
              {saveLoaded && <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem', fontSize: '0.875rem' }}>Active save path: {loadedPath}</p>}
            </div>

            {saveLoaded ? (
              <div>
                <div className="filter-bar glass-card" style={{ marginBottom: '2rem' }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Location</label>
                    <select value={locFilter} onChange={e => setLocFilter(e.target.value)}>
                      <option value="">All Locations</option>
                      <option value="party">Player Party</option>
                      <option value="palbox">Palbox Storage</option>
                      <option value="base">Base Camp Workers</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Species</label>
                    <input type="text" placeholder="Filter by species..." value={specFilter} onChange={e => setSpecFilter(e.target.value)} />
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Gender</label>
                    <select value={genderFilter} onChange={e => setGenderFilter(e.target.value)}>
                      <option value="">All Genders</option>
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Min Level</label>
                    <input type="text" placeholder="Min level..." value={minLvlFilter} onChange={e => setMinLvlFilter(e.target.value)} />
                  </div>
                </div>

                <div className="glass-card table-container">
                  <table>
                    <thead>
                      <tr>
                        <th onClick={() => handleSort('display_name')} style={{cursor:'pointer'}}>Species{sortCol === 'display_name' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                        <th onClick={() => handleSort('level')} style={{cursor:'pointer'}}>Level{sortCol === 'level' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                        <th onClick={() => handleSort('gender')} style={{cursor:'pointer'}}>Gender{sortCol === 'gender' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                        <th onClick={() => handleSort('rank')} style={{cursor:'pointer'}}>Rank{sortCol === 'rank' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                        <th>IVs (HP/Melee/Defense)</th>
                        <th onClick={() => handleSort('location')} style={{cursor:'pointer'}}>Location{sortCol === 'location' ? (sortDesc ? ' ▼' : ' ▲') : ''}</th>
                        <th>Passives</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedInstances.map((pi, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 600 }}>
                            <div className="pal-avatar-container">
                              {pi.icon_path && (
                                <img src={pi.icon_path} alt={pi.display_name} className="pal-avatar-small" onError={(e) => { e.target.style.display = 'none'; }} />
                              )}
                              <span>{pi.display_name}</span>
                            </div>
                          </td>
                          <td>Lv. {pi.level}</td>
                          <td>{pi.gender}</td>
                          <td>{pi.rank} ⭐</td>
                          <td>{pi.iv_hp} / {pi.iv_melee} / {pi.iv_defense}</td>
                          <td>{pi.location.toUpperCase()} {pi.location_details_base_camp_name && `(${pi.location_details_base_camp_name})`}</td>
                          <td>
                            <div className="badge-container">
                              {pi.passives.map(pass => (
                                <SkillBadgeWithTooltip key={pass.id} skill={pass}>
                                  <span className="badge badge-element" style={{ cursor: 'pointer' }}>
                                    {pass.name}
                                  </span>
                                </SkillBadgeWithTooltip>
                              ))}
                              {pi.passives.length === 0 && <span style={{ color: 'var(--text-secondary)' }}>None</span>}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="glass-card" style={{ textAlign: 'center', padding: '4rem' }}>
                <p style={{ color: 'var(--text-secondary)', fontSize: '1.25rem' }}>No save file loaded. Please click "Load & Parse" to view save game details.</p>
              </div>
            )}
          </div>
        )}

        {/* 🏰 Base Camps Tab */}
        {activeTab === 'bases' && (
          <div>
            {!saveLoaded ? (
              <div className="glass-card" style={{ textAlign: 'center', padding: '4rem' }}>
                <p style={{ color: 'var(--text-secondary)', fontSize: '1.25rem' }}>No save file loaded. Please load a save file in the Save Game tab first.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                {bases.map(base => (
                  <BaseCampCard key={base.base_camp_id} base={base} />
                ))}
                {bases.length === 0 && <p style={{ color: 'var(--text-secondary)' }}>No base camps found in save file.</p>}
              </div>
            )}
          </div>
        )}

        {/* ⭐ Condenser Tab */}
        {activeTab === 'condenser' && <CondenserView />}

                {/* ⚙️ Settings Tab */}
        {activeTab === 'settings' && (
          <SettingsView
            savePath={savePath}
            setSavePath={setSavePath}
            handleLoadSave={handleLoadSave}
            loading={loading}
            errorMsg={errorMsg}
            successMsg={successMsg}
          />
        )}

        {/* 🐣 Breeding Center Tab */}
        {activeTab === 'breeding' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>
            {/* Global vs Caught Source Selector */}
            <div className="glass-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', padding: '1.25rem 1.75rem' }}>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>📊 Pal Dropdown Options Source</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.2rem', margin: 0 }}>
                  Choose whether dropdowns show all game Pals or only Pals you have caught in your save.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button 
                  className={`btn ${palSourceMode === 'global' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ padding: '0.5rem 1.25rem', fontWeight: 600 }}
                  onClick={() => setPalSourceMode('global')}
                >
                  🌐 All Game Pals ({pals ? pals.length : 0})
                </button>
                <button 
                  className={`btn ${palSourceMode === 'caught' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ padding: '0.5rem 1.25rem', fontWeight: 600 }}
                  onClick={() => {
                    if (!saveLoaded) {
                      alert("Please load a save file in Settings first to filter by your caught Pals!")
                      return
                    }
                    setPalSourceMode('caught')
                  }}
                >
                  💼 My Caught Pals ({ownedSpecies.length})
                </button>
              </div>
            </div>

            {/* Datalist for searchable dropdown options */}
            <datalist id="pal-list-options">
              {availablePalOptions.map((name, idx) => (
                <option key={idx} value={name} />
              ))}
            </datalist>

            {/* 1. Calculator Card */}
            <div className="glass-card">
              <h2 style={{ marginBottom: '1.5rem', fontWeight: 800 }}>🐣 Breeding Calculator</h2>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '1.5rem', alignItems: 'end' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Parent 1</label>
                  <select 
                    style={{ width: '100%', padding: '0.65rem 1rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.95rem' }}
                    value={parent1} 
                    onChange={e => setParent1(e.target.value)}
                  >
                    <option value="">-- Select Parent 1 --</option>
                    {availablePalOptions.map((name, idx) => (
                      <option key={idx} value={name}>{name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Parent 2</label>
                  <select 
                    style={{ width: '100%', padding: '0.65rem 1rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.95rem' }}
                    value={parent2} 
                    onChange={e => setParent2(e.target.value)}
                  >
                    <option value="">-- Select Parent 2 --</option>
                    {availablePalOptions.map((name, idx) => (
                      <option key={idx} value={name}>{name}</option>
                    ))}
                  </select>
                </div>
                <button className="btn btn-primary" onClick={handleCalculateBreed} disabled={!parent1 || !parent2}>Calculate</button>
              </div>

              {breedError && (
                <div style={{ marginTop: '1rem', color: '#f87171', padding: '0.75rem 1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                  ⚠️ {breedError}
                </div>
              )}

              {breedResult && (
                <div className="glass-card" style={{ marginTop: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(99, 102, 241, 0.15)', borderColor: 'var(--border-color-hover)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                    {breedResult.icon_path && (
                      <img src={breedResult.icon_path} alt={breedResult.display_name} className="pal-card-avatar" onError={(e) => { e.target.style.display = 'none'; }} />
                    )}
                    <div>
                      <h3 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Child: {breedResult.display_name}</h3>
                      <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>Breeding Power: {breedResult.breeding_power}</p>
                    </div>
                  </div>
                  <div className="badge-container">
                    {breedResult.element_1 && <span className="badge badge-element">{breedResult.element_1}</span>}
                    {breedResult.element_2 && <span className="badge badge-element">{breedResult.element_2}</span>}
                  </div>
                </div>
              )}
            </div>

            {/* 2. Reverse Lookup Card */}
            <div className="glass-card">
              <h2 style={{ marginBottom: '1.5rem', fontWeight: 800 }}>🔍 Reverse Breeding Lookup</h2>
              <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'end', marginBottom: '1.5rem' }}>
                <div style={{ flexGrow: 1 }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Target Child</label>
                  <select 
                    style={{ width: '100%', padding: '0.65rem 1rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.95rem' }}
                    value={reverseChild} 
                    onChange={e => setReverseChild(e.target.value)}
                  >
                    <option value="">-- Select Target Child Pal --</option>
                    {availablePalOptions.map((name, idx) => (
                      <option key={idx} value={name}>{name}</option>
                    ))}
                  </select>
                </div>
                <button className="btn btn-primary" onClick={handleCalculateReverse} disabled={!reverseChild || reverseLoading}>
                  {reverseLoading ? 'Searching...' : 'Find Combinations'}
                </button>
              </div>

              {reverseSearched && !reverseLoading && (
                parentCombos.length > 0 ? (
                  <div>
                    <div style={{ marginBottom: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                      Found {parentCombos.length} parent combinations yielding <strong>{reverseSearchTerm}</strong>:
                    </div>
                    <div className="table-container" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                      <table>
                        <thead>
                          <tr>
                            <th>Parent 1</th>
                            <th>Parent 2</th>
                          </tr>
                        </thead>
                        <tbody>
                          {parentCombos.map((combo, idx) => (
                            <tr key={idx}>
                              <td>{combo[0]}</td>
                              <td>{combo[1]}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-secondary)', padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', textAlign: 'center' }}>
                    No breeding combinations found for "{reverseSearchTerm}".
                  </div>
                )
              )}
            </div>

            {/* 3. Breeding Path Finder Card */}
            <div className="glass-card">
              <h2 style={{ marginBottom: '1.5rem', fontWeight: 800 }}>🧬 BFS Breeding Path Finder</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                Finds the shortest multi-step breeding chain to create your target Pal using your available inventory.
              </p>

              <div style={{ marginBottom: '1.5rem', background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontWeight: 600 }}>
                  <input 
                    type="checkbox" 
                    checked={useSaveOwned} 
                    onChange={e => setUseSaveOwned(e.target.checked)} 
                    disabled={!saveLoaded}
                  />
                  <span>Automatically use my caught Pals from save file ({saveLoaded ? `${ownedSpecies.length} species owned` : 'No save loaded'})</span>
                </label>

                {!useSaveOwned && (
                  <div style={{ marginTop: '1rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Custom Owned Species (comma-separated)</label>
                    <input 
                      type="text" 
                      placeholder="e.g. Lamball, Cattiva, Penking" 
                      value={ownedPals} 
                      onChange={e => setOwnedPals(e.target.value)} 
                    />
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'end', marginBottom: '1.5rem' }}>
                <div style={{ flexGrow: 1 }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Target Pal to Breed</label>
                  <select 
                    style={{ width: '100%', padding: '0.65rem 1rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.95rem' }}
                    value={targetPal} 
                    onChange={e => setTargetPal(e.target.value)}
                  >
                    <option value="">-- Select Target Pal --</option>
                    {availablePalOptions.map((name, idx) => (
                      <option key={idx} value={name}>{name}</option>
                    ))}
                  </select>
                </div>
                <button className="btn btn-primary" onClick={handleFindPath} disabled={!targetPal || pathLoading}>
                  {pathLoading ? 'Finding Path...' : 'Find Path'}
                </button>
              </div>

              {pathError && (
                <div style={{ marginTop: '1rem', color: '#f87171', padding: '0.75rem 1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                  ⚠️ {pathError}
                </div>
              )}

              {pathSearched && !pathLoading && allBreedingPaths.length > 0 && (
                <div>
                  {/* Alternative Path Selection Tabs */}
                  {allBreedingPaths.length > 1 && (
                    <div style={{ display: 'flex', gap: '0.6rem', marginBottom: '1.25rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
                      {allBreedingPaths.map((pObj, pIdx) => (
                        <button
                          key={pIdx}
                          className={`btn ${activePathIdx === pIdx ? 'btn-primary' : 'btn-secondary'}`}
                          style={{ fontSize: '0.85rem', padding: '0.45rem 1rem', whiteSpace: 'nowrap' }}
                          onClick={() => setActivePathIdx(pIdx)}
                        >
                          {pObj.title}
                        </button>
                      ))}
                    </div>
                  )}

                  {(() => {
                    const currentPathObj = allBreedingPaths[activePathIdx] || allBreedingPaths[0]
                    const currentSteps = currentPathObj ? currentPathObj.steps : []
                    return (
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                          <h4 style={{ fontWeight: 700, color: 'var(--accent-light)', margin: 0 }}>
                            🎯 {currentPathObj.title} to get {targetPal}:
                          </h4>
                          <span style={{ fontSize: '0.8rem', padding: '0.25rem 0.65rem', borderRadius: '6px', background: 'rgba(255,255,255,0.08)', color: 'var(--text-secondary)' }}>
                            {currentPathObj.difficulty}
                          </span>
                        </div>

                        <div className="steps-list" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                          {currentSteps.map((step, idx) => (
                            <div key={idx} className="step-card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1rem', background: 'rgba(255,255,255,0.05)', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <div className="step-num" style={{ background: 'var(--accent-color)', color: 'white', fontWeight: 800, width: '32px', height: '32px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                                  {idx + 1}
                                </div>
                                <div className="step-details" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.05rem', fontWeight: 600, flexWrap: 'wrap', flexGrow: 1 }}>
                                  <span style={{ color: '#a5b4fc', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                                    {step.parent1}
                                    {step.parent1_gender === 'Male' && <span style={{ color: '#60a5fa', background: 'rgba(96, 165, 250, 0.15)', padding: '0.1rem 0.4rem', borderRadius: '4px', fontSize: '0.85rem' }}>♂ Male</span>}
                                    {step.parent1_gender === 'Female' && <span style={{ color: '#f472b6', background: 'rgba(244, 114, 182, 0.15)', padding: '0.1rem 0.4rem', borderRadius: '4px', fontSize: '0.85rem' }}>♀ Female</span>}
                                  </span>
                                  <span style={{ color: 'var(--text-secondary)' }}>+</span>
                                  <span style={{ color: '#a5b4fc', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                                    {step.parent2}
                                    {step.parent2_gender === 'Male' && <span style={{ color: '#60a5fa', background: 'rgba(96, 165, 250, 0.15)', padding: '0.1rem 0.4rem', borderRadius: '4px', fontSize: '0.85rem' }}>♂ Male</span>}
                                    {step.parent2_gender === 'Female' && <span style={{ color: '#f472b6', background: 'rgba(244, 114, 182, 0.15)', padding: '0.1rem 0.4rem', borderRadius: '4px', fontSize: '0.85rem' }}>♀ Female</span>}
                                  </span>
                                  <span style={{ color: 'var(--accent-light)' }}>➔</span>
                                  <span style={{ color: '#34d399', fontWeight: 700 }}>{step.child}</span>
                                </div>
                              </div>

                              {step.gender_note && (
                                <div style={{ marginLeft: '2.75rem', fontSize: '0.82rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                  <span>🎲</span>
                                  <span><strong>Hatch Odds for {step.child}:</strong> {step.gender_note}</span>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })()}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
