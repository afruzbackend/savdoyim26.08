"""REST API view'lari — token login + do'konga bog'langan o'qish endpointlari.

Barcha ma'lumot FAQAT so'rov yuborgan foydalanuvchining o'z do'koniga tegishli
bo'ladi (boshqa do'kon ma'lumoti ko'rinmaydi).
"""
from django.contrib.auth import authenticate
from rest_framework import viewsets, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle

from mahsulot.models import Mahsulot
from kassa.models import Kassa, SavdoChek, QarzDaftar
from .serializers import (
    UserSerializer, MahsulotSerializer, KassaSerializer,
    QarzDaftarSerializer, SavdoChekSerializer, OmmaviyMahsulotSerializer,
)
from .utils import foydalanuvchi_dokoni


class LoginView(APIView):
    """POST {username, password} -> {token, user}. Token'ni keyingi
    so'rovlarda `Authorization: Token <token>` sarlavhasida yuboriladi."""
    authentication_classes = []
    permission_classes = [AllowAny]
    # Parolni tanlab topishdan himoya (settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login'])
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        if not username or not password:
            return Response(
                {'error': 'username va password kerak'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {'error': "Login yoki parol noto'g'ri"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user': UserSerializer(user).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Joriy token'ni bekor qiladi (chiqish)."""
    Token.objects.filter(user=request.user).delete()
    return Response({'status': 'ok'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Joriy foydalanuvchi ma'lumoti."""
    return Response(UserSerializer(request.user).data)


class _DokonQuerysetMixin:
    """Queryset'ni so'rov yuborgan foydalanuvchining do'koni bilan cheklaydi."""

    def _dokon(self):
        return foydalanuvchi_dokoni(self.request.user)


class MahsulotViewSet(_DokonQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """Do'kon mahsulotlari. `?q=` bilan nom yoki barkod bo'yicha qidirish."""
    serializer_class = MahsulotSerializer

    def get_queryset(self):
        dokon = self._dokon()
        if not dokon:
            return Mahsulot.objects.none()
        qs = Mahsulot.objects.filter(dokon=dokon).order_by('nomi')
        q = (self.request.query_params.get('q') or '').strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(nomi__icontains=q) | Q(barkod__icontains=q))
        return qs


class QarzViewSet(_DokonQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """Do'kon qarzlari. Default — to'lanmaganlar; `?hammasi=1` bilan barchasi."""
    serializer_class = QarzDaftarSerializer

    def get_queryset(self):
        dokon = self._dokon()
        if not dokon:
            return QarzDaftar.objects.none()
        qs = QarzDaftar.objects.filter(dokon=dokon).order_by('-yaratilgan')
        if self.request.query_params.get('hammasi') != '1':
            qs = qs.filter(to_langan=False)
        return qs


class SavdoChekViewSet(_DokonQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    """Do'kon savdo cheklari (so'nggilari birinchi)."""
    serializer_class = SavdoChekSerializer

    def get_queryset(self):
        dokon = self._dokon()
        if not dokon:
            return SavdoChek.objects.none()
        return (SavdoChek.objects.filter(dokon=dokon)
                .prefetch_related('mahsulotlar').order_by('-yaratilgan'))


@api_view(['GET'])
@permission_classes([AllowAny])
def ommaviy_mahsulotlar(request):
    """Mijoz uchun: barcha do'konlardagi faol va sotuvda bor mahsulotlar.
    `?q=` bilan nom yoki barkod qidiruvi. Login talab qilmaydi."""
    qs = (Mahsulot.objects.filter(faol=True, soni__gt=0)
          .select_related('dokon').order_by('nomi'))
    q = (request.query_params.get('q') or '').strip()
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(nomi__icontains=q) | Q(barkod__icontains=q))
    return Response(OmmaviyMahsulotSerializer(qs[:100], many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kassa_view(request):
    """Do'kon kassa balansi."""
    dokon = foydalanuvchi_dokoni(request.user)
    if not dokon:
        return Response({'error': "Do'kon topilmadi"}, status=status.HTTP_403_FORBIDDEN)
    kassa, _ = Kassa.objects.get_or_create(dokon=dokon)
    return Response(KassaSerializer(kassa).data)


# ══════════════════════════════════════════════════════════════
#  SOTUVCHI — SMENA + SAVDO (yozish). Yadro: kassa.savdo_service
# ══════════════════════════════════════════════════════════════
def _dec(v, default='0'):
    from decimal import Decimal, InvalidOperation
    try:
        return Decimal(str(v if v not in (None, '') else default))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def smena_holati(request):
    """Do'konning ochiq smenasi bor-yo'qligi."""
    dokon = foydalanuvchi_dokoni(request.user)
    if not dokon:
        return Response({'error': "Do'kon topilmadi"}, status=status.HTTP_403_FORBIDDEN)
    from kassa.savdo_service import ochiq_smena
    s = ochiq_smena(dokon)
    if not s:
        return Response({'ochiq': False})
    return Response({
        'ochiq': True,
        'id': s.id,
        'ochilgan': s.ochilgan,
        'boshlangich_naqd': str(s.boshlangich_naqd),
        'sotuvchi': s.sotuvchi.username if s.sotuvchi else None,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def smena_ochish_api(request):
    """Smena ochadi. body: {boshlangich_naqd}."""
    dokon = foydalanuvchi_dokoni(request.user)
    if not dokon:
        return Response({'error': "Do'kon topilmadi"}, status=status.HTTP_403_FORBIDDEN)
    from kassa.savdo_service import smena_och
    smena, yangi = smena_och(dokon, request.user, _dec(request.data.get('boshlangich_naqd', 0)))
    return Response({'ochiq': True, 'id': smena.id if smena else None, 'yangi': yangi})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def smena_yopish_api(request):
    """Smenani yopadi. body: {real_naqd} (ixtiyoriy — naqd verka uchun)."""
    dokon = foydalanuvchi_dokoni(request.user)
    if not dokon:
        return Response({'error': "Do'kon topilmadi"}, status=status.HTTP_403_FORBIDDEN)
    from kassa.savdo_service import smena_yop, SavdoXato
    real_raw = request.data.get('real_naqd', None)
    real_naqd = _dec(real_raw) if real_raw not in (None, '') else None
    try:
        smena, data = smena_yop(dokon, real_naqd)
    except SavdoXato as e:
        return Response({'error': e.message}, status=e.code)

    def _f(x):
        return float(x) if x is not None else None

    return Response({
        'status': 'ok',
        'jami_savdo': _f(data['jami_savdo'] or 0),
        'kassaga_tushgan': _f(data['kassaga_tushgan'] or 0),
        'chek_soni': data['chek_soni'],
        'naqd': _f(data['naqd'] or 0),
        'karta': _f(data['karta'] or 0),
        'qarz': _f(data['qarz'] or 0),
        'kutilgan_naqd': _f(smena.kutilgan_naqd),
        'real_naqd': _f(smena.real_naqd),
        'naqd_farq': _f(smena.naqd_farq),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def savdo_api(request):
    """Sotuv yakunlaydi. body: {mahsulotlar:[{id,soni}], tolash_turi,
    chegirma, berilgan, mijoz_ism, mijoz_telefon, qaytarish_sana}."""
    dokon = foydalanuvchi_dokoni(request.user)
    if not dokon:
        return Response({'error': "Do'kon topilmadi"}, status=status.HTTP_403_FORBIDDEN)
    from kassa.savdo_service import ochiq_smena, savdo_yarat, SavdoXato
    if not ochiq_smena(dokon):
        return Response({'error': "Smena yopiq. Avval smenani oching."},
                        status=status.HTTP_400_BAD_REQUEST)
    qaytarish_sana = (request.data.get('qaytarish_sana') or '').strip() or None
    try:
        chek = savdo_yarat(
            dokon, request.user,
            request.data.get('mahsulotlar') or [],
            tolash_turi=request.data.get('tolash_turi', 'naqd'),
            chegirma=_dec(request.data.get('chegirma', 0)),
            berilgan=_dec(request.data.get('berilgan', 0)),
            mijoz_ism=request.data.get('mijoz_ism', '') or '',
            mijoz_telefon=request.data.get('mijoz_telefon', '') or '',
            qaytarish_sana=qaytarish_sana,
        )
    except SavdoXato as e:
        return Response({'error': e.message}, status=e.code)
    return Response({
        'status': 'ok', 'chek_id': chek.id,
        'jami': float(chek.jami), 'qaytim': float(chek.qaytim),
        'tolash_turi': chek.tolash_turi,
    })


# ══════════════════════════════════════════════════════════════
#  MIJOZ — BUYURTMA (Click & Collect). Yadro: buyurtma.OrderService
# ══════════════════════════════════════════════════════════════
def _buyurtma_json(b):
    return {
        'id': b.id,
        'raqam': b.raqam,
        'dokon': b.dokon.dokon_nomi if b.dokon_id else None,
        'holat': b.holat,
        'holat_nomi': b.get_holat_display(),
        'jami': float(b.jami),
        'yaratilgan': b.yaratilgan,
        'keyingi': b.keyingi_holat(),
        'itemlar': [
            {'mahsulot_id': it.mahsulot_id, 'nomi': it.mahsulot_nomi,
             'soni': float(it.soni), 'narx': float(it.narx)}
            for it in b.itemlar.all()
        ],
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mijoz_buyurtmalar(request):
    """Joriy mijozning buyurtmalari (so'nggilari birinchi)."""
    from buyurtma.models import MijozBuyurtma
    qs = (MijozBuyurtma.objects.filter(mijoz=request.user)
          .prefetch_related('itemlar')[:50])
    return Response([_buyurtma_json(b) for b in qs])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mijoz_buyurtma_yarat(request):
    """Buyurtma yaratadi. body: {mahsulotlar:[{id,soni}]}.
    Turli do'kon mahsulotlari bo'lsa — har do'konga alohida buyurtma.
    Ombor rezervlanadi (OrderService.create)."""
    from django.db import transaction
    from mahsulot.models import Mahsulot
    from buyurtma.services import OrderService
    from users.services import ServiceError

    groups = {}
    for it in (request.data.get('mahsulotlar') or []):
        m = (Mahsulot.objects.filter(id=it.get('id'), faol=True)
             .select_related('dokon').first())
        if not m or not m.dokon_id:
            continue
        soni = _dec(it.get('soni', 1), '1')
        if not m.kasrli:
            soni = _dec(int(soni), '1')
        if soni <= 0:
            continue
        groups.setdefault(m.dokon_id, (m.dokon, []))[1].append((m, soni))

    if not groups:
        return Response({'error': "Mahsulot tanlang"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        with transaction.atomic():
            buyurtmalar = [OrderService.create(request.user, dokon, items, request)
                           for dokon, items in groups.values()]
    except ServiceError as e:
        return Response({'error': e.message}, status=e.code)
    return Response(
        {'status': 'ok', 'buyurtma_ids': [b.id for b in buyurtmalar]},
        status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mijoz_buyurtma_bekor(request, buyurtma_id):
    """Mijoz o'z buyurtmasini bekor qiladi (ombor qaytadi)."""
    from django.shortcuts import get_object_or_404
    from buyurtma.models import MijozBuyurtma
    from buyurtma.services import OrderService
    from users.services import ServiceError
    b = get_object_or_404(MijozBuyurtma, id=buyurtma_id, mijoz=request.user)
    try:
        OrderService.cancel(b, request.user, request)
    except ServiceError as e:
        return Response({'error': e.message}, status=e.code)
    return Response({'status': 'ok', 'holat': b.holat})


# ══════════════════════════════════════════════════════════════
#  SOTUVCHI — QARZ TO'LASH · BARKOD · QAYTARISH (refund)
# ══════════════════════════════════════════════════════════════
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def qarz_tolash_api(request, qarz_id):
    """Qarzni to'langan deb belgilaydi (kassaga qo'shiladi)."""
    dokon = foydalanuvchi_dokoni(request.user)
    if not dokon:
        return Response({'error': "Do'kon topilmadi"}, status=status.HTTP_403_FORBIDDEN)
    from kassa.savdo_service import qarz_tolash_yadro
    if qarz_tolash_yadro(dokon, qarz_id):
        return Response({'status': 'ok'})
    return Response({'error': "Topilmadi yoki allaqachon to'langan"},
                    status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mahsulot_barkod(request, barkod):
    """Barkod bo'yicha mahsulot (skaner uchun). Faqat o'z do'koni."""
    dokon = foydalanuvchi_dokoni(request.user)
    if not dokon:
        return Response({'error': "Do'kon topilmadi"}, status=status.HTTP_403_FORBIDDEN)
    m = Mahsulot.objects.filter(barkod=barkod, dokon=dokon, faol=True).first()
    if not m:
        return Response({'error': f"Barkod topilmadi: {barkod}"},
                        status=status.HTTP_404_NOT_FOUND)
    return Response(MahsulotSerializer(m).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chek_topish_api(request):
    """Chekni raqami/token bo'yicha topadi. `?q=`. Qatorlar + qolgan qaytarish."""
    dokon = foydalanuvchi_dokoni(request.user)
    if not dokon:
        return Response({'error': "Do'kon topilmadi"}, status=status.HTTP_403_FORBIDDEN)
    from kassa.savdo_service import chek_topish
    chek = chek_topish(dokon, request.query_params.get('q'))
    if not chek:
        return Response({'error': "Chek topilmadi"}, status=status.HTTP_404_NOT_FOUND)
    return Response({
        'id': chek.id,
        'jami': float(chek.jami),
        'tolash_turi': chek.tolash_turi,
        'yaratilgan': chek.yaratilgan,
        'qaytarish_holati': chek.qaytarish_holati,
        'qatorlar': [
            {
                'cm_id': cm.id,
                'nomi': cm.mahsulot_nomi,
                'narx': float(cm.narx),
                'soni': float(cm.soni),
                'qolgan': float(cm.qolgan_qaytarish),
            }
            for cm in chek.mahsulotlar.all()
        ],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def qaytarish_api(request):
    """Qaytarish (refund). body: {chek_id, sabab, izoh, qatorlar:[{cm_id,soni}]}."""
    dokon = foydalanuvchi_dokoni(request.user)
    if not dokon:
        return Response({'error': "Do'kon topilmadi"}, status=status.HTTP_403_FORBIDDEN)
    from kassa.models import SavdoChek
    from kassa.savdo_service import qaytarish_yarat, SavdoXato
    chek = SavdoChek.objects.filter(dokon=dokon, id=request.data.get('chek_id')).first()
    if not chek:
        return Response({'error': "Chek topilmadi"}, status=status.HTTP_404_NOT_FOUND)
    try:
        _, jami, kassadan = qaytarish_yarat(
            dokon, request.user, chek,
            request.data.get('qatorlar') or [],
            sabab=request.data.get('sabab', 'boshqa'),
            izoh=(request.data.get('izoh') or '').strip(),
        )
    except SavdoXato as e:
        return Response({'error': e.message}, status=e.code)
    return Response({'status': 'ok', 'summa': float(jami),
                     'manba': 'kassadan' if kassadan else 'qarzdan'})


# ══════════════════════════════════════════════════════════════
#  MIJOZ — SODIQLIK BALLARI · MAHSULOT SHARHI
# ══════════════════════════════════════════════════════════════
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mijoz_sodiqlik(request):
    """Mijozning sodiqlik ballari, darajasi va tarixi."""
    from users.models import MijozProfil
    from buyurtma.models import SodiqlikTarix
    from buyurtma.services import BALL_QIYMATI
    profil = MijozProfil.objects.filter(foydalanuvchi=request.user).first()
    ball = profil.sodiqlik_ball if profil else 0
    return Response({
        'ball': ball,
        'qiymat': ball * BALL_QIYMATI,
        'daraja': profil.daraja if profil else None,
        'tarix': [
            {'ball': t.ball, 'sabab': t.sabab, 'sana': t.sana}
            for t in SodiqlikTarix.objects.filter(mijoz=request.user)[:50]
        ],
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def mahsulot_sharh(request, mahsulot_id):
    """GET: mahsulot sharhlari + o'rtacha reyting.
    POST {yulduz, izoh}: sharh yozadi (faqat olib ketilgan mahsulotga)."""
    from django.shortcuts import get_object_or_404
    from mahsulot.services import ReviewService, ReviewStats
    m = get_object_or_404(Mahsulot, id=mahsulot_id)

    if request.method == 'POST':
        from users.services import ServiceError
        try:
            ReviewService.create(
                request.user, m,
                request.data.get('yulduz', 5),
                request.data.get('izoh', ''),
                [], request)
        except ServiceError as e:
            return Response({'error': e.message}, status=e.code)
        return Response({'status': 'ok'}, status=status.HTTP_201_CREATED)

    stats = ReviewStats.get(m)
    sharhlar = m.sharhlar.filter(holat='faol').select_related('foydalanuvchi')[:50]
    return Response({
        'ortacha': stats['ortacha'],
        'jami': stats['jami'],
        'sharhlar': [
            {
                'kim': s.foydalanuvchi.first_name or s.foydalanuvchi.username,
                'yulduz': s.yulduz,
                'izoh': s.izoh,
                'sana': s.yaratilgan,
            }
            for s in sharhlar
        ],
    })
