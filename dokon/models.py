from django.db import models
from users.models import DokonEgasiProfil


class DokonSozlama(models.Model):
    dokon = models.OneToOneField(
        DokonEgasiProfil, on_delete=models.CASCADE, related_name='sozlama'
    )
    ish_vaqti_boshlanish = models.TimeField(default='08:00')
    ish_vaqti_tugash = models.TimeField(default='21:00')
    dam_olish_kuni = models.CharField(max_length=20, blank=True)
    ochiq = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.dokon.dokon_nomi} sozlamalari"

    class Meta:
        verbose_name = 'Dokon Sozlama'
