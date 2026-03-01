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
					<input class="cost-input" type="number" min="0" :value="maxCost"
						@input="$emit('update:maxCost', Number($event.target.value))" :disabled="noBudget" />
					<span class="filter-max">coins</span>
				</div>
				<label class="no-budget-label">
					<input type="checkbox" :checked="noBudget"
						@change="$emit('update:noBudget', $event.target.checked)" />
					No budget limit
				</label>
			</div>
			<div class="filter-field">
				<span class="filter-label">Min Weekly Volume</span>
				<div class="filter-controls">
					<input class="cost-input" type="number" min="0" :value="minVolume"
						@input="$emit('update:minVolume', Number($event.target.value))" />
					<span class="filter-max">/ week</span>
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
});

defineEmits(["levelChange", "update:maxCost", "update:noBudget", "update:minVolume", "reset"]);
</script>

<style scoped>
.filter-panel {
	flex: 0 0 13rem;
	background: #13131f;
	border: 1px solid #1e1e2e;
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
	color: #94a3b8;
	font-size: 0.75rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.04em;
}

.filter-field select {
	background: #0d0d14;
	border: 1px solid #2e2e4e;
	border-radius: 0.35rem;
	color: #e2e8f0;
	padding: 0.25rem 0.4rem;
	font-size: 0.8rem;
	cursor: pointer;
}

.filter-field select:focus {
	outline: none;
	border-color: #a78bfa;
}

.cost-input {
	width: 100%;
	max-width: 7rem;
	background: #0d0d14;
	border: 1px solid #2e2e4e;
	border-radius: 0.35rem;
	color: #e2e8f0;
	padding: 0.25rem 0.4rem;
	font-size: 0.8rem;
	text-align: center;
}

.cost-input:focus {
	outline: none;
	border-color: #a78bfa;
}

.cost-input:disabled {
	opacity: 0.2;
	cursor: not-allowed;
}

.no-budget-label {
	display: flex;
	align-items: center;
	gap: 0.35rem;
	color: #64748b;
	font-size: 0.78rem;
	cursor: pointer;
	user-select: none;
	white-space: nowrap;
}

.no-budget-label input[type="checkbox"] {
	accent-color: #a78bfa;
	cursor: pointer;
	width: 0.85rem;
	height: 0.85rem;
}

.filter-max {
	color: #475569;
	font-size: 0.75rem;
	white-space: nowrap;
}

.filter-reset {
	background: none;
	border: 1px solid #2e2e4e;
	border-radius: 0.4rem;
	color: #64748b;
	font-size: 0.75rem;
	padding: 0.25rem 0.75rem;
	cursor: pointer;
	transition:
		color 0.15s,
		border-color 0.15s;
}

.filter-reset:hover {
	color: #f87171;
	border-color: #f87171;
}
</style>
