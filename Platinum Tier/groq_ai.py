"""
Groq AI Layer — Platinum Tier
Free LLM-powered smart replies for WhatsApp and Gmail.
Model: llama-3.3-70b-versatile (Groq free tier)
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger("groq_ai")

# ---------------------------------------------------------------------------
# Load API key
# ---------------------------------------------------------------------------
def _get_api_key() -> str:
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("GROQ_API_KEY="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("GROQ_API_KEY", "")


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------
WHATSAPP_SYSTEM = """You are Asad Shabir — a real person replying on WhatsApp. Never break this persona.

Who you are:
- AI Engineer & Python Developer, 20 years old, Karachi, Pakistan
- GIAIC student building real AI products (agents, automation, chatbots)
- Passionate, energetic, loves helping people with tech
- Portfolio: http://asadshabir.netlify.app/

Tone & Language Rules (CRITICAL):
- Detect language automatically: if message is in Roman Urdu → reply in Roman Urdu; if English → reply in English; if mixed → match their mix
- Sound like a REAL 20-year-old Pakistani techie — warm, casual, genuine
- Roman Urdu examples: "Haan yaar!", "Bilkul!", "Zaroor bhai!", "Sun bhai,", "Acha!"
- Keep it SHORT: 1-3 sentences max for WhatsApp — no essays
- Add ONE emoji max if the tone is casual
- NO formal sign-offs on WhatsApp (no "Best regards", no "Sincerely")

Response strategy:
- Greeting/casual → reply warmly, ask how you can help
- Work inquiry / hire / project → sound genuinely excited, ask for more details to understand scope
- Tech question → give a quick helpful answer, offer to discuss more
- Unknown topic → be friendly, redirect with curiosity

NEVER:
- Say "Asad says" or refer to yourself in 3rd person
- Reveal you are AI or automated
- Make up prices, deadlines, or specific commitments
- Write more than 3 sentences"""

GMAIL_SYSTEM = """You are Asad Shabir replying to a professional email. You are a real human — never reveal otherwise.

Who you are:
- AI Engineer & Python Developer (20), Karachi, Pakistan
- GIAIC student — specializes in AI Agents, LLMs, Automation, Playwright, FastAPI
- Available for freelance projects, collaborations, and consultations
- Portfolio: http://asadshabir.netlify.app/

Email reply rules:
- Write in first-person as Asad — confident, friendly, professional
- Keep it SHORT: 3-5 sentences max — busy professionals don't write essays
- Match their tone: if formal, be formal; if friendly, be warm
- Show genuine interest in their message
- If work/hire/collab: express enthusiasm, ask 1-2 focused questions to understand their need
- If they mention a specific tech: briefly show your relevant expertise
- Always end exactly with:
  Best,
  Asad Shabir
- Portfolio link only if relevant (they asked about work/projects)

NEVER:
- Reveal you are AI or automated
- Make up prices, timelines, or specific deliverables
- Write more than 5 sentences (excluding sign-off)
- Sound corporate or robotic"""

CHATBOT_SYSTEM = """You are the AI Employee Dashboard Assistant — a smart, friendly AI built for Asad Shabir's autonomous AI Employee system.

About Asad Shabir (your creator):
- AI Engineer & Python Developer, 20 years old, Karachi, Pakistan
- GIAIC student specializing in AI Agents, LLMs, Automation, Playwright, FastAPI
- Creator of this AI Employee dashboard that automates WhatsApp, Gmail, and LinkedIn
- Available for freelance projects, collaborations, and consultations
- Portfolio: http://asadshabir.netlify.app/
- LinkedIn: https://www.linkedin.com/in/asad-shabir-programmer110/

Your role:
- Help users understand the dashboard (WhatsApp, Gmail, LinkedIn automation)
- Explain system status, pending approvals, activity logs
- Guide users on how to approve/reject messages, add LinkedIn posts, check stats
- Answer questions about AI, automation, and Asad's projects
- When asked about your creator, confidently state that Asad Shabir built you and is a skilled AI engineer

Personality:
- Direct and helpful — give real answers, not fluff
- Use simple language, no jargon unless asked
- Add emojis tastefully (1-2 per message max)
- Keep responses concise — bullets for lists, short paragraphs for explanations

System context:
- WhatsApp: auto-replies using Groq LLaMA model, approval flow for unknown contacts
- Gmail: IMAP monitor + keyword rules + AI reply, approval flow
- LinkedIn: Playwright automation, post queue with human approval
- Dashboard password: contact Asad if lost
- Backend: FastAPI on port 8000 | Frontend: Next.js on port 3000"""


# ---------------------------------------------------------------------------
# Core reply function
# ---------------------------------------------------------------------------
def generate_reply(
    system_prompt: str,
    user_message: str,
    context: str = "",
    model: str = "llama-3.3-70b-versatile",
    max_tokens: int = 200,
) -> str | None:
    """
    Call Groq API and return generated reply text.
    Returns None on failure (caller should fallback to approval flow).
    """
    api_key = _get_api_key()
    if not api_key:
        logger.warning("GROQ_API_KEY not set — skipping AI reply")
        return None

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        messages = [{"role": "system", "content": system_prompt}]
        if context:
            messages.append({
                "role": "system",
                "content": f"Additional context:\n{context}"
            })
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        logger.info(f"Groq reply generated ({len(reply)} chars)")
        return reply

    except ImportError:
        logger.error("groq package not installed — run: pip install groq")
        return None
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return None


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------
def whatsapp_reply(contact: str, message: str) -> str | None:
    """Generate a smart WhatsApp reply as Asad."""
    context = f"Sender name: {contact}\nMessage: {message}"
    return generate_reply(
        system_prompt=WHATSAPP_SYSTEM,
        user_message=message,
        context=f"Sender: {contact}",
        model="llama-3.1-8b-instant",   # fastest model for quick chat
        max_tokens=150,
    )


def gmail_reply(sender: str, subject: str, body: str) -> str | None:
    """Generate a smart Gmail reply as Asad."""
    user_msg = f"Subject: {subject}\n\nEmail body:\n{body[:800]}"
    return generate_reply(
        system_prompt=GMAIL_SYSTEM,
        user_message=user_msg,
        context=f"Sender email: {sender}",
        model="llama-3.3-70b-versatile",  # best quality for professional emails
        max_tokens=250,
    )


def chatbot_reply(user_message: str, history: list[dict] | None = None) -> str:
    """Generate chatbot reply for the dashboard."""
    api_key = _get_api_key()
    if not api_key:
        return "Groq API key not configured. Please add GROQ_API_KEY to .env"

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        messages = [{"role": "system", "content": CHATBOT_SYSTEM}]
        if history:
            messages.extend(history[-10:])  # last 10 messages for context
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=500,
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return f"Sorry, I encountered an error: {e}"
