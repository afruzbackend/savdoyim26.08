from django.contrib import admin
from .models import (Kassa, SavdoChek, SavdoChekMahsulot, QarzDaftar,
                     Qaytarish, QaytarishItem)


@admin.register(Kassa)
class KassaAdmin(admin.ModelAdmin):
    list_display = ['dokon', 'balans', 'yangilangan']


class SavdoChekMahsulotInline(admin.TabularInline):
    model = SavdoChekMahsulot
    extra = 0


@admin.register(SavdoChek)
class SavdoChekAdmin(admin.ModelAdmin):
    list_display = ['id', 'dokon', 'jami', 'tolash_turi', 'yaratilgan']
    inlines = [SavdoChekMahsulotInline]


@admin.register(QarzDaftar)
class QarzDaftarAdmin(admin.ModelAdmin):
    list_display = ['mijoz_ism', 'dokon', 'summa', 'to_langan', 'yaratilgan']
    list_filter = ['to_langan']


class QaytarishItemInline(admin.TabularInline):
    model = QaytarishItem
    extra = 0


@admin.register(Qaytarish)
class QaytarishAdmin(admin.ModelAdmin):
    list_display = ['id', 'dokon', 'chek', 'summa', 'sabab', 'kassadan', 'yaratilgan']
    list_filter = ['sabab', 'kassadan']
    inlines = [QaytarishItemInline]
