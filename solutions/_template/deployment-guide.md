# Deployment Guide: {{SOLUTION_NAME}}

## Prerequisites

- [ ] Agent Mahoo platform access (v2.0+)
- [ ] Required API keys and credentials:
  - {{List each required credential}}
- [ ] Infrastructure requirements:
  - {{Compute, memory, storage minimums}}
- [ ] Client-side requirements:
  - {{Any client systems or access needed}}

## Environment Setup

### 1. Clone and Configure

```bash
# Clone the solution scaffold
jumbo solutions init {{SOLUTION_SLUG}}

# Navigate to the solution directory
cd solutions/{{SOLUTION_SLUG}}

# Copy and edit the environment file
cp .env.example .env
```

### 2. Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `{{VAR_NAME}}` | {{Description}} | Yes/No | {{Default}} |

### 3. Dependencies

```bash
# Install solution-specific dependencies
jumbo solutions install {{SOLUTION_SLUG}}
```

## Configuration

### Agent Configuration

Edit `agents.yaml` to customize AI agent behavior:

```yaml
agents:
  - name: {{agent_name}}
    model: {{model_id}}
    temperature: 0.3
    max_tokens: 4096
    instruments:
      - {{instrument_name}}
```

### Integration Configuration

Configure each integration in `integrations.yaml`:

```yaml
integrations:
  - name: {{integration_name}}
    type: {{type}}
    config:
      {{key}}: {{value}}
```

## Deployment Steps

### Step 1: Validate Configuration

```bash
jumbo solutions validate {{SOLUTION_SLUG}}
```

### Step 2: Run Database Migrations

```bash
jumbo solutions migrate {{SOLUTION_SLUG}}
```

### Step 3: Deploy Agents

```bash
jumbo solutions deploy {{SOLUTION_SLUG}} --environment production
```

### Step 4: Verify Health

```bash
jumbo solutions health {{SOLUTION_SLUG}}
```

## Verification

### Smoke Tests

Run the built-in smoke test suite to verify the deployment:

```bash
jumbo solutions test {{SOLUTION_SLUG}} --suite smoke
```

### Manual Verification Checklist

- [ ] All agents are running and responsive
- [ ] Integrations are connected and authenticated
- [ ] Data flow is working end-to-end
- [ ] Monitoring dashboards are populating
- [ ] Alerting rules are active

## Troubleshooting

### Common Issues

#### Agent fails to start

**Symptom:** Agent status shows `error` after deployment.

**Resolution:**

1. Check logs: `jumbo solutions logs {{SOLUTION_SLUG}} --agent {{agent_name}}`
2. Verify API keys are correctly set in `.env`
3. Confirm model access permissions

#### Integration connection timeout

**Symptom:** Integration health check returns `timeout`.

**Resolution:**

1. Verify network connectivity to the external service
2. Check API rate limits on the external service
3. Review firewall rules for outbound connections

#### Data not flowing through pipeline

**Symptom:** Ingested data does not appear in output.

**Resolution:**

1. Check the ingestion queue: `jumbo solutions queue {{SOLUTION_SLUG}}`
2. Verify transformation rules in `pipeline.yaml`
3. Review agent logs for processing errors

### Getting Help

- Platform docs: <https://docs.agentjumbo.com/solutions/{{SOLUTION_SLUG}}>
- Support: <support@agentjumbo.com>
- Status page: <https://status.agentjumbo.com>
