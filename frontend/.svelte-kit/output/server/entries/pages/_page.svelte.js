import "../../chunks/index-server.js";
import "../../chunks/server.js";
//#endregion
//#region src/lib/components/SummetryGame.svelte
function SummetryGame($$renderer, $$props) {
	$$renderer.component(($$renderer) => {
		let { defaultMode = "daily" } = $$props;
		$$renderer.push("<!--[0-->");
		$$renderer.push(`<div class="game-loading svelte-1vaf2ag">Loading...</div>`);
		$$renderer.push(`<!--]-->`);
	});
}
//#endregion
//#region src/routes/+page.svelte
function _page($$renderer) {
	$$renderer.push(`<main class="main-layout svelte-1uha8ag">`);
	SummetryGame($$renderer, {});
	$$renderer.push(`<!----> <footer class="footer-navigation svelte-1uha8ag"><a href="/solver" class="solver-link svelte-1uha8ag">🛠️ Open Standalone Solver &amp; Diagnostics</a></footer></main>`);
}
//#endregion
export { _page as default };
