"""20 task templates: 5 types × 4 templates each.

Each template is a dict with:
  - id: unique template identifier
  - task_type: one of the 5 TaskType values
  - difficulty: easy / medium / hard
  - reward: float
  - deadline_seconds: int
  - generate_input: callable() -> input_data dict (randomized)
  - output_schema: JSON Schema for validation
  - validation_method: "schema" or "rule"
  - token_estimate: int
"""

from __future__ import annotations

import random

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pick(*choices: str) -> str:
    return random.choice(choices)


def _rand_int(lo: int, hi: int) -> int:
    return random.randint(lo, hi)


def _rand_float(lo: float, hi: float, decimals: int = 2) -> float:
    return round(random.uniform(lo, hi), decimals)


def _rand_name() -> str:
    first = _pick("Alice", "Bob", "Carlos", "Diana", "Ethan", "Fiona", "Guo", "Hana", "Ivan", "Jia")
    last = _pick("Smith", "Chen", "Garcia", "Müller", "Tanaka", "Kim", "Patel", "Santos", "Lee", "Wang")
    return f"{first} {last}"


# ============================================================================
# 1. DATA_STRUCTURING (4 templates)
# ============================================================================

def _ds_earnings_input() -> dict:
    company = _pick("Apple Inc.", "Microsoft Corp.", "Alphabet Inc.", "Amazon.com Inc.", "Meta Platforms")
    quarter = _pick("Q1", "Q2", "Q3", "Q4")
    year = _rand_int(2024, 2026)
    revenue = _rand_float(20.0, 120.0, 1)
    growth = _rand_int(-5, 25)
    net_income = _rand_float(5.0, 35.0, 1)
    segment = _pick("Cloud", "Advertising", "Devices", "Services", "Subscriptions")
    seg_rev = _rand_float(5.0, 50.0, 1)
    return {
        "raw_text": (
            f"{company} reported {quarter} {year} revenue of ${revenue}B, "
            f"{'up' if growth >= 0 else 'down'} {abs(growth)}% YoY. "
            f"Net income was ${net_income}B. {segment} revenue was ${seg_rev}B."
        ),
    }

DS_EARNINGS = {
    "id": "ds_earnings",
    "task_type": "data_structuring",
    "difficulty": "easy",
    "reward": 0.05,
    "deadline_seconds": 3600,
    "token_estimate": 500,
    "validation_method": "schema",
    "generate_input": _ds_earnings_input,
    "output_schema": {
        "type": "object",
        "required": ["company", "quarter", "revenue_usd", "net_income_usd"],
        "properties": {
            "company": {"type": "string"},
            "quarter": {"type": "string"},
            "revenue_usd": {"type": "number"},
            "net_income_usd": {"type": "number"},
            "segments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "revenue_usd": {"type": "number"},
                    },
                },
            },
        },
    },
}


def _ds_product_input() -> dict:
    product = _pick("Wireless Mouse X1", "Mechanical Keyboard Pro", "USB-C Hub 7-in-1",
                     "Noise-Cancelling Headphones Z3", "Portable SSD 2TB")
    price = _rand_float(19.99, 199.99)
    rating = _rand_float(3.5, 5.0, 1)
    reviews = _rand_int(50, 5000)
    weight = _rand_int(50, 500)
    return {
        "raw_text": (
            f"Product: {product}\nPrice: ${price}\n"
            f"Rating: {rating}/5 ({reviews:,} reviews)\n"
            f"Weight: {weight}g\nWarranty: {_rand_int(1, 3)} year(s)"
        ),
    }

DS_PRODUCT = {
    "id": "ds_product",
    "task_type": "data_structuring",
    "difficulty": "medium",
    "reward": 0.08,
    "deadline_seconds": 3600,
    "token_estimate": 600,
    "validation_method": "schema",
    "generate_input": _ds_product_input,
    "output_schema": {
        "type": "object",
        "required": ["product_name", "price_usd", "rating", "specs"],
        "properties": {
            "product_name": {"type": "string"},
            "price_usd": {"type": "number"},
            "rating": {"type": "number"},
            "review_count": {"type": "integer"},
            "specs": {"type": "object"},
        },
    },
}


def _ds_clinical_input() -> dict:
    trial_id = f"NCT{_rand_int(10000000, 99999999)}"
    phase = _pick("2", "3")
    drug = _pick("Examplivir", "Novacure", "Betazol", "Cardiflex", "Neuromin")
    dose = _pick("100mg", "200mg", "500mg")
    n = _rand_int(200, 2000)
    reduction = _rand_float(1.5, 4.0, 1)
    sae = _rand_float(1.0, 5.0, 1)
    return {
        "raw_text": (
            f"Clinical Trial {trial_id}: Phase {phase}, randomized, double-blind. "
            f"Drug: {drug} {dose} vs placebo. N={n} ({n // 2}/group). "
            f"Primary endpoint: viral load reduction at week 12. "
            f"Results: -{reduction} log10 vs -0.3 log10 (p<0.001). "
            f"SAEs: {sae}% vs {sae - 0.3:.1f}%. Completion rate: {_rand_int(80, 95)}%."
        ),
    }

DS_CLINICAL = {
    "id": "ds_clinical",
    "task_type": "data_structuring",
    "difficulty": "hard",
    "reward": 0.15,
    "deadline_seconds": 3600,
    "token_estimate": 1000,
    "validation_method": "schema",
    "generate_input": _ds_clinical_input,
    "output_schema": {
        "type": "object",
        "required": ["trial_id", "phase", "drug", "sample_size", "primary_endpoint", "results"],
        "properties": {
            "trial_id": {"type": "string"},
            "phase": {"type": "integer"},
            "drug": {"type": "string"},
            "dosage": {"type": "string"},
            "sample_size": {"type": "integer"},
            "primary_endpoint": {"type": "string"},
            "results": {"type": "object"},
            "safety": {"type": "object"},
        },
    },
}


def _ds_resume_input() -> dict:
    name = _rand_name()
    role = _pick("Software Engineer", "Data Scientist", "Product Manager", "DevOps Engineer", "ML Engineer")
    company = _pick("Google", "Amazon", "Stripe", "Shopify", "Datadog", "Cloudflare")
    years = _rand_int(2, 12)
    lang = _pick("Python, Go", "TypeScript, Rust", "Java, Kotlin", "Python, C++")
    degree = _pick("B.S. Computer Science", "M.S. Data Science", "B.Eng. Software Engineering", "Ph.D. AI")
    uni = _pick("MIT", "Stanford", "CMU", "UC Berkeley", "ETH Zurich", "NTU")
    return {
        "raw_text": (
            f"{name}\n{role} — {years} years experience\n"
            f"Current: {role} at {company} ({_rand_int(1, years)} yrs)\n"
            f"Skills: {lang}, AWS, Docker, Kubernetes\n"
            f"Education: {degree}, {uni} ({_rand_int(2012, 2023)})"
        ),
    }

DS_RESUME = {
    "id": "ds_resume",
    "task_type": "data_structuring",
    "difficulty": "medium",
    "reward": 0.08,
    "deadline_seconds": 3600,
    "token_estimate": 600,
    "validation_method": "schema",
    "generate_input": _ds_resume_input,
    "output_schema": {
        "type": "object",
        "required": ["name", "current_role", "years_experience", "skills"],
        "properties": {
            "name": {"type": "string"},
            "current_role": {"type": "string"},
            "current_company": {"type": "string"},
            "years_experience": {"type": "integer"},
            "skills": {"type": "array", "items": {"type": "string"}},
            "education": {"type": "object"},
        },
    },
}


# ============================================================================
# 2. RESEARCH_EXTRACTION (4 templates)
# ============================================================================

def _re_factual_input() -> dict:
    queries = [
        ("What is the current population of Tokyo metropolitan area?", "Based on publicly available demographic data."),
        ("What is the GDP of Germany?", "Use the latest available annual figure."),
        ("What is the altitude of Mount Everest?", "Use the most recent official survey."),
        ("How many satellites are currently in Earth orbit?", "Include both active and defunct."),
        ("What is the speed of light in a vacuum?", "Exact value per SI definition."),
    ]
    q, c = random.choice(queries)
    return {"query": q, "context": c}

RE_FACTUAL = {
    "id": "re_factual",
    "task_type": "research_extraction",
    "difficulty": "easy",
    "reward": 0.03,
    "deadline_seconds": 3600,
    "token_estimate": 300,
    "validation_method": "rule",
    "generate_input": _re_factual_input,
    "output_schema": {
        "type": "object",
        "required": ["answer", "source_description"],
        "properties": {
            "answer": {"type": "string"},
            "source_description": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    },
}


def _re_comparison_input() -> dict:
    comparisons = [
        ("Compare the top 3 Python async web frameworks by GitHub stars and key features.",
         "Focus on FastAPI, Starlette, and Sanic."),
        ("Compare Redis, Memcached, and DragonflyDB for caching use cases.",
         "Focus on performance, data structures, and clustering."),
        ("Compare Next.js, Nuxt, and SvelteKit for full-stack web apps.",
         "Focus on SSR, DX, and ecosystem maturity."),
        ("Compare PostgreSQL, CockroachDB, and TiDB for distributed SQL.",
         "Focus on scaling, compatibility, and operational complexity."),
    ]
    q, c = random.choice(comparisons)
    return {"query": q, "context": c}

RE_COMPARISON = {
    "id": "re_comparison",
    "task_type": "research_extraction",
    "difficulty": "medium",
    "reward": 0.10,
    "deadline_seconds": 3600,
    "token_estimate": 800,
    "validation_method": "schema",
    "generate_input": _re_comparison_input,
    "output_schema": {
        "type": "object",
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "features"],
                    "properties": {
                        "name": {"type": "string"},
                        "github_stars": {"type": "integer"},
                        "features": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
    },
}


def _re_market_input() -> dict:
    sectors = [
        ("AI infrastructure", "cloud GPU providers, model hosting, inference APIs"),
        ("developer tools", "CI/CD, code review, AI-assisted coding"),
        ("edge computing", "CDN, serverless edge, IoT platforms"),
        ("observability", "APM, logging, distributed tracing"),
    ]
    sector, focus = random.choice(sectors)
    return {
        "query": f"Summarize the current competitive landscape in {sector}.",
        "context": f"Cover key players, recent funding, and trends. Focus on: {focus}.",
    }

RE_MARKET = {
    "id": "re_market",
    "task_type": "research_extraction",
    "difficulty": "hard",
    "reward": 0.18,
    "deadline_seconds": 3600,
    "token_estimate": 1200,
    "validation_method": "schema",
    "generate_input": _re_market_input,
    "output_schema": {
        "type": "object",
        "required": ["summary", "players", "trends"],
        "properties": {
            "summary": {"type": "string"},
            "players": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "description"],
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                    },
                },
            },
            "trends": {"type": "array", "items": {"type": "string"}},
        },
    },
}


def _re_api_docs_input() -> dict:
    apis = [
        ("Stripe Payment Intents API", "List required parameters, authentication method, and error codes."),
        ("GitHub REST API for Pull Requests", "Cover create, list, merge endpoints with required headers."),
        ("OpenAI Chat Completions API", "Document parameters, streaming mode, and token counting."),
        ("AWS S3 PutObject API", "List required headers, authentication (SigV4), and common errors."),
    ]
    api, instruction = random.choice(apis)
    return {"query": f"Document the {api}.", "context": instruction}

RE_API_DOCS = {
    "id": "re_api_docs",
    "task_type": "research_extraction",
    "difficulty": "medium",
    "reward": 0.10,
    "deadline_seconds": 3600,
    "token_estimate": 900,
    "validation_method": "schema",
    "generate_input": _re_api_docs_input,
    "output_schema": {
        "type": "object",
        "required": ["api_name", "endpoints"],
        "properties": {
            "api_name": {"type": "string"},
            "endpoints": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["method", "path", "description"],
                    "properties": {
                        "method": {"type": "string"},
                        "path": {"type": "string"},
                        "description": {"type": "string"},
                        "parameters": {"type": "array", "items": {"type": "object"}},
                    },
                },
            },
        },
    },
}


# ============================================================================
# 3. CODING (4 templates)
# ============================================================================

def _code_utility_input() -> dict:
    tasks = [
        {
            "task": "Write a function `flatten(nested_list)` that flattens an arbitrarily nested list.",
            "examples": [
                {"input": [[1, 2], [3, [4, 5]]], "output": [1, 2, 3, 4, 5]},
                {"input": [1, [2, [3, [4]]]], "output": [1, 2, 3, 4]},
            ],
        },
        {
            "task": "Write a function `chunk(lst, n)` that splits a list into chunks of size n.",
            "examples": [
                {"input": [[1, 2, 3, 4, 5], 2], "output": [[1, 2], [3, 4], [5]]},
            ],
        },
        {
            "task": "Write a function `deep_merge(a, b)` that recursively merges two dicts.",
            "examples": [
                {"input": [{"a": 1, "b": {"c": 2}}, {"b": {"d": 3}}], "output": {"a": 1, "b": {"c": 2, "d": 3}}},
            ],
        },
    ]
    chosen = random.choice(tasks)
    return {"language": "python", **chosen}

CODE_UTILITY = {
    "id": "code_utility",
    "task_type": "coding",
    "difficulty": "easy",
    "reward": 0.05,
    "deadline_seconds": 3600,
    "token_estimate": 400,
    "validation_method": "rule",
    "generate_input": _code_utility_input,
    "output_schema": {
        "type": "object",
        "required": ["code"],
        "properties": {
            "code": {"type": "string"},
            "explanation": {"type": "string"},
        },
    },
}


def _code_datastructure_input() -> dict:
    tasks = [
        {
            "task": (
                "Implement a simple LRU cache class with `get(key)` and `put(key, value)` methods. "
                "The cache should have a configurable max size."
            ),
            "constraints": ["O(1) for both get and put", "Use only stdlib"],
        },
        {
            "task": "Implement a MinStack that supports push, pop, top, and getMin in O(1) time.",
            "constraints": ["All operations must be O(1)", "Use only stdlib"],
        },
        {
            "task": "Implement a Trie (prefix tree) with insert, search, and startsWith methods.",
            "constraints": ["Lowercase English letters only", "Use only stdlib"],
        },
    ]
    chosen = random.choice(tasks)
    return {"language": "python", **chosen}

CODE_DATASTRUCTURE = {
    "id": "code_datastructure",
    "task_type": "coding",
    "difficulty": "medium",
    "reward": 0.12,
    "deadline_seconds": 3600,
    "token_estimate": 800,
    "validation_method": "rule",
    "generate_input": _code_datastructure_input,
    "output_schema": {
        "type": "object",
        "required": ["code", "test_code"],
        "properties": {
            "code": {"type": "string"},
            "test_code": {"type": "string"},
            "time_complexity": {"type": "string"},
        },
    },
}


def _code_algorithm_input() -> dict:
    tasks = [
        {
            "task": (
                "Write an async rate limiter using the token bucket algorithm. "
                "Support `async acquire()` that waits and `try_acquire()` that returns immediately."
            ),
            "constraints": ["asyncio only, no external deps", "Configurable rate and burst size"],
        },
        {
            "task": "Implement a concurrent-safe bounded thread pool with future-based result retrieval.",
            "constraints": ["threading only, no concurrent.futures", "Support graceful shutdown"],
        },
        {
            "task": (
                "Write a streaming JSON parser that processes large JSON arrays element by element "
                "without loading the full array into memory."
            ),
            "constraints": ["No external deps", "Must handle nested objects within array elements"],
        },
    ]
    chosen = random.choice(tasks)
    return {"language": "python", **chosen}

CODE_ALGORITHM = {
    "id": "code_algorithm",
    "task_type": "coding",
    "difficulty": "hard",
    "reward": 0.25,
    "deadline_seconds": 3600,
    "token_estimate": 1500,
    "validation_method": "rule",
    "generate_input": _code_algorithm_input,
    "output_schema": {
        "type": "object",
        "required": ["code", "test_code"],
        "properties": {
            "code": {"type": "string"},
            "test_code": {"type": "string"},
            "explanation": {"type": "string"},
        },
    },
}


def _code_api_endpoint_input() -> dict:
    tasks = [
        {
            "task": (
                "Write a FastAPI endpoint POST /shorten that accepts a URL and returns a shortened slug. "
                "Store mappings in a dict. Add GET /{slug} to redirect."
            ),
            "constraints": ["No database required (in-memory dict)", "Validate URL format"],
        },
        {
            "task": (
                "Write a FastAPI endpoint POST /tasks that creates a background task, "
                "and GET /tasks/{id}/status that returns progress."
            ),
            "constraints": ["Use asyncio.create_task", "Return task ID immediately"],
        },
    ]
    chosen = random.choice(tasks)
    return {"language": "python", **chosen}

CODE_API_ENDPOINT = {
    "id": "code_api_endpoint",
    "task_type": "coding",
    "difficulty": "medium",
    "reward": 0.12,
    "deadline_seconds": 3600,
    "token_estimate": 900,
    "validation_method": "rule",
    "generate_input": _code_api_endpoint_input,
    "output_schema": {
        "type": "object",
        "required": ["code", "test_code"],
        "properties": {
            "code": {"type": "string"},
            "test_code": {"type": "string"},
            "explanation": {"type": "string"},
        },
    },
}


# ============================================================================
# 4. CONTENT_GENERATION (4 templates)
# ============================================================================

def _cg_summarize_input() -> dict:
    articles = [
        (
            "The European Union announced a new AI Act that will regulate artificial intelligence systems "
            "based on risk levels. High-risk AI (medical devices, hiring tools) must pass conformity assessments. "
            "General-purpose AI models must disclose training data summaries. Penalties up to 7% of global revenue. "
            "The act takes full effect in 2026, with some provisions starting in 2025."
        ),
        (
            "SpaceX successfully launched its Starship rocket on its fifth test flight, achieving full stage "
            "separation and catching the Super Heavy booster with the mechazilla tower arms. The upper stage "
            "completed a controlled re-entry over the Indian Ocean. This marks a major milestone toward "
            "full reusability. NASA's Artemis program depends on a Starship variant for lunar landings."
        ),
        (
            "Global semiconductor revenue hit $627B in 2024, up 19% YoY driven by AI chip demand. "
            "NVIDIA captured 80%+ of data center GPU market. TSMC's 3nm node reached full utilization. "
            "US CHIPS Act funded $52B in domestic manufacturing. Intel's foundry business lost $7B. "
            "China's SMIC continued expanding on mature nodes (28nm+) despite export restrictions."
        ),
    ]
    return {"text": random.choice(articles), "max_sentences": _rand_int(2, 4)}

CG_SUMMARIZE = {
    "id": "cg_summarize",
    "task_type": "content_generation",
    "difficulty": "easy",
    "reward": 0.04,
    "deadline_seconds": 3600,
    "token_estimate": 400,
    "validation_method": "schema",
    "generate_input": _cg_summarize_input,
    "output_schema": {
        "type": "object",
        "required": ["summary"],
        "properties": {
            "summary": {"type": "string"},
            "key_points": {"type": "array", "items": {"type": "string"}},
        },
    },
}


def _cg_technical_doc_input() -> dict:
    topics = [
        {"function_name": "retry_with_backoff", "language": "Python",
         "description": "Decorator that retries a function with exponential backoff on specified exceptions."},
        {"function_name": "RateLimiter", "language": "TypeScript",
         "description": "Class implementing sliding window rate limiting with Redis backend."},
        {"function_name": "parse_cron", "language": "Go",
         "description": "Parse a cron expression string and return the next N scheduled times."},
    ]
    return random.choice(topics)

CG_TECHNICAL_DOC = {
    "id": "cg_technical_doc",
    "task_type": "content_generation",
    "difficulty": "medium",
    "reward": 0.08,
    "deadline_seconds": 3600,
    "token_estimate": 700,
    "validation_method": "schema",
    "generate_input": _cg_technical_doc_input,
    "output_schema": {
        "type": "object",
        "required": ["docstring", "parameters", "returns"],
        "properties": {
            "docstring": {"type": "string"},
            "parameters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "type", "description"],
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "description": {"type": "string"},
                    },
                },
            },
            "returns": {"type": "string"},
            "examples": {"type": "array", "items": {"type": "string"}},
        },
    },
}


def _cg_translation_input() -> dict:
    pairs = [
        ("en", "zh", "The quarterly earnings exceeded analyst expectations by 15%, "
         "driven primarily by strong growth in the cloud services division."),
        ("en", "ja", "Our API rate limit is 1000 requests per minute per API key. "
         "Exceeding this limit will result in HTTP 429 responses."),
        ("en", "es", "The new privacy policy requires explicit user consent for data collection. "
         "Users can withdraw consent at any time through their account settings."),
        ("zh", "en", "本季度營收超出分析師預期 15%，主要受雲端服務部門強勁增長推動。"),
    ]
    src, tgt, text = random.choice(pairs)
    return {"source_language": src, "target_language": tgt, "text": text}

CG_TRANSLATION = {
    "id": "cg_translation",
    "task_type": "content_generation",
    "difficulty": "easy",
    "reward": 0.04,
    "deadline_seconds": 3600,
    "token_estimate": 400,
    "validation_method": "schema",
    "generate_input": _cg_translation_input,
    "output_schema": {
        "type": "object",
        "required": ["translated_text", "source_language", "target_language"],
        "properties": {
            "translated_text": {"type": "string"},
            "source_language": {"type": "string"},
            "target_language": {"type": "string"},
        },
    },
}


def _cg_report_input() -> dict:
    scenarios = [
        {
            "report_type": "incident_postmortem",
            "data": {
                "service": _pick("payment-api", "auth-service", "data-pipeline", "search-index"),
                "duration_minutes": _rand_int(15, 180),
                "affected_users": _rand_int(500, 50000),
                "root_cause": _pick("database connection pool exhaustion", "certificate expiry",
                                    "memory leak in cache layer", "misconfigured load balancer"),
            },
        },
        {
            "report_type": "weekly_metrics",
            "data": {
                "project": _pick("mobile-app", "web-dashboard", "api-gateway", "ml-pipeline"),
                "new_users": _rand_int(100, 5000),
                "active_users": _rand_int(1000, 50000),
                "error_rate_pct": _rand_float(0.01, 2.0),
                "p99_latency_ms": _rand_int(50, 500),
            },
        },
    ]
    return random.choice(scenarios)

CG_REPORT = {
    "id": "cg_report",
    "task_type": "content_generation",
    "difficulty": "hard",
    "reward": 0.15,
    "deadline_seconds": 3600,
    "token_estimate": 1200,
    "validation_method": "schema",
    "generate_input": _cg_report_input,
    "output_schema": {
        "type": "object",
        "required": ["title", "body", "sections"],
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["heading", "content"],
                    "properties": {
                        "heading": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
            },
        },
    },
}


# ============================================================================
# 5. CLASSIFICATION (4 templates)
# ============================================================================

def _cl_sentiment_input() -> dict:
    texts = [
        "Absolutely love this product! Best purchase I've made all year.",
        "The service was okay, nothing special. Took a bit longer than expected.",
        "Terrible experience. The item broke after 2 days and support ghosted me.",
        "It does what it says. Not amazing but not bad either. Fair price.",
        "Exceeded all my expectations. Will definitely buy again!",
        "Complete waste of money. Do not recommend to anyone.",
        "Pretty good overall, though the packaging could be better.",
        "I've had mixed results. Sometimes it works great, sometimes not.",
    ]
    return {"text": random.choice(texts), "labels": ["positive", "neutral", "negative"]}

CL_SENTIMENT = {
    "id": "cl_sentiment",
    "task_type": "classification",
    "difficulty": "easy",
    "reward": 0.03,
    "deadline_seconds": 3600,
    "token_estimate": 200,
    "validation_method": "rule",
    "generate_input": _cl_sentiment_input,
    "output_schema": {
        "type": "object",
        "required": ["label", "confidence"],
        "properties": {
            "label": {"type": "string", "enum": ["positive", "neutral", "negative"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
    },
}


def _cl_topic_input() -> dict:
    texts = [
        ("The Federal Reserve held interest rates steady at 5.25-5.50% amid persistent inflation concerns.",
         ["finance", "politics", "technology", "health", "sports", "science"]),
        ("Researchers at CERN detected a new particle consistent with predictions from the Standard Model.",
         ["science", "technology", "health", "education", "politics", "finance"]),
        ("The new iPhone 17 features a titanium frame, A19 chip, and improved camera stabilization.",
         ["technology", "business", "science", "entertainment", "finance", "sports"]),
        ("Manchester City secured the Premier League title with a 3-1 victory over Arsenal.",
         ["sports", "entertainment", "business", "politics", "technology", "health"]),
    ]
    text, labels = random.choice(texts)
    return {"text": text, "labels": labels}

CL_TOPIC = {
    "id": "cl_topic",
    "task_type": "classification",
    "difficulty": "medium",
    "reward": 0.05,
    "deadline_seconds": 3600,
    "token_estimate": 300,
    "validation_method": "rule",
    "generate_input": _cl_topic_input,
    "output_schema": {
        "type": "object",
        "required": ["label", "confidence"],
        "properties": {
            "label": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reasoning": {"type": "string"},
        },
    },
}


def _cl_intent_input() -> dict:
    utterances = [
        ("I want to cancel my subscription", ["cancel", "refund", "upgrade", "billing_inquiry", "support"]),
        ("How do I reset my password?", ["password_reset", "account_access", "support", "billing_inquiry", "cancel"]),
        ("Can I get a refund for my last order?", ["refund", "cancel", "billing_inquiry", "support", "shipping"]),
        ("I'd like to upgrade to the pro plan", ["upgrade", "billing_inquiry", "cancel", "support", "refund"]),
        ("My package hasn't arrived yet", ["shipping", "refund", "support", "cancel", "billing_inquiry"]),
        ("What payment methods do you accept?", ["billing_inquiry", "upgrade", "support", "refund", "cancel"]),
    ]
    text, labels = random.choice(utterances)
    return {"text": text, "labels": labels}

CL_INTENT = {
    "id": "cl_intent",
    "task_type": "classification",
    "difficulty": "medium",
    "reward": 0.05,
    "deadline_seconds": 3600,
    "token_estimate": 300,
    "validation_method": "rule",
    "generate_input": _cl_intent_input,
    "output_schema": {
        "type": "object",
        "required": ["label", "confidence"],
        "properties": {
            "label": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reasoning": {"type": "string"},
        },
    },
}


def _cl_multilabel_input() -> dict:
    issues = [
        (
            "Login fails on mobile when using SSO. Also the page takes 10+ seconds to load on slow connections.",
            ["authentication", "performance", "mobile", "ux", "security", "api"],
        ),
        (
            "The dashboard shows incorrect currency formatting for JPY (should have no decimals) "
            "and the chart tooltip overlaps with the legend on small screens.",
            ["localization", "ux", "data_display", "responsive", "charting", "api"],
        ),
        (
            "API returns 500 when request body exceeds 1MB. No rate limiting on the upload endpoint. "
            "Error message leaks internal stack trace.",
            ["api", "security", "error_handling", "performance", "validation", "logging"],
        ),
    ]
    text, labels = random.choice(issues)
    return {"text": text, "labels": labels, "multi_label": True}

CL_MULTILABEL = {
    "id": "cl_multilabel",
    "task_type": "classification",
    "difficulty": "hard",
    "reward": 0.10,
    "deadline_seconds": 3600,
    "token_estimate": 500,
    "validation_method": "rule",
    "generate_input": _cl_multilabel_input,
    "output_schema": {
        "type": "object",
        "required": ["labels", "confidence_scores"],
        "properties": {
            "labels": {"type": "array", "items": {"type": "string"}},
            "confidence_scores": {
                "type": "array",
                "items": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "reasoning": {"type": "string"},
        },
    },
}


# ============================================================================
# ALL TEMPLATES — indexed by type and as flat list
# ============================================================================

ALL_TEMPLATES: list[dict] = [
    # data_structuring (4)
    DS_EARNINGS,
    DS_PRODUCT,
    DS_CLINICAL,
    DS_RESUME,
    # research_extraction (4)
    RE_FACTUAL,
    RE_COMPARISON,
    RE_MARKET,
    RE_API_DOCS,
    # coding (4)
    CODE_UTILITY,
    CODE_DATASTRUCTURE,
    CODE_ALGORITHM,
    CODE_API_ENDPOINT,
    # content_generation (4)
    CG_SUMMARIZE,
    CG_TECHNICAL_DOC,
    CG_TRANSLATION,
    CG_REPORT,
    # classification (4)
    CL_SENTIMENT,
    CL_TOPIC,
    CL_INTENT,
    CL_MULTILABEL,
]

TEMPLATES_BY_TYPE: dict[str, list[dict]] = {}
for _t in ALL_TEMPLATES:
    TEMPLATES_BY_TYPE.setdefault(_t["task_type"], []).append(_t)


def get_template(template_id: str) -> dict | None:
    """Look up a template by its id."""
    for t in ALL_TEMPLATES:
        if t["id"] == template_id:
            return t
    return None
