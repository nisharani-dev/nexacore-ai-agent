// mock_responses.js
// ---------------------------------------------------------------------------
// All fake data used while the real backend isn't ready.
// When Person 1's /chat endpoint is live, NOTHING in this file needs to change —
// just flip the flag in api.js.
//
// Shape every response follows:
// {
//   reply: string,
//   memory_used: boolean,
//   new_memories: Array<{ scope, type, text }> | null
// }
// ---------------------------------------------------------------------------

export const MOCK_PERSONAS = {
  // Person #1 — agent has seen nobody from this team before. Generic, cautious.
  person1: {
    label: "Person #1",
    description: "First ever Platform Eng onboarding — agent knows nothing team-specific yet",
    memories: [
      { scope: "company", type: "access",  text: "VPN setup required before anything else" },
      { scope: "company", type: "access",  text: "SSO via Okta — activate on Day 1" },
      { scope: "company", type: "access",  text: "Badge + HR portal (Workday) access" },
      { scope: "org",     type: "access",  text: "GitHub org invite — ping your manager" },
    ],
    responses: {
      greeting: {
        reply: "Hey! Welcome aboard. I'm Ramp — I'll help you navigate onboarding.\n\nI don't have much team-specific info for Platform Engineering yet, but here's what I know for everyone:\n\n• Set up VPN first — everything else depends on it\n• Activate your Okta SSO account\n• Get your badge via the HR portal (Workday)\n\nWhat do you need help with?",
        memory_used: false,
        new_memories: null,
      },
      aws: {
        reply: "AWS access — I don't have specific notes on Platform Engineering's process yet. Generally you'd raise an IT ticket.\n\nI'd suggest asking your manager or team lead how long it usually takes. Once you find out, I'll remember it for the next person.",
        memory_used: false,
        new_memories: {
          scope: "team", type: "blocker",
          text: "AWS access process unknown — flagged by first Platform Eng joiner",
        },
      },
      confluence: {
        reply: "For Confluence access, raise a ticket with IT. I don't have the specific spaces your team uses documented yet — your onboarding buddy should be able to share those.\n\nOnce you get them, let me know and I'll log it for the next person.",
        memory_used: false,
        new_memories: null,
      },
      jira: {
        reply: "Jira access — request a Jira Software license through IT. I don't have notes on which license tier Platform Engineering uses, so just ask IT for the default and your manager can correct it if needed.",
        memory_used: false,
        new_memories: {
          scope: "team", type: "exception",
          text: "Jira license tier for Platform Eng unknown — needs verification",
        },
      },
      stuck: {
        reply: "Hmm, I don't have a logged resolution for that blocker yet. Try reaching the general IT queue, or ask your manager to escalate.\n\nOnce this gets resolved, let me know how — I'll remember the fix for the next person who hits the same wall.",
        memory_used: false,
        new_memories: null,
      },
      default: {
        reply: "I'm still learning what Platform Engineering's onboarding looks like — I don't have much team-specific info yet. Your safest bet is to ask your manager or check the general company onboarding doc in Confluence.\n\nKeep asking me things though — everything you share helps me get better for the next person.",
        memory_used: false,
        new_memories: null,
      },
    },
  },

  // Person #10 — agent has seen 9 previous joiners. Precise, proactive, knows every edge case.
  person10: {
    label: "Person #10",
    description: "9 prior onboardings — agent knows 6 edge cases, exact sequences, contractor flows",
    memories: [
      { scope: "company",   type: "access",    text: "VPN setup required before anything else" },
      { scope: "company",   type: "access",    text: "SSO via Okta — activate on Day 1" },
      { scope: "company",   type: "access",    text: "Badge + HR portal (Workday) access" },
      { scope: "org",       type: "access",    text: "GitHub org invite — ping your manager" },
      { scope: "org",       type: "access",    text: "Jira Software — request via IT portal" },
      { scope: "team",      type: "access",    text: "Request 7 Confluence spaces in one ticket: platform-wiki, infra-runbooks, incident-reports, rfc-proposals, deploy-docs, okr-tracking, platform-onboarding" },
      { scope: "team",      type: "blocker",   text: "AWS access takes 5 days minimum — request on Day 1" },
      { scope: "team",      type: "ritual",    text: "Use #platform-onboarding-2024, NOT #general" },
      { scope: "team",      type: "exception", text: "Contractors get Jira Lite, not Standard — IT defaults to wrong one" },
      { scope: "team",      type: "exception", text: "Manager must approve Okta ticket before IT actions it" },
      { scope: "team",      type: "blocker",   text: "Okta blocks all SSO tools — do this before anything else" },
      { scope: "role",      type: "access",    text: "SDE interns: read-only on prod repos until Week 2 sign-off" },
    ],
    responses: {
      greeting: {
        reply: "Hey! I've helped 9 Platform Engineering joiners before you — here's what actually matters:\n\n• Request AWS access today — it takes 5 days minimum. Three people got blocked waiting on it\n• As a contractor, you need Jira Lite, not Standard — IT will give you the wrong one\n• Your manager needs to approve the Okta ticket before IT will action it\n• Join #platform-onboarding-2024, not #general — that channel is where the team actually is\n• Request all 7 Confluence spaces in one ticket, not individually (saves 3 days)\n\nWhat do you want to tackle first?",
        memory_used: true,
        new_memories: null,
      },
      aws: {
        reply: "AWS access for Platform Engineering — this consistently takes 5 days. Three previous joiners got blocked on it.\n\nDo this right now:\n1. Raise the AWS access IT ticket immediately\n2. Make sure your manager has approved your Okta ticket first — otherwise IT won't process the AWS request\n3. Set a Day 3 calendar reminder to follow up if you haven't heard back\n\nDon't wait until you 'need' AWS. You'll need it by Day 3.",
        memory_used: true,
        new_memories: null,
      },
      confluence: {
        reply: "You need exactly these 7 Confluence spaces for Platform Engineering:\n\nplatform-wiki · infra-runbooks · incident-reports · rfc-proposals · deploy-docs · okr-tracking · platform-onboarding\n\nRequest all 7 in one ticket — people who requested them individually waited an extra 3 days for IT to process each one. Just list all 7 in the description field.",
        memory_used: true,
        new_memories: null,
      },
      jira: {
        reply: "Jira for Platform Engineering — you need Jira Lite, not Standard. IT will automatically give you Standard, which costs the team budget unnecessarily and sometimes triggers an approval loop.\n\nWhen raising the ticket, explicitly write 'Jira Lite license' in the request. If they still give you Standard, just reply to the ticket and cite the team's license policy.",
        memory_used: true,
        new_memories: null,
      },
      stuck: {
        reply: "If an IT ticket has been sitting for more than 3 days, don't re-submit — that resets the queue.\n\nInstead: find the ticket in Jira Service Management, add a comment tagging @it-platform-lead (not the general queue). Previous joiners resolved blockers 2x faster this way.\n\nIf it's the Okta ticket specifically, your manager needs to approve it first — that's the most common reason IT doesn't action it.",
        memory_used: true,
        new_memories: null,
      },
      default: {
        reply: "Based on 9 previous Platform Engineering onboardings, most blockers come down to one of three things: Okta not approved by manager, AWS requested too late, or Jira license type being wrong.\n\nWhich one is it? I'll give you the exact fix.",
        memory_used: true,
        new_memories: null,
      },
    },
  },
};

// Team-specific memory overrides for multi-team demo
const TEAM_MEMORY_OVERRIDES = {
  fp_and_a: {
    person1: [
      { scope: "company", type: "access", text: "VPN + Okta required Day 1" },
      { scope: "org", type: "access", text: "NetSuite license via IT portal" },
    ],
    person10: [
      { scope: "company", type: "access", text: "VPN + Okta required Day 1" },
      { scope: "team", type: "access", text: "Anaplan model access: request FP&A workspace + sandbox" },
      { scope: "team", type: "blocker", text: "Pigment license takes 4 days — request on Day 1" },
      { scope: "team", type: "ritual", text: "Monthly close office hours: Tuesdays 2pm #fpna-close" },
    ],
  },
  data_platform: {
    person10: [
      { scope: "team", type: "access", text: "Databricks workspace: data-platform-prod + sandbox" },
      { scope: "team", type: "blocker", text: "Airflow DAG deploy access needs platform lead approval" },
    ],
  },
};

export function getPersonaMemories(personaMode, team) {
  const base = MOCK_PERSONAS[personaMode]?.memories ?? [];
  const override = TEAM_MEMORY_OVERRIDES[team]?.[personaMode];
  return override ? [...base.slice(0, 2), ...override] : base;
}

// classify user input into a response key
export function classifyMessage(text) {
  const t = text.toLowerCase();
  if (t.includes("hi") || t.includes("hello") || t.includes("start") || t.includes("help") || t.includes("begin")) return "greeting";
  if (t.includes("aws") || t.includes("amazon") || t.includes("cloud")) return "aws";
  if (t.includes("confluence") || t.includes("wiki") || t.includes("docs") || t.includes("documentation")) return "confluence";
  if (t.includes("jira") || t.includes("ticket") || t.includes("license")) return "jira";
  if (t.includes("stuck") || t.includes("blocked") || t.includes("pending") || t.includes("waiting") || t.includes("days")) return "stuck";
  return "default";
}
