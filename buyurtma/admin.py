from django.contrib import admin
from .models import (
    Buyurtma, BuyurtmaMahsulot, YetkazishBuyurtma,
    MijozBuyurtma, MijozBuyurtmaItem, BuyurtmaStatusTarix,
)


class BuyurtmaMahsulotInline(admin.TabularInline):
    model = BuyurtmaMahsulot
    extra = 0


@admin.register(Buyurtma)
class BuyurtmaAdmin(admin.ModelAdmin):
    list_display = ['id', 'dokon', 'zavod', 'holat', 'jami', 'yaratilgan']
    list_filter = ['holat']
    inlines = [BuyurtmaMahsulotInline]


admin.site.register(YetkazishBuyurtma)


class MijozBuyurtmaItemInline(admin.TabularInline):
    model = MijozBuyurtmaItem
    extra = 0
    readonly_fields = ['mahsulot_nomi', 'narx']


class BuyurtmaStatusTarixInline(admin.TabularInline):
    model = BuyurtmaStatusTarix
    extra = 0
    readonly_fields = ['holat', 'vaqt']
    can_delete = False


@admin.register(MijozBuyurtma)
class MijozBuyurtmaAdmin(admin.ModelAdmin):
    list_display = ['raqam', 'mijoz', 'dokon', 'holat',
                    'topshirish_turi', 'jami', 'is_deleted', 'yaratilgan']
    list_filter = ['holat', 'topshirish_turi', 'is_deleted']
    search_fields = ['mijoz__username', 'dokon__dokon_nomi']
    readonly_fields = ['jami', 'yaratilgan', 'yangilangan', 'is_deleted', 'deleted_at']
    inlines = [MijozBuyurtmaItemInline, BuyurtmaStatusTarixInline]

    def get_queryset(self, request):
        return self.model.hammasi.get_queryset().select_related('mijoz', 'dokon')
