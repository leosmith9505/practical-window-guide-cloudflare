import os
import re
import html
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit
from xml.sax.saxutils import escape as xml_escape

import requests
import markdown
import bleach


OWNER = "leosmith9505"
REPO = "practical-window-guide-cloudflare"

SITE_NAME = "Practical Window Guide"
BASE_URL = "https://practical-window-guide-cloudflare.pages.dev"

DESCRIPTION = (
    "Practical guides to window maintenance, glass care, "
    "window repair, and home improvement."
)

OUTPUT = Path("site")
ARTICLES = OUTPUT / "articles"
ARTICLES.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
    "X-GitHub-Api-Version": "2022-11-28",
}

API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/issues"


CSS = """
:root {
  --navy: #17324d;
  --teal: #168c91;
  --light: #f3f8fa;
  --white: #ffffff;
  --muted: #617486;
  --border: #dce8ed;
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
  color: var(--navy);
  background: var(--light);
  line-height: 1.75;
}

a {
  color: var(--teal);
}

.site-header {
  background: var(--white);
  border-bottom: 1px solid var(--border);
}

.nav {
  max-width: 1120px;
  margin: auto;
  padding: 22px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.brand {
  font-size: 23px;
  font-weight: 700;
  color: var(--navy);
  text-decoration: none;
}

.nav-links a {
  margin-left: 24px;
  color: var(--navy);
  font-weight: 600;
  text-decoration: none;
}

.hero {
  padding: 90px 24px;
  background: linear-gradient(
    125deg,
    #17324d 0%,
    #205a70 65%,
    #168c91 100%
  );
  color: white;
}

.hero-inner {
  max-width: 1120px;
  margin: auto;
}

.eyebrow {
  color: #a9e8e6;
  text-transform: uppercase;
  letter-spacing: 2px;
  font-size: 13px;
  font-weight: bold;
}

.hero h1 {
  max-width: 800px;
  font-size: clamp(36px, 5vw, 58px);
  line-height: 1.15;
  margin: 20px 0;
}

.hero p {
  max-width: 720px;
  font-size: 19px;
  color: #e2f3f5;
}

.container {
  max-width: 1120px;
  margin: 60px auto;
  padding: 0 24px;
}

.section-title {
  font-size: 31px;
  margin-bottom: 28px;
}

.article-grid {
  display: grid;
  grid-template-columns: repeat(
    auto-fit,
    minmax(280px, 1fr)
  );
  gap: 26px;
}

.article-card {
  background: white;
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 30px;
  box-shadow: 0 8px 25px rgba(23, 50, 77, 0.04);
}

.article-card::before {
  content: "";
  display: block;
  width: 45px;
  height: 4px;
  background: var(--teal);
  margin-bottom: 20px;
}

.article-card h2 {
  font-size: 23px;
  line-height: 1.35;
}

.article-card h2 a {
  color: var(--navy);
  text-decoration: none;
}

.article-card h2 a:hover,
.nav-links a:hover {
  color: var(--teal);
}

.date {
  color: var(--muted);
  font-size: 14px;
}

.read-more {
  display: inline-block;
  margin-top: 12px;
  font-weight: bold;
  text-decoration: none;
}

.article-page {
  max-width: 880px;
  margin: 55px auto;
  padding: 48px;
  background: white;
  border: 1px solid var(--border);
  border-radius: 14px;
}

.article-page h1 {
  font-size: clamp(30px, 4vw, 44px);
  line-height: 1.25;
}

.article-content {
  overflow-wrap: anywhere;
}

.article-content img {
  max-width: 100%;
  height: auto;
  border-radius: 10px;
}

.article-content h2,
.article-content h3 {
  color: var(--navy);
  margin-top: 32px;
}

.article-content blockquote {
  margin: 24px 0;
  padding: 12px 22px;
  border-left: 4px solid var(--teal);
  background: var(--light);
}

.article-content pre,
.article-content table {
  max-width: 100%;
  overflow-x: auto;
}

.article-content table {
  display: block;
  border-collapse: collapse;
}

.article-content th,
.article-content td {
  border: 1px solid var(--border);
  padding: 10px;
}

.site-footer {
  margin-top: 65px;
  padding: 32px 24px;
  background: var(--navy);
  color: white;
  text-align: center;
}

@media (max-width: 600px) {
  .nav {
    flex-wrap: wrap;
  }

  .nav-links a {
    margin: 0 16px 0 0;
  }

  .hero {
    padding: 60px 24px;
  }

  .article-page {
    margin: 18px;
    padding: 24px;
  }
}
"""


def safe(value):
    return html.escape(str(value or ""), quote=True)


def clean_text(value):
    return re.sub(
        r"\s+",
        " ",
        bleach.clean(
            str(value or ""),
            tags=[],
            strip=True
        )
    ).strip()


def excerpt(value, limit=155):
    text = clean_text(value)

    if len(text) <= limit:
        return text

    return text[:limit].rsplit(" ", 1)[0] + "..."


def allowed_attribute(tag, name, value):
    allowed = {
        "a": {"href", "title"},
        "img": {
            "src", "alt", "title", "width", "height"
        },
        "th": {"colspan", "rowspan"},
        "td": {"colspan", "rowspan"},
    }

    if name not in allowed.get(tag, set()):
        return False

    if name in ("href", "src"):
        url = str(value).strip()
        parsed = urlsplit(url)

        if parsed.scheme:
            return parsed.scheme.lower() in (
                "https", "http"
            )

        return (
            url.startswith("/")
            and not url.startswith("//")
        ) or url.startswith("#")

    return True


def render_content(body):
    rendered = markdown.markdown(
        str(body or ""),
        extensions=[
            "extra",
            "sane_lists",
            "nl2br"
        ],
    )

    return bleach.clean(
        rendered,
        tags=[
            "p", "br", "h1", "h2", "h3", "h4",
            "strong", "b", "em", "i",
            "a", "img", "ul", "ol", "li",
            "blockquote", "code", "pre", "hr",
            "table", "thead", "tbody",
            "tr", "th", "td", "del", "s",
        ],
        attributes=allowed_attribute,
        protocols=["http", "https"],
        strip=True,
    )


def layout(
    title,
    description,
    canonical,
    content,
    page_type="website"
):
    full_title = f"{title} | {SITE_NAME}"
    year = datetime.now(timezone.utc).year

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>{safe(full_title)}</title>
<meta name="description" content="{safe(description)}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{safe(canonical)}">

<meta property="og:type" content="{safe(page_type)}">
<meta property="og:site_name" content="{safe(SITE_NAME)}">
<meta property="og:title" content="{safe(full_title)}">
<meta property="og:description" content="{safe(description)}">
<meta property="og:url" content="{safe(canonical)}">

<meta name="twitter:card" content="summary">

<style>{CSS}</style>
</head>

<body>
<header class="site-header">
  <nav class="nav" aria-label="Main navigation">
    <a class="brand" href="/">{safe(SITE_NAME)}</a>

    <div class="nav-links">
      <a href="/">Home</a>
      <a href="/#articles">Articles</a>
    </div>
  </nav>
</header>

{content}

<footer class="site-footer">
  &copy; {year} {safe(SITE_NAME)}.
  Practical advice for better window care.
</footer>
</body>
</html>"""


def get_issues():
    issues = []
    page = 1

    while True:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            params={
                "state": "open",
                "per_page": 100,
                "page": page,
                "sort": "created",
                "direction": "desc",
            },
            timeout=30,
        )

        response.raise_for_status()
        batch = response.json()

        if not batch:
            break

        issues.extend(
            item for item in batch
            if "pull_request" not in item
        )

        page += 1

    return issues


def publish():
    issues = get_issues()

    cards = []
    urls = [BASE_URL + "/"]
    active_files = set()

    for issue in issues:
        number = issue["number"]
        title = issue.get("title") or "Untitled"
        body = issue.get("body") or ""
        date = issue["created_at"][:10]

        filename = f"issue-{number}.html"
        active_files.add(filename)

        url = f"{BASE_URL}/articles/{filename}"
        urls.append(url)

        description = excerpt(body) or excerpt(title)
        content_html = render_content(body)

        article = f"""
<main class="article-page">
  <article>
    <h1>{safe(title)}</h1>
    <p class="date">
      <time datetime="{date}">{date}</time>
    </p>
    <div class="article-content">
      {content_html}
    </div>
  </article>
</main>"""

        page_html = layout(
            title,
            description,
            url,
            article,
            "article"
        )

        (ARTICLES / filename).write_text(
            page_html,
            encoding="utf-8"
        )

        cards.append(f"""
<article class="article-card">
  <p class="date">{date}</p>

  <h2>
    <a href="/articles/{filename}">
      {safe(title)}
    </a>
  </h2>

  <p>{safe(excerpt(body, 190))}</p>

  <a class="read-more" href="/articles/{filename}">
    Read article →
  </a>
</article>""")

    for old in ARTICLES.glob("issue-*.html"):
        if old.name not in active_files:
            old.unlink()

    listing = "\n".join(cards) if cards else (
        "<p>No articles published yet.</p>"
    )

    home = f"""
<section class="hero">
  <div class="hero-inner">
    <div class="eyebrow">Practical home improvement</div>

    <h1>Clear Advice for Better Windows</h1>

    <p>
      Explore useful guides about window maintenance,
      glass care, repairs, and everyday home comfort.
    </p>
  </div>
</section>

<main class="container" id="articles">
  <h2 class="section-title">Latest Articles</h2>

  <div class="article-grid">
    {listing}
  </div>
</main>"""

    (OUTPUT / "index.html").write_text(
        layout(
            "Window Maintenance & Repair Guides",
            DESCRIPTION,
            BASE_URL + "/",
            home
        ),
        encoding="utf-8"
    )

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(
            f"  <url><loc>{xml_escape(url)}</loc></url>"
            for url in urls
        )
        + "\n</urlset>\n"
    )

    (OUTPUT / "sitemap.xml").write_text(
        sitemap,
        encoding="utf-8"
    )

    (OUTPUT / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {BASE_URL}/sitemap.xml\n",
        encoding="utf-8"
    )

    print(f"Published {len(issues)} articles.")


if __name__ == "__main__":
    publish()
