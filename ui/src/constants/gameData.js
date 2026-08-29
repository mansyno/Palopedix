// Palopedix Unified Game Constants & Mappings

export const WORK_SUITABILITY_MAP = {
  EmitFlame: 'Kindling',
  Kindling: 'Kindling',
  Watering: 'Watering',
  Seeding: 'Planting',
  Planting: 'Planting',
  GenerateElectricity: 'Generating Electricity',
  GeneratingElectricity: 'Generating Electricity',
  Electricity: 'Generating Electricity',
  Handcraft: 'Handiwork',
  Handiwork: 'Handiwork',
  Collection: 'Gathering',
  Gathering: 'Gathering',
  Deforest: 'Lumbering',
  Lumbering: 'Lumbering',
  Wood: 'Lumbering',
  Mining: 'Mining',
  Mine: 'Mining',
  ProductMedicine: 'Medicine Production',
  Medicine: 'Medicine Production',
  MedicineProduction: 'Medicine Production',
  Cool: 'Cooling',
  Cooling: 'Cooling',
  Transport: 'Transporting',
  Transporting: 'Transporting',
  MonsterFarm: 'Farming',
  Farming: 'Farming',
  OilExtraction: 'Oil Extraction',
};

export const WORK_TYPE_ASSET_MAP = {
  Kindling: { icon: '/assets/work/Kindling.png', label: 'Kindling', emoji: '🔥' },
  EmitFlame: { icon: '/assets/work/Kindling.png', label: 'Kindling', emoji: '🔥' },
  Watering: { icon: '/assets/work/Watering.png', label: 'Watering', emoji: '💧' },
  Planting: { icon: '/assets/work/Planting.png', label: 'Planting', emoji: '🌱' },
  Seeding: { icon: '/assets/work/Planting.png', label: 'Planting', emoji: '🌱' },
  GeneratingElectricity: { icon: '/assets/work/GeneratingElectricity.png', label: 'Electricity', emoji: '⚡' },
  Electricity: { icon: '/assets/work/GeneratingElectricity.png', label: 'Electricity', emoji: '⚡' },
  Handcraft: { icon: '/assets/work/Handcraft.png', label: 'Handcraft', emoji: '🔨' },
  Handiwork: { icon: '/assets/work/Handcraft.png', label: 'Handcraft', emoji: '🔨' },
  Gathering: { icon: '/assets/work/Gathering.png', label: 'Gathering', emoji: '🧺' },
  Collection: { icon: '/assets/work/Gathering.png', label: 'Gathering', emoji: '🧺' },
  Lumbering: { icon: '/assets/work/Lumbering.png', label: 'Lumbering', emoji: '🌲' },
  Deforest: { icon: '/assets/work/Lumbering.png', label: 'Lumbering', emoji: '🌲' },
  Mining: { icon: '/assets/work/Mining.png', label: 'Mining', emoji: '⛏️' },
  Mine: { icon: '/assets/work/Mining.png', label: 'Mining', emoji: '⛏️' },
  Medicine: { icon: '/assets/work/Medicine.png', label: 'Medicine', emoji: '💊' },
  MedicineProduction: { icon: '/assets/work/Medicine.png', label: 'Medicine', emoji: '💊' },
  ProductMedicine: { icon: '/assets/work/Medicine.png', label: 'Medicine', emoji: '💊' },
  Cooling: { icon: '/assets/work/Cooling.png', label: 'Cooling', emoji: '❄️' },
  Cool: { icon: '/assets/work/Cooling.png', label: 'Cooling', emoji: '❄️' },
  Transporting: { icon: '/assets/work/Transport.png', label: 'Transporting', emoji: '📦' },
  Transport: { icon: '/assets/work/Transport.png', label: 'Transporting', emoji: '📦' },
  Farming: { icon: '/assets/work/MonsterFarm.png', label: 'Farming', emoji: '🍳' },
  MonsterFarm: { icon: '/assets/work/MonsterFarm.png', label: 'Farming', emoji: '🍳' },
};

export const LEGEND_PASSIVES = new Set([
  'legend', 'celestial emperor', 'lord of lightning', 'divine dragon',
  'siren of the void', 'eternal flame', 'ice emperor', 'flame emperor',
  'earth emperor', 'spirit emperor', 'emperor', 'holy beast'
]);

export const GOLD_PASSIVES = new Set([
  'artisan', 'ferocious', 'musclehead', 'swift', 'lucky',
  'work slave', 'vanguard', 'stronghold strategist', 'burly body', 'remarkable',
  'runner', 'workaholic', 'mine foreman', 'logging foreman', 'motivational leader', 'serious'
]);

export const NEGATIVE_PASSIVES = new Set([
  'slacker', 'downtrodden', 'pacifist', 'bottomless stomach', 'brittle',
  'glutton', 'destructive', 'sadist', 'coward', 'clumsy', 'distracted',
  'unstable', 'dehydrated', 'sloppy'
]);

export const CATEGORY_STYLES = {
  'Breeding & Food': { emoji: '🍳', bg: 'rgba(236, 72, 153, 0.15)', border: 'rgba(236, 72, 153, 0.35)', color: '#f472b6', desc: 'Optimized for breeding farms, cake production ingredients (Milk, Honey, Eggs), agriculture & cooking' },
  'Agriculture': { emoji: '🌾', bg: 'rgba(34, 197, 94, 0.15)', border: 'rgba(34, 197, 94, 0.35)', color: '#4ade80', desc: 'Optimized for high-yield planting, watering, gathering & crop transport' },
  'Extraction': { emoji: '⛏️', bg: 'rgba(245, 158, 11, 0.15)', border: 'rgba(245, 158, 11, 0.35)', color: '#fbbf24', desc: 'Optimized for mining pits, natural ore/coal nodes, logging & high-speed hauling' },
  'Production': { emoji: '🏭', bg: 'rgba(59, 130, 246, 0.15)', border: 'rgba(59, 130, 246, 0.35)', color: '#60a5fa', desc: 'Optimized for 24/7 smelting furnaces, assembly lines & workbench handcrafting' },
  'Energy & Tech': { emoji: '⚡', bg: 'rgba(168, 85, 247, 0.15)', border: 'rgba(168, 85, 247, 0.35)', color: '#c084fc', desc: 'Optimized for high-output power generation, oil extraction & electric furnaces' },
  'Ranching': { emoji: '🐑', bg: 'rgba(20, 184, 166, 0.15)', border: 'rgba(20, 184, 166, 0.35)', color: '#2dd4bf', desc: 'Optimized for ranch drop harvesting & item transport' },
  'Balanced': { emoji: '⚖️', bg: 'rgba(148, 163, 184, 0.15)', border: 'rgba(148, 163, 184, 0.35)', color: '#cbd5e1', desc: 'General-purpose balance across all detected base facilities' },
};

export const BASE_CATEGORY_MAP = {
  'Breeding & Food': { emoji: '🍳', color: 'rgba(236, 72, 153, 0.15)', border: 'rgba(236, 72, 153, 0.4)', text: '#f472b6' },
  'Agriculture': { emoji: '🌾', color: 'rgba(34, 197, 94, 0.15)', border: 'rgba(34, 197, 94, 0.4)', text: '#4ade80' },
  'Extraction': { emoji: '⛏️', color: 'rgba(245, 158, 11, 0.15)', border: 'rgba(245, 158, 11, 0.4)', text: '#fbbf24' },
  'Production': { emoji: '🏭', color: 'rgba(59, 130, 246, 0.15)', border: 'rgba(59, 130, 246, 0.4)', text: '#60a5fa' },
  'Energy & Tech': { emoji: '⚡', color: 'rgba(168, 85, 247, 0.15)', border: 'rgba(168, 85, 247, 0.4)', text: '#c084fc' },
  'Ranching': { emoji: '🐑', color: 'rgba(20, 184, 166, 0.15)', border: 'rgba(20, 184, 166, 0.4)', text: '#2dd4bf' },
  'Balanced': { emoji: '⚖️', color: 'rgba(148, 163, 184, 0.15)', border: 'rgba(148, 163, 184, 0.4)', text: '#cbd5e1' },
};
