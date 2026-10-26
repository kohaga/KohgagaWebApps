from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="Category", fields=[
            ("id", models.AutoField(primary_key=True, serialize=False)),
            ("name", models.CharField(max_length=80, unique=True)),
            ("slug", models.SlugField(allow_unicode=True, max_length=100, unique=True)),
        ], options={"ordering": ("name",), "verbose_name_plural": "Categories"}),
        migrations.CreateModel(name="Post", fields=[
            ("id", models.AutoField(primary_key=True, serialize=False)),
            ("title", models.CharField(max_length=250)),
            ("slug", models.SlugField(allow_unicode=True, max_length=260, unique=True)),
            ("excerpt", models.TextField(blank=True)),
            ("content", models.TextField(help_text="Trusted HTML content; edit only as an administrator.")),
            ("featured_image_url", models.URLField(blank=True, max_length=1000)),
            ("published_at", models.DateTimeField(blank=True, db_index=True, null=True)),
            ("is_published", models.BooleanField(db_index=True, default=False)),
            ("original_url", models.URLField(blank=True, max_length=1000)),
            ("wordpress_id", models.PositiveBigIntegerField(blank=True, null=True, unique=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="posts", to="blog.category")),
        ], options={"ordering": ("-published_at", "-pk")}),
    ]
