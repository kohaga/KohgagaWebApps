"""Normalize imported Elementor EWM knowledge hub into portable Django HTML."""
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from blog.models import Post


class Command(BaseCommand):
    help = "Convert SAP EWM Knowledge Hub WordPress markup to clean, collapsible HTML."

    def handle(self, *args, **options):
        post = Post.objects.filter(title="SAP EWM Knowledge Hub").first()
        if not post:
            raise CommandError("Post 'SAP EWM Knowledge Hub' is not imported.")
        # Keep re-runs harmless: only convert the original HTML.
        if 'data-kohaga-hub="1"' in post.content:
            self.stdout.write("Already formatted; no changes made.")
            return
        soup = BeautifulSoup(post.content, "html.parser")
        sections = soup.find_all("details")
        if len(sections) != 8:
            raise CommandError(f"Expected 8 hub sections, found {len(sections)}. No change made.")
        result = BeautifulSoup('<div class="ewm-knowledge-hub" data-kohaga-hub="1"></div>', "html.parser")
        root = result.div
        intro = result.new_tag("p")
        intro["class"] = "hub-intro"
        intro.string = "A personal collection of links and references that I’ve found particularly useful while working on SAP EWM topics."
        root.append(intro)
        links = result.new_tag("div")
        links["class"] = "hub-quick-links"
        for anchor in soup.find_all("a", recursive=False)[:6]:
            anchor.extract()
            links.append(anchor)
        root.append(links)
        for section in sections:
            section.extract()
            root.append(section)
        for tag in root.select("svg, script, style, iframe, form"):
            tag.decompose()
        for tag in root.find_all(True):
            # No Elementor handlers, inline scripting, or CSS needed in Django.
            for name in list(tag.attrs):
                if name not in {"href", "src", "alt", "title", "class", "open", "loading"}:
                    del tag.attrs[name]
            if tag.name == "a":
                tag["target"] = "_blank"
                tag["rel"] = "noopener noreferrer"
            elif tag.name == "img":
                tag["loading"] = "lazy"
        for summary in root.find_all("summary"):
            summary["class"] = "hub-section-title"
        post.content = str(root)
        post.save(update_fields=["content", "updated_at"])
        self.stdout.write(self.style.SUCCESS("EWM Knowledge Hub formatted. Review the post in /blog/."))
