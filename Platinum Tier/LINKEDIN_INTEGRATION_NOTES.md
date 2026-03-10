# LinkedIn Integration - Playwright Implementation Notes

## 🎯 **Overview**
The LinkedIn integration uses Playwright browser automation instead of API keys, providing a robust way to create and publish LinkedIn posts while maintaining constitutional governance requirements.

## 🏗️ **Architecture**

### **Directory Structure**
```
📁 Platinum Tier/
├── linkedin_mcp.py               # Main MCP server with Playwright automation
├── linkedin_session/            # Persistent browser session storage
│   └── storage_state.json       # Saved login cookies and session data
├── Skills/
│   └── SKILL-LINKEDIN-POST.md   # Skill definition
├── TEST_LINKEDIN_TASK_EXAMPLE.md # Example task file
├── LINKEDIN_INTEGRATION_NOTES.md # This file
└── dashboard_screenshot.png     # Example image (optional)
📁 Pending_Approval/             # Posts awaiting approval
📁 Done/                         # Successful post logs
📁 Logs/                         # Action logs and error screenshots
└── linkedin_actions.log         # Timestamped LinkedIn actions
```

## 🚀 **Setup Process**

### **Step 1: Install Dependencies**
```bash
pip install playwright
playwright install chromium
```

### **Step 2: First-Time Session Setup**
```bash
python "Platinum Tier/linkedin_mcp.py" --setup
```
- Browser will open automatically
- Log in to LinkedIn with your credentials
- Close the browser after successful login
- Session will be saved for future use

### **Step 3: Normal Operation**
```bash
python "Platinum Tier/linkedin_mcp.py"
```

## ⚙️ **Workflow**

### **Draft Creation Flow**
1. Task triggers SK-LINKEDIN-POST-001 skill
2. Skill validates content and format
3. Creates draft in `/Pending_Approval/LINKEDIN_POST_APPROVAL_REQUIRED_*.md`
4. Draft awaits human approval

### **Approval & Publishing Flow**
1. Human reviews and approves draft
2. Draft moved to `/Approved` directory (or status updated)
3. MCP server detects approved content
4. Playwright automates LinkedIn posting:
   - Navigates to LinkedIn feed
   - Fills content in the post textbox
   - Uploads image if provided
   - Clicks Post button
5. Success logged in `/Done/LINKEDIN_POST_LOG_*.md`

## 🛡️ **Constitutional Compliance**

### **Governance Features**
- **No Direct Posting**: All posts require human approval
- **Session Persistence**: Browser session saved between runs
- **Error Recovery**: 2 retry attempts with screenshot on failure
- **Complete Audit Trail**: All actions logged with timestamps
- **Browser Isolation**: Separate persistent context for LinkedIn

### **Safety Mechanisms**
- Drafts stored in Pending_Approval before posting
- Content validation against constitutional rules
- Human oversight for all external communications
- Session state verification before operations
- Screenshot capture on errors for debugging

## 🔧 **Technical Implementation Details**

### **Playwright Features Used**
- Persistent browser context with saved session
- Automatic retry logic for network issues
- Dynamic selector detection for LinkedIn UI changes
- File upload handling for images
- Screenshot capture on failure

### **Error Handling**
- **Timeout Errors**: Retry with backoff
- **Authentication Errors**: Session refresh process
- **UI Selector Errors**: Multiple selector strategies
- **File Upload Errors**: Alternative upload methods
- **Screenshot Capture**: On all failures for debugging

### **Selectors Used**
- Post textbox: `textarea[aria-label="What do you want to talk about?"]`
- Alternative post textbox: `div[contenteditable="true"][data-placeholder="What do you want to talk about?"]`
- Post button: `button[aria-label="Post"]`
- Image upload: `button[aria-label="Add photos/videos"]`
- Alternative image upload: `button[aria-label="Add visual media"]`

## 🧪 **Testing**

### **Test Task Example**
The file `TEST_LINKEDIN_TASK_EXAMPLE.md` demonstrates how to structure a LinkedIn posting task.

### **Verification Steps**
1. Create a test task in Inbox directory
2. Verify draft appears in Pending_Approval
3. Manually approve by moving to Approved directory
4. Confirm post appears on LinkedIn
5. Check success log in Done directory

## 📋 **Run Commands**

### **First-Time Setup**
```bash
python "Platinum Tier/linkedin_mcp.py" --setup
```

### **Normal Operation**
```bash
python "Platinum Tier/linkedin_mcp.py"
```

### **MCP Integration**
The LinkedIn server is configured in `mcp.json` and will be automatically available to the AI Employee system.

## 🚨 **Important Notes**

### **Session Management**
- Session is automatically saved after login
- Session remains valid until LinkedIn cookies expire
- If login expires, run setup command again

### **Browser Automation**
- Browser runs in non-headless mode (visible) by default
- This allows for human intervention if needed
- Can be changed to headless in code if desired

### **Image Handling**
- Supports any image format supported by LinkedIn
- Image path must be accessible from the system
- Upload happens during posting, not during draft creation

### **Constitutional Requirement**
- The system enforces human approval before any LinkedIn posting
- This is a hard requirement that cannot be bypassed
- All posts must follow constitutional governance rules

## 🔄 **Monitoring & Maintenance**

### **Log Files**
- `/Logs/linkedin_actions.log` - All LinkedIn-related actions
- `/Logs/linkedin_error_*.png` - Screenshots on failures
- `/Done/LINKEDIN_POST_LOG_*.md` - Successful post records

### **Troubleshooting**
- If authentication fails, run setup command again
- If selectors fail, LinkedIn UI may have changed - update selectors
- If posting fails, check for LinkedIn posting restrictions
- All errors are logged with timestamps for review

---

<div align="center">

> 🚀 **"Browser Automation for Professional Social Media with Constitutional Governance"**
> LinkedIn integration using Playwright with required human approval workflows

</div>