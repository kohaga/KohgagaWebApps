"""Import a local WordPress WXR XML export. Does not download remote images."""
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from blog.models import Category, Post

WP = "{http://wordpress.org/export/1.2/}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"
EXCERPT = "{http://wordpress.org/export/1.2/excerpt/}"


class Command(BaseCommand):
    help = "Import posts from a WordPress WXR XML export (idempotent by WP post ID). Defaults to unpublished drafts."

    def add_arguments(self, parser):
        parser.add_argument("file", help="Path to WordPress Tools > Export XML file")
        parser.add_argument("--publish", action="store_true", help="Publish imported posts with published WP status")

    def handle(self, *args, **options):
        source = Path(options["file"])
        if not source.is_file():
            raise CommandError(f"File not found: {source}")
        try:
            root = ET.parse(source).getroot()
        except ET.ParseError as exc:
            raise CommandError(f"Invalid XML: {exc}") from exc
        counts = {"created": 0, "updated": 0, "skipped": 0}
        for item in root.findall("./channel/item"):
            if (item.findtext(WP + "post_type") or "") != "post":
                counts["skipped"] += 1
                continue
            wp_id_str = item.findtext(WP + "post_id")
            if not wp_id_str or not wp_id_str.isdecimal():
                counts["skipped"] += 1
                continue
            wp_id = int(wp_id_str)
            title = item.findtext("title") or f"WordPress post {wp_id}"
            old_url = item.findtext("link") or ""
            old_slug = item.findtext(WP + "post_name") or urlparse(old_url).path.rstrip("/").rsplit("/", 1)[-1]
            slug = slugify(old_slug, allow_unicode=True) or f"wp-{wp_id}"
            existing = Post.objects.filter(wordpress_id=wp_id).first()
            if Post.objects.filter(slug=slug).exclude(wordpress_id=wp_id).exists():
                slug = f"{slug[:240]}-{wp_id}"
            category_node = next((c for c in item.findall("category") if c.get("domain") == "category"), None)
            category = None
            if category_node is not None and category_node.text:
                label = category_node.text.strip()[:80]
                category_slug = slugify(category_node.get("nicename") or label, allow_unicode=True)[:100]
                category, _ = Category.objects.get_or_create(slug=category_slug, defaults={"name": label})
            date_str = item.findtext(WP + "post_date_gmt") or ""
            try:
                published_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt_timezone.utc)
            except ValueError:
                published_at = None
            if published_at and published_at.year <= 1970:
                published_at = None
            status = (item.findtext(WP + "status") or "") == "publish"
            defaults = {
                "title": title[:250], "slug": slug[:260],
                "excerpt": item.findtext(EXCERPT + "encoded") or "",
                "content": item.findtext(CONTENT + "encoded") or "",
                "category": category, "published_at": published_at,
                "original_url": old_url[:1000],
                "is_published": bool(options["publish"] and status and published_at),
            }
            # Re-importing never silently changes publication state of an existing post.
            if existing:
                defaults["is_published"] = existing.is_published
            _, created = Post.objects.update_or_create(wordpress_id=wp_id, defaults=defaults)
            counts["created" if created else "updated"] += 1
        self.stdout.write(self.style.SUCCESS(f"Import complete: {counts}. Remote media URLs remain external; review posts before publishing."))
