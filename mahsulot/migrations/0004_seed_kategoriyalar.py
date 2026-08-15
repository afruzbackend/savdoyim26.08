from django.db import migrations


KATEGORIYA_KEYS = [
    'ichimliklar', 'non', 'sut', 'gosht', 'baliq', 'tuxum', 'un_yorma',
    'makaron', 'shirinlik', 'choy_qahva', 'yog', 'konserva', 'muzlatilgan',
    'yarim_tayyor', 'meva_sabzavot', 'ziravorlar', 'gazaklar', 'gigiyena',
    'maishiy_kimyo', 'tamaki', 'bolalar', 'hayvonlar', 'hayvon_ozuqa', 'boshqa',
]


def seed(apps, schema_editor):
    Kategoriya = apps.get_model('mahsulot', 'Kategoriya')
    for key in KATEGORIYA_KEYS:
        Kategoriya.objects.get_or_create(nomi=key)


def unseed(apps, schema_editor):
    # Ma'lumotlarni o'chirmaymiz (mahsulotlar bog'langan bo'lishi mumkin)
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('mahsulot', '0003_alter_kategoriya_options_alter_mahsulot_options_and_more'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
