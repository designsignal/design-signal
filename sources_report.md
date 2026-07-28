# Sources Verification Report

**Generated:** 2026-06-30 16:43
**Status:** 23/25 feeds working (92%)

## By layer

### layer_1_primary — 12/14 working

| Status | Items | Source | URL |
|--------|------:|--------|-----|
| ✅ ok | 38 | AI design tools (broad) | `https://news.google.com/rss/search?q=AI%20design%20tool%20%28Figma%20OR%20Framer%20OR%20Lovable%20OR%20Cursor%20OR%20prototyping%29%20when%3A7d&hl=en-US&gl=US&ceid=US:en` |
| ✅ ok | 5 | Builder.io blog | `https://www.builder.io/blog/feed.xml` |
| ✅ ok | 36 | Claude Design / Anthropic (news) | `https://news.google.com/rss/search?q=%28Anthropic%20OR%20%22Claude%20Design%22%29%20%28design%20OR%20Artifacts%20OR%20canvas%29%20when%3A14d&hl=en-US&gl=US&ceid=US:en` |
| ✅ ok | 40 | Cursor (news) | `https://news.google.com/rss/search?q=%22Cursor%22%20%28AI%20editor%20OR%20coding%20OR%20update%20OR%20release%29%20when%3A14d&hl=en-US&gl=US&ceid=US:en` |
| ✅ ok | 40 | Figma (news) | `https://news.google.com/rss/search?q=Figma%20%28update%20OR%20launch%20OR%20feature%20OR%20Make%20OR%20Config%20OR%20Motion%29%20when%3A14d&hl=en-US&gl=US&ceid=US:en` |
| ✅ ok | 36 | Framer (news) | `https://news.google.com/rss/search?q=Framer%20%28AI%20OR%20update%20OR%20feature%20OR%20launch%20OR%20agent%29%20when%3A14d&hl=en-US&gl=US&ceid=US:en` |
| ✅ ok | 18 | Lovable (news) | `https://news.google.com/rss/search?q=%22Lovable%22%20%28AI%20app%20builder%20OR%20update%20OR%20feature%29%20when%3A14d&hl=en-US&gl=US&ceid=US:en` |
| ✅ ok | 20 | Nielsen Norman Group | `https://www.nngroup.com/feed/rss/` |
| ✅ ok | 82 | OpenAI blog | `https://openai.com/blog/rss.xml` |
| ✅ ok | 10 | Telegraf.design | `https://telegraf.design/feed/` |
| ✅ ok | 8 | UX Collective | `https://uxdesign.cc/feed` |
| ✅ ok | 6 | v0 by Vercel (news) | `https://news.google.com/rss/search?q=%22v0%22%20Vercel%20%28update%20OR%20feature%20OR%20design%29%20when%3A14d&hl=en-US&gl=US&ceid=US:en` |
| ❌ feed_sparse | 1 | Lenny's Newsletter | `https://www.lennysnewsletter.com/feed` |
| ❌ feed_sparse | 1 | Smashing Magazine | `https://www.smashingmagazine.com/feed/` |

### quarantine — 6/6 working

| Status | Items | Source | URL |
|--------|------:|--------|-----|
| ✅ ok | 22 | Apple Developer News | `https://developer.apple.com/news/rss/news.rss` |
| ✅ ok | 20 | Google Developers Blog | `https://developers.googleblog.com/feeds/posts/default?alt=rss` |
| ✅ ok | 62 | Tailwind CSS blog | `https://tailwindcss.com/feeds/feed.xml` |
| ✅ ok | 15 | Vercel blog (atom) | `https://vercel.com/atom` |
| ✅ ok | 23 | arXiv cs.AI | `https://export.arxiv.org/rss/cs.AI` |
| ✅ ok | 10 | shadcn/ui releases | `https://github.com/shadcn-ui/ui/releases.atom` |

### layer_2_signals — 4/4 working

| Status | Items | Source | URL |
|--------|------:|--------|-----|
| ✅ ok | 10 | HN front page (200+ points) | `https://hnrss.org/frontpage?points=200` |
| ✅ ok | 20 | HN — AI/agent keywords | `https://hnrss.org/newest?q=AI+OR+agent+OR+LLM+OR+Claude+OR+Cursor+OR+Lovable&points=100` |
| ✅ ok | 50 | Product Hunt — Design Tools | `https://www.producthunt.com/feed?category=design-tools` |
| ✅ ok | 23 | r/cursor (top weekly) | `https://www.reddit.com/r/cursor/top/.rss?t=week` |

### layer_3_competitors — 1/1 working

| Status | Items | Source | URL |
|--------|------:|--------|-----|
| ✅ ok | 20 | Sidebar.io | `https://sidebar.io/feed.xml` |

## ❌ Broken — needs replacement

Common fixes:
- `404` → check current URL on the site's footer (look for RSS icon)
- `not_a_feed` → URL is HTML, not RSS. Use rss.app to convert.
- `conn_error` / `ssl_error` → site may be down or moved
- `timeout` → retry in 1 hour; if persists, replace

- **Lenny's Newsletter** (layer_1_primary/design_publications) — `feed_sparse` — https://www.lennysnewsletter.com/feed
- **Smashing Magazine** (layer_1_primary/design_publications) — `feed_sparse` — https://www.smashingmagazine.com/feed/
