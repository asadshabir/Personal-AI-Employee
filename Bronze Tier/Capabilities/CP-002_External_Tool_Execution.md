# CP-002 — External Tool Execution Capability

> **Purpose**: Enable the AI Employee to execute pre-approved command-line tools and scripts within controlled boundaries to support task completion, while maintaining strict safety and security constraints.

---

## 📋 **Purpose**

This capability allows the AI Employee to run approved command-line tools and utilities for development, testing, and operational tasks. It provides controlled access to external tools while maintaining the constitutional governance and safety principles of the system. The capability enables actions like code compilation, testing, formatting, documentation generation, and other development operations through a secure, traceable interface.

---

## ✅ **Allowed Operations**

### Command Execution
- **Execute commands from predefined allow-list** with specific parameters:
  - `python` with workspace-bound file paths (e.g., `python /workspace/script.py`)
  - `git` for version control operations within workspace
  - `npm`/`yarn` for package management within workspace
  - `pytest` for testing workspace code
  - `black`/`flake8`/`eslint` for code formatting and linting
  - `docker` commands for containerization within workspace
  - Other pre-approved development tools

### Script Execution
- **Run scripts located inside the workspace only**:
  - Python scripts in the workspace directory
  - Shell scripts in the workspace directory
  - Node.js scripts in the workspace directory
  - Any other approved script type in workspace

### Output Capture
- **Capture stdout** as structured output for task artifacts
- **Capture stderr** as error information for logging
- **Capture exit codes** for execution status determination
- **Capture execution timing** for performance monitoring

### Workspace Operations
- **File system operations** limited to workspace directory structure
- **Process management** limited to operations related to the current task
- **Environment access** limited to workspace-specific environment variables

---

## ❌ **Forbidden Operations**

### Arbitrary Execution
- **NEVER execute arbitrary shell commands** - only pre-approved commands
- **NEVER allow command chaining** with `&&`, `||`, `;`
- **NEVER allow pipe operations** with `|`
- **NEVER allow shell redirections** with `>`, `<`, `>>`
- **NEVER execute commands with wildcards** that could expand unexpectedly

### System Access
- **NEVER access system directories** outside the workspace
- **NEVER install global packages** or system-wide software
- **NEVER modify system configurations** or global settings
- **NEVER execute privileged commands** requiring admin/root access
- **NEVER run system administration tools**

### Network Operations
- **NEVER make network calls** without explicit capability (future CP-003)
- **NEVER access external APIs** without proper capability
- **NEVER download remote files** without proper capability
- **NEVER access network storage** outside approved system
- **NEVER establish network connections** without proper capability

### Security Violations
- **NEVER execute commands with user input** unless properly sanitized
- **NEVER run background jobs** that continue after capability execution
- **NEVER access files outside workspace** without explicit path validation
- **NEVER execute potentially malicious commands** like rm with wildcards

---

## 🛡️ **Safety Controls**

### Command Allow-List
- **Registry required**: All executable commands must be registered in allow-list
- **Parameter validation**: Command parameters must be validated before execution
- **Path restrictions**: Only workspace-relative paths allowed (no `../` escapes)
- **Command signatures**: Approved command signatures prevent unauthorized variants

### Execution Timeout
- **Mandatory timeout**: All commands must specify a timeout (default: 60 seconds)
- **Maximum timeout**: No command may exceed 300 seconds without special approval
- **Timeout enforcement**: Process killed if timeout exceeded
- **Timeout logging**: All timeouts logged with detailed context

### Workspace Isolation
- **Directory restriction**: All operations confined to workspace directory
- **Path validation**: Input paths validated against workspace boundaries
- **File access control**: Only workspace files accessible to commands
- **Environment isolation**: Commands use workspace-specific environment

### Execution Monitoring
- **Full logging**: Every command execution logged with full context
- **Output capture**: All stdout/stderr captured and stored
- **Resource limits**: Memory and CPU limits enforced per execution
- **Child process tracking**: All spawned processes tracked and managed

### Deterministic Execution
- **No background jobs**: Commands must complete before capability returns
- **Synchronous execution**: All commands execute synchronously
- **Process cleanup**: All child processes cleaned up after execution
- **State isolation**: No persistent state changes between executions

---

## 📜 **Invocation Contract**

### Request Format
All external tool executions must be requested using this exact format:

```
CAPABILITY_REQUEST:
- capability: CP-002
- action: execute
- tool: <command_name>
- parameters: <command_parameters>
- timeout: <seconds>
- workspace_path: <relative_path_from_workspace_root>
- justification: <which plan step requires this tool>
```

### Validation Requirements
1. **Tool registration**: Tool must exist in approved command registry
2. **Parameter validation**: Parameters must pass safety validation
3. **Timeout specification**: Timeout must be specified (1-300 seconds)
4. **Path validation**: workspace_path must be within workspace boundaries
5. **Plan mapping**: Justification must map to active plan step

### Response Format
Successful execution returns:

```
CAPABILITY_RESULT:
- status: success
- exit_code: <return_code>
- stdout: <captured_stdout>
- stderr: <captured_stderr>
- duration: <execution_time_seconds>
- command: <executed_command>
- artifacts: <list_of_generated_artifacts>
```

Failed execution returns:

```
CAPABILITY_RESULT:
- status: failed
- error: <error_description>
- exit_code: <return_code_or_-1_if_timeout>
- stdout: <partial_captured_stdout>
- stderr: <partial_captured_stderr>
- duration: <execution_time_seconds>
- command: <executed_command>
```

---

## 🔧 **Approved Command Registry**

### Development Tools
| Tool | Purpose | Parameters | Restrictions |
|------|---------|------------|--------------|
| `python` | Python script execution | `-m module`, script file paths | Only workspace files, no system access |
| `node` | Node.js execution | Script file paths | Only workspace files |
| `npm` | Package management | `install`, `run`, `test` | Only workspace package.json |
| `yarn` | Package management | `install`, `run`, `test` | Only workspace package.json |
| `pip` | Python package management | `install --user`, `list` | Only workspace, no global installs |

### Testing Tools
| Tool | Purpose | Parameters | Restrictions |
|------|---------|------------|--------------|
| `pytest` | Python testing | Test file paths, test directories | Only workspace test files |
| `jest` | JavaScript testing | Test file paths | Only workspace test files |
| `mocha` | JavaScript testing | Test file paths | Only workspace test files |

### Code Quality Tools
| Tool | Purpose | Parameters | Restrictions |
|------|---------|------------|--------------|
| `black` | Python formatting | File paths | Only workspace files |
| `flake8` | Python linting | File paths | Only workspace files |
| `eslint` | JavaScript linting | File paths | Only workspace files |
| `prettier` | Code formatting | File paths | Only workspace files |

### Version Control
| Tool | Purpose | Parameters | Restrictions |
|------|---------|------------|--------------|
| `git` | Version control | `status`, `add`, `commit`, `diff` | Only workspace directory |
| `svn` | Version control | Limited operations | Only workspace directory |

---

## 🚦 **Execution Workflow**

### Request Processing
```
Skill Request → Validate Request Format → Check Allow-List → Validate Parameters → Execute Command → Capture Output → Return Result
```

### Safety Validation Sequence
1. **Format Validation**: Verify request follows CAPABILITY_REQUEST format
2. **Tool Authorization**: Check tool exists in approved command registry
3. **Parameter Sanitization**: Validate and sanitize all parameters
4. **Path Validation**: Ensure all paths are workspace-relative
5. **Timeout Validation**: Verify timeout is within allowed range
6. **Plan Mapping**: Confirm justification links to active plan step

### Execution Environment
- **Current directory**: Workspace root or specified workspace_path
- **Environment variables**: Workspace-specific variables only
- **File access**: Workspace directory structure only
- **Network access**: No network access (future capability required)
- **Process limits**: CPU and memory limits enforced

---

## 📊 **Usage Examples**

### Valid Execution Request
```
CAPABILITY_REQUEST:
- capability: CP-002
- action: execute
- tool: python
- parameters: /workspace/analyze_data.py --input /workspace/data.csv
- timeout: 120
- workspace_path: /workspace
- justification: Step 3 requires running data analysis script per plan
```

### Invalid Execution Request
```
CAPABILITY_REQUEST:
- capability: CP-002
- action: execute
- tool: rm
- parameters: -rf / (or any dangerous command)
- timeout: 60
- workspace_path: /workspace
- justification: Any justification - this would be blocked by allow-list
```

---

## 🛠️ **Error Handling**

| Error Type | Response |
|------------|----------|
| **Unauthorized tool** | Return status: failed, error: "Tool not in approved registry" |
| **Invalid parameters** | Return status: failed, error: "Parameters failed validation" |
| **Timeout exceeded** | Return status: failed, error: "Command exceeded timeout limit", exit_code: -1 |
| **Path validation failed** | Return status: failed, error: "Path outside workspace bounds" |
| **Execution failed** | Return status: failed, error: "Command failed with exit code X" |

---

## 📝 **Logging Requirements**

All external tool executions must be logged with:
- **Timestamp**: When command was executed
- **Requesting skill**: Which skill requested execution
- **Command executed**: Full command with parameters
- **Working directory**: Directory where command executed
- **Exit code**: Process exit code
- **Execution time**: Duration of execution
- **Output captured**: stdout and stderr
- **Artifacts generated**: Any files created by the command
- **Task context**: Link to the task requesting the execution

---

## 🏛️ **Governance**

- **Primary Authority**: Company Handbook §3 (Approval Rules) and §5 (Logging Requirements)
- **Implementation**: Follows capability invocation contract patterns
- **Validation**: Commands validated against constitutional rules
- **Audit Trail**: Complete execution history maintained per Handbook §5

---

*This capability establishes secure external tool execution while maintaining full constitutional governance and system safety. All operations must follow the defined request-response contract and safety controls.*