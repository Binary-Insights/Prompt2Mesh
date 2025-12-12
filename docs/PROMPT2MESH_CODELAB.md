# **Prompt2Mesh: Agentic 3D Modeling with LangChain + LangGraph on EKS**

# **DAMG 7245 – Fall'25 – Binary Insights**

| Summary | This Codelab demonstrates an agentic, multi-user system for converting natural language into 3D models in Blender. Using **LangChain** for tool abstraction and **LangGraph** for multi-agent orchestration, the system autonomously plans, executes, and refines modeling steps via Model Context Protocol (MCP). Claude Sonnet 4.5 Vision provides quality feedback for iterative refinement. Deployed on AWS EKS with per-user containers, the architecture supports concurrent users, persistent workspaces, and cloud-native analytics. |
| :---- | :---- |
| **Scope** | Multi-user auth + JWT, **LangChain MCP tool wrappers**, **LangGraph state machine workflows**, **Artisan Agent** (autonomous 3D builder), **Refinement Agent** (prompt enhancer), vision-based quality assessment, EKS/ECR deployment, and operational runbooks. |
| **Status** | Production-ready on EKS. Implements **LangChain StructuredTools**, **LangGraph StateGraph**, **Claude Sonnet 4.5 Vision** feedback loop, checkpointed state for resume, and per-user Blender pods. |
| **Authors** | MyclineShareena John Peter Kennedy, Reky George Philip |

---

# **Introduction**

Prompt2Mesh addresses the challenge of procedural 3D modeling for non-experts and rapid prototyping workflows. Traditional tools require deep domain knowledge and manual execution. Neural reconstruction (NeRF, diffusion models) produces black-box outputs without interpretability or editability.

This project combines:
1. **LangChain**: Structured tool abstraction wrapping Blender MCP operations
2. **LangGraph**: Multi-agent orchestration with state machines, retries, and human-in-the-loop checkpoints
3. **Claude Sonnet 4.5**: Natural language understanding + tool calling
4. **Vision AI**: Screenshot-based quality assessment with iterative refinement
5. **Multi-User Cloud Infrastructure**: EKS-based deployment with per-user isolation

**Key Innovation**: The **Artisan Agent** autonomously plans 5–12 modeling steps, executes MCP tool calls, captures viewport screenshots, analyzes quality with vision AI, and **refines sub-par work** before continuing—mirroring human iterative design workflows.

By the end, a user logs in, enters "Create a decorated Christmas tree," and receives a fully modeled, refined 3D asset with transparent execution logs.

---

# **Technology Stack Involved**

| Component | Technology | Purpose |
| :---- | :---- | :---- |
| **Frontend** | Streamlit | Chat UI, login, session display |
| **Backend API** | FastAPI | Auth, per-user container orchestration, session APIs |
| **Agent Framework** | LangChain + LangGraph | Tool abstraction (StructuredTools), workflow orchestration (StateGraph), state checkpointing (MemorySaver) |
| **LLM** | Anthropic Claude Sonnet 4.5 | Prompt understanding, tool calling, multi-step planning |
| **Vision AI** | Claude Sonnet 4.5 Vision | Screenshot quality assessment (1-10 scoring), refinement feedback |
| **Execution Layer** | Blender MCP Addon | Model Context Protocol server exposing Blender operations as tools |
| **Containerization** | Docker | Images for backend, frontend, Blender-MCP |
| **Orchestration** | Kubernetes on AWS EKS | Scalable deployment, per-user pods, services |
| **Registry** | AWS ECR | Store versioned container images |
| **Storage** | EBS via CSI | Persist user scenes/workspaces |
| **Ingress / LB** | AWS Load Balancer Controller + Nginx | External HTTP access |

---

# **Problem Statement, Challenges, Solution & Limitations**

### **Problem Statement**
Traditional 3D modeling requires domain expertise; neural approaches lack interpretability; procedural systems execute blindly without quality assessment. Multi-user cloud deployment requires session isolation, rate-limit handling, and auto-recovery.

### **Challenges**
| Challenge | Impact |
| :---- | :---- |
| **Per-user isolation** | Shared Blender instances collide; users affect each other |
| **Autonomous quality control** | How to verify modeling steps without human inspection? |
| **Iterative refinement** | Agent must detect poor-quality work and improve it autonomously |
| **MCP addon enablement** | Addon must be installed and enabled reliably in containers |
| **Cloud access** | External LB + Ingress wiring for user UI routes |
| **Persistence** | User data must persist across restarts |
| **Rate limiting** | Anthropic API throttles high-frequency tool calls |

### **Solution Approach**
We deploy a **multi-agent architecture with vision-based refinement**:

1. **ArtisanAgent (LangGraph StateGraph)**:
   - **7 workflow nodes**: `analyze_scene` → `plan` → `execute_step` → `capture_feedback` → `assess_quality` → `refine_step` (conditional) → `evaluate_progress` → `complete`
   - **LangChain integration**: `ChatAnthropic` with `.bind_tools(mcp_tools)` for structured tool calling
   - **Vision feedback loop**: Claude Sonnet 4.5 Vision scores screenshots (1-10); quality < 6 (or < 7 for critical steps) triggers refinement
   - **State checkpointing**: `MemorySaver` persists graph state for resume after rate limits/interruptions
   - **Max 2 refinement attempts per step** to prevent infinite loops

2. **PromptRefinementAgent**: Enhances user prompts with specificity before execution

3. **Per-User Containers**: Each login spawns a Blender-MCP container with unique ports (MCP: 10000+, UI: 13000+)

4. **Auth + Session**: FastAPI issues JWT and manages per-user sessions

5. **Frontend**: Streamlit UI for login and chat

6. **Cloud Infra**: EKS with LoadBalancer Service for frontend; ClusterIP for backend and DB; EBS CSI for persistent volumes

### **Limitations & Trade-offs**
| Limitation | Reason | Mitigation |
| :---- | :---- | :---- |
| **Vision assessment accuracy** | Claude may misinterpret screenshots in complex scenes | Use clear viewport angles, adaptive quality thresholds |
| **Rate limiting** | Anthropic API throttles high-frequency calls | Exponential backoff with `invoke_with_retry()`, 3 retries |
| **Refinement overhead** | Max 2 refinements per step adds latency | Trade-off: quality vs. speed; configurable max_refinements_per_step |
| **Addon auto-start edge cases** | Container display / permissions | Use custom image and init script; fallback manual enable in Preferences |
| **LB propagation delays** | AWS LB readiness | Allow 1–3 minutes; verify via `kubectl get svc` and `describe` |

---

# **Setup & Running Instructions**

### **Prerequisites**
- Windows with PowerShell 5.1 (or macOS/Linux with equivalents)
- Docker Desktop installed
- AWS CLI + `kubectl` configured for your EKS cluster
- Anthropic API key

### **Local Development (Docker Compose)**

#### 1. Start Services
```powershell
cd C:\Prompt2Mesh
docker-compose -f docker\docker-compose.yml up -d
```

#### 2. Access Web Interface
Open: `http://localhost:8501`

#### 3. Sign Up / Login
- Create account → Login
- Wait ~10–30 seconds for your Blender container
- You’ll see your Blender UI URL (e.g., `http://localhost:13000`)

#### 4. Enable MCP Addon (if not auto-enabled)
- Open Blender UI → Edit → Preferences → Add-ons
- Search “MCP” and enable “Blender MCP Server”
- MCP server starts on port 9876, mapped to your host MCP port (10000+)

---

## **Cloud Deployment (EKS)**

### 1. Build & Push Images to ECR
```powershell
# Authenticate to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 785186658816.dkr.ecr.us-east-1.amazonaws.com

# Build images
cd C:\Prompt2Mesh
docker build -t 785186658816.dkr.ecr.us-east-1.amazonaws.com/prompt2mesh/backend:latest -f docker/dockerfile --target backend .
docker build -t 785186658816.dkr.ecr.us-east-1.amazonaws.com/prompt2mesh/frontend:latest -f docker/dockerfile --target frontend .
docker build -t 785186658816.dkr.ecr.us-east-1.amazonaws.com/prompt2mesh/blender-mcp:latest -f docker/dockerfile .

# Push images
docker push 785186658816.dkr.ecr.us-east-1.amazonaws.com/prompt2mesh/backend:latest
docker push 785186658816.dkr.ecr.us-east-1.amazonaws.com/prompt2mesh/frontend:latest
docker push 785186658816.dkr.ecr.us-east-1.amazonaws.com/prompt2mesh/blender-mcp:latest
```

### 2. Deploy/Restart on EKS
```powershell
# Restart deployments to pull latest images
kubectl rollout restart deployment/backend -n prompt2mesh
kubectl rollout restart deployment/frontend -n prompt2mesh
kubectl rollout restart deployment/postgres -n prompt2mesh
```

### 3. Verify
```powershell
kubectl get pods -n prompt2mesh
```
All should be `Running` with `1/1` ready.

### 4. Frontend URL
Use the LoadBalancer hostname:
```powershell
$frontendUrl = kubectl get svc frontend -n prompt2mesh -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
Write-Host "Application URL: http://${frontendUrl}:8501"
```

---

# **Architecture Diagram**

```
┌─────────────────────┐
│  Streamlit Frontend │  (Port 8501, LoadBalancer)
└──────────┬──────────┘
           │ HTTP
           ▼
┌──────────────────────────────────┐
│  FastAPI Backend                  │  (Port 8000, ClusterIP)
│  - ArtisanAgent (LangGraph)      │
│  - RefinementAgent (LangChain)   │
│  - K8sUserSessionManager         │
└──────────┬──────────────────────┘
           │ Spawns per-user pod
           ▼
┌──────────────────────────────────┐
│ Blender + MCP (per user)         │
│ MCP: 9876 → 10000+               │
│ UI:  3000 → 13000+               │
│ - MCP Server (stdio)             │
│ - Blender 3.6+ with addon        │
└──────────────────────────────────┘
```

**LangGraph Workflow (ArtisanAgent)**:
```
START
  ↓
analyze_scene ──→ plan ──→ execute_step ──→ capture_feedback ──→ assess_quality
                                 ↑                                      │
                                 │                                      ↓
                                 │                              needs_refinement?
                                 │                                      │
                                 │                                      ├─ YES → refine_step ─┘
                                 │                                      │
                                 │                                      └─ NO → evaluate_progress
                                 │                                               │
                                 │                                               ├─ more steps? → (loop back)
                                 │                                               │
                                 └───────────────────────────────────────────────┴─ complete → END
```

Key files: see `README.md`, `docs/ARCHITECTURE.md`, `docs/MULTI_USER_ARCHITECTURE.md`, `docs/REFINEMENT_LOOP_ARCHITECTURE.md`.

---

# **Pipeline Implementation**

## **Phase 0: Prompt Refinement**
**Goal**: Transform vague user prompts into detailed, actionable instructions

**Implementation** (`src/refinement_agent/prompt_refinement_agent.py`):
```python
class PromptRefinementAgent:
    def __init__(self):
        self.llm = ChatAnthropic(model="claude-sonnet-4-20250514")
        # Uses LangChain prompt templates to enhance specificity
    
    def refine_prompt(self, user_prompt: str) -> str:
        # Adds geometric details, material properties, constraints
        # Example: "Christmas tree" → "Create 3D conical mesh (height 5m, base 1.5m), 
        #          add 20 sphere ornaments (red/gold/silver), star topper at apex"
```

**Example Flow**:
```
User Input: "Make a Christmas tree"
          ↓
RefinementAgent:
          ↓
Enhanced Prompt: "Create a 3D conical evergreen tree (height 5 meters, base radius 1.5 meters).
                  Add 20 sphere ornaments distributed evenly in red, gold, and silver.
                  Place a star mesh at the apex. Apply green material to trunk."
```

---

## **Phase 1: Scene Analysis & Planning**
**Goal**: Understand current scene state and decompose prompt into 5-12 executable steps

**Implementation** (`src/artisan_agent/artisan_agent.py`):
```python
def _analyze_scene_node(self, state: AgentState) -> AgentState:
    """Node 1: Analyze scene with MCP list_objects tool"""
    tool_call = self.llm_with_tools.invoke([
        SystemMessage("You are analyzing a Blender scene."),
        HumanMessage(f"Analyze: {state['user_prompt']}")
    ])
    # Returns: existing objects, scene structure, constraints

def _plan_node(self, state: AgentState) -> AgentState:
    """Node 2: Generate 5-12 modeling steps"""
    response = self.llm_with_tools.invoke([
        SystemMessage("Generate modeling plan from scene analysis."),
        HumanMessage(state['scene_analysis'])
    ])
    # Returns: [
    #   "Step 1: Create cone primitive for tree trunk",
    #   "Step 2: Add sphere for first ornament at (0, 0, 2)",
    #   ...
    # ]
```

**Example Plan Output**:
```json
{
  "steps": [
    {"id": 1, "action": "create_mesh", "params": {"type": "cone", "height": 5, "radius": 1.5}},
    {"id": 2, "action": "add_material", "params": {"name": "evergreen", "color": [0.1, 0.4, 0.1]}},
    {"id": 3, "action": "create_mesh", "params": {"type": "uv_sphere", "location": [0.5, 0.5, 2]}},
    ...
  ]
}
```

---

## **Phase 2: Iterative Execution with Vision Feedback**
**Goal**: Execute steps, capture screenshots, assess quality, refine if needed

### **Step 2a: Execute & Capture**
```python
def _execute_step_node(self, state: AgentState) -> AgentState:
    """Node 3: Execute MCP tool calls for current step"""
    current_step = state['plan'][state['current_step_idx']]
    
    # LangChain tool binding: llm.bind_tools(mcp_tools)
    response = self.llm_with_tools.invoke([
        SystemMessage("Execute this modeling step using MCP tools."),
        HumanMessage(f"Step: {current_step}")
    ])
    
    # Extract tool calls and execute via MCP
    for tool_call in response.tool_calls:
        result = self.mcp_connection.execute_tool(
            tool_call['name'], 
            tool_call['args']
        )
        state['execution_history'].append(result)
    
    return state

def _capture_feedback_node(self, state: AgentState) -> AgentState:
    """Node 4: Capture Blender viewport screenshot"""
    screenshot_path = self.mcp_connection.execute_tool(
        "capture_viewport_screenshot",
        {"output_path": f"/tmp/step_{state['current_step_idx']}.png"}
    )
    state['latest_screenshot'] = screenshot_path
    return state
```

### **Step 2b: Vision-Based Quality Assessment**
```python
def _assess_quality_node(self, state: AgentState) -> AgentState:
    """Node 5: Analyze screenshot with Claude Sonnet 4.5 Vision"""
    vision_llm = ChatAnthropic(model="claude-sonnet-4-20250514")
    
    with open(state['latest_screenshot'], 'rb') as img:
        image_b64 = base64.b64encode(img.read()).decode()
    
    response = vision_llm.invoke([
        HumanMessage(content=[
            {"type": "image", "source": {"type": "base64", "data": image_b64}},
            {"type": "text", "text": f"""
                Evaluate this 3D modeling step (Step {state['current_step_idx']}):
                Expected: {state['plan'][state['current_step_idx']]}
                
                Rate 1-10 and provide feedback:
                - Geometry accuracy
                - Material/color correctness
                - Spatial positioning
                - Overall quality
            """}
        ])
    ])
    
    # Parse vision feedback
    quality_score = extract_score(response.content)  # Regex: "Score: 7/10"
    state['quality_scores'][state['current_step_idx']] = quality_score
    state['vision_feedback'][state['current_step_idx']] = response.content
    
    # Determine refinement need (adaptive thresholds)
    is_critical_step = state['current_step_idx'] < 5  # First 5 steps are critical
    threshold = 7 if is_critical_step else 6
    
    state['needs_refinement'] = (
        quality_score < threshold and 
        state['refinement_attempts'][state['current_step_idx']] < 2
    )
    
    return state
```

**Example Vision Feedback**:
```
"The cone mesh is correctly positioned with proper height (5m) and base radius (1.5m).
However, the green material appears too dark (RGB [0.05, 0.2, 0.05] instead of [0.1, 0.4, 0.1]).
Geometry: 9/10, Materials: 5/10, Overall: Score: 6/10.
Recommendation: Adjust material color to be brighter."
```

### **Step 2c: Conditional Refinement**
```python
def _should_refine(self, state: AgentState) -> str:
    """Conditional edge: route to refine_step or evaluate_progress"""
    return "refine" if state['needs_refinement'] else "continue"

def _refine_step_node(self, state: AgentState) -> AgentState:
    """Node 6: Generate and execute improvement code"""
    refinement_prompt = f"""
    Step {state['current_step_idx']} scored {state['quality_scores'][state['current_step_idx']]}/10.
    Vision feedback: {state['vision_feedback'][state['current_step_idx']]}
    
    Generate MCP tool calls to fix the issues. Focus on:
    {parse_issues_from_feedback(state['vision_feedback'][state['current_step_idx']])}
    """
    
    response = self.llm_with_tools.invoke([
        SystemMessage("You are refining a 3D modeling step based on quality feedback."),
        HumanMessage(refinement_prompt)
    ])
    
    # Execute refinement tool calls
    for tool_call in response.tool_calls:
        self.mcp_connection.execute_tool(tool_call['name'], tool_call['args'])
    
    state['refinement_attempts'][state['current_step_idx']] += 1
    state['refinement_history'].append({
        'step': state['current_step_idx'],
        'attempt': state['refinement_attempts'][state['current_step_idx']],
        'feedback': state['vision_feedback'][state['current_step_idx']]
    })
    
    # Loop back to capture_feedback for re-assessment
    return state
```

**Refinement Loop Example**:
```
Step 2: Add green material
  ↓
Execute: create_material(color=[0.05, 0.2, 0.05])
  ↓
Capture Screenshot
  ↓
Vision Assessment: "Too dark, score 6/10"
  ↓
Refine: update_material(color=[0.1, 0.4, 0.1])
  ↓
Capture Screenshot (2nd time)
  ↓
Vision Assessment: "Correct brightness, score 8/10" → Continue
```

---

## **Phase 3: Progress Evaluation & Completion**
```python
def _evaluate_progress_node(self, state: AgentState) -> AgentState:
    """Node 7: Check if more steps remain"""
    state['current_step_idx'] += 1
    if state['current_step_idx'] < len(state['plan']):
        return state  # Continue to next step
    else:
        state['complete'] = True
        return state

def _complete_node(self, state: AgentState) -> AgentState:
    """Node 8: Final summary and save"""
    state['final_message'] = f"""
    Modeling complete! {len(state['plan'])} steps executed.
    Refinements: {sum(state['refinement_attempts'].values())} 
    Average quality: {sum(state['quality_scores'].values()) / len(state['quality_scores']):.1f}/10
    """
    self.mcp_connection.execute_tool("save_blend_file", {"path": "/workspace/output.blend"})
    return state
```

---

## **State Checkpointing & Recovery**
```python
# LangGraph MemorySaver for persistent state
checkpointer = MemorySaver()
graph = StateGraph(AgentState)
# ... add nodes and edges ...
agent = graph.compile(checkpointer=checkpointer)

# Invoke with thread_id for resumable sessions
result = agent.invoke(
    {"user_prompt": "Create Christmas tree"},
    config={"configurable": {"thread_id": "user_123_session_1"}}
)

# Resume after interruption (rate limit, crash, etc.)
result = agent.invoke(
    None,  # Resume from checkpoint
    config={"configurable": {"thread_id": "user_123_session_1"}}
)
```

---

## **Rate Limit Handling**
```python
def invoke_with_retry(self, messages, max_retries=3):
    """Exponential backoff for Anthropic rate limits"""
    for attempt in range(max_retries):
        try:
            return self.llm_with_tools.invoke(messages)
        except AnthropicRateLimitError as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            time.sleep(wait_time)
```
- Init script auto-enables addon and starts MCP on port 9876
- Fallback: manual enable via Preferences

## **Phase 2: Chat & Refinement Agents**
- Frontend integrates with backend chat endpoints
- Agents interact with MCP to perform Blender actions
- Long-running operations handled asynchronously with generous timeouts

## **Phase 3: Persistence & Volumes**
- EBS CSI provides persistent volumes for user data
- Pods restart without data loss; scenes/config remain intact

---

# **Operational Runbooks**

## **Scale Down / Up Nodes**
See `docs/EKS_NODEGROUP_RESTART_GUIDE.md`. Typical timings:
- Scale down: 2–3 minutes
- Scale up: nodes Ready in 30–60 seconds

## **Restart Deployments**
```powershell
kubectl rollout restart deployment/backend -n prompt2mesh
kubectl rollout restart deployment/frontend -n prompt2mesh
kubectl rollout restart deployment/postgres -n prompt2mesh
kubectl get pods -n prompt2mesh
```

## **Get Frontend URL**
```powershell
$frontendUrl = kubectl get svc frontend -n prompt2mesh -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
Write-Host "Application URL: http://${frontendUrl}:8501"
```

---

# **How It Works: End-to-End Flow**

## **1. User Login & Session Creation**
```
User → Streamlit Frontend → POST /auth/login
                                    ↓
                              FastAPI Backend
                                    ↓
                        K8sUserSessionManager.create_session()
                                    ↓
                   ┌────────────────┴────────────────┐
                   │  Creates 4 Kubernetes Resources │
                   └────────────────┬────────────────┘
                                    ↓
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
   1. Pod:                    2. Service:              3. Ingress:
   blender-{username}         blender-svc-{username}   blender-ingress-{username}
   - Blender 3.6+             - Type: ClusterIP        - Class: nginx
   - MCP Server (port 9876)   - Port 3000 → Pod 3000   - Host: blender-{username}.{IP}.nip.io
   - Web UI (port 3000)       - Selector: user label   - TLS: cert-manager + Let's Encrypt
   - Python 3.10                                        - WebSocket support
                                                        - Backend: Service port 3000
                                    │
                                    ▼
                        Returns: JWT token, MCP port,
                                 Blender UI URL (https://blender-{username}.{IP}.nip.io)
```

### **Per-User Ingress Creation Details**

**Step 1: Get Nginx Ingress Controller LoadBalancer IP**
```python
# K8sUserSessionManager.__init__()
def _get_ingress_controller_ip(self):
    """Fetch the external IP of nginx-ingress-controller LoadBalancer"""
    try:
        svc = self.core_v1.read_namespaced_service(
            name="ingress-nginx-controller",
            namespace="ingress-nginx"
        )
        if svc.status.load_balancer.ingress:
            hostname = svc.status.load_balancer.ingress[0].hostname
            # Resolve AWS LoadBalancer hostname to IP for nip.io
            import socket
            ip = socket.gethostbyname(hostname)
            logger.info(f"Ingress Controller IP: {ip}")
            return ip  # e.g., "52.70.123.45"
    except Exception as e:
        logger.warning(f"Could not get Ingress IP: {e}")
        return "127.0.0.1"  # Fallback
```

**Step 2: Create Per-User ClusterIP Service**
```python
def _create_service_manifest(self, username: str, user_id: int):
    """Create ClusterIP service to expose user's Blender pod internally"""
    service_name = f"blender-svc-{username}"
    
    return client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(
            name=service_name,
            namespace="prompt2mesh",
            labels={"app": "blender-mcp-service", "user": username}
        ),
        spec=client.V1ServiceSpec(
            type="ClusterIP",  # Internal only, exposed via Ingress
            selector={"app": "blender-mcp", "user": username},
            ports=[
                client.V1ServicePort(
                    name="blender-ui",
                    port=3000,           # Service port
                    target_port=3000,    # Pod port
                    protocol="TCP"
                )
            ]
        )
    )
```

**Step 3: Create Per-User Ingress with nip.io DNS**
```python
def _create_ingress_manifest(self, username: str, user_id: int, service_name: str):
    """Create Ingress with TLS for user's Blender UI"""
    
    # nip.io provides wildcard DNS without configuration
    # Format: blender-alice.52-70-123-45.nip.io → resolves to 52.70.123.45
    host = f"blender-{username}.{self.ingress_ip.replace('.', '-')}.nip.io"
    
    return client.V1Ingress(
        api_version="networking.k8s.io/v1",
        kind="Ingress",
        metadata=client.V1ObjectMeta(
            name=f"blender-ingress-{username}",
            namespace="prompt2mesh",
            labels={
                "app": "blender-mcp-ingress",
                "user": username,
                "user-id": str(user_id),
                "managed-by": "prompt2mesh"
            },
            annotations={
                # cert-manager automatically provisions TLS certificate
                "cert-manager.io/cluster-issuer": "letsencrypt-prod",
                
                # Nginx configuration for Blender web UI
                "nginx.ingress.kubernetes.io/backend-protocol": "HTTP",
                "nginx.ingress.kubernetes.io/websocket-services": service_name,  # Enable WebSockets
                "nginx.ingress.kubernetes.io/proxy-read-timeout": "3600",        # 1 hour
                "nginx.ingress.kubernetes.io/proxy-send-timeout": "3600",
            }
        ),
        spec=client.V1IngressSpec(
            ingress_class_name="nginx",
            tls=[
                client.V1IngressTLS(
                    hosts=[host],
                    secret_name=f"blender-{username}-tls"  # cert-manager creates this
                )
            ],
            rules=[
                client.V1IngressRule(
                    host=host,
                    http=client.V1HTTPIngressRuleValue(
                        paths=[
                            client.V1HTTPIngressPath(
                                path="/",
                                path_type="Prefix",
                                backend=client.V1IngressBackend(
                                    service=client.V1IngressServiceBackend(
                                        name=service_name,
                                        port=client.V1ServiceBackendPort(number=3000)
                                    )
                                )
                            )
                        ]
                    )
                )
            ]
        )
    )
```

**Step 4: Create Resources in Order**
```python
def create_user_session(self, user_id: int, username: str):
    """Create pod, service, and ingress for user"""
    
    # 1. Create Pod
    pod_manifest = self._create_pod_manifest(username, user_id, mcp_port, ui_port)
    pod = self.core_v1.create_namespaced_pod(
        namespace=self.namespace,
        body=pod_manifest
    )
    
    # 2. Create ClusterIP Service
    service_manifest = self._create_service_manifest(username, user_id)
    service = self.core_v1.create_namespaced_service(
        namespace=self.namespace,
        body=service_manifest
    )
    
    # 3. Create Ingress
    ingress_manifest = self._create_ingress_manifest(username, user_id, service_name)
    ingress = self.networking_v1.create_namespaced_ingress(
        namespace=self.namespace,
        body=ingress_manifest
    )
    
    # 4. Generate Blender UI URL
    ingress_host = f"blender-{username}.{self.ingress_ip.replace('.', '-')}.nip.io"
    blender_ui_url = f"https://{ingress_host}"
    
    return UserBlenderSession(
        user_id=user_id,
        username=username,
        blender_ui_url=blender_ui_url,  # e.g., https://blender-alice.52-70-123-45.nip.io
        mcp_port=mcp_port,
        external_ip=ingress_host
    )
```

**Traffic Flow**:
```
User Browser
    ↓
https://blender-alice.52-70-123-45.nip.io (DNS resolves to 52.70.123.45)
    ↓
AWS LoadBalancer (52.70.123.45) for ingress-nginx-controller
    ↓
Nginx Ingress Controller Pod (reads Ingress resource)
    ↓
Routes to: blender-svc-alice:3000 (ClusterIP Service)
    ↓
Service forwards to: blender-alice Pod port 3000
    ↓
Blender Web UI responds
```

**Why nip.io?**
- **No DNS Configuration Required**: `52-70-123-45.nip.io` automatically resolves to `52.70.123.45`
- **Wildcard Subdomains**: `*.52-70-123-45.nip.io` all resolve to same IP
- **Per-User Isolation**: Each user gets unique subdomain (e.g., `blender-alice`, `blender-bob`)
- **TLS/HTTPS**: cert-manager + Let's Encrypt provision certificates for each subdomain

**Alternative (Production)**: Replace nip.io with real domain:
```python
# Instead of: blender-alice.52-70-123-45.nip.io
# Use: blender-alice.prompt2mesh.example.com

# Requires:
# 1. DNS A record: *.prompt2mesh.example.com → 52.70.123.45
# 2. Update host in _create_ingress_manifest():
host = f"blender-{username}.prompt2mesh.example.com"
```

---

## **2. User Submits Prompt**
```
User Input: "Create a decorated Christmas tree"
         ↓
POST /chat → Backend → RefinementAgent.refine_prompt()
         ↓
Enhanced: "Create 3D conical evergreen tree (height 5m, base 1.5m), 
          add 20 sphere ornaments in red/gold/silver, star topper"
```

## **3. ArtisanAgent Execution (LangGraph Workflow)**

### **Step 3a: Analysis & Planning**
```python
# Node 1: analyze_scene
state = {
    "user_prompt": "Create 3D conical evergreen tree...",
    "scene_analysis": "Empty scene, no objects",
    "plan": [],
    "current_step_idx": 0
}
agent.invoke(state) → calls list_objects via MCP

# Node 2: plan
state["plan"] = [
    {"id": 1, "action": "create_cone", "params": {...}},
    {"id": 2, "action": "add_material", "params": {...}},
    {"id": 3, "action": "create_sphere", "params": {...}},
    # ... 5-12 steps total
]
```

### **Step 3b: Execution Loop (Nodes 3-7)**
For each step in plan:

```
┌─────────────────────────────────────────────────┐
│ Node 3: execute_step                            │
│ - LangChain llm.bind_tools(mcp_tools)           │
│ - Calls: create_mesh, add_material, etc.        │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ Node 4: capture_feedback                        │
│ - MCP tool: capture_viewport_screenshot         │
│ - Saves to: /tmp/step_{idx}.png                 │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ Node 5: assess_quality                          │
│ - Claude Sonnet 4.5 Vision analyzes screenshot  │
│ - Scores 1-10 on geometry, materials, position  │
│ - Determines: needs_refinement = (score < 6/7)  │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
         ┌───────┴───────┐
         │ Conditional   │
         │ Edge:         │
         │ _should_refine│
         └───────┬───────┘
                 │
       ┌─────────┴─────────┐
       │                   │
    score < 6         score ≥ 6
  (or < 7 if critical)     │
       │                   │
       ▼                   ▼
┌──────────────┐   ┌──────────────────┐
│ Node 6:      │   │ Node 7:          │
│ refine_step  │   │ evaluate_progress│
│              │   │                  │
│ - Generate   │   │ - Increment step │
│   improvement│   │   index          │
│   code       │   │ - Check if more  │
│ - Execute    │   │   steps remain   │
│   via MCP    │   └────────┬─────────┘
│ - Increment  │            │
│   refinement │            ▼
│   attempts   │    ┌────────────────┐
└──────┬───────┘    │ More steps?    │
       │            └───────┬────────┘
       │                    │
       │             ┌──────┴──────┐
       │             │             │
       │           YES           NO
       │             │             │
       │             ▼             ▼
       │      (Loop back)   ┌──────────┐
       │        to step 3   │ Node 8:  │
       │                    │ complete │
       │                    └──────────┘
       │
       └─────► (Loop back to capture_feedback for re-assessment)
               Max 2 refinement attempts per step
```

### **Step 3c: Example Refinement Loop**
```
Step 2: Add green material
  ↓
execute_step: create_material(color=[0.05, 0.2, 0.05])
  ↓
capture_feedback: screenshot_step_2_v1.png
  ↓
assess_quality:
  Vision AI: "Material too dark, expected brighter green. Score: 5/10"
  needs_refinement = True (5 < 6)
  ↓
refine_step:
  LLM generates: update_material(color=[0.1, 0.4, 0.1])
  Execute via MCP
  refinement_attempts[2] = 1
  ↓
capture_feedback: screenshot_step_2_v2.png
  ↓
assess_quality:
  Vision AI: "Material brightness correct, good contrast. Score: 8/10"
  needs_refinement = False (8 ≥ 6)
  ↓
evaluate_progress: Move to Step 3
```

## **4. State Persistence & Recovery**
```python
# LangGraph MemorySaver checkpointer
agent = graph.compile(checkpointer=MemorySaver())

# Invoke with thread_id
result = agent.invoke(
    state,
    config={"configurable": {"thread_id": "user_123_session_1"}}
)

# If rate limit or crash occurs:
# - State saved to checkpoint after each node
# - Resume with same thread_id
result = agent.invoke(
    None,  # Resume from last checkpoint
    config={"configurable": {"thread_id": "user_123_session_1"}}
)
```

## **5. Final Output**
```
Backend → Frontend:
{
  "status": "complete",
  "message": "Modeling complete! 8 steps executed, 3 refinements applied.",
  "quality_scores": [8, 8, 7, 9, 6, 8, 7, 9],
  "average_quality": 7.8,
  "blend_file": "/workspace/user_123/christmas_tree.blend",
  "final_screenshot": "/workspace/user_123/final_render.png"
}
```

---

# **Key Technical Achievements**

### **1. LangChain Tool Abstraction**
```python
from langchain_core.tools import StructuredTool

# Wrap MCP tools as LangChain StructuredTools
mcp_tools = [
    StructuredTool.from_function(
        func=lambda **kwargs: mcp_connection.call_tool("create_mesh", kwargs),
        name="create_mesh",
        description="Create a mesh primitive in Blender"
    ),
    # ... 15+ MCP tools wrapped
]

llm_with_tools = llm.bind_tools(mcp_tools)
```

### **2. LangGraph Multi-Agent Orchestration**
```python
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

# Define state schema
class AgentState(TypedDict):
    user_prompt: str
    scene_analysis: str
    plan: List[Dict]
    current_step_idx: int
    execution_history: List[Dict]
    quality_scores: Dict[int, float]
    vision_feedback: Dict[int, str]
    refinement_attempts: Dict[int, int]
    needs_refinement: bool
    complete: bool

# Build graph
graph = StateGraph(AgentState)
graph.add_node("analyze_scene", self._analyze_scene_node)
graph.add_node("plan", self._plan_node)
graph.add_node("execute_step", self._execute_step_node)
graph.add_node("capture_feedback", self._capture_feedback_node)
graph.add_node("assess_quality", self._assess_quality_node)
graph.add_node("refine_step", self._refine_step_node)
graph.add_node("evaluate_progress", self._evaluate_progress_node)
graph.add_node("complete", self._complete_node)

# Conditional edges
graph.add_conditional_edges(
    "assess_quality",
    self._should_refine,
    {"refine": "refine_step", "continue": "evaluate_progress"}
)

# Compile with checkpointing
agent = graph.compile(checkpointer=MemorySaver())
```

### **3. Vision-Based Quality Assessment**
```python
from langchain_anthropic import ChatAnthropic

vision_llm = ChatAnthropic(model="claude-sonnet-4-20250514")

# Multi-modal input: image + text
response = vision_llm.invoke([
    HumanMessage(content=[
        {
            "type": "image",
            "source": {
                "type": "base64",
                "data": base64_screenshot
            }
        },
        {
            "type": "text",
            "text": "Rate this 3D modeling step 1-10..."
        }
    ])
])

# Extract structured feedback
quality_score = parse_score(response.content)  # e.g., "Score: 7/10" → 7
```

### **4. Rate Limit Resilience**
```python
def invoke_with_retry(self, messages, max_retries=3):
    for attempt in range(max_retries):
        try:
            return self.llm_with_tools.invoke(messages)
        except AnthropicRateLimitError as e:
            if attempt == max_retries - 1:
                # Save checkpoint, return gracefully
                raise
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            time.sleep(wait_time)
```

---

# **Comparison to Traditional Approaches**

| Aspect | **Traditional Blender** | **NeRF/Diffusion Models** | **Prompt2Mesh** |
|:-------|:------------------------|:---------------------------|:----------------|
| **Input** | Manual UI + Python scripting | 2D images or text prompts | Natural language prompts |
| **Expertise Required** | High (3D modeling skills) | Low (prompt engineering) | Low (conversational) |
| **Output Editability** | Full control | Black-box mesh | Full Blender scene (.blend) |
| **Transparency** | Explicit operations | Opaque neural weights | Logged MCP tool calls + reasoning |
| **Quality Control** | Manual inspection | No feedback loop | Automated vision assessment + refinement |
| **Iterative Improvement** | Manual re-modeling | Re-train/re-generate | Autonomous refinement (max 2 per step) |
| **Multi-User Scalability** | Local installation only | Cloud APIs (no isolation) | Per-user Kubernetes pods |

---

### 404 on Blender UI (nip.io / nginx)
- Ensure per-user Ingress/Service has correct target
- Logout/login to recreate routes
- Verify `kubectl describe svc frontend -n prompt2mesh` and AWS LB controller

### Pods Pending
```powershell
kubectl describe pod <POD_NAME> -n prompt2mesh
# Wait for nodes Ready; check PV/PVC
kubectl get pv
kubectl get pvc -n prompt2mesh
```
If EBS CSI issues: restart driver:
```powershell
kubectl rollout restart deployment/ebs-csi-controller -n kube-system
```

### LoadBalancer Not Ready
```powershell
kubectl get svc frontend -n prompt2mesh
kubectl describe svc frontend -n prompt2mesh
```
Allow 1–3 minutes for hostname propagation.

---

# **Command Reference (Quick)**

| Action | Command |
| :---- | :---- |
| **Scale to 0** | `aws eks update-nodegroup-config --cluster-name prompt2mesh-cluster --nodegroup-name prompt2mesh-nodegroup --scaling-config minSize=0,maxSize=3,desiredSize=0 --region us-east-1` |
| **Scale to 2** | `aws eks update-nodegroup-config --cluster-name prompt2mesh-cluster --nodegroup-name prompt2mesh-nodegroup --scaling-config minSize=1,maxSize=3,desiredSize=2 --region us-east-1` |
| **Check nodes** | `kubectl get nodes` |
| **Restart all** | `kubectl rollout restart deployment/backend deployment/frontend deployment/postgres -n prompt2mesh` |
| **Frontend URL** | `kubectl get svc frontend -n prompt2mesh -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'` |

---

# **Conclusion**

Prompt2Mesh demonstrates a production-ready pattern for **autonomous 3D modeling with quality feedback loops**, combining:

1. **LangChain**: Structured tool abstraction over Blender MCP operations
2. **LangGraph**: Multi-agent workflow orchestration with state checkpointing
3. **Claude Sonnet 4.5 Vision**: Screenshot-based quality assessment driving iterative refinement
4. **Multi-User Cloud Infrastructure**: EKS-managed per-user isolation with persistent storage

**Key Innovations**:
- **Autonomous refinement**: Agent self-assesses quality and improves work without human intervention
- **Vision-based feedback**: Claude Vision analyzes 3D viewport screenshots to detect geometric/material issues
- **Resilient execution**: State checkpointing enables resume after rate limits or failures
- **Scalable multi-user**: Kubernetes orchestration with per-user pod isolation

**Achieved Proposal Requirements**:
- ✅ LangChain + LangGraph multi-agent architecture
- ✅ Autonomous planning and execution via MCP tools
- ✅ Iterative refinement with quality thresholds
- ✅ Vision AI feedback loop (Claude Sonnet 4.5 Vision)
- ✅ Multi-user backend with FastAPI + JWT auth
- ✅ Streamlit frontend for user interaction
- ✅ Cloud deployment on AWS EKS with ECR, LoadBalancer, persistent volumes

This system bridges the gap between **natural language understanding** and **procedural 3D modeling**, making Blender accessible to non-experts while maintaining full transparency and editability of outputs.

**Next Steps**:
- Expand MCP tool library (modifiers, physics simulations, rendering)
- Multi-agent collaboration (specialized agents for modeling, texturing, lighting)
- Human-in-the-loop checkpoints for critical decisions
- Advanced quality metrics (mesh topology, UV unwrapping quality)

---

# **References & Further Reading**

- **LangChain Documentation**: https://python.langchain.com/docs/
- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **Anthropic Claude API**: https://docs.anthropic.com/claude/docs
- **Model Context Protocol (MCP)**: https://modelcontextprotocol.io/
- **Blender Python API**: https://docs.blender.org/api/current/
- **Project Documentation**:
  - `docs/REFINEMENT_LOOP_ARCHITECTURE.md`: Detailed refinement loop implementation
  - `docs/MULTI_USER_ARCHITECTURE.md`: Multi-user session management
  - `docs/ARCHITECTURE.md`: System architecture overview
  - `src/artisan_agent/artisan_agent.py`: LangGraph agent implementation (1300+ lines)

---

**Document Version**: 2.0  
**Last Updated**: January 2025  
**Authors**: Prompt2Mesh Development Team  
**License**: See LICENSE file in repository root
