<template>
	<aside class="filter-panel">
		<div class="filter-grid">
			<label v-for="(max, key) in REQUIREMENTS" :key="key" class="filter-field">
				<span class="filter-label">{{ key }}</span>
				<div class="filter-controls">
					<select :value="myLevels[key]" @change="$emit('levelChange', key, Number($event.target.value))">
						<option v-for="n in max + 1" :key="n - 1" :value="n - 1">{{ n - 1 }}</option>
					</select>
					<span class="filter-max">/ {{ max }}</span>
				</div>
			</label>
			<div class="filter-field">
				<span class="filter-label">Max Cost</span>
				<div class="filter-controls">
					<input
						class="cost-input"
						type="number"
						min="0"
						:value="maxCost"
						@input="$emit('update:maxCost', Number($event.target.value))"
						:disabled="noBudget"
					/>
					<span class="filter-max">coins</span>
				</div>
				<label class="no-budget-label">
					<input
						type="checkbox"
						:checked="noBudget"
						@change="$emit('update:noBudget', $event.target.checked)"
					/>
					No budget limit
				</label>
			</div>
			<div class="filter-field">
				<span class="filter-label">Min Weekly Volume</span>
				<div class="filter-controls">
					<input
						class="cost-input"
						type="number"
						min="0"
						:value="minVolume"
						@input="$emit('update:minVolume', Number($event.target.value))"
					/>
					<span class="filter-max">/ week</span>
				</div>
			</div>
			<div class="filter-field">
				<span class="filter-label">Recipe Source</span>
				<div class="filter-controls">
					<select :value="recipeSource" @change="$emit('update:recipeSource', $event.target.value)">
						<option value="both">Both</option>
						<option value="bazaar">Bazaar only</option>
					</select>
				</div>
			</div>
			<div class="filter-field">
				<span class="filter-label">Sell Market</span>
				<div class="filter-controls">
					<select :value="sellMarket" @change="$emit('update:sellMarket', $event.target.value)">
						<option value="both">Both</option>
						<option value="bazaar">Bazaar</option>
						<option value="ah">AH</option>
					</select>
				</div>
			</div>
		</div>
		<button class="filter-reset" @click="$emit('reset')">Reset</button>
	</aside>
</template>

<script setup>
defineProps({
	REQUIREMENTS: Object,
	myLevels: Object,
	maxCost: Number,
	noBudget: Boolean,
	minVolume: Number,
	recipeSource: String,
	sellMarket: String,
});

defineEmits([
	"levelChange",
	"update:maxCost",
	"update:noBudget",
	"update:minVolume",
	"update:recipeSource",
	"update:sellMarket",
	"reset",
]);
</script>

<style scoped>
.filter-panel {
	flex: 0 0 13rem;
	background: var(--filter-bg);
	border: 1px solid var(--border);
	border-radius: 0.75rem;
	padding: 1rem 1rem 0.75rem;
	position: sticky;
	top: 1rem;
}

.filter-grid {
	display: flex;
	flex-direction: column;
	gap: 0.85rem;
	margin-bottom: 0.75rem;
}

.filter-field {
	display: flex;
	flex-direction: column;
	gap: 0.3rem;
	font-size: 0.8rem;
}

.filter-controls {
	display: flex;
	align-items: center;
	gap: 0.4rem;
}

.filter-label {
	color: var(--text-tertiary);
	font-size: 0.75rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.04em;
}

.filter-field select {
	background: var(--filter-input-bg);
	border: 1px solid var(--filter-input-border);
	border-radius: 0.35rem;
	color: var(--text-primary);
	padding: 0.25rem 0.4rem;
	font-size: 0.8rem;
	cursor: pointer;
	transition: all 0.2s;
}

.filter-field select:focus {
	outline: none;
	border-color: var(--accent);
}

.cost-input {
	width: 100%;
	max-width: 7rem;
	background: var(--filter-input-bg);
	border: 1px solid var(--filter-input-border);
	border-radius: 0.35rem;
	color: var(--text-primary);
	padding: 0.25rem 0.4rem;
	font-size: 0.8rem;
	text-align: center;
	transition: all 0.2s;
}

.cost-input:focus {
	outline: none;
	border-color: var(--accent);
}

.cost-input:disabled {
	opacity: 0.2;
	cursor: not-allowed;
}

.no-budget-label {
	display: flex;
	align-items: center;
	gap: 0.35rem;
	color: var(--color-secondary-text);
	font-size: 0.78rem;
	cursor: pointer;
	user-select: none;
	white-space: nowrap;
}

.no-budget-label input[type="checkbox"] {
	accent-color: var(--accent);
	cursor: pointer;
	width: 0.85rem;
	height: 0.85rem;
}

.filter-max {
	color: var(--text-muted);
	font-size: 0.75rem;
	white-space: nowrap;
}

.filter-reset {
	background: none;
	border: 1px solid var(--filter-input-border);
	border-radius: 0.4rem;
	color: var(--color-secondary-text);
	font-size: 0.75rem;
	padding: 0.25rem 0.75rem;
	cursor: pointer;
	transition:
		color 0.15s,
		border-color 0.15s;
}

.filter-reset:hover {
	color: var(--color-cost);
	border-color: var(--color-cost);
}
</style>
