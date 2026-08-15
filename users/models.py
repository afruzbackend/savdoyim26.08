from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from .soft_delete import SoftDeleteModel
from .validators import (rasm_kengaytma, hujjat_kengaytma, fayl_hajmi, hujjat_hajmi)


class TelegramLink(models.Model):
    """Telegram akkauntini tizim foydalanuvchisiga bog'laydi.
    Bot orqali login qilganda yaratiladi."""
    foydalanuvchi = models.OneToOneField(
        'CustomUser', on_delete=models.CASCADE, related_name='telegram'
    )
    chat_id = models.BigIntegerField(unique=True, db_index=True)
    telegram_username = models.CharField(max_length=150, blank=True)
    ulangan = models.DateTimeField(auto_now_add=True)
    oxirgi_faollik = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Telegram ulanish'
        verbose_name_plural = 'Telegram ulanishlar'

    def __str__(self):
        return f"{self.foydalanuvchi.username} ↔ TG:{self.chat_id}"


class CustomUser(AbstractUser):
    ROL_CHOICES = [
        ('dokon_egasi', 'Dokon Egasi'),
        ('sotuvchi', 'Sotuvchi'),
        ('zavod', 'Zavod'),
        ('mijoz', 'Mijoz'),
        ('yetkazib_beruvchi', 'Yetkazib Beruvchi'),
    ]
    rol = models.CharField(max_length=30, choices=ROL_CHOICES, blank=True, null=True)
    telefon = models.CharField(max_length=20, blank=True, null=True)
    jshshr = models.CharField(max_length=14, blank=True, null=True)
    passport = models.CharField(max_length=20, blank=True, null=True)
    tasdiqlangan = models.BooleanField(default=False)
    rasm = models.ImageField(upload_to='users/', blank=True, null=True,
                             validators=[rasm_kengaytma, fayl_hajmi])
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    # Sayt ichidagi bildirishnomalar yoqilganmi (Settings sahifasidan boshqariladi)
    sayt_bildirishnoma = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        from .image_utils import rasm_optimallash
        rasm_optimallash(self.rasm, max_tomon=600, sifat=82)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"


class DokonEgasiProfil(models.Model):
    foydalanuvchi = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='dokon_profil'
    )
    dokon_nomi = models.CharField(max_length=200)
    soliq_raqami = models.CharField(max_length=20, blank=True)
    manzil = models.TextField(blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    logo = models.ImageField(upload_to='dokon_logolar/', blank=True, null=True,
                             validators=[rasm_kengaytma, fayl_hajmi])
    yaratilgan = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        from .image_utils import rasm_optimallash
        rasm_optimallash(self.logo, max_tomon=512, sifat=82)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.dokon_nomi

    class Meta:
        verbose_name = 'Dokon Egasi Profil'


class SotuvchiProfil(models.Model):
    HOLAT = [
        ('kutilmoqda', 'Kutilmoqda'),
        ('tasdiqlangan', 'Tasdiqlangan'),
        ('rad_etilgan', 'Rad Etilgan'),
    ]
    foydalanuvchi = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='sotuvchi_profil'
    )
    dokon = models.ForeignKey(
        DokonEgasiProfil, on_delete=models.SET_NULL,
        related_name='sotuvchilar', null=True, blank=True
    )
    sorov_holati = models.CharField(max_length=20, choices=HOLAT, default='kutilmoqda')
    yaratilgan = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.foydalanuvchi.username}"

    class Meta:
        verbose_name = 'Sotuvchi Profil'


class ZavodProfil(models.Model):
    foydalanuvchi = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='zavod_profil'
    )
    zavod_nomi = models.CharField(max_length=200)
    soliq_raqami = models.CharField(max_length=20, blank=True)
    mchj_nomi = models.CharField(max_length=200, blank=True)
    hujjatlar = models.FileField(upload_to='zavod_hujjatlar/', blank=True, null=True,
                                 validators=[hujjat_kengaytma, hujjat_hajmi])
    mahsulot_turi = models.TextField(blank=True)
    manzil = models.TextField(blank=True)
    tasdiqlangan = models.BooleanField(default=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.zavod_nomi

    class Meta:
        verbose_name = 'Zavod Profil'


class YetkazibBeruvchiProfil(models.Model):
    MASHINA_TURLARI = [
        ('', '— Tanlanmagan —'),
        # Yengil yuk
        ('Damas', '🚐 Damas'),
        ('Labo', '🚐 Labo'),
        ('Ford Transit', '🚐 Ford Transit'),
        ('Mercedes-Benz Sprinter', '🚐 Mercedes-Benz Sprinter'),
        # O'rta yuk
        ('Isuzu NQR', '🚛 Isuzu NQR'),
        ('Isuzu NPR', '🚛 Isuzu NPR'),
        ('Hyundai Mighty', '🚛 Hyundai Mighty'),
        ('Hyundai HD78', '🚛 Hyundai HD78'),
        ('JAC N75', '🚛 JAC N75'),
        # Og'ir yuk
        ('KamAZ 4308', '🚚 KamAZ 4308'),
        ('MAN TGL', '🚚 MAN TGL'),
        ('Mercedes-Benz Atego', '🚚 Mercedes-Benz Atego'),
        ('Volvo FL', '🚚 Volvo FL'),
        ('Scania P-Series', '🚚 Scania P-Series'),
        # Muzlatkichli
        ('Isuzu NQR Refrigerated', '❄️ Isuzu NQR Muzlatkichli'),
        ('Hyundai Mighty Refrigerated', '❄️ Hyundai Mighty Muzlatkichli'),
        ('Ford Transit Refrigerated', '❄️ Ford Transit Muzlatkichli'),
        ('Mercedes-Benz Sprinter Refrigerated', '❄️ Sprinter Muzlatkichli'),
        ('Mercedes-Benz Atego Refrigerated', '❄️ Atego Muzlatkichli'),
    ]

    foydalanuvchi = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='yetkazuvchi_profil'
    )
    zavod = models.ForeignKey(
        ZavodProfil, on_delete=models.SET_NULL,
        related_name='yetkazuvchilar', null=True, blank=True
    )
    mashina_turi = models.CharField(max_length=100, blank=True, choices=MASHINA_TURLARI)
    mashina_raqami = models.CharField(max_length=20, blank=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.foydalanuvchi.username

    class Meta:
        verbose_name = 'Yetkazib Beruvchi Profil'


class MijozProfil(models.Model):
    foydalanuvchi = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='mijoz_profil'
    )
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    sodiqlik_ball = models.PositiveIntegerField(default=0, help_text="Sodiqlik ballari (yig'ilgan)")
    yaratilgan = models.DateTimeField(auto_now_add=True)

    @property
    def daraja(self):
        """Sodiqlik darajasi (yig'ilgan ballarga qarab)."""
        b = self.sodiqlik_ball
        if b >= 2000:
            return {'nom': 'Oltin', 'emoji': '🥇', 'rang': '#fbbf24'}
        if b >= 500:
            return {'nom': 'Kumush', 'emoji': '🥈', 'rang': '#cbd5e1'}
        return {'nom': 'Bronza', 'emoji': '🥉', 'rang': '#d97706'}

    def __str__(self):
        return self.foydalanuvchi.username

    class Meta:
        verbose_name = 'Mijoz Profil'



class Reyting(models.Model):
    """5 yulduzli baholash tizimi (#5).
    baholovchi -> baholanuvchi (ikkalasi ham CustomUser).
    Mijoz: do'kon egasi / sotuvchini baholaydi.
    Do'kon egasi: zavod / yetkazib beruvchini baholaydi.
    """
    baholovchi = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='bergan_reytinglar'
    )
    baholanuvchi = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='olgan_reytinglar'
    )
    yulduz = models.PositiveSmallIntegerField(default=5)
    izoh = models.TextField(blank=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('baholovchi', 'baholanuvchi')
        ordering = ['-yaratilgan']
        verbose_name = 'Reyting'
        verbose_name_plural = 'Reytinglar'

    def __str__(self):
        return f"{self.baholovchi} -> {self.baholanuvchi}: {self.yulduz}★"


class Bildirishnoma(SoftDeleteModel):
    """Ilova ichidagi bildirishnoma (o'qilgan/o'qilmagan + soft-delete)."""
    foydalanuvchi = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='bildirishnomalar'
    )
    matn = models.CharField(max_length=255)
    havola = models.CharField(max_length=255, blank=True)  # ixtiyoriy: bosilганda o'tadigan sahifa
    oqilgan = models.BooleanField(default=False)
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-yaratilgan']
        verbose_name = 'Bildirishnoma'
        verbose_name_plural = 'Bildirishnomalar'

    def __str__(self):
        return f"{self.foydalanuvchi.username}: {self.matn[:40]}"

    @classmethod
    def yubor(cls, foydalanuvchi, matn, havola=''):
        """Bildirishnoma yaratish uchun qulay yordamchi.
        Foydalanuvchi sayt bildirishnomalarini o'chirgan bo'lsa — yaratilmaydi."""
        if not getattr(foydalanuvchi, 'sayt_bildirishnoma', True):
            return None
        return cls.objects.create(foydalanuvchi=foydalanuvchi, matn=matn, havola=havola)


class AuditLog(models.Model):
    """Muhim amallarni qayd etish (audit): kim, nima, qaysi obyekt, qachon, IP."""
    AMAL = [
        ('order_created', 'Buyurtma yaratildi'),
        ('order_status_changed', 'Buyurtma statusi o‘zgardi'),
        ('review_created', 'Sharh yaratildi'),
        ('review_updated', 'Sharh tahrirlandi'),
        ('review_hidden', 'Sharh yashirildi'),
        ('review_restored', 'Sharh tiklandi'),
    ]
    foydalanuvchi = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_loglar'
    )
    amal = models.CharField(max_length=40, choices=AMAL)
    obyekt_turi = models.CharField(max_length=60, blank=True)   # masalan: MijozBuyurtma
    obyekt_id = models.PositiveIntegerField(null=True, blank=True)
    tafsilot = models.CharField(max_length=255, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    vaqt = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-vaqt']
        verbose_name = 'Audit log'
        verbose_name_plural = 'Audit loglar'
        indexes = [
            models.Index(fields=['amal']),
            models.Index(fields=['-vaqt']),
        ]

    def __str__(self):
        who = self.foydalanuvchi.username if self.foydalanuvchi else 'anon'
        return f"{who} · {self.amal} · {self.obyekt_turi}#{self.obyekt_id}"
