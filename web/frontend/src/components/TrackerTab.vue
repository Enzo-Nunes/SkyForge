<template>
	<div class="tracker-layout">
		<FilterPanel :REQUIREMENTS="REQUIREMENTS" :myLevels="myLevels" v-model:maxCost="maxCost"
			v-model:noBudget="noBudget" v-model:minVolume="minVolume" @levelChange="(key, val) => (myLevels[key] = val)"
			@reset="resetFilters" />

		<div class="tracker-content">
			<div class="waiting" v-if="profits.length === 0">
				<div class="spinner"></div>
				<p>Waiting for calculator results…</p>
			</div>

			<div class="table-wrap" v-else>
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
							<th class="sortable" :class="sortClass('Profit per Hour')"
								@click="sortBy('Profit per Hour')">
								Profit / hour <span class="sort-arrow">{{ sortArrow("Profit per Hour") }}</span>
							</th>
							<th class="sortable" :class="sortClass('Weekly Volume')" @click="sortBy('Weekly Volume')">
								Weekly Volume <span class="sort-arrow">{{ sortArrow("Weekly Volume") }}</span>
							</th>

							<th>Recipe</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="item in profitsSorted.slice(0, visibleCount)" :key="item.Rank"
							:class="{ top3: item.Rank <= 3 }">
							<td class="rank">
								<span class="badge" :class="'rank-' + item.Rank">{{ item.Rank }}</span>
							</td>
							<td class="name">{{ item.Name }}</td>
							<td class="number cost">{{ fmt(item.Cost) }}</td>
							<td class="number sell">
								<span class="vol-source"
									:class="item['Selling Market'] === 'Bazaar' ? 'vol-bz' : 'vol-ah'">
									{{ item["Selling Market"] }}
								</span>
								{{ fmt(item["Sell Value"]) }}
							</td>
							<td class="number profit">+{{ fmt(item.Profit) }}</td>
							<td class="number">{{ fmtDuration(item.Duration) }}</td>
							<td class="number pph">{{ fmt(item["Profit per Hour"]) }}</td>
							<td class="number volume">{{ item["Volume Estimated"] ? "~" : "" }}{{ fmt(item["Weekly Volume"]) }}</td>
							<td class="recipe">
								<span v-for="(qty, mat) in item.Recipe" :key="mat" class="ingredient">
									{{ qty }}x {{ mat }}
									<span class="vol-source"
										:class="item['Recipe Markets']?.[mat] === 'Bazaar' ? 'vol-bz' : 'vol-ah'">
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
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, watch, computed } from "vue";
import FilterPanel from "./FilterPanel.vue";

const props = defineProps({
	profits: Array,
});

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
		return true;
	}),
);

const sortKey = ref("Profit per Hour");
const sortDir = ref("desc");
const visibleCount = ref(10);

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

/* Waiting state */
.waiting {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 1.2rem;
	padding: 6rem 0;
	color: #475569;
}

.spinner {
	width: 36px;
	height: 36px;
	border: 3px solid #1e1e2e;
	border-top-color: #a78bfa;
	border-radius: 50%;
	animation: spin 0.9s linear infinite;
}

@keyframes spin {
	to {
		transform: rotate(360deg);
	}
}

/* Table */
.table-wrap {
	overflow-x: auto;
	border-radius: 0.75rem;
	border: 1px solid #1e1e2e;
}

table {
	width: 100%;
	border-collapse: collapse;
	font-size: 0.85rem;
}

thead tr {
	background: #13131f;
}

th {
	padding: 0.75rem 1rem;
	text-align: left;
	font-size: 0.7rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.07em;
	color: #475569;
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
	color: #94a3b8;
}

th.sortable.active {
	color: #a78bfa;
}

.sort-arrow {
	display: inline-block;
	width: 0.8em;
	font-style: normal;
	color: #2e3a4e;
}

th.sortable.active .sort-arrow {
	color: #a78bfa;
}

tbody tr {
	border-top: 1px solid #1a1a2e;
	transition: background 0.15s;
}

tbody tr:hover {
	background: #13131f;
}

tbody tr.top3 {
	background: #0f0f1f;
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
	background: #1e1e2e;
	color: #94a3b8;
}

.badge.rank-1 {
	background: #713f12;
	color: #fde68a;
}

.badge.rank-2 {
	background: #1c2637;
	color: #93c5fd;
}

.badge.rank-3 {
	background: #1c1917;
	color: #d6a87a;
}

.name {
	font-weight: 500;
	color: #f1f5f9;
	white-space: nowrap;
}

.number {
	text-align: right;
	font-variant-numeric: tabular-nums;
	white-space: nowrap;
}

.cost {
	color: #f87171;
}

.sell {
	color: #94a3b8;
}

.profit {
	color: #4ade80;
	font-weight: 600;
}

.pph {
	color: #a78bfa;
	font-weight: 600;
}

.volume {
	color: #67e8f9;
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
	background: #1a2e2e;
	color: #67e8f9;
	border: 1px solid #164e6380;
}

.vol-ah {
	background: #2a1f2e;
	color: #c084fc;
	border: 1px solid #6b21a880;
}

.recipe {
	color: #64748b;
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
	border-top: 1px solid #1e1e2e;
}

.load-more button {
	background: #13131f;
	color: #a78bfa;
	border: 1px solid #2e2e4e;
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
	background: #1a1a2e;
	border-color: #a78bfa;
}
</style>
