from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from .models import Category, Post


def index(request):
    posts = Post.objects.filter(is_published=True, published_at__lte=timezone.now()).select_related("category")
    category = request.GET.get("category", "")
    query = request.GET.get("q", "").strip()
    if category:
        posts = posts.filter(category__slug=category)
    if query:
        posts = posts.filter(Q(title__icontains=query) | Q(excerpt__icontains=query) | Q(content__icontains=query))
    page = Paginator(posts, 9).get_page(request.GET.get("page"))
    return render(request, "blog/index.html", {"page": page, "categories": Category.objects.all(), "selected_category": category, "query": query})


def detail(request, slug):
    post = get_object_or_404(Post, slug=slug, is_published=True, published_at__lte=timezone.now())
    return render(request, "blog/detail.html", {"post": post})
