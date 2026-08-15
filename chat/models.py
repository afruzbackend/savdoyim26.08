from django.db import models
from users.models import CustomUser


class ChatXona(models.Model):
    ishtirokchilar = models.ManyToManyField(CustomUser, related_name='chat_xonalar')
    nomi = models.CharField(max_length=200, blank=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat #{self.id}"

    class Meta:
        verbose_name = 'Chat Xona'


class ChatXabar(models.Model):
    xona = models.ForeignKey(
        ChatXona, on_delete=models.CASCADE, related_name='xabarlar'
    )
    yuboruvchi = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    matn = models.TextField()
    o_qildi = models.BooleanField(default=False)
    yaratilgan = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.yuboruvchi.username}: {self.matn[:30]}"

    class Meta:
        ordering = ['yaratilgan']
        verbose_name = 'Chat Xabar'
