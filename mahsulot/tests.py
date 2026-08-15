# -*- coding: utf-8 -*-
"""Jo'natma qabul (zavod -> do'kon ombori) uchun testlar.

Do'kon QR (barkod) orqali jo'natmani qabul qilganda mahsulotlar OMBORGA
qo'shiladi. Eng katta xavf — bir jo'natmani IKKI marta qabul qilib, omborni
ikki barobar oshirib yuborish. Bu yerda tekshiriladi:
  • yangi mahsulot omborga qo'shiladi;
  • mavjud mahsulot (barkod bo'yicha) soni to'g'ri oshadi;
  • ikkinchi marta qabul RAD etiladi va ombor o'zgarmaydi (idempotentlik).

Ishga tushirish:
    python manage.py test mahsulot
"""
import json
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from users.models import CustomUser, DokonEgasiProfil, ZavodProfil
from yetkazib_beruvchi.models import Jonatma, JonatmaMahsulot
from .models import Mahsulot


class JonatmaQabulTest(TestCase):

    def setUp(self):
        # Do'kon egasi
        self.egasi = CustomUser.objects.create_user(
            username='egasi', password='parol12345', rol='dokon_egasi'
        )
        self.dokon = DokonEgasiProfil.objects.create(
            foydalanuvchi=self.egasi, dokon_nomi='Test Do\'kon'
        )
        # Zavod (jo'natma manbai)
        self.zavod_user = CustomUser.objects.create_user(
            username='zavod', password='parol12345', rol='zavod'
        )
        self.zavod = ZavodProfil.objects.create(
            foydalanuvchi=self.zavod_user, zavod_nomi='Test Zavod'
        )
        self.client.force_login(self.egasi)

    def _jonatma(self, mahsulotlar):
        """mahsulotlar: [(nomi, barkod, soni, narx), ...]"""
        j = Jonatma.objects.create(zavod=self.zavod, manzil_dokon=self.dokon)
        for nomi, barkod, soni, narx in mahsulotlar:
            JonatmaMahsulot.objects.create(
                jonatma=j, mahsulot_nomi=nomi, barkod=barkod,
                soni=soni, narx=Decimal(str(narx)),
            )
        j.refresh_from_db()   # save() barkodni avto-generatsiya qiladi
        return j

    def _qabul(self, barkod):
        return self.client.post(
            reverse('jonatma_qabul_dokon_action'),
            data=json.dumps({'barkod': barkod}),
            content_type='application/json',
        )

    def test_yangi_mahsulot_omborga_qoshiladi(self):
        j = self._jonatma([('Yog\'', '111', 20, 15000)])
        resp = self._qabul(j.barkod)
        self.assertEqual(resp.status_code, 200)

        mah = Mahsulot.objects.get(dokon=self.dokon, barkod='111')
        self.assertEqual(mah.soni, 20)

        j.refresh_from_db()
        self.assertTrue(j.dokon_qabul)
        self.assertEqual(j.holat, 'yetkazildi')

    def test_mavjud_mahsulot_soni_oshadi(self):
        Mahsulot.objects.create(
            nomi='Yog\'', dokon=self.dokon, barkod='111',
            narx=Decimal('15000'), sotib_olish_narxi=Decimal('12000'), soni=5,
        )
        j = self._jonatma([('Yog\'', '111', 20, 15000)])
        self._qabul(j.barkod)

        mah = Mahsulot.objects.get(dokon=self.dokon, barkod='111')
        self.assertEqual(mah.soni, 25)                 # 5 + 20
        # Ikkita alohida yozuv yaratilmasligi kerak
        self.assertEqual(Mahsulot.objects.filter(dokon=self.dokon, barkod='111').count(), 1)

    def test_ikki_marta_qabul_omborni_ikki_barobar_oshirmaydi(self):
        j = self._jonatma([('Yog\'', '111', 20, 15000)])
        resp1 = self._qabul(j.barkod)
        resp2 = self._qabul(j.barkod)

        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 400)        # allaqachon qabul qilingan

        mah = Mahsulot.objects.get(dokon=self.dokon, barkod='111')
        self.assertEqual(mah.soni, 20)                  # 40 EMAS

    def test_notogri_barkod_404(self):
        resp = self._qabul('YOQBUNDAY')
        self.assertEqual(resp.status_code, 404)

    def test_bir_nechta_mahsulot_qabul(self):
        j = self._jonatma([
            ('Yog\'', '111', 10, 15000),
            ('Un', '222', 30, 8000),
        ])
        resp = self._qabul(j.barkod)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Mahsulot.objects.get(dokon=self.dokon, barkod='111').soni, 10)
        self.assertEqual(Mahsulot.objects.get(dokon=self.dokon, barkod='222').soni, 30)
