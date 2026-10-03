# APEX-OS Business Platform — Deepened API Endpoints (v4)

## HR Module

### Recruitment

#### POST /api/v4/hr/recruitment/jobs
- **Request:** `{"title": "string", "department": "string", "location": "string", "type": "full-time|contract", "salary_range": {"min": 0, "max": 0}, "description": "string"}`
- **Response:** `{"job_id": "string", "status": "open", "created_at": "ISO8601"}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/hr/recruitment/jobs -d '{"title":"Senior Engineer","department":"Engineering"}'`

#### GET /api/v4/hr/recruitment/jobs/{job_id}/candidates
- **Request:** —
- **Response:** `{"candidates": [{"candidate_id": "string", "name": "string", "stage": "screening|interview|offer|rejected", "score": 0.0}]}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/hr/recruitment/jobs/job_123/candidates`

#### POST /api/v4/hr/recruitment/candidates/{id}/advance
- **Request:** `{"stage": "interview", "notes": "string"}`
- **Response:** `{"candidate_id": "string", "new_stage": "interview", "updated_at": "ISO8601"}`
- **Status:** 200, 400, 404
- **Example:** `curl -X POST /api/v4/hr/recruitment/candidates/c_456/advance -d '{"stage":"interview"}'`

#### DELETE /api/v4/hr/recruitment/jobs/{job_id}
- **Request:** —
- **Response:** `{"deleted": true}`
- **Status:** 200, 401, 404
- **Example:** `curl -X DELETE /api/v4/hr/recruitment/jobs/job_123`

### Performance

#### POST /api/v4/hr/performance/reviews
- **Request:** `{"employee_id": "string", "period": "2026-Q3", "goals": [{"goal": "string", "weight": 0, "rating": 1-5}], "reviewer_id": "string"}`
- **Response:** `{"review_id": "string", "overall_rating": 0.0, "status": "draft|submitted"}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/hr/performance/reviews -d '{"employee_id":"e_789","period":"2026-Q3"}'`

#### GET /api/v4/hr/performance/reviews/{review_id}
- **Request:** —
- **Response:** `{"review_id": "string", "employee_id": "string", "goals": [], "overall_rating": 0.0, "feedback": "string"}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/hr/performance/reviews/rev_001`

#### PUT /api/v4/hr/performance/reviews/{review_id}
- **Request:** `{"goals": [{"goal": "string", "rating": 1-5}], "feedback": "string"}`
- **Response:** `{"review_id": "string", "updated_at": "ISO8601"}`
- **Status:** 200, 400, 404
- **Example:** `curl -X PUT /api/v4/hr/performance/reviews/rev_001 -d '{"feedback":"Strong Q3"}'`

#### GET /api/v4/hr/performance/employees/{emp_id}/history
- **Request:** —
- **Response:** `{"reviews": [{"period": "string", "overall_rating": 0.0, "review_id": "string"}]}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/hr/performance/employees/e_789/history`

### Learning

#### POST /api/v4/hr/learning/courses
- **Request:** `{"title": "string", "category": "string", "duration_hours": 0, "url": "string"}`
- **Response:** `{"course_id": "string", "status": "active"}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/hr/learning/courses -d '{"title":"Leadership 101"}'`

#### POST /api/v4/hr/learning/enrollments
- **Request:** `{"employee_id": "string", "course_id": "string"}`
- **Response:** `{"enrollment_id": "string", "status": "enrolled", "progress": 0}`
- **Status:** 201, 400, 404
- **Example:** `curl -X POST /api/v4/hr/learning/enrollments -d '{"employee_id":"e_789","course_id":"c_101"}'`

#### GET /api/v4/hr/learning/employees/{emp_id}/progress
- **Request:** —
- **Response:** `{"courses": [{"course_id": "string", "title": "string", "progress": 0, "completed": false}]}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/hr/learning/employees/e_789/progress`

#### PUT /api/v4/hr/learning/enrollments/{id}/complete
- **Request:** —
- **Response:** `{"enrollment_id": "string", "status": "completed", "completed_at": "ISO8601"}`
- **Status:** 200, 404
- **Example:** `curl -X PUT /api/v4/hr/learning/enrollments/en_001/complete`

### Payroll

#### POST /api/v4/hr/payroll/runs
- **Request:** `{"period": "2026-09", "employee_ids": ["string"]}`
- **Response:** `{"run_id": "string", "status": "processing", "total_amount": 0.0}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/hr/payroll/runs -d '{"period":"2026-09"}'`

#### GET /api/v4/hr/payroll/runs/{run_id}
- **Request:** —
- **Response:** `{"run_id": "string", "status": "completed|failed", "entries": [{"employee_id": "string", "net_pay": 0.0}]}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/hr/payroll/runs/run_001`

#### GET /api/v4/hr/payroll/employees/{emp_id}/payslips
- **Request:** —
- **Response:** `{"payslips": [{"period": "string", "gross": 0.0, "deductions": 0.0, "net": 0.0}]}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/hr/payroll/employees/e_789/payslips`

#### POST /api/v4/hr/payroll/adjustments
- **Request:** `{"employee_id": "string", "period": "string", "type": "bonus|deduction", "amount": 0.0, "reason": "string"}`
- **Response:** `{"adjustment_id": "string", "status": "applied"}`
- **Status:** 201, 400, 404
- **Example:** `curl -X POST /api/v4/hr/payroll/adjustments -d '{"employee_id":"e_789","amount":500,"type":"bonus"}'`

### Engagement

#### POST /api/v4/hr/engagement/surveys
- **Request:** `{"title": "string", "questions": [{"text": "string", "type": "likert|open"}], "audience": "all|department"}`
- **Response:** `{"survey_id": "string", "status": "active", "response_count": 0}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/hr/engagement/surveys -d '{"title":"Q3 Pulse"}'`

#### POST /api/v4/hr/engagement/surveys/{id}/responses
- **Request:** `{"employee_id": "string", "answers": [{"question_id": "string", "value": "string|int"}]}`
- **Response:** `{"response_id": "string", "submitted_at": "ISO8601"}`
- **Status:** 201, 400, 404
- **Example:** `curl -X POST /api/v4/hr/engagement/surveys/s_001/responses -d '{"employee_id":"e_789"}'`

#### GET /api/v4/hr/engagement/surveys/{id}/results
- **Request:** —
- **Response:** `{"survey_id": "string", "response_rate": 0.0, "aggregates": [{"question_id": "string", "avg_score": 0.0}]}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/hr/engagement/surveys/s_001/results`

#### GET /api/v4/hr/engagement/metrics
- **Request:** —
- **Response:** `{"eNPS": 0, "satisfaction": 0.0, "turnover_rate": 0.0, "headcount": 0}`
- **Status:** 200, 401
- **Example:** `curl /api/v4/hr/engagement/metrics`

---

## Projects Module

### Gantt

#### POST /api/v4/projects/gantt/tasks
- **Request:** `{"project_id": "string", "name": "string", "start": "ISO8601", "end": "ISO8601", "dependencies": ["string"], "assignee": "string"}`
- **Response:** `{"task_id": "string", "status": "scheduled"}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/projects/gantt/tasks -d '{"project_id":"p_001","name":"Design Phase"}'`

#### GET /api/v4/projects/gantt/{project_id}
- **Request:** —
- **Response:** `{"tasks": [{"task_id": "string", "name": "string", "start": "ISO8601", "end": "ISO8601", "progress": 0}]}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/projects/gantt/p_001`

#### PUT /api/v4/projects/gantt/tasks/{task_id}
- **Request:** `{"start": "ISO8601", "end": "ISO8601", "progress": 0}`
- **Response:** `{"task_id": "string", "updated_at": "ISO8601"}`
- **Status:** 200, 400, 404
- **Example:** `curl -X PUT /api/v4/projects/gantt/tasks/t_001 -d '{"progress":50}'`

#### DELETE /api/v4/projects/gantt/tasks/{task_id}
- **Request:** —
- **Response:** `{"deleted": true}`
- **Status:** 200, 404
- **Example:** `curl -X DELETE /api/v4/projects/gantt/tasks/t_001`

### Resources

#### POST /api/v4/projects/resources/allocate
- **Request:** `{"project_id": "string", "task_id": "string", "user_id": "string", "allocation_pct": 0}`
- **Response:** `{"allocation_id": "string", "status": "allocated"}`
- **Status:** 201, 400, 404
- **Example:** `curl -X POST /api/v4/projects/resources/allocate -d '{"project_id":"p_001","user_id":"u_001"}'`

#### GET /api/v4/projects/resources/availability
- **Request:** —
- **Response:** `{"users": [{"user_id": "string", "name": "string", "available_pct": 0, "allocated_projects": []}]}`
- **Status:** 200, 401
- **Example:** `curl /api/v4/projects/resources/availability`

#### GET /api/v4/projects/resources/utilization
- **Request:** —
- **Response:** `{"utilization": [{"user_id": "string", "utilization_pct": 0, "overallocated": false}]}`
- **Status:** 200, 401
- **Example:** `curl /api/v4/projects/resources/utilization`

#### DELETE /api/v4/projects/resources/allocations/{id}
- **Request:** —
- **Response:** `{"deleted": true}`
- **Status:** 200, 404
- **Example:** `curl -X DELETE /api/v4/projects/resources/allocations/a_001`

### Time Tracking

#### POST /api/v4/projects/timetracking/entries
- **Request:** `{"task_id": "string", "user_id": "string", "hours": 0, "date": "YYYY-MM-DD", "description": "string"}`
- **Response:** `{"entry_id": "string", "status": "logged"}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/projects/timetracking/entries -d '{"task_id":"t_001","hours":4}'`

#### GET /api/v4/projects/timetracking/tasks/{task_id}
- **Request:** —
- **Response:** `{"entries": [{"entry_id": "string", "user_id": "string", "hours": 0, "date": "YYYY-MM-DD"}], "total_hours": 0}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/projects/timetracking/tasks/t_001`

#### GET /api/v4/projects/timetracking/users/{user_id}/summary
- **Request:** —
- **Response:** `{"total_hours": 0, "by_task": [{"task_id": "string", "hours": 0}]}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/projects/timetracking/users/u_001/summary`

#### PUT /api/v4/projects/timetracking/entries/{entry_id}
- **Request:** `{"hours": 0, "description": "string"}`
- **Response:** `{"entry_id": "string", "updated_at": "ISO8601"}`
- **Status:** 200, 400, 404
- **Example:** `curl -X PUT /api/v4/projects/timetracking/entries/et_001 -d '{"hours":6}'`

### Risk

#### POST /api/v4/projects/risks
- **Request:** `{"project_id": "string", "title": "string", "probability": 0.0, "impact": "low|medium|high", "mitigation": "string"}`
- **Response:** `{"risk_id": "string", "severity": "low|medium|high|critical"}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/projects/risks -d '{"project_id":"p_001","title":"Vendor delay"}'`

#### GET /api/v4/projects/risks/{project_id}
- **Request:** —
- **Response:** `{"risks": [{"risk_id": "string", "title": "string", "severity": "string", "status": "open|mitigated|closed"}]}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/projects/risks/p_001`

#### PUT /api/v4/projects/risks/{risk_id}
- **Request:** `{"status": "mitigated", "mitigation": "string"}`
- **Response:** `{"risk_id": "string", "updated_at": "ISO8601"}`
- **Status:** 200, 400, 404
- **Example:** `curl -X PUT /api/v4/projects/risks/r_001 -d '{"status":"mitigated"}'`

#### DELETE /api/v4/projects/risks/{risk_id}
- **Request:** —
- **Response:** `{"deleted": true}`
- **Status:** 200, 404
- **Example:** `curl -X DELETE /api/v4/projects/risks/r_001`

### Portfolio

#### GET /api/v4/projects/portfolio
- **Request:** —
- **Response:** `{"projects": [{"project_id": "string", "name": "string", "health": "green|yellow|red", "progress": 0, "budget_used_pct": 0}]}`
- **Status:** 200, 401
- **Example:** `curl /api/v4/projects/portfolio`

#### GET /api/v4/projects/portfolio/summary
- **Request:** —
- **Response:** `{"total_projects": 0, "on_track": 0, "at_risk": 0, "over_budget": 0, "avg_progress": 0}`
- **Status:** 200, 401
- **Example:** `curl /api/v4/projects/portfolio/summary`

#### POST /api/v4/projects/portfolio/{project_id}/prioritize
- **Request:** `{"priority": 1-10, "rationale": "string"}`
- **Response:** `{"project_id": "string", "priority": 1-10}`
- **Status:** 200, 400, 404
- **Example:** `curl -X POST /api/v4/projects/portfolio/p_001/prioritize -d '{"priority":9}'`

#### GET /api/v4/projects/portfolio/resource-heatmap
- **Request:** —
- **Response:** `{"heatmap": [{"user_id": "string", "projects": 0, "overallocated": false}]}`
- **Status:** 200, 401
- **Example:** `curl /api/v4/projects/portfolio/resource-heatmap`

---

## Blockchain Module

### Smart Contracts

#### POST /api/v4/blockchain/contracts/deploy
- **Request:** `{"name": "string", "bytecode": "string", "abi": [], "constructor_args": [], "network": "string"}`
- **Response:** `{"contract_address": "string", "tx_hash": "string", "status": "deployed"}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/blockchain/contracts/deploy -d '{"name":"Token","bytecode":"0x..."}'`

#### POST /api/v4/blockchain/contracts/{address}/call
- **Request:** `{"function": "string", "args": [], "value": 0, "from": "string"}`
- **Response:** `{"result": "any", "tx_hash": "string", "gas_used": 0}`
- **Status:** 200, 400, 404
- **Example:** `curl -X POST /api/v4/blockchain/contracts/0x.../call -d '{"function":"transfer"}'`

#### GET /api/v4/blockchain/contracts/{address}
- **Request:** —
- **Response:** `{"address": "string", "name": "string", "network": "string", "deployed_at": "ISO8601", "abi": []}`
- **Status:** 200, 404
- **Example:** `curl /api/v4/blockchain/contracts/0x...`

#### GET /api/v4/blockchain/contracts/{address}/events
- **Request:** —
- **Response:** `{"events": [{"name": "string", "args": {}, "block_number": 0, "tx_hash": "string"}]}`
- **Status:** 200, 404
- **Example:** `curl /api/v4/blockchain/contracts/0x.../events`

### Tokens

#### POST /api/v4/blockchain/tokens/mint
- **Request:** `{"token_address": "string", "to": "string", "amount": 0}`
- **Response:** `{"tx_hash": "string", "status": "pending"}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/blockchain/tokens/mint -d '{"to":"0x...","amount":1000}'`

#### POST /api/v4/blockchain/tokens/transfer
- **Request:** `{"token_address": "string", "from": "string", "to": "string", "amount": 0}`
- **Response:** `{"tx_hash": "string", "status": "pending"}`
- **Status:** 201, 400, 404
- **Example:** `curl -X POST /api/v4/blockchain/tokens/transfer -d '{"to":"0x...","amount":500}'`

#### GET /api/v4/blockchain/tokens/{address}/balance/{wallet}
- **Request:** —
- **Response:** `{"balance": 0, "symbol": "string", "decimals": 0}`
- **Status:** 200, 404
- **Example:** `curl /api/v4/blockchain/tokens/0x.../balance/0x...`

#### GET /api/v4/blockchain/tokens/{address}/holders
- **Request:** —
- **Response:** `{"holders": [{"wallet": "string", "balance": 0, "pct": 0.0}]}`
- **Status:** 200, 404
- **Example:** `curl /api/v4/blockchain/tokens/0x.../holders`

### Consensus

#### GET /api/v4/blockchain/consensus/status
- **Request:** —
- **Response:** `{"network": "string", "block_height": 0, "participating_nodes": 0, "consensus_type": "PoS|PoW|DPoS"}`
- **Status:** 200
- **Example:** `curl /api/v4/blockchain/consensus/status`

#### POST /api/v4/blockchain/consensus/validate
- **Request:** `{"block_hash": "string", "transactions": []}`
- **Response:** `{"valid": true, "confirmations": 0}`
- **Status:** 200, 400
- **Example:** `curl -X POST /api/v4/blockchain/consensus/validate -d '{"block_hash":"0x..."}'`

#### GET /api/v4/blockchain/consensus/nodes
- **Request:** —
- **Response:** `{"nodes": [{"node_id": "string", "address": "string", "stake": 0, "status": "active|inactive"}]}`
- **Status:** 200
- **Example:** `curl /api/v4/blockchain/consensus/nodes`

#### POST /api/v4/blockchain/consensus/stake
- **Request:** `{"node_id": "string", "amount": 0}`
- **Response:** `{"tx_hash": "string", "status": "staked"}`
- **Status:** 201, 400
- **Example:** `curl -X POST /api/v4/blockchain/consensus/stake -d '{"amount":10000}'`

### Bridge

#### POST /api/v4/blockchain/bridge/transfer
- **Request:** `{"from_chain": "string", "to_chain": "string", "token": "string", "amount": 0, "recipient": "string"}`
- **Response:** `{"bridge_tx_id": "string", "status": "initiated", "estimated_time_sec": 0}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/blockchain/bridge/transfer -d '{"from_chain":"ethereum","to_chain":"polygon"}'`

#### GET /api/v4/blockchain/bridge/{tx_id}
- **Request:** —
- **Response:** `{"bridge_tx_id": "string", "status": "pending|completed|failed", "from_chain": "string", "to_chain": "string", "amount": 0}`
- **Status:** 200, 404
- **Example:** `curl /api/v4/blockchain/bridge/btx_001`

#### GET /api/v4/blockchain/bridge/supported-chains
- **Request:** —
- **Response:** `{"chains": [{"id": "string", "name": "string", "bridgeable": true}]}`
- **Status:** 200
- **Example:** `curl /api/v4/blockchain/bridge/supported-chains`

#### GET /api/v4/blockchain/bridge/fees
- **Request:** —
- **Response:** `{"fees": [{"from_chain": "string", "to_chain": "string", "fee_pct": 0.0, "min_fee": 0.0}]}`
- **Status:** 200
- **Example:** `curl /api/v4/blockchain/bridge/fees`

### Analytics

#### GET /api/v4/blockchain/analytics/network
- **Request:** —
- **Response:** `{"total_transactions_24h": 0, "avg_gas_price": 0, "active_addresses": 0, "tvl": 0}`
- **Status:** 200
- **Example:** `curl /api/v4/blockchain/analytics/network`

#### GET /api/v4/blockchain/analytics/tokens/{address}/volume
- **Request:** —
- **Response:** `{"volume_24h": 0, "volume_7d": 0, "price_change_24h_pct": 0.0}`
- **Status:** 200, 404
- **Example:** `curl /api/v4/blockchain/analytics/tokens/0x.../volume`

#### GET /api/v4/blockchain/analytics/contracts/{address}/activity
- **Request:** —
- **Response:** `{"calls_24h": 0, "unique_callers": 0, "top_functions": [{"name": "string", "calls": 0}]}`
- **Status:** 200, 404
- **Example:** `curl /api/v4/blockchain/analytics/contracts/0x.../activity`

#### GET /api/v4/blockchain/analytics/wallet/{address}
- **Request:** —
- **Response:** `{"balance": 0, "token_count": 0, "transaction_count": 0, "first_seen": "ISO8601"}`
- **Status:** 200, 404
- **Example:** `curl /api/v4/blockchain/analytics/wallet/0x...`

---

## ML Module

### Training

#### POST /api/v4/ml/training/jobs
- **Request:** `{"dataset_id": "string", "model_type": "string", "hyperparams": {}, "compute": "cpu|gpu"}`
- **Response:** `{"job_id": "string", "status": "queued", "estimated_duration_sec": 0}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/ml/training/jobs -d '{"dataset_id":"ds_001","model_type":"xgboost"}'`

#### GET /api/v4/ml/training/jobs/{job_id}
- **Request:** —
- **Response:** `{"job_id": "string", "status": "running|completed|failed", "progress": 0, "metrics": {}}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/ml/training/jobs/jt_001`

#### POST /api/v4/ml/training/jobs/{job_id}/stop
- **Request:** —
- **Response:** `{"job_id": "string", "status": "stopped"}`
- **Status:** 200, 404
- **Example:** `curl -X POST /api/v4/ml/training/jobs/jt_001/stop`

#### GET /api/v4/ml/training/jobs/{job_id}/logs
- **Request:** —
- **Response:** `{"logs": [{"timestamp": "ISO8601", "level": "info", "message": "string"}]}`
- **Status:** 200, 404
- **Example:** `curl /api/v4/ml/training/jobs/jt_001/logs`

### Evaluation

#### POST /api/v4/ml/evaluation/runs
- **Request:** `{"model_id": "string", "dataset_id": "string", "metrics": ["accuracy", "f1", "auc"]}`
- **Response:** `{"eval_id": "string", "status": "running"}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/ml/evaluation/runs -d '{"model_id":"m_001","dataset_id":"ds_002"}'`

#### GET /api/v4/ml/evaluation/runs/{eval_id}
- **Request:** —
- **Response:** `{"eval_id": "string", "status": "completed", "metrics": {"accuracy": 0.0, "f1": 0.0}, "confusion_matrix": []}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/ml/evaluation/runs/ev_001`

#### GET /api/v4/ml/evaluation/models/{eval_id}/compare
- **Request:** —
- **Response:** `{"comparison": [{"model_id": "string", "metrics": {}, "rank": 0}]}`
- **Status:** 200, 404
- **Example:** `curl /api/v4/ml/evaluation/models/ev_001/compare`

#### POST /api/v4/ml/evaluation/benchmarks
- **Request:** `{"model_ids": [], "dataset_id": "string"}`
- **Response:** `{"benchmark_id": "string", "results": []}`
- **Status:** 201, 400
- **Example:** `curl -X POST /api/v4/ml/evaluation/benchmarks -d '{"model_ids":["m_001","m_002"]}'`

### Deployment

#### POST /api/v4/ml/deployment/endpoints
- **Request:** `{"model_id": "string", "name": "string", "traffic_split": 100, "instance_type": "string"}`
- **Response:** `{"endpoint_id": "string", "url": "string", "status": "deploying"}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/ml/deployment/endpoints -d '{"model_id":"m_001","name":"prod-v2"}'`

#### GET /api/v4/ml/deployment/endpoints/{endpoint_id}
- **Request:** —
- **Response:** `{"endpoint_id": "string", "status": "active|draining|offline", "traffic_pct": 0, "latency_p99_ms": 0}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/ml/deployment/endpoints/ep_001`

#### POST /api/v4/ml/deployment/endpoints/{id}/predict
- **Request:** `{"instances": [{}]}`
- **Response:** `{"predictions": [], "model_version": "string", "latency_ms": 0}`
- **Status:** 200, 400, 404
- **Example:** `curl -X POST /api/v4/ml/deployment/endpoints/ep_001/predict -d '{"instances":[{"f1":1}]}'`

#### DELETE /api/v4/ml/deployment/endpoints/{endpoint_id}
- **Request:** —
- **Response:** `{"deleted": true}`
- **Status:** 200, 404
- **Example:** `curl -X DELETE /api/v4/ml/deployment/endpoints/ep_001`

### Feature Engineering

#### POST /api/v4/ml/features/transformations
- **Request:** `{"dataset_id": "string", "transformations": [{"column": "string", "method": "normalize|encode|impute"}]}`
- **Response:** `{"transform_id": "string", "status": "applied", "columns_affected": []}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/ml/features/transformations -d '{"dataset_id":"ds_001"}'`

#### GET /api/v4/ml/features/datasets/{dataset_id}/profile
- **Request:** —
- **Response:** `{"columns": [{"name": "string", "type": "string", "null_pct": 0.0, "unique": 0}], "row_count": 0}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/ml/features/datasets/ds_001/profile`

#### POST /api/v4/ml/features/selection
- **Request:** `{"dataset_id": "string", "target": "string", "method": "correlation|mutual_info|shap", "k": 10}`
- **Response:** `{"selected_features": [], "scores": {}}`
- **Status:** 200, 400, 404
- **Example:** `curl -X POST /api/v4/ml/features/selection -d '{"dataset_id":"ds_001","target":"label"}'`

#### GET /api/v4/ml/features/store
- **Request:** —
- **Response:** `{"features": [{"name": "string", "version": "string", "type": "string", "tags": []}]}`
- **Status:** 200, 401
- **Example:** `curl /api/v4/ml/features/store`

### Monitoring

#### GET /api/v4/ml/monitoring/models/{model_id}/drift
- **Request:** —
- **Response:** `{"drift_detected": true, "drift_score": 0.0, "affected_features": [], "window": "7d"}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/ml/monitoring/models/m_001/drift`

#### GET /api/v4/ml/monitoring/endpoints/{endpoint_id}/metrics
- **Request:** —
- **Response:** `{"requests_per_sec": 0, "error_rate": 0.0, "latency_p50_ms": 0, "latency_p99_ms": 0}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/ml/monitoring/endpoints/ep_001/metrics`

#### POST /api/v4/ml/monitoring/alerts
- **Request:** `{"model_id": "string", "metric": "drift|latency|error_rate", "threshold": 0.0, "channel": "email|slack|webhook"}`
- **Response:** `{"alert_id": "string", "status": "active"}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/ml/monitoring/alerts -d '{"model_id":"m_001","metric":"drift"}'`

#### GET /api/v4/ml/monitoring/data-quality/{dataset_id}
- **Request:** —
- **Response:** `{"null_pct": 0.0, "outlier_pct": 0.0, "distribution_shift": 0.0, "passed": true}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/ml/monitoring/data-quality/ds_001`

---

## AI Module

### Conversational

#### POST /api/v4/ai/conversational/sessions
- **Request:** `{"agent_id": "string", "user_id": "string", "context": {}}`
- **Response:** `{"session_id": "string", "status": "active", "created_at": "ISO8601"}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/ai/conversational/sessions -d '{"agent_id":"agent_001"}'`

#### POST /api/v4/ai/conversational/sessions/{session_id}/messages
- **Request:** `{"role": "user|assistant", "content": "string", "attachments": []}`
- **Response:** `{"message_id": "string", "reply": "string", "tokens_used": 0}`
- **Status:** 201, 400, 404
- **Example:** `curl -X POST /api/v4/ai/conversational/sessions/cs_001/messages -d '{"role":"user","content":"Hello"}'`

#### GET /api/v4/ai/conversational/sessions/{session_id}/history
- **Request:** —
- **Response:** `{"messages": [{"role": "string", "content": "string", "timestamp": "ISO8601"}]}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/ai/conversational/sessions/cs_001/history`

#### DELETE /api/v4/ai/conversational/sessions/{session_id}
- **Request:** —
- **Response:** `{"deleted": true}`
- **Status:** 200, 404
- **Example:** `curl -X DELETE /api/v4/ai/conversational/sessions/cs_001`

### Document

#### POST /api/v4/ai/document/ingest
- **Request:** `{"source": "url|file", "content": "string", "metadata": {}, "chunk_size": 512}`
- **Response:** `{"document_id": "string", "status": "processing", "chunks_created": 0}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/ai/document/ingest -d '{"source":"url","content":"https://..."}'`

#### POST /api/v4/ai/document/query
- **Request:** `{"document_ids": [], "query": "string", "top_k": 5}`
- **Response:** `{"results": [{"document_id": "string", "chunk": "string", "score": 0.0}]}`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v4/ai/document/query -d '{"query":"What is the policy?"}'`

#### GET /api/v4/ai/document/{document_id}/summary
- **Request:** —
- **Response:** `{"document_id": "string", "summary": "string", "key_points": []}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/ai/document/doc_001/summary`

#### POST /api/v4/ai/document/extract
- **Request:** `{"document_id": "string", "schema": {"field": "type"}}`
- **Response:** `{"extracted": {"field": "value"}, "confidence": 0.0}`
- **Status:** 200, 400, 404
- **Example:** `curl -X POST /api/v4/ai/document/extract -d '{"document_id":"doc_001"}'`

### Vision

#### POST /api/v4/vision/analyze
- **Request:** `{"image_url": "string", "tasks": ["ocr", "object_detection", "classification"]}`
- **Response:** `{"results": {"ocr": {"text": "string"}, "objects": [{"label": "string", "bbox": [], "confidence": 0.0}]}}`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v4/vision/analyze -d '{"image_url":"https://...","tasks":["ocr"]}'`

#### POST /api/v4/vision/compare
- **Request:** `{"image_a": "string", "image_b": "string", "metric": "ssim|embedding"}`
- **Response:** `{"similarity": 0.0, "metric": "string"}`
- **Status:** 200, 400
- **Example:** `curl -X POST /api/v4/vision/compare -d '{"image_a":"https://...","image_b":"https://..."}'`

#### POST /api/v4/vision/generate
- **Request:** `{"prompt": "string", "style": "string", "resolution": "1024x1024", "n": 1}`
- **Response:** `{"images": [{"url": "string", "seed": 0}]}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/vision/generate -d '{"prompt":"a sunset over mountains"}'`

#### GET /api/v4/vision/models
- **Request:** —
- **Response:** `{"models": [{"id": "string", "type": "detection|segmentation|generation", "status": "available"}]}`
- **Status:** 200, 401
- **Example:** `curl /api/v4/vision/models`

### Speech

#### POST /api/v4/speech/transcribe
- **Request:** `{"audio_url": "string", "language": "en", "diarize": false}`
- **Response:** `{"transcript": "string", "segments": [{"start": 0, "end": 0, "text": "string", "speaker": "string"}]}`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v4/speech/transcribe -d '{"audio_url":"https://...","language":"en"}'`

#### POST /api/v4/speech/synthesize
- **Request:** `{"text": "string", "voice": "string", "speed": 1.0, "format": "mp3|wav"}`
- **Response:** `{"audio_url": "string", "duration_sec": 0}`
- **Status:** 201, 400, 401
- **Example:** `curl -X POST /api/v4/speech/synthesize -d '{"text":"Hello world","voice":"alloy"}'`

#### POST /api/v4/speech/translate
- **Request:** `{"audio_url": "string", "source_lang": "en", "target_lang": "es"}`
- **Response:** `{"translated_text": "string", "audio_url": "string"}`
- **Status:** 200, 400
- **Example:** `curl -X POST /api/v4/speech/translate -d '{"audio_url":"https://...","target_lang":"es"}'`

#### GET /api/v4/speech/voices
- **Request:** —
- **Response:** `{"voices": [{"id": "string", "name": "string", "language": "string", "gender": "string"}]}`
- **Status:** 200, 401
- **Example:** `curl /api/v4/speech/voices`

### Recommendations

#### POST /api/v4/ai/recommendations
- **Request:** `{"user_id": "string", "context": {}, "n_results": 10, "strategy": "collaborative|content|hybrid"}`
- **Response:** `{"recommendations": [{"item_id": "string", "score": 0.0, "reason": "string"}]}`
- **Status:** 200, 400, 401
- **Example:** `curl -X POST /api/v4/ai/recommendations -d '{"user_id":"u_001","n_results":5}'`

#### POST /api/v4/ai/recommendations/feedback
- **Request:** `{"user_id": "string", "item_id": "string", "event": "click|purchase|dismiss", "recommendation_id": "string"}`
- **Response:** `{"recorded": true}`
- **Status:** 201, 400
- **Example:** `curl -X POST /api/v4/ai/recommendations/feedback -d '{"user_id":"u_001","item_id":"i_001","event":"click"}'`

#### GET /api/v4/ai/recommendations/trending
- **Request:** —
- **Response:** `{"items": [{"item_id": "string", "score": 0.0, "category": "string"}]}`
- **Status:** 200, 401
- **Example:** `curl /api/v4/ai/recommendations/trending`

#### GET /api/v4/ai/recommendations/users/{user_id}/profile
- **Request:** —
- **Response:** `{"user_id": "string", "preferences": {}, "interaction_count": 0, "segments": []}`
- **Status:** 200, 401, 404
- **Example:** `curl /api/v4/ai/recommendations/users/u_001/profile`
