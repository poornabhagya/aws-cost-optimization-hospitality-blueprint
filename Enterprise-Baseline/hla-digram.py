"""
Platform-Neutral High-Level Architecture (HLA) Diagram Generator
Aligned with: BRD_SPECIFICATION.md, NFR_SPECIFICATION.md, CAPACITY_SIZING.md
Scope: Single Boutique Property (10 Rooms, 30 Dining, 20 Bar, 4 POS Nodes)
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import Users, Client
from diagrams.onprem.network import Nginx, Haproxy
from diagrams.onprem.container import Docker
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.storage import Ceph
from diagrams.onprem.monitoring import Prometheus, Grafana

# Dark Mode Canvas Palette Configuration
graph_attr = {
    "fontsize": "20",
    "bgcolor": "#0d1117",
    "fontcolor": "#ffffff",
    "pad": "0.8",
    "ranksep": "1.2",
    "nodesep": "0.9",
}

node_attr = {
    "fontcolor": "#ffffff",
    "fontsize": "11",
    "labelfontsize": "11",
}

with Diagram(
    name="Hospitality OS - End-to-End High-Level System Architecture (HLA)\nPlatform-Neutral / Multi-AZ Topology / Local-First Resilience",
    show=False,
    filename="hospitality_os_hla_architecture",
    outformat="png",
    direction="TB",
    graph_attr=graph_attr,
    node_attr=node_attr
):

    # ---------------------------------------------------------
    # 1. CLIENT & ON-PREMISE HARDWARE TIER (BRD 3.1 / BRD 5.2)
    # ---------------------------------------------------------
    with Cluster("1. Client & On-Premise Hardware Layer", graph_attr={"bgcolor": "#161b22", "fontcolor": "#58a6ff"}):
        guest_clients = Users("Public Guest Channels\n• Direct Booking Engine\n• Mobile QR Digital Menu\n(20-30 Concurrent Sessions)")
        
        with Cluster("On-Premise Property LAN Terminals", graph_attr={"bgcolor": "#21262d", "fontcolor": "#79c0ff"}):
            pos_terminals = Client("Local POS Terminals (x2)\n[Dining & Speed Bar]\n• Embedded SQLite / RxDB\n• Native ESC/POS Bridge\n(72h Local-First Offline Mode)")
            pms_workstation = Client("Front Desk PMS PC\n• Visual Booking Grid\n• Guest Check-In/Out")
            kds_display = Client("Kitchen Display System (KDS)\n• Visual Ticket Timers\n• Station Order Bump (<250ms)")

    # ---------------------------------------------------------
    # 2. EDGE SECURITY & INGRESS TIER (NFR 1.1 / NFR 5.2)
    # ---------------------------------------------------------
    with Cluster("2. Edge Security & Ingress Routing Plane", graph_attr={"bgcolor": "#161b22", "fontcolor": "#bc8cff"}):
        edge_waf = Nginx("Edge Reverse Proxy & WAF\n• TLS 1.3 Termination / HSTS\n• Rate Limiting (30-120 req/min)\n• PII Scrubbing / CORS Engine")
        load_balancer = Haproxy("Ingress Load Balancer (HAProxy)\n• HTTP/gRPC Routing\n• Multi-AZ Health Probes (10s)\n• Socket Capacity: 100 Sockets")

    # ---------------------------------------------------------
    # 3. STATELESS APPLICATION EXECUTION PLANE (Sizing 2.1-2.3)
    # ---------------------------------------------------------
    with Cluster("3. Stateless Compute Execution Plane (Modular Monolith)", graph_attr={"bgcolor": "#161b22", "fontcolor": "#3fb950"}):
        with Cluster("Availability Zone A (Fault Domain 1)", graph_attr={"bgcolor": "#21262d", "fontcolor": "#7ee787"}):
            app_node_1 = Docker("App Runtime Task 1\n• Python 3.12 / Gunicorn\n• PMS, POS, GL, Inventory Core\n(0.25 vCPU / 512 MB RAM)")

        with Cluster("Availability Zone B (Fault Domain 2)", graph_attr={"bgcolor": "#21262d", "fontcolor": "#7ee787"}):
            app_node_2 = Docker("App Runtime Task 2\n• Python 3.12 / Gunicorn\n• PMS, POS, GL, Inventory Core\n(0.25 vCPU / 512 MB RAM)")

        with Cluster("Async Background Worker Pool", graph_attr={"bgcolor": "#21262d", "fontcolor": "#7ee787"}):
            celery_worker = Docker("Celery Outbox Consumer\n• Async BOM Explosion\n• GL Double-Entry Journaling\n• Night Audit Batch Runner")

    # ---------------------------------------------------------
    # 4. EPHEMERAL IN-MEMORY STATE PLANE (Sizing 4.1 / NFR 5.3)
    # ---------------------------------------------------------
    with Cluster("4. Ephemeral State & In-Memory Event Bus", graph_attr={"bgcolor": "#161b22", "fontcolor": "#d29922"}):
        redis_cache = Redis("In-Memory State Engine (512 MB)\n• Room Slices (`pms:avail:slice`)\n• Distributed Locks (`pms:lock`)\n• Idempotency Dedup (`pos:sync:dedup`)\n• Transactional Outbox Stream")

    # ---------------------------------------------------------
    # 5. MULTIPLEXING & PERSISTENCE PLANE (Sizing 3.1-3.3 / BRD 6.1)
    # ---------------------------------------------------------
    with Cluster("5. Relational Persistence & Multiplexing Plane", graph_attr={"bgcolor": "#161b22", "fontcolor": "#ff7b72"}):
        pg_bouncer = PostgreSQL("PgBouncer Connection Pooler\n• Transaction Pooling Mode\n• 30 Client Sockets -> 5-10 DB Sockets\n(1,000 TPS Capacity Ceiling)")
        db_primary = PostgreSQL("PostgreSQL 17 Primary Engine\n• Schema-per-Tenant Isolation\n• Append-Only Double-Entry Ledger\n• Effective-Dated Tax Tables\n(0.50 vCPU / 2.0 GB RAM / 20 GB SSD)")

    # ---------------------------------------------------------
    # 6. DURABLE OBJECT VAULT & ARCHIVAL (NFR 4.2 / BRD 6.3)
    # ---------------------------------------------------------
    with Cluster("6. Durable Object & Compliance Vault", graph_attr={"bgcolor": "#161b22", "fontcolor": "#79c0ff"}):
        object_vault = Ceph("Immutable Object Store (S3-Compatible)\n• WORM Locked Folio & Invoice PDFs\n• Continuous WAL Archive Stream (PITR)\n• 7-Year Fiscal Audit Records")

    # ---------------------------------------------------------
    # 7. OBSERVABILITY & TELEMETRY PLANE (Sizing 5.1 / NFR 2.1)
    # ---------------------------------------------------------
    with Cluster("7. Observability & Telemetry Plane", graph_attr={"bgcolor": "#161b22", "fontcolor": "#f0883e"}):
        prometheus = Prometheus("Prometheus Metrics Collector\n• Latency Probes (P50/P95/P99)\n• Active TPS, DB IOPS & Sockets\n• Host & Memory Headroom Scrape")
        grafana = Grafana("Grafana Dashboards & Alerts\n• SLA/SLO Performance Visualizer\n• Revenue Center Telemetry")

    # ---------------------------------------------------------
    # EXPLICIT DIRECTED DATA FLOWS
    # ---------------------------------------------------------
    # Ingress Traffic Routing
    guest_clients >> Edge(label="HTTPS / TLS 1.3", color="#58a6ff", fontcolor="#ffffff") >> edge_waf
    pms_workstation >> Edge(label="LAN HTTPS", color="#79c0ff", fontcolor="#ffffff") >> edge_waf
    pos_terminals >> Edge(label="Online Checkout (HTTPS)", color="#79c0ff", fontcolor="#ffffff") >> edge_waf
    
    # Offline Batch Sync Replay Flow (BRD 5.2)
    pos_terminals >> Edge(label="Post-Outage Batch Replay\n(Idempotent Sync)", color="#e3b341", style="dashed", fontcolor="#e3b341") >> edge_waf
    
    edge_waf >> Edge(label="WAF Cleaned Stream", color="#bc8cff", fontcolor="#ffffff") >> load_balancer

    # Multi-AZ Compute Load Balancing
    load_balancer >> Edge(label="Round-Robin (AZ-A)", color="#3fb950", fontcolor="#ffffff") >> app_node_1
    load_balancer >> Edge(label="Round-Robin (AZ-B)", color="#3fb950", fontcolor="#ffffff") >> app_node_2

    # Real-Time KDS Push Flow (<250ms)
    app_node_1 >> Edge(label="WebSocket KDS Push (<250ms)", color="#7ee787", style="bold", fontcolor="#7ee787") >> kds_display

    # Ephemeral State & Outbox Messaging
    app_node_1 >> Edge(label="Locks & Search Cache", color="#d29922", fontcolor="#ffffff") >> redis_cache
    app_node_2 >> Edge(label="Locks & Search Cache", color="#d29922", fontcolor="#ffffff") >> redis_cache
    app_node_1 >> Edge(label="Publish Domain Events", color="#d29922", fontcolor="#ffffff") >> redis_cache
    
    redis_cache >> Edge(label="Consume Outbox Queue", color="#d29922", fontcolor="#ffffff") >> celery_worker

    # Persistence & Connection Multiplexing
    app_node_1 >> Edge(label="SQL Queries / CRUD", color="#ff7b72", fontcolor="#ffffff") >> pg_bouncer
    app_node_2 >> Edge(label="SQL Queries / CRUD", color="#ff7b72", fontcolor="#ffffff") >> pg_bouncer
    celery_worker >> Edge(label="Async GL Ledger Entries", color="#ff7b72", fontcolor="#ffffff") >> pg_bouncer
    pg_bouncer >> Edge(label="Multiplexed TCP (5-10 Sockets)", color="#ff7b72", fontcolor="#ffffff") >> db_primary

    # Durable Storage & Backups
    app_node_1 >> Edge(label="Export Invoices (WORM PDF)", color="#79c0ff", fontcolor="#ffffff") >> object_vault
    db_primary >> Edge(label="Streaming WAL Logs (PITR)", color="#79c0ff", fontcolor="#ffffff") >> object_vault

    # Telemetry Monitoring
    app_node_1 >> Edge(label="Scrape Metrics", color="#f0883e", style="dotted", fontcolor="#f0883e") >> prometheus
    db_primary >> Edge(label="DB Stats / IOPS", color="#f0883e", style="dotted", fontcolor="#f0883e") >> prometheus
    prometheus >> Edge(label="Query Metrics", color="#f0883e", fontcolor="#ffffff") >> grafana