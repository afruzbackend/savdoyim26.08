from django.contrib import admin
from .models import Jonatma, JonatmaMahsulot, YetkazuvchiSorov


class JonatmaMahsulotInline(admin.TabularInline):
    model = JonatmaMahsulot
    extra = 0


@admin.register(Jonatma)
class JonatmaAdmin(admin.ModelAdmin):
    list_display = ['id', 'zavod', 'yetkazuvchi', 'holat', 'jami_summa', 'barkod', 'yaratilgan']
    list_filter = ['holat', 'zavod']
    search_fields = ['barkod', 'zavod__zavod_nomi']
    inlines = [JonatmaMahsulotInline]


@admin.register(JonatmaMahsulot)
class JonatmaMahsulotAdmin(admin.ModelAdmin):
    list_display = ['jonatma', 'mahsulot_nomi', 'soni', 'narx']


@admin.register(YetkazuvchiSorov)
class YetkazuvchiSorovAdmin(admin.ModelAdmin):
    list_display = ['yetkazuvchi', 'zavod', 'holat', 'yaratilgan']
    list_filter = ['holat', 'zavod']