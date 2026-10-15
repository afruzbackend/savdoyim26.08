"""Eski to'langan qarzlarni yangi qisman-to'lov sxemasiga o'tkazadi:
summa = qolgan qarz (0), tolangan_summa = to'langan, va bitta QarzTolov yozuvi."""
from django.db import migrations


def oldinga(apps, schema_editor):
    QarzDaftar = apps.get_model('kassa', 'QarzDaftar')
    QarzTolov = apps.get_model('kassa', 'QarzTolov')
    for q in QarzDaftar.objects.filter(to_langan=True, tolangan_summa=0):
        if q.summa and q.summa > 0:
            QarzTolov.objects.create(qarz=q, dokon_id=q.dokon_id, summa=q.summa,
                                     tolov_turi='naqd', sana=q.to_langan_sana or q.yaratilgan)
            q.tolangan_summa = q.summa
            q.summa = 0
            q.save(update_fields=['summa', 'tolangan_summa'])


def orqaga(apps, schema_editor):
    QarzDaftar = apps.get_model('kassa', 'QarzDaftar')
    for q in QarzDaftar.objects.filter(to_langan=True):
        q.summa = q.summa + q.tolangan_summa
        q.tolangan_summa = 0
        q.save(update_fields=['summa', 'tolangan_summa'])


class Migration(migrations.Migration):
    dependencies = [
        ('kassa', '0012_qarzdaftar_tolangan_summa_savdochekmahsulot_ikpu_and_more'),
    ]
    operations = [migrations.RunPython(oldinga, orqaga)]
