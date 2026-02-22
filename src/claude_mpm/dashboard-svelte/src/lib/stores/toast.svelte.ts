// Toast notification store using Svelte 5 runes
// Provides transient notifications for success/error/warning/info

type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
	id: string;
	type: ToastType;
	message: string;
	duration: number; // ms, 0 = no auto-dismiss
}

class ToastStore {
	toasts = $state<Toast[]>([]);

	add(type: ToastType, message: string, duration: number = 5000): string {
		const id = crypto.randomUUID();
		this.toasts = [...this.toasts, { id, type, message, duration }];

		if (duration > 0) {
			setTimeout(() => this.remove(id), duration);
		}

		return id;
	}

	remove(id: string) {
		this.toasts = this.toasts.filter((t) => t.id !== id);
	}

	success(message: string) {
		return this.add('success', message);
	}
	error(message: string) {
		return this.add('error', message, 8000);
	}
	warning(message: string) {
		return this.add('warning', message, 6000);
	}
	info(message: string) {
		return this.add('info', message);
	}
}

export const toastStore = new ToastStore();
