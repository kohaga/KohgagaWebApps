# KOHAGA Blog

Public Django blog at /blog/; management via /admin/. Content is trusted HTML (only administrators should be able to edit it).

## First deploy

1. Pull the feature branch locally for testing; merge only after review.
2. Run `python manage.py migrate`.
3. Run `python manage.py check` and test /blog/ and /admin/.
4. WordPress: Tools > Export > Posts (WXR XML). Keep a full backup of WordPress files and database as well.
5. Run `python manage.py import_wordpress wordpress-export.xml` to import **drafts**; validate text, category, embeds, HTML and image URLs in admin.
6. If desired, `--publish` publishes only posts with published status and valid date on *first import*. Publish verified drafts in admin otherwise.

Caveats: WXR import does **not** download image/media files or rewrite their URLs, and WordPress shortcodes/blocks may require manual clean-up. The original domain's URL routing or DNS must be configured separately; do not shut off WordPress before media assets and old links have been checked. Embedded scripts in imported HTML should be reviewed before publication. WordPress IDs are used for repeatable imports.
