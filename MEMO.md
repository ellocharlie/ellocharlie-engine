# ellocharlie: The Founding Memo

*April 2026*

---

## Why We're Building This

There's a specific kind of frustration you feel when a deal closes, the champagne pops in the Slack channel, and then — within 72 hours — the customer is already confused about what happens next. The sales team moves on. The onboarding doc lives in someone's Google Drive. The first support ticket comes in and lands in a completely different system than the one where the deal was closed. Three weeks later, the customer churns and everyone is surprised.

We've both watched this happen more times than we can count. At companies with tens of millions in revenue. At startups with five employees. At organizations with billions in assets and armies of consultants. The tooling problem is universal.

Nicholas built ShipHero from a sketch on a napkin to a warehouse management system trusted by thousands of e-commerce brands. He knows what it looks like when systems break under scale — not because of bad engineering, but because the tools that handle sales never talked to the tools that handle support, which never talked to the tools that tracked the customer's health. He spent years at Code and Theory building digital infrastructure for some of the most demanding clients in the world. He went inside the National Basketball Players Association and saw a different kind of organizational complexity — high-stakes relationships, public accountability, zero tolerance for dropped balls. At Packiyo, he built a modern WMS from scratch, and every decision came back to the same problem: the data lives in silos, and the people who need it most are the last to get it.

Cristine has been entangled with tech and fast-moving startups her entire career — from early work at IBM when it was *the* technology company to startups serving customers like Jeff Bezos in the final leg of building out their infrastructure. She saw, from the inside, how large organizations actually adopt technology — the politics, the inertia, the gap between what gets promised in a boardroom and what gets used by an actual human being at 2pm on a Tuesday. She spent years at the frontier of enterprise systems and early-stage companies, and what she learned is this: the last mile is everything. You can build the most sophisticated platform in the world and lose at the last mile — the moment when a real customer tries to get something done.

We've been in rooms where this was discussed as a technology problem. We've been in rooms where it was discussed as a process problem. We've been in rooms where consultants charged $500 an hour to explain why the CRM didn't talk to the helpdesk.

It's not a technology problem. It's an architecture decision that nobody had sufficient skin in the game to make correctly. Sales tools are built by people who care about closing deals. Support tools are built by people who care about tickets. Nobody was building the whole customer journey as a single, coherent system designed to serve the founders who are trying to do everything at once.

That's what ellocharlie is. It's the system we both wished we had at every company we worked for.

---

## What We Believe

### 1. CX is the CRM.

Support is not a department. It is not a cost center. It is not something you bolt on after the sale closes.

Customer experience is the product loop. The quality of your response to a support ticket is part of your sales motion, because unhappy customers don't refer other customers. The knowledge base your team maintains is part of your onboarding motion, because a customer who can find their own answers doesn't churn out of frustration. The onboarding workflow your team runs is part of your retention motion, because customers who reach value quickly stay.

Every system in ellocharlie is designed with this belief at its core. The CRM feeds the helpdesk. The helpdesk feeds the knowledge base. The knowledge base informs the product roadmap. The product roadmap comes back to the CRM. There is no break in the loop.

### 2. Human connection scales with AI, not despite it.

Five AI agents run our operations. Not because we're trying to replace human judgment — we're not. Because we want every conversation our customers have to be with a human who has full context, infinite patience, and zero distractions from repetitive work.

The AI handles the repetitive work so humans can focus on the irreplaceable work. This is the right way to think about it. When the CX Lead agent monitors every customer interaction and surfaces the ones that need human attention, it's not diminishing the human role. It's making sure the human shows up where it actually matters.

We believe every company, especially every startup, deserves to operate this way. The five-agent model isn't magic — it's discipline applied to operations. The same engineering rigor that makes software systems reliable, applied to the workflows that drive a company.

### 3. The tools should disappear.

The best software gets out of the way. You shouldn't think about your CRM. You should think about your customer.

When your CRM, helpdesk, docs, onboarding, and status page are the same system — when a customer's entire history, every ticket, every check-in, every open deal, every support interaction, lives in one place — context stops getting lost. The tool disappears and the customer appears. That's the experience we're building toward.

Every feature decision we make gets tested against a single question: does this make the customer feel seen, or does it make our team feel organized? Those are not the same thing. We optimize for the customer feeling seen.

### 4. Startups deserve enterprise-grade systems without enterprise-grade complexity.

The tools that large organizations use to manage customer relationships are powerful. They're also expensive, slow to deploy, require consultants to configure, and are fundamentally designed for companies with dedicated RevOps teams, IT departments, and training budgets.

The tools that startups can actually afford are simple, but they create the exact fragmentation problem we're solving. You end up duct-taping Notion, Linear, Intercom, HubSpot, Loom, Confluence, and a spreadsheet together and hoping nothing falls through the gap.

ellocharlie exists in the space between. Enterprise architecture, startup economics. Sophisticated enough to run a thousand-customer operation, simple enough to configure in a day.

### 5. Engineering discipline applies to everything — including how we treat customers.

Nicholas comes from a mechanical engineering background. The discipline that shapes how he thinks about systems — first principles, load testing, failure modes, graceful degradation — is the same discipline we apply to the customer relationship.

What happens when a customer's account goes quiet for two weeks? That's a failure mode. You should have a detection mechanism. What happens when a customer can't find an answer in the docs? That's a load-bearing gap. You should fix it before the next person hits it. What happens when onboarding goes sideways? You need a recovery path that doesn't require a human to notice the problem first.

Systems thinking for human relationships. This is what ellocharlie is built on.

---

## How We Work

We are two founders. Nicholas and Cristine.

We also have five agents.

**The CEO Agent** tracks strategy execution, monitors growth metrics, identifies drift between what we said we'd do and what we're actually doing, and flags decisions that need human judgment. It doesn't make decisions. It makes sure we're making the right ones.

**The CTO Agent** reviews every architecture decision, audits code quality, tracks technical debt, and ensures that what we're building today doesn't become a liability tomorrow. Twenty years of building digital systems has taught Nicholas exactly how technical debt accumulates — the CTO Agent is how we prevent it from silently accruing.

**The Growth Agent** produces content, manages the SEO strategy, analyzes acquisition channels, and runs the build-in-public pipeline. Three blog posts a week. Case studies. Open-source documentation. It works; we ship.

**The CX Lead Agent** monitors every customer interaction, tracks health scores, surfaces at-risk accounts, and ensures our 15-minute first-response SLA holds at every stage of growth. Cristine's background — that last-mile obsession — is encoded into the agent's logic.

**The Ops Agent** handles deploys, monitors infrastructure, manages incidents, and keeps the system running. The thing that should never page us at 3am because a deploy went wrong is the thing we've invested the most automation in.

These five agents plus two humans run ellocharlie. Not because we can't hire — but because we believe this is the right architecture for a company in 2026. The question isn't "when do we hire?" The question is "what does a human need to do here that an agent genuinely cannot?"

When the answer to that question is clear, we hire. Until then, we build.

The ethos here is simple: engineering discipline meets customer empathy. Every process we run — whether it's how we onboard a new customer or how we ship a new feature — is designed the way a good engineer designs a system. It has a clear input, a defined output, a failure mode, and a recovery path. And at every step, it's designed to make the customer feel like they're being taken care of by people who actually give a damn.

Because they are.

---

## Where We're Going

The $100 million target is not a vanity number. It's a measurement.

At $100M ARR, ellocharlie has helped somewhere between 10,000 and 15,000 startups stop losing customers to broken processes. That's the actual metric. Revenue is just how we know we got there.

Every startup that churns a customer because the handoff from sales to support was broken — that's a failure we could have prevented. Every founder who spends three hours on a Sunday trying to figure out why a customer went quiet — that's three hours we could have given back. Every team that loses a customer they never knew was at risk — those customers matter.

The vision for ellocharlie is not to become another enterprise software company that startups are vaguely aware of. It's to become the default operating system for the customer relationship at companies with 2 to 500 employees — the layer of infrastructure that founders stop thinking about because it just works.

We want to be the first thing a founder sets up when they get their first customer, and the last thing they'd ever consider replacing when they have their thousandth.

We'll know we're on track when founders start recommending ellocharlie the same way they recommend Stripe. Not because it's cool. Because you don't run a company without it.

---

## A Note on Building in Public

We're open-sourcing our agent infrastructure.

Not a sanitized showcase. The actual skills, the actual workflows, the actual content pipeline. The configuration we use to run our Growth Agent. The health-scoring logic in our CX Lead Agent. The prompts and feedback loops and edge cases we've worked through.

We're doing this for one reason: the best way to build trust with startups is to show them exactly how we work.

There's a secondary reason, which is honest: the developers who look at our open-source framework and understand what we've built are also the ones who become customers, contributors, and advocates. We're not hiding the engine. The engine is part of the product.

We also believe, genuinely, that the companies best positioned to build in 2026 are the ones who are transparent about how they build. The playbook for running a two-person company with the operational capacity of twenty is not a trade secret. It's a methodology. We'd rather share it and lead the conversation than protect it and watch someone else do it worse.

This memo is part of that commitment. It's real. It's true. And if you're a founder reading this wondering whether ellocharlie is what you need — know that we built this the same way we'd build it for you.

With empathy. With rigor. And with no tolerance for systems that let your customers fall through the cracks.

---

*Nicholas Daniel-Richards & Cristine*  
*Founders, ellocharlie*  
*New York, 2026*
