"""Soft-delete uchun umumiy baza (Orders, Reviews, Notifications).
O'chirish yozuvni bazadan olib tashlamaydi, faqat is_deleted=True qiladi."""
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def faol(self):
        return self.filter(is_deleted=False)


class SoftDeleteManager(models.Manager):
    """Default manager — o'chirilmagan (faol) yozuvlarni qaytaradi."""
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()   # faqat faol yozuvlar
    hammasi = models.Manager()      # barcha yozuvlar (o'chirilganlar ham)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])
