import "../../../chunks/index-server.js";
import { b as escape_html, r as ensure_array_like, t as attr_class, y as attr } from "../../../chunks/server.js";
//#region src/routes/solver/+page.svelte
function _page($$renderer, $$props) {
	$$renderer.component(($$renderer) => {
		let solverGrid = Array(5).fill(null).map(() => Array(5).fill(""));
		let searchId = "";
		let isSolving = false;
		let solutions = [];
		let elapsedMs = 0;
		let branchesCount = 0;
		$$renderer.push(`<div class="solver-container svelte-1beuhz4"><header class="header svelte-1beuhz4"><h1 class="svelte-1beuhz4">🛠️ Standalone Solver &amp; Diagnostics</h1> <a href="/" class="back-link svelte-1beuhz4">🎮 Back to Main Game</a></header> <section class="load-by-id-section svelte-1beuhz4"><h3 class="svelte-1beuhz4">🔍 Load Board by ID</h3> <div class="search-bar svelte-1beuhz4"><input type="text" placeholder="Enter Board ID (UUID)..."${attr("value", searchId)} class="svelte-1beuhz4"/> <button class="search-btn svelte-1beuhz4">Load Clues</button></div> `);
		$$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--></section> <section class="grid-section svelte-1beuhz4"><h3 class="svelte-1beuhz4">🎛️ Input Grid &amp; Controls</h3> <div class="grid-box svelte-1beuhz4"><!--[-->`);
		const each_array = ensure_array_like(solverGrid);
		for (let r = 0, $$length = each_array.length; r < $$length; r++) {
			let row = each_array[r];
			$$renderer.push(`<div class="grid-row svelte-1beuhz4"><!--[-->`);
			const each_array_1 = ensure_array_like(row);
			for (let c = 0, $$length = each_array_1.length; c < $$length; c++) {
				let val = each_array_1[c];
				$$renderer.push(`<input type="text" class="solver-input svelte-1beuhz4"${attr("data-row", r)}${attr("data-col", c)}${attr("value", val)} maxlength="1"/>`);
			}
			$$renderer.push(`<!--]--></div>`);
		}
		$$renderer.push(`<!--]--></div> <div class="action-row svelte-1beuhz4"><button class="solve-btn svelte-1beuhz4"${attr("disabled", isSolving, true)}>${escape_html("✅ Solve Board")}</button> <button class="clear-btn svelte-1beuhz4">🧹 Clear Grid</button></div></section> `);
		if (solutions.length > 0) {
			$$renderer.push("<!--[0-->");
			$$renderer.push(`<section class="results-section svelte-1beuhz4"><div class="results-header svelte-1beuhz4"><h2 class="svelte-1beuhz4">🎉 Found ${escape_html(solutions.length)} valid completion(s) in ${escape_html(elapsedMs)} ms!</h2> `);
			$$renderer.push("<!--[-1-->");
			$$renderer.push(`<!--]--></div> <div class="stats-box svelte-1beuhz4"><h3 class="svelte-1beuhz4">🧠 Solver Statistics:</h3> <ul class="svelte-1beuhz4"><li class="svelte-1beuhz4">Variables Evaluated: <strong>26</strong> (25 grid cells + magic sum)</li> <li class="svelte-1beuhz4">Constraints Enforced: <strong>12</strong> magic sum equations</li> <li class="svelte-1beuhz4">Search Branches Evaluated: <strong>${escape_html(branchesCount)}</strong></li></ul></div> <div class="solutions-grid svelte-1beuhz4"><!--[-->`);
			const each_array_2 = ensure_array_like(solutions);
			for (let idx = 0, $$length = each_array_2.length; idx < $$length; idx++) {
				let sol = each_array_2[idx];
				$$renderer.push(`<div class="solution-card svelte-1beuhz4"><h4 class="svelte-1beuhz4">Solution #${escape_html(idx + 1)} (Magic Sum = ${escape_html(sol[0].reduce((a, b) => a + b, 0))}):</h4> <div class="matrix svelte-1beuhz4"><!--[-->`);
				const each_array_3 = ensure_array_like(sol);
				for (let rIdx = 0, $$length = each_array_3.length; rIdx < $$length; rIdx++) {
					let solRow = each_array_3[rIdx];
					$$renderer.push(`<div class="matrix-row svelte-1beuhz4"><!--[-->`);
					const each_array_4 = ensure_array_like(solRow);
					for (let cIdx = 0, $$length = each_array_4.length; cIdx < $$length; cIdx++) {
						let val = each_array_4[cIdx];
						$$renderer.push(`<span${attr_class("matrix-cell svelte-1beuhz4", void 0, { "given": solverGrid[rIdx][cIdx] !== "" })}>${escape_html(val)}</span>`);
					}
					$$renderer.push(`<!--]--></div>`);
				}
				$$renderer.push(`<!--]--></div></div>`);
			}
			$$renderer.push(`<!--]--></div></section>`);
		} else $$renderer.push("<!--[-1-->");
		$$renderer.push(`<!--]--></div>`);
	});
}
//#endregion
export { _page as default };
