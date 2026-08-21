from django.test import TestCase
from django.urls import reverse


class PwaConfigurationTests(TestCase):
    def test_service_worker_is_available_at_root_scope(self):
        response = self.client.get(reverse("core:service_worker"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/javascript")
        self.assertContains(response, 'const CACHE_NAME = "kohaga-pwa-v2";')

    def test_manifest_is_available_at_root_scope(self):
        response = self.client.get(reverse("core:web_manifest"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/manifest+json")
        self.assertContains(response, '"display": "standalone"')
        self.assertContains(response, '"id": "/"')

    def test_login_page_contains_pwa_metadata_and_install_hook(self):
        response = self.client.get(reverse("core:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("core:web_manifest"))
        self.assertContains(response, 'name="theme-color"')
        self.assertContains(response, reverse("core:service_worker"))
        self.assertContains(response, "beforeinstallprompt")
        self.assertContains(response, 'id="pwaInstallButton"')
