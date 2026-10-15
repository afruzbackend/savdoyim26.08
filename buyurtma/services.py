"""Buyurtma biznes logikasi (state machine). View'lar faqat shu servisni chaqiradi."""
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import MijozBuyurtma, MijozBuyurtmaItem, BuyurtmaStatusTarix, Savat
from users.services import ServiceError, AuditService, NotificationService


def sotuvchi_dokoni(user):
    """Sotuvchi/do'kon egasining do'koni (aks holda None) — yagona manba."""
    from users.services import foydalanuvchi_dokoni
    return foydalanuvchi_dokoni(user)


FAOL_HOLATLAR = ('yangi', 'tayyorlanmoqda', 'tayyor')
MAX_FAOL_BUYURTMA = 5      # bir mijozda bir vaqtda yakunlanmagan buyurtmalar
MAX_BIR_MAHSULOT = 50      # bitta mahsulotdan bir buyurtmada
REZERV_SOAT = 24           # shuncha soatda olib ketilmasa — avtomatik bekor, ombor qaytadi


class OrderService:
    """Buyurtma yaratish va status o'tkazish — barcha qoidalar shu yerda."""

    @staticmethod
    @transaction.atomic
    def create(mijoz, dokon, itemlar, request=None):
        """itemlar: [(mahsulot, soni), ...] — bitta do'konga tegishli.

        Buyurtma yaratilganda ombor ATOMIK kamaytiriladi (rezerv qilinadi) —
        shu tovar boshqa mijozga yoki kassada qayta sotilmaydi (oversell yo'q).
        Buyurtma bekor qilinsa (OrderService.cancel) ombor qaytariladi."""
        if not itemlar:
            raise ServiceError("Buyurtma bo'sh.", 400)
        if getattr(mijoz, 'rol', None) != 'mijoz':
            raise ServiceError("Onlayn buyurtmani faqat mijoz bera oladi.", 403)
        from mahsulot.models import Mahsulot
        from django.db.models import F
        # Muddati o'tgan (olib ketilmagan) buyurtmalar rezervini bo'shatamiz
        OrderService.eskilarni_bekor_qil(dokon)
        faol = MijozBuyurtma.objects.filter(mijoz=mijoz, holat__in=FAOL_HOLATLAR).count()
        if faol >= MAX_FAOL_BUYURTMA:
            raise ServiceError(
                f"Sizda {faol} ta yakunlanmagan buyurtma bor. Avval ularni olib keting yoki bekor qiling.", 429)
        for mahsulot, soni in itemlar:
            if soni <= 0:
                raise ServiceError(f"{mahsulot.nomi}: son noto'g'ri.", 400)
            if soni > MAX_BIR_MAHSULOT:
                raise ServiceError(f"{mahsulot.nomi}: bitta buyurtmada ko'pi bilan {MAX_BIR_MAHSULOT} ta.", 400)
        buyurtma = MijozBuyurtma.objects.create(mijoz=mijoz, dokon=dokon, holat='yangi')
        for mahsulot, soni in itemlar:
            # Faqat omborda yetarli bo'lsagina kamayadi (poyga/race himoyasi).
            # Yetmasa — butun tranzaksiya (buyurtma + oldingi kamayishlar) bekor bo'ladi.
            kamaydi = (Mahsulot.objects
                       .filter(id=mahsulot.id, soni__gte=soni)
                       .update(soni=F('soni') - soni))
            if not kamaydi:
                qoldiq = (Mahsulot.objects.filter(id=mahsulot.id)
                          .values_list('soni', flat=True).first() or 0)
                raise ServiceError(
                    f"{mahsulot.nomi}: omborda faqat {qoldiq} {mahsulot.birlik} bor.", 409)
            MijozBuyurtmaItem.objects.create(
                buyurtma=buyurtma, mahsulot=mahsulot, mahsulot_nomi=mahsulot.nomi,
                soni=soni, narx=mahsulot.narx,
            )
        buyurtma.jami_hisobla()
        BuyurtmaStatusTarix.objects.create(buyurtma=buyurtma, holat='yangi')
        NotificationService.send_order_created(buyurtma)
        AuditService.log(mijoz, 'order_created', buyurtma, str(dokon), request)
        return buyurtma

    @staticmethod
    @transaction.atomic
    def cancel(buyurtma, user, request=None):
        """Buyurtmani bekor qiladi va rezervlangan omborni qaytaradi.
        Ruxsat: buyurtma egasi (mijoz) yoki do'kon xodimi. Yakuniy holatda mumkin emas."""
        egasimi = (buyurtma.mijoz_id == getattr(user, 'id', None))
        dokon = sotuvchi_dokoni(user)
        if not (egasimi or (dokon and dokon == buyurtma.dokon)):
            raise ServiceError("Ruxsat yo'q.", 403)
        OrderService._bekorga_otkaz(buyurtma)
        BuyurtmaStatusTarix.objects.create(buyurtma=buyurtma, holat='bekor')
        NotificationService.send_order_status(buyurtma, 'bekor')
        AuditService.log(user, 'order_status_changed', buyurtma, 'bekor', request)
        return buyurtma

    @staticmethod
    def _bekorga_otkaz(buyurtma):
        """Holatni ATOMIK (shartli UPDATE) 'bekor' ga o'tkazadi va rezervni qaytaradi.
        Ikki marta bir vaqtda bekor qilinsa ham ombor faqat BIR marta qaytadi."""
        from mahsulot.models import Mahsulot
        from django.db.models import F
        ozgardi = (MijozBuyurtma.objects
                   .filter(pk=buyurtma.pk, holat__in=FAOL_HOLATLAR)
                   .update(holat='bekor', yangilangan=timezone.now()))
        if not ozgardi:
            raise ServiceError("Bu buyurtmani bekor qilib bo'lmaydi.", 409)
        for it in buyurtma.itemlar.all():
            if it.mahsulot_id:
                Mahsulot.objects.filter(id=it.mahsulot_id).update(soni=F('soni') + it.soni)
        buyurtma.holat = 'bekor'

    @staticmethod
    def eskilarni_bekor_qil(dokon=None):
        """REZERV_SOAT dan ko'p olib ketilmagan buyurtmalarni bekor qilib, omborni bo'shatadi."""
        chegara = timezone.now() - timedelta(hours=REZERV_SOAT)
        qs = MijozBuyurtma.objects.filter(holat__in=FAOL_HOLATLAR, yaratilgan__lt=chegara)
        if dokon is not None:
            qs = qs.filter(dokon=dokon)
        soni = 0
        for b in qs[:200]:
            try:
                with transaction.atomic():
                    OrderService._bekorga_otkaz(b)
                    BuyurtmaStatusTarix.objects.create(buyurtma=b, holat='bekor')
                soni += 1
            except ServiceError:
                continue
        return soni

    @staticmethod
    @transaction.atomic
    def create_from_cart(mijoz, request=None):
        """Savatni do'kon bo'yicha guruhlab, har biriga alohida buyurtma yaratadi."""
        savat, _ = Savat.objects.get_or_create(mijoz=mijoz)
        itemlar = list(savat.itemlar.select_related('mahsulot', 'mahsulot__dokon'))
        if not itemlar:
            raise ServiceError("Savat bo'sh.", 400)
        groups = {}
        for it in itemlar:
            if not it.mahsulot or not it.mahsulot.dokon:
                continue
            key = it.mahsulot.dokon_id
            if key not in groups:
                groups[key] = (it.mahsulot.dokon, [])
            groups[key][1].append((it.mahsulot, it.soni))
        if not groups:
            raise ServiceError("Savatda do'konga bog'langan mahsulot yo'q.", 400)
        buyurtmalar = [OrderService.create(mijoz, dokon, items, request)
                       for dokon, items in groups.values()]
        savat.itemlar.all().delete()
        return buyurtmalar

    @staticmethod
    @transaction.atomic
    def advance_status(buyurtma, user, target=None, request=None):
        """Statusni FAQAT keyingi (oldingi) holatga o'tkazadi.
        Ruxsat + transition tekshiruvi + tarix + bildirishnoma + audit."""
        dokon = sotuvchi_dokoni(user)
        if not dokon or dokon != buyurtma.dokon:
            raise ServiceError("Ruxsat yo'q.", 403)
        keyingi = buyurtma.keyingi_holat()
        if keyingi is None:
            raise ServiceError("Buyurtma yakuniy holatda.", 409)
        if target is not None and target != keyingi:
            raise ServiceError("Statusni faqat ketma-ket oldinga o'tkazish mumkin.", 400)
        # Shartli UPDATE: ikki xodim bir vaqtda bossa ham holat (va chek/ball) bir marta o'zgaradi
        ozgardi = (MijozBuyurtma.objects
                   .filter(pk=buyurtma.pk, holat=buyurtma.holat)
                   .update(holat=keyingi, yangilangan=timezone.now()))
        if not ozgardi:
            raise ServiceError("Buyurtma holati allaqachon o'zgargan. Sahifani yangilang.", 409)
        buyurtma.holat = keyingi
        BuyurtmaStatusTarix.objects.create(buyurtma=buyurtma, holat=keyingi)
        NotificationService.send_order_status(buyurtma, keyingi)
        AuditService.log(user, 'order_status_changed', buyurtma, keyingi, request)

        # Buyurtma olib ketilganda:
        #  1) savdo cheki yaratiladi (daromad + kassa) — ombor rezervда kamaygan,
        #     shu yerda QAYTA kamaymaydi;
        #  2) sodiqlik ballari beriladi (1 ball / 1000 so'm).
        if keyingi == 'olib_ketildi':
            from kassa.savdo_service import chek_buyurtmadan
            chek_buyurtmadan(buyurtma, sotuvchi=user, tolash_turi='naqd')
            SodiqlikService.ball_ber(buyurtma)
        return buyurtma


# Sodiqlik ballari: 1 ball = 1000 so'm xarid; ishlatishda 1 ball = 100 so'm chegirma
BALL_TOPISH_NARXI = 1000
BALL_QIYMATI = 100


class SodiqlikService:
    """Mijoz sodiqlik ballari — topish/ishlatish."""

    @staticmethod
    def ball_ber(buyurtma):
        """Yakunlangan buyurtma uchun mijozga ball qo'shadi."""
        from .models import SodiqlikTarix
        from users.models import MijozProfil
        ball = int(buyurtma.jami // BALL_TOPISH_NARXI)
        if ball <= 0:
            return 0
        from django.db.models import F
        from django.db.models.functions import Coalesce
        ozgardi = (MijozProfil.objects.filter(foydalanuvchi=buyurtma.mijoz)
                   .update(sodiqlik_ball=Coalesce(F('sodiqlik_ball'), 0) + ball))
        if not ozgardi:
            return 0
        SodiqlikTarix.objects.create(
            mijoz=buyurtma.mijoz, buyurtma=buyurtma, ball=ball,
            sabab=f"Buyurtma {buyurtma.raqam} uchun",
        )
        return ball
