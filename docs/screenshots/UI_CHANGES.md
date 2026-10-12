# Look and feel pass (step 12)

Before: `before/*.png`. After: the screenshots in this folder.

No new features. What changed:

- **First screen explains itself.** A one-line intro above the Sessions tab says what Lucidity does and that
  the `e12` chips open the log line a claim came from.
- **Every box has a one-line "what is this".** Needs you, Runaway spend, Stalled, the done checker verdict
  and Heads up each say where they come from (a plain-code rule, the checker running tests, or the triage agent).
- **Each tab opens with one line** saying what it shows (How it decided, Planner replay, Evals).
- **Empty states say what to do.** First load: "Reading your sessions…" with how long it takes (20 to 40 seconds). Local mode with
  no sessions: where it looked and how to get some. Sample mode with no data: how to rebuild it. No refresh yet
  on the flow tab: press Refresh. When nothing needs you, a green "Nothing needs you" box replaces the orange one.
- **"All sessions (n)" heading** separates the needs-you summary from the cards.
- **Contrast.** The primary button's text is dark on the light-blue accent in dark mode (it was white on light
  blue). Disabled buttons look disabled.
- **Narrow screens.** Under 640px the cost meter drops to its own row under the tabs. Checked at a real
  390px viewport (`sessions_phone.png`): no sideways scrolling. (`before/sessions_phone.png` looks clipped
  because of a headless-browser minimum window width, not the page.)
- Light and dark themes both checked (`sessions_light.png`, `sessions.png`).
