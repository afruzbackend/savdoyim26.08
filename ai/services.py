# -*- coding: utf-8 -*-
"""
AI xizmati — do'kon egasi uchun HISOBOT yordamchisi.

Ikki vazifa bajaradi:
  1) hisobot_tahlil(dokon, davr) — hisobotni avtomatik tahlil qiladi:
        • natijalar NEGA shunday (sabab)
        • yaxshilash/tuzatish uchun NIMA qilish kerak (aniq qadamlar)
  2) savol_javob(dokon, savol, davr) — CHEKLANGAN chat:
        do'kon egasi FAQAT o'z hisoboti bo'yicha savol bera oladi
        ("nega bunday", "qanday tuzataman"). Boshqa (umumiy) savollarga
        AI javob bermaydi — muloyimlik bilan hisobotga qaytaradi.

Model TokenRouter (OpenAI-mos) orqali ishlaydi.
.env:  TOKENROUTER_API_KEY, AI_MODEL (ixtiyoriy), AI_BASE_URL (ixtiyoriy)
"""
from decimal import Decimal
from datetime import timedelta

from django.conf import settings
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone

from kassa.hisobot_service import (
    _oralig, _yig, kassa_holati, ombor_prognoz, pul,
)


# ═══════════════════════════════════════════════════════════
#  KONFIGURATSIYA
# ═══════════════════════════════════════════════════════════
BASE_URL = getattr(settings, 'AI_BASE_URL', 'https://api.tokenrouter.io/v1')
# Model .env dan olinadi. Kimi ishlatmoqchi bo'lsangiz .env ga:
#   AI_MODEL=moonshotai/kimi-k2      (yoki provayder bergan aniq nom)
# Standart "auto:balance" — TokenRouter o'zi eng mos modelni tanlaydi.
MODEL = getattr(settings, 'AI_MODEL', 'auto:balance')
# API uslubi: 'responses' (TokenRouter) yoki 'chat' (Moonshot/OpenAI to'g'ridan).
API_STYLE = (getattr(settings, 'AI_API', 'responses') or 'responses').strip().lower()


def _kalit():
    return (getattr(settings, 'TOKENROUTER_API_KEY', '') or '').strip()


def mavjud():
    """AI sozlanganmi (API kalit bormi)."""
    return bool(_kalit())


def _client():
    """OpenAI-mos mijoz (lazy). TokenRouter ham, boshqa OpenAI-mos
    provayderlar ham shu orqali ishlaydi."""
    from openai import OpenAI
    return OpenAI(api_key=_kalit(), base_url=BASE_URL)


# ═══════════════════════════════════════════════════════════
#  DAVR
# ═══════════════════════════════════════════════════════════
DAVR_NOMI = {
    'kunlik': 'Bugun',
    'haftalik': "So'nggi 7 kun",
    'oylik': 'Joriy oy',
    'yillik': 'Joriy yil',
}


def _davr_oralig(davr):
    """davr kodidan (kunlik/haftalik/oylik/yillik) sana oralig'ini qaytaradi."""
    bugun = timezone.localdate()
    if davr == 'haftalik':
        boshlanish = bugun - timedelta(days=6)
    elif davr == 'oylik':
        boshlanish = bugun.replace(day=1)
    elif davr == 'yillik':
        boshlanish = bugun.replace(month=1, day=1)
    else:  # kunlik
        boshlanish = bugun
    return boshlanish, bugun


# ═══════════════════════════════════════════════════════════
#  BIZNES MA'LUMOTINI YIG'ISH (foyda, tan narx, yetkazib beruvchi ...)
# ═══════════════════════════════════════════════════════════
def _tan_narx(dokon, boshi, oxiri):
    """Sotilgan mahsulotlarning TAN NARXI (sotib olish narxi bo'yicha).
    Mahsulot o'chirilgan bo'lsa (mahsulot=None) — hisobga olinmaydi."""
    from kassa.models import SavdoChekMahsulot
    agg = (
        SavdoChekMahsulot.objects
        .filter(chek__dokon=dokon, mahsulot__isnull=False,
                chek__yaratilgan__gte=boshi, chek__yaratilgan__lt=oxiri)
        .aggregate(
            s=Coalesce(
                Sum(F('soni') * F('mahsulot__sotib_olish_narxi'),
                    output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal('0'),
            )
        )
    )
    return agg['s'] or Decimal('0')


def _yetkazib_summa(dokon, boshi, oxiri):
    """Shu davrda do'konga yetkazib beruvchidan kelgan jo'natmalar summasi va soni."""
    try:
        from yetkazib_beruvchi.models import Jonatma
    except Exception:
        return {'summa': 0, 'soni': 0}
    qs = Jonatma.objects.filter(
        manzil_dokon=dokon, yaratilgan__gte=boshi, yaratilgan__lt=oxiri
    )
    agg = qs.aggregate(s=Sum('jami_summa'))
    return {'summa': agg['s'] or 0, 'soni': qs.count()}


def biznes_holati(dokon, davr='oylik', top_limit=8):
    """AI uchun to'liq biznes tasviri (dict). Foyda, tan narx, yetkazib
    beruvchi xarajati, to'lov turlari, ombor bashorati, qarzlar."""
    boshlanish, tugash = _davr_oralig(davr)
    boshi, oxiri = _oralig(boshlanish, tugash)

    yig = _yig(dokon, boshi, oxiri, top_limit)
    tan = _tan_narx(dokon, boshi, oxiri)
    yetkazib = _yetkazib_summa(dokon, boshi, oxiri)
    kassa = kassa_holati(dokon)

    jami_savdo = Decimal(str(yig['jami_savdo'] or 0))
    foyda = jami_savdo - Decimal(str(tan))
    marja = float(foyda / jami_savdo * 100) if jami_savdo > 0 else 0.0

    # Ombor: tugash arafasidagi mahsulotlar (eng shoshilinch bir nechtasi)
    ombor = ombor_prognoz(dokon, limit=8)

    return {
        'davr': davr,
        'davr_nomi': DAVR_NOMI.get(davr, davr),
        'dokon_nomi': yig['dokon_nomi'],
        'jami_savdo': jami_savdo,
        'tan_narx': Decimal(str(tan)),
        'foyda': foyda,
        'marja': round(marja, 1),
        'chek_soni': yig['chek_soni'],
        'naqd': yig['naqd'],
        'karta': yig['karta'],
        'qarz': yig['qarz'],
        'chegirma': yig['chegirma'],
        'kassaga_tushgan': yig['kassaga_tushgan'],
        'kassa_balans': kassa['balans'],
        'qarz_jami': kassa['qarz_jami'],
        'yetkazib_summa': yetkazib['summa'],
        'yetkazib_soni': yetkazib['soni'],
        'top': yig['top'],
        'ombor': ombor,
    }


def _holat_matni(h):
    """biznes_holati() dict'ini AI o'qiydigan ixcham matnga aylantiradi."""
    q = []
    q.append(f"Do'kon: {h['dokon_nomi']}")
    q.append(f"Davr: {h['davr_nomi']}")
    q.append(f"Umumiy savdo (tushum): {pul(h['jami_savdo'])}")
    q.append(f"Sotilgan tovarlarning tan narxi (sotib olingan narx): {pul(h['tan_narx'])}")
    q.append(f"Sof foyda (savdo - tan narx): {pul(h['foyda'])}  (marja {h['marja']}%)")
    q.append(f"Cheklar (savdolar) soni: {h['chek_soni']}")
    q.append(f"To'lov: naqd {pul(h['naqd'])}, karta {pul(h['karta'])}, qarz/nasiya {pul(h['qarz'])}")
    q.append(f"Berilgan chegirma: {pul(h['chegirma'])}")
    q.append(f"Kassa balansi: {pul(h['kassa_balans'])}")
    q.append(f"To'lanmagan qarzlar (mijozlar): {pul(h['qarz_jami'])}")
    q.append(f"Yetkazib beruvchidan bu davrda kelgan tovar: {pul(h['yetkazib_summa'])} "
             f"({h['yetkazib_soni']} ta jo'natma)")

    if h['top']:
        q.append("Eng ko'p sotilgan mahsulotlar:")
        for i, m in enumerate(h['top'], 1):
            q.append(f"  {i}) {m['mahsulot_nomi']} — {m['jami_soni'] or 0} dona, {pul(m['summa'])}")

    if h['ombor']:
        q.append("Ombor ogohlantirishi (tugab qolayotgan mahsulotlar):")
        for m in h['ombor']:
            qk = m['qolgan_kun']
            qk_txt = f"~{qk} kunda tugaydi" if qk is not None else "sotilmayapti"
            q.append(f"  • {m['nomi']}: qoldiq {m['soni']} {m['birlik']}, {qk_txt} (trend: {m['trend']})")

    return "\n".join(q)


# ═══════════════════════════════════════════════════════════
#  AI CHAQIRUV
# ═══════════════════════════════════════════════════════════
def _sorash(system, user, max_tokens=700):
    """AI ga so'rov yuboradi, matn qaytaradi. Xato bo'lsa Exception ko'taradi.

    API_STYLE='responses' (TokenRouter) yoki 'chat' (OpenAI/Moonshot)."""
    client = _client()
    if API_STYLE == 'chat':
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()

    # TokenRouter Responses API
    resp = client.responses.create(
        model=MODEL,
        instructions=system,
        input=user,
        temperature=0.3,
        max_output_tokens=max_tokens,
    )
    return (getattr(resp, 'output_text', '') or "").strip()


# ── Chatni faqat hisobotga cheklaydigan asosiy qoida ──
CHEKLOV = (
    "Sen 'Savdoyim' do'kon boshqaruv tizimidagi HISOBOT yordamchisisan. "
    "Sen FAQAT quyida berilgan shu do'konning hisoboti va raqamlari haqida "
    "javob berasan: natijalar NEGA shunday ekanini tushuntirasan va ularni "
    "yaxshilash/tuzatish uchun NIMA qilish kerakligini aniq aytasan. "
    "Agar savol hisobotga yoki do'kon biznesiga aloqador bo'lmasa (umumiy "
    "bilim, dasturlash, boshqa mavzular, suhbat) — javob BERMA, bir jumlada "
    "muloyim rad et va foydalanuvchini hisobot bo'yicha savol berishga yo'naltir. "
    "Faqat o'zbek tilida, qisqa va amaliy yoz. Raqamlarni so'mda ayt. "
    "Ma'lumotda yo'q narsani o'ylab topma."
)


def hisobot_tahlil(dokon, davr='oylik'):
    """Hisobotni avtomatik tahlil qiladi: NEGA shunday + NIMA qilish kerak.
    Qaytadi: {'ok': bool, 'matn': str, 'xato': str|None}"""
    if not mavjud():
        return {'ok': False, 'matn': '', 'xato': 'AI sozlanmagan (TOKENROUTER_API_KEY yo\'q).'}

    h = biznes_holati(dokon, davr)
    kontekst = _holat_matni(h)
    user = (
        "Quyida do'konimning hisoboti. Menga tushuntir:\n"
        "1) Natijalar NEGA shunday (asosiy sabablar).\n"
        "2) Foydani oshirish va kamchiliklarni tuzatish uchun 3–5 ta ANIQ qadam.\n"
        "Qisqa, sarlavhalar bilan, o'zbekcha yoz.\n\n"
        f"--- HISOBOT ---\n{kontekst}"
    )
    try:
        matn = _sorash(CHEKLOV, user, max_tokens=800)
        return {'ok': True, 'matn': matn, 'xato': None}
    except Exception as e:
        return {'ok': False, 'matn': '', 'xato': f'AI xatosi: {e}'}


def savol_javob(dokon, savol, davr='oylik'):
    """CHEKLANGAN chat: do'kon egasi faqat hisoboti bo'yicha savol beradi.
    Qaytadi: {'ok': bool, 'matn': str, 'xato': str|None}"""
    savol = (savol or '').strip()
    if not savol:
        return {'ok': False, 'matn': '', 'xato': 'Savol bo\'sh.'}
    if not mavjud():
        return {'ok': False, 'matn': '', 'xato': 'AI sozlanmagan (TOKENROUTER_API_KEY yo\'q).'}

    h = biznes_holati(dokon, davr)
    kontekst = _holat_matni(h)
    user = (
        f"--- MENING HISOBOTIM ---\n{kontekst}\n\n"
        f"--- SAVOLIM ---\n{savol}"
    )
    try:
        matn = _sorash(CHEKLOV, user, max_tokens=600)
        return {'ok': True, 'matn': matn, 'xato': None}
    except Exception as e:
        return {'ok': False, 'matn': '', 'xato': f'AI xatosi: {e}'}
