"""REST API serializerlari — kelajakdagi React/mobil ilova uchun poydevor.

Hozircha asosan O'QISH (read) uchun. Yozish (savdo qilish va h.k.) mavjud
web view'larda atomik qilingan — ularni API'ga ko'chirish keyingi bosqich.
"""
from rest_framework import serializers

from users.models import CustomUser
from mahsulot.models import Mahsulot
from kassa.models import Kassa, SavdoChek, SavdoChekMahsulot, QarzDaftar


class UserSerializer(serializers.ModelSerializer):
    dokon_nomi = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'rol', 'dokon_nomi']

    def get_dokon_nomi(self, obj):
        from api.utils import foydalanuvchi_dokoni
        dokon = foydalanuvchi_dokoni(obj)
        return dokon.dokon_nomi if dokon else None


class MahsulotSerializer(serializers.ModelSerializer):
    kam_qoldi = serializers.SerializerMethodField()

    class Meta:
        model = Mahsulot
        fields = [
            'id', 'nomi', 'barkod', 'ikpu', 'narx', 'sotib_olish_narxi',
            'soni', 'minimum_son', 'birlik', 'faol', 'kam_qoldi',
            'yaroqlilik_muddati', 'rasm', 'tavsif',
        ]

    def get_kam_qoldi(self, obj):
        return obj.soni <= obj.minimum_son


class OmmaviyMahsulotSerializer(serializers.ModelSerializer):
    """Mijoz uchun: mahsulot + qaysi do'konga tegishli (ommaviy ko'rinish)."""
    dokon_nomi = serializers.SerializerMethodField()
    dokon_id = serializers.SerializerMethodField()

    class Meta:
        model = Mahsulot
        fields = [
            'id', 'nomi', 'barkod', 'narx', 'soni', 'birlik',
            'rasm', 'tavsif', 'dokon_id', 'dokon_nomi',
        ]

    def get_dokon_nomi(self, obj):
        return obj.dokon.dokon_nomi if obj.dokon_id else None

    def get_dokon_id(self, obj):
        return obj.dokon_id


class KassaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kassa
        fields = ['balans', 'yangilangan']


class QarzDaftarSerializer(serializers.ModelSerializer):
    class Meta:
        model = QarzDaftar
        fields = [
            'id', 'mijoz_ism', 'mijoz_telefon', 'summa', 'tolangan_summa', 'jami_qarz',
            'to_langan', 'to_langan_sana', 'qaytarish_sana', 'yaratilgan',
        ]


class SavdoChekMahsulotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavdoChekMahsulot
        fields = ['mahsulot_nomi', 'ikpu', 'soni', 'narx', 'jami']


class SavdoChekSerializer(serializers.ModelSerializer):
    mahsulotlar = SavdoChekMahsulotSerializer(many=True, read_only=True)

    class Meta:
        model = SavdoChek
        fields = [
            'id', 'jami', 'chegirma', 'to_langan', 'qaytim',
            'tolash_turi', 'yaratilgan', 'mahsulotlar',
        ]
