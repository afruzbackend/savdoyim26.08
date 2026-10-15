"""API uchun umumiy yordamchilar."""


def foydalanuvchi_dokoni(user):
    """Foydalanuvchining do'koni — yagona manba users.services.foydalanuvchi_dokoni."""
    from users.services import foydalanuvchi_dokoni as _f
    return _f(user)
