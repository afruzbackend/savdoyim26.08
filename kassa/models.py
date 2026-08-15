import uuid
from decimal import Decimal
from django.db import models
from datetime import time as _time
from users.models import DokonEgasiProfil, CustomUser
from mahsulot.models import Mahsulot


class AvtoHisobotSozlama(models.Model):
    """Do'kon egasi tanlagan avtomatik Telegram hisobot sozlamalari.
    - kunlik_vaqt: har kuni shu vaqtda kunlik savdo hisoboti botga yuboriladi
    - ombor_vaqt: har kuni ertalab shu vaqtda ombor prognozi (X kun qoldi) yuboriladi
    """
    dokon = models.OneToOneField(DokonEgasiProfil, on_delete=models.CASCADE,
                                 related_name='avto_hisobot')
    kunlik_yoq = models.BooleanField(default=True)      # kunlik hisobot yoqilganmi
    kunlik_vaqt = models.TimeField(default=_time(21, 0))
    ombor_yoq = models.BooleanField(default=True)       # ombor prognozi yoqilganmi
    ombor_vaqt = models.TimeField(default=_time(8, 0))
    oxirgi_kunlik = models.DateField(null=True, blank=True)   # takror yubormaslik uchun
    oxirgi_ombor = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Avto hisobot sozlama'
        verbose_name_plural = 'Avto hisobot sozlamalar'

    def __str__(self):
        return f"{self.dokon.dokon_nomi} avto-hisobot"


class Smena(models.Model):
    """Sotuvchi smenasi. Smena ochiq bo'lmasa kassada sotib bo'lmaydi.
    Yopilganda o'sha smena hisoboti do'kon egasiga Telegramga yuboriladi."""
    HOLAT = [('ochiq', 'Ochiq'), ('yopiq', 'Yopiq')]
    dokon = models.ForeignKey(DokonEgasiProfil, on_delete=models.CASCADE, related_name='smenalar')
    sotuvchi = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    ochilgan = models.DateTimeField(auto_now_add=True)
    yopilgan = models.DateTimeField(null=True, blank=True)
    holat = models.CharField(max_length=10, choices=HOLAT, default='ochiq')

    # ── Pul verkasi (Z-hisobot) ──
    # Smena ochilganda kassadagi boshlang'ich naqd (float).
    boshlangich_naqd = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    # Smena yopilganda kassir REAL sanagan naqd.
    real_naqd = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    # Tizim kutgan naqd (boshlang'ich + naqd sotuv − naqd qaytarish) — yopishda saqlanadi.
    kutilgan_naqd = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    # Farq = real − kutilgan (manfiy = kamomad, musbat = ortiqcha).
    naqd_farq = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-ochilgan']
        verbose_name = 'Smena'
        verbose_name_plural = 'Smenalar'

    def __str__(self):
        return f"{self.dokon.dokon_nomi} · {self.ochilgan:%d.%m %H:%M} ({self.holat})"

    @property
    def verka_holati(self):
        """'yoq' | 'mos' | 'kamomad' | 'ortiqcha' — naqd sanoq natijasi."""
        if self.real_naqd is None or self.naqd_farq is None:
            return 'yoq'
        if self.naqd_farq == 0:
            return 'mos'
        return 'kamomad' if self.naqd_farq < 0 else 'ortiqcha'


class Kassa(models.Model):
    dokon = models.OneToOneField(
        DokonEgasiProfil, on_delete=models.CASCADE, related_name='kassa'
    )
    balans = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    yangilangan = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.dokon.dokon_nomi} kassa"

    class Meta:
        verbose_name = 'Kassa'


class SavdoChek(models.Model):
    TOLASH = [
        ('naqd', 'Naqd'),
        ('karta', 'Karta'),
        ('qarz', 'Qarz'),
    ]
    dokon = models.ForeignKey(DokonEgasiProfil, on_delete=models.CASCADE)
    sotuvchi = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True
    )
    jami = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    chegirma = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    to_langan = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    qaytim = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tolash_turi = models.CharField(max_length=10, choices=TOLASH, default='naqd')
    token = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True, null=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chek #{self.id}"

    class Meta:
        verbose_name = 'Savdo Chek'

    @property
    def qaytarilgan_summa(self):
        """Shu chek bo'yicha jami qaytarilgan pul."""
        return self.qaytarishlar.aggregate(s=models.Sum('summa'))['s'] or Decimal('0')

    @property
    def qaytarish_holati(self):
        """'yoq' | 'qisman' | 'toliq' — chek qaytarilganmi."""
        q = self.qaytarilgan_summa
        if not q:
            return 'yoq'
        return 'toliq' if q >= self.jami else 'qisman'


class SavdoChekMahsulot(models.Model):
    chek = models.ForeignKey(
        SavdoChek, on_delete=models.CASCADE, related_name='mahsulotlar'
    )
    mahsulot = models.ForeignKey(
        Mahsulot, on_delete=models.SET_NULL, null=True, blank=True
    )
    mahsulot_nomi = models.CharField(max_length=200)
    soni = models.DecimalField(max_digits=12, decimal_places=3)
    narx = models.DecimalField(max_digits=12, decimal_places=2)
    jami = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.mahsulot_nomi} x{self.soni}"

    class Meta:
        verbose_name = 'Chek Mahsulot'

    @property
    def qaytarilgan_soni(self):
        """Bu qatordan hozirgacha necha dona qaytarilgan."""
        return self.qaytarish_itemlari.aggregate(s=models.Sum('soni'))['s'] or 0

    @property
    def qolgan_qaytarish(self):
        """Yana necha dona qaytarish mumkin (sotilgan − qaytarilgan)."""
        return self.soni - self.qaytarilgan_soni


class Qaytarish(models.Model):
    """Sotilgan mahsulotni qaytarish (refund).
    Asl chek O'ZGARMAYDI — bu alohida audit yozuvi. Har qaytarishda tovar
    omborga qaytadi va pul kassadan chiqadi (yoki qarzdan kamayadi)."""
    SABAB = [
        ('nuqson', 'Nuqsonli / buzuq tovar'),
        ('mijoz', 'Mijoz fikri o\'zgardi'),
        ('xato', 'Kassir xatosi'),
        ('muddat', 'Muddati o\'tgan'),
        ('boshqa', 'Boshqa sabab'),
    ]
    dokon = models.ForeignKey(DokonEgasiProfil, on_delete=models.CASCADE,
                              related_name='qaytarishlar')
    chek = models.ForeignKey(SavdoChek, on_delete=models.CASCADE,
                             related_name='qaytarishlar')
    sotuvchi = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    summa = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # qaytarilgan pul
    sabab = models.CharField(max_length=10, choices=SABAB, default='boshqa')
    izoh = models.TextField(blank=True)
    # Pul qayerdan chiqdi: kassadan (naqd/karta) yoki qarzdan kamaydimi
    kassadan = models.BooleanField(default=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-yaratilgan']
        verbose_name = 'Qaytarish'
        verbose_name_plural = 'Qaytarishlar'

    def __str__(self):
        return f"Qaytarish #{self.id} · chek #{self.chek_id}"


class QaytarishItem(models.Model):
    qaytarish = models.ForeignKey(Qaytarish, on_delete=models.CASCADE,
                                  related_name='mahsulotlar')
    chek_mahsulot = models.ForeignKey(
        SavdoChekMahsulot, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='qaytarish_itemlari'
    )
    mahsulot = models.ForeignKey(Mahsulot, on_delete=models.SET_NULL, null=True, blank=True)
    mahsulot_nomi = models.CharField(max_length=200)
    soni = models.DecimalField(max_digits=12, decimal_places=3)
    narx = models.DecimalField(max_digits=12, decimal_places=2)
    jami = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.mahsulot_nomi} x{self.soni} (qaytdi)"


class QarzDaftar(models.Model):
    dokon = models.ForeignKey(DokonEgasiProfil, on_delete=models.CASCADE)
    mijoz_ism = models.CharField(max_length=200)
    mijoz_telefon = models.CharField(max_length=20, blank=True)
    chek = models.ForeignKey(
        SavdoChek, on_delete=models.SET_NULL, null=True, blank=True
    )
    summa = models.DecimalField(max_digits=15, decimal_places=2)
    to_langan = models.BooleanField(default=False)
    to_langan_sana = models.DateTimeField(blank=True, null=True)
    qaytarish_sana = models.DateField(blank=True, null=True,
                                      help_text="Mijoz qarzni qaytarishga va'da bergan sana")
    izoh = models.TextField(blank=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mijoz_ism} - {self.summa}"

    class Meta:
        verbose_name = 'Qarz Daftar'
