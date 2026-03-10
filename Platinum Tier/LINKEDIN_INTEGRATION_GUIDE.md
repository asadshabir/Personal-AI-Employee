# 📋 LinkedIn Integration Guide for AI Employee

## 🎯 **Overview**

This guide explains how to set up LinkedIn API access for the AI Employee's Platinum Tier LinkedIn integration feature. The system allows drafting and posting professional content to LinkedIn with constitutional governance and approval workflows.

---

## 🔐 **Getting LinkedIn API Access**

### **Step 1: Create a LinkedIn Developer Account**
1. Go to [https://developer.linkedin.com/](https://developer.linkedin.com/)
2. Sign in with your LinkedIn account
3. Accept the terms and conditions

### **Step 2: Create a New Application**
1. Click on "Create app" in the top-right corner
2. Fill in the application details:
   - **Application name**: AI Employee LinkedIn Integration
   - **Application logo**: Upload a logo (optional)
   - **Description**: AI Employee system for professional social media management
   - **Website URL**: Your website or placeholder URL
   - **Authorized redirect URLs**: `http://localhost:3000` (for development)

### **Step 3: Configure OAuth 2.0 Settings**
1. In your app's "Auth" tab:
   - Under "Default OAuth 2.0 scopes", add:
     - `w_member_social` - Write member social actions
     - `r_liteprofile` - View basic profile information
     - `r_emailaddress` - View email address (optional)
     - `w_orgsocial` - Write organization social actions (if posting to company page)

### **Step 4: Get Your Credentials**
1. Go to the "Products" tab of your app
2. Set up "Share on LinkedIn" product if not already enabled
3. Note down:
   - **Client ID**: Found in "Auth" tab under "Client ID"
   - **Client Secret**: Found in "Auth" tab under "Client Secret"

### **Step 5: Generate Access Tokens**
1. Use OAuth 2.0 flow to get your access token:
   - Go to: `https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URL&scope=w_member_social,r_liteprofile`
   - Authorize the application in your browser
   - Capture the authorization code from the redirect URL
   - Exchange the code for tokens using LinkedIn's token endpoint

---

## 📁 **Configuration Files**

### **Environment Variables (.env)**
The `.env` file contains your LinkedIn credentials:

```
LINKEDIN_CLIENT_ID=your_linkedin_client_id_here
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret_here
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token_here
LINKEDIN_REFRESH_TOKEN=your_linkedin_refresh_token_here
LINKEDIN_PERSONAL_ACCESS_TOKEN=your_personal_access_token_here
```

### **Configuration Setup**
1. Copy the `.env` template provided with the AI Employee system
2. Replace placeholder values with your actual LinkedIn credentials
3. Store the file securely and never commit to version control

---

## 🏗️ **System Architecture**

### **Directory Structure**
```
📁 Platinum Tier/
├── linkedin_mcp.py          # LinkedIn MCP server
├── Skills/
│   └── SKILL-LINKEDIN-POST.md  # LinkedIn skill definition
├── LINKEDIN_INTEGRATION_GUIDE.md  # This guide
└── README.md
├── 📁 Pending_Approval/     # Posts awaiting approval
└── 📁 Done/                 # Completed post logs
```

### **Processing Flow**
```
1. Task → SK-LINKEDIN-POST-001 skill
2. → Validate content and format
3. → Create draft in Pending_Approval/ directory
4. → Awaiting human approval
5. → If approved → Post via LinkedIn API
6. → Log results to Done/ directory
```

---

## 🛠️ **MCP Server Configuration**

### **mcp.json Entry**
```json
{
  "servers": [
    {
      "name": "linkedin",
      "command": "python",
      "args": ["Platinum Tier/linkedin_mcp.py"]
    }
  ]
}
```

### **LinkedIn MCP Server Features**
- **Draft Creation**: Creates pending approval files instead of direct posting
- **API Integration**: Uses LinkedIn API v2 for posting
- **Content Validation**: Ensures constitutional compliance
- **Image Support**: Handles image uploads when provided
- **Error Handling**: Comprehensive error management
- **Audit Logging**: Complete audit trail for all operations

---

## 🧠 **Skill Configuration**

### **SKILL-LINKEDIN-POST-001 Features**
- **Skill ID**: SK-LINKEDIN-POST-001
- **Tier**: 2 (requires approval for posting)
- **Trigger**: Tasks requiring LinkedIn social media content
- **Inputs**:
  - `text`: Post content
  - `image_url`: Optional image URL
  - `title`: Draft file title
- **Output**: Draft file in Pending_Approval/ directory

---

## 🚀 **Usage Example**

### **Task for Claude**:
```
"Draft and post LinkedIn update about new Odoo feature after approval."
```

### **Expected Flow**:
1. AI Employee recognizes LinkedIn posting requirement
2. Calls SK-LINKEDIN-POST-001 skill
3. Skill validates content for constitutional compliance
4. Creates draft post in Pending_Approval/LINKEDIN_POST_DRAFT_*.md
5. Human reviews and approves the draft
6. MCP server posts content to LinkedIn
7. Success logged in Done/LINKEDIN_POST_LOG_*.md

---

## 🛡️ **Constitutional Compliance**

### **Governance Rules**
- **No Direct Posting**: All LinkedIn posts require human approval
- **Content Validation**: Posts must comply with constitutional principles
- **Privacy Protection**: No sensitive information in posts
- **Professional Tone**: Maintains professional LinkedIn presence
- **Audit Trail**: Complete logs of all LinkedIn operations

### **Safety Mechanisms**
- Drafts stored in Pending_Approval directory before posting
- Content validation against constitutional rules
- Human oversight for all external communications
- Comprehensive error handling and recovery

---

## 🧪 **Testing the Integration**

### **Basic Test**:
```bash
python test_linkedin_integration.py
```

### **Expected Behavior**:
- MCP server initializes with LinkedIn credentials
- Creates test draft in Pending_Approval directory
- Validates constitutional compliance
- Provides success/failure feedback

---

## 🚨 **Troubleshooting**

### **Common Issues**:
1. **"LinkedIn access token not found"**: Missing or incorrect .env configuration
2. **API permission errors**: Insufficient OAuth scopes
3. **Connection failures**: Network or LinkedIn API issues
4. **Content rejection**: Posts violating LinkedIn's content policy

### **Solutions**:
- Verify all environment variables are set
- Check OAuth scopes match requirements
- Test LinkedIn API access separately
- Review content for policy compliance

---

## 📞 **Support**

For technical issues with LinkedIn integration:
- Check the logs in the `/Logs` directory
- Verify configuration in `.env` file
- Ensure LinkedIn app has proper permissions
- Consult LinkedIn developer documentation

---

<div align="center">

> 🚀 **"Professional Social Media Automation with Constitutional Governance"**
> LinkedIn integration for the Platinum Tier AI Employee system

</div>