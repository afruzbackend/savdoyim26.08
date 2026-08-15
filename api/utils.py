"""API uchun umumiy yordamchilar."""


def foydalanuvchi_dokoni(user):
    """Foydalanuvchining do'koni (do'kon egasi yoki tasdiqlangan sotuvchi).

    Aks holda None. mahsulot.views._get_dokon bilan bir xil mantiq — bitta
    joyda saqlansa yaxshi bo'lardi, lekin bog'liqlikni oshirmaslik uchun
    API o'zi hisoblaydi.
    """
    if not user or not user.is_authenticated:
        return None
    rol = getattr(user, 'rol', None)
    if rol == 'dokon_egasi':
        return getattr(user, 'dokon_profil', None)
    if rol == 'sotuvchi':
        sp = getattr(user, 'sotuvchi_profil', None)
        # Faqat tasdiqlangan sotuvchi do'kon ma'lumotiga kira oladi
        if sp and getattr(sp, 'sorov_holati', None) == 'tasdiqlangan':
            return sp.dokon
    return None
