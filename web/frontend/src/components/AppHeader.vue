<template>
	<header>
		<div class="header-left">
			<h1>
				⚒ SkyForge <span class="version">v{{ version }}</span>
			</h1>
			<span class="subtitle">Hypixel Skyblock Forge Profit Tracker</span>
		</div>
		<div class="header-right">
			<div class="meta-info">
				<span v-if="lastUpdated">Updated {{ lastUpdated }}</span>
				<span v-if="uptimeLabel">Uptime {{ uptimeLabel }}</span>
			</div>
			<div class="theme-switch-container">
				<label class="theme-switch" :title="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'">
					<input type="checkbox" :checked="theme === 'light'" @change="toggleTheme" />
					<span class="slider"></span>
				</label>
			</div>
			<span class="status" :class="status">{{ statusLabel }}</span>
		</div>
	</header>
</template>

<script setup>
import { computed } from "vue";
import { useTheme } from "../composables/useTheme.js";

const props = defineProps({
	lastUpdated: String,
	status: String,
	uptimeSeconds: Number,
});

const version = import.meta.env.VITE_APP_VERSION || "dev";
const { theme, toggleTheme } = useTheme();

const statusLabel = computed(
	() =>
		({
			connecting: "Connecting…",
			connected: "Live",
			disconnected: "Disconnected",
			offline: "Offline",
		})[props.status],
);

const uptimeLabel = computed(() => {
	if (!props.uptimeSeconds) return null;
	const days = Math.floor(props.uptimeSeconds / 86400);
	const hours = Math.floor((props.uptimeSeconds % 86400) / 3600);
	const mins = Math.floor((props.uptimeSeconds % 3600) / 60);
	if (days > 0) return `${days} day${days > 1 ? "s" : ""}`;
	if (hours > 0) return `${hours} hour${hours > 1 ? "s" : ""}`;
	return `${mins} minute${mins > 1 ? "s" : ""}`;
});
</script>

<style scoped>
header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding-bottom: 1.25rem;
	border-bottom: 1px solid var(--border);
	margin-bottom: 1.5rem;
}

.header-left {
	display: flex;
	flex-direction: column;
	gap: 0.2rem;
}

h1 {
	font-size: 1.6rem;
	font-weight: 700;
	letter-spacing: -0.02em;
	color: var(--accent);
}

.version {
	font-size: 0.75rem;
	color: var(--text-muted);
	margin-left: 0.5rem;
}

.subtitle {
	font-size: 0.8rem;
	color: var(--color-secondary-text);
}

.header-right {
	display: flex;
	align-items: center;
	gap: 1.5rem;
}

.meta-info {
	display: flex;
	flex-direction: column;
	gap: 0.3rem;
	align-items: flex-end;
}

.meta-info > span {
	font-size: 0.75rem;
	color: var(--text-muted);
}

.theme-switch-container {
	display: flex;
	align-items: center;
}

.theme-switch {
	position: relative;
	display: inline-block;
	width: 2.5rem;
	height: 1.4rem;
	cursor: pointer;
}

.theme-switch input {
	opacity: 0;
	width: 0;
	height: 0;
}

.slider {
	position: absolute;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background-color: var(--text-muted);
	border-radius: 34px;
	transition: all 0.3s ease;
	display: flex;
	align-items: center;
	padding: 0 0.2rem;
}

.slider::before {
	content: "🌙";
	position: absolute;
	height: 1rem;
	width: 1rem;
	left: 0.2rem;
	bottom: 0.2rem;
	background-color: var(--bg-primary);
	border-radius: 50%;
	transition: all 0.3s ease;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 0.6rem;
}

.theme-switch input:checked + .slider {
	background-color: var(--accent);
}

.theme-switch input:checked + .slider::before {
	content: "☀️";
	transform: translateX(1.1rem);
}

.status {
	font-size: 0.72rem;
	font-weight: 600;
	padding: 0.25rem 0.7rem;
	border-radius: 999px;
	text-transform: uppercase;
	letter-spacing: 0.05em;
}

.status.connected {
	background: var(--status-connected-bg);
	color: var(--status-connected-text);
}

.status.connecting {
	background: var(--status-connecting-bg);
	color: var(--status-connecting-text);
}

.status.disconnected {
	background: var(--status-disconnected-bg);
	color: var(--status-disconnected-text);
}

.status.offline {
	background: var(--status-offline-bg);
	color: var(--status-offline-text);
}
</style>
