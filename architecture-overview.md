# AI Agent + Blender On-Demand Architecture

This is a fascinating architectural scenario because it mixes AI with state (Agents) with heavy, ephemeral computation (Blender) on demand.

For a platform with thousands of users, you can't have Blender instances always running. You also don't want the Agent (the logic/LLM) to live in the same container as Blender (the tool), because they would scale inefficiently.

Here's the detailed workflow, communication architecture, and strategic placement of MCP (Model Context Protocol).

## The Actors

**The Agent (The Brain)**: A lightweight process. Maintains the conversation, project context, and decides what to do.

**The MCP Server (The Interface)**: A lightweight server that translates standardized instructions into Blender Python commands.

**The Blender Instance (The Muscle)**: A heavy container (Docker/MicroVM) that only exists while rendering or editing.

## The Step-by-Step Workflow

Imagine the user requests: "Add a red cube and render the scene".

### 1. Intent and Decision (Control Plane)

- **Start**: The user sends the message.
- **Reasoning**: The Agent (using an LLM) analyzes the request. Determines it can't do it alone with text; it needs the `blender_tool`.
- **State Check**: The Agent verifies if a Blender instance already exists for this `project_id`.
  - **If NO**: The Agent calls the Infrastructure API (K8s/Knative).

### 2. The "Spin Up" (Infrastructure Plane)

- **Trigger**: An HTTP request is made to an internal URL like `http://blender-service-project-123.cluster.local`.
- **Interception**: Knative Activator receives the request. Sees there are 0 pods. Pauses the HTTP request.
- **Provisioning**: Knative orders Kubernetes to create the Pod.
  - Here's where the Kata/Firecracker magic happens: The isolated MicroVM spins up.
  - Inside, a container with Blender + MCP Server starts.
- **Ready**: In ~2 seconds, the pod is ready and the Activator lets the original request through.

### 3. MCP Connection (Communication Plane)

- **Handshake**: The Agent (MCP Client) connects to the newly created Pod's endpoint (MCP Server) via SSE (Server-Sent Events) or WebSockets.
- **List Tools**: The MCP Server tells the Agent: "Hello, I have these tools available: `add_object`, `render_frame`, `export_glb`".

### 4. Execution (Execution Plane)

- **Action 1**: The Agent sends a JSON-RPC: `{ "method": "add_object", "params": { "type": "cube", "color": "red" } }`.
  - **Translation**: The MCP Server (inside the pod) receives the JSON, executes an internal Blender Python script (`bpy.ops.mesh.primitive_cube_add()`) and returns "Success".
- **Action 2**: The Agent sends `{ "method": "render_frame" }`.
  - **Load**: The pod's CPU/GPU spikes to 100%. The Agent waits.
  - **Result**: The MCP Server returns the URL of the rendered image (which it uploaded to S3/MinIO internally) or the blob in base64.

### 5. Scale-to-Zero (Cleanup)

- **Completion**: The Agent tells the user: "Here's your render".
- **Wait Time**: The Agent no longer sends requests to the Blender Pod.
- **Shutdown**: After a configured period (e.g., 60 seconds) without receiving HTTP/RPC traffic, Knative detects inactivity.
- **Kill**: Sends the SIGTERM signal. The Blender pod and MicroVM are destroyed. Resources freed.

## Where Does MCP Live?

This is the critical part for making the design agnostic and decoupled.

MCP follows a Client-Server architecture:

### MCP Client (Lives in the Agent)

- It's part of your agent orchestrator (can be in a lightweight Node.js/Python pod or even a Lambda/Cloud Run function).
- Doesn't have Blender installed.
- Its job is only to know how to request things.

### MCP Server (Lives WITH Blender)

- This process must live inside the same container (or Pod) as Blender.
- **Why?** Because the MCP Server needs direct access to Blender's Python `bpy` module. They have to share the same memory space or local file system.
- The container you deploy in Knative is a Docker image containing:
  - Linux + Headless Blender + Python Script (MCP Server)

## The Communication

Since you're in a distributed environment (Cloud/K8s), you can't use stdio (standard input/output) which is normal in local MCP. You must use MCP over HTTP (SSE).

- **Transport**: HTTP/2 or Server-Sent Events (SSE).
- **Protocol**: JSON-RPC 2.0.
- **Flow**:
  - The Agent makes a POST to `/mcp/messages` to the Knative service.
  - If the service is "asleep", Knative wakes it up, routes the POST, and returns the response.

## Mental Architecture Diagram

```
[ USER ]
     |
     v
[ GATEWAY / API ]
     |
     v
[ AGENT ORCHESTRATOR (MCP Client) ] <--- Always "alive" or lightweight on-demand
     |  (Decides to use Blender)
     |
     |  1. HTTP Request (JSON-RPC)
     v
[ KNATIVE SERVING (Load Balancer) ]
     |
     |  2. Detects traffic -> Scales from 0 to 1
     |  3. Creates MicroVM (Kata/Firecracker)
     v
[ EPHEMERAL POD (Blender) ] =========================
|  [ MCP SERVER (Python script) ]                 |
|       ^                                         |
|       | (Local calls to bpy)                    |
|       v                                         |
|  [ BLENDER ENGINE (Headless) ]                  |
===================================================
     |
     | 4. Uploads result (Render)
     v
[ OBJECT STORAGE (S3/MinIO) ]
```

## Summary of the Agnostic Approach

To achieve this without tying yourself to AWS/Google:

1. **Package** Blender + MCP Server in a single Docker image.
2. **Deploy** it as a Knative Service.
3. **Configure** the Agent so that when it needs Blender, it simply "talks" to the Knative service URL.
4. The platform (K8s + Knative + Kata) takes care of turning it on when receiving the message and turning it off when finished, charging (or consuming resources) only for the seconds the render lasted.

## Key Benefits

- **Cost Efficiency**: Pay only for actual compute time (seconds of rendering)
- **Scalability**: Handle thousands of users without maintaining idle Blender instances
- **Isolation**: Each render runs in its own secure MicroVM
- **Cloud Agnostic**: Works on any Kubernetes cluster with Knative
- **Clean Separation**: Agent logic separate from heavy computation
