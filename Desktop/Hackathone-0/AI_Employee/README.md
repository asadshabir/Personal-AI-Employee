# AI Employee - Advanced Automation Dashboard

<div align="center">

[![AI Employee Dashboard](https://img.shields.io/badge/Live%20Demo-Deployed-green?style=for-the-badge&logo=vercel)](https://ai-employee-asadshbair.vercel.app)
[![Next.js](https://img.shields.io/badge/Next.js-16.1.6-000000?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/)

*A revolutionary AI-powered automation dashboard that manages WhatsApp, Gmail, and LinkedIn with stunning visualizations and intuitive controls.*

</div>

## 🚀 Live Demo

**[✨ Visit AI Employee Dashboard](https://ai-employee-asadshbair.vercel.app)**

## 🌟 Features

### 🎨 Stunning Visual Design
- **Glassmorphism UI** - Modern glass-like transparency effects with backdrop filters
- **3D Globe Visualization** - Interactive CSS-powered globe showing activity
- **Smooth Animations** - Custom keyframe animations and transitions
- **Service-specific Theming** - Color-coded systems for WhatsApp, Gmail, LinkedIn

### 📊 Real-time Dashboard
- **Live Status Updates** - Auto-refreshing every 10 seconds
- **Activity Metrics** - Track messages, emails, and posts in real-time
- **Performance Charts** - Beautiful bar charts and data visualization
- **Approval Tracking** - Pending approvals and queue management

### 🔧 Multi-Platform Integration
- **WhatsApp Automation** - Automated messaging and response handling
- **Gmail Integration** - Email automation and management
- **LinkedIn Posts** - Social media automation
- **Approval System** - Human oversight for AI decisions

## 🛠️ Tech Stack

### Frontend
- **Next.js 16.1.6** - Modern React framework with Turbopack
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **CSS Animations** - Custom keyframe animations
- **Responsive Design** - Mobile-first approach

### Backend
- **FastAPI** - High-performance Python API framework
- **Python 3.x** - Backend logic and AI integration
- **uvicorn** - ASGI server

### Deployment
- **Vercel** - Frontend deployment
- **Docker** - Containerization (optional)

## 🎯 Dashboard Overview

### 📊 Main Dashboard
The central hub displaying:
- **Service Cards** - WhatsApp, Gmail, LinkedIn with real-time status
- **3D Globe** - Visual representation of global activity
- **Summary Stats** - Total actions, pending approvals, queue status
- **Activity Feed** - Recent events and logs

### 📋 Approvals Page
- **Review Queue** - AI-drafted messages requiring approval
- **Service-specific Cards** - Visual distinction between platforms
- **Quick Actions** - One-click approval/rejection
- **Real-time Updates** - Auto-refreshing pending items

### 🔐 Secure Authentication
- **Password Protection** - Secure access control
- **Token-based Auth** - JWT implementation
- **Session Management** - Secure cookie handling

## 🎨 Design Highlights

### Glassmorphism Effects
```css
.glass {
  background: rgba(12, 24, 40, 0.35);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 229, 255, 0.1);
}
```

### 3D Globe Animation
- Multiple rotating rings with gradient borders
- Pulsating dots with individual animations
- 3D perspective and rotation effects
- Smooth floating animations

### Interactive Elements
- Hover effects with glow and shadow changes
- Smooth transitions and micro-animations
- Typing indicators during loading
- Service-specific color coding

## 🚀 Getting Started

### Prerequisites
- Node.js 16.x or higher
- Python 3.8 or higher
- npm or yarn package manager

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/asadshabir/Personal-AI-Employee.git
cd Personal-AI-Employee
```

2. **Install frontend dependencies**
```bash
cd frontend
npm install
```

3. **Set up environment variables**
```bash
# Create .env.local in the frontend directory
NEXT_PUBLIC_API_URL=http://localhost:8000
DASHBOARD_PASSWORD=your_secure_password
```

4. **Start the frontend development server**
```bash
npm run dev
# Frontend will be available at http://localhost:3000
```

5. **Start the backend server**
```bash
# In a separate terminal
cd backend  # or wherever your FastAPI app is located
uvicorn api_server:app --reload --port 8000
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | Yes |
| `DASHBOARD_PASSWORD` | Secure password for dashboard access | Yes |

## 🔧 Configuration

### Customizing the UI
The dashboard supports extensive customization through CSS variables in `globals.css`:

```css
:root {
  --bg: #060d18;          /* Dark background */
  --accent: #00e5ff;      /* Primary accent color */
  --accent-gradient: linear-gradient(135deg, #00e5ff 0%, #7b2fff 100%);
  --text: #cce8f4;        /* Primary text */
  --border: rgba(0, 200, 255, 0.12);
}
```

## 🚀 Deployment

### Vercel Deployment
1. Link your repository to Vercel
2. Set environment variables in Vercel dashboard
3. Deploy automatically on git push

### Docker Deployment
```bash
# Build the frontend
docker build -t ai-employee-frontend .
docker run -p 3000:3000 ai-employee-frontend
```

## 📊 API Endpoints

### Frontend API Calls
- `GET /api/status` - Get real-time service status
- `GET /api/stats` - Get statistics and metrics
- `GET /api/logs/all` - Get activity logs
- `POST /api/auth/login` - Authentication
- `GET /api/pending` - Get pending approvals
- `POST /api/approve/:filename` - Approve content
- `DELETE /api/pending/:filename` - Reject content

## 🤖 AI Capabilities

### Automated Actions
- **WhatsApp**: Automated messaging and responses
- **Gmail**: Email composition and sending
- **LinkedIn**: Post creation and publishing
- **Approval Workflow**: Human oversight for AI decisions

### Intelligence Features
- Natural language processing
- Context-aware responses
- Smart scheduling
- Quality assurance checks

## 📈 Performance

### Optimizations
- Efficient state management with React hooks
- Optimized API calls with caching
- Lazy loading for components
- Tree shaking for smaller bundles

### Monitoring
- Real-time metrics
- Performance tracking
- Error logging
- Uptime monitoring

## 🛡️ Security

- Password-protected access
- Secure token handling
- Input validation
- Rate limiting
- Secure API communications

## 📱 Responsive Design

The dashboard is fully responsive and works on:
- Desktop computers
- Tablets
- Mobile devices
- Various screen sizes

## 📚 Advanced Features

### Real-time Updates
- WebSocket connections (if implemented)
- Live data streaming
- Auto-refreshing metrics
- Push notifications

### Analytics
- Usage statistics
- Performance metrics
- User engagement data
- Action tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support, please open an issue in the GitHub repository or contact the maintainers.

---

<div align="center">

**AI Employee Dashboard** - *Transforming automation with stunning visuals and intelligent workflows*

[✨ Visit Live Demo](https://ai-employee-asadshbair.vercel.app) | [📄 License](LICENSE)

</div>