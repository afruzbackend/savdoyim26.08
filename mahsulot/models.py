from decimal import Decimal
from django.db import models
from django.db.models import Q
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import DokonEgasiProfil, ZavodProfil, CustomUser
from users.soft_delete import SoftDeleteModel
from users.validators import rasm_kengaytma, fayl_hajmi


class Kategoriya(models.Model):
    KATEGORIYALAR = [
        ('ichimliklar', '🥤 Ichimliklar'),
        ('non', '🍞 Non mahsulotlari'),
        ('sut', '🥛 Sut mahsulotlari'),
        ('gosht', "🥩 Go'sht mahsulotlari"),
        ('baliq', '🐟 Baliq mahsulotlari'),
        ('tuxum', '🥚 Tuxum'),
        ('un_yorma', '🌾 Un va yorma mahsulotlari'),
        ('makaron', '🍝 Makaron mahsulotlari'),
        ('shirinlik', '🍬 Shirinliklar'),
        ('choy_qahva', '☕ Choy va qahva'),
        ('yog', "🫙 Yog' mahsulotlari"),
        ('konserva', '🥫 Konserva mahsulotlari'),
        ('muzlatilgan', '❄️ Muzlatilgan mahsulotlar'),
        ('yarim_tayyor', '🍱 Yarim tayyor mahsulotlar'),
        ('meva_sabzavot', '🥦 Meva va sabzavotlar'),
        ('ziravorlar', "🧂 Ziravorlar va qo'shimchalar"),
        ('gazaklar', '🍿 Gazaklar'),
        ('gigiyena', '🧴 Gigiyena mahsulotlari'),
        ('maishiy_kimyo', '🧹 Maishiy kimyo'),
        ('tamaki', '🚬 Tamaki mahsulotlari'),
        ('bolalar', '👶 Bolalar mahsulotlari'),
        ('hayvonlar', '🐾 Hayvonlar uchun mahsulotlar'),
        ('hayvon_ozuqa', '🦴 Hayvonlar uchun ozuqa'),
        ('boshqa', '📦 Boshqalar'),
    ]

    nomi = models.CharField(max_length=100, choices=KATEGORIYALAR, unique=True)
    ikonka = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return dict(self.KATEGORIYALAR).get(self.nomi, self.nomi)

    class Meta:
        verbose_name = 'Kategoriya'
        verbose_name_plural = 'Kategoriyalar'


class Mahsulot(models.Model):
    nomi = models.CharField(max_length=200)
    kategoriya = models.ForeignKey(
        Kategoriya, on_delete=models.SET_NULL, null=True, blank=True
    )
    dokon = models.ForeignKey(
        DokonEgasiProfil, on_delete=models.CASCADE,
        related_name='mahsulotlar', null=True, blank=True
    )
    zavod = models.ForeignKey(
        ZavodProfil, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='mahsulotlar'
    )
    barkod = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    narx = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sotib_olish_narxi = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Ombor soni — kasrli (kg/litr uchun 0.750 kabi). dona uchun butun ishlatiladi.
    soni = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    minimum_son = models.DecimalField(max_digits=12, decimal_places=3, default=5)
    birlik = models.CharField(max_length=20, default='dona')
    yaroqlilik_muddati = models.DateTimeField(null=True, blank=True)  # yaroqlilik (expiry) sana + soat
    rasm = models.ImageField(upload_to='mahsulotlar/', blank=True, null=True,
                             validators=[rasm_kengaytma, fayl_hajmi])
    tavsif = models.TextField(blank=True)
    faol = models.BooleanField(default=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)
    yangilangan = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Yangi yuklangan rasmni kichraytirib/siqib saqlaymiz (tezlik uchun)
        from users.image_utils import rasm_optimallash
        rasm_optimallash(self.rasm, max_tomon=1280, sifat=82)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nomi

    # Kasrli miqdor bilan sotiladigan birliklar (tarozi mahsulotlari)
    KASRLI_BIRLIKLAR = ('kg', 'litr', 'gramm', 'metr')

    @property
    def kasrli(self):
        """Mahsulot kasrli (tarozi) miqdorda sotiladimi — kg/litr kabi."""
        return (self.birlik or '').lower() in self.KASRLI_BIRLIKLAR

    @property
    def kam_qoldi(self):
        return self.soni <= self.minimum_son

    @property
    def foyda(self):
        """Bir dona uchun foyda (sotuv − tannarx)."""
        return (self.narx or 0) - (self.sotib_olish_narxi or 0)

    @property
    def foyda_foizi(self):
        """Ustama foiz (margin): foyda / tannarx * 100. Tannarx 0 bo'lsa None."""
        if not self.sotib_olish_narxi:
            return None
        return round(float(self.foyda) / float(self.sotib_olish_narxi) * 100, 1)

    @property
    def muddati_otgan(self):
        """Yaroqlilik muddati (sana+soat) o'tganmi."""
        from django.utils import timezone
        return bool(self.yaroqlilik_muddati and self.yaroqlilik_muddati < timezone.now())

    @property
    def muddati_tugayapti(self):
        """Yaroqlilik muddati 7 kun ichida tugaydimi (hali o'tmagan)."""
        from django.utils import timezone
        from datetime import timedelta
        if not self.yaroqlilik_muddati:
            return False
        hozir = timezone.now()
        return hozir <= self.yaroqlilik_muddati <= hozir + timedelta(days=7)

    @property
    def ortacha_reyting(self):
        """Faqat ko'rinadigan (faol) sharhlar bo'yicha o'rtacha reyting."""
        agg = self.sharhlar.filter(holat='faol').aggregate(o=models.Avg('yulduz'))
        return round(agg['o'], 1) if agg['o'] else 0

    @property
    def sharhlar_soni(self):
        return self.sharhlar.filter(holat='faol').count()

    class Meta:
        verbose_name = 'Mahsulot'
        verbose_name_plural = 'Mahsulotlar'
        constraints = [
            # Barkod endi har DO'KON ichida unikal (global emas) — turli do'konlar
            # bir xil barkodli mahsulotni qo'sha oladi (Coca-Cola hamma do'konda).
            models.UniqueConstraint(
                fields=['dokon', 'barkod'],
                condition=Q(barkod__isnull=False),
                name='uniq_dokon_barkod',
            ),
        ]


class SkannerLog(models.Model):
    HARAKAT = [('kirim', 'Kirim'), ('chiqim', 'Chiqim')]
    mahsulot = models.ForeignKey(Mahsulot, on_delete=models.CASCADE)
    harakat = models.CharField(max_length=10, choices=HARAKAT)
    soni = models.DecimalField(max_digits=12, decimal_places=3, default=1)
    foydalanuvchi = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True
    )
    yaratilgan = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.harakat} - {self.mahsulot.nomi}"

    class Meta:
        verbose_name = 'Skanner Log'
        verbose_name_plural = 'Skanner Loglar'


class NarxTarix(models.Model):
    """Mahsulot narxi (sotuv yoki tannarx) o'zgargan har safar yoziladi.
    Kirim narxi oshsa sotuv narxини to'g'rilashга yordam beradi."""
    mahsulot = models.ForeignKey(Mahsulot, on_delete=models.CASCADE,
                                 related_name='narx_tarixi')
    eski_narx = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    yangi_narx = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    eski_sotib = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    yangi_sotib = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    kim = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    sana = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sana']
        verbose_name = 'Narx tarixi'
        verbose_name_plural = 'Narx tarixi'

    def __str__(self):
        return f"{self.mahsulot_id}: {self.eski_narx}→{self.yangi_narx}"

    @property
    def narx_ozgardi(self):
        return self.eski_narx != self.yangi_narx

    @property
    def sotib_ozgardi(self):
        return self.eski_sotib != self.yangi_sotib


class Inventarizatsiya(models.Model):
    """Ombor reviziyasi (sanoq) sessiyasi.
    Egasi/sotuvchi real sonlarni kiritadi → tizim farqni (kamomad/ortiqcha)
    ko'rsatadi → yakunlanganda ombor real songa avtomatik tuzatiladi va
    har farq log qilinadi. O'g'irlik va hisob xatosini ochib beradi."""
    HOLAT = [
        ('ochiq', 'Ochiq'),
        ('yakunlangan', 'Yakunlangan'),
        ('bekor', 'Bekor qilingan'),
    ]
    dokon = models.ForeignKey(DokonEgasiProfil, on_delete=models.CASCADE,
                              related_name='inventarizatsiyalar')
    boshlagan = models.ForeignKey(CustomUser, on_delete=models.SET_NULL,
                                  null=True, blank=True)
    izoh = models.CharField(max_length=200, blank=True)
    holat = models.CharField(max_length=12, choices=HOLAT, default='ochiq', db_index=True)
    boshlangan = models.DateTimeField(auto_now_add=True)
    yakunlangan_vaqt = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-boshlangan']
        verbose_name = 'Inventarizatsiya'
        verbose_name_plural = 'Inventarizatsiyalar'

    def __str__(self):
        return f"Sanoq #{self.id} · {self.dokon_id} · {self.holat}"

    # ── Yig'ma ko'rsatkichlar (hisobot uchun) ──
    def _sanalgan_itemlar(self):
        return self.itemlar.filter(real_soni__isnull=False)

    @property
    def sanalgan_soni(self):
        return self._sanalgan_itemlar().count()

    @property
    def jami_soni(self):
        return self.itemlar.count()

    @property
    def kamomad_qiymat(self):
        """Kamomad (real < tizim) tovarlarning tannarxdagi qiymati."""
        jami = Decimal('0')
        for it in self._sanalgan_itemlar():
            if it.farq < 0:
                jami += (it.sotib_olish_narxi or Decimal('0')) * abs(it.farq)
        return jami

    @property
    def ortiqcha_qiymat(self):
        jami = Decimal('0')
        for it in self._sanalgan_itemlar():
            if it.farq > 0:
                jami += (it.sotib_olish_narxi or Decimal('0')) * it.farq
        return jami

    @property
    def kamomad_soni(self):
        return sum(1 for it in self._sanalgan_itemlar() if it.farq < 0)

    @property
    def ortiqcha_soni(self):
        return sum(1 for it in self._sanalgan_itemlar() if it.farq > 0)


class InventarizatsiyaItem(models.Model):
    inventarizatsiya = models.ForeignKey(Inventarizatsiya, on_delete=models.CASCADE,
                                         related_name='itemlar')
    mahsulot = models.ForeignKey(Mahsulot, on_delete=models.SET_NULL, null=True, blank=True)
    mahsulot_nomi = models.CharField(max_length=200)
    birlik = models.CharField(max_length=20, default='dona')
    # Sanoq boshlangandagi tizim soni (snapshot — o'zgarmas dalil)
    tizim_soni = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    # Egasi kiritgan real son. None = hali sanalmagan.
    real_soni = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    # Kamomad qiymatini hisoblash uchun tannarx snapshot
    sotib_olish_narxi = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    izoh = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['mahsulot_nomi']
        verbose_name = 'Sanoq qatori'

    def __str__(self):
        return f"{self.mahsulot_nomi}: {self.tizim_soni}→{self.real_soni}"

    @property
    def kasrli(self):
        return (self.birlik or '').lower() in Mahsulot.KASRLI_BIRLIKLAR

    @property
    def farq(self):
        """real − tizim (musbat = ortiqcha, manfiy = kamomad). Sanalmagan = 0."""
        if self.real_soni is None:
            return 0
        return self.real_soni - self.tizim_soni

    @property
    def holat(self):
        """'sanalmagan' | 'mos' | 'kamomad' | 'ortiqcha'."""
        if self.real_soni is None:
            return 'sanalmagan'
        f = self.farq
        if f == 0:
            return 'mos'
        return 'kamomad' if f < 0 else 'ortiqcha'


class MahsulotSharh(SoftDeleteModel):
    """Mahsulot sharhi/bahosi. Faqat mahsulotni sotib olib, olib ketgan
    foydalanuvchi yoza oladi (backend tekshiradi). Har mahsulot uchun 1 ta sharh.
    Soft-delete: o'chirilgan sharh bazada qoladi (is_deleted).
    """
    mahsulot = models.ForeignKey(
        Mahsulot, on_delete=models.CASCADE, related_name='sharhlar'
    )
    foydalanuvchi = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='mahsulot_sharhlari'
    )
    # Qaysi buyurtma orqali tasdiqlangani (traceability uchun)
    buyurtma = models.ForeignKey(
        'buyurtma.MijozBuyurtma', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sharhlar'
    )
    yulduz = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )  # 1..5
    izoh = models.TextField(blank=True)
    # Faqat backend belgilaydi — frontend o'zgartira olmaydi
    xaridor_tasdiqlangan = models.BooleanField(default=False)
    # Moderatsiya holati: faol=ko'rinadi (default), yashirin=admin yashirgan
    HOLAT = [('faol', 'Faol'), ('yashirin', 'Yashirin')]
    holat = models.CharField(max_length=10, choices=HOLAT, default='faol', db_index=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)
    yangilangan = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-yaratilgan']
        verbose_name = 'Mahsulot sharh'
        verbose_name_plural = 'Mahsulot sharhlari'
        constraints = [
            # 1 foydalanuvchi -> 1 mahsulotga 1 ta FAOL sharh (o'chirilgani hisobga olinmaydi)
            models.UniqueConstraint(
                fields=['mahsulot', 'foydalanuvchi'],
                condition=Q(is_deleted=False),
                name='uniq_faol_sharh_mahsulot_user',
            ),
            # Baho faqat 1..5
            models.CheckConstraint(
                check=Q(yulduz__gte=1) & Q(yulduz__lte=5), name='sharh_yulduz_1_5'
            ),
        ]
        indexes = [
            models.Index(fields=['mahsulot', 'holat']),
            models.Index(fields=['foydalanuvchi']),
            models.Index(fields=['-yaratilgan']),
        ]

    def __str__(self):
        return f"{self.mahsulot} · {self.foydalanuvchi} · {self.yulduz}★"

    @property
    def korinadi(self):
        return self.holat == 'faol'


class SharhRasm(models.Model):
    """Sharhga biriktirilgan rasm (kameradan). Har sharhga maksimal 3 ta."""
    sharh = models.ForeignKey(
        MahsulotSharh, on_delete=models.CASCADE, related_name='rasmlar'
    )
    rasm = models.ImageField(upload_to='sharh_rasmlar/',
                             validators=[rasm_kengaytma, fayl_hajmi])
    yaratilgan = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        from users.image_utils import rasm_optimallash
        rasm_optimallash(self.rasm, max_tomon=1000, sifat=80)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Rasm · sharh {self.sharh_id}"


class BarkodKatalog(models.Model):
    """Umumiy (markaziy) barkod katalogi — barcha do'konlar birgalikda to'ldiradi.
    Bir do'kon barkodli mahsulot qo'shsa, boshqa do'kon o'sha barkodni
    skanerlaganda mahsulot nomi/kategoriyasi avtomatik chiqadi.
    Tashqi API (GS1 va h.k.) kerak emas — baza foydalanuvchilar orqali o'sadi."""
    barkod = models.CharField(max_length=50, unique=True, db_index=True)
    nomi = models.CharField(max_length=200)
    kategoriya = models.CharField(max_length=100, blank=True)  # Kategoriya.nomi (slug)
    marta = models.PositiveIntegerField(default=1)             # necha do'kon ishlatgan (ishonch)
    yaratilgan = models.DateTimeField(auto_now_add=True)
    yangilangan = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Barkod katalog'
        verbose_name_plural = 'Barkod katalog'
        ordering = ['-marta', '-yangilangan']

    def __str__(self):
        return f"{self.barkod} — {self.nomi}"

    @classmethod
    def yangila(cls, barkod, nomi, kategoriya=''):
        """Katalogga qo'shadi yoki mavjudini yangilaydi (upsert)."""
        barkod = (barkod or '').strip()
        nomi = (nomi or '').strip()
        if not barkod or not nomi:
            return None
        obj, created = cls.objects.get_or_create(
            barkod=barkod, defaults={'nomi': nomi, 'kategoriya': kategoriya or ''}
        )
        if not created:
            obj.marta += 1
            # Bo'sh maydonlarni to'ldiramiz (eskisini buzmaymiz)
            if kategoriya and not obj.kategoriya:
                obj.kategoriya = kategoriya
            obj.save(update_fields=['marta', 'kategoriya', 'yangilangan'])
        return obj
