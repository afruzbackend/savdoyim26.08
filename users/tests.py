# -*- coding: utf-8 -*-
"""Ro'yxatdan o'tish va rol komfortlari uchun testlar.

Qamrab olinadi:
  • ism/username formatini tekshirish (faqat harf / Instagram uslubi);
  • live endpointlar: check_username (band/bo'sh), check_dokon (do'kon nomi);
  • sotuvchi tasdiqlanganda unga bildirishnoma yaratilishi.

Ishga tushirish:
    python manage.py test users
"""
import json

from django.test import TestCase
from django.urls import reverse

from .models import (
    CustomUser, DokonEgasiProfil, SotuvchiProfil, Bildirishnoma,
)
from .views import ism_xatosi, username_xatosi


class FormatTest(TestCase):
    """Server tomonidagi ism/username tekshiruvi (client'ga ishonmaslik)."""

    def test_ism_faqat_harf(self):
        self.assertIsNone(ism_xatosi("Ali Valiyev"))
        self.assertIsNone(ism_xatosi("O'ktam"))
        self.assertIsNotNone(ism_xatosi("Ali123"))
        self.assertIsNotNone(ism_xatosi("Ali_"))
        self.assertIsNotNone(ism_xatosi(""))

    def test_username_instagram_uslubi(self):
        self.assertIsNone(username_xatosi("ali.valiyev99"))
        self.assertIsNone(username_xatosi("ali_v"))
        self.assertIsNotNone(username_xatosi("ab"))          # qisqa
        self.assertIsNotNone(username_xatosi("ali..v"))      # ikki nuqta
        self.assertIsNotNone(username_xatosi(".ali"))        # nuqta bilan boshlanadi
        self.assertIsNotNone(username_xatosi("Ali!"))        # taqiqlangan belgi


class CheckUsernameTest(TestCase):
    def setUp(self):
        CustomUser.objects.create_user(username='bandusername', password='p', rol='mijoz')

    def _post(self, username):
        return self.client.post(
            reverse('check_username'),
            data=json.dumps({'username': username}),
            content_type='application/json',
        ).json()

    def test_bosh_username_available(self):
        d = self._post('yangi.user')
        self.assertTrue(d['available'])

    def test_band_username(self):
        d = self._post('bandusername')
        self.assertFalse(d['available'])

    def test_notogri_format(self):
        d = self._post('ab')
        self.assertFalse(d['available'])


class CheckDokonTest(TestCase):
    def setUp(self):
        eg = CustomUser.objects.create_user(username='salomat_egasi', password='p', rol='dokon_egasi')
        DokonEgasiProfil.objects.create(foydalanuvchi=eg, dokon_nomi='Salomat Market')

    def _post(self, username):
        return self.client.post(
            reverse('check_dokon'),
            data=json.dumps({'username': username}),
            content_type='application/json',
        ).json()

    def test_dokon_topildi_nom_qaytadi(self):
        d = self._post('salomat_egasi')
        self.assertTrue(d['ok'])
        self.assertEqual(d['dokon_nomi'], 'Salomat Market')

    def test_dokon_topilmadi(self):
        d = self._post('yoq_egasi')
        self.assertFalse(d['ok'])


class SotuvchiTasdiqBildirishnomaTest(TestCase):
    """Egasi sotuvchini tasdiqlaganda sotuvchiga bildirishnoma kelishi shart."""

    def setUp(self):
        self.egasi = CustomUser.objects.create_user(username='eg', password='p', rol='dokon_egasi')
        self.dokon = DokonEgasiProfil.objects.create(foydalanuvchi=self.egasi, dokon_nomi='Salomat Market')
        self.sotuvchi = CustomUser.objects.create_user(
            username='so', password='p', rol='sotuvchi', email='so@test.uz', tasdiqlangan=False
        )
        self.sp = SotuvchiProfil.objects.create(
            foydalanuvchi=self.sotuvchi, dokon=self.dokon, sorov_holati='kutilmoqda'
        )

    def test_tasdiqlanganda_bildirishnoma_keladi(self):
        self.client.force_login(self.egasi)
        self.client.post(reverse('sotuvchi_ruxsat'),
                         {'sotuvchi_id': self.sp.id, 'harakat': 'tasdiqlash'})
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.sorov_holati, 'tasdiqlangan')
        b = Bildirishnoma.objects.filter(foydalanuvchi=self.sotuvchi).first()
        self.assertIsNotNone(b)
        self.assertIn('Salomat Market', b.matn)

    def test_rad_etilganda_ham_xabar(self):
        self.client.force_login(self.egasi)
        self.client.post(reverse('sotuvchi_ruxsat'),
                         {'sotuvchi_id': self.sp.id, 'harakat': 'rad'})
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.sorov_holati, 'rad_etilgan')
        self.assertTrue(Bildirishnoma.objects.filter(foydalanuvchi=self.sotuvchi).exists())
