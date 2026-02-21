
The dashboard feature which provides the "Config" tab to display Agents and Skills tabs needs investigation.

The problem is:
 1) Deployed agents are listed using a underscore or dash naming convention, e.g. "svelte_engineer" and the Available agents are listed using spaces, e.g. "Svelte Engineer".
 2) This has been a problem before and has not been addressed fully. 
 3) This quite likely relates to using incorrect id or naming attributes we retrieve from the backend, or the backend provinding inconsistent naming data.
 4) This causes confusion, for example "svelte_engineer" is deployed, but we show the same agent as "Svelte Engineer" in the Available agents list, which makes it look like there are two different agents instead of one deployed agent.

The "/api/config/agents/deployed" API call returns a list of deployed agents, the agent record has a name attribute, but no agent_id attribute.
The "/api/config/agents/available" API call returns a list of available agents, the agent record has an agent_id attribute, and also a name attribute in the metadata object.
This discrepency is quite likely what is causing the UI to display the deployed agents and available agents with different naming conventions, and treating them as different agents.
 
Goal is:
    1) Investigate the root cause of this issue, whether it's in the backend or frontend code.
    2) Propose a solution to ensure consistent naming convention for agents across the dashboard. Ideally using the underscore/dash convention (agent_id)
    3) Verify end to end implementation to identify any related edge cases or issues.

Create an agent team to explore this from different angles. one of the teammates to play devil's advocate to challenge assumptions and proposed solutions.

Write your findings in docs-local/research/agent-skill-naming-v1/ 

 
