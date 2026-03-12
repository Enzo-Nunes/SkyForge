<template>
	<div class="tracker-layout">
		<FilterPanel
			:REQUIREMENTS="REQUIREMENTS"
			:myLevels="myLevels"
			v-model:maxCost="maxCost"
			v-model:noBudget="noBudget"
			v-model:minVolume="minVolume"
			@levelChange="(key, val) => (myLevels[key] = val)"
			@reset="resetFilters"
		/>

		<div class="tracker-content">
			<div class="waiting" v-if="profits.length === 0">
				<div class="spinner"></div>
				<p>Waiting for calculator results…</p>
			</div>

			<template v-else>
				<div class="early-warning" v-if="uptimeSeconds !== null && uptimeSeconds < 604800">
					⚠ AH volume data is incomplete — the tool has been running for less than 7 days.
					<button class="guide-link" @click="$emit('go-to-guide')">Learn more in the Guide</button>
				</div>

				<div class="search-bar-wrapper">
					<input type="text" class="search-bar" v-model="searchQuery" placeholder="Search items…" />
				</div>

				<div class="table-wrap">
					<table>
						<thead>
							<tr>
								<th class="sortable" :class="sortClass('Rank')" @click="sortBy('Rank')">
									# <span class="sort-arrow">{{ sortArrow("Rank") }}</span>
								</th>
								<th>Item</th>
								<th class="sortable" :class="sortClass('Cost')" @click="sortBy('Cost')">
									Total Ingredient Cost <span class="sort-arrow">{{ sortArrow("Cost") }}</span>
								</th>
								<th class="sortable" :class="sortClass('Sell Value')" @click="sortBy('Sell Value')">
									Sell Value <span class="sort-arrow">{{ sortArrow("Sell Value") }}</span>
								</th>
								<th class="sortable" :class="sortClass('Profit')" @click="sortBy('Profit')">
									Profit <span class="sort-arrow">{{ sortArrow("Profit") }}</span>
								</th>
								<th class="sortable" :class="sortClass('Duration')" @click="sortBy('Duration')">
									Duration <span class="sort-arrow">{{ sortArrow("Duration") }}</span>
								</th>
								<th
									class="sortable"
									:class="sortClass('Profit per Hour')"
									@click="sortBy('Profit per Hour')"
								>
									Profit / hour <span class="sort-arrow">{{ sortArrow("Profit per Hour") }}</span>
								</th>
								<th
									class="sortable"
									:class="sortClass('Weekly Volume')"
									@click="sortBy('Weekly Volume')"
								>
									Weekly Volume <span class="sort-arrow">{{ sortArrow("Weekly Volume") }}</span>
								</th>

								<th>Recipe</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="item in profitsSorted.slice(0, visibleCount)"
								:key="item.Rank"
								:class="{ top3: item.Rank <= 3 }"
							>
								<td class="rank">
									<span class="badge" :class="'rank-' + item.Rank">{{ item.Rank }}</span>
								</td>
								<td class="name">{{ item.Name }}</td>
								<td class="number cost">{{ fmt(item.Cost) }}</td>
								<td class="number sell">
									<span
										class="vol-source"
										:class="item['Selling Market'] === 'Bazaar' ? 'vol-bz' : 'vol-ah'"
									>
										{{ item["Selling Market"] }}
									</span>
									{{ fmt(item["Sell Value"]) }}
								</td>
								<td class="number profit">+{{ fmt(item.Profit) }}</td>
								<td class="number">{{ fmtDuration(item.Duration) }}</td>
								<td class="number pph">{{ fmt(item["Profit per Hour"]) }}</td>
								<td class="number volume">
									{{ item["Volume Estimated"] ? "~" : "" }}{{ fmt(item["Weekly Volume"]) }}
								</td>
								<td class="recipe">
									<span v-for="(qty, mat) in item.Recipe" :key="mat" class="ingredient">
										{{ qty }}x {{ mat }}
										<span
											class="vol-source"
											:class="item['Recipe Markets']?.[mat] === 'Bazaar' ? 'vol-bz' : 'vol-ah'"
										>
											{{ item["Recipe Markets"]?.[mat] }}
										</span>
									</span>
								</td>
							</tr>
						</tbody>
					</table>
					<div class="load-more" v-if="visibleCount < profitsSorted.length">
						<button @click="visibleCount += 10">
							Load 10 more ({{ profitsSorted.length - visibleCount }} remaining)
						</button>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, watch, computed } from "vue";
import FilterPanel from "./FilterPanel.vue";

const props = defineProps({
	profits: Array,
	uptimeSeconds: { type: Number, default: null },
});

const emit = defineEmits(["go-to-guide"]);

const REQUIREMENTS = {
	"Heart of the Mountain Tier": 10,
	"Gemstone Collection": 11,
	"Tungsten Collection": 9,
	"Umber Collection": 9,
	"Glacite Collection": 9,
	"Hard Stone Collection": 7,
};

const savedLevels = JSON.parse(localStorage.getItem("skyforge_levels") || "null");
const myLevels = reactive(savedLevels || Object.fromEntries(Object.entries(REQUIREMENTS).map(([k, v]) => [k, v])));
const maxCost = ref(parseInt(localStorage.getItem("skyforge_maxCost") || "-1"));
const noBudget = ref(maxCost.value === -1);
const minVolume = ref(parseInt(localStorage.getItem("skyforge_minVolume") || "0"));

watch(noBudget, (val) => {
	if (val) {
		maxCost.value = -1;
	} else if (maxCost.value < 0) {
		maxCost.value = 0;
	}
});

watch(myLevels, () => {
	localStorage.setItem("skyforge_levels", JSON.stringify({ ...myLevels }));
	visibleCount.value = 10;
});

watch(maxCost, (val) => {
	localStorage.setItem("skyforge_maxCost", String(val));
	visibleCount.value = 10;
});

watch(minVolume, (val) => {
	localStorage.setItem("skyforge_minVolume", String(val));
	visibleCount.value = 10;
});

const profitsFiltered = computed(() =>
	props.profits.filter((item) => {
		for (const [key, level] of Object.entries(myLevels)) {
			if ((item.Requirements?.[key] ?? 0) > level) return false;
		}
		if (!noBudget.value && maxCost.value >= 0 && item.Cost > maxCost.value) return false;
		if (minVolume.value > 0 && (item["Weekly Volume"] ?? 0) < minVolume.value) return false;
		if (searchQuery.value && !item.Name.toLowerCase().includes(searchQuery.value.toLowerCase())) return false;
		return true;
	}),
);

const sortKey = ref("Profit per Hour");
const sortDir = ref("desc");
const visibleCount = ref(10);
const searchQuery = ref("");

function sortBy(key) {
	if (sortKey.value === key) {
		sortDir.value = sortDir.value === "desc" ? "asc" : "desc";
	} else {
		sortKey.value = key;
		sortDir.value = key === "Cost" || key === "Duration" || key === "Rank" ? "asc" : "desc";
	}
	visibleCount.value = 10;
}

function sortClass(key) {
	return { active: sortKey.value === key, asc: sortKey.value === key && sortDir.value === "asc" };
}

function sortArrow(key) {
	if (sortKey.value !== key) return "↕";
	return sortDir.value === "desc" ? "↓" : "↑";
}

const profitsSorted = computed(() => {
	const key = sortKey.value;
	const dir = sortDir.value === "desc" ? -1 : 1;
	return [...profitsFiltered.value].sort((a, b) => {
		const av = a[key] ?? 0;
		const bv = b[key] ?? 0;
		return (av < bv ? -1 : av > bv ? 1 : 0) * dir;
	});
});

function resetFilters() {
	for (const [key, max] of Object.entries(REQUIREMENTS)) {
		myLevels[key] = max;
	}
	maxCost.value = -1;
	minVolume.value = 0;
}

const fmt = (n) => Number(n).toLocaleString("en-US");

const fmtDuration = (hours) => {
	const totalSeconds = Math.round(hours * 3600);
	const d = Math.floor(totalSeconds / 86400);
	const h = Math.floor((totalSeconds % 86400) / 3600);
	const m = Math.floor((totalSeconds % 3600) / 60);
	const s = totalSeconds % 60;
	if (d > 0) return m > 0 ? `${d}d ${h}h ${m}m` : h > 0 ? `${d}d ${h}h` : `${d}d`;
	if (h > 0) return m > 0 ? `${h}h ${m}m` : `${h}h`;
	if (m > 0) return s > 0 ? `${m}m ${s}s` : `${m}m`;
	return `${s}s`;
};
</script>

<style scoped>
.tracker-layout {
	display: flex;
	align-items: flex-start;
	gap: 1.25rem;
}

.tracker-content {
	flex: 1;
	min-width: 0;
}

/* Search Bar */
.search-bar-wrapper {
	margin-bottom: 1rem;
}

.search-bar {
	width: 100%;
	padding: 0.65rem 1rem;
	background: var(--filter-input-bg);
	border: 1px solid var(--filter-input-border);
	border-radius: 0.5rem;
	color: var(--text-primary);
	font-size: 0.9rem;
	transition:
		border-color 0.15s,
		background 0.15s;
}

.search-bar::placeholder {
	color: var(--text-muted);
}

.search-bar:focus {
	outline: none;
	border-color: var(--accent);
	background: var(--bg-primary);
}

/* Waiting state */
.waiting {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 1.2rem;
	padding: 6rem 0;
	color: var(--text-muted);
}

.spinner {
	width: 36px;
	height: 36px;
	border: 3px solid var(--border);
	border-top-color: var(--accent);
	border-radius: 50%;
	animation: spin 0.9s linear infinite;
}

@keyframes spin {
	to {
		transform: rotate(360deg);
	}
}

/* Early uptime warning */
.early-warning {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	padding: 0.75rem 1rem;
	background: var(--warning-bg);
	border-left: 3px solid var(--warning-text);
	border-radius: 6px;
	color: var(--text-secondary);
	font-size: 0.8rem;
	margin-bottom: 1rem;
}

.guide-link {
	margin-left: auto;
	background: none;
	border: 1px solid var(--warning-text);
	color: var(--warning-text);
	border-radius: 4px;
	padding: 0.25rem 0.65rem;
	font-size: 0.75rem;
	cursor: pointer;
	white-space: nowrap;
	transition:
		background 0.15s,
		color 0.15s;
}

.guide-link:hover {
	background: var(--warning-text);
	color: var(--bg-primary);
}

/* Table */
.table-wrap {
	overflow-x: auto;
	border-radius: 0.75rem;
	border: 1px solid var(--border);
}

table {
	width: 100%;
	border-collapse: collapse;
	font-size: 0.85rem;
}

thead tr {
	background: var(--table-header-bg);
}

th {
	padding: 0.75rem 1rem;
	text-align: left;
	font-size: 0.7rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.07em;
	color: var(--text-muted);
	white-space: nowrap;
}

th:nth-child(1) {
	text-align: center;
}

th:nth-child(3),
th:nth-child(4),
th:nth-child(5),
th:nth-child(6),
th:nth-child(7),
th:nth-child(8) {
	text-align: right;
}

th.sortable {
	cursor: pointer;
	user-select: none;
	transition: color 0.15s;
}

th.sortable:hover {
	color: var(--text-tertiary);
}

th.sortable.active {
	color: var(--accent);
}

.sort-arrow {
	display: inline-block;
	width: 0.8em;
	font-style: normal;
	color: var(--text-muted);
}

th.sortable.active .sort-arrow {
	color: var(--accent);
}

tbody tr {
	border-top: 1px solid var(--table-row-border);
	transition: background 0.15s;
}

tbody tr:hover {
	background: var(--table-row-hover-bg);
}

tbody tr.top3 {
	background: var(--table-top3-bg);
}

td {
	padding: 0.65rem 1rem;
	vertical-align: top;
}

.rank {
	width: 3rem;
	text-align: center;
}

.badge {
	display: inline-block;
	width: 1.6rem;
	height: 1.6rem;
	line-height: 1.6rem;
	border-radius: 50%;
	text-align: center;
	font-size: 0.75rem;
	font-weight: 700;
	background: var(--badge-bg);
	color: var(--badge-color);
}

.badge.rank-1 {
	background: var(--badge-rank1-bg);
	color: var(--badge-rank1-color);
}

.badge.rank-2 {
	background: var(--badge-rank2-bg);
	color: var(--badge-rank2-color);
}

.badge.rank-3 {
	background: var(--badge-rank3-bg);
	color: var(--badge-rank3-color);
}

.name {
	font-weight: 500;
	color: var(--text-accent);
	white-space: nowrap;
}

.number {
	text-align: right;
	font-variant-numeric: tabular-nums;
	white-space: nowrap;
}

.cost {
	color: var(--color-cost);
}

.sell {
	color: var(--text-tertiary);
}

.profit {
	color: var(--color-profit);
	font-weight: 600;
}

.pph {
	color: var(--accent);
	font-weight: 600;
}

.volume {
	color: var(--color-volume);
}

.vol-source {
	display: inline-block;
	margin-left: 0.35rem;
	padding: 0.05rem 0.35rem;
	border-radius: 0.25rem;
	font-size: 0.65rem;
	font-weight: 700;
	line-height: 1;
	vertical-align: middle;
	letter-spacing: 0.04em;
}

.vol-bz {
	background: var(--vol-bz-bg);
	color: var(--vol-bz-text);
	border: 1px solid var(--vol-bz-border);
}

.vol-ah {
	background: var(--vol-ah-bg);
	color: var(--vol-ah-text);
	border: 1px solid var(--vol-ah-border);
}

.recipe {
	color: var(--color-secondary-text);
	font-size: 0.78rem;
	line-height: 1.8;
}

.ingredient {
	display: block;
	white-space: nowrap;
}

.load-more {
	display: flex;
	justify-content: center;
	padding: 1rem;
	border-top: 1px solid var(--border);
}

.load-more button {
	background: var(--load-more-btn-bg);
	color: var(--accent);
	border: 1px solid var(--load-more-btn-border);
	border-radius: 0.5rem;
	padding: 0.5rem 1.25rem;
	font-size: 0.8rem;
	font-weight: 600;
	cursor: pointer;
	transition:
		background 0.15s,
		border-color 0.15s;
}

.load-more button:hover {
	background: var(--border);
	border-color: var(--accent);
}
</style>
