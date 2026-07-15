

export const index = 2;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_page.svelte.js')).default;
export const imports = ["_app/immutable/nodes/2.Dkd0Vh_a.js","_app/immutable/chunks/BOLnnYLn.js","_app/immutable/chunks/xihTtKlq.js"];
export const stylesheets = ["_app/immutable/assets/2.BXZ9sA4i.css"];
export const fonts = [];
