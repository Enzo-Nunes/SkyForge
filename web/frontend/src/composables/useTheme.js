import { ref } from "vue";

const THEME_STORAGE_KEY = "theme";
const SYSTEM_DARK_QUERY = "(prefers-color-scheme: dark)";
const SYSTEM_LIGHT_QUERY = "(prefers-color-scheme: light)";

let systemThemeListenerAttached = false;

function getInitialTheme() {
	if (typeof window === "undefined") {
		return "dark";
	}

	// Check if user has a saved preference
	const saved = localStorage.getItem(THEME_STORAGE_KEY);
	if (saved) {
		return saved;
	}

	// Follow a light system preference. Browsers report "light" when the OS has no setting at all,
	// so only systems that explicitly prefer dark (or unsupported browsers) get the dark default.
	if (window.matchMedia && window.matchMedia(SYSTEM_LIGHT_QUERY).matches) {
		return "light";
	}

	return "dark";
}

const theme = ref(getInitialTheme());

export function useTheme() {
	function setTheme(newTheme, options = {}) {
		const { persist = true } = options;
		theme.value = newTheme;

		if (typeof document !== "undefined") {
			document.documentElement.setAttribute("data-theme", newTheme);
		}

		if (persist && typeof window !== "undefined") {
			localStorage.setItem(THEME_STORAGE_KEY, newTheme);
		}
	}

	function toggleTheme() {
		setTheme(theme.value === "dark" ? "light" : "dark");
	}

	// Set initial theme on app load
	if (typeof document !== "undefined" && !document.documentElement.hasAttribute("data-theme")) {
		document.documentElement.setAttribute("data-theme", theme.value);
	}

	// Listen for system theme changes once for the app lifetime.
	if (!systemThemeListenerAttached && typeof window !== "undefined" && window.matchMedia) {
		const darkModeQuery = window.matchMedia(SYSTEM_DARK_QUERY);
		const handleSystemThemeChange = (e) => {
			// Only apply system changes when user did not set a manual preference.
			if (!localStorage.getItem(THEME_STORAGE_KEY)) {
				setTheme(e.matches ? "dark" : "light", { persist: false });
			}
		};

		if (darkModeQuery.addEventListener) {
			darkModeQuery.addEventListener("change", handleSystemThemeChange);
		} else if (darkModeQuery.addListener) {
			darkModeQuery.addListener(handleSystemThemeChange);
		}

		systemThemeListenerAttached = true;
	}

	return {
		theme,
		setTheme,
		toggleTheme,
	};
}
