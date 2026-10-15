# -*- coding: utf-8 -*-
"""Xavfsizlik tuzatishlari uchun regressiya testlari (audit 2026-10-16).

    python manage.py test users.tests_xavfsizlik
"""
from decimal import Decimal

from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from kassa.hisobot_service import dokon_aniqla
from kassa.models import SavdoChek, SavdoChekMahsulot, Qaytarish
from kassa.savdo_service import qaytarish_yarat, SavdoXato
from mahsulot.models import Mahsulot
from users.models import CustomUser, DokonEgasiProfil, SotuvchiProfil, TelegramLink
from users.services import foydalanuvchi_dokoni

KUCHLI_PAROL = 'Savdo#Kuchli2026'


class Asos(TestCase):
    def setUp(self):
        cache.clear()
        self.egasi = CustomUser.objects.create_user(
            username='egasi', password=KUCHLI_PAROL, rol='dokon_egasi',
            email='egasi@example.com', tasdiqlangan=True)
        self.dokon = DokonEgasiProfil.objects.create(foydalanuvchi=self.egasi, dokon_nomi='Test')

    def _sotuvchi(self, holat):
        u = CustomUser.objects.create_user(
            username=f'sot_{holat}', password=KUCHLI_PAROL, rol='sotuvchi',
            tasdiqlangan=(holat == 'tasdiqlangan'))
        SotuvchiProfil.objects.create(foydalanuvchi=u, dokon=self.dokon, sorov_holati=holat)
        return u


class DokonKirishTest(Asos):
    """C1/C2: faqat tasdiqlangan sotuvchi do'kon ma'lumotini ko'radi."""

    def test_tasdiqlanmagan_sotuvchi_dokon_olmaydi(self):
        for holat in ('kutilmoqda', 'rad_etilgan'):
            u = self._sotuvchi(holat)
            self.assertIsNone(foydalanuvchi_dokoni(u))
            self.assertIsNone(dokon_aniqla(u))   # Telegram bot ham shu orqali

    def test_tasdiqlangan_sotuvchi_dokon_oladi(self):
        u = self._sotuvchi('tasdiqlangan')
        self.assertEqual(foydalanuvchi_dokoni(u), self.dokon)

    def test_rad_etilganda_sessiya_va_telegram_bekor(self):
        u = self._sotuvchi('tasdiqlangan')
        TelegramLink.objects.create(foydalanuvchi=u, chat_id=12345)
        c = self.client_class()
        c.force_login(u)
        self.assertEqual(c.get(reverse('qarz_royxat')).status_code, 200)

        self.client.force_login(self.egasi)
        sp = SotuvchiProfil.objects.get(foydalanuvchi=u)
        self.client.post(reverse('sotuvchi_ruxsat'), {'sotuvchi_id': sp.id, 'harakat': 'rad'})

        self.assertFalse(TelegramLink.objects.filter(foydalanuvchi=u).exists())
        r = c.get(reverse('qarz_royxat'))
        self.assertNotEqual(r.status_code, 200)   # sessiya o'chirilgan -> login'ga

    def test_kassir_hisobot_va_ai_ololmaydi(self):
        u = self._sotuvchi('tasdiqlangan')
        self.client.force_login(u)
        self.assertEqual(self.client.get(reverse('hisobot')).status_code, 302)
        r = self.client.post(reverse('ai_tahlil'))
        self.assertEqual(r.status_code, 403)


@override_settings(DEBUG=False, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ParolTiklashTest(Asos):
    """C3/M6: kod ekranda chiqmaydi, urinishlar cheklangan, email oshkor bo'lmaydi."""

    def _kod_yubor(self, email='egasi@example.com'):
        return self.client.post(reverse('forgot_password'), {'action': 'send_code', 'email': email})

    def test_kod_ekranda_korsatilmaydi(self):
        r = self._kod_yubor()
        self.assertEqual(len(mail.outbox), 1)
        kod = [t for t in mail.outbox[0].body.split() if t.isdigit() and len(t) == 6][0]
        self.assertNotIn(kod, r.content.decode())

    def test_notogri_email_oshkor_qilinmaydi(self):
        r1 = self._kod_yubor('yoq@example.com').content.decode()
        self.assertNotIn('topilmadi', r1)
        self.assertEqual(len(mail.outbox), 0)

    def test_5_xatodan_keyin_kod_bekor(self):
        self._kod_yubor()
        kod = [t for t in mail.outbox[0].body.split() if t.isdigit() and len(t) == 6][0]
        notogri = '000000' if kod != '000000' else '111111'
        for _ in range(5):
            self.client.post(reverse('forgot_password'),
                             {'action': 'reset', 'code': notogri, 'new_password': 'Yangi#Parol2026'})
        # To'g'ri kod ham endi ishlamaydi
        self.client.post(reverse('forgot_password'),
                         {'action': 'reset', 'code': kod, 'new_password': 'Yangi#Parol2026'})
        self.egasi.refresh_from_db()
        self.assertTrue(self.egasi.check_password(KUCHLI_PAROL))

    def test_togri_kod_parolni_ozgartiradi(self):
        self._kod_yubor()
        kod = [t for t in mail.outbox[0].body.split() if t.isdigit() and len(t) == 6][0]
        self.client.post(reverse('forgot_password'),
                         {'action': 'reset', 'code': kod, 'new_password': 'Yangi#Parol2026'})
        self.egasi.refresh_from_db()
        self.assertTrue(self.egasi.check_password('Yangi#Parol2026'))


class FaylYuklashTest(Asos):
    """H2: rasm bo'lmagan fayl saqlanmaydi; media faqat rasmlarni beradi."""

    def test_html_fayl_rasm_sifatida_saqlanmaydi(self):
        m = Mahsulot(nomi='X', dokon=self.dokon, narx=1, soni=1)
        m.rasm = SimpleUploadedFile('evil.html', b'<script>alert(1)</script>', content_type='text/html')
        m.save()
        m.refresh_from_db()
        self.assertFalse(m.rasm)

    def test_media_html_berilmaydi(self):
        self.assertEqual(self.client.get('/media/mahsulotlar/evil.html').status_code, 404)
        self.assertEqual(self.client.get('/media/zavod_hujjatlar/a.pdf').status_code, 404)


class QaytarishTest(Asos):
    """M1: qaytarish soni sotilgandan oshmaydi (qayta tekshiruv qulf ostida)."""

    def test_ortiqcha_qaytarish_mumkin_emas(self):
        m = Mahsulot.objects.create(nomi='Non', dokon=self.dokon, narx=Decimal('5000'), soni=10)
        chek = SavdoChek.objects.create(dokon=self.dokon, sotuvchi=self.egasi, jami=Decimal('10000'),
                                        to_langan=Decimal('10000'), tolash_turi='naqd')
        cm = SavdoChekMahsulot.objects.create(chek=chek, mahsulot=m, mahsulot_nomi='Non',
                                              soni=2, narx=Decimal('5000'), jami=Decimal('10000'))
        qaytarish_yarat(self.dokon, self.egasi, chek, [{'cm_id': cm.id, 'soni': 2}])
        with self.assertRaises(SavdoXato):
            qaytarish_yarat(self.dokon, self.egasi, chek, [{'cm_id': cm.id, 'soni': 1}])
        self.assertEqual(Qaytarish.objects.filter(chek=chek).count(), 1)


class OnlaynBuyurtmaTest(Asos):
    """H6: mijoz bo'lmagan foydalanuvchi ombordagi tovarni band qila olmaydi."""

    def test_mijoz_emas_buyurtma_bera_olmaydi(self):
        from buyurtma.services import OrderService
        from users.services import ServiceError
        m = Mahsulot.objects.create(nomi='Non', dokon=self.dokon, narx=Decimal('5000'), soni=10)
        boshqa = self._sotuvchi('kutilmoqda')
        with self.assertRaises(ServiceError):
            OrderService.create(boshqa, self.dokon, [(m, Decimal('10'))])
        m.refresh_from_db()
        self.assertEqual(m.soni, Decimal('10'))
