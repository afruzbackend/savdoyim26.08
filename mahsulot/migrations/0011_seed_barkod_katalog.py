# Mavjud mahsulotlardagi barkodlarni umumiy katalogga ko'chiradi.
from django.db import migrations


def seed(apps, schema_editor):
    Mahsulot = apps.get_model('mahsulot', 'Mahsulot')
    BarkodKatalog = apps.get_model('mahsulot', 'BarkodKatalog')
    for m in Mahsulot.objects.exclude(barkod__isnull=True).exclude(barkod='').select_related('kategoriya'):
        b = (m.barkod or '').strip()
        nomi = (m.nomi or '').strip()
        if not b or not nomi:
            continue
        kat = m.kategoriya.nomi if m.kategoriya_id else ''
        obj, created = BarkodKatalog.objects.get_or_create(
            barkod=b, defaults={'nomi': nomi, 'kategoriya': kat}
        )
        if not created:
            obj.marta += 1
            if kat and not obj.kategoriya:
                obj.kategoriya = kat
            obj.save()


def unseed(apps, schema_editor):
    # Orqaga: katalogni tozalamaymiz (foydali ma'lumot yo'qolmasin)
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('mahsulot', '0010_barkodkatalog_alter_mahsulot_barkod_and_more'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
