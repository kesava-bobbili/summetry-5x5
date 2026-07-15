

export const index = 3;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/solver/_page.svelte.js')).default;
export const imports = ["_app/immutable/nodes/3.CgDwDK-g.js","_app/immutable/chunks/hq50ZQI6.js","_app/immutable/chunks/xihTtKlq.js"];
export const stylesheets = ["_app/immutable/assets/3.CJ4Zo7vU.css"];
export const fonts = [];
