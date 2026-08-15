# -*- coding: utf-8 -*-
"""Barkod katalogini O'ZBEK do'konlariga to'liq moslaydi:
  • Kirill (rus) nomlarni lotin/o'zbekchaga o'giradi (Хлеб->Non, Молоко->Sut)
  • Dorixona/kosmetika/keraksiz (oziq-ovqat bo'lmagan) yozuvlarni o'chiradi
  • Har mahsulotga to'g'ri KATEGORIYA belgilaydi (kalit so'zlar bo'yicha)
  • Nomni "Coca Cola 0.5 L" ko'rinishiga keltiradi

  python manage.py uzbek_barkod            # bajaradi
  python manage.py uzbek_barkod --korish   # faqat ko'rsatadi
"""
import re
import html
from django.core.management.base import BaseCommand
from mahsulot.models import BarkodKatalog

# ── Kirill -> Lotin (o'zbek) transliteratsiya ──
TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh',
    'ъ': '', 'ы': 'i', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'қ': 'q', 'ғ': 'g', 'ҳ': 'h', 'ў': "o'",
}

# ── Ruscha oziq-ovqat so'zlari -> o'zbekcha/tanish ──
RUS_UZ = {
    'хлеб': 'Non', 'молоко': 'Sut', 'вода': 'Suv', 'сок': 'Sharbat',
    'кетчуп': 'Ketchup', 'майонез': 'Mayonez', 'масло': "Yog'", 'сахар': 'Shakar',
    'соль': 'Tuz', 'мука': 'Un', 'рис': 'Guruch', 'чай': 'Choy', 'кофе': 'Kofe',
    'печенье': 'Pechenye', 'конфеты': 'Konfet', 'конфета': 'Konfet',
    'шоколад': 'Shokolad', 'макароны': 'Makaron', 'макарон': 'Makaron',
    'яйцо': 'Tuxum', 'яйца': 'Tuxum', 'колбаса': 'Kolbasa', 'сыр': 'Pishloq',
    'сметана': 'Smetana', 'творог': 'Tvorog', 'кефир': 'Kefir', 'йогурт': 'Yogurt',
    'спички': 'Gugurt', 'напиток': 'Ichimlik', 'сок яблоко': 'Olma sharbati',
    'вафли': 'Vafli', 'сухарики': 'Suxarik', 'семечки': 'Semichka',
    'жвачка': 'Saqich', 'мороженое': 'Muzqaymoq', 'пельмени': 'Pelmen',
}

# ── OZIQ-OVQAT/DO'KON MAHSULOTI BO'LMAGAN — o'chiriladi ──
JUNK = [
    'нафт', 'ингаля', 'карандаш', 'таблет', 'капсул', 'мазь', 'osteocare',
    'aravia', 'professional', 'osteo', 'omega-3', 'isoflav', 'нафтизин',
    'нафтозалин', 'нафтимизин', 'spray 18000', 'hayay', 'графин', 'mona fit',
    'крем', 'сироп', 'бальзам', 'витамин', 'бинт', 'вата', 'шприц',
    # Dorilar (dorixona)
    'диклофенак', 'аспирин', 'парацетамол', 'анальгин', 'цитрамон', 'но-шпа',
    'аскорбин', 'смекта', 'активированный уголь', 'ибупрофен', 'амоксицил',
    # Buzuq/yuklanmagan/test yozuvlar
    'загрузк', 'zagruzk', 'undefined', 'null', 'error', 'страница',
    'example', 'secureaws', 'brendnam', ' aws', 'aws2', 'test product',
    'lorem', 'ipsum', 'sample product',
]

# ── Kategoriya kalit so'zlari (nom ichida uchrasa) ──
KATEGORIYA = [
    ('hayvon_ozuqa', ['myau', 'whiskas', 'felix', 'kitekat', 'kite kat', 'korm ',
                      'padina', 'chappi', 'pedigree', 'darling']),
    ('bolalar', ['nan ', 'nan 1', 'nan 2', 'nan 3', 'optipro', 'malish', 'malyut',
                 'малыш', 'малют', 'agusha', 'nestogen', 'frisolac', 'nutrilon',
                 'bolalar', 'fruto nyanya', 'malutka']),
    ('muzlatilgan', ['ice cream', 'muzqaymoq', 'plombir', 'morojen', 'pelmen',
                     'vareniki', 'muzlatilgan', 'eskimo']),
    ('baliq', ['ribnaya', 'riba ', 'baliq', 'seld', 'kilka', 'tunets', 'sardin',
               'skumbriya', 'shprot', 'losos', 'seld', 'ikra']),
    ('ichimliklar', ['cola', 'pepsi', 'fanta', 'sprite', 'mirinda', 'schweppes',
                     'suv', 'water', 'sharbat', 'juice', 'sok ', 'ichimlik', 'napitok',
                     'red bull', 'adrenal', 'adrinalin', 'energy', 'hydrolife', 'swell',
                     'montella', 'nesquik', 'limonad', 'kvas', 'borjomi', 'nabeghlavi',
                     '7up', 'dena ', 'aqua', 'damla', 'stella', 'pivo', 'beer', 'kokteyl',
                     'koktey', 'ayran', 'kola', 'multifrukt', 'gazlangan', 'biolife']),
    ('sut', ['sut', ' milk', 'moloko', 'yogurt', 'yogurti', 'kefir', 'smetana',
             'tvorog', 'pishloq', 'cheese', 'puremilky', 'danone', 'activia',
             'president', 'lactel', 'musaffo', 'ryazhenka', 'qatiq', 'togʻ suti',
             'tog suti', 'yunon', 'greek yogurt', 'cottage', 'slivki', 'tvorojn']),
    ('non', ['non', 'bread', 'xleb', 'lepyoshka', 'batafon', 'buxanka', 'batak']),
    ('shirinlik', ['shokolad', 'chocolate', 'konfet', 'candy', 'pechenye', 'pechen',
                   'biscuit', 'oreo', 'kitkat', 'snickers', 'twix', 'bounty', 'milka',
                   'alpen gold', 'halva', 'marmelad', 'vafli', 'nutella', 'kinder',
                   'bonpari', 'bon pari', 'chupa', 'zefir', 'pryanik', 'trolli', 'barni',
                   'tort', ' cake', 'protein bar', 'rokki', 'shokalad', 'jelly', 'shariklar']),
    ('choy_qahva', ['choy', 'chay', ' tea', 'kofe', 'coffee', 'nescafe', 'jacobs',
                    'jacabs', 'lipton', 'jardin', 'mocaccino', 'kapuchino', 'cappuccino']),
    ('makaron', ['makaron', 'makfa', ' pasta', 'spagetti', 'vermishel', 'lapsha']),
    ('un_yorma', ['un ', 'muka', 'guruch', ' rice', 'yorma', 'grechka', 'arpa',
                  'gerkules', 'ovsyan', 'yasmiq', 'mosh', 'kasha', 'kashka', 'botqa',
                  'boʻtqa', 'botqasi', 'kisel', 'minutka', 'mistral', 'passim',
                  'za radinu', 'xlopya', 'gречка', 'boʻtqasi']),
    ('yog', ['yogʻ', 'moyi', 'maslo', ' oil', 'podsolnech', 'olive', 'sviestas', 'sviyos']),
    ('konserva', ['konserva', 'konserv', 'tushonka', 'gorox', 'fasol', 'kukuruza',
                  'tomat pasta', 'pasta tomat', 'sobstvennom']),
    ('gosht', ['goʻsht', 'gosht', 'myaso', 'kolbasa', 'kolbas', 'sosiska', 'sosisk',
               'sardelka', 'vetchina', 'kotlet', 'farsh', 'konina', 'halol', 'shaxskaya']),
    ('gazaklar', ['chips', 'chipsi', ' lay', 'pringles', 'cheetos', 'suxarik', 'xrustik',
                  'semichka', 'snack', 'kraker', 'popkorn', 'cheers', 'nachos',
                  'saqich', 'jvachka', 'orbit', 'dirol', 'mentos', 'eclipse', 'shashlik']),
    ('ziravorlar', ['tuz ', 'shakar', 'sugar', 'ketchup', 'kechup', 'mayonez', 'sous',
                    'sauce', 'ziravor', 'priprava', 'lavr', 'qalampir', 'zira', 'gorchitsa',
                    'limon kislota', 'vanilin', 'vanelin', 'karitsa', 'chesnok', 'kunjut',
                    'sedana', 'uksus', 'gorchit']),
    ('tuxum', ['tuxum', 'yaytso', 'yayka', 'yaйтсо']),
    ('tamaki', ['sigaret', 'cigarette', 'tabak', 'marlboro', 'winston', 'kent',
                'parliament', 'camel', 'rothmans']),
    ('gigiyena', ['sovun', ' milo', 'shampun', 'shampoo', 'zubn', 'pasta zub', 'wet wipes',
                  'colgate', 'nivea', 'dove', 'shoulders', 'prokladka', 'salfetka',
                  'pampers', 'podguznik', 'wipes', 'clear', 'salfet']),
    ('maishiy_kimyo', ['poroshok', 'parashok', 'tozalash', 'fairy', 'tide', 'ariel',
                       'domestos', 'sredstvo', 'otbelivat']),
    ('meva_sabzavot', ['olma', 'banan', 'kartoshka', 'piyoz', 'sabzi', 'pomidor',
                       'bodring', 'meva', 'sabzavot', 'yablok', 'shaftoli', 'olcha',
                       'apelsin', 'limon', 'uzum', 'kunjut']),
]


def transliterate(s):
    """Kirill harflarni lotinga o'giradi (bosh harflarni ham)."""
    out = []
    for ch in s:
        low = ch.lower()
        if low in TRANSLIT:
            lat = TRANSLIT[low]
            out.append(lat.upper() if ch.isupper() and lat else lat)
        else:
            out.append(ch)
    return ''.join(out)


def hajm_ajrat(nom):
    m = re.search(r'(\d+[\.,]?\d*)\s*(мл|кг|грамм|грам|гр|мг|л|г|ml|kg|gramm|gram|gr|mg|litr|l|g)\b',
                  nom, re.IGNORECASE)
    if not m:
        return nom, ''
    son = m.group(1).replace(',', '.')
    b = m.group(2).lower()
    b = {'gr': 'g', 'gram': 'g', 'gramm': 'g', 'мг': 'mg', 'litr': 'L', 'l': 'L',
         'л': 'L', 'мл': 'ml', 'г': 'g', 'кг': 'kg', 'гр': 'g', 'грам': 'g',
         'грамм': 'g'}.get(b, b)
    return (nom[:m.start()] + ' ' + nom[m.end():]).strip(), f"{son} {b}"


def kategoriya_top(nom):
    past = ' ' + nom.lower() + ' '
    for slug, kalitlar in KATEGORIYA:
        for k in kalitlar:
            if k in past:
                return slug
    return ''


def gibberish(nom):
    """Klaviatura-mashi / buzuq yozuvni aniqlaydi (o'chirish uchun)."""
    # 4+ bir xil belgi ketma-ket: "33333", "aaaa"
    if re.search(r'(.)\1\1\1', nom):
        return True
    for w in nom.split():
        harf = re.sub(r'[^a-zA-Zа-яА-Я]', '', w).lower()
        unli = sum(c in 'aeiouаеёиоуыэюя' for c in harf)
        # Unlisiz uzun so'z: "vrrhrhbg"
        if len(harf) >= 7 and unli == 0:
            return True
        # G'ayritabiiy uzun so'z, kam unli: "feyfyfudufy..."
        if len(harf) >= 12 and unli / len(harf) < 0.30:
            return True
    return False


def tozala(nom):
    """Nomni tozalaydi. None qaytsa -> o'chiriladi (junk)."""
    if not nom:
        return None
    nom = html.unescape(nom)                 # &quot; &amp; -> " &
    nom = re.sub(r'&\w+;', ' ', nom)         # qolgan HTML belgilar
    low = nom.lower()
    for j in JUNK:
        if j in low:
            return None  # dorixona/kosmetika/keraksiz
    if gibberish(nom):
        return None      # klaviatura-mashi / buzuq

    # Narx/miqdor quyruqlarini kesamiz ("0,5" kabi o'lchamni SAQLAB):
    #   ", 3.500 Сум ..."  va  ", 1 Бутылка/Пакет/Коробка/Шт ..."
    nom = re.sub(r',?\s*[\d\.\s]+(сум|so\'m|сўм|so’m)\b.*$', '', nom, flags=re.IGNORECASE)
    nom = re.sub(r',\s*\d+\s*(шт|штук|бутылк|пакет|коробк|dona|упаковк)\w*.*$', '', nom, flags=re.IGNORECASE)
    # Ruscha so'zlarni almashtirish (butun so'z)
    for rus, uz in RUS_UZ.items():
        nom = re.sub(r'\b' + re.escape(rus) + r'\b', uz, nom, flags=re.IGNORECASE)
    # Qolgan kirillni translit
    nom = transliterate(nom)
    # Hajmni ajratib, oxiriga qo'yamiz
    tan, hajm = hajm_ajrat(nom)
    tan = re.sub(r'[«»"()\[\]]+', ' ', tan)
    tan = re.sub(r'\s+', ' ', tan).strip(' -_.,;|/\\')
    if len(tan) < 2 or not re.search(r'[A-Za-z]', tan):
        return None
    # Title-case (qisqa qisqartmalar KATTA)
    KATTA = {'uht', 'pet', '7up', 'ld', 'bbq'}
    sozlar = []
    for w in tan.split():
        wl = w.lower()
        if wl in KATTA:
            sozlar.append(w.upper())
        elif any(c.isdigit() for c in w):
            sozlar.append(w)
        else:
            sozlar.append(w[:1].upper() + w[1:].lower())
    natija = ' '.join(sozlar)
    if hajm:
        natija = f"{natija} {hajm}"
    return re.sub(r'\s+', ' ', natija).strip()[:200]


class Command(BaseCommand):
    help = "Barkod katalogini o'zbek do'konlariga to'liq moslaydi (nom+kategoriya)."

    def add_arguments(self, parser):
        parser.add_argument('--korish', action='store_true')

    def handle(self, *args, **opts):
        korish = opts['korish']
        ozgardi = ochirildi = kat_berildi = 0
        namuna = []
        for obj in list(BarkodKatalog.objects.all()):
            yangi = tozala(obj.nomi)
            if yangi is None:
                if len(namuna) < 20:
                    namuna.append(f"  🗑  O'CHIR: {obj.nomi!r}")
                if not korish:
                    obj.delete()
                ochirildi += 1
                continue
            # Kategoriyani toza nomdan qayta hisoblaymiz (eski noto'g'ri bo'lishi mumkin)
            kat = kategoriya_top(yangi) or obj.kategoriya or ''
            oz = False
            if yangi != obj.nomi:
                if len(namuna) < 20:
                    namuna.append(f"  ✏  {obj.nomi!r} -> {yangi!r} [{kat}]")
                oz = True
            if kat and kat != obj.kategoriya:
                kat_berildi += 1
                oz = True
            if oz:
                ozgardi += 1
                if not korish:
                    obj.nomi = yangi
                    obj.kategoriya = kat
                    obj.save(update_fields=['nomi', 'kategoriya', 'yangilangan'])

        for s in namuna:
            self.stdout.write(s)
        rejim = "(faqat ko'rish)" if korish else ""
        self.stdout.write(self.style.SUCCESS(
            f"Tugadi {rejim}. Tozalandi: {ozgardi}, kategoriya berildi: {kat_berildi}, "
            f"o'chirildi (keraksiz): {ochirildi}, qoldi: {BarkodKatalog.objects.count()} ta."
        ))
