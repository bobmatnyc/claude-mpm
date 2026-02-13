export interface PaginationState {
	offset: number;
	limit: number;
	total: number;
}

export interface PaginatedResponse<T> {
	items: T[];
	total: number;
	offset: number;
	limit: number;
	has_more: boolean;
}

export function getPageRange(state: PaginationState): { start: number; end: number } {
	const start = state.total === 0 ? 0 : state.offset + 1;
	const end = Math.min(state.offset + state.limit, state.total);
	return { start, end };
}

export function encodeCursor(offset: number, limit: number): string {
	return btoa(JSON.stringify({ offset, limit }));
}

export function decodeCursor(cursor: string): { offset: number; limit: number } {
	try {
		return JSON.parse(atob(cursor));
	} catch {
		return { offset: 0, limit: 20 };
	}
}

export function createPaginationState(limit: number = 20): PaginationState {
	return { offset: 0, limit, total: 0 };
}

export function nextPage(state: PaginationState): PaginationState {
	const newOffset = state.offset + state.limit;
	if (newOffset >= state.total) return state;
	return { ...state, offset: newOffset };
}

export function previousPage(state: PaginationState): PaginationState {
	const newOffset = Math.max(0, state.offset - state.limit);
	return { ...state, offset: newOffset };
}

export function hasNextPage(state: PaginationState): boolean {
	return state.offset + state.limit < state.total;
}

export function hasPreviousPage(state: PaginationState): boolean {
	return state.offset > 0;
}
