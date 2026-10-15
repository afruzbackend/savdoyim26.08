# -*- coding: utf-8 -*-
"""MVP funksiyalari: qisman qarz to'lash, IKPU, AJAX savat, USB skaner, smena verkasi.

    python manage.py test kassa.tests_mvp
"""
import json
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from mahsulot.models import Mahsulot
from users.models import CustomUser, DokonEgasiProfil
from .models import Kassa, QarzDaftar, QarzTolov, SavdoChek, SavdoChekMahsulot, Smena
from .savdo_service import qarz_tolash_yadro, qaytarish_yarat, smena_yop, SavdoXato


class Asos(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='egasi', password='x', rol='dokon_egasi')
        self.dokon = DokonEgasiProfil.objects.create(foydalanuvchi=self.user, dokon_nomi='Test')
        self.smena = Smena.objects.create(dokon=self.dokon, sotuvchi=self.user, holat='ochiq',
                                          boshlangich_naqd=Decimal('0'))
        self.m = Mahsulot.objects.create(nomi='Non', dokon=self.dokon, narx=Decimal('5000'), soni=10,
                                         barkod='4780000000011', ikpu='10202001001000000')
        self.client.force_login(self.user)

    def _qarz(self, summa='30000'):
        return QarzDaftar.objects.create(dokon=self.dokon, mijoz_ism='Ali', summa=Decimal(summa))

    def _kassa(self):
        return Kassa.objects.get(dokon=self.dokon).balans


class QismanQarzTest(Asos):

    def test_qisman_tolov_qolganni_kamaytiradi(self):
        q = self._qarz()
        qarz_tolash_yadro(self.dokon, q.id, summa='10000')
        q.refresh_from_db()
        self.assertEqual(q.summa, Decimal('20000'))
        self.assertEqual(q.tolangan_summa, Decimal('10000'))
        self.assertFalse(q.to_langan)
        self.assertEqual(q.jami_qarz, Decimal('30000'))
        self.assertEqual(self._kassa(), Decimal('10000'))

    def test_qolganini_tolash_yopadi(self):
        q = self._qarz()
        qarz_tolash_yadro(self.dokon, q.id, summa='10000')
        qarz_tolash_yadro(self.dokon, q.id)          # summa yo'q -> qolgan hammasi
        q.refresh_from_db()
        self.assertTrue(q.to_langan)
        self.assertEqual(q.summa, Decimal('0'))
        self.assertEqual(QarzTolov.objects.filter(qarz=q).count(), 2)
        self.assertEqual(self._kassa(), Decimal('30000'))

    def test_ortiqcha_tolov_rad_etiladi(self):
        q = self._qarz()
        with self.assertRaises(SavdoXato):
            qarz_tolash_yadro(self.dokon, q.id, summa='40000')
        with self.assertRaises(SavdoXato):
            qarz_tolash_yadro(self.dokon, q.id, summa='0')

    def test_web_endpoint_qisman(self):
        q = self._qarz()
        r = self.client.post(reverse('qarz_tolash', args=[q.id]),
                             data=json.dumps({'summa': '12 000', 'tolov_turi': 'karta'}),
                             content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['qolgan'], 18000.0)
        self.assertEqual(QarzTolov.objects.get(qarz=q).tolov_turi, 'karta')

    def test_verka_faqat_naqd_tolovlarni_hisoblaydi(self):
        q = self._qarz()
        qarz_tolash_yadro(self.dokon, q.id, summa='10000', tolov_turi='naqd')
        qarz_tolash_yadro(self.dokon, q.id, summa='5000', tolov_turi='karta')
        smena, _ = smena_yop(self.dokon, real_naqd=Decimal('10000'))
        self.assertEqual(smena.kutilgan_naqd, Decimal('10000'))
        self.assertEqual(smena.naqd_farq, Decimal('0'))

    def test_qisman_tolangan_qarzni_qaytarish(self):
        # Qarzga 3 ta non (15 000), 10 000 to'langan, keyin 3 tasi qaytarildi:
        # 5 000 qarzdan ayiriladi, 10 000 kassadan qaytariladi.
        chek = SavdoChek.objects.create(dokon=self.dokon, sotuvchi=self.user, jami=Decimal('15000'),
                                        to_langan=0, tolash_turi='qarz')
        cm = SavdoChekMahsulot.objects.create(chek=chek, mahsulot=self.m, mahsulot_nomi='Non',
                                              soni=3, narx=Decimal('5000'), jami=Decimal('15000'))
        q = QarzDaftar.objects.create(dokon=self.dokon, mijoz_ism='Ali', summa=Decimal('15000'), chek=chek)
        qarz_tolash_yadro(self.dokon, q.id, summa='10000')
        qaytarish_yarat(self.dokon, self.user, chek, [{'cm_id': cm.id, 'soni': 3}])
        q.refresh_from_db()
        self.assertTrue(q.to_langan)
        self.assertEqual(q.summa, Decimal('0'))
        self.assertEqual(self._kassa(), Decimal('0'))   # +10 000 to'lov, -10 000 qaytarish


class IkpuTest(Asos):

    def test_sotuvda_ikpu_chekka_yoziladi(self):
        r = self.client.post(reverse('savdo_qilish'),
                             data=json.dumps({'mahsulotlar': [{'id': self.m.id, 'soni': 1}],
                                              'tolash_turi': 'naqd'}),
                             content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(SavdoChekMahsulot.objects.get().ikpu, '10202001001000000')
        chek = SavdoChek.objects.get()
        sahifa = self.client.get(reverse('chek_korish', args=[chek.token])).content.decode()
        self.assertIn('IKPU: 10202001001000000', sahifa)
        self.assertIn('FISKAL CHEK EMAS', sahifa)

    def test_notogri_ikpu_tahrirda_rad_etiladi(self):
        self.client.post(reverse('mahsulot_tahrir', args=[self.m.id]),
                         {'nomi': 'Non', 'narx': '5000', 'ikpu': '123', 'birlik': 'dona'})
        self.m.refresh_from_db()
        self.assertEqual(self.m.ikpu, '10202001001000000')


class AjaxSavatTest(Asos):
    H = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

    def test_add_json_qaytaradi(self):
        r = self.client.post(reverse('kassa_savat'), {'action': 'add', 'product_id': self.m.id}, **self.H)
        d = r.json()
        self.assertEqual(d['count'], 1)
        self.assertEqual(d['total'], 5000.0)
        r = self.client.post(reverse('kassa_savat'), {'action': 'set', 'product_id': self.m.id, 'soni': '4'}, **self.H)
        self.assertEqual(r.json()['items'][0]['qty'], '4')

    def test_ombordan_ortiq_ogohlantirish(self):
        r = self.client.post(reverse('kassa_savat'), {'action': 'set', 'product_id': self.m.id, 'soni': '99'}, **self.H)
        d = r.json()
        self.assertEqual(d['items'][0]['qty'], '10')
        self.assertTrue(d['xabarlar'])

    def test_formasiz_eski_yol_ishlaydi(self):
        r = self.client.post(reverse('kassa_savat'), {'action': 'add', 'product_id': self.m.id})
        self.assertEqual(r.status_code, 302)

    def test_skaner_savatni_qaytaradi(self):
        r = self.client.post(reverse('kassa_skan'), data=json.dumps({'barkod': '4780000000011'}),
                             content_type='application/json')
        d = r.json()
        self.assertTrue(d['qoshildi'])
        self.assertEqual(d['cart']['count'], 1)
