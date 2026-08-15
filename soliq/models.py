from django.db import models
from users.models import DokonEgasiProfil


class SoliqSozlama(models.Model):
    TUR = [
        ('qqs', 'QQS (12%)'),
        ('patent', "Patent solig'i"),
        ('soddalashtirilgan', 'Soddalashtirilgan'),
    ]
    dokon = models.OneToOneField(
        DokonEgasiProfil, on_delete=models.CASCADE, related_name='soliq_sozlama'
    )
    stavka = models.FloatField(default=12.0)
    tur = models.CharField(max_length=30, choices=TUR, default='qqs')

    def __str__(self):
        return f"{self.dokon.dokon_nomi} - {self.stavka}%"

    class Meta:
        verbose_name = 'Soliq Sozlama'
