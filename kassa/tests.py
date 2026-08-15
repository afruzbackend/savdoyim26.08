# -*- coding: utf-8 -*-
"""
Kassa (POS) yadrosi uchun testlar.

Diqqat markazida — PUL va OMBOR bilan ishlaydigan eng muhim yo'llar:
  • savdo_qilish  — chek, ombor kamayishi, kassa balansi, atomiklik
  • qarz_tolash   — qarzni to'lash va ikki marta to'lashning oldini olish

Ishga tushirish:
    python manage.py test kassa
"""
import json
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from users.models import CustomUser, DokonEgasiProfil
from mahsulot.models import Mahsulot
from .models import Kassa, SavdoChek, SavdoChekMahsulot, QarzDaftar, Smena


class SavdoTestBazasi(TestCase):
    """Umumiy tayyorgarlik: do'kon egasi, ochiq smena, ikkita mahsulot."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='egasi', password='parol12345', rol='dokon_egasi'
        )
        self.dokon = DokonEgasiProfil.objects.create(
            foydalanuvchi=self.user, dokon_nomi='Test Do\'kon'
        )
        # Savdo qilish uchun smena ochiq bo'lishi shart.
        Smena.objects.create(dokon=self.dokon, sotuvchi=self.user, holat='ochiq')

        self.m1 = Mahsulot.objects.create(
            nomi='Non', dokon=self.dokon, narx=Decimal('5000'),
            sotib_olish_narxi=Decimal('3000'), soni=10,
        )
        self.m2 = Mahsulot.objects.create(
            nomi='Sut', dokon=self.dokon, narx=Decimal('12000'),
            sotib_olish_narxi=Decimal('9000'), soni=2,
        )
        self.client.force_login(self.user)

    def _savdo(self, mahsulotlar, tolash_turi='naqd', **qoshimcha):
        payload = {'mahsulotlar': mahsulotlar, 'tolash_turi': tolash_turi}
        payload.update(qoshimcha)
        return self.client.post(
            reverse('savdo_qilish'),
            data=json.dumps(payload),
            content_type='application/json',
        )


class SavdoQilishTest(SavdoTestBazasi):

    def test_naqd_savdo_omborni_kamaytiradi_va_kassani_oshiradi(self):
        resp = self._savdo(
            [{'id': self.m1.id, 'soni': 3}],
            tolash_turi='naqd', berilgan='20000',
        )
        self.assertEqual(resp.status_code, 200)

        self.m1.refresh_from_db()
        self.assertEqual(self.m1.soni, 7)                 # 10 - 3

        self.assertEqual(SavdoChek.objects.count(), 1)
        chek = SavdoChek.objects.get()
        self.assertEqual(chek.jami, Decimal('15000'))     # 3 * 5000

        kassa = Kassa.objects.get(dokon=self.dokon)
        self.assertEqual(kassa.balans, Decimal('15000'))

    def test_yetarli_bolmasa_rad_etadi_va_hech_narsa_yozilmaydi(self):
        resp = self._savdo(
            [{'id': self.m2.id, 'soni': 5}],   # omborda faqat 2 ta
            tolash_turi='naqd', berilgan='100000',
        )
        self.assertEqual(resp.status_code, 400)

        self.m2.refresh_from_db()
        self.assertEqual(self.m2.soni, 2)                 # o'zgarmadi
        self.assertEqual(SavdoChek.objects.count(), 0)    # chek yaratilmadi

    def test_atomiklik_ikkinchi_mahsulot_yetmasa_birinchisi_ham_bekor(self):
        """Ko'p mahsulotli savatda bittasi yetmasa — BUTUN savdo bekor bo'ladi
        (yarim yozilgan savdo qolmasligi kerak)."""
        resp = self._savdo(
            [
                {'id': self.m1.id, 'soni': 2},    # bu yetarli
                {'id': self.m2.id, 'soni': 99},   # bu yetmaydi
            ],
            tolash_turi='naqd', berilgan='500000',
        )
        self.assertEqual(resp.status_code, 400)

        # Hech narsa o'zgarmasligi kerak:
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.assertEqual(self.m1.soni, 10)
        self.assertEqual(self.m2.soni, 2)
        self.assertEqual(SavdoChek.objects.count(), 0)
        self.assertEqual(SavdoChekMahsulot.objects.count(), 0)

    def test_qarz_savdo_kassani_oshirmaydi_va_qarz_yozadi(self):
        resp = self._savdo(
            [{'id': self.m1.id, 'soni': 1}],
            tolash_turi='qarz', mijoz_ism='Ali', mijoz_telefon='901112233',
        )
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(QarzDaftar.objects.count(), 1)
        qarz = QarzDaftar.objects.get()
        self.assertEqual(qarz.summa, Decimal('5000'))
        self.assertFalse(qarz.to_langan)

        # Qarz savdoda kassaga pul tushmaydi.
        kassa = Kassa.objects.filter(dokon=self.dokon).first()
        self.assertTrue(kassa is None or kassa.balans == Decimal('0'))

    def test_smena_yopiq_bolsa_sotib_bolmaydi(self):
        Smena.objects.filter(dokon=self.dokon).update(holat='yopiq')
        resp = self._savdo(
            [{'id': self.m1.id, 'soni': 1}],
            tolash_turi='naqd', berilgan='5000',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(SavdoChek.objects.count(), 0)


class QarzTolashTest(SavdoTestBazasi):

    def _qarz_yarat(self):
        return QarzDaftar.objects.create(
            dokon=self.dokon, mijoz_ism='Vali', summa=Decimal('30000'),
        )

    def test_qarz_tolash_kassani_oshiradi(self):
        qarz = self._qarz_yarat()
        resp = self.client.post(reverse('qarz_tolash', args=[qarz.id]))
        self.assertEqual(resp.status_code, 200)

        qarz.refresh_from_db()
        self.assertTrue(qarz.to_langan)
        self.assertIsNotNone(qarz.to_langan_sana)

        kassa = Kassa.objects.get(dokon=self.dokon)
        self.assertEqual(kassa.balans, Decimal('30000'))

    def test_ikki_marta_tolash_summani_ikki_marta_qoshmaydi(self):
        qarz = self._qarz_yarat()
        self.client.post(reverse('qarz_tolash', args=[qarz.id]))
        resp2 = self.client.post(reverse('qarz_tolash', args=[qarz.id]))

        self.assertEqual(resp2.status_code, 404)          # allaqachon to'langan
        kassa = Kassa.objects.get(dokon=self.dokon)
        self.assertEqual(kassa.balans, Decimal('30000'))  # ikki marta emas


class HisobotGrafikTest(SavdoTestBazasi):
    """`hisobot_view` grafik ma'lumotlari (soat/kun/oy) TO'G'RI chiqishini
    muhrlaydi. Bu test optimallashtirishdan OLDIN ham, KEYIN ham bir xil
    natija berishini kafolatlaydi (buzilishni darrov ushlaydi)."""

    TZ = ZoneInfo('Asia/Tashkent')

    def _chek(self, aware_dt, summa):
        """Berilgan (timezone-aware) vaqtda summa bilan chek yaratadi.
        yaratilgan=auto_now_add bo'lgani uchun keyin update bilan o'rnatamiz."""
        chek = SavdoChek.objects.create(dokon=self.dokon, jami=Decimal(str(summa)))
        SavdoChek.objects.filter(id=chek.id).update(yaratilgan=aware_dt)
        return chek

    def _bugun(self, soat, minut=0):
        b = timezone.localdate()
        return datetime(b.year, b.month, b.day, soat, minut, tzinfo=self.TZ)

    def _grafik(self, davr):
        # Template render'siz to'g'ridan-to'g'ri sof funksiyani chaqiramiz
        # (Py3.14 test-client context bug'ini chetlab o'tadi).
        from kassa.views import _hisobot_grafik
        return _hisobot_grafik(self.dokon, davr, timezone.localdate())

    def test_kunlik_soat_data(self):
        self._chek(self._bugun(10), 15000)
        self._chek(self._bugun(10, 30), 5000)   # yana soat 10
        self._chek(self._bugun(14), 8000)

        soat_data, _, _ = self._grafik('kunlik')

        self.assertEqual(len(soat_data), 24)
        by_soat = {d['soat']: d['summa'] for d in soat_data}
        self.assertEqual(by_soat[10], 20000.0)   # 15000 + 5000
        self.assertEqual(by_soat[14], 8000.0)
        self.assertEqual(by_soat[9], 0.0)

    def test_haftalik_kun_data(self):
        self._chek(self._bugun(12), 25000)
        _, kun_data, _ = self._grafik('haftalik')

        self.assertEqual(len(kun_data), 7)
        # Oxirgi element — bugun
        self.assertEqual(kun_data[-1]['summa'], 25000.0)
        for kun in kun_data[:-1]:
            self.assertEqual(kun['summa'], 0.0)

    def test_oylik_kun_data(self):
        bugun = timezone.localdate()
        self._chek(self._bugun(12), 40000)
        _, kun_data, _ = self._grafik('oylik')

        # Bugungi kun raqamiga mos yozuv 40000 bo'lishi kerak
        bugungi = [d for d in kun_data if d['kun'] == bugun.day][0]
        self.assertEqual(bugungi['summa'], 40000.0)

    def test_yillik_oy_data(self):
        bugun = timezone.localdate()
        self._chek(self._bugun(12), 3_000_000)
        _, _, oy_data = self._grafik('yillik')

        self.assertEqual(len(oy_data), 12)
        joriy_oy = oy_data[bugun.month - 1]
        self.assertEqual(joriy_oy['summa'], 3_000_000.0)
        self.assertEqual(joriy_oy['mln'], 3.0)
        self.assertEqual(joriy_oy['foiz'], 10.0)   # 3mln / 30mln * 100
