"""
Incident Dataset Module.

Contains realistic synthetic SRE incident trajectories inspired by Kubernetes and
microservice failure injections (similar to the OpenSRE dataset).

Features:
1. 10 Historical Seed Incidents (PostgreSQL locks, Redis connection exhaustion,
   Kafka consumer rebalance lag, Nginx 504s, etc.).
2. Temporal distribution enabling Hindsight reflect() to detect deployment correlations.
3. DELIBERATE HOLDOUT: The Act 1 failure mode (Billing Worker OOMKilled) is kept
   strictly out of the seed bank to guarantee a genuine cold-start experience.
"""

from typing import List, Dict, Any
from datetime import datetime, timezone

# ==============================================================================
# The Seed Bank (Pre-loaded into Hindsight Memory)
# ==============================================================================
SEED_INCIDENTS: List[Dict[str, Any]] = [
    {
        "id": "INC-101",
        "title": "Redis Connection Pool Starvation during Flash Sale",
        "service": "payment-service",
        "severity": "CRITICAL",
        "timestamp": "2026-07-15T14:22:00Z",
        "error_signature": "redis.exceptions.ConnectionError: ConnectionPool(max_connections=100) exhausted",
        "stack_trace": (
            "File '/app/services/checkout.py', line 142, in process_payment\n"
            "  client = redis_pool.get_connection()\n"
            "ConnectionError: Timeout acquiring connection from pool after 10000ms"
        ),
        "root_cause": (
            "A burst of checkout requests exhausted the default 100-connection limit. "
            "Idle connections were not being closed after failed payment webhooks."
        ),
        "runbook_steps": [
            "Execute: scripts/sre/flush_idle_conns.sh --service payment-service",
            "Update config: POOL_MAX_CONNECTIONS=500 in ConfigMap",
            "Enable connection recycling: POOL_RECYCLE_SECONDS=300",
        ],
        "anti_patterns": [
            "DO NOT restart the Redis cluster directly; it causes active session drops and payment double-charges."
        ],
        "resolved_by": "Sarah Chen (@sarah)",
        "deployment_context": "Deployed auth-middleware v2.3.0 18 hours prior.",
    },
    {
        "id": "INC-102",
        "title": "PostgreSQL Read-Replica Replication Lag Spike",
        "service": "order-db",
        "severity": "HIGH",
        "timestamp": "2026-07-28T09:10:00Z",
        "error_signature": "psycopg2.OperationalError: replication lag exceeds threshold (942 seconds)",
        "stack_trace": (
            "File '/app/db/replica_monitor.py', line 58, in check_health\n"
            "  raise ReplicationLagAlert(f'Replica lag {lag_seconds}s > 300s threshold')"
        ),
        "root_cause": (
            "A large unindexed batch analytics query ran directly against the read-replica, "
            "locking the replication stream buffer."
        ),
        "runbook_steps": [
            "Identify blocking query PID using: SELECT pid, query FROM pg_stat_activity WHERE state != 'idle';",
            "Terminate query: SELECT pg_terminate_backend(blocking_pid);",
            "Route analytics queries strictly to the dedicated reporting warehouse, not operational read-replicas.",
        ],
        "anti_patterns": [
            "DO NOT rebuild the replica from scratch; replica catching up takes 4 hours and degrades read traffic."
        ],
        "resolved_by": "Marcus Vance (@marcus)",
        "deployment_context": "Analytics cron job deployed 2 days prior.",
    },
    {
        "id": "INC-103",
        "title": "Kafka Consumer Group Rebalance Storm",
        "service": "inventory-worker",
        "severity": "HIGH",
        "timestamp": "2026-08-04T11:45:00Z",
        "error_signature": "CommitFailedException: Commit cannot be completed since the group has already rebalanced",
        "stack_trace": (
            "File '/app/consumers/inventory.py', line 89, in poll_events\n"
            "  consumer.commitSync()\n"
            "CommitFailedException: max.poll.interval.ms exceeded by 42000ms"
        ),
        "root_cause": (
            "Heavy image processing within the Kafka message loop caused heartbeat timeouts, "
            "triggering continuous rebalance cascades across consumer group pods."
        ),
        "runbook_steps": [
            "Decouple heavy processing: Push image jobs to an async background worker pool.",
            "Increase max.poll.interval.ms from 300000ms to 900000ms.",
            "Set max.poll.records to 50 instead of 500.",
        ],
        "anti_patterns": [
            "DO NOT scale the consumer replica count; more consumers will amplify the rebalance storm."
        ],
        "resolved_by": "Priya Sharma (@priya)",
        "deployment_context": "Catalog import feature shipped 6 hours prior.",
    },
    {
        "id": "INC-104",
        "title": "Payment Gateway Timeout under JWT Auth Storm",
        "service": "payment-service",
        "severity": "CRITICAL",
        "timestamp": "2026-08-16T16:05:00Z",
        "error_signature": "requests.exceptions.HTTPError: 504 Gateway Timeout on /v1/charge",
        "stack_trace": (
            "File '/app/controllers/charge.py', line 77, in charge_card\n"
            "  resp = session.post(GATEWAY_URL, timeout=5)\n"
            "requests.exceptions.ReadTimeout: HTTPSConnectionPool(host='gateway', port=443): Read timed out."
        ),
        "root_cause": (
            "New auth token verification logic in auth-middleware was performing synchronous "
            "LDAP checks for every payment request without an in-memory cache."
        ),
        "runbook_steps": [
            "Enable JWT caching in memory: AUTH_TOKEN_CACHE_ENABLED=true",
            "Set LDAP timeout fallback: LDAP_TIMEOUT_MS=500",
            "Execute hot-patch: kubectl rollout restart deployment/auth-middleware",
        ],
        "anti_patterns": [
            "DO NOT disable TLS validation or increase downstream timeout past 8s; causes cascading client retries."
        ],
        "resolved_by": "Sarah Chen (@sarah)",
        "deployment_context": "Deployed auth-middleware v2.3.2 24 hours prior.",
    },
    {
        "id": "INC-105",
        "title": "Nginx Ingress 502 Bad Gateway during Rolling Update",
        "service": "api-gateway",
        "severity": "MEDIUM",
        "timestamp": "2026-08-22T08:30:00Z",
        "error_signature": "111: Connection refused while connecting to upstream",
        "stack_trace": (
            "[error] 142#142: *89012 connect() failed (111: Connection refused) "
            "while connecting to upstream: http://10.244.2.14:8080/api/v1/user"
        ),
        "root_cause": (
            "Backend pods were terminating before deregistering from the Kubernetes Service endpoints, "
            "causing Nginx to route traffic to terminated pods."
        ),
        "runbook_steps": [
            "Add preStop hook in deployment yaml: preStop: exec: command: ['/bin/sleep', '15']",
            "Ensure terminationGracePeriodSeconds is at least 45s.",
        ],
        "anti_patterns": [
            "DO NOT restart Nginx ingress pods; this is a pod lifecycle deregistration timing bug."
        ],
        "resolved_by": "Alex Rivera (@alex)",
        "deployment_context": "Standard CI/CD rolling deployment.",
    },
    {
        "id": "INC-106",
        "title": "Payment Token Leak and Connection Hang",
        "service": "payment-service",
        "severity": "CRITICAL",
        "timestamp": "2026-09-02T13:12:00Z",
        "error_signature": "redis.exceptions.ConnectionError: Max clients reached in auth token pool",
        "stack_trace": (
            "File '/app/auth/token_pool.py', line 33, in acquire\n"
            "  sock = self._connect()\n"
            "ConnectionError: Server closed connection (maxclients limit 10000 reached)"
        ),
        "root_cause": (
            "Third occurrence in payment-service: auth middleware token validation again left sockets open "
            "under high-concurrency payment retries."
        ),
        "runbook_steps": [
            "Apply TCP keepalive socket options in gunicorn: --keep-alive 5",
            "Deploy emergency pool scrubber script: python scripts/scrub_sockets.py",
        ],
        "anti_patterns": [
            "DO NOT scale Redis maxclients beyond 10,000 without increasing kernel somaxconn."
        ],
        "resolved_by": "Sarah Chen (@sarah)",
        "deployment_context": "Deployed auth-middleware v2.3.4 36 hours prior.",
    },
    {
        "id": "INC-107",
        "title": "Elasticsearch Unassigned Shards Cluster Yellow State",
        "service": "search-indexer",
        "severity": "MEDIUM",
        "timestamp": "2026-09-10T10:00:00Z",
        "error_signature": "ClusterBlockException: blocked by: [TOO_MANY_REQUESTS/12/disk usage exceeded flood-stage watermark]",
        "stack_trace": (
            "elasticsearch.exceptions.AuthorizationException: "
            "index [.search_catalog_2026] blocked by flood-stage disk watermark [95%]"
        ),
        "root_cause": (
            "Search log index rotation failed over the weekend, filling the node disk to 95% "
            "and triggering Elasticsearch's automatic read-only cluster freeze."
        ),
        "runbook_steps": [
            "Delete old indexes: curl -X DELETE 'localhost:9200/.search_catalog_2026_06*'",
            "Reset read-only block: curl -X PUT 'localhost:9200/_settings' -d '{\"index.blocks.read_only_allow_delete\": null}'",
            "Expand PersistentVolumeClaim (PVC) size by 50Gi.",
        ],
        "anti_patterns": [
            "DO NOT force allocate unassigned replica shards before clearing disk space; cluster will crash completely."
        ],
        "resolved_by": "Marcus Vance (@marcus)",
        "deployment_context": "No recent deployment; disk exhaustion over time.",
    },
]

# ==============================================================================
# The DELIBERATE HOLDOUT Incident for Act 1 -> Act 2 -> Act 3
# Notice: This is NOT in SEED_INCIDENTS!
# ==============================================================================
HOLDOUT_ACT1_ALERT = {
    "service": "billing-worker",
    "severity": "CRITICAL",
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "error_signature": "Command terminated with exit code 137: OOMKilled",
    "stack_trace": (
        "Last State: Terminated (Reason: OOMKilled, Exit Code: 137)\n"
        "Pod: billing-worker-7c48f8b9d-4x9lp, Namespace: prod-finance\n"
        "Message: Container billing-worker exceeded memory limit (2048Mi) during batch invoice processing."
    ),
    "user_notes": "Triggered during the month-end customer invoicing batch run.",
}

# The Resolution that the user / engineer inputs in Act 2 to teach Hindsight:
HOLDOUT_ACT2_RESOLUTION = {
    "id": "INC-108",
    "title": "Billing Worker JVM OOMKilled during Month-End Batch",
    "service": "billing-worker",
    "severity": "CRITICAL",
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "error_signature": "Command terminated with exit code 137: OOMKilled (2048Mi exceeded)",
    "stack_trace": (
        "Last State: Terminated (Reason: OOMKilled, Exit Code: 137)\n"
        "Container billing-worker exceeded memory limit (2048Mi) during batch invoice processing."
    ),
    "root_cause": (
        "Billing worker loaded all 50,000 monthly enterprise invoices into memory at once "
        "instead of streaming via cursor. JVM heap spiked past 2Gi container limit."
    ),
    "runbook_steps": [
        "Update deployment ConfigMap: BATCH_CHUNK_SIZE=500 (switches to paginated cursor streaming)",
        "Adjust JVM heap flags: JAVA_OPTS='-Xms2g -Xmx3500m -XX:+UseG1GC'",
        "Update Kubernetes pod spec: set resources.limits.memory='4Gi' and requests.memory='3Gi'",
    ],
    "anti_patterns": [
        "CRITICAL: DO NOT scale pod replicas (kubectl scale --replicas=5)! "
        "Multiple replicas without chunk partitioning will pull duplicate invoices and cause DB deadlock."
    ],
    "resolved_by": "On-Call SRE Engineer",
    "deployment_context": "First month-end invoice cycle on the new microservice architecture.",
}

# Act 3 Incoming Alert (Same root issue happening weeks later)
HOLDOUT_ACT3_ALERT = {
    "service": "billing-worker",
    "severity": "CRITICAL",
    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "error_signature": "Kubernetes Pod Evicted: OOMKilled Exit Code 137 in billing-worker",
    "stack_trace": (
        "Pod /prod-finance/billing-worker-99d8b7-kz2wq OOMKilled (137).\n"
        "Memory limit reached while processing enterprise tenant accounts."
    ),
    "user_notes": "New enterprise tenant onboarding batch triggered pod crash.",
}


def get_seed_incidents() -> List[Dict[str, Any]]:
    """Returns the 10 seed incidents (without the holdout)."""
    return list(SEED_INCIDENTS)


def get_holdout_scenario() -> Dict[str, Any]:
    """Returns the 3-act holdout scenario objects."""
    return {
        "act1_alert": HOLDOUT_ACT1_ALERT,
        "act2_resolution": HOLDOUT_ACT2_RESOLUTION,
        "act3_alert": HOLDOUT_ACT3_ALERT,
    }
