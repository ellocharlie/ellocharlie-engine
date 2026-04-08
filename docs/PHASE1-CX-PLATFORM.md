# Phase 1 Technical Specification: Pylon-like CX Layer
## ellocharlie — "Attio but better"

**Version:** 1.0  
**Date:** 2026-04-08  
**Author:** Architecture Team  
**Status:** Implementation-Ready Draft

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Database Schema (Drizzle ORM)](#2-database-schema-drizzle-orm)
3. [tRPC Router Definitions](#3-trpc-router-definitions)
4. [Channel Integration Architecture](#4-channel-integration-architecture)
5. [AI Agent Architecture](#5-ai-agent-architecture)
6. [Developer Platform (Phase 1 Foundations)](#6-developer-platform-phase-1-foundations)
7. [Implementation Roadmap](#7-implementation-roadmap)
8. [File Structure](#8-file-structure)

---

## 1. Architecture Overview

### 1.1 System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ellocharlie Platform                                │
│                                                                             │
│  ┌─────────────────────── INBOUND CHANNELS ───────────────────────────┐    │
│  │  Slack Connect │  Email (Resend) │  Live Chat │  Forms │  API/REST  │    │
│  └────────────────────────────┬────────────────────────────────────────┘    │
│                               │                                             │
│  ┌────────────────────────────▼────────────────────────────────────────┐    │
│  │                    CHANNEL GATEWAY (Hono edge)                       │    │
│  │   • Inbound normalization → canonical Message format                 │    │
│  │   • Auth validation (org-scoped API keys / webhooks)                 │    │
│  │   • Rate limiting + dedup                                            │    │
│  └────────────────────────────┬────────────────────────────────────────┘    │
│                               │                                             │
│  ┌────────────────────────────▼────────────────────────────────────────┐    │
│  │                    CONVERSATION ENGINE (tRPC)                        │    │
│  │   • Thread detection / dedup (email Message-ID, Slack thread ts)    │    │
│  │   • Contact + Company resolution (fuzzy email/domain match)         │    │
│  │   • Ticket auto-creation with smart defaults                        │    │
│  │   • SLA clock start                                                  │    │
│  └──────────┬─────────────────┬──────────────────┬──────────────────────┘    │
│             │                 │                  │                           │
│  ┌──────────▼──────┐  ┌──────▼───────┐  ┌───────▼─────────────────────┐    │
│  │   AI PIPELINE   │  │  CRM GRAPH   │  │    WORKFLOW ENGINE           │    │
│  │  ─────────────  │  │  ──────────  │  │  ─────────────────────────   │    │
│  │  • Triage       │  │  Contacts    │  │  • Trigger evaluation        │    │
│  │  • Routing      │  │  Companies   │  │  • Step execution            │    │
│  │  • Draft reply  │  │  Deals       │  │  • Action dispatch           │    │
│  │  • Classify     │  │  Activities  │  │  • Run history               │    │
│  │  • KB gaps      │  │  Signals     │  │                              │    │
│  │  • Health score │  │              │  │                              │    │
│  └──────────┬──────┘  └──────┬───────┘  └───────┬─────────────────────┘    │
│             │                │                   │                          │
│  ┌──────────▼────────────────▼───────────────────▼──────────────────────┐   │
│  │                       NEON POSTGRES (Drizzle ORM)                     │   │
│  │  conversations │ messages │ tickets │ channels │ kb_articles           │   │
│  │  account_health_scores │ feature_requests │ workflows │ ai_actions      │   │
│  │  (all tables scoped to organizationId)                                │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────── NEXT.JS 15 FRONTEND ──────────────────────────────────────┐   │
│  │  /inbox (unified)  /tickets  /knowledge  /accounts  /workflows        │   │
│  │  TanStack Query v5 + tRPC client + Tiptap + Radix UI                  │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘

EXTERNAL:
  Clerk (Auth/Org) ──────────────────────→ organizationId on every request
  Resend (Email) ─────────────────────────→ inbound webhooks + outbound SMTP
  Cloudflare R2 (Storage) ────────────────→ attachment blobs
  Stripe (Billing) ───────────────────────→ plan gating on channel limits
  OpenAI / Anthropic ─────────────────────→ AI pipeline (abstracted behind lib/ai/)
```

### 1.2 CX ↔ CRM Integration Points

The fundamental design principle: **CX and CRM share a single data model.** There is no sync layer. A ticket is attached to the same `contacts` and `companies` rows that sales uses.

```
contacts ──────────┬──→ conversations (contact is the customer)
                   ├──→ tickets       (ticket belongs to contact)
                   └──→ account_activities (unified feed)

companies ─────────┬──→ account_health_scores
                   ├──→ feature_requests (company context)
                   └──→ account_signals

deals ─────────────┬──→ conversations (deal context surfaced in inbox)
                   ├──→ account_health_scores (deal status is a signal)
                   └──→ ai_actions (context assembly includes deal stage)
```

**Bi-directional enrichment flow:**
- New inbound message → resolve contact by email → attach conversation to contact record
- Ticket resolution → write `account_activity` → visible in contact timeline
- Feature request mention → auto-link to feature_request cluster → visible in deal notes
- Health score recomputed → surfaced in CRM contact view as "support health" badge

### 1.3 Channel Architecture

```
                     CHANNEL GATEWAY
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    PUSH channels    PULL channels    EMBEDDED
    (webhooks in)    (polling)        channels
         │                │                │
    ┌────┴────┐      ┌────┴────┐     ┌─────┴────┐
    │  Email  │      │  Slack  │     │   Chat   │
    │ (Resend │      │(Events  │     │ (Widget  │
    │ inbound │      │   API)  │     │   SDK)   │
    │webhook) │      └─────────┘     └──────────┘
    └─────────┘
    ┌─────────┐      ┌─────────┐     ┌──────────┐
    │  Forms  │      │  Teams  │     │   API    │
    │(submit  │      │(future) │     │  (REST)  │
    │ handler)│      └─────────┘     └──────────┘
    └─────────┘

All channels normalize to: CanonicalMessage {
  channelType, externalId, threadId?,
  fromAddress, fromName, subject?,
  body (plain + html), attachments[],
  metadata (channel-specific)
}
```

**Channel normalization contract** (`lib/channels/types.ts`):
```typescript
export interface CanonicalMessage {
  channelType: ChannelType;        // 'email' | 'slack' | 'chat' | 'form' | 'api'
  externalId: string;              // channel-native ID (email Message-ID, Slack ts, etc.)
  externalThreadId?: string;       // for threading (email References header, Slack thread_ts)
  from: { address: string; name?: string };
  to?: { address: string; name?: string }[];
  subject?: string;
  bodyText: string;
  bodyHtml?: string;
  attachments?: CanonicalAttachment[];
  metadata: Record<string, unknown>; // channel-specific extras
  receivedAt: Date;
}

export interface CanonicalAttachment {
  filename: string;
  mimeType: string;
  size: number;
  storageKey: string; // R2 key after upload
}
```

### 1.4 AI Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI ORCHESTRATOR                       │
│              (lib/ai/orchestrator.ts)                    │
│                                                          │
│  Incoming message                                        │
│       │                                                  │
│       ▼                                                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │           CONTEXT ASSEMBLER                      │    │
│  │   Pulls from: conversation history, contact      │    │
│  │   record, company record, deal stage, open       │    │
│  │   tickets, KB articles (semantic search),        │    │
│  │   account health, previous AI drafts             │    │
│  └─────────────────────┬───────────────────────────┘    │
│                         │                                │
│          ┌──────────────┼──────────────┐                │
│          ▼              ▼              ▼                │
│   ┌──────────┐  ┌──────────────┐ ┌──────────────┐     │
│   │ TRIAGE   │  │  DRAFT REPLY │ │  CATEGORIZE  │     │
│   │ classify │  │  tone-match  │ │  topic tags  │     │
│   │ priority │  │  KB-grounded │ │  product area│     │
│   │ route-to │  │  cite source │ │  sentiment   │     │
│   └────┬─────┘  └──────┬───────┘ └──────┬───────┘     │
│        │               │                │              │
│        ▼               ▼                ▼              │
│   ┌─────────────────────────────────────────────────┐  │
│   │              AI ACTIONS LOG                      │  │
│   │  Every AI inference stored: model, prompt,       │  │
│   │  tokens, latency, outcome, human-overridden?     │  │
│   └─────────────────────────────────────────────────┘  │
│                                                          │
│  Background jobs (Hono scheduled handlers):             │
│  • Knowledge gap detection (daily scan)                  │
│  • Health score recomputation (hourly)                   │
│  • Feature request clustering (on ticket close)          │
└─────────────────────────────────────────────────────────┘
```

**AI provider abstraction** (`lib/ai/provider.ts`): single interface over OpenAI/Anthropic, swappable per org config. All calls include `organizationId` for usage tracking.

---

## 2. Database Schema (Drizzle ORM)

All schemas live in `shared/schema/`. Each file exports the Drizzle table, a Zod insert schema, a Zod select schema, and TypeScript inferred types.

### 2.0 Shared Utilities (`shared/schema/_utils.ts`)

```typescript
import { createId } from "@paralleldrive/cuid2";
import { timestamp, text } from "drizzle-orm/pg-core";

export const cuid = () => text("id").primaryKey().$defaultFn(() => createId());

export const timestamps = {
  createdAt: timestamp("created_at", { withTimezone: true })
    .notNull()
    .defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true })
    .notNull()
    .defaultNow()
    .$onUpdateFn(() => new Date()),
};

export const orgScope = text("organization_id").notNull();
```

---

### 2.1 Core CX Tables (`shared/schema/conversations.ts`)

```typescript
import {
  pgTable,
  text,
  timestamp,
  boolean,
  integer,
  jsonb,
  index,
  pgEnum,
} from "drizzle-orm/pg-core";
import { createId } from "@paralleldrive/cuid2";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";
import { timestamps, orgScope } from "./_utils";

// ─── Enums ────────────────────────────────────────────────────────────────────

export const channelTypeEnum = pgEnum("channel_type", [
  "email",
  "slack",
  "chat",
  "teams",
  "discord",
  "form",
  "api",
]);

export const conversationStatusEnum = pgEnum("conversation_status", [
  "open",
  "pending",
  "resolved",
  "closed",
  "spam",
]);

export const conversationPriorityEnum = pgEnum("conversation_priority", [
  "urgent",
  "high",
  "medium",
  "low",
]);

export const messageTypeEnum = pgEnum("message_type", [
  "inbound",   // customer → agent
  "outbound",  // agent → customer
  "note",      // internal note (not sent to customer)
  "activity",  // system activity (status change, assignment, etc.)
  "ai_draft",  // AI-generated draft (not yet sent)
]);

// ─── channels ─────────────────────────────────────────────────────────────────
// One row per channel type supported by the platform (static seed data +
// per-org customization via channel_connections)

export const channels = pgTable(
  "channels",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    channelType: channelTypeEnum("channel_type").notNull(),
    name: text("name").notNull(),               // human label, e.g. "Support Email"
    isActive: boolean("is_active").notNull().default(true),
    config: jsonb("config").notNull().default({}), // channel-type-specific config blob
    ...timestamps,
  },
  (t) => [
    index("channels_org_idx").on(t.organizationId),
    index("channels_org_type_idx").on(t.organizationId, t.channelType),
  ]
);

export const insertChannelSchema = createInsertSchema(channels, {
  config: z.record(z.unknown()).optional(),
});
export const selectChannelSchema = createSelectSchema(channels);
export type InsertChannel = z.infer<typeof insertChannelSchema>;
export type Channel = z.infer<typeof selectChannelSchema>;

// ─── channel_connections ──────────────────────────────────────────────────────
// Per-org OAuth tokens, webhook secrets, routing addresses

export const channelConnections = pgTable(
  "channel_connections",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    channelId: text("channel_id").notNull().references(() => channels.id, { onDelete: "cascade" }),
    // Slack-specific
    slackWorkspaceId: text("slack_workspace_id"),
    slackBotToken: text("slack_bot_token"),       // encrypted at rest
    slackSigningSecret: text("slack_signing_secret"), // encrypted at rest
    // Email-specific
    inboundAddress: text("inbound_address"),       // e.g. support@acme.ellocharlie.app
    customDomain: text("custom_domain"),           // e.g. support@acme.com (verified)
    resendDomainId: text("resend_domain_id"),
    // Chat widget
    widgetPublicKey: text("widget_public_key"),    // public key for widget auth
    allowedOrigins: text("allowed_origins").array(), // CORS whitelist
    // Generic
    webhookSecret: text("webhook_secret"),         // HMAC secret for inbound webhooks
    oauthAccessToken: text("oauth_access_token"),  // encrypted at rest
    oauthRefreshToken: text("oauth_refresh_token"), // encrypted at rest
    oauthExpiresAt: timestamp("oauth_expires_at", { withTimezone: true }),
    metadata: jsonb("metadata").notNull().default({}),
    isActive: boolean("is_active").notNull().default(true),
    ...timestamps,
  },
  (t) => [
    index("channel_connections_org_idx").on(t.organizationId),
    index("channel_connections_channel_idx").on(t.channelId),
    index("channel_connections_slack_ws_idx").on(t.slackWorkspaceId),
  ]
);

export const insertChannelConnectionSchema = createInsertSchema(channelConnections);
export const selectChannelConnectionSchema = createSelectSchema(channelConnections);
export type InsertChannelConnection = z.infer<typeof insertChannelConnectionSchema>;
export type ChannelConnection = z.infer<typeof selectChannelConnectionSchema>;

// ─── conversations ────────────────────────────────────────────────────────────
// One conversation = one customer interaction thread, regardless of channel.
// A conversation may span multiple channels (e.g. starts in chat, continues in email).

export const conversations = pgTable(
  "conversations",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    channelId: text("channel_id").references(() => channels.id, { onDelete: "set null" }),
    channelType: channelTypeEnum("channel_type").notNull(),
    // Channel-native thread identifiers for dedup
    externalId: text("external_id"),               // channel-native conversation/thread ID
    externalThreadId: text("external_thread_id"),  // for nested threads (Slack thread_ts)
    // CRM links — the fusion point
    contactId: text("contact_id"),                 // FK → contacts (existing CRM table)
    companyId: text("company_id"),                 // FK → companies (existing CRM table)
    dealId: text("deal_id"),                       // FK → deals (existing CRM table)
    // Conversation metadata
    subject: text("subject"),
    status: conversationStatusEnum("status").notNull().default("open"),
    priority: conversationPriorityEnum("priority").notNull().default("medium"),
    assigneeId: text("assignee_id"),               // FK → users (Clerk user ID)
    assignedTeamId: text("assigned_team_id"),      // FK → teams
    // AI-computed fields (refreshed on each triage pass)
    aiSummary: text("ai_summary"),
    aiSentiment: text("ai_sentiment"),             // 'positive'|'neutral'|'negative'|'frustrated'
    aiTopics: text("ai_topics").array(),
    aiPriorityScore: integer("ai_priority_score"), // 0-100
    // Timestamps
    firstResponseAt: timestamp("first_response_at", { withTimezone: true }),
    resolvedAt: timestamp("resolved_at", { withTimezone: true }),
    closedAt: timestamp("closed_at", { withTimezone: true }),
    snoozedUntil: timestamp("snoozed_until", { withTimezone: true }),
    lastActivityAt: timestamp("last_activity_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
    ...timestamps,
  },
  (t) => [
    index("conversations_org_idx").on(t.organizationId),
    index("conversations_org_status_idx").on(t.organizationId, t.status),
    index("conversations_contact_idx").on(t.contactId),
    index("conversations_company_idx").on(t.companyId),
    index("conversations_assignee_idx").on(t.assigneeId),
    index("conversations_external_idx").on(t.organizationId, t.externalId),
    index("conversations_last_activity_idx").on(t.organizationId, t.lastActivityAt),
  ]
);

export const insertConversationSchema = createInsertSchema(conversations, {
  aiTopics: z.array(z.string()).optional(),
  allowedOrigins: z.array(z.string()).optional(),
});
export const selectConversationSchema = createSelectSchema(conversations);
export type InsertConversation = z.infer<typeof insertConversationSchema>;
export type Conversation = z.infer<typeof selectConversationSchema>;

// ─── messages ─────────────────────────────────────────────────────────────────

export const messages = pgTable(
  "messages",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    conversationId: text("conversation_id")
      .notNull()
      .references(() => conversations.id, { onDelete: "cascade" }),
    messageType: messageTypeEnum("message_type").notNull(),
    // Sender info (denormalized for speed — authoritative source is CRM contact)
    authorId: text("author_id"),                   // Clerk user ID if agent/member
    authorEmail: text("author_email"),
    authorName: text("author_name"),
    // Content — stored as both plain and rich formats
    bodyText: text("body_text"),
    bodyHtml: text("body_html"),
    // Rich text (Tiptap JSON document stored in jsonb)
    bodyTiptap: jsonb("body_tiptap"),
    // Channel-native IDs for dedup and deep-linking
    externalId: text("external_id"),               // email Message-ID, Slack message ts
    externalThreadId: text("external_thread_id"),
    // Attachments stored as R2 keys
    attachments: jsonb("attachments").notNull().default([]),
    // Email-specific headers
    emailHeaders: jsonb("email_headers"),          // From, To, CC, BCC, References
    // AI metadata
    aiGenerated: boolean("ai_generated").notNull().default(false),
    aiActionId: text("ai_action_id"),              // FK → ai_actions if this came from AI
    // Delivery status
    deliveredAt: timestamp("delivered_at", { withTimezone: true }),
    readAt: timestamp("read_at", { withTimezone: true }),
    failedAt: timestamp("failed_at", { withTimezone: true }),
    failureReason: text("failure_reason"),
    ...timestamps,
  },
  (t) => [
    index("messages_conversation_idx").on(t.conversationId),
    index("messages_org_idx").on(t.organizationId),
    index("messages_external_idx").on(t.organizationId, t.externalId),
    index("messages_author_idx").on(t.authorId),
    index("messages_created_at_idx").on(t.conversationId, t.createdAt),
  ]
);

export const insertMessageSchema = createInsertSchema(messages, {
  attachments: z
    .array(
      z.object({
        filename: z.string(),
        mimeType: z.string(),
        size: z.number(),
        storageKey: z.string(),
        url: z.string().url().optional(),
      })
    )
    .optional(),
  bodyTiptap: z.record(z.unknown()).optional(),
  emailHeaders: z.record(z.string()).optional(),
});
export const selectMessageSchema = createSelectSchema(messages);
export type InsertMessage = z.infer<typeof insertMessageSchema>;
export type Message = z.infer<typeof selectMessageSchema>;
```

---

### 2.2 Ticketing (`shared/schema/tickets.ts`)

```typescript
import {
  pgTable,
  text,
  timestamp,
  boolean,
  integer,
  jsonb,
  index,
  pgEnum,
} from "drizzle-orm/pg-core";
import { createId } from "@paralleldrive/cuid2";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";
import { timestamps, orgScope } from "./_utils";
import { conversations } from "./conversations";

export const ticketStatusEnum = pgEnum("ticket_status", [
  "new",
  "open",
  "pending_customer",
  "pending_internal",
  "on_hold",
  "resolved",
  "closed",
]);

export const ticketTypeEnum = pgEnum("ticket_type", [
  "bug",
  "feature_request",
  "billing",
  "onboarding",
  "integration",
  "security",
  "general",
  "other",
]);

export const slaBreachTypeEnum = pgEnum("sla_breach_type", [
  "first_response",
  "resolution",
  "next_response",
]);

// ─── tickets ──────────────────────────────────────────────────────────────────

export const tickets = pgTable(
  "tickets",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    // Readable ticket number (org-scoped sequence, handled in app layer)
    number: integer("number").notNull(),
    conversationId: text("conversation_id").references(() => conversations.id, {
      onDelete: "set null",
    }),
    // CRM links
    contactId: text("contact_id"),                 // FK → contacts
    companyId: text("company_id"),                 // FK → companies
    dealId: text("deal_id"),                       // FK → deals
    // Ticket fields
    title: text("title").notNull(),
    description: text("description"),
    descriptionTiptap: jsonb("description_tiptap"),
    status: ticketStatusEnum("status").notNull().default("new"),
    ticketType: ticketTypeEnum("ticket_type").notNull().default("general"),
    priority: text("priority")
      .$type<"urgent" | "high" | "medium" | "low">()
      .notNull()
      .default("medium"),
    // Assignees
    assigneeId: text("assignee_id"),               // Clerk user ID
    assignedTeamId: text("assigned_team_id"),
    // SLA
    slaPolicyId: text("sla_policy_id"),            // FK → sla_policies
    slaFirstResponseDue: timestamp("sla_first_response_due", { withTimezone: true }),
    slaResolutionDue: timestamp("sla_resolution_due", { withTimezone: true }),
    slaBreached: boolean("sla_breached").notNull().default(false),
    // Source
    sourceChannelType: text("source_channel_type"),
    // Timestamps
    firstResponseAt: timestamp("first_response_at", { withTimezone: true }),
    resolvedAt: timestamp("resolved_at", { withTimezone: true }),
    closedAt: timestamp("closed_at", { withTimezone: true }),
    ...timestamps,
  },
  (t) => [
    index("tickets_org_idx").on(t.organizationId),
    index("tickets_org_status_idx").on(t.organizationId, t.status),
    index("tickets_org_number_idx").on(t.organizationId, t.number),
    index("tickets_contact_idx").on(t.contactId),
    index("tickets_company_idx").on(t.companyId),
    index("tickets_assignee_idx").on(t.assigneeId),
    index("tickets_conversation_idx").on(t.conversationId),
  ]
);

export const insertTicketSchema = createInsertSchema(tickets, {
  descriptionTiptap: z.record(z.unknown()).optional(),
});
export const selectTicketSchema = createSelectSchema(tickets);
export type InsertTicket = z.infer<typeof insertTicketSchema>;
export type Ticket = z.infer<typeof selectTicketSchema>;

// ─── ticket_assignments ───────────────────────────────────────────────────────

export const ticketAssignments = pgTable(
  "ticket_assignments",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    ticketId: text("ticket_id")
      .notNull()
      .references(() => tickets.id, { onDelete: "cascade" }),
    assigneeId: text("assignee_id").notNull(), // Clerk user ID
    assignedById: text("assigned_by_id"),       // who made the assignment
    assignedAt: timestamp("assigned_at", { withTimezone: true }).notNull().defaultNow(),
    unassignedAt: timestamp("unassigned_at", { withTimezone: true }),
    note: text("note"),
  },
  (t) => [
    index("ticket_assignments_ticket_idx").on(t.ticketId),
    index("ticket_assignments_assignee_idx").on(t.assigneeId),
  ]
);

export const insertTicketAssignmentSchema = createInsertSchema(ticketAssignments);
export const selectTicketAssignmentSchema = createSelectSchema(ticketAssignments);
export type InsertTicketAssignment = z.infer<typeof insertTicketAssignmentSchema>;
export type TicketAssignment = z.infer<typeof selectTicketAssignmentSchema>;

// ─── ticket_tags ──────────────────────────────────────────────────────────────

export const ticketTags = pgTable(
  "ticket_tags",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    ticketId: text("ticket_id")
      .notNull()
      .references(() => tickets.id, { onDelete: "cascade" }),
    tag: text("tag").notNull(),
    createdById: text("created_by_id"),
    ...timestamps,
  },
  (t) => [
    index("ticket_tags_ticket_idx").on(t.ticketId),
    index("ticket_tags_org_tag_idx").on(t.organizationId, t.tag),
  ]
);

export const insertTicketTagSchema = createInsertSchema(ticketTags);
export const selectTicketTagSchema = createSelectSchema(ticketTags);
export type InsertTicketTag = z.infer<typeof insertTicketTagSchema>;
export type TicketTag = z.infer<typeof selectTicketTagSchema>;

// ─── sla_policies ─────────────────────────────────────────────────────────────

export const slaPolicies = pgTable(
  "sla_policies",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    name: text("name").notNull(),
    description: text("description"),
    isDefault: boolean("is_default").notNull().default(false),
    // Time targets in minutes
    firstResponseMinutes: integer("first_response_minutes").notNull(), // e.g. 60 = 1hr
    nextResponseMinutes: integer("next_response_minutes"),
    resolutionMinutes: integer("resolution_minutes").notNull(),        // e.g. 1440 = 24hr
    // Business hours config
    businessHoursOnly: boolean("business_hours_only").notNull().default(true),
    businessHoursConfig: jsonb("business_hours_config").notNull().default({}),
    // Scope: apply to specific priority levels
    appliesTo: text("applies_to").array(), // ['urgent', 'high'] — null = all
    ...timestamps,
  },
  (t) => [index("sla_policies_org_idx").on(t.organizationId)]
);

export const insertSlaPolicySchema = createInsertSchema(slaPolicies, {
  appliesTo: z.array(z.string()).optional(),
  businessHoursConfig: z
    .object({
      timezone: z.string().optional(),
      // Mon=0...Sun=6 → { start: "09:00", end: "17:00" }
      schedule: z
        .record(z.object({ start: z.string(), end: z.string() }))
        .optional(),
    })
    .optional(),
});
export const selectSlaPolicySchema = createSelectSchema(slaPolicies);
export type InsertSlaPolicy = z.infer<typeof insertSlaPolicySchema>;
export type SlaPolicy = z.infer<typeof selectSlaPolicySchema>;

// ─── sla_status ───────────────────────────────────────────────────────────────

export const slaStatus = pgTable(
  "sla_status",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    ticketId: text("ticket_id")
      .notNull()
      .references(() => tickets.id, { onDelete: "cascade" }),
    slaPolicyId: text("sla_policy_id")
      .notNull()
      .references(() => slaPolicies.id, { onDelete: "cascade" }),
    breachType: slaBreachTypeEnum("breach_type").notNull(),
    dueAt: timestamp("due_at", { withTimezone: true }).notNull(),
    achievedAt: timestamp("achieved_at", { withTimezone: true }),
    breachedAt: timestamp("breached_at", { withTimezone: true }),
    breached: boolean("breached").notNull().default(false),
    // Remaining time snapshot (refreshed on each ticket update)
    remainingMinutes: integer("remaining_minutes"),
    ...timestamps,
  },
  (t) => [
    index("sla_status_ticket_idx").on(t.ticketId),
    index("sla_status_due_idx").on(t.dueAt),
    index("sla_status_breached_idx").on(t.organizationId, t.breached),
  ]
);

export const insertSlaStatusSchema = createInsertSchema(slaStatus);
export const selectSlaStatusSchema = createSelectSchema(slaStatus);
export type InsertSlaStatus = z.infer<typeof insertSlaStatusSchema>;
export type SlaStatus = z.infer<typeof selectSlaStatusSchema>;
```

---

### 2.3 Knowledge Base (`shared/schema/knowledge-base.ts`)

```typescript
import {
  pgTable,
  text,
  timestamp,
  boolean,
  integer,
  jsonb,
  index,
  pgEnum,
} from "drizzle-orm/pg-core";
import { createId } from "@paralleldrive/cuid2";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";
import { timestamps, orgScope } from "./_utils";

export const kbArticleStatusEnum = pgEnum("kb_article_status", [
  "draft",
  "in_review",
  "published",
  "archived",
]);

export const kbVisibilityEnum = pgEnum("kb_visibility", [
  "public",       // visible to end-users (customer portal)
  "internal",     // visible to org members only
  "restricted",   // visible to specific contact groups
]);

// ─── kb_collections ───────────────────────────────────────────────────────────

export const kbCollections = pgTable(
  "kb_collections",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    parentId: text("parent_id"),               // self-referential for nested folders
    name: text("name").notNull(),
    slug: text("slug").notNull(),
    description: text("description"),
    icon: text("icon"),                         // emoji or icon key
    visibility: kbVisibilityEnum("visibility").notNull().default("public"),
    position: integer("position").notNull().default(0),
    ...timestamps,
  },
  (t) => [
    index("kb_collections_org_idx").on(t.organizationId),
    index("kb_collections_parent_idx").on(t.parentId),
    index("kb_collections_slug_idx").on(t.organizationId, t.slug),
  ]
);

export const insertKbCollectionSchema = createInsertSchema(kbCollections);
export const selectKbCollectionSchema = createSelectSchema(kbCollections);
export type InsertKbCollection = z.infer<typeof insertKbCollectionSchema>;
export type KbCollection = z.infer<typeof selectKbCollectionSchema>;

// ─── kb_articles ──────────────────────────────────────────────────────────────

export const kbArticles = pgTable(
  "kb_articles",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    collectionId: text("collection_id").references(() => kbCollections.id, {
      onDelete: "set null",
    }),
    // Authoring
    title: text("title").notNull(),
    slug: text("slug").notNull(),
    excerpt: text("excerpt"),                   // auto-generated or manual summary
    bodyText: text("body_text"),                // plain text (search + AI context)
    bodyTiptap: jsonb("body_tiptap"),           // rich editor content
    // Status & visibility
    status: kbArticleStatusEnum("status").notNull().default("draft"),
    visibility: kbVisibilityEnum("visibility").notNull().default("public"),
    // Authorship
    authorId: text("author_id"),               // Clerk user ID
    lastEditedById: text("last_edited_by_id"),
    publishedAt: timestamp("published_at", { withTimezone: true }),
    // Metadata
    metaTitle: text("meta_title"),
    metaDescription: text("meta_description"),
    tags: text("tags").array(),
    // AI fields
    aiGenerated: boolean("ai_generated").notNull().default(false),
    aiEmbeddingVersion: integer("ai_embedding_version"),  // track re-embedding needs
    // Stats
    viewCount: integer("view_count").notNull().default(0),
    helpfulCount: integer("helpful_count").notNull().default(0),
    notHelpfulCount: integer("not_helpful_count").notNull().default(0),
    position: integer("position").notNull().default(0),
    ...timestamps,
  },
  (t) => [
    index("kb_articles_org_idx").on(t.organizationId),
    index("kb_articles_org_status_idx").on(t.organizationId, t.status),
    index("kb_articles_collection_idx").on(t.collectionId),
    index("kb_articles_slug_idx").on(t.organizationId, t.slug),
    index("kb_articles_tags_idx").on(t.tags),
  ]
);

export const insertKbArticleSchema = createInsertSchema(kbArticles, {
  tags: z.array(z.string()).optional(),
  bodyTiptap: z.record(z.unknown()).optional(),
});
export const selectKbArticleSchema = createSelectSchema(kbArticles);
export type InsertKbArticle = z.infer<typeof insertKbArticleSchema>;
export type KbArticle = z.infer<typeof selectKbArticleSchema>;

// ─── kb_article_versions ──────────────────────────────────────────────────────

export const kbArticleVersions = pgTable(
  "kb_article_versions",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    articleId: text("article_id")
      .notNull()
      .references(() => kbArticles.id, { onDelete: "cascade" }),
    version: integer("version").notNull(),
    title: text("title").notNull(),
    bodyText: text("body_text"),
    bodyTiptap: jsonb("body_tiptap"),
    editedById: text("edited_by_id"),
    changeNote: text("change_note"),
    ...timestamps,
  },
  (t) => [
    index("kb_versions_article_idx").on(t.articleId),
    index("kb_versions_org_idx").on(t.organizationId),
  ]
);

export const insertKbArticleVersionSchema = createInsertSchema(kbArticleVersions, {
  bodyTiptap: z.record(z.unknown()).optional(),
});
export const selectKbArticleVersionSchema = createSelectSchema(kbArticleVersions);
export type InsertKbArticleVersion = z.infer<typeof insertKbArticleVersionSchema>;
export type KbArticleVersion = z.infer<typeof selectKbArticleVersionSchema>;
```

---

### 2.4 Account Intelligence (`shared/schema/account-intelligence.ts`)

```typescript
import {
  pgTable,
  text,
  timestamp,
  boolean,
  integer,
  real,
  jsonb,
  index,
  pgEnum,
} from "drizzle-orm/pg-core";
import { createId } from "@paralleldrive/cuid2";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";
import { timestamps, orgScope } from "./_utils";

export const signalTypeEnum = pgEnum("signal_type", [
  // Support signals
  "ticket_volume_spike",
  "ticket_sentiment_negative",
  "ticket_sentiment_positive",
  "sla_breach",
  "response_time_slow",
  "unresolved_tickets_high",
  // Engagement signals
  "conversation_frequency_drop",
  "no_recent_activity",
  "feature_request_submitted",
  // Product / usage signals
  "usage_drop",
  "usage_spike",
  // Deal / commercial signals
  "deal_stage_advanced",
  "deal_at_risk",
  "renewal_approaching",
  "payment_failed",
  // Onboarding signals
  "onboarding_incomplete",
  "onboarding_completed",
]);

export const healthScoreTrendEnum = pgEnum("health_score_trend", [
  "improving",
  "stable",
  "declining",
]);

export const activityTypeEnum = pgEnum("activity_type", [
  "ticket_created",
  "ticket_resolved",
  "conversation_opened",
  "conversation_closed",
  "deal_stage_changed",
  "note_added",
  "feature_request_linked",
  "health_score_changed",
  "contact_added",
  "meeting_logged",
]);

// ─── account_health_scores ────────────────────────────────────────────────────

export const accountHealthScores = pgTable(
  "account_health_scores",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    companyId: text("company_id").notNull(),     // FK → companies
    // Composite score 0-100
    overallScore: integer("overall_score").notNull().default(50),
    // Component scores 0-100
    supportScore: integer("support_score"),
    engagementScore: integer("engagement_score"),
    usageScore: integer("usage_score"),
    npsScore: integer("nps_score"),
    // Trend
    trend: healthScoreTrendEnum("trend").notNull().default("stable"),
    previousScore: integer("previous_score"),
    scoredAt: timestamp("scored_at", { withTimezone: true }).notNull().defaultNow(),
    // Risk assessment
    churnRisk: real("churn_risk"),               // 0.0-1.0 probability
    expansionPotential: real("expansion_potential"), // 0.0-1.0
    // Contributing factors (for explainability)
    factors: jsonb("factors").notNull().default([]),
    ...timestamps,
  },
  (t) => [
    index("account_health_company_idx").on(t.companyId),
    index("account_health_org_idx").on(t.organizationId),
    index("account_health_score_idx").on(t.organizationId, t.overallScore),
  ]
);

export const insertAccountHealthScoreSchema = createInsertSchema(accountHealthScores, {
  factors: z
    .array(
      z.object({
        name: z.string(),
        weight: z.number(),
        value: z.number(),
        direction: z.enum(["positive", "negative", "neutral"]),
        description: z.string().optional(),
      })
    )
    .optional(),
});
export const selectAccountHealthScoreSchema = createSelectSchema(accountHealthScores);
export type InsertAccountHealthScore = z.infer<typeof insertAccountHealthScoreSchema>;
export type AccountHealthScore = z.infer<typeof selectAccountHealthScoreSchema>;

// ─── account_signals ──────────────────────────────────────────────────────────

export const accountSignals = pgTable(
  "account_signals",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    companyId: text("company_id").notNull(),     // FK → companies
    contactId: text("contact_id"),               // optional contact-level signal
    signalType: signalTypeEnum("signal_type").notNull(),
    // Impact on health score
    impact: real("impact").notNull().default(0), // positive or negative delta
    // Context
    title: text("title").notNull(),
    description: text("description"),
    metadata: jsonb("metadata").notNull().default({}), // signal-type specific data
    // Source reference
    sourceType: text("source_type"),             // 'ticket' | 'deal' | 'conversation' | etc.
    sourceId: text("source_id"),                 // FK to source record
    // Lifecycle
    triggeredAt: timestamp("triggered_at", { withTimezone: true }).notNull().defaultNow(),
    expiresAt: timestamp("expires_at", { withTimezone: true }),
    resolvedAt: timestamp("resolved_at", { withTimezone: true }),
    isActive: boolean("is_active").notNull().default(true),
    ...timestamps,
  },
  (t) => [
    index("account_signals_company_idx").on(t.companyId),
    index("account_signals_org_idx").on(t.organizationId),
    index("account_signals_type_idx").on(t.organizationId, t.signalType),
    index("account_signals_active_idx").on(t.companyId, t.isActive),
  ]
);

export const insertAccountSignalSchema = createInsertSchema(accountSignals, {
  metadata: z.record(z.unknown()).optional(),
});
export const selectAccountSignalSchema = createSelectSchema(accountSignals);
export type InsertAccountSignal = z.infer<typeof insertAccountSignalSchema>;
export type AccountSignal = z.infer<typeof selectAccountSignalSchema>;

// ─── account_activities ───────────────────────────────────────────────────────
// Unified activity feed per account — CX + CRM events in one timeline

export const accountActivities = pgTable(
  "account_activities",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    companyId: text("company_id").notNull(),     // FK → companies
    contactId: text("contact_id"),
    activityType: activityTypeEnum("activity_type").notNull(),
    title: text("title").notNull(),
    description: text("description"),
    // Polymorphic source reference
    sourceType: text("source_type"),             // 'ticket' | 'deal' | 'conversation' | 'note'
    sourceId: text("source_id"),
    // Actor
    actorId: text("actor_id"),                   // Clerk user ID or 'system'
    actorName: text("actor_name"),
    metadata: jsonb("metadata").notNull().default({}),
    occurredAt: timestamp("occurred_at", { withTimezone: true }).notNull().defaultNow(),
    ...timestamps,
  },
  (t) => [
    index("account_activities_company_idx").on(t.companyId),
    index("account_activities_org_idx").on(t.organizationId),
    index("account_activities_occurred_idx").on(t.companyId, t.occurredAt),
    index("account_activities_type_idx").on(t.organizationId, t.activityType),
  ]
);

export const insertAccountActivitySchema = createInsertSchema(accountActivities, {
  metadata: z.record(z.unknown()).optional(),
});
export const selectAccountActivitySchema = createSelectSchema(accountActivities);
export type InsertAccountActivity = z.infer<typeof insertAccountActivitySchema>;
export type AccountActivity = z.infer<typeof selectAccountActivitySchema>;
```

---

### 2.5 Product Intelligence (`shared/schema/product-intelligence.ts`)

```typescript
import {
  pgTable,
  text,
  integer,
  real,
  jsonb,
  boolean,
  index,
  pgEnum,
} from "drizzle-orm/pg-core";
import { createId } from "@paralleldrive/cuid2";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";
import { timestamps, orgScope } from "./_utils";
import { tickets } from "./tickets";

export const featureRequestStatusEnum = pgEnum("feature_request_status", [
  "under_review",
  "planned",
  "in_progress",
  "shipped",
  "declined",
  "duplicate",
]);

// ─── feature_requests ─────────────────────────────────────────────────────────
// AI-clustered feature request groups. Each cluster represents a distinct
// product need, aggregated from individual ticket mentions and conversations.

export const featureRequests = pgTable(
  "feature_requests",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    title: text("title").notNull(),
    description: text("description"),
    // AI cluster metadata
    aiClusterLabel: text("ai_cluster_label"),     // AI-generated short label
    aiClusterSummary: text("ai_cluster_summary"), // AI-generated synthesis of all mentions
    embeddingVector: text("embedding_vector"),    // serialized for storage (use pgvector in prod)
    // Status tracking
    status: featureRequestStatusEnum("status").notNull().default("under_review"),
    // Business impact aggregated from evidence
    mentionCount: integer("mention_count").notNull().default(0),
    uniqueCompanyCount: integer("unique_company_count").notNull().default(0),
    uniqueContactCount: integer("unique_contact_count").notNull().default(0),
    // Revenue impact (sum of ARR from requesting companies)
    estimatedRevenueImpact: real("estimated_revenue_impact"),
    // Priority score (combination of volume, ARR, sentiment urgency)
    priorityScore: real("priority_score"),
    // Tags / product area
    tags: text("tags").array(),
    productArea: text("product_area"),
    // External tracking
    externalIssueUrl: text("external_issue_url"), // GitHub/Linear/Jira link
    externalIssueId: text("external_issue_id"),
    // Managed by
    ownerId: text("owner_id"),
    ...timestamps,
  },
  (t) => [
    index("feature_requests_org_idx").on(t.organizationId),
    index("feature_requests_status_idx").on(t.organizationId, t.status),
    index("feature_requests_priority_idx").on(t.organizationId, t.priorityScore),
  ]
);

export const insertFeatureRequestSchema = createInsertSchema(featureRequests, {
  tags: z.array(z.string()).optional(),
});
export const selectFeatureRequestSchema = createSelectSchema(featureRequests);
export type InsertFeatureRequest = z.infer<typeof insertFeatureRequestSchema>;
export type FeatureRequest = z.infer<typeof selectFeatureRequestSchema>;

// ─── feature_request_evidence ─────────────────────────────────────────────────
// Individual mentions linking to the cluster

export const featureRequestEvidence = pgTable(
  "feature_request_evidence",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    featureRequestId: text("feature_request_id")
      .notNull()
      .references(() => featureRequests.id, { onDelete: "cascade" }),
    // Source (polymorphic)
    sourceType: text("source_type").notNull(), // 'ticket' | 'message' | 'conversation'
    sourceId: text("source_id").notNull(),
    ticketId: text("ticket_id").references(() => tickets.id, { onDelete: "set null" }),
    // Contact/company context
    contactId: text("contact_id"),
    companyId: text("company_id"),
    // The actual quote/excerpt from the source
    excerpt: text("excerpt"),
    // AI confidence that this mention matches the cluster
    confidenceScore: real("confidence_score"),
    // Whether a human confirmed this linkage
    humanVerified: boolean("human_verified").notNull().default(false),
    ...timestamps,
  },
  (t) => [
    index("fr_evidence_request_idx").on(t.featureRequestId),
    index("fr_evidence_org_idx").on(t.organizationId),
    index("fr_evidence_company_idx").on(t.companyId),
  ]
);

export const insertFeatureRequestEvidenceSchema = createInsertSchema(featureRequestEvidence);
export const selectFeatureRequestEvidenceSchema = createSelectSchema(featureRequestEvidence);
export type InsertFeatureRequestEvidence = z.infer<typeof insertFeatureRequestEvidenceSchema>;
export type FeatureRequestEvidence = z.infer<typeof selectFeatureRequestEvidenceSchema>;
```

---

### 2.6 AI Layer (`shared/schema/ai.ts`)

```typescript
import {
  pgTable,
  text,
  integer,
  real,
  jsonb,
  boolean,
  timestamp,
  index,
  pgEnum,
} from "drizzle-orm/pg-core";
import { createId } from "@paralleldrive/cuid2";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";
import { timestamps, orgScope } from "./_utils";

export const aiActionTypeEnum = pgEnum("ai_action_type", [
  "triage",
  "routing",
  "draft_reply",
  "categorize",
  "summarize",
  "knowledge_gap_detection",
  "health_score_computation",
  "feature_request_clustering",
  "sentiment_analysis",
  "priority_scoring",
]);

export const aiSuggestionTypeEnum = pgEnum("ai_suggestion_type", [
  "reply_draft",
  "ticket_assignment",
  "priority_change",
  "status_change",
  "knowledge_gap",
  "feature_cluster",
]);

export const aiSuggestionStatusEnum = pgEnum("ai_suggestion_status", [
  "pending",
  "accepted",
  "rejected",
  "auto_applied",
  "expired",
]);

// ─── ai_actions ───────────────────────────────────────────────────────────────
// Audit log of every AI inference call — for debugging, cost tracking, 
// and human override analysis

export const aiActions = pgTable(
  "ai_actions",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    actionType: aiActionTypeEnum("action_type").notNull(),
    // Source context
    conversationId: text("conversation_id"),
    ticketId: text("ticket_id"),
    contactId: text("contact_id"),
    companyId: text("company_id"),
    // Model info
    modelProvider: text("model_provider").notNull(), // 'openai' | 'anthropic'
    modelName: text("model_name").notNull(),         // 'gpt-4o' | 'claude-3-5-sonnet'
    // Usage
    promptTokens: integer("prompt_tokens"),
    completionTokens: integer("completion_tokens"),
    latencyMs: integer("latency_ms"),
    // Input/output (stored for debugging — PII should be scrubbed after N days)
    promptSummary: text("prompt_summary"),           // non-PII summary
    outputSummary: text("output_summary"),           // non-PII summary
    // Outcome tracking
    humanOverridden: boolean("human_overridden").notNull().default(false),
    overriddenById: text("overridden_by_id"),
    overrideReason: text("override_reason"),
    // Success/failure
    success: boolean("success").notNull().default(true),
    errorMessage: text("error_message"),
    triggeredAt: timestamp("triggered_at", { withTimezone: true }).notNull().defaultNow(),
    ...timestamps,
  },
  (t) => [
    index("ai_actions_org_idx").on(t.organizationId),
    index("ai_actions_type_idx").on(t.organizationId, t.actionType),
    index("ai_actions_conversation_idx").on(t.conversationId),
    index("ai_actions_ticket_idx").on(t.ticketId),
    index("ai_actions_triggered_idx").on(t.organizationId, t.triggeredAt),
  ]
);

export const insertAiActionSchema = createInsertSchema(aiActions);
export const selectAiActionSchema = createSelectSchema(aiActions);
export type InsertAiAction = z.infer<typeof insertAiActionSchema>;
export type AiAction = z.infer<typeof selectAiActionSchema>;

// ─── ai_suggestions ───────────────────────────────────────────────────────────
// Pending AI suggestions shown to human agents for review/approval

export const aiSuggestions = pgTable(
  "ai_suggestions",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    aiActionId: text("ai_action_id"),            // FK → ai_actions
    suggestionType: aiSuggestionTypeEnum("suggestion_type").notNull(),
    // Target
    conversationId: text("conversation_id"),
    ticketId: text("ticket_id"),
    // The suggestion payload
    content: jsonb("content").notNull(),         // type-specific payload
    confidenceScore: real("confidence_score"),   // 0.0-1.0
    // Workflow
    status: aiSuggestionStatusEnum("status").notNull().default("pending"),
    reviewedById: text("reviewed_by_id"),
    reviewedAt: timestamp("reviewed_at", { withTimezone: true }),
    expiresAt: timestamp("expires_at", { withTimezone: true }),
    ...timestamps,
  },
  (t) => [
    index("ai_suggestions_org_idx").on(t.organizationId),
    index("ai_suggestions_status_idx").on(t.organizationId, t.status),
    index("ai_suggestions_conversation_idx").on(t.conversationId),
    index("ai_suggestions_ticket_idx").on(t.ticketId),
  ]
);

export const insertAiSuggestionSchema = createInsertSchema(aiSuggestions, {
  content: z.record(z.unknown()),
});
export const selectAiSuggestionSchema = createSelectSchema(aiSuggestions);
export type InsertAiSuggestion = z.infer<typeof insertAiSuggestionSchema>;
export type AiSuggestion = z.infer<typeof selectAiSuggestionSchema>;
```

---

### 2.7 Workflow Engine (`shared/schema/workflows.ts`)

```typescript
import {
  pgTable,
  text,
  integer,
  jsonb,
  boolean,
  timestamp,
  index,
  pgEnum,
} from "drizzle-orm/pg-core";
import { createId } from "@paralleldrive/cuid2";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";
import { timestamps, orgScope } from "./_utils";

export const workflowTriggerTypeEnum = pgEnum("workflow_trigger_type", [
  "conversation_created",
  "conversation_status_changed",
  "ticket_created",
  "ticket_status_changed",
  "ticket_assigned",
  "sla_breach_imminent",
  "sla_breached",
  "message_received",
  "health_score_changed",
  "manual",
  "scheduled",
  "webhook",
]);

export const workflowStepTypeEnum = pgEnum("workflow_step_type", [
  // Actions
  "assign_ticket",
  "change_status",
  "change_priority",
  "add_tag",
  "remove_tag",
  "send_email",
  "send_slack_message",
  "add_note",
  "create_ticket",
  "close_conversation",
  "escalate",
  // AI steps
  "ai_triage",
  "ai_draft_reply",
  "ai_categorize",
  // Control flow
  "condition",
  "delay",
  "webhook_call",
  // CRM steps
  "update_contact_field",
  "update_company_field",
  "create_activity",
]);

export const workflowRunStatusEnum = pgEnum("workflow_run_status", [
  "pending",
  "running",
  "completed",
  "failed",
  "cancelled",
]);

// ─── workflows ────────────────────────────────────────────────────────────────

export const workflows = pgTable(
  "workflows",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    name: text("name").notNull(),
    description: text("description"),
    isActive: boolean("is_active").notNull().default(false),
    triggerType: workflowTriggerTypeEnum("trigger_type").notNull(),
    // Trigger conditions (evaluated on each trigger event)
    triggerConditions: jsonb("trigger_conditions").notNull().default([]),
    // Stats
    runCount: integer("run_count").notNull().default(0),
    lastRunAt: timestamp("last_run_at", { withTimezone: true }),
    createdById: text("created_by_id"),
    ...timestamps,
  },
  (t) => [
    index("workflows_org_idx").on(t.organizationId),
    index("workflows_active_idx").on(t.organizationId, t.isActive),
    index("workflows_trigger_idx").on(t.organizationId, t.triggerType),
  ]
);

export const insertWorkflowSchema = createInsertSchema(workflows, {
  triggerConditions: z
    .array(
      z.object({
        field: z.string(),
        operator: z.enum(["eq", "neq", "contains", "not_contains", "gt", "lt", "is_set", "is_empty"]),
        value: z.unknown(),
      })
    )
    .optional(),
});
export const selectWorkflowSchema = createSelectSchema(workflows);
export type InsertWorkflow = z.infer<typeof insertWorkflowSchema>;
export type Workflow = z.infer<typeof selectWorkflowSchema>;

// ─── workflow_steps ───────────────────────────────────────────────────────────

export const workflowSteps = pgTable(
  "workflow_steps",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    workflowId: text("workflow_id")
      .notNull()
      .references(() => workflows.id, { onDelete: "cascade" }),
    stepType: workflowStepTypeEnum("step_type").notNull(),
    position: integer("position").notNull(),
    // Step configuration (type-specific)
    config: jsonb("config").notNull().default({}),
    // Branching (for condition steps)
    nextStepIdOnTrue: text("next_step_id_on_true"),
    nextStepIdOnFalse: text("next_step_id_on_false"),
    nextStepId: text("next_step_id"),            // for linear steps
    ...timestamps,
  },
  (t) => [
    index("workflow_steps_workflow_idx").on(t.workflowId),
  ]
);

export const insertWorkflowStepSchema = createInsertSchema(workflowSteps, {
  config: z.record(z.unknown()),
});
export const selectWorkflowStepSchema = createSelectSchema(workflowSteps);
export type InsertWorkflowStep = z.infer<typeof insertWorkflowStepSchema>;
export type WorkflowStep = z.infer<typeof selectWorkflowStepSchema>;

// ─── workflow_triggers ────────────────────────────────────────────────────────

export const workflowTriggers = pgTable(
  "workflow_triggers",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    workflowId: text("workflow_id")
      .notNull()
      .references(() => workflows.id, { onDelete: "cascade" }),
    triggerType: workflowTriggerTypeEnum("trigger_type").notNull(),
    // For scheduled triggers
    cronExpression: text("cron_expression"),
    // For webhook triggers
    webhookSecret: text("webhook_secret"),
    ...timestamps,
  },
  (t) => [index("workflow_triggers_workflow_idx").on(t.workflowId)]
);

export const insertWorkflowTriggerSchema = createInsertSchema(workflowTriggers);
export const selectWorkflowTriggerSchema = createSelectSchema(workflowTriggers);
export type InsertWorkflowTrigger = z.infer<typeof insertWorkflowTriggerSchema>;
export type WorkflowTrigger = z.infer<typeof selectWorkflowTriggerSchema>;

// ─── workflow_runs ────────────────────────────────────────────────────────────

export const workflowRuns = pgTable(
  "workflow_runs",
  {
    id: text("id").primaryKey().$defaultFn(() => createId()),
    organizationId: orgScope,
    workflowId: text("workflow_id")
      .notNull()
      .references(() => workflows.id, { onDelete: "cascade" }),
    status: workflowRunStatusEnum("status").notNull().default("pending"),
    // Trigger context
    triggerType: workflowTriggerTypeEnum("trigger_type").notNull(),
    triggerPayload: jsonb("trigger_payload"),
    // Source entity
    conversationId: text("conversation_id"),
    ticketId: text("ticket_id"),
    contactId: text("contact_id"),
    companyId: text("company_id"),
    // Execution log (step-by-step results)
    executionLog: jsonb("execution_log").notNull().default([]),
    // Timing
    startedAt: timestamp("started_at", { withTimezone: true }),
    completedAt: timestamp("completed_at", { withTimezone: true }),
    errorMessage: text("error_message"),
    ...timestamps,
  },
  (t) => [
    index("workflow_runs_workflow_idx").on(t.workflowId),
    index("workflow_runs_org_status_idx").on(t.organizationId, t.status),
    index("workflow_runs_conversation_idx").on(t.conversationId),
    index("workflow_runs_ticket_idx").on(t.ticketId),
  ]
);

export const insertWorkflowRunSchema = createInsertSchema(workflowRuns, {
  triggerPayload: z.record(z.unknown()).optional(),
  executionLog: z
    .array(
      z.object({
        stepId: z.string(),
        stepType: z.string(),
        status: z.enum(["success", "failure", "skipped"]),
        output: z.record(z.unknown()).optional(),
        errorMessage: z.string().optional(),
        durationMs: z.number().optional(),
      })
    )
    .optional(),
});
export const selectWorkflowRunSchema = createSelectSchema(workflowRuns);
export type InsertWorkflowRun = z.infer<typeof insertWorkflowRunSchema>;
export type WorkflowRun = z.infer<typeof selectWorkflowRunSchema>;
```

---

## 3. tRPC Router Definitions

All routers use the same pattern:
- `protectedProcedure` (from existing auth middleware) — injects `ctx.organizationId` and `ctx.userId`
- All inputs validated with Zod
- Cursor-based pagination using the existing cursor pattern

**Router entry point** (`server/routers/cx.ts`):
```typescript
import { router } from "../trpc";
import { conversationsRouter } from "./conversations";
import { ticketsRouter } from "./tickets";
import { knowledgeBaseRouter } from "./knowledgeBase";
import { accountIntelligenceRouter } from "./accountIntelligence";
import { productIntelligenceRouter } from "./productIntelligence";
import { channelsRouter } from "./channels";
import { workflowsRouter } from "./workflows";
import { aiRouter } from "./ai";

export const cxRouter = router({
  conversations: conversationsRouter,
  tickets: ticketsRouter,
  knowledgeBase: knowledgeBaseRouter,
  accountIntelligence: accountIntelligenceRouter,
  productIntelligence: productIntelligenceRouter,
  channels: channelsRouter,
  workflows: workflowsRouter,
  ai: aiRouter,
});
```

---

### 3.1 Conversations Router (`server/routers/conversations.ts`)

```typescript
import { z } from "zod";
import { router, protectedProcedure } from "../trpc";
import { TRPCError } from "@trpc/server";
import { db } from "../db";
import {
  conversations,
  messages,
  conversationStatusEnum,
  conversationPriorityEnum,
} from "../../shared/schema/conversations";
import { eq, and, desc, lt, sql } from "drizzle-orm";

const cursorSchema = z.string().cuid2().optional();

const listConversationsInput = z.object({
  cursor: cursorSchema,
  limit: z.number().min(1).max(100).default(25),
  status: z.enum(["open", "pending", "resolved", "closed", "spam"]).optional(),
  assigneeId: z.string().optional(),
  contactId: z.string().cuid2().optional(),
  companyId: z.string().cuid2().optional(),
  channelType: z
    .enum(["email", "slack", "chat", "teams", "discord", "form", "api"])
    .optional(),
  priority: z.enum(["urgent", "high", "medium", "low"]).optional(),
  search: z.string().max(255).optional(),
});

export const conversationsRouter = router({
  list: protectedProcedure
    .input(listConversationsInput)
    .query(async ({ ctx, input }) => {
      const { organizationId } = ctx;
      const { cursor, limit, status, assigneeId, contactId, companyId, channelType, priority } = input;

      const conditions = [eq(conversations.organizationId, organizationId)];
      if (status) conditions.push(eq(conversations.status, status));
      if (assigneeId) conditions.push(eq(conversations.assigneeId, assigneeId));
      if (contactId) conditions.push(eq(conversations.contactId, contactId));
      if (companyId) conditions.push(eq(conversations.companyId, companyId));
      if (channelType) conditions.push(eq(conversations.channelType, channelType));
      if (priority) conditions.push(eq(conversations.priority, priority));
      if (cursor) {
        conditions.push(lt(conversations.lastActivityAt, sql`(SELECT last_activity_at FROM conversations WHERE id = ${cursor})`));
      }

      const rows = await db
        .select()
        .from(conversations)
        .where(and(...conditions))
        .orderBy(desc(conversations.lastActivityAt))
        .limit(limit + 1);

      const hasMore = rows.length > limit;
      const items = hasMore ? rows.slice(0, limit) : rows;
      return {
        items,
        nextCursor: hasMore ? items[items.length - 1].id : undefined,
      };
    }),

  get: protectedProcedure
    .input(z.object({ id: z.string().cuid2() }))
    .query(async ({ ctx, input }) => {
      const row = await db.query.conversations.findFirst({
        where: and(
          eq(conversations.id, input.id),
          eq(conversations.organizationId, ctx.organizationId)
        ),
        with: {
          messages: {
            orderBy: [messages.createdAt],
            limit: 50,
          },
        },
      });
      if (!row) throw new TRPCError({ code: "NOT_FOUND" });
      return row;
    }),

  create: protectedProcedure
    .input(
      z.object({
        channelType: z.enum(["email", "slack", "chat", "teams", "discord", "form", "api"]),
        channelId: z.string().cuid2().optional(),
        contactId: z.string().cuid2().optional(),
        companyId: z.string().cuid2().optional(),
        dealId: z.string().cuid2().optional(),
        subject: z.string().max(500).optional(),
        priority: z.enum(["urgent", "high", "medium", "low"]).default("medium"),
        firstMessage: z.object({
          bodyText: z.string().min(1).max(50000),
          bodyHtml: z.string().optional(),
          bodyTiptap: z.record(z.unknown()).optional(),
          attachments: z
            .array(
              z.object({
                filename: z.string(),
                mimeType: z.string(),
                size: z.number(),
                storageKey: z.string(),
              })
            )
            .optional(),
        }),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // 1. Create conversation
      // 2. Create first message
      // 3. Dispatch ai.triage job (async)
      // 4. Start SLA clock
      // 5. Emit account_activity
      // Implementation: see lib/cx/createConversation.ts
    }),

  reply: protectedProcedure
    .input(
      z.object({
        conversationId: z.string().cuid2(),
        bodyText: z.string().min(1).max(50000),
        bodyHtml: z.string().optional(),
        bodyTiptap: z.record(z.unknown()).optional(),
        attachments: z
          .array(z.object({ filename: z.string(), mimeType: z.string(), size: z.number(), storageKey: z.string() }))
          .optional(),
        messageType: z.enum(["outbound", "note"]).default("outbound"),
        // If accepting an AI draft
        aiSuggestionId: z.string().cuid2().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // 1. Verify conversation belongs to org
      // 2. Insert message
      // 3. Dispatch via channel adapter (email/slack/etc.)
      // 4. Update conversation.lastActivityAt
      // 5. Record first response time if applicable
      // 6. If aiSuggestionId, mark suggestion as accepted
    }),

  close: protectedProcedure
    .input(
      z.object({
        conversationId: z.string().cuid2(),
        resolution: z.string().max(1000).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Sets status = 'resolved', resolvedAt, emits activity
    }),

  reopen: protectedProcedure
    .input(z.object({ conversationId: z.string().cuid2() }))
    .mutation(async ({ ctx, input }) => {}),

  assign: protectedProcedure
    .input(
      z.object({
        conversationId: z.string().cuid2(),
        assigneeId: z.string().optional(),        // null to unassign
        teamId: z.string().optional(),
        note: z.string().max(500).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {}),

  snooze: protectedProcedure
    .input(
      z.object({
        conversationId: z.string().cuid2(),
        until: z.coerce.date(),
      })
    )
    .mutation(async ({ ctx, input }) => {}),

  tag: protectedProcedure
    .input(
      z.object({
        conversationId: z.string().cuid2(),
        tags: z.array(z.string().min(1).max(50)),
        action: z.enum(["add", "remove", "replace"]),
      })
    )
    .mutation(async ({ ctx, input }) => {}),

  getMessages: protectedProcedure
    .input(
      z.object({
        conversationId: z.string().cuid2(),
        cursor: cursorSchema,
        limit: z.number().min(1).max(100).default(50),
      })
    )
    .query(async ({ ctx, input }) => {
      // Cursor-based pagination of messages, oldest-first
    }),

  mergeTo: protectedProcedure
    .input(
      z.object({
        sourceConversationId: z.string().cuid2(),
        targetConversationId: z.string().cuid2(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Moves all messages from source to target, marks source as closed
    }),
});
```

---

### 3.2 Tickets Router (`server/routers/tickets.ts`)

```typescript
import { z } from "zod";
import { router, protectedProcedure } from "../trpc";
import { TRPCError } from "@trpc/server";

export const ticketsRouter = router({
  list: protectedProcedure
    .input(
      z.object({
        cursor: z.string().cuid2().optional(),
        limit: z.number().min(1).max(100).default(25),
        status: z
          .enum(["new", "open", "pending_customer", "pending_internal", "on_hold", "resolved", "closed"])
          .optional(),
        priority: z.enum(["urgent", "high", "medium", "low"]).optional(),
        assigneeId: z.string().optional(),
        companyId: z.string().cuid2().optional(),
        contactId: z.string().cuid2().optional(),
        ticketType: z
          .enum(["bug", "feature_request", "billing", "onboarding", "integration", "security", "general", "other"])
          .optional(),
        slaBreach: z.boolean().optional(),
        tags: z.array(z.string()).optional(),
        search: z.string().max(255).optional(),
        orderBy: z.enum(["created_at", "updated_at", "priority", "sla_due"]).default("created_at"),
        orderDir: z.enum(["asc", "desc"]).default("desc"),
      })
    )
    .query(async ({ ctx, input }) => {
      // Returns paginated { items: Ticket[], nextCursor?: string }
    }),

  get: protectedProcedure
    .input(z.object({ id: z.string().cuid2() }))
    .query(async ({ ctx, input }) => {
      // Returns ticket with related: conversation, contact, company, deal,
      // assignments, tags, slaStatus, aiSuggestions (pending)
    }),

  getByNumber: protectedProcedure
    .input(z.object({ number: z.number().int().positive() }))
    .query(async ({ ctx, input }) => {
      // Human-readable lookup via ticket number (org-scoped)
    }),

  create: protectedProcedure
    .input(
      z.object({
        title: z.string().min(1).max(500),
        description: z.string().max(50000).optional(),
        descriptionTiptap: z.record(z.unknown()).optional(),
        contactId: z.string().cuid2().optional(),
        companyId: z.string().cuid2().optional(),
        dealId: z.string().cuid2().optional(),
        conversationId: z.string().cuid2().optional(),
        priority: z.enum(["urgent", "high", "medium", "low"]).default("medium"),
        ticketType: z
          .enum(["bug", "feature_request", "billing", "onboarding", "integration", "security", "general", "other"])
          .default("general"),
        assigneeId: z.string().optional(),
        tags: z.array(z.string()).optional(),
        slaPolicyId: z.string().cuid2().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // 1. Generate ticket number (SELECT MAX(number)+1 WHERE org)
      // 2. Resolve default SLA policy if none specified
      // 3. Compute SLA due dates
      // 4. Create ticket + sla_status rows in transaction
      // 5. Emit account_activity
    }),

  update: protectedProcedure
    .input(
      z.object({
        id: z.string().cuid2(),
        title: z.string().min(1).max(500).optional(),
        description: z.string().max(50000).optional(),
        descriptionTiptap: z.record(z.unknown()).optional(),
        priority: z.enum(["urgent", "high", "medium", "low"]).optional(),
        ticketType: z
          .enum(["bug", "feature_request", "billing", "onboarding", "integration", "security", "general", "other"])
          .optional(),
        status: z
          .enum(["new", "open", "pending_customer", "pending_internal", "on_hold", "resolved", "closed"])
          .optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {}),

  assign: protectedProcedure
    .input(
      z.object({
        ticketId: z.string().cuid2(),
        assigneeId: z.string().optional(),
        teamId: z.string().optional(),
        note: z.string().max(500).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Writes ticket_assignments row, updates ticket.assigneeId
    }),

  resolve: protectedProcedure
    .input(
      z.object({
        ticketId: z.string().cuid2(),
        resolution: z.string().max(2000).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Sets status=resolved, resolvedAt, achieves SLA if within target
    }),

  escalate: protectedProcedure
    .input(
      z.object({
        ticketId: z.string().cuid2(),
        reason: z.string().min(1).max(1000),
        escalateTo: z.string().optional(), // Clerk user ID
        priority: z.enum(["urgent", "high"]).default("urgent"),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Bumps priority, reassigns, sends notification, logs activity
    }),

  addTag: protectedProcedure
    .input(
      z.object({
        ticketId: z.string().cuid2(),
        tag: z.string().min(1).max(50),
      })
    )
    .mutation(async ({ ctx, input }) => {}),

  removeTag: protectedProcedure
    .input(
      z.object({
        ticketId: z.string().cuid2(),
        tag: z.string().min(1).max(50),
      })
    )
    .mutation(async ({ ctx, input }) => {}),

  getSlaStatus: protectedProcedure
    .input(z.object({ ticketId: z.string().cuid2() }))
    .query(async ({ ctx, input }) => {
      // Returns all sla_status rows for ticket with remaining time calculated
    }),

  listTags: protectedProcedure
    .input(z.object({ search: z.string().optional() }))
    .query(async ({ ctx, input }) => {
      // Distinct tags used by org, ordered by frequency
    }),
});
```

---

### 3.3 Knowledge Base Router (`server/routers/knowledgeBase.ts`)

```typescript
import { z } from "zod";
import { router, protectedProcedure } from "../trpc";

export const knowledgeBaseRouter = router({
  // ── Articles ──────────────────────────────────────────────────────────────

  listArticles: protectedProcedure
    .input(
      z.object({
        cursor: z.string().cuid2().optional(),
        limit: z.number().min(1).max(100).default(20),
        collectionId: z.string().cuid2().optional(),
        status: z.enum(["draft", "in_review", "published", "archived"]).optional(),
        visibility: z.enum(["public", "internal", "restricted"]).optional(),
        search: z.string().max(255).optional(),
        tags: z.array(z.string()).optional(),
      })
    )
    .query(async ({ ctx, input }) => {}),

  getArticle: protectedProcedure
    .input(z.object({ id: z.string().cuid2() }))
    .query(async ({ ctx, input }) => {
      // Returns article + collection + version history (latest 5)
    }),

  getArticleBySlug: protectedProcedure
    .input(z.object({ slug: z.string() }))
    .query(async ({ ctx, input }) => {}),

  createArticle: protectedProcedure
    .input(
      z.object({
        collectionId: z.string().cuid2().optional(),
        title: z.string().min(1).max(500),
        slug: z.string().min(1).max(255).optional(), // auto-generated if omitted
        bodyText: z.string().optional(),
        bodyTiptap: z.record(z.unknown()).optional(),
        status: z.enum(["draft", "in_review", "published", "archived"]).default("draft"),
        visibility: z.enum(["public", "internal", "restricted"]).default("public"),
        tags: z.array(z.string()).optional(),
        metaTitle: z.string().max(255).optional(),
        metaDescription: z.string().max(500).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // 1. Auto-generate slug from title if not provided
      // 2. Create article
      // 3. Create version 1
    }),

  updateArticle: protectedProcedure
    .input(
      z.object({
        id: z.string().cuid2(),
        title: z.string().min(1).max(500).optional(),
        bodyText: z.string().optional(),
        bodyTiptap: z.record(z.unknown()).optional(),
        status: z.enum(["draft", "in_review", "published", "archived"]).optional(),
        visibility: z.enum(["public", "internal", "restricted"]).optional(),
        collectionId: z.string().cuid2().nullable().optional(),
        tags: z.array(z.string()).optional(),
        changeNote: z.string().max(500).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Creates new version row on each update
    }),

  publishArticle: protectedProcedure
    .input(z.object({ id: z.string().cuid2() }))
    .mutation(async ({ ctx, input }) => {}),

  archiveArticle: protectedProcedure
    .input(z.object({ id: z.string().cuid2() }))
    .mutation(async ({ ctx, input }) => {}),

  deleteArticle: protectedProcedure
    .input(z.object({ id: z.string().cuid2() }))
    .mutation(async ({ ctx, input }) => {}),

  getVersionHistory: protectedProcedure
    .input(
      z.object({
        articleId: z.string().cuid2(),
        cursor: z.string().cuid2().optional(),
        limit: z.number().min(1).max(50).default(20),
      })
    )
    .query(async ({ ctx, input }) => {}),

  restoreVersion: protectedProcedure
    .input(
      z.object({
        articleId: z.string().cuid2(),
        versionId: z.string().cuid2(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Creates new version from restored content
    }),

  // ── Collections ────────────────────────────────────────────────────────────

  listCollections: protectedProcedure
    .input(
      z.object({
        parentId: z.string().cuid2().nullable().optional(),
        visibility: z.enum(["public", "internal", "restricted"]).optional(),
      })
    )
    .query(async ({ ctx, input }) => {}),

  createCollection: protectedProcedure
    .input(
      z.object({
        name: z.string().min(1).max(255),
        slug: z.string().min(1).max(255).optional(),
        description: z.string().max(1000).optional(),
        parentId: z.string().cuid2().optional(),
        visibility: z.enum(["public", "internal", "restricted"]).default("public"),
        icon: z.string().optional(),
        position: z.number().int().default(0),
      })
    )
    .mutation(async ({ ctx, input }) => {}),

  updateCollection: protectedProcedure
    .input(
      z.object({
        id: z.string().cuid2(),
        name: z.string().min(1).max(255).optional(),
        description: z.string().max(1000).optional(),
        parentId: z.string().cuid2().nullable().optional(),
        visibility: z.enum(["public", "internal", "restricted"]).optional(),
        icon: z.string().optional(),
        position: z.number().int().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {}),

  deleteCollection: protectedProcedure
    .input(
      z.object({
        id: z.string().cuid2(),
        moveArticlesTo: z.string().cuid2().optional(), // collection to move articles to
      })
    )
    .mutation(async ({ ctx, input }) => {}),

  // ── Search & AI ────────────────────────────────────────────────────────────

  search: protectedProcedure
    .input(
      z.object({
        query: z.string().min(1).max(500),
        visibility: z.enum(["public", "internal", "restricted"]).optional(),
        limit: z.number().min(1).max(20).default(10),
      })
    )
    .query(async ({ ctx, input }) => {
      // Full-text search via Postgres tsvector + optional semantic search
      // Returns: articles with highlighted excerpts
    }),

  suggest: protectedProcedure
    .input(
      z.object({
        conversationId: z.string().cuid2().optional(),
        ticketId: z.string().cuid2().optional(),
        query: z.string().min(1).max(500),
        limit: z.number().min(1).max(5).default(3),
      })
    )
    .query(async ({ ctx, input }) => {
      // AI-powered: given conversation context, find relevant KB articles
      // Returns articles ranked by relevance with confidence scores
    }),

  detectGaps: protectedProcedure
    .input(
      z.object({
        since: z.coerce.date().optional(), // analyze conversations since this date
        limit: z.number().min(1).max(50).default(20),
      })
    )
    .query(async ({ ctx, input }) => {
      // Returns: array of detected knowledge gaps with supporting ticket refs
    }),

  aiDraftArticle: protectedProcedure
    .input(
      z.object({
        topic: z.string().min(1).max(500),
        context: z.string().max(5000).optional(),
        ticketIds: z.array(z.string().cuid2()).optional(),
        targetLength: z.enum(["short", "medium", "long"]).default("medium"),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Uses AI to draft a new article — saves as draft, returns articleId
    }),
});
```

---

### 3.4 Account Intelligence Router (`server/routers/accountIntelligence.ts`)

```typescript
import { z } from "zod";
import { router, protectedProcedure } from "../trpc";

export const accountIntelligenceRouter = router({
  getHealth: protectedProcedure
    .input(z.object({ companyId: z.string().cuid2() }))
    .query(async ({ ctx, input }) => {
      // Returns latest account_health_scores row with factors breakdown
    }),

  getHealthHistory: protectedProcedure
    .input(
      z.object({
        companyId: z.string().cuid2(),
        days: z.number().int().min(7).max(365).default(90),
      })
    )
    .query(async ({ ctx, input }) => {
      // Historical score snapshots for trend chart
    }),

  getSignals: protectedProcedure
    .input(
      z.object({
        companyId: z.string().cuid2(),
        cursor: z.string().cuid2().optional(),
        limit: z.number().min(1).max(100).default(20),
        signalType: z
          .enum([
            "ticket_volume_spike",
            "ticket_sentiment_negative",
            "ticket_sentiment_positive",
            "sla_breach",
            "response_time_slow",
            "unresolved_tickets_high",
            "conversation_frequency_drop",
            "no_recent_activity",
            "feature_request_submitted",
            "usage_drop",
            "usage_spike",
            "deal_stage_advanced",
            "deal_at_risk",
            "renewal_approaching",
            "payment_failed",
            "onboarding_incomplete",
            "onboarding_completed",
          ])
          .optional(),
        activeOnly: z.boolean().default(true),
      })
    )
    .query(async ({ ctx, input }) => {}),

  getActivity: protectedProcedure
    .input(
      z.object({
        companyId: z.string().cuid2(),
        cursor: z.string().cuid2().optional(),
        limit: z.number().min(1).max(100).default(25),
        activityType: z
          .enum([
            "ticket_created",
            "ticket_resolved",
            "conversation_opened",
            "conversation_closed",
            "deal_stage_changed",
            "note_added",
            "feature_request_linked",
            "health_score_changed",
            "contact_added",
            "meeting_logged",
          ])
          .optional(),
      })
    )
    .query(async ({ ctx, input }) => {
      // Unified activity feed — CX + CRM events merged chronologically
    }),

  computeHealth: protectedProcedure
    .input(
      z.object({
        companyId: z.string().cuid2(),
        force: z.boolean().default(false), // force recompute even if recent
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Triggers health score recomputation via lib/ai/health-score.ts
      // Returns new score immediately (sync) and stores snapshot
    }),

  listAtRisk: protectedProcedure
    .input(
      z.object({
        cursor: z.string().cuid2().optional(),
        limit: z.number().min(1).max(100).default(25),
        churnRiskMin: z.number().min(0).max(1).default(0.6),
      })
    )
    .query(async ({ ctx, input }) => {
      // Companies ordered by churnRisk descending with health snapshots
    }),

  listHealthSummary: protectedProcedure
    .input(
      z.object({
        cursor: z.string().cuid2().optional(),
        limit: z.number().min(1).max(100).default(50),
        orderBy: z.enum(["overall_score", "churn_risk", "expansion_potential"]).default("overall_score"),
        orderDir: z.enum(["asc", "desc"]).default("asc"),
      })
    )
    .query(async ({ ctx, input }) => {
      // All companies with health scores for dashboard grid
    }),
});
```

---

### 3.5 Product Intelligence Router (`server/routers/productIntelligence.ts`)

```typescript
import { z } from "zod";
import { router, protectedProcedure } from "../trpc";

export const productIntelligenceRouter = router({
  listRequests: protectedProcedure
    .input(
      z.object({
        cursor: z.string().cuid2().optional(),
        limit: z.number().min(1).max(100).default(25),
        status: z
          .enum(["under_review", "planned", "in_progress", "shipped", "declined", "duplicate"])
          .optional(),
        productArea: z.string().optional(),
        tags: z.array(z.string()).optional(),
        orderBy: z
          .enum(["priority_score", "mention_count", "revenue_impact", "created_at"])
          .default("priority_score"),
        orderDir: z.enum(["asc", "desc"]).default("desc"),
      })
    )
    .query(async ({ ctx, input }) => {}),

  getRequest: protectedProcedure
    .input(z.object({ id: z.string().cuid2() }))
    .query(async ({ ctx, input }) => {
      // Returns feature request + all evidence + requesting companies + revenue impact
    }),

  createRequest: protectedProcedure
    .input(
      z.object({
        title: z.string().min(1).max(500),
        description: z.string().max(5000).optional(),
        productArea: z.string().optional(),
        tags: z.array(z.string()).optional(),
        externalIssueUrl: z.string().url().optional(),
        ownerId: z.string().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {}),

  updateRequest: protectedProcedure
    .input(
      z.object({
        id: z.string().cuid2(),
        title: z.string().min(1).max(500).optional(),
        description: z.string().max(5000).optional(),
        status: z
          .enum(["under_review", "planned", "in_progress", "shipped", "declined", "duplicate"])
          .optional(),
        productArea: z.string().optional(),
        tags: z.array(z.string()).optional(),
        externalIssueUrl: z.string().url().nullable().optional(),
        ownerId: z.string().nullable().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {}),

  cluster: protectedProcedure
    .input(
      z.object({
        ticketIds: z.array(z.string().cuid2()).optional(),  // specific tickets to cluster
        since: z.coerce.date().optional(),                  // cluster all since date
        minClusterSize: z.number().int().min(2).default(3),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // AI-powered clustering of feature mentions into request groups
      // Returns: { clustersCreated: number, clustersUpdated: number, evidenceLinked: number }
    }),

  linkEvidence: protectedProcedure
    .input(
      z.object({
        featureRequestId: z.string().cuid2(),
        sourceType: z.enum(["ticket", "message", "conversation"]),
        sourceId: z.string().cuid2(),
        excerpt: z.string().max(2000).optional(),
        humanVerified: z.boolean().default(true),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Manually links a ticket/message to a feature request
      // Updates mention count and revenue impact
    }),

  unlinkEvidence: protectedProcedure
    .input(z.object({ evidenceId: z.string().cuid2() }))
    .mutation(async ({ ctx, input }) => {}),

  getRevenueSummary: protectedProcedure
    .input(z.object({ featureRequestId: z.string().cuid2() }))
    .query(async ({ ctx, input }) => {
      // Returns ARR breakdown by company for a feature request
    }),
});
```

---

### 3.6 Channels Router (`server/routers/channels.ts`)

```typescript
import { z } from "zod";
import { router, protectedProcedure } from "../trpc";

const channelTypeEnum = z.enum(["email", "slack", "chat", "teams", "discord", "form", "api"]);

export const channelsRouter = router({
  list: protectedProcedure
    .query(async ({ ctx }) => {
      // Returns all channels + connections for org
    }),

  get: protectedProcedure
    .input(z.object({ id: z.string().cuid2() }))
    .query(async ({ ctx, input }) => {}),

  connect: protectedProcedure
    .input(
      z.object({
        channelType: channelTypeEnum,
        name: z.string().min(1).max(255),
        config: z.record(z.unknown()).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Creates channel + channel_connection rows
      // For OAuth channels (Slack), returns OAuth URL
      // For email, provisions Resend inbound address
    }),

  disconnect: protectedProcedure
    .input(z.object({ channelId: z.string().cuid2() }))
    .mutation(async ({ ctx, input }) => {
      // Revokes tokens, deactivates channel, does NOT delete history
    }),

  configure: protectedProcedure
    .input(
      z.object({
        channelId: z.string().cuid2(),
        // Email-specific
        customDomain: z.string().optional(),
        // Slack-specific
        defaultAssigneeId: z.string().optional(),
        // Chat widget-specific
        allowedOrigins: z.array(z.string()).optional(),
        widgetConfig: z
          .object({
            primaryColor: z.string().optional(),
            greeting: z.string().max(500).optional(),
            offlineMessage: z.string().max(500).optional(),
            position: z.enum(["bottom-right", "bottom-left"]).optional(),
          })
          .optional(),
        // General
        name: z.string().min(1).max(255).optional(),
        isActive: z.boolean().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {}),

  getEmailAddress: protectedProcedure
    .input(z.object({ channelId: z.string().cuid2() }))
    .query(async ({ ctx, input }) => {
      // Returns the inbound email address for this email channel
    }),

  rotateWidgetKey: protectedProcedure
    .input(z.object({ channelId: z.string().cuid2() }))
    .mutation(async ({ ctx, input }) => {
      // Rotates widget public key — existing widget installations stop working
    }),

  testConnection: protectedProcedure
    .input(z.object({ channelId: z.string().cuid2() }))
    .mutation(async ({ ctx, input }) => {
      // Sends test message through the channel to verify config
    }),

  getWebhookUrl: protectedProcedure
    .input(z.object({ channelId: z.string().cuid2() }))
    .query(async ({ ctx, input }) => {
      // Returns the inbound webhook URL for this channel
    }),
});
```

---

### 3.7 Workflows Router (`server/routers/workflows.ts`)

```typescript
import { z } from "zod";
import { router, protectedProcedure } from "../trpc";

const triggerTypeEnum = z.enum([
  "conversation_created", "conversation_status_changed",
  "ticket_created", "ticket_status_changed", "ticket_assigned",
  "sla_breach_imminent", "sla_breached", "message_received",
  "health_score_changed", "manual", "scheduled", "webhook",
]);

const conditionSchema = z.object({
  field: z.string(),
  operator: z.enum(["eq", "neq", "contains", "not_contains", "gt", "lt", "is_set", "is_empty"]),
  value: z.unknown(),
});

const stepConfigSchema = z.record(z.unknown());

export const workflowsRouter = router({
  list: protectedProcedure
    .input(
      z.object({
        cursor: z.string().cuid2().optional(),
        limit: z.number().min(1).max(100).default(25),
        isActive: z.boolean().optional(),
        triggerType: triggerTypeEnum.optional(),
      })
    )
    .query(async ({ ctx, input }) => {}),

  get: protectedProcedure
    .input(z.object({ id: z.string().cuid2() }))
    .query(async ({ ctx, input }) => {
      // Returns workflow + all steps (ordered by position) + recent runs (5)
    }),

  create: protectedProcedure
    .input(
      z.object({
        name: z.string().min(1).max(255),
        description: z.string().max(1000).optional(),
        triggerType: triggerTypeEnum,
        triggerConditions: z.array(conditionSchema).optional(),
        steps: z.array(
          z.object({
            stepType: z.string(),
            position: z.number().int(),
            config: stepConfigSchema,
            nextStepId: z.string().optional(),
            nextStepIdOnTrue: z.string().optional(),
            nextStepIdOnFalse: z.string().optional(),
          })
        ),
        isActive: z.boolean().default(false),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Creates workflow + all steps in transaction
    }),

  update: protectedProcedure
    .input(
      z.object({
        id: z.string().cuid2(),
        name: z.string().min(1).max(255).optional(),
        description: z.string().max(1000).optional(),
        triggerConditions: z.array(conditionSchema).optional(),
        isActive: z.boolean().optional(),
        // Steps are replaced wholesale on update
        steps: z
          .array(
            z.object({
              id: z.string().cuid2().optional(), // existing step ID to retain
              stepType: z.string(),
              position: z.number().int(),
              config: stepConfigSchema,
              nextStepId: z.string().optional(),
              nextStepIdOnTrue: z.string().optional(),
              nextStepIdOnFalse: z.string().optional(),
            })
          )
          .optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {}),

  delete: protectedProcedure
    .input(z.object({ id: z.string().cuid2() }))
    .mutation(async ({ ctx, input }) => {}),

  activate: protectedProcedure
    .input(z.object({ id: z.string().cuid2() }))
    .mutation(async ({ ctx, input }) => {}),

  deactivate: protectedProcedure
    .input(z.object({ id: z.string().cuid2() }))
    .mutation(async ({ ctx, input }) => {}),

  run: protectedProcedure
    .input(
      z.object({
        workflowId: z.string().cuid2(),
        // Context payload for manual runs
        conversationId: z.string().cuid2().optional(),
        ticketId: z.string().cuid2().optional(),
        companyId: z.string().cuid2().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Manually triggers a workflow run
      // Returns workflowRunId for polling
    }),

  history: protectedProcedure
    .input(
      z.object({
        workflowId: z.string().cuid2(),
        cursor: z.string().cuid2().optional(),
        limit: z.number().min(1).max(100).default(25),
        status: z.enum(["pending", "running", "completed", "failed", "cancelled"]).optional(),
      })
    )
    .query(async ({ ctx, input }) => {}),

  getRun: protectedProcedure
    .input(z.object({ runId: z.string().cuid2() }))
    .query(async ({ ctx, input }) => {
      // Returns run with full execution log
    }),
});
```

---

### 3.8 AI Router (`server/routers/ai.ts`)

```typescript
import { z } from "zod";
import { router, protectedProcedure } from "../trpc";

export const aiRouter = router({
  triage: protectedProcedure
    .input(
      z.object({
        conversationId: z.string().cuid2(),
        force: z.boolean().default(false),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Runs full AI triage pipeline:
      // 1. Classify ticket type
      // 2. Score priority (0-100)
      // 3. Detect sentiment
      // 4. Extract topics
      // 5. Suggest assignee
      // 6. Check if KB article exists
      // 7. Save ai_action log + ai_suggestions
      // Returns: { priority, sentiment, topics, suggestedAssignee, kbMatches }
    }),

  suggestResponse: protectedProcedure
    .input(
      z.object({
        conversationId: z.string().cuid2(),
        // Optional context hints
        tone: z.enum(["formal", "friendly", "technical", "empathetic"]).optional(),
        includeKbSource: z.boolean().default(true),
        maxLength: z.number().int().min(50).max(2000).default(500),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Context assembly: conversation history + contact record + company record
      // + deal stage + open tickets + KB semantic search
      // Returns: { draft: string, draftTiptap: object, kbSourceIds: string[], aiSuggestionId: string }
    }),

  categorize: protectedProcedure
    .input(
      z.object({
        conversationId: z.string().cuid2().optional(),
        ticketId: z.string().cuid2().optional(),
        text: z.string().min(1).max(10000).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Returns: { ticketType, productArea, tags, topics, sentiment, urgency }
    }),

  detectKnowledgeGaps: protectedProcedure
    .input(
      z.object({
        since: z.coerce.date().optional(),
        minTicketCount: z.number().int().min(1).default(3),
        limit: z.number().int().min(1).max(50).default(20),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Analyzes recent conversations, groups uncovered topics
      // Returns: array of { topic, description, supportingTicketIds, suggestedArticleTitle }
    }),

  summarizeConversation: protectedProcedure
    .input(z.object({ conversationId: z.string().cuid2() }))
    .mutation(async ({ ctx, input }) => {
      // Returns: { summary, keyPoints, nextSteps, sentiment }
    }),

  getSuggestions: protectedProcedure
    .input(
      z.object({
        conversationId: z.string().cuid2().optional(),
        ticketId: z.string().cuid2().optional(),
        status: z.enum(["pending", "accepted", "rejected", "auto_applied", "expired"]).optional(),
      })
    )
    .query(async ({ ctx, input }) => {}),

  reviewSuggestion: protectedProcedure
    .input(
      z.object({
        suggestionId: z.string().cuid2(),
        action: z.enum(["accept", "reject"]),
        reason: z.string().max(500).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Marks suggestion as accepted/rejected, applies if accepted
    }),

  getUsage: protectedProcedure
    .input(
      z.object({
        since: z.coerce.date().optional(),
        until: z.coerce.date().optional(),
        actionType: z.string().optional(),
      })
    )
    .query(async ({ ctx, input }) => {
      // Returns token usage, cost estimate, action type breakdown
    }),
});
```

---

## 4. Channel Integration Architecture

### 4.1 Slack Integration (`lib/channels/slack.ts`)

**Architecture: Slack Connect + Bot**

Slack Connect channels allow B2B companies to connect their Slack workspace with a customer's Slack workspace. The bot monitors these shared channels, threading conversations back to ellocharlie.

```
Customer Slack workspace                ellocharlie backend
────────────────────────────────────    ────────────────────────────
#company-acme-support (Connect)         
  Customer posts message         ───→   Slack Events API POST /webhooks/slack
                                        │
                                        ▼
                                        lib/channels/slack.ts
                                        verifySlackSignature(req)
                                        │
                                        ▼
                                        resolveConversation(thread_ts)
                                        │
                                        ├── existing? → append message
                                        └── new? → createConversation()
                                                    + auto-triage
                                                    + notify assignee
                                        
Agent replies in ellocharlie inbox ───→ POST /api/slack/send
                                        Slack Web API: chat.postMessage
                                        channel: C12345, thread_ts: ...
                                        
                                  ←─── Message appears in Slack thread
```

**Setup flow:**
1. Org admin clicks "Connect Slack" → OAuth 2.0 flow with `channels:read`, `chat:write`, `chat:write.public`, `reactions:read`, `team:read` scopes
2. Bot installed to workspace, `bot_user_id` stored
3. Admin selects which Slack Connect channels to monitor
4. `channel_connections` row created with `slackBotToken`, `slackWorkspaceId`
5. Channel registered for Events API at `https://api.ellocharlie.app/webhooks/slack/{orgId}`

**Key implementation details:**

```typescript
// lib/channels/slack.ts

import { WebClient } from "@slack/web-api";
import { createHmac } from "crypto";

export interface SlackInboundEvent {
  type: string;
  event: {
    type: "message";
    ts: string;
    thread_ts?: string;
    channel: string;
    user: string;
    text: string;
    files?: SlackFile[];
    subtype?: string;     // 'bot_message' | 'file_share' | etc.
  };
  team_id: string;
}

export function verifySlackSignature(
  signingSecret: string,
  rawBody: string,
  timestamp: string,
  signature: string
): boolean {
  const base = `v0:${timestamp}:${rawBody}`;
  const expected = `v0=${createHmac("sha256", signingSecret).update(base).digest("hex")}`;
  return expected === signature;
}

export async function normalizeSlackEvent(
  event: SlackInboundEvent,
  client: WebClient
): Promise<CanonicalMessage> {
  // Resolve user info from Slack API (cached)
  const userInfo = await client.users.info({ user: event.event.user });
  // Upload any files to R2
  const attachments = await processSlackFiles(event.event.files ?? []);
  
  return {
    channelType: "slack",
    externalId: event.event.ts,
    externalThreadId: event.event.thread_ts,
    from: {
      address: userInfo.user?.profile?.email ?? `${event.event.user}@slack`,
      name: userInfo.user?.real_name,
    },
    bodyText: event.event.text,
    attachments,
    metadata: {
      slackChannel: event.event.channel,
      slackWorkspace: event.team_id,
      slackUserId: event.event.user,
    },
    receivedAt: new Date(parseFloat(event.event.ts) * 1000),
  };
}

export async function sendSlackReply(
  client: WebClient,
  channelId: string,
  threadTs: string,
  text: string,
  htmlBlocks?: object[]
): Promise<void> {
  await client.chat.postMessage({
    channel: channelId,
    thread_ts: threadTs,
    text,
    blocks: htmlBlocks, // Block Kit formatting
  });
}
```

**Thread-to-ticket conversion:**
- Every new Slack thread in a monitored channel → auto-creates a conversation + ticket
- Thread replies → append as messages to existing conversation
- Emoji reactions (✅ 🎫) → trigger status changes (e.g., ✅ = resolved)
- Bot posts back to Slack thread with ticket number: "Ticket #42 created — [View →](https://app.ellocharlie.app/tickets/42)"

---

### 4.2 Email Integration (`lib/channels/email.ts`)

**Architecture: Inbound via Resend webhook, outbound via Resend API**

```
Customer sends to: support@acme.ellocharlie.app (or support@acme.com w/ DNS)
         │
         ▼
Resend inbound email routing
         │
         ▼
POST /webhooks/email/{orgId}/{channelId}
Content-Type: application/json
{
  "from": "customer@example.com",
  "to": ["support@acme.ellocharlie.app"],
  "subject": "Integration not working",
  "html": "...",
  "text": "...",
  "messageId": "<msg-id@example.com>",
  "references": ["<previous@example.com>"],
  "attachments": [...]
}
         │
         ▼
lib/channels/email.ts
  1. Verify Resend webhook signature
  2. Thread detection: match References header to existing conversation.externalId
  3. Contact resolution: match From email → existing contact → else create new
  4. createConversation() or appendMessage()
  5. Trigger AI triage
```

**Thread tracking strategy:**
- `conversation.externalId` = canonical Message-ID of the first email in thread
- `message.emailHeaders.references` array → match against existing conversation IDs
- If match found → append to conversation
- If no match → create new conversation

**Outbound reply:**
```typescript
// lib/channels/email.ts

import { Resend } from "resend";

const resend = new Resend(process.env.RESEND_API_KEY);

export async function sendEmailReply(opts: {
  to: string;
  from: string;           // verified Resend address
  subject: string;
  bodyHtml: string;
  bodyText: string;
  replyToMessageId?: string; // for In-Reply-To header
  references?: string[];    // for References header
  attachments?: { filename: string; content: Buffer; contentType: string }[];
}): Promise<{ messageId: string }> {
  const result = await resend.emails.send({
    from: opts.from,
    to: opts.to,
    subject: opts.subject.startsWith("Re:") ? opts.subject : `Re: ${opts.subject}`,
    html: opts.bodyHtml,
    text: opts.bodyText,
    headers: {
      "In-Reply-To": opts.replyToMessageId ?? "",
      References: [...(opts.references ?? []), opts.replyToMessageId ?? ""].filter(Boolean).join(" "),
    },
    attachments: opts.attachments,
  });
  return { messageId: result.data?.id ?? "" };
}
```

**Custom domain setup:**
1. Org admin adds domain (e.g., `acme.com`)
2. ellocharlie provisions Resend domain via API, returns DNS records
3. Admin adds DNS records (MX, DKIM, SPF)
4. ellocharlie verifies domain is active via Resend API
5. Admin sets routing: `support@acme.com` → `support@acme.ellocharlie.app` (MX record)

---

### 4.3 Live Chat Widget (`lib/widgets/chat-widget/`)

**Architecture: Embeddable JS snippet + WebSocket for real-time**

```html
<!-- Customer installs on their website -->
<script>
  window.ElloCharlie = window.ElloCharlie || {};
  window.ElloCharlie.apiKey = "pk_live_xxxx";
  window.ElloCharlie.orgId  = "org_xxxx";
</script>
<script src="https://widget.ellocharlie.app/v1/widget.js" async></script>
```

**Widget architecture:**

```
Browser (customer's website)                  ellocharlie backend
────────────────────────────                  ──────────────────
widget.js (< 15kb gzipped)
  │
  ├── Shadow DOM iframe (isolated CSS)
  │   └── React (preact for size) UI
  │
  ├── REST: POST /api/widget/session
  │   { apiKey, visitorId (anon CUID), url, referrer }  ──────→  creates/resumes session
  │                                               ←──────  { sessionToken, conversation? }
  │
  └── WebSocket: wss://ws.ellocharlie.app/widget
      { sessionToken }
      │
      ├── SEND: { type: "message", body: "..." }  ──────→  creates message + triage
      ├── RECV: { type: "message", body: "...", author: "Agent" }
      ├── RECV: { type: "typing", authorName: "..." }
      └── RECV: { type: "status_change", status: "resolved" }
```

**WebSocket server** (Hono + Cloudflare Durable Objects or native WS on Cloud Run):
```typescript
// lib/widgets/chat-widget/ws-handler.ts

export interface ChatSession {
  sessionToken: string;
  organizationId: string;
  conversationId: string;
  visitorId: string;
  contactId?: string;
}

export type WidgetInboundEvent =
  | { type: "message"; body: string; attachments?: CanonicalAttachment[] }
  | { type: "typing" }
  | { type: "read"; messageId: string }
  | { type: "identify"; email: string; name?: string };

export type WidgetOutboundEvent =
  | { type: "message"; id: string; body: string; authorName: string; authorType: "agent" | "bot"; createdAt: string }
  | { type: "typing"; authorName: string }
  | { type: "status_change"; status: "open" | "resolved" }
  | { type: "ai_greeting"; body: string };
```

**Widget initialization flow:**
1. Widget loads, reads `apiKey` from `window.ElloCharlie`
2. `POST /api/widget/session` → verify `apiKey` against `channel_connections.widgetPublicKey` + check `allowedOrigins`
3. If returning visitor (matching `visitorId` cookie), resume existing open conversation
4. WebSocket opened with `sessionToken`
5. AI greeting sent if org has configured one
6. On visitor identifying (email capture form) → `identify` event → resolve/create contact → enrich conversation

---

### 4.4 Forms Integration (`lib/channels/forms.ts`)

**Configurable ticket submission forms embedded anywhere.**

```typescript
// Form schema definition (stored in channel_connections.config)
export interface FormConfig {
  title: string;
  fields: FormField[];
  successMessage: string;
  notifyAssignee?: string;  // default assignee Clerk user ID
  slaPolicyId?: string;
  defaultPriority?: "urgent" | "high" | "medium" | "low";
  defaultTicketType?: string;
  redirectUrl?: string;
}

export interface FormField {
  name: string;
  label: string;
  type: "text" | "textarea" | "email" | "select" | "checkbox" | "file";
  required: boolean;
  options?: string[];       // for select
  maxLength?: number;
  placeholder?: string;
}
```

**Submission endpoint:** `POST /api/widget/form/{channelId}`
- Validates CORS origin against `allowedOrigins`
- Validates all required fields
- Creates conversation + ticket
- Sends confirmation email via Resend
- Returns `{ ticketId, ticketNumber, message: "We'll be in touch shortly." }`

**Embeddable form snippet:**
```html
<script src="https://widget.ellocharlie.app/v1/form.js" 
        data-channel-id="ch_xxxx"
        async>
</script>
<div id="ellocharlie-form"></div>
```

---

### 4.5 REST API Channel (`lib/channels/api.ts`)

For programmatic ticket creation from customer applications.

```typescript
// POST /api/v1/conversations
// Authorization: Bearer {org_api_key}
// Content-Type: application/json

export interface ApiCreateConversationRequest {
  channelType?: "api";
  contactEmail: string;         // required — used to resolve/create contact
  contactName?: string;
  companyDomain?: string;       // used to resolve/create company
  subject: string;
  body: string;
  bodyHtml?: string;
  priority?: "urgent" | "high" | "medium" | "low";
  ticketType?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;  // arbitrary key-value, stored in message.metadata
  externalId?: string;          // caller's own ID for idempotency
}

export interface ApiCreateConversationResponse {
  id: string;
  ticketId: string;
  ticketNumber: number;
  contactId: string;
  companyId?: string;
  status: "open";
  createdAt: string;
}
```

**API key management:**
- Org generates API keys in Settings → Developer → API Keys
- Keys scoped to `read` or `read_write`
- Keys stored hashed (bcrypt), prefix stored for display (`ec_live_xxxx...`)
- All API calls log to `ai_actions` for usage tracking

---

### 4.6 Outbound Webhooks

ellocharlie emits webhooks for all CX events. Orgs configure webhook endpoints in Settings → Developer → Webhooks.

```typescript
// Webhook event catalog

export type WebhookEventType =
  | "conversation.created"
  | "conversation.status_changed"
  | "conversation.assigned"
  | "message.received"
  | "message.sent"
  | "ticket.created"
  | "ticket.status_changed"
  | "ticket.assigned"
  | "ticket.resolved"
  | "sla.breach_imminent"        // 15min before breach
  | "sla.breached"
  | "health_score.changed"
  | "feature_request.created"
  | "workflow.run_completed"
  | "workflow.run_failed";

export interface WebhookPayload<T extends WebhookEventType, D> {
  id: string;                    // webhook delivery ID (cuid2)
  type: T;
  organizationId: string;
  createdAt: string;             // ISO 8601
  data: D;
}

// Example payload for ticket.created
export type TicketCreatedPayload = WebhookPayload<
  "ticket.created",
  {
    ticket: {
      id: string;
      number: number;
      title: string;
      status: string;
      priority: string;
      ticketType: string;
      contactId?: string;
      companyId?: string;
      createdAt: string;
    };
    conversation?: { id: string; channelType: string };
  }
>;
```

**Delivery mechanics:**
- Signed with `HMAC-SHA256` using `webhookSecret`, sent as `X-ElloCharlie-Signature-256` header
- 3 retries with exponential backoff: 5s, 30s, 5m
- Delivery logged with status (success/failed/retrying) + response code
- Dead letter queue after 3 failures — admin can replay from dashboard
- Webhook endpoint must respond `200-299` within 10s

---

## 5. AI Agent Architecture

### 5.1 AI Triage Pipeline (`lib/ai/triage.ts`)

Runs asynchronously after every new inbound message. Completes within 2-3 seconds.

```
NEW MESSAGE RECEIVED
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  CONTEXT ASSEMBLER (lib/ai/context.ts)                      │
│                                                             │
│  Pulls in parallel:                                         │
│  ├── conversation.messages (last 10)                        │
│  ├── contact record (name, role, company, deal stage)       │
│  ├── company record (ARR tier, plan, health score)          │
│  ├── open tickets count (for volume spike detection)        │
│  └── recent account_signals (last 30 days)                  │
│                                                             │
│  Assembles: TriageContext {                                  │
│    conversationId, organizationId,                          │
│    customerContext, companyContext, messageHistory,          │
│    openTicketCount, recentSignals                           │
│  }                                                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│  CLASSIFY    │  │  PRIORITIZE  │  │  SENTIMENT       │
│              │  │              │  │                  │
│  ticketType  │  │  0-100 score │  │  positive/       │
│  productArea │  │  Factors:    │  │  neutral/        │
│  tags        │  │  • urgency   │  │  negative/       │
│  topics      │  │    words     │  │  frustrated      │
│              │  │  • ARR tier  │  │                  │
│  Model:      │  │  • health    │  │  Also: churn     │
│  GPT-4o-mini │  │    score     │  │  risk words      │
│  structured  │  │  • open      │  │  detection       │
│  output      │  │    tickets   │  │                  │
└──────┬───────┘  └──────┬───────┘  └──────────┬───────┘
       │                 │                      │
       └─────────────────┴──────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  ROUTING SUGGESTION │
              │                     │
              │  Based on:          │
              │  • ticketType       │
              │  • priority score   │
              │  • team workload    │
              │  • skills (future)  │
              │                     │
              │  Output:            │
              │  suggestedAssignee  │
              │  suggestedTeam      │
              │  confidence         │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  KB MATCH CHECK     │
              │                     │
              │  Semantic search    │
              │  against published  │
              │  KB articles        │
              │                     │
              │  Returns top 3      │
              │  with similarity    │
              │  scores             │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  WRITE RESULTS      │
              │                     │
              │  • Update           │
              │    conversation     │
              │    (aiTopics,       │
              │    aiSentiment,     │
              │    aiPriorityScore) │
              │  • Create           │
              │    ai_suggestions   │
              │  • Log ai_action    │
              └─────────────────────┘
```

**Classification prompt design (structured output):**
```typescript
// lib/ai/triage.ts

const triageOutputSchema = z.object({
  ticketType: z.enum(["bug", "feature_request", "billing", "onboarding", "integration", "security", "general"]),
  productArea: z.string().max(100),
  topics: z.array(z.string()).max(5),
  tags: z.array(z.string()).max(8),
  priorityScore: z.number().int().min(0).max(100),
  priorityRationale: z.string().max(200),
  sentiment: z.enum(["positive", "neutral", "negative", "frustrated"]),
  churnRiskMentioned: z.boolean(),
  urgencyWords: z.array(z.string()),
  suggestedAssigneeReason: z.string().max(200).optional(),
});

export async function triageConversation(
  context: TriageContext,
  orgId: string
): Promise<z.infer<typeof triageOutputSchema>> {
  const systemPrompt = `You are a B2B SaaS support triage system for ${context.companyContext?.name ?? "a company"}.
Analyze the incoming support conversation and extract structured metadata.

Company context:
- ARR tier: ${context.companyContext?.arrTier ?? "unknown"}
- Plan: ${context.companyContext?.plan ?? "unknown"}
- Health score: ${context.companyContext?.healthScore ?? "unknown"}
- Open tickets: ${context.openTicketCount}
- Recent signals: ${context.recentSignals.map(s => s.signalType).join(", ") || "none"}

Priority scoring guidance (0-100):
- 90-100: Critical ("can't login", "data loss", "security breach", "down")
- 70-89:  High urgency + high ARR, or executive escalation
- 50-69:  Standard issue from healthy account
- 30-49:  Feature request or low urgency question
- 0-29:   General inquiry, clearly non-urgent
`;

  // Using OpenAI structured output / Anthropic tool use
  // Returns parsed + validated triageOutputSchema result
}
```

---

### 5.2 AI Response Drafting (`lib/ai/draft.ts`)

Triggered when an agent clicks "Draft Reply" or when triage confidence is high.

**Context assembly for drafts:**
```typescript
export interface DraftContext {
  // Conversation
  conversationHistory: { author: string; body: string; createdAt: string }[];
  // CRM graph
  contactName: string;
  contactRole?: string;
  companyName: string;
  companyPlan?: string;
  dealStage?: string;
  // Relevant KB articles (semantic search results)
  relevantArticles: { title: string; bodyText: string; url: string }[];
  // Previous resolutions (similar closed tickets)
  similarResolutions: { title: string; resolution: string }[];
  // Org-level settings
  brandVoice?: string;   // "friendly and technical" | "formal" | etc.
  signature?: string;
}
```

**Draft output includes:**
- `draft`: plain text version
- `draftTiptap`: rich Tiptap JSON with formatted links to KB articles
- `kbSourceIds`: which KB articles were used (for citation)
- `confidenceScore`: 0-1 how confident the AI is
- `caveats`: if AI is uncertain about something, flags it

**Grounding strategy:**
1. Run semantic search against KB articles: `SELECT ... WHERE org AND published ORDER BY embedding <-> query_embedding LIMIT 5`
2. Include top 3 articles in context (truncated to 500 chars each)
3. AI instructed to cite articles and never invent answers not in KB
4. If no relevant KB content found → draft includes `[I don't have a KB article for this — would you like me to draft one?]` flag

---

### 5.3 Knowledge Gap Detection (`lib/ai/knowledge-gaps.ts`)

Runs as a daily background job. Scans closed conversations from the past 7 days.

**Algorithm:**
```
1. Fetch closed conversations (last 7 days) where ai_kb_match_score < 0.5
   (low KB match = question wasn't covered)

2. Extract message bodies (customer messages only, first message per conversation)

3. Batch into groups of 20, send to AI:
   "Identify distinct topics that are not covered by the knowledge base.
    Group similar topics together. For each gap, provide:
    - topic name
    - 2-sentence description
    - suggested article title
    - supporting conversation IDs"

4. Dedup against existing ai_suggestions of type 'knowledge_gap'

5. Create ai_suggestion rows for net-new gaps

6. Notify KB owners via email/Slack (if configured)
```

**Gap scoring:** gaps with 5+ supporting tickets are flagged as "critical" and appear at top of KB management view.

---

### 5.4 Account Health Scoring (`lib/ai/health-score.ts`)

Computes a 0-100 composite health score per company. Run hourly as a background job, or on-demand via `accountIntelligence.computeHealth`.

**Scoring model (weighted factors):**

| Factor | Weight | How it's measured |
|--------|--------|-------------------|
| Support ticket volume (30d) | -15% | Spike vs. rolling avg → `ticket_volume_spike` signal |
| Avg sentiment (30d) | +/-20% | Mean of `conversation.aiSentiment` scores |
| SLA breach rate (30d) | -15% | `sla_status` breach rows / total |
| Response time | +/-10% | Avg time-to-first-response vs. SLA target |
| Unresolved tickets | -15% | Count open > 7 days |
| Deal stage | +20% | `expansion` stage = +20, `churned` = -50, `closed_won` = +15 |
| Feature requests submitted | +5% | Engagement signal (not purely negative) |
| Recency of last interaction | +/-10% | Days since last message |
| Payment status (from Stripe) | -20% | If `payment_failed` signal active |

**Output:**
```typescript
export interface HealthScoreResult {
  overallScore: number;           // 0-100
  supportScore: number;           // 0-100
  engagementScore: number;        // 0-100
  churnRisk: number;              // 0.0-1.0
  expansionPotential: number;     // 0.0-1.0
  trend: "improving" | "stable" | "declining";
  factors: HealthFactor[];        // for explainability
  signals: AccountSignal[];       // signals contributing to score
}
```

**Churn risk model:** A simple logistic function over: overallScore, recentSentiment, dealStage, slaBreachRate, paymentStatus. Scores > 0.6 trigger `deal_at_risk` signal. No ML model in Phase 1 — rule-based is fine, upgrade in Phase 2.

---

## 6. Developer Platform (Phase 1 Foundations)

### 6.1 REST API Design

Base URL: `https://api.ellocharlie.app/v1`

Authentication: `Authorization: Bearer {api_key}` where `api_key` is an org-scoped key generated in Settings → Developer.

**OpenAPI spec outline:**

```yaml
openapi: "3.1.0"
info:
  title: ellocharlie API
  version: "1.0"
  description: >
    The ellocharlie REST API. All resources are scoped to your organization.
    Authenticate with your API key in the Authorization header.

servers:
  - url: https://api.ellocharlie.app/v1

security:
  - ApiKeyAuth: []

components:
  securitySchemes:
    ApiKeyAuth:
      type: http
      scheme: bearer

  schemas:
    Cursor:
      type: object
      properties:
        items: { type: array }
        nextCursor: { type: string, nullable: true }
        hasMore: { type: boolean }

    Error:
      type: object
      required: [code, message]
      properties:
        code: { type: string }
        message: { type: string }
        details: { type: object }

paths:
  /conversations:
    get:
      summary: List conversations
      parameters:
        - { name: cursor, in: query, schema: { type: string } }
        - { name: limit, in: query, schema: { type: integer, default: 25, maximum: 100 } }
        - { name: status, in: query, schema: { type: string, enum: [open, pending, resolved, closed] } }
        - { name: assignee_id, in: query, schema: { type: string } }
        - { name: contact_id, in: query, schema: { type: string } }
        - { name: company_id, in: query, schema: { type: string } }
        - { name: channel_type, in: query, schema: { type: string } }
      responses:
        "200": { description: Paginated conversations }
        "401": { description: Unauthorized }
    post:
      summary: Create a conversation
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [contact_email, subject, body]
              properties:
                contact_email: { type: string, format: email }
                contact_name: { type: string }
                company_domain: { type: string }
                subject: { type: string }
                body: { type: string }
                priority: { type: string, enum: [urgent, high, medium, low] }
                ticket_type: { type: string }
                tags: { type: array, items: { type: string } }
                external_id: { type: string, description: "Idempotency key" }
      responses:
        "201": { description: Conversation created }
        "409": { description: Duplicate (external_id already exists) }

  /conversations/{id}:
    get:
      summary: Get a conversation
    patch:
      summary: Update conversation (status, priority, assignee)
    
  /conversations/{id}/messages:
    get:
      summary: List messages in a conversation
    post:
      summary: Send a reply

  /tickets:
    get:
      summary: List tickets
    post:
      summary: Create a ticket

  /tickets/{id}:
    get:
      summary: Get a ticket
    patch:
      summary: Update ticket
    
  /tickets/{id}/resolve:
    post:
      summary: Resolve a ticket

  /contacts/{id}/health:
    get:
      summary: Get account health score for a company

  /knowledge-base/articles:
    get:
      summary: List published KB articles (public visibility only for API keys)
    
  /knowledge-base/search:
    get:
      summary: Search KB articles
      parameters:
        - { name: q, in: query, required: true, schema: { type: string } }
```

**Rate limiting:**
- Default: 300 requests/minute per org
- Burst: 600 requests/minute for 10 seconds
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- 429 response with `Retry-After` header

**API key management (`server/routers/apiKeys.ts`):**
```typescript
// Key format: ec_live_{random_32_bytes_hex}
// Stored: { prefix: "ec_live_xxxx", hash: bcrypt(key), permissions: [...] }

export const apiKeysRouter = router({
  list: protectedProcedure.query(...),
  create: protectedProcedure
    .input(z.object({
      name: z.string().min(1).max(100),
      permissions: z.array(z.enum(["read", "write"])),
      expiresAt: z.coerce.date().optional(),
    }))
    .mutation(...),  // returns full key ONCE, then only prefix
  revoke: protectedProcedure.input(z.object({ id: z.string().cuid2() })).mutation(...),
});
```

---

### 6.2 Webhook System

**Webhook endpoint management:**
```typescript
// shared/schema/webhooks.ts

export const webhookEndpoints = pgTable("webhook_endpoints", {
  id: text("id").primaryKey().$defaultFn(() => createId()),
  organizationId: orgScope,
  url: text("url").notNull(),
  name: text("name").notNull(),
  secret: text("secret").notNull(),         // HMAC signing secret (shown once)
  events: text("events").array().notNull(), // subscribed event types
  isActive: boolean("is_active").notNull().default(true),
  // Stats
  totalDeliveries: integer("total_deliveries").notNull().default(0),
  failedDeliveries: integer("failed_deliveries").notNull().default(0),
  lastSuccessAt: timestamp("last_success_at", { withTimezone: true }),
  lastFailureAt: timestamp("last_failure_at", { withTimezone: true }),
  ...timestamps,
});

export const webhookDeliveries = pgTable("webhook_deliveries", {
  id: text("id").primaryKey().$defaultFn(() => createId()),
  organizationId: orgScope,
  endpointId: text("endpoint_id").notNull(),
  eventType: text("event_type").notNull(),
  payload: jsonb("payload").notNull(),
  status: text("status").$type<"pending"|"success"|"failed"|"retrying">().notNull(),
  statusCode: integer("status_code"),
  responseBody: text("response_body"),
  attemptCount: integer("attempt_count").notNull().default(0),
  nextRetryAt: timestamp("next_retry_at", { withTimezone: true }),
  ...timestamps,
});
```

**Delivery worker** (`lib/webhooks/deliver.ts`):
```typescript
export async function deliverWebhook(
  endpoint: WebhookEndpoint,
  event: WebhookPayload<any, any>
): Promise<void> {
  const body = JSON.stringify(event);
  const timestamp = Date.now().toString();
  const sig = createHmac("sha256", endpoint.secret)
    .update(`${timestamp}.${body}`)
    .digest("hex");

  const response = await fetch(endpoint.url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-ElloCharlie-Signature-256": `t=${timestamp},v1=${sig}`,
      "X-ElloCharlie-Event": event.type,
      "X-ElloCharlie-Delivery": event.id,
      "User-Agent": "ElloCharlie-Webhooks/1.0",
    },
    body,
    signal: AbortSignal.timeout(10_000), // 10s timeout
  });

  if (!response.ok) throw new Error(`HTTP ${response.status}`);
}

// Retry schedule: immediate, 5s, 30s (max 3 attempts)
const RETRY_DELAYS_MS = [0, 5_000, 30_000];
```

---

### 6.3 Embeddable Widget SDK Architecture

**Widget bundle structure:**
```
lib/widgets/chat-widget/
├── src/
│   ├── index.ts          — entry point, reads window.ElloCharlie config
│   ├── sdk.ts            — public API (ElloCharlie.identify, .track, .open, .close)
│   ├── ui/
│   │   ├── Widget.tsx    — root component (Preact, ~8kb)
│   │   ├── Launcher.tsx  — floating button
│   │   ├── Inbox.tsx     — conversation list
│   │   └── Thread.tsx    — message thread view
│   ├── ws.ts             — WebSocket connection manager (reconnect logic)
│   └── session.ts        — visitor session management (localStorage + cookie)
├── build.ts              — esbuild config targeting < 15kb gzipped
└── types.ts              — SDK public types
```

**Public SDK API:**
```typescript
// Exposed on window.ElloCharlie after widget loads

interface ElloCharlieSDK {
  // Identity
  identify(user: { email: string; name?: string; userId?: string; metadata?: Record<string, unknown> }): void;
  
  // Programmatic control
  open(): void;
  close(): void;
  toggle(): void;
  
  // Pre-populate conversation
  startConversation(opts: { message?: string; subject?: string }): void;
  
  // Events
  on(event: "open" | "close" | "message_sent" | "conversation_created", handler: (data: unknown) => void): void;
  off(event: string, handler: Function): void;
  
  // Config override (before boot)
  config: {
    apiKey: string;
    orgId?: string;
    primaryColor?: string;
    greeting?: string;
    position?: "bottom-right" | "bottom-left";
  };
}
```

**Shadow DOM isolation:** Widget renders inside a Shadow DOM attached to a `<div id="ellocharlie-widget-root">` element. This prevents CSS conflicts with the host page.

---

### 6.4 MCP Server Design (`lib/mcp/server.ts`)

Model Context Protocol server exposes ellocharlie data to AI agents (Claude, Cursor, etc.).

```typescript
// MCP Server for ellocharlie
// Mounted at: GET /mcp/{orgId} (with API key auth)

export const mcpTools = [
  {
    name: "get_conversation",
    description: "Get a support conversation by ID, including all messages",
    inputSchema: {
      type: "object",
      properties: {
        conversation_id: { type: "string" },
      },
      required: ["conversation_id"],
    },
  },
  {
    name: "list_open_tickets",
    description: "List open support tickets, optionally filtered by company or assignee",
    inputSchema: {
      type: "object",
      properties: {
        company_id: { type: "string" },
        assignee_id: { type: "string" },
        limit: { type: "number", default: 10 },
      },
    },
  },
  {
    name: "get_account_health",
    description: "Get health score and signals for a company",
    inputSchema: {
      type: "object",
      properties: {
        company_id: { type: "string" },
      },
      required: ["company_id"],
    },
  },
  {
    name: "search_knowledge_base",
    description: "Search the knowledge base for relevant articles",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string" },
        limit: { type: "number", default: 5 },
      },
      required: ["query"],
    },
  },
  {
    name: "create_ticket",
    description: "Create a new support ticket",
    inputSchema: {
      type: "object",
      properties: {
        title: { type: "string" },
        description: { type: "string" },
        contact_email: { type: "string" },
        priority: { type: "string", enum: ["urgent", "high", "medium", "low"] },
      },
      required: ["title", "contact_email"],
    },
  },
  {
    name: "reply_to_conversation",
    description: "Send a reply to an existing support conversation",
    inputSchema: {
      type: "object",
      properties: {
        conversation_id: { type: "string" },
        message: { type: "string" },
        internal_note: { type: "boolean", default: false },
      },
      required: ["conversation_id", "message"],
    },
  },
  {
    name: "get_feature_requests",
    description: "Get the top feature requests by priority score",
    inputSchema: {
      type: "object",
      properties: {
        limit: { type: "number", default: 10 },
        product_area: { type: "string" },
      },
    },
  },
];

// MCP server implementation uses @modelcontextprotocol/sdk
// Handles: initialize, tools/list, tools/call, resources/list
// Mounted as a Hono sub-app at /mcp
```

---

## 7. Implementation Roadmap

### Sprint 1 (Weeks 1–2): Core Engine + Email

**Goal:** A working email inbox. New emails create tickets. Agents can reply. Everything stored in Postgres.

**Database migrations:**
- [ ] `channels`, `channel_connections`
- [ ] `conversations`, `messages`
- [ ] `tickets`, `ticket_assignments`, `ticket_tags`
- [ ] `sla_policies`, `sla_status`
- [ ] `account_activities` (for CRM feed)

**API (tRPC + Hono):**
- [ ] `conversations.list`, `conversations.get`, `conversations.create`, `conversations.reply`, `conversations.close`, `conversations.assign`
- [ ] `tickets.list`, `tickets.get`, `tickets.create`, `tickets.update`, `tickets.assign`, `tickets.resolve`
- [ ] `channels.list`, `channels.connect`, `channels.configure`

**Channel:** Email
- [ ] Resend inbound webhook handler (`POST /webhooks/email/{orgId}/{channelId}`)
- [ ] Email normalization → `CanonicalMessage`
- [ ] Thread detection (References header matching)
- [ ] Contact resolution (email → contacts table)
- [ ] Outbound reply via Resend API
- [ ] Email channel provisioning (auto-assign `support@{orgSlug}.ellocharlie.app`)

**Frontend:**
- [ ] `/inbox` — unified inbox with conversation list + thread view
- [ ] `/tickets` — ticket table with filters
- [ ] `/settings/channels` — channel list + connect email
- [ ] Tiptap reply composer (with attachment support)
- [ ] Real-time updates via TanStack Query polling (WebSockets in Sprint 2)

**SLA engine:**
- [ ] Default SLA policy creation on org signup
- [ ] SLA clock start on ticket creation
- [ ] Background job: mark `sla_status.breached = true` when due date passes
- [ ] SLA badge on ticket list

**Acceptance criteria:**
- Customer sends email → appears in inbox within 5 seconds
- Agent replies → customer receives email within 10 seconds
- Ticket created automatically, SLA clock ticking
- All queries scoped to `organizationId` (verified by test)

---

### Sprint 2 (Weeks 3–4): Slack + Live Chat + Knowledge Base

**Goal:** Three-channel coverage. Agents never need to leave ellocharlie.

**Database migrations:**
- [ ] `kb_collections`, `kb_articles`, `kb_article_versions`

**Channel:** Slack
- [ ] Slack OAuth 2.0 flow (`/settings/channels/connect/slack`)
- [ ] Slack Events API webhook handler
- [ ] Signature verification middleware
- [ ] Thread → conversation mapping
- [ ] Outbound message via Slack Web API (with Block Kit)
- [ ] Slack channel selector UI (pick which channels to monitor)
- [ ] Reaction handler (✅ → resolve ticket)

**Channel:** Live Chat
- [ ] Widget bundle build pipeline (esbuild, < 15kb target)
- [ ] Shadow DOM widget UI (Preact)
- [ ] Session management (anon visitor → identified contact)
- [ ] WebSocket server (Hono WS or Cloud Run WebSocket)
- [ ] `POST /api/widget/session` endpoint
- [ ] Identity capture form (email + name)
- [ ] Widget config UI in `/settings/channels`

**Knowledge Base:**
- [ ] `knowledgeBase.*` tRPC procedures
- [ ] `/knowledge` — article list, collection sidebar
- [ ] Article editor (Tiptap, full rich text)
- [ ] Publish/archive flow
- [ ] Full-text search (Postgres `tsvector` + `to_tsquery`)
- [ ] Version history UI

**Inbox upgrades:**
- [ ] Channel filter tabs (All, Email, Slack, Chat)
- [ ] Snooze functionality
- [ ] Merge conversations
- [ ] Tag management

**Acceptance criteria:**
- Slack Connect channel message → appears in inbox, agent replies appear in Slack thread
- Chat widget installs with one `<script>` tag, loads < 15kb
- KB article published → searchable from inbox via suggest procedure

---

### Sprint 3 (Weeks 5–6): AI Layer + Account Intelligence

**Goal:** AI does the first pass on every ticket. Agents approve/edit. Churn risk visible in CRM.

**Database migrations:**
- [ ] `ai_actions`, `ai_suggestions`
- [ ] `account_health_scores`, `account_signals`

**AI pipeline:**
- [ ] AI provider abstraction (`lib/ai/provider.ts`) — OpenAI + Anthropic
- [ ] Triage pipeline (`lib/ai/triage.ts`) — runs async after every inbound message
- [ ] Response drafting (`lib/ai/draft.ts`) — "Draft Reply" button in inbox
- [ ] KB semantic search for drafts (pgvector or cosine similarity via embeddings)
- [ ] Categorization (`lib/ai/classify.ts`)
- [ ] Sentiment analysis (part of triage)
- [ ] `ai.triage`, `ai.suggestResponse`, `ai.categorize` tRPC procedures
- [ ] AI usage dashboard (tokens, cost, override rate)

**AI/Inbox integration:**
- [ ] AI-generated summary shown at top of conversation
- [ ] "AI suggests: Priority High" with accept/dismiss
- [ ] Draft reply panel with "Generate Draft" button
- [ ] KB article suggestions panel (right sidebar)
- [ ] AI confidence score display

**Account Intelligence:**
- [ ] Health score computation (`lib/ai/health-score.ts`)
- [ ] Hourly background job for score recomputation
- [ ] Signal emission (on ticket created/resolved, SLA breach, etc.)
- [ ] `accountIntelligence.*` tRPC procedures
- [ ] Account health view in `/accounts/{companyId}`
- [ ] At-risk accounts dashboard (`/accounts?filter=at_risk`)
- [ ] Health score widget in CRM company record

**Acceptance criteria:**
- New inbound email → AI triage completes within 3s
- "Draft Reply" → contextual AI draft appears within 5s, grounded in KB
- Company health score visible in both CRM and support views
- AI override rate tracked and displayed

---

### Sprint 4 (Weeks 7–8): Workflow Engine + Developer API + Product Intelligence

**Goal:** Automation, public API, and the feedback loop from support to product.

**Database migrations:**
- [ ] `workflows`, `workflow_steps`, `workflow_triggers`, `workflow_runs`
- [ ] `feature_requests`, `feature_request_evidence`
- [ ] `webhook_endpoints`, `webhook_deliveries`

**Workflow Engine:**
- [ ] Workflow trigger evaluation system (event-driven, not polling)
- [ ] Step executor (`lib/workflows/executor.ts`) — async, non-blocking
- [ ] Built-in step types: assign, status change, tag, send email, add note, escalate, AI triage, AI draft
- [ ] Condition evaluator (field comparisons, boolean logic)
- [ ] Delay step (via scheduled Hono handler)
- [ ] Visual workflow builder UI (`/workflows`)
- [ ] Run history with execution log
- [ ] `workflows.*` tRPC procedures

**Developer Platform:**
- [ ] REST API (`/api/v1/`) — conversations, tickets, KB articles
- [ ] API key management UI (`/settings/developer/api-keys`)
- [ ] Outbound webhook system + delivery worker
- [ ] Webhook management UI (`/settings/developer/webhooks`)
- [ ] Webhook delivery log with replay
- [ ] MCP server (`/mcp/{orgId}`) — 7 tools as specified
- [ ] Developer docs page (auto-generated from OpenAPI spec)

**Product Intelligence:**
- [ ] Knowledge gap detection job (daily, scans closed conversations)
- [ ] Feature request clustering on ticket close (async)
- [ ] `productIntelligence.*` tRPC procedures
- [ ] `/accounts/product-intelligence` — feature request board
- [ ] Revenue impact visualization (ARR per feature request cluster)
- [ ] Evidence linking UI (drag ticket to feature request)

**Acceptance criteria:**
- "Auto-assign urgent tickets to on-call engineer" workflow runs correctly
- REST API creates ticket, fires webhook to external system within 5s
- Feature requests page shows top 10 requests with ARR impact
- MCP server responds to `tools/call` from Claude Desktop

---

## 8. File Structure

```
app/
├── (dashboard)/
│   ├── inbox/
│   │   ├── page.tsx                    — unified inbox: conversation list + empty state
│   │   ├── [conversationId]/
│   │   │   └── page.tsx                — conversation thread view
│   │   ├── _components/
│   │   │   ├── ConversationList.tsx    — sortable/filterable conversation list
│   │   │   ├── ConversationRow.tsx     — single row: avatar, subject, preview, badges
│   │   │   ├── ThreadView.tsx          — message thread container
│   │   │   ├── MessageBubble.tsx       — individual message (inbound/outbound/note)
│   │   │   ├── ReplyComposer.tsx       — Tiptap editor + send controls + attachment
│   │   │   ├── AiDraftPanel.tsx        — AI draft suggestion with accept/edit/dismiss
│   │   │   ├── KbSuggestionsPanel.tsx  — KB article suggestions sidebar
│   │   │   ├── ConversationSidebar.tsx — contact info, company health, deal context
│   │   │   ├── InboxFilters.tsx        — status, assignee, channel, priority filters
│   │   │   └── ChannelTabs.tsx         — All / Email / Slack / Chat tabs
│   │   └── layout.tsx
│   │
│   ├── tickets/
│   │   ├── page.tsx                    — ticket table with advanced filters
│   │   ├── [ticketId]/
│   │   │   └── page.tsx                — ticket detail: description, timeline, SLA
│   │   ├── _components/
│   │   │   ├── TicketTable.tsx
│   │   │   ├── TicketRow.tsx
│   │   │   ├── TicketDetail.tsx
│   │   │   ├── SlaCountdown.tsx        — visual SLA timer
│   │   │   ├── TicketTimeline.tsx      — activity feed
│   │   │   ├── TicketAssignee.tsx
│   │   │   └── TicketFilters.tsx
│   │   └── layout.tsx
│   │
│   ├── knowledge/
│   │   ├── page.tsx                    — KB home: collections grid + search
│   │   ├── articles/
│   │   │   ├── new/
│   │   │   │   └── page.tsx            — new article editor
│   │   │   └── [articleId]/
│   │   │       ├── page.tsx            — article view (published)
│   │   │       └── edit/
│   │   │           └── page.tsx        — article editor
│   │   ├── collections/
│   │   │   └── [collectionId]/
│   │   │       └── page.tsx            — collection view with article list
│   │   ├── gaps/
│   │   │   └── page.tsx                — AI-detected knowledge gaps
│   │   ├── _components/
│   │   │   ├── ArticleEditor.tsx       — Tiptap editor with KB-specific extensions
│   │   │   ├── CollectionSidebar.tsx
│   │   │   ├── ArticleCard.tsx
│   │   │   ├── VersionHistory.tsx
│   │   │   ├── GapCard.tsx             — knowledge gap with "Draft Article" CTA
│   │   │   └── KbSearch.tsx
│   │   └── layout.tsx
│   │
│   ├── accounts/
│   │   ├── page.tsx                    — account health grid / at-risk list
│   │   ├── [companyId]/
│   │   │   ├── page.tsx                — company overview (health + activity feed)
│   │   │   ├── tickets/
│   │   │   │   └── page.tsx            — all tickets for this company
│   │   │   └── signals/
│   │   │       └── page.tsx            — signal history
│   │   ├── product-intelligence/
│   │   │   └── page.tsx                — feature request board
│   │   ├── _components/
│   │   │   ├── HealthScoreCard.tsx     — score + trend + churn risk
│   │   │   ├── HealthScoreChart.tsx    — 90-day trend line chart
│   │   │   ├── SignalFeed.tsx          — chronological signal list
│   │   │   ├── ActivityFeed.tsx        — unified CX+CRM activity timeline
│   │   │   ├── FeatureRequestBoard.tsx — Kanban-style or priority-sorted list
│   │   │   ├── FeatureRequestCard.tsx  — title, ARR, mention count, status badge
│   │   │   └── AtRiskBanner.tsx        — shown on company page when churnRisk > 0.6
│   │   └── layout.tsx
│   │
│   ├── workflows/
│   │   ├── page.tsx                    — workflow list
│   │   ├── [workflowId]/
│   │   │   ├── page.tsx                — visual builder
│   │   │   └── history/
│   │   │       └── page.tsx            — run history + log viewer
│   │   ├── _components/
│   │   │   ├── WorkflowBuilder.tsx     — drag-and-drop step builder
│   │   │   ├── TriggerSelector.tsx
│   │   │   ├── StepNode.tsx            — individual step card
│   │   │   ├── ConditionBuilder.tsx    — visual condition editor
│   │   │   ├── RunHistoryTable.tsx
│   │   │   └── RunLogViewer.tsx        — step-by-step execution log
│   │   └── layout.tsx
│   │
│   └── settings/
│       ├── channels/
│       │   ├── page.tsx                — channel list
│       │   ├── [channelId]/
│       │   │   └── page.tsx            — channel config
│       │   ├── connect/
│       │   │   ├── email/
│       │   │   │   └── page.tsx        — email setup wizard
│       │   │   └── slack/
│       │   │       └── page.tsx        — Slack OAuth callback handler
│       │   └── _components/
│       │       ├── ChannelCard.tsx
│       │       ├── EmailSetupWizard.tsx
│       │       ├── SlackChannelPicker.tsx
│       │       ├── ChatWidgetConfig.tsx
│       │       └── WidgetCodeSnippet.tsx
│       ├── sla/
│       │   └── page.tsx                — SLA policy management
│       └── developer/
│           ├── api-keys/
│           │   └── page.tsx
│           └── webhooks/
│               ├── page.tsx
│               └── [endpointId]/
│                   └── page.tsx        — webhook config + delivery log

server/
├── routers/
│   ├── cx.ts                           — CX router aggregate
│   ├── conversations.ts
│   ├── tickets.ts
│   ├── knowledgeBase.ts
│   ├── accountIntelligence.ts
│   ├── productIntelligence.ts
│   ├── channels.ts
│   ├── workflows.ts
│   ├── ai.ts
│   └── apiKeys.ts
├── webhooks/
│   ├── slack.ts                        — Hono route: POST /webhooks/slack/:orgId
│   ├── email.ts                        — Hono route: POST /webhooks/email/:orgId/:channelId
│   └── incoming-api.ts                 — Hono route: POST /webhooks/external/:endpointId
└── middleware/
    ├── orgScope.ts                     — injects organizationId from Clerk
    ├── apiKeyAuth.ts                   — REST API key validation
    └── rateLimiter.ts

shared/
└── schema/
    ├── _utils.ts                       — cuid(), timestamps, orgScope helpers
    ├── conversations.ts                — channels, channel_connections, conversations, messages
    ├── tickets.ts                      — tickets, ticket_assignments, ticket_tags, sla_policies, sla_status
    ├── knowledge-base.ts               — kb_collections, kb_articles, kb_article_versions
    ├── account-intelligence.ts         — account_health_scores, account_signals, account_activities
    ├── product-intelligence.ts         — feature_requests, feature_request_evidence
    ├── workflows.ts                    — workflows, workflow_steps, workflow_triggers, workflow_runs
    ├── ai.ts                           — ai_actions, ai_suggestions
    └── webhooks.ts                     — webhook_endpoints, webhook_deliveries

lib/
├── channels/
│   ├── types.ts                        — CanonicalMessage, CanonicalAttachment interfaces
│   ├── normalizer.ts                   — routes inbound CanonicalMessage to conversation engine
│   ├── slack.ts                        — Slack adapter (verify, normalize, send)
│   ├── email.ts                        — Email adapter (normalize inbound, send via Resend)
│   ├── chat.ts                         — WebSocket session + message handler
│   └── forms.ts                        — Form submission handler
├── ai/
│   ├── provider.ts                     — AI provider abstraction (OpenAI/Anthropic)
│   ├── context.ts                      — TriageContext assembler (pulls from CRM graph)
│   ├── triage.ts                       — Full triage pipeline
│   ├── draft.ts                        — Response draft generation
│   ├── classify.ts                     — Standalone classification (type, area, tags)
│   ├── health-score.ts                 — Account health computation
│   ├── knowledge-gaps.ts               — Knowledge gap detection
│   └── embeddings.ts                   — Text embedding + semantic search utilities
├── workflows/
│   ├── executor.ts                     — Step executor (dispatches to step handlers)
│   ├── trigger-evaluator.ts            — Condition matching for trigger events
│   └── steps/
│       ├── assign.ts
│       ├── status-change.ts
│       ├── send-email.ts
│       ├── add-note.ts
│       ├── ai-triage.ts
│       ├── condition.ts
│       ├── delay.ts
│       └── webhook-call.ts
├── webhooks/
│   ├── deliver.ts                      — HTTP delivery with retry logic
│   ├── sign.ts                         — HMAC signing helpers
│   └── events.ts                       — Event type definitions + payload builders
├── sla/
│   ├── calculator.ts                   — Due date computation (with business hours)
│   ├── checker.ts                      — Background job: breach detection
│   └── business-hours.ts              — Business hours utilities
└── widgets/
    └── chat-widget/
        ├── src/
        │   ├── index.ts
        │   ├── sdk.ts
        │   ├── ws.ts
        │   ├── session.ts
        │   └── ui/
        │       ├── Widget.tsx
        │       ├── Launcher.tsx
        │       ├── Inbox.tsx
        │       └── Thread.tsx
        └── build.ts

api/
└── v1/
    ├── middleware.ts                   — API key auth + rate limiting
    ├── conversations.ts               — REST handlers
    ├── tickets.ts
    ├── contacts.ts
    ├── knowledge-base.ts
    └── mcp/
        └── server.ts                  — MCP server (tools + resources)
```

---

## Appendix A: Key Design Decisions

### A.1 Why conversations AND tickets?

Not every conversation needs a ticket. A quick "what's your pricing?" chat is a conversation. An "integration is broken in production" message should auto-escalate to a ticket. The two concepts are related but distinct:

- **Conversation** = the communication thread (messages back and forth)
- **Ticket** = the work item with SLA, assignee, resolution tracking

A conversation can exist without a ticket (quick queries). A ticket always has a linked conversation (or is created standalone). Auto-ticket creation is triggered by the triage pipeline based on priority score > 40 or ticketType ≠ "general".

### A.2 Why not use pgvector for embeddings in Phase 1?

pgvector requires an extension and complicates the Neon Postgres setup. Phase 1 uses:
- Full-text search (`tsvector`/`to_tsquery`) for KB article search
- Cosine similarity computed in application code for small corpora (< 10k articles)
- Embeddings stored as `text` (serialized float array) until pgvector is enabled in Phase 2

Phase 2 migration: `ALTER TABLE kb_articles ADD COLUMN embedding vector(1536)` + backfill job.

### A.3 Ticket number generation

Ticket numbers must be sequential per org for human readability (e.g., "Ticket #42"). With distributed writes, this requires care:

```typescript
// In createTicket mutation, inside a transaction:
const [{ number }] = await db
  .select({ number: sql<number>`COALESCE(MAX(${tickets.number}), 0) + 1` })
  .from(tickets)
  .where(eq(tickets.organizationId, ctx.organizationId));

await db.insert(tickets).values({ ...data, number, organizationId: ctx.organizationId });
```

This is safe because the transaction serializes the MAX + INSERT. For very high write rates (> 100 tickets/sec per org, unlikely in Phase 1), a dedicated sequence table is better.

### A.4 Multi-tenant security

Every tRPC procedure that reads/writes data MUST include `organizationId` in the WHERE clause. The pattern enforced by code review:

```typescript
// ✅ Correct — always AND with organizationId
await db.query.tickets.findFirst({
  where: and(
    eq(tickets.id, input.id),
    eq(tickets.organizationId, ctx.organizationId) // never omit this
  ),
});

// ❌ Wrong — can return data from any org
await db.query.tickets.findFirst({
  where: eq(tickets.id, input.id),
});
```

A Drizzle middleware should enforce this as a default policy in the DB client setup — if the `organizationId` filter is missing on any `SELECT`, throw a developer error in development.

---

## Appendix B: Environment Variables (Phase 1 additions)

```bash
# Existing
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
DATABASE_URL=                           # Neon Postgres connection string
RESEND_API_KEY=
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_R2_ACCESS_KEY_ID=
CLOUDFLARE_R2_SECRET_ACCESS_KEY=
CLOUDFLARE_R2_BUCKET_NAME=
STRIPE_SECRET_KEY=

# Phase 1 additions
SLACK_CLIENT_ID=                        # Slack OAuth app
SLACK_CLIENT_SECRET=
SLACK_SIGNING_SECRET=                   # For webhook verification
OPENAI_API_KEY=                         # AI provider (primary)
ANTHROPIC_API_KEY=                      # AI provider (fallback)
AI_DEFAULT_PROVIDER=openai              # 'openai' | 'anthropic'
WIDGET_BUNDLE_URL=https://widget.ellocharlie.app/v1/widget.js
INBOUND_EMAIL_DOMAIN=ellocharlie.app    # {orgSlug}.{domain} = email address
WEBHOOK_DELIVERY_SECRET=                # Internal secret for webhook delivery worker
ENCRYPTION_KEY=                         # For encrypting OAuth tokens at rest (32-byte hex)
```

---

*End of Phase 1 Technical Specification*
