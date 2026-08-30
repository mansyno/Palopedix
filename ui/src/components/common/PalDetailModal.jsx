import React from 'react';
import { WORK_SUITABILITY_MAP } from '../../constants/gameData';
import { PassiveBadge, getPassiveMeta } from './PassiveBadge';

export function PalDetailModal({ pal, onClose }) {
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
              {pal.isInstance ? (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Level</span>
                    <span style={{ fontWeight: 700, color: 'var(--accent-gold)' }}>Lv. {pal.level}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Gender</span>
                    <span style={{ fontWeight: 600 }}>{pal.gender === 'Male' ? '♂ Male' : pal.gender === 'Female' ? '♀ Female' : pal.gender || 'Unknown'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Condenser Rank</span>
                    <span style={{ fontWeight: 600, color: 'var(--accent-gold)' }}>{pal.rank || 0} ⭐</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>IVs (HP/Atk/Def)</span>
                    <span style={{ fontWeight: 700, color: '#38bdf8' }}>{pal.iv_hp} / {pal.iv_melee} / {pal.iv_defense}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>💨 Speed (Current/Base)</span>
                    <span style={{ fontWeight: 700, color: (pal.speed_modifier_pct && pal.speed_modifier_pct > 0) ? '#34d399' : 'var(--text-primary)' }}>
                      {pal.current_speed || pal.base_speed || pal.run_speed || 'N/A'}
                      {pal.base_speed && pal.current_speed && pal.speed_modifier_pct > 0 ? (
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 400, marginLeft: '0.35rem' }}>
                          (Base: {pal.base_speed})
                        </span>
                      ) : null}
                    </span>
                  </div>
                  {pal.speed_buffs && pal.speed_buffs.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', justifyContent: 'flex-end', marginTop: '-0.2rem' }}>
                      {pal.speed_buffs.map((b, bIdx) => (
                        <span key={bIdx} className="badge" style={{ background: 'rgba(52, 211, 153, 0.15)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.35)', fontSize: '0.7rem', padding: '0.05rem 0.3rem' }}>
                          ⚡ {b}
                        </span>
                      ))}
                    </div>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Location</span>
                    <span style={{ fontWeight: 600 }}>{pal.location ? pal.location.toUpperCase() : 'PALBOX'} {pal.location_details_base_camp_name ? `(${pal.location_details_base_camp_name})` : ''}</span>
                  </div>
                </>
              ) : null}
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
                  <div className="stat-label"><span>Base Movement Speed</span><span style={{fontWeight:700, color: '#38bdf8'}}>{pal.base_speed || pal.run_speed || 'N/A'}</span></div>
                  <div className="stat-bar"><div className="stat-fill" style={{ width: `${Math.min(((pal.base_speed || pal.run_speed || 500)/1700)*100, 100)}%`, background: 'linear-gradient(135deg, #10b981, #34d399)' }}></div></div>
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
              <div style={{ background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.15), rgba(168, 85, 247, 0.15))', border: '1px solid var(--accent-gold)', borderRadius: '12px', padding: '1rem', marginBottom: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <h4 style={{ fontWeight: 800, color: 'var(--accent-gold)', margin: 0, fontSize: '1rem' }}>🤝 Partner Skill: {pal.partner_skill.name}</h4>
                  {pal.partner_skill.unlock_item && (
                    <span className="badge" style={{ background: 'rgba(255,255,255,0.1)' }}>Req: {pal.partner_skill.unlock_item}</span>
                  )}
                </div>
                {pal.partner_skill.description && (
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', margin: 0, lineHeight: 1.4 }}>{pal.partner_skill.description}</p>
                )}
                {pal.partner_skill_categories && pal.partner_skill_categories.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.6rem' }}>
                    {pal.partner_skill_categories.map(cat => (
                      <span
                        key={cat.id}
                        className="badge"
                        style={{
                          background: 'rgba(234, 179, 8, 0.2)',
                          color: '#fef08a',
                          border: '1px solid rgba(234, 179, 8, 0.4)',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.3rem'
                        }}
                      >
                        <span>{cat.icon}</span>
                        <span>{cat.name}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* SKILLS SECTION */}
            {pal.isInstance ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                <div>
                  <h3 style={{ fontWeight: 700, marginBottom: '0.75rem', color: 'var(--text-primary)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
                    🛡️ Pal Passives ({pal.passives ? pal.passives.length : 0})
                  </h3>
                  {pal.passives && pal.passives.length > 0 ? (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '0.65rem' }}>
                      {pal.passives.map((pass, pIdx) => {
                        const meta = getPassiveMeta(pass);
                        return (
                          <div key={pIdx} className="skill-row" style={{ padding: '0.5rem 0.65rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <PassiveBadge skill={pass} size="modal" />
                            {meta?.statModifier ? (
                              <p style={{ fontSize: '0.78rem', color: 'var(--accent-green)', fontWeight: 600, margin: '0.15rem 0 0 0.25rem' }}>
                                ✨ {meta.statModifier}
                              </p>
                            ) : meta?.description ? (
                              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '0.15rem 0 0 0.25rem' }}>{meta.description}</p>
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic', margin: 0 }}>No passive skills on this Pal.</p>
                  )}
                </div>

                <div>
                  <h3 style={{ fontWeight: 700, marginBottom: '0.75rem', color: 'var(--text-primary)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
                    ⚔️ Equipped Active Attacks ({pal.equip_waza ? pal.equip_waza.length : 0})
                  </h3>
                  {pal.equip_waza && pal.equip_waza.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {pal.equip_waza.map((waza, wIdx) => (
                        <div key={wIdx} className="skill-row" style={{ padding: '0.65rem 0.85rem' }}>
                          {waza.icon_path ? (
                            <img src={waza.icon_path} alt={waza.name} className="skill-icon-large" onError={(e) => { e.target.style.display = 'none'; }} />
                          ) : (
                            <div className="skill-icon-large" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>⚡</div>
                          )}
                          <div style={{ flexGrow: 1 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ fontWeight: 700 }}>{waza.name}</span>
                              <div className="badge-container">
                                {waza.element && <span className="badge badge-element">{waza.element}</span>}
                              </div>
                            </div>
                            {waza.description && <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem', margin: '0.25rem 0 0 0' }}>{waza.description}</p>}
                            {(waza.power > 0 || (waza.cooldown_sec || waza.cooldown) > 0) && (
                              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.35rem', display: 'flex', gap: '1rem' }}>
                                {waza.power > 0 && <span>Power: <strong style={{ color: 'var(--accent-gold)' }}>{waza.power}</strong></span>}
                                {(waza.cooldown_sec || waza.cooldown) > 0 && <span>CD: <strong style={{ color: 'var(--text-primary)' }}>{waza.cooldown_sec || waza.cooldown}s</strong></span>}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic', margin: 0 }}>No active attacks equipped.</p>
                  )}
                </div>
              </div>
            ) : (
              pal.skills && pal.skills.filter(sk => sk.type !== 'Partner' && sk.category !== 'Partner').length > 0 && (
                <div>
                  <h3 style={{ fontWeight: 700, marginBottom: '0.75rem', color: 'var(--text-primary)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
                    ⚔️ Active & Passive Skills ({pal.skills.filter(sk => sk.type !== 'Partner' && sk.category !== 'Partner').length})
                  </h3>
                  <div style={{ maxHeight: '250px', overflowY: 'auto', paddingRight: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {pal.skills.filter(sk => sk.type !== 'Partner' && sk.category !== 'Partner').map(sk => (
                      <div key={sk.id} className="skill-row">
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
                    ))}
                  </div>
                </div>
              )
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

export default PalDetailModal;
