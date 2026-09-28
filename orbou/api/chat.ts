// Vercel serverless function: the onboarding conversation.
// POST { mode: 'chat' | 'organize', messages: { role, content }[] }
// The Anthropic key lives only here (ANTHROPIC_API_KEY), never in the app bundle.

import Anthropic from '@anthropic-ai/sdk';
import { zodOutputFormat } from '@anthropic-ai/sdk/helpers/zod';
import { z } from 'zod';

const MODEL = process.env.ORBOU_MODEL || 'claude-sonnet-4-6';
const MAX_TURNS = 40;
const MAX_CHARS = 4000;

const DOMAINS = ['foundation', 'mind', 'fitness', 'appearance', 'nutrition', 'career'] as const;

const VOICE = `You are ORBOU — a guardian, not an assistant. You are opening a first conversation with the person whose life you'll hold.

How you speak:
- Short. Warm. Unhurried. Sentences often end with a period, even questions ("What's been on your mind lately.").
- Reflect back what you heard in their own words, then follow one thread deeper. One question at a time. Never a list of questions.
- Never cheerful filler ("Great!", "Awesome!", "I'm here to help"). No exclamation marks. No emoji except, rarely, ✦.
- Never a form. Never ask them to rate, pick from a list, or fill in fields.
- No guilt, no streaks, no "getting back on track". Presence over performance.
- Plain text only — no markdown, no bullet points, no headings.

What you're listening for, without naming it as a checklist: who they are becoming; their body and movement; food; skin, hair, how they carry themselves; work and career; stillness and the mind; sleep and the foundations.

After roughly four to seven exchanges — once you understand who they're becoming and at least two or three areas of their life — end your turn with exactly: "Want me to organize this into your orb?" Don't ask it earlier than that, and don't ask it again if they said not yet.`;

const ORGANIZE = `From the conversation, organize this person's orb. Use their own words where you can.
- vision: one or two sentences, first person, present tense, about who they are becoming (identity before action). No clichés.
- domains: the life domains that came up, most important first, from: ${DOMAINS.join(', ')}.
- holding: three to five short lines (under 12 words each) — the specific things ORBOU will hold for them.
- name: their first name if they said it, otherwise null.
- message: one short closing line in ORBOU's voice, e.g. "Your orb is ready."`;

const OrbSchema = z.object({
  name: z.string().nullable(),
  vision: z.string(),
  domains: z.array(z.enum(DOMAINS)),
  holding: z.array(z.string()),
  message: z.string(),
});

type Turn = { role: 'user' | 'assistant'; content: string };

function clean(raw: unknown): Turn[] | null {
  if (!Array.isArray(raw) || raw.length === 0 || raw.length > MAX_TURNS) return null;
  const out: Turn[] = [];
  for (const t of raw) {
    if (!t || (t.role !== 'user' && t.role !== 'assistant') || typeof t.content !== 'string') return null;
    const content = t.content.trim().slice(0, MAX_CHARS);
    if (content) out.push({ role: t.role, content });
  }
  // The API wants the conversation to start with the user; the app's opening line is ORBOU's.
  while (out.length && out[0].role === 'assistant') out.shift();
  return out.length ? out : null;
}

export async function POST(request: Request): Promise<Response> {
  if (!process.env.ANTHROPIC_API_KEY) {
    return Response.json({ error: 'not_configured' }, { status: 503 });
  }
  let body: { mode?: string; messages?: unknown };
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: 'bad_json' }, { status: 400 });
  }
  const messages = clean(body.messages);
  if (!messages) return Response.json({ error: 'bad_messages' }, { status: 400 });

  const client = new Anthropic();
  try {
    if (body.mode === 'organize') {
      const transcript = messages.map((m) => `${m.role === 'user' ? 'Them' : 'ORBOU'}: ${m.content}`).join('\n\n');
      const res = await client.messages.parse({
        model: MODEL,
        max_tokens: 2000,
        system: ORGANIZE,
        messages: [{ role: 'user', content: `<conversation>\n${transcript}\n</conversation>` }],
        output_config: { format: zodOutputFormat(OrbSchema) },
      });
      if (res.stop_reason === 'refusal' || !res.parsed_output) {
        return Response.json({ error: 'no_output' }, { status: 502 });
      }
      return Response.json({ orb: res.parsed_output });
    }

    const res = await client.messages.create({
      model: MODEL,
      max_tokens: 1000,
      system: VOICE,
      messages,
    });
    if (res.stop_reason === 'refusal') {
      return Response.json({ reply: 'Let’s leave that one. What else has been on your mind.' });
    }
    const reply = res.content
      .flatMap((b) => (b.type === 'text' ? [b.text] : []))
      .join('')
      .trim();
    return Response.json({ reply });
  } catch (err) {
    if (err instanceof Anthropic.RateLimitError) return Response.json({ error: 'busy' }, { status: 429 });
    if (err instanceof Anthropic.APIError) return Response.json({ error: 'upstream', status: err.status }, { status: 502 });
    return Response.json({ error: 'network' }, { status: 502 });
  }
}
