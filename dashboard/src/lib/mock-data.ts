// ─── Types matching backend API response schemas ───────────────────────────

export interface AgentResponse {
  id: string;
  name: string;
  quota_profile: Record<string, unknown>;
  capabilities: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface TaskSpec {
  type: "data_structuring" | "research_extraction" | "coding";
  description: string;
  input_data: Record<string, unknown>;
  output_schema?: Record<string, unknown>;
  validation_method?: string;
  token_estimate?: number;
}

export interface TaskResponse {
  id: string;
  task_spec: TaskSpec;
  status: "open" | "claimed" | "submitted" | "validating" | "completed" | "failed" | "expired";
  publisher_id: string;
  claimed_by: string | null;
  reward: number;
  deadline_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SubmissionResponse {
  id: string;
  task_id: string;
  agent_id: string;
  output_data: Record<string, unknown>;
  submitted_at: string;
  created_at: string;
  updated_at: string;
}

export interface ValidationRunResponse {
  id: string;
  submission_id: string;
  validator_type: "schema" | "rule" | "test" | "consensus" | "llm_judge";
  passed: boolean;
  score: number;
  details: Record<string, unknown>;
  validated_at: string;
}

export interface LedgerEntry {
  id: string;
  agent_id: string;
  task_id: string | null;
  amount: number;
  entry_type: "reward" | "penalty";
  created_at: string;
  updated_at: string;
}

export interface ReputationMetrics {
  completion_rate: number;
  pass_rate: number;
  avg_latency_seconds: number;
  token_efficiency: number;
  rework_rate: number;
  quality_score: number;
}

export interface ReputationResponse {
  id: string;
  agent_id: string;
  metrics: ReputationMetrics;
  snapshot_at: string;
  created_at: string;
  updated_at: string;
}

// ─── Mock UUIDs ────────────────────────────────────────────────────────────

const AGENT_IDS = [
  "a1000000-0000-4000-8000-000000000001",
  "a1000000-0000-4000-8000-000000000002",
  "a1000000-0000-4000-8000-000000000003",
  "a1000000-0000-4000-8000-000000000004",
  "a1000000-0000-4000-8000-000000000005",
] as const;

const TASK_IDS = [
  "b2000000-0000-4000-8000-000000000001",
  "b2000000-0000-4000-8000-000000000002",
  "b2000000-0000-4000-8000-000000000003",
  "b2000000-0000-4000-8000-000000000004",
  "b2000000-0000-4000-8000-000000000005",
  "b2000000-0000-4000-8000-000000000006",
  "b2000000-0000-4000-8000-000000000007",
  "b2000000-0000-4000-8000-000000000008",
  "b2000000-0000-4000-8000-000000000009",
  "b2000000-0000-4000-8000-000000000010",
] as const;

const SUBMISSION_IDS = [
  "c3000000-0000-4000-8000-000000000001",
  "c3000000-0000-4000-8000-000000000002",
  "c3000000-0000-4000-8000-000000000003",
  "c3000000-0000-4000-8000-000000000004",
  "c3000000-0000-4000-8000-000000000005",
  "c3000000-0000-4000-8000-000000000006",
  "c3000000-0000-4000-8000-000000000007",
  "c3000000-0000-4000-8000-000000000008",
  "c3000000-0000-4000-8000-000000000009",
  "c3000000-0000-4000-8000-000000000010",
  "c3000000-0000-4000-8000-000000000011",
  "c3000000-0000-4000-8000-000000000012",
  "c3000000-0000-4000-8000-000000000013",
  "c3000000-0000-4000-8000-000000000014",
  "c3000000-0000-4000-8000-000000000015",
] as const;

// ─── Agents (5) ────────────────────────────────────────────────────────────

export const mockAgents: AgentResponse[] = [
  {
    id: AGENT_IDS[0],
    name: "data-parser-bot",
    status: "active",
    quota_profile: { provider: "anthropic", model: "claude-3-haiku", daily_task_budget: 100, safe_token_cap: 50000 },
    capabilities: { languages: ["python", "javascript"], specialties: ["data_structuring"] },
    created_at: "2026-03-01T08:00:00Z",
    updated_at: "2026-03-13T10:00:00Z",
  },
  {
    id: AGENT_IDS[1],
    name: "research-crawler",
    status: "active",
    quota_profile: { provider: "anthropic", model: "claude-sonnet-4-6", daily_task_budget: 50, safe_token_cap: 100000 },
    capabilities: { languages: ["python"], specialties: ["research_extraction", "coding"] },
    created_at: "2026-03-02T09:00:00Z",
    updated_at: "2026-03-13T09:30:00Z",
  },
  {
    id: AGENT_IDS[2],
    name: "code-reviewer-agent",
    status: "active",
    quota_profile: { provider: "openai", model: "gpt-4o", daily_task_budget: 75, safe_token_cap: 80000 },
    capabilities: { languages: ["python", "typescript", "rust"], specialties: ["coding"] },
    created_at: "2026-03-03T14:00:00Z",
    updated_at: "2026-03-12T18:00:00Z",
  },
  {
    id: AGENT_IDS[3],
    name: "metric-extractor",
    status: "active",
    quota_profile: { provider: "anthropic", model: "claude-3-haiku", daily_task_budget: 200, safe_token_cap: 30000 },
    capabilities: { languages: ["python"], specialties: ["data_structuring", "research_extraction"] },
    created_at: "2026-03-05T11:00:00Z",
    updated_at: "2026-03-13T07:00:00Z",
  },
  {
    id: AGENT_IDS[4],
    name: "legacy-transformer",
    status: "inactive",
    quota_profile: { provider: "openai", model: "gpt-3.5-turbo", daily_task_budget: 30, safe_token_cap: 20000 },
    capabilities: { languages: ["javascript"], specialties: ["data_structuring"] },
    created_at: "2026-02-15T10:00:00Z",
    updated_at: "2026-03-01T12:00:00Z",
  },
];

// ─── Tasks (10) — various statuses ─────────────────────────────────────────

export const mockTasks: TaskResponse[] = [
  {
    id: TASK_IDS[0],
    status: "open",
    publisher_id: AGENT_IDS[0],
    claimed_by: null,
    reward: 25.0,
    deadline_at: "2026-03-14T08:00:00Z",
    task_spec: { type: "research_extraction", description: "Extract funding data from SEC filing", input_data: { url: "https://example.com/sec/filing-2026" }, output_schema: { type: "object", required: ["company", "amount"], properties: { company: { type: "string" }, amount: { type: "number" } } }, validation_method: "schema+rule", token_estimate: 3000 },
    created_at: "2026-03-13T06:00:00Z",
    updated_at: "2026-03-13T06:00:00Z",
  },
  {
    id: TASK_IDS[1],
    status: "open",
    publisher_id: AGENT_IDS[1],
    claimed_by: null,
    reward: 10.0,
    deadline_at: "2026-03-14T12:00:00Z",
    task_spec: { type: "data_structuring", description: "Normalize CSV to JSON", input_data: { format: "csv", rows: 500 }, output_schema: { type: "array", items: { type: "object" } }, validation_method: "schema", token_estimate: 1500 },
    created_at: "2026-03-13T07:00:00Z",
    updated_at: "2026-03-13T07:00:00Z",
  },
  {
    id: TASK_IDS[2],
    status: "claimed",
    publisher_id: AGENT_IDS[0],
    claimed_by: AGENT_IDS[2],
    reward: 50.0,
    deadline_at: "2026-03-14T18:00:00Z",
    task_spec: { type: "coding", description: "Write unit tests for auth module", input_data: { repo: "mnemox-ai/agent-relay", module: "security/auth.py" }, validation_method: "test", token_estimate: 5000 },
    created_at: "2026-03-12T14:00:00Z",
    updated_at: "2026-03-13T08:00:00Z",
  },
  {
    id: TASK_IDS[3],
    status: "submitted",
    publisher_id: AGENT_IDS[1],
    claimed_by: AGENT_IDS[3],
    reward: 15.0,
    deadline_at: "2026-03-13T20:00:00Z",
    task_spec: { type: "research_extraction", description: "Summarize HN thread on AI agents", input_data: { hn_id: "39876543" }, output_schema: { type: "object", required: ["summary", "key_points"], properties: { summary: { type: "string" }, key_points: { type: "array" } } }, validation_method: "schema+rule", token_estimate: 2000 },
    created_at: "2026-03-12T10:00:00Z",
    updated_at: "2026-03-13T09:00:00Z",
  },
  {
    id: TASK_IDS[4],
    status: "validating",
    publisher_id: AGENT_IDS[2],
    claimed_by: AGENT_IDS[0],
    reward: 30.0,
    deadline_at: "2026-03-14T06:00:00Z",
    task_spec: { type: "data_structuring", description: "Parse API response into structured format", input_data: { endpoint: "/v1/metrics", sample_size: 100 }, output_schema: { type: "object", required: ["metrics"], properties: { metrics: { type: "array" } } }, validation_method: "schema", token_estimate: 2500 },
    created_at: "2026-03-12T16:00:00Z",
    updated_at: "2026-03-13T10:00:00Z",
  },
  {
    id: TASK_IDS[5],
    status: "completed",
    publisher_id: AGENT_IDS[0],
    claimed_by: AGENT_IDS[1],
    reward: 20.0,
    deadline_at: "2026-03-13T12:00:00Z",
    task_spec: { type: "research_extraction", description: "Extract product features from landing page", input_data: { url: "https://example.com/product" }, output_schema: { type: "object", required: ["features"], properties: { features: { type: "array" } } }, validation_method: "schema+rule", token_estimate: 1800 },
    created_at: "2026-03-11T09:00:00Z",
    updated_at: "2026-03-12T11:00:00Z",
  },
  {
    id: TASK_IDS[6],
    status: "completed",
    publisher_id: AGENT_IDS[3],
    claimed_by: AGENT_IDS[2],
    reward: 40.0,
    deadline_at: "2026-03-12T18:00:00Z",
    task_spec: { type: "coding", description: "Implement retry logic for HTTP client", input_data: { language: "python", max_retries: 3 }, validation_method: "test", token_estimate: 4000 },
    created_at: "2026-03-10T12:00:00Z",
    updated_at: "2026-03-11T15:00:00Z",
  },
  {
    id: TASK_IDS[7],
    status: "failed",
    publisher_id: AGENT_IDS[1],
    claimed_by: AGENT_IDS[4],
    reward: 35.0,
    deadline_at: "2026-03-12T10:00:00Z",
    task_spec: { type: "coding", description: "Refactor database connection pooling", input_data: { db: "postgresql", current_pool_size: 5 }, validation_method: "test", token_estimate: 6000 },
    created_at: "2026-03-09T08:00:00Z",
    updated_at: "2026-03-11T08:00:00Z",
  },
  {
    id: TASK_IDS[8],
    status: "expired",
    publisher_id: AGENT_IDS[2],
    claimed_by: AGENT_IDS[3],
    reward: 12.0,
    deadline_at: "2026-03-11T06:00:00Z",
    task_spec: { type: "data_structuring", description: "Convert XML feed to JSON", input_data: { feed_url: "https://example.com/feed.xml" }, output_schema: { type: "array" }, validation_method: "schema", token_estimate: 1200 },
    created_at: "2026-03-08T14:00:00Z",
    updated_at: "2026-03-11T06:00:00Z",
  },
  {
    id: TASK_IDS[9],
    status: "completed",
    publisher_id: AGENT_IDS[3],
    claimed_by: AGENT_IDS[0],
    reward: 18.0,
    deadline_at: "2026-03-13T10:00:00Z",
    task_spec: { type: "research_extraction", description: "Aggregate pricing data from competitor pages", input_data: { urls: ["https://example.com/a", "https://example.com/b"] }, output_schema: { type: "object", required: ["prices"], properties: { prices: { type: "array" } } }, validation_method: "schema+rule", token_estimate: 3500 },
    created_at: "2026-03-11T07:00:00Z",
    updated_at: "2026-03-12T09:00:00Z",
  },
];

// ─── Submissions (15) ──────────────────────────────────────────────────────

export const mockSubmissions: SubmissionResponse[] = [
  // Task 3 (submitted) — 1 submission
  { id: SUBMISSION_IDS[0], task_id: TASK_IDS[3], agent_id: AGENT_IDS[3], output_data: { summary: "AI agents discussion highlights delegation, safety, multi-agent coordination", key_points: ["Safety-first design", "Task decomposition", "Verification loops"] }, submitted_at: "2026-03-13T09:00:00Z", created_at: "2026-03-13T09:00:00Z", updated_at: "2026-03-13T09:00:00Z" },
  // Task 4 (validating) — 1 submission
  { id: SUBMISSION_IDS[1], task_id: TASK_IDS[4], agent_id: AGENT_IDS[0], output_data: { metrics: [{ name: "latency_p99", value: 120 }, { name: "throughput", value: 5000 }] }, submitted_at: "2026-03-13T09:30:00Z", created_at: "2026-03-13T09:30:00Z", updated_at: "2026-03-13T09:30:00Z" },
  // Task 5 (completed) — 2 submissions (one from each agent that tried)
  { id: SUBMISSION_IDS[2], task_id: TASK_IDS[5], agent_id: AGENT_IDS[1], output_data: { features: ["SSO login", "Role-based access", "Audit logs", "API keys"] }, submitted_at: "2026-03-12T10:00:00Z", created_at: "2026-03-12T10:00:00Z", updated_at: "2026-03-12T10:00:00Z" },
  // Task 6 (completed) — 1 submission
  { id: SUBMISSION_IDS[3], task_id: TASK_IDS[6], agent_id: AGENT_IDS[2], output_data: { code: "def retry(fn, max_retries=3): ...", tests_passed: 12, coverage: 0.94 }, submitted_at: "2026-03-11T14:00:00Z", created_at: "2026-03-11T14:00:00Z", updated_at: "2026-03-11T14:00:00Z" },
  // Task 7 (failed) — 1 submission
  { id: SUBMISSION_IDS[4], task_id: TASK_IDS[7], agent_id: AGENT_IDS[4], output_data: { code: "# incomplete refactor", tests_passed: 3, tests_failed: 7 }, submitted_at: "2026-03-10T16:00:00Z", created_at: "2026-03-10T16:00:00Z", updated_at: "2026-03-10T16:00:00Z" },
  // Task 8 (expired) — 1 submission (too late)
  { id: SUBMISSION_IDS[5], task_id: TASK_IDS[8], agent_id: AGENT_IDS[3], output_data: { converted: [{ item: "partial" }] }, submitted_at: "2026-03-11T07:00:00Z", created_at: "2026-03-11T07:00:00Z", updated_at: "2026-03-11T07:00:00Z" },
  // Task 9 (completed) — 1 submission
  { id: SUBMISSION_IDS[6], task_id: TASK_IDS[9], agent_id: AGENT_IDS[0], output_data: { prices: [{ competitor: "A", price: 29.99 }, { competitor: "B", price: 34.99 }] }, submitted_at: "2026-03-12T08:00:00Z", created_at: "2026-03-12T08:00:00Z", updated_at: "2026-03-12T08:00:00Z" },
  // Extra submissions from various agents on older tasks
  { id: SUBMISSION_IDS[7], task_id: TASK_IDS[5], agent_id: AGENT_IDS[3], output_data: { features: ["OAuth2", "RBAC", "Webhooks"] }, submitted_at: "2026-03-12T09:30:00Z", created_at: "2026-03-12T09:30:00Z", updated_at: "2026-03-12T09:30:00Z" },
  { id: SUBMISSION_IDS[8], task_id: TASK_IDS[6], agent_id: AGENT_IDS[0], output_data: { code: "async def retry_async(...)", tests_passed: 10, coverage: 0.87 }, submitted_at: "2026-03-11T13:00:00Z", created_at: "2026-03-11T13:00:00Z", updated_at: "2026-03-11T13:00:00Z" },
  { id: SUBMISSION_IDS[9], task_id: TASK_IDS[9], agent_id: AGENT_IDS[1], output_data: { prices: [{ competitor: "A", price: 30.0 }, { competitor: "C", price: 27.5 }] }, submitted_at: "2026-03-12T07:30:00Z", created_at: "2026-03-12T07:30:00Z", updated_at: "2026-03-12T07:30:00Z" },
  { id: SUBMISSION_IDS[10], task_id: TASK_IDS[7], agent_id: AGENT_IDS[2], output_data: { code: "class ConnectionPool: ...", tests_passed: 8, tests_failed: 2 }, submitted_at: "2026-03-10T18:00:00Z", created_at: "2026-03-10T18:00:00Z", updated_at: "2026-03-10T18:00:00Z" },
  { id: SUBMISSION_IDS[11], task_id: TASK_IDS[0], agent_id: AGENT_IDS[1], output_data: { company: "Acme Corp", amount: 15000000 }, submitted_at: "2026-03-13T07:30:00Z", created_at: "2026-03-13T07:30:00Z", updated_at: "2026-03-13T07:30:00Z" },
  { id: SUBMISSION_IDS[12], task_id: TASK_IDS[1], agent_id: AGENT_IDS[3], output_data: { rows: [{ id: 1, value: "test" }], total: 500 }, submitted_at: "2026-03-13T08:00:00Z", created_at: "2026-03-13T08:00:00Z", updated_at: "2026-03-13T08:00:00Z" },
  { id: SUBMISSION_IDS[13], task_id: TASK_IDS[2], agent_id: AGENT_IDS[2], output_data: { code: "def test_auth_login(): ...", tests_passed: 5, coverage: 0.82 }, submitted_at: "2026-03-13T10:00:00Z", created_at: "2026-03-13T10:00:00Z", updated_at: "2026-03-13T10:00:00Z" },
  { id: SUBMISSION_IDS[14], task_id: TASK_IDS[4], agent_id: AGENT_IDS[3], output_data: { metrics: [{ name: "error_rate", value: 0.02 }] }, submitted_at: "2026-03-13T09:45:00Z", created_at: "2026-03-13T09:45:00Z", updated_at: "2026-03-13T09:45:00Z" },
];

// ─── Validation Runs ───────────────────────────────────────────────────────

export const mockValidationRuns: ValidationRunResponse[] = [
  // Task 4 (validating) — schema pass, rule pending
  { id: "d4000000-0000-4000-8000-000000000001", submission_id: SUBMISSION_IDS[1], validator_type: "schema", passed: true, score: 1.0, details: { schema_errors: [] }, validated_at: "2026-03-13T10:00:00Z" },
  { id: "d4000000-0000-4000-8000-000000000002", submission_id: SUBMISSION_IDS[1], validator_type: "rule", passed: true, score: 0.88, details: { rules_checked: 5, rules_passed: 4, warnings: ["Missing optional field: description"] }, validated_at: "2026-03-13T10:01:00Z" },
  // Task 5 (completed) — both pass
  { id: "d4000000-0000-4000-8000-000000000003", submission_id: SUBMISSION_IDS[2], validator_type: "schema", passed: true, score: 1.0, details: { schema_errors: [] }, validated_at: "2026-03-12T10:30:00Z" },
  { id: "d4000000-0000-4000-8000-000000000004", submission_id: SUBMISSION_IDS[2], validator_type: "rule", passed: true, score: 0.95, details: { rules_checked: 3, rules_passed: 3 }, validated_at: "2026-03-12T10:31:00Z" },
  // Task 6 (completed) — test pass
  { id: "d4000000-0000-4000-8000-000000000005", submission_id: SUBMISSION_IDS[3], validator_type: "test", passed: true, score: 0.94, details: { tests_total: 12, tests_passed: 12, coverage: 0.94 }, validated_at: "2026-03-11T14:30:00Z" },
  // Task 7 (failed) — test fail
  { id: "d4000000-0000-4000-8000-000000000006", submission_id: SUBMISSION_IDS[4], validator_type: "test", passed: false, score: 0.30, details: { tests_total: 10, tests_passed: 3, failures: ["test_pool_resize", "test_conn_timeout", "test_max_overflow"] }, validated_at: "2026-03-10T17:00:00Z" },
  // Task 9 (completed)
  { id: "d4000000-0000-4000-8000-000000000007", submission_id: SUBMISSION_IDS[6], validator_type: "schema", passed: true, score: 1.0, details: { schema_errors: [] }, validated_at: "2026-03-12T08:30:00Z" },
  { id: "d4000000-0000-4000-8000-000000000008", submission_id: SUBMISSION_IDS[6], validator_type: "rule", passed: true, score: 0.90, details: { rules_checked: 4, rules_passed: 4 }, validated_at: "2026-03-12T08:31:00Z" },
];

// ─── Ledger Entries ────────────────────────────────────────────────────────

export const mockLedgerEntries: LedgerEntry[] = [
  // Task 5 completed → reward to agent 1
  { id: "e5000000-0000-4000-8000-000000000001", agent_id: AGENT_IDS[1], task_id: TASK_IDS[5], amount: 20.0, entry_type: "reward", created_at: "2026-03-12T11:00:00Z", updated_at: "2026-03-12T11:00:00Z" },
  // Task 6 completed → reward to agent 2
  { id: "e5000000-0000-4000-8000-000000000002", agent_id: AGENT_IDS[2], task_id: TASK_IDS[6], amount: 40.0, entry_type: "reward", created_at: "2026-03-11T15:00:00Z", updated_at: "2026-03-11T15:00:00Z" },
  // Task 7 failed → penalty to agent 4
  { id: "e5000000-0000-4000-8000-000000000003", agent_id: AGENT_IDS[4], task_id: TASK_IDS[7], amount: -5.0, entry_type: "penalty", created_at: "2026-03-11T08:00:00Z", updated_at: "2026-03-11T08:00:00Z" },
  // Task 9 completed → reward to agent 0
  { id: "e5000000-0000-4000-8000-000000000004", agent_id: AGENT_IDS[0], task_id: TASK_IDS[9], amount: 18.0, entry_type: "reward", created_at: "2026-03-12T09:00:00Z", updated_at: "2026-03-12T09:00:00Z" },
  // Bonus reward for high quality
  { id: "e5000000-0000-4000-8000-000000000005", agent_id: AGENT_IDS[2], task_id: TASK_IDS[6], amount: 5.0, entry_type: "reward", created_at: "2026-03-11T15:05:00Z", updated_at: "2026-03-11T15:05:00Z" },
];

// ─── Reputation Snapshots ──────────────────────────────────────────────────

export const mockReputationSnapshots: ReputationResponse[] = [
  {
    id: "f6000000-0000-4000-8000-000000000001",
    agent_id: AGENT_IDS[0],
    metrics: { completion_rate: 0.92, pass_rate: 0.88, avg_latency_seconds: 120.5, token_efficiency: 0.75, rework_rate: 0.05, quality_score: 0.85 },
    snapshot_at: "2026-03-13T00:00:00Z",
    created_at: "2026-03-13T00:00:00Z",
    updated_at: "2026-03-13T00:00:00Z",
  },
  {
    id: "f6000000-0000-4000-8000-000000000002",
    agent_id: AGENT_IDS[1],
    metrics: { completion_rate: 0.85, pass_rate: 0.90, avg_latency_seconds: 95.0, token_efficiency: 0.82, rework_rate: 0.08, quality_score: 0.88 },
    snapshot_at: "2026-03-13T00:00:00Z",
    created_at: "2026-03-13T00:00:00Z",
    updated_at: "2026-03-13T00:00:00Z",
  },
  {
    id: "f6000000-0000-4000-8000-000000000003",
    agent_id: AGENT_IDS[2],
    metrics: { completion_rate: 0.95, pass_rate: 0.93, avg_latency_seconds: 180.0, token_efficiency: 0.70, rework_rate: 0.02, quality_score: 0.91 },
    snapshot_at: "2026-03-13T00:00:00Z",
    created_at: "2026-03-13T00:00:00Z",
    updated_at: "2026-03-13T00:00:00Z",
  },
  {
    id: "f6000000-0000-4000-8000-000000000004",
    agent_id: AGENT_IDS[3],
    metrics: { completion_rate: 0.78, pass_rate: 0.75, avg_latency_seconds: 200.0, token_efficiency: 0.65, rework_rate: 0.12, quality_score: 0.72 },
    snapshot_at: "2026-03-13T00:00:00Z",
    created_at: "2026-03-13T00:00:00Z",
    updated_at: "2026-03-13T00:00:00Z",
  },
  {
    id: "f6000000-0000-4000-8000-000000000005",
    agent_id: AGENT_IDS[4],
    metrics: { completion_rate: 0.40, pass_rate: 0.30, avg_latency_seconds: 350.0, token_efficiency: 0.45, rework_rate: 0.25, quality_score: 0.35 },
    snapshot_at: "2026-03-13T00:00:00Z",
    created_at: "2026-03-13T00:00:00Z",
    updated_at: "2026-03-13T00:00:00Z",
  },
];

// ─── Lookup helpers ────────────────────────────────────────────────────────

export function getMockAgent(id: string): AgentResponse | undefined {
  return mockAgents.find((a) => a.id === id);
}

export function getMockTask(id: string): TaskResponse | undefined {
  return mockTasks.find((t) => t.id === id);
}

export function getMockSubmissionsByTask(taskId: string): SubmissionResponse[] {
  return mockSubmissions.filter((s) => s.task_id === taskId);
}

export function getMockValidationsBySubmission(submissionId: string): ValidationRunResponse[] {
  return mockValidationRuns.filter((v) => v.submission_id === submissionId);
}

export function getMockLedgerByAgent(agentId: string): LedgerEntry[] {
  return mockLedgerEntries.filter((l) => l.agent_id === agentId);
}

export function getMockReputationByAgent(agentId: string): ReputationResponse | undefined {
  return mockReputationSnapshots.find((r) => r.agent_id === agentId);
}
