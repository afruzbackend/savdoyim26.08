# -*- coding: utf-8 -*-
"""Fayl yuklash xavfsizligi — zararli/katta fayllarni to'sadi."""
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

# Ruxsat etilgan hujjat turlari (zavod hujjatlari uchun)
hujjat_kengaytma = FileExtensionValidator(
    allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx']
)

# Ruxsat etilgan rasm turlari
rasm_kengaytma = FileExtensionValidator(
    allowed_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif']
)


def fayl_hajmi(f, max_mb=5):
    """Fayl hajmini cheklaydi (standart 5 MB)."""
    if f and hasattr(f, 'size') and f.size > max_mb * 1024 * 1024:
        raise ValidationError(f"Fayl juda katta — {max_mb} MB dan oshmasin.")


def hujjat_hajmi(f):
    fayl_hajmi(f, max_mb=10)
