# -*- coding: utf-8 -*-
"""REST API poydevori uchun testlar.

Tekshiriladi:
  • token login (to'g'ri / noto'g'ri parol / bo'sh maydon);
  • himoya — token'siz kirish rad etiladi;
  • DO'KON IZOLYATSIYASI — foydalanuvchi FAQAT o'z do'koni mahsulotini ko'radi;
  • mahsulot qidiruv (?q=) va kassa balansi.

Ishga tushirish:
    python manage.py test api
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token

from users.models import CustomUser, DokonEgasiProfil
from mahsulot.models import Mahsulot
from kassa.models import Kassa


class ApiBazasi(TestCase):
    def setUp(self):
        # 1-do'kon egasi + mahsuloti
        self.u1 = CustomUser.objects.create_user(
            username='egasi1', password='parol12345', rol='dokon_egasi'
        )
        self.d1 = DokonEgasiProfil.objects.create(
            foydalanuvchi=self.u1, dokon_nomi='Do\'kon 1'
        )
        self.m1 = Mahsulot.objects.create(
            nomi='Non', dokon=self.d1, barkod='111',
            narx=Decimal('5000'), soni=10,
        )
        # 2-do'kon egasi + mahsuloti (izolyatsiya tekshiruvi uchun)
        self.u2 = CustomUser.objects.create_user(
            username='egasi2', password='parol12345', rol='dokon_egasi'
        )
        self.d2 = DokonEgasiProfil.objects.create(
            foydalanuvchi=self.u2, dokon_nomi='Do\'kon 2'
        )
        self.m2 = Mahsulot.objects.create(
            nomi='Sut', dokon=self.d2, barkod='222',
            narx=Decimal('12000'), soni=5,
        )

    def _auth(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}


class LoginTest(ApiBazasi):

    def test_togri_login_token_beradi(self):
        resp = self.client.post(
            reverse('api-login'),
            data={'username': 'egasi1', 'password': 'parol12345'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('token', resp.json())
        self.assertEqual(resp.json()['user']['username'], 'egasi1')
        self.assertEqual(resp.json()['user']['dokon_nomi'], "Do'kon 1")

    def test_notogri_parol_401(self):
        resp = self.client.post(
            reverse('api-login'),
            data={'username': 'egasi1', 'password': 'xato'},
        )
        self.assertEqual(resp.status_code, 401)

    def test_bosh_maydon_400(self):
        resp = self.client.post(reverse('api-login'), data={'username': 'egasi1'})
        self.assertEqual(resp.status_code, 400)


class HimoyaTest(ApiBazasi):

    def test_tokensiz_401(self):
        resp = self.client.get(reverse('api-me'))
        self.assertEqual(resp.status_code, 401)

    def test_token_bilan_me_ishlaydi(self):
        resp = self.client.get(reverse('api-me'), **self._auth(self.u1))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['username'], 'egasi1')


class DokonIzolyatsiyaTest(ApiBazasi):
    """Eng muhim xavfsizlik tekshiruvi — begona do'kon ma'lumoti ko'rinmasligi."""

    def test_faqat_oz_mahsulotini_koradi(self):
        resp = self.client.get(reverse('api-mahsulot-list'), **self._auth(self.u1))
        self.assertEqual(resp.status_code, 200)
        nomlar = [m['nomi'] for m in resp.json()]
        self.assertIn('Non', nomlar)         # o'ziniki
        self.assertNotIn('Sut', nomlar)      # BEGONA do'kon — ko'rinmasligi shart

    def test_qidiruv_ishlaydi(self):
        Mahsulot.objects.create(nomi='Guruch', dokon=self.d1, barkod='333',
                                narx=Decimal('9000'), soni=3)
        resp = self.client.get(
            reverse('api-mahsulot-list') + '?q=guru', **self._auth(self.u1)
        )
        nomlar = [m['nomi'] for m in resp.json()]
        self.assertEqual(nomlar, ['Guruch'])

    def test_kassa_balansi(self):
        Kassa.objects.create(dokon=self.d1, balans=Decimal('45000'))
        resp = self.client.get(reverse('api-kassa'), **self._auth(self.u1))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Decimal(resp.json()['balans']), Decimal('45000'))
