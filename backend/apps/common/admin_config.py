"""AppConfig that swaps in our custom admin site (master prompt §6)."""
from django.contrib.admin.apps import AdminConfig


class LMSAdminConfig(AdminConfig):
    default_site = "apps.common.admin_site.LMSAdminSite"
