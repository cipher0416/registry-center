<!--
Copyright (c) 2026 Huawei Technologies Co., Ltd.
All Rights Reserved.

   Licensed under the Apache License, Version 2.0 (the "License"); you may
   not use this file except in compliance with the License. You may obtain
   a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
   License for the specific language governing permissions and limitations
   under the License.
-->

# A2A-T AgentCard Registry Center

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-green.svg" alt="License"></a>
</p>

<p align="center">
  <strong>A centralized registry for managing AgentCards across multi-vendor AI agents in the A2A-T ecosystem.</strong>
  <br>
  面向 A2A-T 生态的多厂商智能体 AgentCard 统一注册与管理服务。
</p>

<p align="center">
  <a href="./README_zh.md">中文</a>
</p>

---

## Overview

The Registry Center provides unified lifecycle management for **AgentCards** — structured descriptions of AI agents from different vendors. Built for the A2A-T protocol ecosystem, it enables controlled onboarding, discovery, and governance of multi-source agents.

**Use cases:** Telecom operators managing RAN optimization agents, enterprise platforms orchestrating vendor-provided AI services, internal systems with agent approval workflows.

<img src="docs/zh/images/integrated_interactive_relationship.png" width="700" alt="Registry Center Integration Architecture">

## Features

| Category | Capability |
|----------|------------|
| **AgentCard CRUD** | Register, query (by name/organization), update, and deregister agent descriptions |
| **Semantic Search** | Natural-language task matching via LLM + optional vector DB (Milvus) |
| **Agent Approval** | Optional manual review workflow — agents start as `registered`, admins promote to `published` |
| **Tag Management** | Independent tag entities with full CRUD, assignable to agents |
| **TLS Security** | TLS 1.2/1.3 with strong cipher suites, mutual TLS client certificate verification |
| **Signature Verification** | JWS-based AgentCard integrity checks (RS256, ES256), static JWK or dynamic `jku` lookup |
| **Owner Isolation** | Per-agent ownership via TLS client certificate CN, strict or relaxed mode |
| **Content Safety** | Prompt injection and high-risk skill blacklist filtering on registration |
| **Rate Limiting** | Per-endpoint rate limits (configurable: 10–100 req/s) with moving-window algorithm |
| **Audit Logging** | Rotating JSON audit log (time, client IP, user, operation, object, result) |
| **CLI Administration** | Interactive CLI for agent approval, tag management, and full agent listing |
| **Custom Extensions** | Pluggable handlers (auth, audit, decrypt, storage) and LLM providers |

## Quick Start

### Prerequisites
- **Python** 3.10+
- **OS**: Linux for production; Windows supported for development/debugging

### Install & Run

```bash
# Clone the repository
git clone https://gitcode.com/OpenAN/registry-center.git
cd registry-center

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Linux
# .venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt

# Interactive configuration wizard (certificates, storage, security options)
python -m agent_registry.init

# Start the service
python -m agent_registry.start
```

The service starts on `https://127.0.0.1:5000` by default (HTTPS). For a quick test without certificates:

```bash
python -m agent_registry.init    # choose: enable_https = false
python -m agent_registry.start   # starts on http://127.0.0.1:5000
```

### Register Your First Agent

```bash
curl -X POST http://127.0.0.1:5000/rest/v1/registry-center/agent-cards \
  -H "Content-Type: application/json" \
  -d '{
    "agentCards": [{
      "name": "My Agent",
      "description": "An example agent for demonstration.",
      "version": "1.0.0",
      "provider": {"organization": "MyOrg", "url": "https://example.com"},
      "capabilities": {"streaming": true, "pushNotifications": false},
      "skills": [{
        "id": "example-skill",
        "name": "Example Skill",
        "description": "Demonstrates basic agent registration."
      }],
      "supportedInterfaces": [{
        "url": "http://127.0.0.1:8080/",
        "protocolBinding": "HTTP+JSON",
        "protocolVersion": "1.0.0"
      }]
    }]
  }'
```

## Architecture

```
                          HTTPS / TLS
Client ──────────────────────────────────────────┐
                                                  │
┌─────────────────────────────────────────────────▼──────────────────┐
│                        FastAPI Server (:5000)                       │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────────────┐  │
│  │ Rate     │ │ Signature│ │ Owner     │ │ Content Safety       │  │
│  │ Limiter  │ │ Verifier │ │ Isolation │ │ (Prompt Injection)   │  │
│  └──────────┘ └──────────┘ └───────────┘ └──────────────────────┘  │
│                               │                                      │
│                        RegistryCore                                  │
│                    (CRUD + Semantic Search)                           │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  File Storage   │ │  PostgreSQL     │ │  Vector DB      │
│  (JSON, default)│ │  (optional)     │ │  (Milvus, opt)  │
└─────────────────┘ └─────────────────┘ └─────────────────┘

              ┌─────────────────────────────────────┐
              │  CLI (local) ── UDS/TCP ── Internal │
              │  agent approval, tags, management    │
              └─────────────────────────────────────┘
```

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/rest/v1/registry-center/agent-cards` | Register an AgentCard |
| `GET` | `/rest/v1/registry-center/agent-cards` | Query agents (by name/organization) |
| `GET` | `/rest/v1/registry-center/agent-cards/{org}/{name}` | Get a specific agent |
| `PUT` | `/rest/v1/registry-center/agent-cards/{org}/{name}` | Update an agent |
| `DELETE` | `/rest/v1/registry-center/agent-cards/{org}/{name}` | Deregister an agent |
| `POST` | `/rest/v1/registry-center/agent-cards/semantic-query` | Semantic search by task description |
| `GET` | `/rest/v1/registry-center/keys` | Retrieve registry signing public keys (JWK Set) |

See the [API Reference](docs/zh/注册中心API参考.md) for full request/response schemas, error codes, and constraints.

## Configuration

| Config File | Purpose |
|-------------|---------|
| `etc/conf/server.conf` | Server IP, port, TLS certificates, signing, approval, owner isolation |
| `etc/conf/server.properties` | TLS versions, ciphers, connection/timeout/rate limits |
| `etc/conf/persistence.conf` | Storage backend: `file` (default), `postgresql`, `sqlite` |
| `etc/conf/log_config.conf` | Audit log rotation (size, backup count) |
| `common/config/llm_config.json` | LLM model endpoints for semantic search (OpenAI-compatible or AOC) |

Configure interactively:
```bash
python -m agent_registry.init
```

## Documentation

| Document | Language | Description |
|----------|----------|-------------|
| [User Guide](docs/zh/注册中心用户指南.md) | 中文 | Features, deployment, CLI quick reference, FAQ |
| [Development Guide](docs/zh/注册中心开发指南.md) | 中文 | Architecture, registration workflow, custom LLM/handler extensions |
| [API Reference](docs/zh/注册中心API参考.md) | 中文 | Full REST API specification with request/response examples |
| [Security Guide](docs/zh/注册中心安全能力指南.md) | 中文 | TLS, access control, audit logging, content safety, certificate tooling |
| [LLM Config](common/config/README_en.md) | EN | LLM configuration file reference |
| [LLM Config](common/config/README_zh.md) | 中文 | LLM 配置文件说明 |

## Deployment

This project is delivered as **source code only**. Users are responsible for:

1. **Build & install** dependencies on a Linux server
2. **Provision TLS certificates** (or generate self-signed test certs via `python generate_selfsign_cert.py <dir> serverAuth`)
3. **Configure** via `python -m agent_registry.init`
4. **Integrate** authentication, authorization, and database infrastructure from the host system
5. **Set minimal file permissions** (e.g., files `400`, directories `700`)

> **Warning:** This is an internal system module. Do not expose it to the public internet without additional firewall, WAF, and authentication layers.

## Constraints

- Single-instance deployment (not distributed)
- Linux production; Windows development/debugging only
- Max 100 registered agents (configurable via `agent.num.max`)
- 1 MB request body limit
- AgentCards must not contain personal data or sensitive credentials

## License

This project is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) for details.
