from django.contrib import admin

from .models import CoinTransaction, PaymentRecord, PremiumGrant


@admin.register(CoinTransaction)
class CoinTransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "type", "reference_id", "created_at")
    list_filter = ("type",)
    search_fields = ("user__email", "reference_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PremiumGrant)
class PremiumGrantAdmin(admin.ModelAdmin):
    list_display = ("user", "source", "start_date", "end_date", "is_active")
    list_filter = ("source",)
    search_fields = ("user__email",)


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "plan_code", "status", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("user__email", "external_id")
