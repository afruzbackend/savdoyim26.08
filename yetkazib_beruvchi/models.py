from django.db import models
from users.models import YetkazibBeruvchiProfil, ZavodProfil, DokonEgasiProfil
from mahsulot.models import Mahsulot
import uuid


class Jonatma(models.Model):
    HOLAT = [
        ('qabul_kutilmoqda', 'Qabul Kutilmoqda'),
        ('qabul_qilindi', 'Qabul Qilindi'),
        ('yolda', "Yo'lda"),
        ('yetkazildi', 'Yetkazildi'),
        ('bekor', 'Bekor Qilindi'),
    ]

    zavod = models.ForeignKey(
        ZavodProfil, on_delete=models.CASCADE, related_name='jonatmalar'
    )
    yetkazuvchi = models.ForeignKey(
        YetkazibBeruvchiProfil, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='jonatmalar'
    )
    barkod = models.CharField(max_length=50, unique=True, blank=True)
    holat = models.CharField(max_length=20, choices=HOLAT, default='qabul_kutilmoqda')
    izoh = models.TextField(blank=True)
    jami_summa = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # ── Yetkazish manzili (zavod belgilaydi yoki do'kon so'rovidan avtomatik) ──
    manzil_dokon = models.ForeignKey(
        DokonEgasiProfil, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='kelgan_jonatmalar',
        help_text="Yetkaziladigan do'kon (manzil shu do'kondan olinadi)"
    )
    lat = models.FloatField(null=True, blank=True, help_text="Qo'lda belgilangan manzil kengligi")
    lng = models.FloatField(null=True, blank=True, help_text="Qo'lda belgilangan manzil uzunligi")
    manzil_txt = models.CharField(max_length=300, blank=True, help_text="Qo'lda kiritilgan manzil matni")

    chiqish_sana = models.DateField(null=True, blank=True, help_text="Zavoddan chiqqan kun")
    dokon_qabul = models.BooleanField(default=False, help_text="Do'kon QR orqali qabul qildimi (omborga qo'shildi)")

    yaratilgan = models.DateTimeField(auto_now_add=True)
    yangilangan = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.barkod:
            self.barkod = str(uuid.uuid4()).replace('-', '').upper()[:12]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Jo'natma #{self.id} | {self.barkod}"

    class Meta:
        verbose_name = "Jo'natma"
        ordering = ['-yaratilgan']

    # ── Yetkazish manzili ──
    def _manba_dokon(self):
        """Aniq belgilangan do'kon, aks holda mahsulotlardan kelib chiqadigan do'kon."""
        if self.manzil_dokon_id:
            return self.manzil_dokon
        for m in self.mahsulotlar.all():
            if m.mahsulot_id and getattr(m.mahsulot, 'dokon_id', None):
                return m.mahsulot.dokon
        return None

    @property
    def manzil_nomi(self):
        d = self._manba_dokon()
        return d.dokon_nomi if d else ''

    @property
    def manzil_matn(self):
        if self.manzil_txt:
            return self.manzil_txt
        d = self._manba_dokon()
        return (d.manzil or d.dokon_nomi or '') if d else ''

    @property
    def manzil_lat(self):
        if self.lat is not None:
            return self.lat
        d = self._manba_dokon()
        return d.latitude if d else None

    @property
    def manzil_lng(self):
        if self.lng is not None:
            return self.lng
        d = self._manba_dokon()
        return d.longitude if d else None

    @property
    def xaritada_bormi(self):
        """Xaritada ko'rsatish uchun koordinatasi bormi."""
        return self.manzil_lat is not None and self.manzil_lng is not None


class JonatmaMahsulot(models.Model):
    jonatma = models.ForeignKey(
        Jonatma, on_delete=models.CASCADE, related_name='mahsulotlar'
    )
    mahsulot = models.ForeignKey(
        Mahsulot, on_delete=models.SET_NULL, null=True, blank=True
    )
    mahsulot_nomi = models.CharField(max_length=200)
    barkod = models.CharField(max_length=50, blank=True, help_text="Mahsulot barkodi")
    soni = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    birlik = models.CharField(max_length=20, default='dona', help_text="dona / kg")
    narx = models.DecimalField(max_digits=12, decimal_places=2)
    tugash_sana = models.DateField(null=True, blank=True, help_text="Yaroqlilik (tugash) muddati")

    def __str__(self):
        return f"{self.mahsulot_nomi} x{self.soni}"

    class Meta:
        verbose_name = "Jo'natma Mahsulot"


class YetkazuvchiSorov(models.Model):
    """Yetkazuvchi zavodga ishlash uchun so'rov yuboradi"""
    HOLAT = [
        ('kutilmoqda', 'Kutilmoqda'),
        ('qabul_qilindi', 'Qabul Qilindi'),
        ('rad_etildi', 'Rad Etildi'),
    ]
    yetkazuvchi = models.ForeignKey(
        YetkazibBeruvchiProfil, on_delete=models.CASCADE, related_name='sorovlar'
    )
    zavod = models.ForeignKey(
        ZavodProfil, on_delete=models.CASCADE, related_name='yetkazuvchi_sorovlar'
    )
    holat = models.CharField(max_length=20, choices=HOLAT, default='kutilmoqda')
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('yetkazuvchi', 'zavod')
        verbose_name = "Yetkazuvchi So'rov"

    def __str__(self):
        return f"{self.yetkazuvchi} → {self.zavod}"