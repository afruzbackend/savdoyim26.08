from django.contrib import admin
from .models import (Kategoriya, Mahsulot, SkannerLog, MahsulotSharh, SharhRasm,
                    Inventarizatsiya, InventarizatsiyaItem, NarxTarix)


@admin.register(NarxTarix)
class NarxTarixAdmin(admin.ModelAdmin):
    list_display = ['mahsulot', 'eski_narx', 'yangi_narx', 'eski_sotib', 'yangi_sotib', 'kim', 'sana']
    search_fields = ['mahsulot__nomi']


@admin.register(Kategoriya)
class KategoriyaAdmin(admin.ModelAdmin):
    list_display = ['nomi']


class InventarizatsiyaItemInline(admin.TabularInline):
    model = InventarizatsiyaItem
    extra = 0


@admin.register(Inventarizatsiya)
class InventarizatsiyaAdmin(admin.ModelAdmin):
    list_display = ['id', 'dokon', 'holat', 'boshlagan', 'boshlangan', 'yakunlangan_vaqt']
    list_filter = ['holat']
    inlines = [InventarizatsiyaItemInline]


@admin.register(Mahsulot)
class MahsulotAdmin(admin.ModelAdmin):
    list_display = ['nomi', 'dokon', 'narx', 'soni', 'faol']
    list_filter = ['faol', 'dokon']
    search_fields = ['nomi', 'barkod']


@admin.register(SkannerLog)
class SkannerLogAdmin(admin.ModelAdmin):
    list_display = ['mahsulot', 'harakat', 'soni', 'foydalanuvchi', 'yaratilgan']


class SharhRasmInline(admin.TabularInline):
    model = SharhRasm
    extra = 0
    readonly_fields = ['yaratilgan']


@admin.register(MahsulotSharh)
class MahsulotSharhAdmin(admin.ModelAdmin):
    """Sharh moderatsiyasi: admin yashira/tiklay oladi (o'chirmasdan).
    Soft-delete qilingan sharhlar ham ko'rinadi (hammasi manager)."""
    list_display = ['id', 'mahsulot', 'foydalanuvchi', 'yulduz',
                    'xaridor_tasdiqlangan', 'holat', 'is_deleted', 'yaratilgan']
    list_filter = ['holat', 'yulduz', 'xaridor_tasdiqlangan', 'is_deleted']
    search_fields = ['mahsulot__nomi', 'foydalanuvchi__username', 'izoh']
    readonly_fields = ['mahsulot', 'foydalanuvchi', 'buyurtma',
                       'xaridor_tasdiqlangan', 'yaratilgan', 'yangilangan',
                       'is_deleted', 'deleted_at']
    inlines = [SharhRasmInline]
    actions = ['yashir', 'tikla']

    def get_queryset(self, request):
        # O'chirilgan sharhlarni ham ko'rsatish (to'liq moderatsiya uchun)
        return self.model.hammasi.get_queryset().select_related(
            'mahsulot', 'foydalanuvchi', 'buyurtma'
        )

    @admin.action(description="Tanlangan sharhlarni yashirish")
    def yashir(self, request, queryset):
        n = queryset.update(holat='yashirin')
        self.message_user(request, f"{n} ta sharh yashirildi.")

    @admin.action(description="Tanlangan sharhlarni tiklash (faol)")
    def tikla(self, request, queryset):
        n = queryset.update(holat='faol')
        self.message_user(request, f"{n} ta sharh tiklandi.")
