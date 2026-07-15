

export const index = 3;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/solver/_page.svelte.js')).default;
export const imports = ["_app/immutable/nodes/3.Dax7nt-5.js","_app/immutable/chunks/D8UAMxAb.js","_app/immutable/chunks/xihTtKlq.js"];
export const stylesheets = ["_app/immutable/assets/3.CJ4Zo7vU.css"];
export const fonts = [];
