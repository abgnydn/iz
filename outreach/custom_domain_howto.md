# Custom domain how-to

Replace `iz-b0n.pages.dev` with `iz.barisgunaydin.com` (or any other custom domain). All
on Cloudflare Pages; takes ~5 minutes.

## Option A — `iz.barisgunaydin.com` subdomain (recommended)

You already own `barisgunaydin.com`. Add a subdomain pointing at the Pages project:

1. **In Cloudflare dashboard:**
   - Go to **Pages** → **iz** project → **Custom domains** tab
   - Click "Set up a custom domain"
   - Enter: `iz.barisgunaydin.com`
   - Click "Continue" → "Activate domain"

2. **DNS:** Cloudflare auto-configures the CNAME if `barisgunaydin.com` is on Cloudflare DNS.
   If `barisgunaydin.com` is on another DNS provider (Namecheap, Google Domains, etc.), add a
   CNAME record manually:
   ```
   Type: CNAME
   Name: iz
   Value: iz.pages.dev
   TTL: auto / 1 hour
   Proxy: orange-cloud ON (if Cloudflare DNS)
   ```

3. **SSL/TLS cert:** Cloudflare auto-provisions a Let's Encrypt cert within a few minutes.

4. **After verification (~5-15 min for DNS to propagate globally):**
   `iz.barisgunaydin.com` will serve the same content as `iz-b0n.pages.dev`. The `.pages.dev`
   URL keeps working in parallel.

## Option B — root `barisgunaydin.com` (only if you want iz to be your whole site)

Same flow but with `barisgunaydin.com` instead. Cloudflare prompts you to also add `www`
redirect. Not recommended unless you actually want iz to replace your personal site at
the root.

## Option C — new domain (`trmrvbench.com` or similar)

Buy via Cloudflare Registrar (cheapest, no markup): ~$10/yr for .com. Then add as in
Option A. Worth it only if you want the bench to feel like a public research artifact
that isn't tied to your personal brand.

---

## After the domain is live

Update all places that reference the URL:

```bash
# in repo root:
grep -rln 'iz-b0n.pages.dev' site/ README.md PAPER_OUTLINE.md PAPER_METHOD.md PAPER_DISCUSSION.md paper/ outreach/ CITATION.cff bin/render_og.py 2>/dev/null
```

Then sed-replace `iz-b0n.pages.dev` → your new domain in each file. The OG meta tags
in each HTML file have `og:url` and `og:image` URLs that need absolute domains too.

Re-render the OG image to point at the new domain:
```bash
# edit site/assets/og.html if the URL is shown
.venv/bin/python bin/render_og.py
```

Then redeploy:
```bash
npx wrangler pages deploy site --project-name=iz --branch=main --commit-dirty=true
```

The `iz-b0n.pages.dev` URL keeps working forever as a backup (Cloudflare doesn't remove it).
Both URLs will serve identical content. Eventually you can set up a 301 redirect from
`iz-b0n.pages.dev` → your custom domain via Page Rules if you want.

---

## Email setup (optional)

If you want `hi@iz.barisgunaydin.com` (or whatever subdomain you choose) to work in
addition to `hi@barisgunaydin.com`:

1. Cloudflare → **Email** → **Email Routing**
2. Add the subdomain
3. Forward `hi@iz.barisgunaydin.com` → wherever your `hi@barisgunaydin.com` already lands

Or just keep using `hi@barisgunaydin.com` — it works regardless of which domain the site uses.

---

## Costs

- Cloudflare Pages: **free** (1 build/min, unlimited bandwidth)
- Custom domain (subdomain of barisgunaydin.com): **free** if barisgunaydin.com is on
  Cloudflare DNS; otherwise just DNS configuration cost at your existing registrar
- New domain (Option C): ~$10/yr from Cloudflare Registrar
- SSL/TLS: **free** (Cloudflare-managed Let's Encrypt)
- Total ongoing cost: **$0/yr** (Option A) or **$10/yr** (Option C)
