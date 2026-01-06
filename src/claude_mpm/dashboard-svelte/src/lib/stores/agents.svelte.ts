/**
 * Agents Store - Builds hierarchical agent tree from events
 *
 * Processes events to create a tree structure showing:
 * - PM (root agent)
 * - Sub-agents (delegated via Task tool)
 * - Tool calls per agent
 * - TodoWrite activities per agent
 */

import { derived } from 'svelte/store';
import type { ClaudeEvent } from '$lib/types/events';

export interface AgentNode {
	id: string; // session_id or "pm" for root
	name: string; // Agent type (PM, Engineer, etc.)
	depth: number; // Hierarchy depth (0 = PM, 1 = first level delegation, etc.)
	sessionId: string;
	status: 'active' | 'completed' | 'error';
	startTime: number;
	endTime: number | null;
	parentId: string | null;
	children: AgentNode[];
	toolCalls: ToolCall[];
	groupedToolCalls: GroupedToolCall[];
	todos: TodoActivity[];
	plans: AgentPlan[]; // Work plans created by this agent
	userPrompt?: string; // Original user message (for PM)
	delegationPrompt?: string; // PM's prompt to this agent
	delegationDescription?: string; // Short description of delegation
	responses: AgentResponse[]; // Messages from this agent
}

export interface AgentResponse {
	timestamp: number;
	content: string;
	type: 'text' | 'tool_result' | 'error';
}

export interface ToolCall {
	id: string;
	toolName: string;
	operation: string;
	status: 'pending' | 'success' | 'error';
	timestamp: number;
	duration: number | null;
}

export interface GroupedToolCall {
	toolName: string;
	target: string; // file path, command, or description
	count: number;
	latestTimestamp: number;
	status: 'pending' | 'success' | 'error';
	instances: ToolCall[]; // Original calls for detail view
}

export interface TodoActivity {
	id: string;
	timestamp: number;
	todos: Array<{
		content: string;
		status: 'pending' | 'in_progress' | 'completed';
		activeForm?: string; // Present continuous form (e.g., "Researching...")
	}>;
}

export interface AgentPlan {
	timestamp: number;
	content: string;
	planFile?: string; // If written to a file
	status: 'draft' | 'approved' | 'completed';
	mode?: 'entered' | 'exited'; // Track plan mode transitions
}

/**
 * Extract session ID from event (matches socket.svelte.ts logic)
 */
function getSessionId(event: ClaudeEvent): string | null {
	return (
		event.session_id ||
		event.sessionId ||
		(event.data as any)?.session_id ||
		(event.data as any)?.sessionId ||
		event.source ||
		null
	);
}

/**
 * Extract agent type from delegation event
 */
function getAgentType(event: ClaudeEvent): string | null {
	if (typeof event.data !== 'object' || !event.data) return null;
	const data = event.data as Record<string, unknown>;

	// Check data.agent_type directly (for subagent_start events)
	if (data.agent_type && typeof data.agent_type === 'string') {
		return data.agent_type;
	}

	// Check delegation_details for agent_type (for Task pre_tool events)
	const delegationDetails = data.delegation_details;
	if (delegationDetails && typeof delegationDetails === 'object') {
		const details = delegationDetails as Record<string, unknown>;
		if (details.agent_type && typeof details.agent_type === 'string') {
			return details.agent_type;
		}
	}

	// Check tool_parameters for agent delegation
	const toolParams = data.tool_parameters;
	if (toolParams && typeof toolParams === 'object') {
		const params = toolParams as Record<string, unknown>;
		if (params.agent && typeof params.agent === 'string') {
			return params.agent;
		}
	}

	return null;
}

/**
 * Check if event is a Task tool delegation
 */
function isTaskDelegation(event: ClaudeEvent): boolean {
	if (event.subtype !== 'pre_tool') return false;

	if (typeof event.data !== 'object' || !event.data) return false;
	const data = event.data as Record<string, unknown>;

	// Check tool_name in data or tool_parameters
	const toolName = data.tool_name || (data.tool_parameters as any)?.tool_name;
	return toolName === 'Task';
}

/**
 * Check if event is a TodoWrite tool call
 */
function isTodoWrite(event: ClaudeEvent): boolean {
	if (event.subtype !== 'pre_tool') return false;

	if (typeof event.data !== 'object' || !event.data) return false;
	const data = event.data as Record<string, unknown>;

	const toolName = data.tool_name || (data.tool_parameters as any)?.tool_name;
	return toolName === 'TodoWrite';
}

/**
 * Check if event is an EnterPlanMode tool call
 */
function isEnterPlanMode(event: ClaudeEvent): boolean {
	if (event.subtype !== 'pre_tool') return false;

	if (typeof event.data !== 'object' || !event.data) return false;
	const data = event.data as Record<string, unknown>;

	const toolName = data.tool_name || (data.tool_parameters as any)?.tool_name;
	return toolName === 'EnterPlanMode';
}

/**
 * Check if event is an ExitPlanMode tool call
 */
function isExitPlanMode(event: ClaudeEvent): boolean {
	if (event.subtype !== 'pre_tool') return false;

	if (typeof event.data !== 'object' || !event.data) return false;
	const data = event.data as Record<string, unknown>;

	const toolName = data.tool_name || (data.tool_parameters as any)?.tool_name;
	return toolName === 'ExitPlanMode';
}

/**
 * Check if event is a Write tool call to a plan file
 */
function isPlanFileWrite(event: ClaudeEvent): boolean {
	if (event.subtype !== 'pre_tool') return false;

	if (typeof event.data !== 'object' || !event.data) return false;
	const data = event.data as Record<string, unknown>;

	const toolName = data.tool_name || (data.tool_parameters as any)?.tool_name;
	if (toolName !== 'Write') return false;

	const toolParams = data.tool_parameters as Record<string, unknown> | null;
	const filePath = (data.file_path || toolParams?.file_path) as string;

	// Check if filename contains "plan" or has typical plan file patterns
	return filePath && (
		filePath.toLowerCase().includes('plan') ||
		filePath.toLowerCase().includes('work-plan') ||
		filePath.toLowerCase().includes('task-plan')
	);
}

/**
 * Extract plan content from Write tool event
 */
function extractPlanContent(event: ClaudeEvent): { content: string; filePath?: string } | null {
	if (typeof event.data !== 'object' || !event.data) return null;
	const data = event.data as Record<string, unknown>;

	const toolParams = data.tool_parameters as Record<string, unknown> | null;
	const content = (toolParams?.content || data.content) as string;
	const filePath = (data.file_path || toolParams?.file_path) as string;

	if (!content) return null;

	return { content, filePath };
}

/**
 * Extract todos from TodoWrite event
 */
function extractTodos(event: ClaudeEvent): TodoActivity['todos'] {
	if (typeof event.data !== 'object' || !event.data) return [];
	const data = event.data as Record<string, unknown>;

	const toolParams = data.tool_parameters;
	if (!toolParams || typeof toolParams !== 'object') return [];

	const params = toolParams as Record<string, unknown>;
	const todos = params.todos;

	if (!Array.isArray(todos)) return [];

	return todos.map((todo: any) => ({
		content: todo.content || '',
		status: todo.status || 'pending',
		activeForm: todo.activeForm || undefined
	}));
}

/**
 * Extract correlation ID from event (matches tools store logic)
 */
function getEventCorrelationId(event: ClaudeEvent): string | null {
	if (typeof event.data !== 'object' || !event.data) return null;
	const data = event.data as Record<string, unknown>;
	return (data.correlation_id as string) || null;
}

/**
 * Extract tool name from tool event
 */
function getToolName(event: ClaudeEvent): string {
	if (typeof event.data !== 'object' || !event.data) return 'Unknown';
	const data = event.data as Record<string, unknown>;
	return (data.tool_name || (data.tool_parameters as any)?.tool_name || 'Unknown') as string;
}

/**
 * Extract target/grouping key for tool call
 */
function getToolTarget(event: ClaudeEvent): string {
	const toolName = getToolName(event);

	if (typeof event.data !== 'object' || !event.data) return 'unknown';
	const data = event.data as Record<string, unknown>;
	const toolParams = data.tool_parameters as Record<string, unknown> | null;

	switch (toolName) {
		case 'Bash':
			const description = (data.description || toolParams?.description) as string;
			return description || 'command';

		case 'Read':
		case 'Edit':
		case 'Write':
			const filePath = (data.file_path || toolParams?.file_path) as string;
			return filePath || 'unknown-file';

		case 'TodoWrite':
			return 'todos';

		case 'Task':
			const agentType = getAgentType(event);
			return agentType || 'agent';

		default:
			return toolName;
	}
}

/**
 * Create operation summary for tool call
 */
function getToolOperation(event: ClaudeEvent): string {
	const toolName = getToolName(event);

	if (typeof event.data !== 'object' || !event.data) return 'No details';
	const data = event.data as Record<string, unknown>;
	const toolParams = data.tool_parameters as Record<string, unknown> | null;

	switch (toolName) {
		case 'Bash':
			const description = (data.description || toolParams?.description) as string;
			if (description) return description.slice(0, 50);
			return 'Execute command';

		case 'Read':
			const filePath = (data.file_path || toolParams?.file_path) as string;
			return filePath ? `Read ${filePath.split('/').pop()}` : 'Read file';

		case 'Edit':
			const editPath = (data.file_path || toolParams?.file_path) as string;
			return editPath ? `Edit ${editPath.split('/').pop()}` : 'Edit file';

		case 'Write':
			const writePath = (data.file_path || toolParams?.file_path) as string;
			return writePath ? `Write ${writePath.split('/').pop()}` : 'Write file';

		case 'TodoWrite':
			return 'Update todos';

		case 'Task':
			const agentType = getAgentType(event);
			return agentType ? `Delegate to ${agentType}` : 'Delegate task';

		default:
			return `${toolName} execution`;
	}
}

/**
 * Group tool calls by tool name and target
 */
function groupToolCalls(toolCalls: ToolCall[]): GroupedToolCall[] {
	const groups = new Map<string, GroupedToolCall>();

	toolCalls.forEach(call => {
		// Extract filename from operation for better grouping
		let target = '';
		if (call.toolName === 'Read' || call.toolName === 'Edit' || call.toolName === 'Write') {
			// Extract filename from operation like "Read installer.py"
			const match = call.operation.match(/(?:Read|Edit|Write)\s+(.+)/);
			target = match ? match[1] : call.operation;
		} else if (call.toolName === 'Bash') {
			// Use first part of operation for bash commands
			target = call.operation.slice(0, 30);
		} else {
			target = call.operation;
		}

		const key = `${call.toolName}:${target}`;

		if (groups.has(key)) {
			const group = groups.get(key)!;
			group.count++;
			group.instances.push(call);
			// Update to latest timestamp
			if (call.timestamp > group.latestTimestamp) {
				group.latestTimestamp = call.timestamp;
			}
			// Update status: error > pending > success priority
			if (call.status === 'error' || (group.status === 'pending' && call.status !== 'success')) {
				group.status = call.status;
			}
		} else {
			groups.set(key, {
				toolName: call.toolName,
				target,
				count: 1,
				latestTimestamp: call.timestamp,
				status: call.status,
				instances: [call]
			});
		}
	});

	// Sort by latest timestamp (most recent first)
	return Array.from(groups.values()).sort((a, b) => b.latestTimestamp - a.latestTimestamp);
}

/**
 * Create agents store from events
 */
export function createAgentsStore(eventsStore: any): any {
	return derived(eventsStore, ($events) => {
		const events = $events as ClaudeEvent[];
		const agentMap = new Map<string, AgentNode>();
		const toolCallMap = new Map<string, ToolCall[]>(); // sessionId -> tool calls
		const todoMap = new Map<string, TodoActivity[]>(); // sessionId -> todos
		const planMap = new Map<string, AgentPlan[]>(); // sessionId -> plans

		// Create PM root node (always exists)
		const pmNode: AgentNode = {
			id: 'pm',
			name: 'PM',
			depth: 0,
			sessionId: 'pm',
			status: 'active',
			startTime: Date.now(),
			endTime: null,
			parentId: null,
			children: [],
			toolCalls: [],
			groupedToolCalls: [],
			todos: [],
			plans: [],
			responses: []
		};
		agentMap.set('pm', pmNode);

		// First pass: Identify agents from subagent_start/stop events and Task delegations
		events.forEach(event => {
			const sessionId = getSessionId(event);

			// Handle subagent lifecycle events
			if (event.subtype === 'subagent_start') {
				const agentType = getAgentType(event) || 'Agent';
				const timestamp = typeof event.timestamp === 'string'
					? new Date(event.timestamp).getTime()
					: event.timestamp;

				// Debug logging for all subagent_start events
				console.log('[AgentsStore] subagent_start detected:', {
					sessionId,
					agentType,
					timestamp: new Date(timestamp).toLocaleTimeString(),
					hasSessionId: !!sessionId
				});

				if (!sessionId) {
					console.warn('[AgentsStore] subagent_start missing session_id:', event);
					return;
				}

				// Always create a new agent for each subagent_start event
				// Each subagent_start should have a unique session_id
				// If we're seeing duplicate session_ids, that's a bug in the event source
				if (!agentMap.has(sessionId)) {
					agentMap.set(sessionId, {
						id: sessionId,
						name: agentType,
						depth: 1, // Will be adjusted later based on parent
						sessionId,
						status: 'active',
						startTime: timestamp,
						endTime: null,
						parentId: null, // Will be set when we find delegation
						children: [],
						toolCalls: [],
						groupedToolCalls: [],
						todos: [],
						plans: [],
						responses: []
					});
				} else {
					// Log if we're seeing duplicate session IDs (this would indicate a bug)
					console.warn('[AgentsStore] Duplicate session_id detected:', sessionId, 'agent_type:', agentType);
				}
			} else if (event.subtype === 'subagent_stop') {
				const agent = agentMap.get(sessionId);
				if (agent) {
					const timestamp = typeof event.timestamp === 'string'
						? new Date(event.timestamp).getTime()
						: event.timestamp;
					agent.endTime = timestamp;

					// Check for error in data
					if (typeof event.data === 'object' && event.data) {
						const data = event.data as Record<string, unknown>;
						if (data.error || data.is_error) {
							agent.status = 'error';
						} else {
							agent.status = 'completed';
						}
					} else {
						agent.status = 'completed';
					}
				}
			}

			// Handle Task delegations to establish parent-child relationships
			if (isTaskDelegation(event)) {
				const parentSessionId = sessionId;
				const agentType = getAgentType(event);

				// The next subagent_start event will be the child
				// Store delegation info temporarily
				if (agentType && !event.correlation_id) {
					// Mark this as pending delegation
					// We'll match it with subagent_start in second pass
				}
			}
		});

		// Second pass: Collect tool calls and todos per agent
		events.forEach(event => {
			const sessionId = getSessionId(event);
			if (!sessionId) return;

			const timestamp = typeof event.timestamp === 'string'
				? new Date(event.timestamp).getTime()
				: event.timestamp;

			// Track tool calls (pre_tool events)
			if (event.subtype === 'pre_tool') {
				const correlationId = getEventCorrelationId(event);
				if (!correlationId) return; // Skip events without correlation ID

				const toolName = getToolName(event);
				const operation = getToolOperation(event);

				const toolCall: ToolCall = {
					id: correlationId,
					toolName,
					operation,
					status: 'pending',
					timestamp,
					duration: null
				};

				if (!toolCallMap.has(sessionId)) {
					toolCallMap.set(sessionId, []);
				}
				toolCallMap.get(sessionId)!.push(toolCall);

				// Handle TodoWrite specially
				if (isTodoWrite(event)) {
					const todos = extractTodos(event);
					const todoActivity: TodoActivity = {
						id: correlationId,
						timestamp,
						todos
					};

					if (!todoMap.has(sessionId)) {
						todoMap.set(sessionId, []);
					}
					todoMap.get(sessionId)!.push(todoActivity);
				}

				// Handle plan mode transitions
				if (isEnterPlanMode(event)) {
					const plan: AgentPlan = {
						timestamp,
						content: 'Agent entered plan mode',
						status: 'draft',
						mode: 'entered'
					};

					if (!planMap.has(sessionId)) {
						planMap.set(sessionId, []);
					}
					planMap.get(sessionId)!.push(plan);
				}

				if (isExitPlanMode(event)) {
					const plan: AgentPlan = {
						timestamp,
						content: 'Agent exited plan mode',
						status: 'completed',
						mode: 'exited'
					};

					if (!planMap.has(sessionId)) {
						planMap.set(sessionId, []);
					}
					planMap.get(sessionId)!.push(plan);
				}

				// Handle plan file writes
				if (isPlanFileWrite(event)) {
					const planData = extractPlanContent(event);
					if (planData) {
						const plan: AgentPlan = {
							timestamp,
							content: planData.content,
							planFile: planData.filePath,
							status: 'draft'
						};

						if (!planMap.has(sessionId)) {
							planMap.set(sessionId, []);
						}
						planMap.get(sessionId)!.push(plan);
					}
				}
			}

			// Update tool call status (post_tool events)
			if (event.subtype === 'post_tool') {
				const correlationId = getEventCorrelationId(event);
				if (!correlationId) return; // Skip events without correlation ID

				const toolCalls = toolCallMap.get(sessionId);
				if (toolCalls) {
					const toolCall = toolCalls.find(tc => tc.id === correlationId);
					if (toolCall) {
						toolCall.duration = timestamp - toolCall.timestamp;

						// Check for error
						if (typeof event.data === 'object' && event.data) {
							const data = event.data as Record<string, unknown>;
							toolCall.status = (data.error || data.is_error) ? 'error' : 'success';
						} else {
							toolCall.status = 'success';
						}
					}
				}
			}
		});

		// Third pass: Capture prompts and responses
		events.forEach(event => {
			const sessionId = getSessionId(event);
			const timestamp = typeof event.timestamp === 'string'
				? new Date(event.timestamp).getTime()
				: event.timestamp;

			// Capture user prompts (for PM only)
			if (event.subtype === 'user_prompt' || event.type === 'user_prompt') {
				const data = event.data as Record<string, unknown>;
				const promptText = data.prompt_text as string;
				if (promptText && pmNode) {
					pmNode.userPrompt = promptText;
				}
			}

			// Capture delegation prompts from Task tool calls
			if (event.subtype === 'pre_tool') {
				const data = event.data as Record<string, unknown>;
				const toolName = data.tool_name as string;

				if (toolName === 'Task') {
					const delegationDetails = data.delegation_details as Record<string, unknown> | undefined;
					if (delegationDetails && sessionId) {
						const prompt = delegationDetails.prompt as string;
						const description = delegationDetails.description as string;

						// Find the next agent with this session ID (will be created in subagent_start)
						// We'll store this temporarily and assign it when we find the agent
						const agentType = delegationDetails.agent_type as string;

						// Look for agents created after this event
						events.forEach(laterEvent => {
							const laterSessionId = getSessionId(laterEvent);
							if (laterEvent.subtype === 'subagent_start' && laterSessionId) {
								const laterData = laterEvent.data as Record<string, unknown>;
								const laterAgentType = laterData.agent_type as string;

								// Match by agent type and ensure it's after the delegation
								if (laterAgentType === agentType) {
									const agent = agentMap.get(laterSessionId);
									if (agent && prompt) {
										agent.delegationPrompt = prompt;
										agent.delegationDescription = description;
									}
								}
							}
						});
					}
				}
			}

			// Capture agent responses from subagent_stop events
			if (event.subtype === 'subagent_stop' || event.type === 'subagent_stop') {
				const data = event.data as Record<string, unknown>;
				const output = data.output as string;

				if (output && sessionId) {
					const agent = agentMap.get(sessionId);
					if (agent) {
						// Store the agent's output/response
						agent.responses.push({
							timestamp,
							content: output,
							type: 'text'
						});
					}
				}
			}

			// Also capture any assistant messages if they exist
			if (event.type === 'assistant_message' || event.subtype === 'assistant_message') {
				const data = event.data as Record<string, unknown>;
				const content = data.content as string;

				if (content && sessionId) {
					const agent = agentMap.get(sessionId) || pmNode;
					if (agent) {
						agent.responses.push({
							timestamp,
							content,
							type: 'text'
						});
					}
				}
			}
		});

		// Fourth pass: Assign tool calls, todos, and plans to agents
		agentMap.forEach((agent, sessionId) => {
			agent.toolCalls = toolCallMap.get(sessionId) || [];
			agent.groupedToolCalls = groupToolCalls(agent.toolCalls);
			agent.todos = todoMap.get(sessionId) || [];
			agent.plans = planMap.get(sessionId) || [];
		});

		// Build hierarchy: For now, all agents are children of PM
		// In future, could parse delegation chains for deeper hierarchies
		const pmAgent = agentMap.get('pm')!;
		agentMap.forEach((agent, sessionId) => {
			if (sessionId !== 'pm') {
				agent.parentId = 'pm';
				pmAgent.children.push(agent);
			}
		});

		// Debug logging for final agent tree
		console.log('[AgentsStore] Final agent tree:', {
			totalAgents: agentMap.size,
			pmChildren: pmAgent.children.length,
			agents: Array.from(agentMap.values()).map(a => ({
				name: a.name,
				sessionId: a.sessionId.slice(0, 12),
				status: a.status,
				startTime: new Date(a.startTime).toLocaleTimeString()
			}))
		});

		// Assign PM's tool calls (tools called before any delegation)
		const pmTools: ToolCall[] = [];
		const pmTodos: TodoActivity[] = [];

		events.forEach(event => {
			const sessionId = getSessionId(event);

			// If no session_id, assume it's PM's activity
			if (!sessionId || sessionId === 'pm') {
				const timestamp = typeof event.timestamp === 'string'
					? new Date(event.timestamp).getTime()
					: event.timestamp;

				if (event.subtype === 'pre_tool') {
					const correlationId = getEventCorrelationId(event);
					if (!correlationId) return; // Skip events without correlation ID

					const toolName = getToolName(event);
					const operation = getToolOperation(event);

					pmTools.push({
						id: correlationId,
						toolName,
						operation,
						status: 'pending',
						timestamp,
						duration: null
					});

					if (isTodoWrite(event)) {
						pmTodos.push({
							id: correlationId,
							timestamp,
							todos: extractTodos(event)
						});
					}
				}
			}
		});

		pmAgent.toolCalls = [...pmTools, ...pmAgent.toolCalls];
		pmAgent.groupedToolCalls = groupToolCalls(pmAgent.toolCalls);
		pmAgent.todos = [...pmTodos, ...pmAgent.todos];
		// Plans are already assigned from planMap

		return pmAgent; // Return root of tree
	});
}
