from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, DokonEgasiProfil, SotuvchiProfil,
    ZavodProfil, YetkazibBeruvchiProfil, MijozProfil,
    Bildirishnoma, AuditLog, TelegramLink
)


@admin.register(TelegramLink)
class TelegramLinkAdmin(admin.ModelAdmin):
    list_display = ['foydalanuvchi', 'chat_id', 'telegram_username', 'ulangan', 'oxirgi_faollik']
    search_fields = ['foydalanuvchi__username', 'chat_id', 'telegram_username']
    readonly_fields = ['ulangan', 'oxirgi_faollik']


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'first_name', 'rol', 'tasdiqlangan', 'telefon']
    list_filter = ['rol', 'tasdiqlangan']
    fieldsets = UserAdmin.fieldsets + (
        ('Qo\'shimcha', {'fields': ('rol', 'telefon', 'jshshr', 'passport', 'tasdiqlangan', 'rasm', 'latitude', 'longitude')}),
    )


@admin.register(DokonEgasiProfil)
class DokonEgasiProfilAdmin(admin.ModelAdmin):
    list_display = ['dokon_nomi', 'foydalanuvchi', 'soliq_raqami']


@admin.register(SotuvchiProfil)
class SotuvchiProfilAdmin(admin.ModelAdmin):
    list_display = ['foydalanuvchi', 'dokon', 'sorov_holati']
    list_filter = ['sorov_holati']


@admin.register(ZavodProfil)
class ZavodProfilAdmin(admin.ModelAdmin):
    list_display = ['zavod_nomi', 'foydalanuvchi', 'tasdiqlangan']


@admin.register(YetkazibBeruvchiProfil)
class YetkazibBeruvchiProfilAdmin(admin.ModelAdmin):
    list_display = ['foydalanuvchi', 'zavod']


@admin.register(MijozProfil)
class MijozProfilAdmin(admin.ModelAdmin):
    list_display = ['foydalanuvchi']


@admin.register(Bildirishnoma)
class BildirishnomaAdmin(admin.ModelAdmin):
    list_display = ['id', 'foydalanuvchi', 'matn', 'oqilgan', 'is_deleted', 'yaratilgan']
    list_filter = ['oqilgan', 'is_deleted']
    search_fields = ['foydalanuvchi__username', 'matn']
    readonly_fields = ['yaratilgan']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Faqat o'qish uchun — audit yozuvlari qo'lda o'zgartirilmaydi."""
    list_display = ['vaqt', 'foydalanuvchi', 'amal', 'obyekt_turi', 'obyekt_id', 'ip']
    list_filter = ['amal', 'vaqt']
    search_fields = ['foydalanuvchi__username', 'tafsilot', 'obyekt_turi']
    readonly_fields = ['foydalanuvchi', 'amal', 'obyekt_turi', 'obyekt_id',
                       'tafsilot', 'ip', 'vaqt']
    date_hierarchy = 'vaqt'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
