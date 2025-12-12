// Theme store using Svelte 5 Runes with proper reactivity
class ThemeStore {
	current = $state<'light' | 'dark'>('dark');
	private initialized = false;

	constructor() {
		// Initialize from localStorage on first access (browser only)
		if (typeof window !== 'undefined' && !this.initialized) {
			const stored = localStorage.getItem('theme') as 'light' | 'dark' | null;
			if (stored) {
				this.current = stored;
			}
			this.applyTheme(this.current);
			this.initialized = true;
		}
	}

	private applyTheme(newTheme: 'light' | 'dark') {
		if (typeof document !== 'undefined') {
			if (newTheme === 'dark') {
				document.documentElement.classList.add('dark');
			} else {
				document.documentElement.classList.remove('dark');
			}
		}
	}

	toggle = () => {
		this.current = this.current === 'dark' ? 'light' : 'dark';
		if (typeof window !== 'undefined') {
			localStorage.setItem('theme', this.current);
			this.applyTheme(this.current);
		}
	};

	set = (newTheme: 'light' | 'dark') => {
		this.current = newTheme;
		if (typeof window !== 'undefined') {
			localStorage.setItem('theme', this.current);
			this.applyTheme(newTheme);
		}
	};
}

export const themeStore = new ThemeStore();
