// Palopedix Unified Partner Skill Categories and Subcategories Constants

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
  { value: 'no_active_skill', label: '❓ No Functional Partner Skill' },
];

export const PARTNER_SUBGROUP_DEFINITIONS = {
  ranch_producer: {
    label: 'Produced Product',
    subcategories: [
      { value: 'egg', label: '🥚 Eggs' },
      { value: 'milk', label: '🥛 Milk' },
      { value: 'honey', label: '🍯 Honey' },
      { value: 'berries', label: '🍒 Red Berries' },
      { value: 'mushrooms', label: '🍄 Mushrooms' },
      { value: 'wool', label: '🧶 Wool' },
      { value: 'high_quality_cloth', label: '🧵 High Quality Cloth' },
      { value: 'flame_organ', label: '🔥 Flame Organ' },
      { value: 'ice_organ', label: '❄️ Ice Organ' },
      { value: 'electric_organ', label: '⚡ Electric Organ' },
      { value: 'pal_fluids', label: '💧 Pal Fluids' },
      { value: 'pal_oil', label: '🛢️ High Quality Pal Oil' },
      { value: 'venom_gland', label: '🧪 Venom Gland' },
      { value: 'bone', label: '🦴 Bone' },
      { value: 'leather', label: '🛡️ Leather' },
      { value: 'gold_coins', label: '🪙 Gold Coins' },
      { value: 'cotton_candy', label: '🍭 Cotton Candy' },
      { value: 'excavated_items', label: '🔮 Spheres & Excavated Items' },
      { value: 'seeds', label: '🌱 Seeds' },
    ],
  },
  player_element_infusion: {
    label: 'Infused Element',
    subcategories: [
      { value: 'fire', label: '🔥 Fire Infusion' },
      { value: 'water', label: '💧 Water Infusion' },
      { value: 'electric', label: '⚡ Electric Infusion' },
      { value: 'ice', label: '❄️ Ice Infusion' },
      { value: 'dark', label: '🌑 Dark Infusion' },
      { value: 'grass', label: '🍃 Grass Infusion' },
      { value: 'ground', label: '⛰️ Ground Infusion' },
      { value: 'dragon', label: '🐉 Dragon Infusion' },
    ],
  },
  drop_loot_booster: {
    label: 'Target Enemy Element',
    subcategories: [
      { value: 'dark', label: '🌑 Dark Pals Drops' },
      { value: 'dragon', label: '🐉 Dragon Pals Drops' },
      { value: 'electric', label: '⚡ Electric Pals Drops' },
      { value: 'fire', label: '🔥 Fire Pals Drops' },
      { value: 'grass', label: '🍃 Grass Pals Drops' },
      { value: 'ground', label: '⛰️ Ground Pals Drops' },
      { value: 'ice', label: '❄️ Ice Pals Drops' },
      { value: 'neutral', label: '⚪ Neutral Pals Drops' },
      { value: 'water', label: '💧 Water Pals Drops' },
      { value: 'pal_souls', label: '👻 Pal Souls Boost' },
    ],
  },
  carrying_capacity: {
    label: 'Weight Target',
    subcategories: [
      { value: 'flat_max_weight', label: '🎒 Max Weight Increase' },
      { value: 'ore_weight', label: '⛏️ Ore & Stone Weight' },
      { value: 'wood_weight', label: '🌲 Wood & Timber Weight' },
      { value: 'food_weight', label: '🍎 Food & Ingredients Weight' },
      { value: 'weapon_weight', label: '⚔️ Weapons Weight' },
    ],
  },
  healer_lifesteal: {
    label: 'Healing Style',
    subcategories: [
      { value: 'active_burst_heal', label: '💖 Active Burst Heal' },
      { value: 'life_steal', label: '🩸 Life Steal (Vampiric)' },
      { value: 'continuous_regen', label: '✨ Continuous HP Regen' },
      { value: 'emergency_revive', label: '🛡️ Emergency Heal / Revive' },
    ],
  },
  heavy_artillery: {
    label: 'Weapon Class',
    subcategories: [
      { value: 'mounted_artillery', label: '🚀 Mounted Artillery' },
      { value: 'handheld_weapons', label: '🗡️ Player Handheld / Wielded' },
      { value: 'support_gunfire', label: '🔫 Autonomous Fire Support' },
    ],
  },
  party_pal_buffer: {
    label: 'Elemental Aura & Synergy',
    subcategories: [
      { value: 'fire_aura', label: '🔥 Fire Pals Buff' },
      { value: 'water_aura', label: '💧 Water Pals Buff' },
      { value: 'electric_aura', label: '⚡ Electric Pals Buff' },
      { value: 'ground_aura', label: '⛰️ Ground Pals Buff' },
      { value: 'ice_aura', label: '❄️ Ice Pals Buff' },
      { value: 'grass_aura', label: '🍃 Grass Pals Buff' },
      { value: 'dark_aura', label: '🌑 Dark Pals Buff' },
      { value: 'dragon_aura', label: '🐉 Dragon Pals Buff' },
      { value: 'neutral_aura', label: '⚪ Neutral Pals Buff' },
      { value: 'misc', label: '🛡️ Team Synergy & Self-Buffers' },
    ],
  },
  player_combat_buffer: {
    label: 'Combat Buff Branch',
    subcategories: [
      { value: 'element_buff_resist', label: '🔰 Damage Resistance & Affliction' },
      { value: 'attack_boost', label: '⚔️ Player Attack Boost' },
      { value: 'defense_boost', label: '🛡️ Player Defense & Reduction' },
      { value: 'weak_point_crit', label: '🎯 Weak Point & Critical Strike' },
      { value: 'weapon_mastery', label: '🏹 Weapon Type Mastery' },
    ],
  },
};

export function hasSubcategories(categoryId) {
  return Boolean(categoryId && PARTNER_SUBGROUP_DEFINITIONS[categoryId]);
}

export function getSubcategoryLabel(categoryId) {
  return PARTNER_SUBGROUP_DEFINITIONS[categoryId]?.label || 'Subcategory';
}

export function getSubcategoryOptions(categoryId) {
  if (!hasSubcategories(categoryId)) return [{ value: '', label: 'All Subcategories' }];
  return [
    { value: '', label: `All ${PARTNER_SUBGROUP_DEFINITIONS[categoryId].label}` },
    ...PARTNER_SUBGROUP_DEFINITIONS[categoryId].subcategories,
  ];
}

export function findSubcategoryLabel(categoryId, subcategoryId) {
  if (!categoryId || !subcategoryId) return subcategoryId || '';
  const def = PARTNER_SUBGROUP_DEFINITIONS[categoryId];
  if (!def) return subcategoryId;
  const match = def.subcategories.find(s => s.value === subcategoryId);
  return match?.label || subcategoryId;
}
