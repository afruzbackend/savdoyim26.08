from decimal import Decimal
from datetime import timedelta
from django.db import models
from users.models import DokonEgasiProfil, ZavodProfil, YetkazibBeruvchiProfil, CustomUser
from users.soft_delete import SoftDeleteModel
from mahsulot.models import Mahsulot


class Buyurtma(models.Model):
    HOLAT = [
        ('yangi', 'Yangi'),
        ('qabul_qilindi', 'Qabul Qilindi'),
        ('tayyorlanmoqda', 'Tayyorlanmoqda'),
        ('yolda', "Yo'lda"),
        ('yetkazildi', 'Yetkazildi'),
        ('bekor', 'Bekor Qilindi'),
    ]
    dokon = models.ForeignKey(
        DokonEgasiProfil, on_delete=models.CASCADE, related_name='buyurtmalar'
    )
    zavod = models.ForeignKey(
        ZavodProfil, on_delete=models.CASCADE,
        related_name='buyurtmalar', null=True, blank=True
    )
    holat = models.CharField(max_length=20, choices=HOLAT, default='yangi')
    izoh = models.TextField(blank=True)
    jami = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    yaratilgan = models.DateTimeField(auto_now_add=True)
    yangilangan = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Buyurtma #{self.id}"

    class Meta:
        verbose_name = 'Buyurtma'


class BuyurtmaMahsulot(models.Model):
    buyurtma = models.ForeignKey(
        Buyurtma, on_delete=models.CASCADE, related_name='mahsulotlar'
    )
    mahsulot = models.ForeignKey(
        Mahsulot, on_delete=models.SET_NULL, null=True, blank=True
    )
    mahsulot_nomi = models.CharField(max_length=200)
    soni = models.IntegerField()
    narx = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.mahsulot_nomi} x{self.soni}"

    class Meta:
        verbose_name = 'Buyurtma Mahsulot'


class YetkazishBuyurtma(models.Model):
    HOLAT = [
        ('yangi', 'Yangi'),
        ('olinmoqda', 'Olinmoqda'),
        ('yolda', "Yo'lda"),
        ('yetkazildi', 'Yetkazildi'),
    ]
    buyurtma = models.OneToOneField(
        Buyurtma, on_delete=models.CASCADE, related_name='yetkazish'
    )
    yetkazuvchi = models.ForeignKey(
        YetkazibBeruvchiProfil, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='buyurtmalar'
    )
    holat = models.CharField(max_length=20, choices=HOLAT, default='yangi')
    yaratilgan = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Yetkazish #{self.id}"

    class Meta:
        verbose_name = 'Yetkazish Buyurtma'


class MijozBuyurtma(SoftDeleteModel):
    """Mijozning bitta do'konga bergan buyurtmasi (bir nechta mahsulot bo'lishi mumkin).
    Savatda turli do'kon mahsulotlari bo'lsa, checkout paytida har do'kon uchun
    alohida buyurtma yaratiladi. Holatlar faqat OLDINGA siljiydi.
    'topshirish_turi' orqali kelajakda Delivery / Courier qo'shish oson.
    """
    HOLAT = [
        ('yangi', 'Yangi buyurtma'),
        ('tayyorlanmoqda', 'Tayyorlanmoqda'),
        ('tayyor', 'Tayyor'),
        ('olib_ketildi', 'Olib ketildi'),
        ('bekor', 'Bekor qilindi'),
    ]
    # Oldinga siljish oqimi (bekor — alohida yakuniy holat)
    OQIM = ['yangi', 'tayyorlanmoqda', 'tayyor', 'olib_ketildi']

    TOPSHIRISH = [
        ('olib_ketish', 'Olib ketish (Click & Collect)'),
        ('yetkazish', 'Yetkazib berish'),   # kelajak: delivery/courier
    ]

    mijoz = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='mijoz_buyurtmalar'
    )
    dokon = models.ForeignKey(
        DokonEgasiProfil, on_delete=models.CASCADE, related_name='mijoz_buyurtmalar'
    )
    holat = models.CharField(max_length=20, choices=HOLAT, default='yangi', db_index=True)
    topshirish_turi = models.CharField(max_length=20, choices=TOPSHIRISH, default='olib_ketish')
    jami = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    izoh = models.TextField(blank=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)
    yangilangan = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-yaratilgan']
        verbose_name = 'Mijoz buyurtma'
        verbose_name_plural = 'Mijoz buyurtmalari'
        indexes = [
            models.Index(fields=['dokon', 'holat']),
            models.Index(fields=['mijoz', '-yaratilgan']),
        ]

    def __str__(self):
        return f"Buyurtma {self.raqam}"

    @property
    def raqam(self):
        return f"#{self.id:05d}"

    def keyingi_holat(self):
        """Keyingi (oldinga) holatni qaytaradi yoki None."""
        if self.holat not in self.OQIM:
            return None
        i = self.OQIM.index(self.holat)
        return self.OQIM[i + 1] if i + 1 < len(self.OQIM) else None

    def oldinga_siljitish_mumkinmi(self, yangi_holat):
        """Faqat aynan keyingi holatga o'tishga ruxsat (orqaga yoki sakrash yo'q)."""
        return yangi_holat == self.keyingi_holat()

    def keyingi_holat_nomi(self):
        k = self.keyingi_holat()
        return dict(self.HOLAT).get(k) if k else None

    @property
    def baholash_ochiqmi(self):
        return self.holat == 'olib_ketildi'

    def jami_hisobla(self, saqla=True):
        total = sum((it.jami for it in self.itemlar.all()), Decimal('0'))
        self.jami = total
        if saqla:
            self.save(update_fields=['jami'])
        return total

    # ── Tayyorlanish vaqti bashorati (mahsulot soniga qarab) ──
    @property
    def tur_soni(self):
        """Buyurtmadagi xil mahsulotlar soni."""
        return len(self.itemlar.all())

    @property
    def item_soni(self):
        """Jami dona (barcha mahsulot birliklari yig'indisi)."""
        return sum(it.soni for it in self.itemlar.all())

    @property
    def tayyorlanish_daqiqa(self):
        """Sotuvchi buyurtmani yig'ib bo'lishi uchun taxminiy vaqt (daqiqa).
        Baza 3 daqiqa + har xil mahsulot 2 daqiqa + har dona 1 daqiqa,
        5 daqiqaga yaxlitlanadi, 5–90 oralig'ida."""
        daqiqa = 3 + self.tur_soni * 2 + self.item_soni * 1
        daqiqa = min(max(daqiqa, 5), 90)
        return int(round(daqiqa / 5.0) * 5)

    @property
    def taxminiy_tayyor_vaqt(self):
        """Buyurtma taxminan qachon tayyor bo'ladi (yaratilgan + tayyorlanish)."""
        return self.yaratilgan + timedelta(minutes=self.tayyorlanish_daqiqa)

    def oqim_bosqichlari(self):
        """Progress stepper uchun bosqichlar ro'yxati.
        Har biri: {holat, nom, done (bajarilgan), current (joriy)}."""
        if self.holat == 'bekor':
            return []
        joriy_i = self.OQIM.index(self.holat) if self.holat in self.OQIM else -1
        nomlar = dict(self.HOLAT)
        return [{
            'holat': h,
            'nom': nomlar.get(h),
            'done': i < joriy_i,
            'current': i == joriy_i,
        } for i, h in enumerate(self.OQIM)]


class MijozBuyurtmaItem(models.Model):
    """Buyurtmadagi bitta mahsulot qatori."""
    buyurtma = models.ForeignKey(
        MijozBuyurtma, on_delete=models.CASCADE, related_name='itemlar'
    )
    mahsulot = models.ForeignKey(
        Mahsulot, on_delete=models.SET_NULL, null=True, related_name='buyurtma_itemlari'
    )
    mahsulot_nomi = models.CharField(max_length=200)
    soni = models.PositiveIntegerField(default=1)
    narx = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.mahsulot_nomi} x{self.soni}"

    @property
    def jami(self):
        return self.narx * self.soni


class BuyurtmaStatusTarix(models.Model):
    """Har bir status o'zgarishi vaqti bilan saqlanadi (status tarixi)."""
    buyurtma = models.ForeignKey(
        MijozBuyurtma, on_delete=models.CASCADE, related_name='tarix'
    )
    holat = models.CharField(max_length=20, choices=MijozBuyurtma.HOLAT)
    vaqt = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['vaqt']
        verbose_name = 'Buyurtma status tarixi'

    def __str__(self):
        return f"{self.buyurtma_id} · {self.holat}"


class SodiqlikTarix(models.Model):
    """Mijozning sodiqlik ball harakatlari tarixi (topilgan / ishlatilgan)."""
    mijoz = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='sodiqlik_tarix'
    )
    buyurtma = models.ForeignKey(
        MijozBuyurtma, on_delete=models.SET_NULL, null=True, blank=True
    )
    ball = models.IntegerField(help_text="Musbat = topildi, manfiy = ishlatildi")
    sabab = models.CharField(max_length=200)
    sana = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sana']
        verbose_name = 'Sodiqlik tarixi'

    def __str__(self):
        return f"{self.mijoz_id}: {self.ball:+d} ({self.sabab})"


class Savat(models.Model):
    """Mijozning savati (har mijoz uchun bitta)."""
    mijoz = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='savat'
    )
    yaratilgan = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Savat · {self.mijoz.username}"

    @property
    def jami(self):
        return sum((it.jami for it in self.itemlar.select_related('mahsulot')), Decimal('0'))

    @property
    def soni(self):
        return sum((it.soni for it in self.itemlar.all()), 0)


class SavatItem(models.Model):
    savat = models.ForeignKey(Savat, on_delete=models.CASCADE, related_name='itemlar')
    mahsulot = models.ForeignKey(Mahsulot, on_delete=models.CASCADE)
    soni = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('savat', 'mahsulot')

    def __str__(self):
        return f"{self.mahsulot} x{self.soni}"

    @property
    def jami(self):
        return (self.mahsulot.narx if self.mahsulot else Decimal('0')) * self.soni
