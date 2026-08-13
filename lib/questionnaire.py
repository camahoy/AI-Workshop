"""Read-only content for the 'N = Everyone' tab: the draft AI Perceptions &
Workflow Assessment questionnaire, shown for reference during the live
session (not fielded in-app — it's a longer, piped/randomized instrument
meant for a real survey platform, with skip logic and tool names still
TBD). Sourced from questionnaire/AI-Perceptions-Questionnaire-Draft.docx.
"""

TITLE = "N = Everyone"
SUBTITLE = "AI Perceptions & Workflow Assessment — Draft Questionnaire, v0.1"
PURPOSE = (
    "Measures current AI usage, tool effectiveness, and workflow-level automation "
    "potential across the organization, and identifies concrete, prioritized inputs "
    "for the AI strategy roadmap."
)
META = "Estimated length: 12–15 minutes · self-administered online · anonymous · service line and title captured for segmentation only."
RESPONDENT_INTRO = (
    "This survey asks about how you currently use AI tools in your work, what's working "
    "and what isn't, and where you'd want AI to show up differently. Your individual "
    "answers are not shared with your manager. Results are reported by service line and "
    "level, not by name. It should take about 12 to 15 minutes."
)
CLOSING_NOTE = (
    "Thank you for your time. Results will be shared in aggregate, and specific themes "
    "from open-ended responses will directly inform the AI strategy roadmap."
)

SECTIONS = [
    {
        "heading": "Section A. Classification",
        "note": "Used for segmentation only. Not used to identify individual respondents in reporting.",
        "items": [
            "A1. Which service line or division do you primarily work in?",
            "A2. What is your title or level?",
            "A3. How long have you worked at the company? (Less than 1 year / 1 to 3 years / 4 to 7 years / 8+ years)",
            "A4. Which region or market do you primarily support?",
        ],
    },
    {
        "heading": "Section B. Current AI Usage (behavioral)",
        "note": "Behavioral questions are asked before attitudinal questions, to anchor respondents in what they actually do, not what they think they should say.",
        "items": [
            "B1. Which of the following AI tools do you currently use for work, even occasionally? Select all that apply — company-provided Copilot, a personal ChatGPT/Claude/similar account used for work, an internal tool or agent built by your division, a third-party research platform with AI features, something else, or none of the above.",
            "B2. For each tool selected above, how often do you use it? (Daily / a few times a week / a few times a month / rarely)",
            "B3. Have you personally built, configured, or requested a custom AI tool, script, or agent for your own work or your team's use, beyond using an off-the-shelf tool as provided? (Yes / No)",
            "B3a. If yes — briefly describe what you built or requested.",
            "B3b. If yes — what does it do? (from the task bank, select all that apply)",
            "B3c. If yes — does anyone else on your team currently use what you built?",
            "B4. Are you aware of any AI tools or agents built by OTHER divisions or teams that you don't currently have access to, but think could be useful to you? (Yes / No / Not sure)",
        ],
    },
    {
        "heading": "Section C. Effectiveness of Current Tools",
        "items": [
            "C1. For each tool you currently use, how effective is it for your work? (1 = not at all effective, 5 = extremely effective)",
            "C2. What's the single biggest limitation of the AI tool or tools you currently use?",
            "C3. Overall, how would you rate the AI tools currently available to you, specifically for the kind of work you do? (1 = poor, does not fit how I actually work, 7 = excellent, well suited to my work)",
        ],
    },
    {
        "heading": "Section D. Workflow and Task-Level Assessment",
        "note": "Identifies where AI could realistically take on parts of the respondent's actual workflow, task by task, rather than asking about AI in the abstract.",
        "items": [
            "D1. Think about a typical week in your role. For each task type: do you spend meaningful time on it, could AI take it on (fully / AI drafts, I finish / not really), and how meaningful is this task to you personally? (1–5)",
            "D2. If you had a magic wand and could hand off any part of your workflow to AI tomorrow, with no limitations, what would it be, and why that specifically?",
            "D3. Is there a part of your workflow where you would NOT want AI involved, even if it were technically capable of doing it? What is it, and why?",
        ],
    },
    {
        "heading": "Section E. Trust and Readiness",
        "items": [
            "E1. How confident are you that AI-assisted output (drafts, summaries, tables) is accurate enough to use with only light review? (1 = not at all confident, 7 = extremely confident)",
            "E2. How much do you trust AI-assisted research findings compared to fully human-led research? (1 = not nearly as much, 7 = just as much)",
            "E3. How easy or hard is it currently to integrate AI into your day-to-day workflow? (1 = very hard, 7 = very easy)",
            "E4. Which best describes how you'd like AI to show up in your role going forward? (want to use it more / using it about the right amount / being asked to use it more than comfortable with / don't think it belongs in my role / not sure)",
            "E5. What would need to be true for you to trust AI more in your work?",
        ],
    },
    {
        "heading": "Section F. Organizational Voice and Priorities",
        "items": [
            "F1. Do you feel you have a say in how AI tools are selected and rolled out for your team? (1 = no say at all, 7 = full say)",
            "F2. Do you feel the AI tools currently provided are actually built for how your division works day to day? (1 = not at all, 7 = completely)",
            "F3. What's one thing leadership could fund or build that would make the biggest difference to your day-to-day work? (a direct input to roadmap prioritization)",
            "F4. If the company could only prioritize ONE of the following for AI investment over the next year, which should it be? Rank your top 3 — tools that make existing work faster, tools that improve quality/accuracy, client-facing AI capabilities, training and skill-building, governance/data security/clear rules, or none of these should be the priority right now.",
        ],
    },
    {
        "heading": "Section G. Closing",
        "items": [
            "G1. Is there anything else about AI in your work that this survey didn't ask about, but you think leadership should know?",
        ],
    },
]
