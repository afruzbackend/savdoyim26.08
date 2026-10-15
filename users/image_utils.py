# -*- coding: utf-8 -*-
"""Rasmlarni yuklashda avtomatik kichraytirish/siqish yordamchisi.

Telefon suratlari ko'pincha 3-5 MB bo'ladi, lekin sayt ularni kichik
kartochka/thumbnail sifatida ko'rsatadi. Bu funksiya faqat SHU so'rovda
yuklangan yangi faylni (UploadedFile) siqadi — bazadan o'qilgan eski
rasm qayta siqilmaydi (masalan `save(update_fields=[...])` da).
"""
import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile


def rasm_optimallash(field, max_tomon=1280, sifat=82):
    """`field` (ImageField qiymati) yangi yuklangan bo'lsa — uni JPEG'ga
    aylantirib, eng katta tomonini `max_tomon` px gacha kichraytiradi va
    `sifat` bilan siqadi. O'zgartirish model .save() dan OLDIN, xotirada
    bajariladi (fayl hali storage'ga yozilmagan)."""
    # Faqat aynan hozir yuklangan faylni siqamiz (eski FieldFile emas)
    if not field or not isinstance(getattr(field, 'file', None), UploadedFile):
        return
    try:
        from PIL import Image, ImageOps
    except Exception:
        # Pillow bo'lmasa rasmni tekshirib bo'lmaydi — xavfsizlik uchun saqlamaymiz
        setattr(field.instance, field.field.attname, '')
        return

    try:
        img = Image.open(field.file)
        img = ImageOps.exif_transpose(img)  # telefon suratini to'g'ri buramiz
        img = img.convert('RGB')
        img.thumbnail((max_tomon, max_tomon), Image.LANCZOS)  # faqat kichraytiradi
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=sifat, optimize=True)
    except Exception:
        # Rasm emas (yoki buzuq) — faylni SAQLAMAYMIZ (HTML/skript yuklashdan himoya)
        setattr(field.instance, field.field.attname, '')
        return

    asos = os.path.splitext(os.path.basename(field.name))[0]
    field.save(f'{asos}.jpg', ContentFile(buf.getvalue()), save=False)


def rasm_haqiqiymi(fayl):
    """Yuklangan fayl haqiqiy rasm ekanini Pillow bilan tekshiradi (kengaytmaga ishonmaydi)."""
    try:
        from PIL import Image
        pos = fayl.tell() if hasattr(fayl, 'tell') else 0
        Image.open(fayl).verify()
        fayl.seek(pos)
        return True
    except Exception:
        return False
