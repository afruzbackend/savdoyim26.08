# -*- coding: utf-8 -*-
"""Sodiqlik ballari (loyalty) uchun testlar.

Ballar QIYMATga (pulga) teng — 1 ball = 100 so'm chegirma — shuning uchun ular
noto'g'ri yoki ikki marta berilmasligi muhim. Bu yerda tekshiriladi:
  • ball to'g'ri hisoblanadi (1 ball / 1000 so'm);
  • kichik summa (< 1000) ball bermaydi;
  • mijoz profili yo'q bo'lsa xatolik bermaydi (graceful);
  • buyurtma yakuniy holatga yetganda ball QAYTA berilmaydi (state-machine kafolati).

Ishga tushirish:
    python manage.py test buyurtma
"""
from decimal import Decimal

from django.test import TestCase

from users.models import CustomUser, DokonEgasiProfil, MijozProfil
from .models import MijozBuyurtma, SodiqlikTarix
from .services import SodiqlikService, BALL_TOPISH_NARXI


class SodiqlikBazasi(TestCase):
    def setUp(self):
        # Do'kon egasi + do'kon
        self.egasi = CustomUser.objects.create_user(
            username='egasi', password='parol12345', rol='dokon_egasi'
        )
        self.dokon = DokonEgasiProfil.objects.create(
            foydalanuvchi=self.egasi, dokon_nomi='Test Do\'kon'
        )
        # Mijoz + profil (ballar shu profilga yoziladi)
        self.mijoz = CustomUser.objects.create_user(
            username='mijoz', password='parol12345', rol='mijoz'
        )
        self.profil = MijozProfil.objects.create(foydalanuvchi=self.mijoz)

    def _buyurtma(self, jami, holat='tayyor'):
        return MijozBuyurtma.objects.create(
            mijoz=self.mijoz, dokon=self.dokon,
            jami=Decimal(str(jami)), holat=holat,
        )


class BallBerTest(SodiqlikBazasi):

    def test_ball_togri_hisoblanadi(self):
        b = self._buyurtma(25000)
        berilgan = SodiqlikService.ball_ber(b)

        self.assertEqual(berilgan, 25)                 # 25000 // 1000
        self.profil.refresh_from_db()
        self.assertEqual(self.profil.sodiqlik_ball, 25)

        tarix = SodiqlikTarix.objects.get()
        self.assertEqual(tarix.ball, 25)
        self.assertEqual(tarix.mijoz, self.mijoz)

    def test_qismli_summa_pastga_yaxlitlanadi(self):
        b = self._buyurtma(25900)                      # 25.9 → 25
        self.assertEqual(SodiqlikService.ball_ber(b), 25)

    def test_kichik_summa_ball_bermaydi(self):
        b = self._buyurtma(500)                         # < 1000
        self.assertEqual(SodiqlikService.ball_ber(b), 0)
        self.profil.refresh_from_db()
        self.assertEqual(self.profil.sodiqlik_ball, 0)
        self.assertEqual(SodiqlikTarix.objects.count(), 0)

    def test_profil_yoq_bolsa_xato_bermaydi(self):
        # Profilsiz mijoz — ball_ber yiqilmasligi, 0 qaytarishi kerak
        self.profil.delete()
        b = self._buyurtma(50000)
        self.assertEqual(SodiqlikService.ball_ber(b), 0)
        self.assertEqual(SodiqlikTarix.objects.count(), 0)

    def test_bir_necha_buyurtma_yigiladi(self):
        SodiqlikService.ball_ber(self._buyurtma(10000))   # +10
        SodiqlikService.ball_ber(self._buyurtma(3000))    # +3
        self.profil.refresh_from_db()
        self.assertEqual(self.profil.sodiqlik_ball, 13)
        self.assertEqual(SodiqlikTarix.objects.count(), 2)


class SodiqlikIdempotentlikTest(SodiqlikBazasi):
    """Buyurtma 'olib_ketildi' (yakuniy) holatga yetgach, oldinga siljish
    yo'q — demak ball ikkinchi marta berilmaydi. State-machine kafolati."""

    def test_yakuniy_holatda_keyingi_yoq(self):
        b = self._buyurtma(20000, holat='olib_ketildi')
        # Yakuniy holatdan keyingi holat bo'lmasligi kerak (qayta award trigger yo'q)
        self.assertIsNone(b.keyingi_holat())

    def test_ball_qiymati_konstantasi(self):
        # Hujjatlangan qoida buzilmasin: 1 ball = 1000 so'm xarid
        self.assertEqual(BALL_TOPISH_NARXI, 1000)


class OlibKetishChekTest(TestCase):
    """Onlayn buyurtma 'olib_ketildi' bo'lganda: savdo cheki + kassa daromadi
    yoziladi, ombor QAYTA kamaymaydi (rezerv allaqachon kamaytirgan)."""

    def setUp(self):
        from mahsulot.models import Mahsulot
        self.egasi = CustomUser.objects.create_user(
            username='e2', password='parol12345', rol='dokon_egasi')
        self.dokon = DokonEgasiProfil.objects.create(
            foydalanuvchi=self.egasi, dokon_nomi='D2')
        self.mijoz = CustomUser.objects.create_user(
            username='m2', password='parol12345', rol='mijoz')
        MijozProfil.objects.create(foydalanuvchi=self.mijoz)
        self.m = Mahsulot.objects.create(
            nomi='Choy', dokon=self.dokon, narx=Decimal('5000'), soni=10)

    def test_olib_ketilganda_chek_kassa_va_ombor(self):
        from buyurtma.services import OrderService
        from kassa.models import SavdoChek, Kassa

        b = OrderService.create(self.mijoz, self.dokon, [(self.m, Decimal('2'))])
        self.m.refresh_from_db()
        self.assertEqual(self.m.soni, Decimal('8'))          # rezerv: 10-2

        # yangi -> tayyorlanmoqda -> tayyor -> olib_ketildi
        for _ in range(3):
            OrderService.advance_status(b, self.egasi)
        b.refresh_from_db()
        self.assertEqual(b.holat, 'olib_ketildi')

        # Savdo cheki yaratildi, kassa oshdi
        self.assertEqual(SavdoChek.objects.filter(dokon=self.dokon).count(), 1)
        chek = SavdoChek.objects.get(dokon=self.dokon)
        self.assertEqual(chek.jami, Decimal('10000'))        # 2 * 5000
        self.assertEqual(Kassa.objects.get(dokon=self.dokon).balans, Decimal('10000'))

        # Ombor QAYTA kamaymadi (hali 8 — ikki marta emas)
        self.m.refresh_from_db()
        self.assertEqual(self.m.soni, Decimal('8'))

    def test_bekor_qilinganda_ombor_qaytadi(self):
        from buyurtma.services import OrderService
        b = OrderService.create(self.mijoz, self.dokon, [(self.m, Decimal('3'))])
        self.m.refresh_from_db()
        self.assertEqual(self.m.soni, Decimal('7'))          # rezerv: 10-3
        OrderService.cancel(b, self.egasi)
        self.m.refresh_from_db()
        self.assertEqual(self.m.soni, Decimal('10'))         # qaytdi
