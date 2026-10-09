# UI/UX Pro Max × VAIXLNS Design Intelligence Office v1

**Status:** SPECIFIED / skill installation and local execution not verified  
**Canonical owner:** VAIXLNS  
**Design routing office:** Ω.DESIGN  
**Implementation and validation:** VX  
**Independent assurance:** ARC-X / independent reviewers  
**Upstream:** https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

## 1. Purpose

Use UI/UX Pro Max as an optional design-intelligence skill in the VAIXLNS Prompt Office pipeline. Its upstream repository describes design-system generation and recommendations across UI styles, palettes, typography, UX guidance, chart patterns and multiple front-end/mobile stacks. The upstream manifest observed during this integration identifies version 2.13.0; pin and re-check the actual installed version before each evaluation. This is an observed upstream value, not a claim that it is installed here.

## 2. Installation routes

For Claude Code, the upstream repository documents these marketplace commands:

```text
/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill
/plugin install ui-ux-pro-max@ui-ux-pro-max-skill
```

The upstream project also documents CLI initialization:

```bash
npx ui-ux-pro-max-cli init --ai claude
```

Use the documented installer for the intended host; do not manually copy internal skill folders or assume commands from one host work in another. After installation, verify the skill is actually available and invoke it in a test session. Record the installed version, generated files, command output and exit code. The routing registry remains `NOT_VERIFIED` until those checks pass.

Official upstream source: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill

## 3. Ω.DESIGN workflow

1. **Intake:** identify product domain, target audience, user needs, platforms, current codebase/stack, brand constraints, accessibility requirements and existing design contracts.
2. **Reference research:** consult permitted references (for example, Pinterest/Dribbble), preserving URLs and attribution; extract abstract patterns rather than clone an individual design.
3. **Design-system proposal:** invoke the available UI/UX Pro Max skill/generator; save its output as a candidate, not a canonical truth.
4. **Comparative reasoning:** have VX architecture and independent design reviewers assess at least relevant trade-offs: clarity, task completion, responsive behaviour, accessibility, consistency, implementation cost, maintainability and visual differentiation.
5. **Prototype/implementation:** implement only on an isolated feature branch and within the approved scope. Reuse existing project stack and components where appropriate rather than introducing unnecessary dependencies.
6. **Validation:** inspect multiple screen sizes, keyboard operation, focus states, contrast, labels, errors/empty/loading/success states and core user journeys. Run applicable automated checks plus manual review.
7. **Learning:** record the design-system version, prompt, tokens, changes, test evidence, reviewer findings and user feedback. Create a new version for improvements; retain previous versions and rollback references.

## 4. Design-system persistence policy

Use a master-plus-overrides model only where it fits the target project's architecture:

- A proposed global system defines color tokens, typography, spacing, layout, motion, components, interaction rules and accessibility constraints.
- Page-specific files declare only intentional deviations from the approved global system.
- Preserve the prior system and provenance. Never silently replace brand identity or historical design decisions.
- Generate a new version/branch and a review diff; canonical adoption requires the relevant approval and tests.
- A skill's own checklist is not equivalent to independent ARC-X verification.

Suggested artifact locations for projects that adopt this layout:

```text
design-system/
  MASTER.md
  pages/
    <page-name>.md
```

Choose the target repository's canonical location only after inspecting its existing structure.

## 5. Routing contract

The `UIUX_DESIGN_SYSTEM` route in `config/office_skill_routing.v1.json` selects Ω.DESIGN roles and requires:
- a user/product brief and target stack;
- generated design-system candidate and rationale;
- tokens/components/layout guidance;
- accessibility, responsiveness and anti-pattern review;
- upstream skill/version/source manifest;
- a diff and explicit approval before canonical persistence.

If the skill is missing, do not fabricate its output; return `NOT_CONFIGURED` or `HOLD` and provide the exact installation/verification next step.

## 6. Status boundaries

- `SPECIFIED`: this integration contract and routing metadata exist.
- `NOT_VERIFIED`: the active host has not shown that the skill is installed and invoked successfully.
- `PARTIAL`: some design artifacts exist but required checks or approvals are incomplete.
- `VERIFIED`: only a narrowly stated claim backed by reproducible generated artifact, environment/version evidence, applicable test results and independent review.

This document does not claim that UI/UX Pro Max has been installed into Claude, Cursor, VS Code or this runtime.
