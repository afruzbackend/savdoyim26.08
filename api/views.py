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

from mahsulot.models import Mahsulot
from kassa.models import Kassa, SavdoChek, QarzDaftar
from .serializers import (
    UserSerializer, MahsulotSerializer, KassaSerializer,
    QarzDaftarSerializer, SavdoChekSerializer,
)
from .utils import foydalanuvchi_dokoni


class LoginView(APIView):
    """POST {username, password} -> {token, user}. Token'ni keyingi
    so'rovlarda `Authorization: Token <token>` sarlavhasida yuboriladi."""
    authentication_classes = []
    permission_classes = [AllowAny]

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
@permission_classes([IsAuthenticated])
def kassa_view(request):
    """Do'kon kassa balansi."""
    dokon = foydalanuvchi_dokoni(request.user)
    if not dokon:
        return Response({'error': "Do'kon topilmadi"}, status=status.HTTP_403_FORBIDDEN)
    kassa, _ = Kassa.objects.get_or_create(dokon=dokon)
    return Response(KassaSerializer(kassa).data)
