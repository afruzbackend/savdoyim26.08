/* ══════════════════════════════════════════════════════════════
   Savdoyim — Ko'p tilli tizim (UZ / RU / EN)
   Bayroq bosilganda butun sayt to'liq o'sha tilga o'tadi.
   Asos til — o'zbekcha (sahifadagi matnning o'zi).
   ────────────────────────────────────────────────────────────── */
(function () {
  "use strict";

  /* ── Tarjima lug'ati: kalit = o'zbekcha matn (asos) ────────── */
  const DICT = {
    ru: {
      // Navigatsiya / bo'limlar
      "Asosiy": "Основное", "Boshqaruv": "Управление", "Moliya": "Финансы",
      "Hisob": "Аккаунт", "Boshqa": "Другое", "Boshqalar": "Другие",
      "Do'kon": "Магазин", "Dokon": "Магазин", "Dashboard": "Панель",
      "Bosh sahifa": "Главная", "Xodimlar": "Сотрудники", "Zavodga buyurtma": "Заказ заводу",
      "Inventarizatsiya": "Инвентаризация", "Qaytarish": "Возврат", "Jo'natma qabul": "Приём поставки",
      "Qaytarish (refund)": "Возврат", "Reyting": "Рейтинг",
      "Kassa": "Касса", "Mahsulotlar": "Товары", "Mahsulot": "Товар",
      "Qarz Daftar": "Долговая книга", "Qarz daftari": "Долговая книга",
      "Soliq": "Налог", "Hisobotlar": "Отчёты", "Hisobot": "Отчёт",
      "Sotuvchilar": "Продавцы", "Sotuvchi": "Продавец",
      "Mijoz buyurtmalari": "Заказы клиентов", "Zavod buyurtmalari": "Заводские заказы",
      "Chat": "Чат", "Chatlar": "Чаты", "Skanner": "Сканер", "Skaner": "Сканер",
      "Yetkazuvchilar": "Поставщики", "Yetkazuvchi": "Поставщик",
      "Jo'natish": "Отправка", "Buyurtmalar": "Заказы",
      "Zavodga so'rov": "Запрос заводу", "Mahsulot Qidirish": "Поиск товаров",
      "Mahsulot qidirish": "Поиск товаров", "🔍 Mahsulot Qidirish": "🔍 Поиск товаров",
      "Savat": "Корзина", "Buyurtmalarim": "Мои заказы",
      "Bildirishnomalar": "Уведомления", "Profil": "Профиль",
      "Chiqish": "Выход", "Kirish": "Вход", "Login": "Логин",
      "Ro'yxatdan o'tish": "Регистрация", "Biz haqimizda": "О нас",
      "Biz haqimizda &rarr;": "О нас →", "Biz haqimizda →": "О нас →", "Mehmon": "Гость",
      "Tizimga kirmagan": "Не авторизован",

      // Rollar
      "Dokon Egasi": "Владелец магазина", "Do'kon egasining": "Владельца магазина",
      "Yetkazib Beruvchi": "Поставщик", "Zavod": "Завод", "Zavodlar": "Заводы",
      "Mijoz": "Клиент", "Kompaniya": "Компания",

      // Umumiy tugmalar / harakatlar
      "Qo'shish": "Добавить", "O'chirish": "Удалить", "Bekor": "Отмена",
      "Bekor qilish": "Отменить", "Saqlash": "Сохранить", "Yangilash": "Обновить",
      "Tozalash": "Очистить", "Ko'rish": "Просмотр", "Yopish": "Закрыть",
      "Orqaga": "Назад", "Yashirish": "Скрыть", "To'xtatish": "Остановить",
      "Qabul": "Принять", "Qabul Qilish": "Принять", "Rad": "Отклонить",
      "Ruxsat": "Доступ", "Amal": "Действие", "Harakatlar": "Действия",
      "Tezkor Harakatlar": "Быстрые действия", "Barchasini ko'rish": "Смотреть все",
      "Barchasi": "Все", "Hammasi": "Всё", "🛒 Hammasi": "🛒 Всё",
      "Sotib olish": "Купить", "Savatga": "В корзину", "Baholash": "Оценить",
      "Yangi": "Новый", "Yangi Hisob": "Новый аккаунт", "Yangi Buyurtma": "Новый заказ",
      "Mahsulotlarni ko'rish": "Смотреть товары", "Hoziroq buyurtma": "Заказать сейчас",
      "Sotib olish narxi (UZS)": "Цена закупки (UZS)",

      // Biz haqimizda (about) — loyiha nomi "Savdoyim" tarjima qilinmaydi
      "Kichik biznesni boshqarish uchun yagona raqamli ekotizim — savdo, ombor, kassa, buyurtma, soliq va yetkazib berish bitta platformada.": "Единая цифровая экосистема для управления малым бизнесом — продажи, склад, касса, заказы, налоги и доставка на одной платформе.",
      "Asoschi": "Основатель",
      "Savdoyim platformasini boshidan oxirigacha ishlab chiqqan asoschi — arxitektura, backend va barcha modullar.": "Основатель, разработавший платформу Savdoyim от начала до конца — архитектура, бэкенд и все модули.",
      "Ma'lumot": "Информация",
      "Joylashuv": "Расположение",
      "Piskent tumani, Toshkent viloyati, O'zbekiston": "Пскентский район, Ташкентская область, Узбекистан",
      "Bosqich": "Этап",
      "Nima qilamiz": "Чем мы занимаемся",
      "Kassa (POS) va savdo": "Касса (POS) и продажи",
      "Ombor va barkod": "Склад и штрихкоды",
      "Zavodga buyurtma": "Заказ на завод",
      "Soliq va hisobot": "Налоги и отчёты",
      "Yetkazib berish va chat": "Доставка и чат",

      // Auth / forma
      "Parol": "Пароль", "Parol *": "Пароль *", "Yangi parol": "Новый пароль",
      "Parolni unutdingizmi?": "Забыли пароль?", "Parolni Tiklash": "Сброс пароля",
      "Foydalanuvchi nomi": "Имя пользователя", "Username *": "Логин *",
      "Ism": "Имя", "Ism *": "Имя *", "Ismingiz": "Ваше имя",
      "Telefon": "Телефон", "Telefon *": "Телефон *", "Telefon raqam:": "Номер телефона:",
      "Email": "Email", "Email *": "Email *", "Email manzil": "Email адрес",
      "Email tasdiqlash kodi *": "Код подтверждения Email *",
      "Emailga tasdiqlash kodini yuborish": "Отправить код подтверждения на Email",
      "Kod yuborish": "Отправить код", "Qayta kod yuborish": "Отправить код заново",
      "Kod emailga yuborildi": "Код отправлен на Email", "Email bloklangan": "Email заблокирован",
      "Tasdiqlash kodi": "Код подтверждения", "Tasdiqlash kodi:": "Код подтверждения:",
      "Kodni kiriting": "Введите код", "Boshqa email bilan urinish": "Попробовать другой Email",
      "Rolingizni tanlang va boshlang": "Выберите роль и начните",
      "(kamida 6 ta belgi)": "(минимум 6 символов)", "(majburiy)": "(обязательно)",
      "Do'kon egasi username *": "Логин владельца магазина *",
      "Qaysi do'konda ishlaysiz?": "В каком магазине работаете?",
      "Do'kon ochish": "Открыть магазин",
      "Yangi hisob ochish": "Создать новый аккаунт", "yoki": "или",
      "— Tanlang —": "— Выберите —",
      "Kod yuborildi. Amal qilish muddati:": "Код отправлен. Срок действия:",
      "Kod muddati tugadi. Qayta kod yuboring.": "Срок кода истёк. Отправьте код заново.",

      // Do'kon / kompaniya ma'lumotlari
      "Dokon ma'lumotlari": "Данные магазина", "Dokon nomi": "Название магазина",
      "Dokon manzili": "Адрес магазина", "Zavod ma'lumotlari": "Данные завода",
      "Zavod nomi": "Название завода", "MCHJ nomi": "Название ООО",
      "Soliq raqami": "ИНН", "Soliq raqami (INN)": "ИНН",
      "Transport ma'lumotlari": "Данные транспорта", "Transport turi": "Тип транспорта",
      "Mashina": "Автомобиль", "Davlat raqami": "Гос. номер", "Davlat raqami *": "Гос. номер *",
      "Pasport seriyasi": "Серия паспорта", "JSHSHR": "ПИНФЛ",
      "Hujjatlar (PDF/rasm)": "Документы (PDF/фото)", "Joylashuv": "Локация",

      // Kassa / savdo
      "Kassa Balansi": "Баланс кассы", "Kassani Ochish": "Открыть кассу",
      "Kassa &amp; savdo": "Касса и продажа", "Kassa (POS) va savdo": "Касса (POS) и продажа",
      "Naqd": "Наличные", "💵 Naqd": "💵 Наличные", "Karta": "Карта", "💳 Karta": "💳 Карта",
      "Qarz": "Долг", "📋 Qarz": "📋 Долг", "Karta raqami:": "Номер карты:",
      "Berilgan pul:": "Внесённая сумма:", "To'lash:": "К оплате:",
      "Jami": "Итого", "Jami:": "Итого:", "Summa": "Сумма", "Narx": "Цена",
      "Soni": "Кол-во", "Chek": "Чек", "Cheklar Soni": "Кол-во чеков",
      "Cheklar yo'q": "Чеков нет", "Kirim": "Приход", "Chiqim": "Расход",
      "Mijoz ismi": "Имя клиента", "Mijoz ismi:": "Имя клиента:",
      "Izoh": "Комментарий", "Izoh (ixtiyoriy)": "Комментарий (необязательно)",

      // Savdo statistikasi
      "Jami Savdo": "Всего продаж", "Kunlik Savdo": "Продажи за день",
      "Haftalik Savdo": "Продажи за неделю", "Oylik Savdo": "Продажи за месяц",
      "Yillik Savdo": "Продажи за год", "Eng Ko'p Sotilgan": "Самые продаваемые",
      "ta savdo": "продаж", "📅 Kunlik": "📅 За день", "📆 Haftalik": "📆 За неделю",
      "🗓 Oylik": "🗓 За месяц", "📊 Yillik": "📊 За год",
      "So'nggi Buyurtmalar": "Последние заказы", "So'nggi Cheklar": "Последние чеки",
      "So'nggi Operatsiyalar": "Последние операции", "So'nggi Qarzlar": "Последние долги",
      "Savdo": "Продажа", "Savdo yo'q": "Продаж нет",

      // Ombor / mahsulot
      "Ombor": "Склад", "Ombor va barkod": "Склад и штрихкод", "Ombordagi soni": "Кол-во на складе",
      "Dokonlarda": "В магазинах", "Dokonlarda Kam Qolgan": "Заканчивается в магазинах",
      "Kam": "Мало", "Kam Qolgan": "Заканчивается", "Kam Qolgan Mahsulotlar": "Заканчивающиеся товары",
      "Kam qolganlar": "Заканчивающиеся", "Qoldi": "Осталось", "Mavjud": "В наличии",
      "Mavjud emas": "Нет в наличии", "Yetarli": "Достаточно", "Tugagan": "Закончился",
      "Tugayotgan": "Заканчивается", "Minimum": "Минимум", "Min": "Мин",
      "Minimum darajada": "На минимуме", "Minimum soni (ogohlantirish)": "Мин. кол-во (предупреждение)",
      "Mahsulot Qo'shish": "Добавить товар", "Mahsulot nomi": "Название товара",
      "Mahsulot nomi *": "Название товара *", "Mahsulot turi": "Тип товара",
      "Mahsulot turi *": "Тип товара *", "Mahsulot tanlang": "Выберите товар",
      "Mahsulot yo'q": "Товаров нет", "Hozircha mahsulotlar yo'q": "Пока нет товаров",
      "Ishlab chiqaruvchi": "Производитель", "Tavsif": "Описание",
      "Tavsiya etilgan mahsulotlar": "Рекомендуемые товары",
      "Sotish narxi (UZS) *": "Цена продажи (UZS) *", "Rasm *": "Фото *",
      "O'lchov birligi": "Единица измерения", "Barkod": "Штрихкод",
      "Barkod Skaneri": "Сканер штрихкода", "Barkod Skanerlash": "Сканирование штрихкода",
      "Kamera Ochish": "Открыть камеру", "Qo'lda Kiritish": "Ввести вручную",
      "Rasmga olish (kamera)": "Снять (камера)", "Suratga olish": "Сфотографировать",

      // O'lchov birliklari
      "Dona": "Шт", "Kilogram": "Килограмм", "Litr": "Литр", "Metr": "Метр",
      "Quti": "Коробка", "Tur": "Тип", "Jami tur": "Всего типов",

      // Kategoriyalar
      "Ichimliklar": "Напитки", "Gazaklar": "Закуски", "Shirinliklar": "Сладости",
      "Sut mahsulotlari": "Молочные продукты", "Go'sht mahsulotlari": "Мясные продукты",
      "Baliq mahsulotlari": "Рыбные продукты", "Non mahsulotlari": "Хлебобулочные изделия",
      "Meva va sabzavot": "Фрукты и овощи", "Un va yorma": "Мука и крупы",
      "Un va yorma mahsulotlari": "Мука и крупы", "Sabzavotlar": "Овощи", "Mevalar": "Фрукты",
      "Yog' mahsulotlari": "Масложировые продукты", "Konserva": "Консервы",
      "Makaron": "Макароны", "Choy va qahva": "Чай и кофе", "Ziravorlar": "Специи",
      "Tuxum": "Яйца", "Muzlatilgan": "Замороженные", "Gigiyena": "Гигиена",
      "Maishiy kimyo": "Бытовая химия", "Bolalar mahsulotlari": "Детские товары",
      "Hayvon ozuqasi": "Корм для животных", "Hayvonlar uchun": "Для животных",
      "Tamaki": "Табак", "Kompaniya": "Компания",

      // Buyurtma / holat
      "Buyurtma berish": "Оформить заказ", "Buyurtma Tarkibi": "Состав заказа",
      "Buyurtma yo'q": "Заказов нет", "Hali buyurtma bermagansiz": "Вы ещё не делали заказов",
      "Holat": "Статус", "Holat tarixi": "История статусов", "Sana": "Дата",
      "Sana va Vaqt": "Дата и время", "Kutilmoqda": "Ожидается", "Kutilayotgan": "Ожидаемые",
      "Tasdiqlangan": "Подтверждён", "Tayyorlanmoqda": "Готовится", "Yarim tayyor": "Полуготов",
      "Yo'lda": "В пути", "Yetkazildi": "Доставлен", "Yakunlandi": "Завершён",
      "Bekor qilindi": "Отменён", "Rad etildi": "Отклонён", "Qabul qilindi": "Принят",
      "To'langan": "Оплачено", "To'lanmagan": "Не оплачено", "Bosqich": "Этап",

      // So'rovlar
      "So'rov": "Запрос", "So'rovlar": "Запросы", "Mening So'rovlarim": "Мои запросы",
      "Yetkazuvchi So'rovlari": "Запросы поставщиков", "So'rov rad etildi": "Запрос отклонён",
      "So'rovingiz kutilmoqda": "Ваш запрос в ожидании", "Ruxsat yo'q": "Нет доступа",
      "Sotuvchilarni Boshqarish": "Управление продавцами", "Sotuvchilar yo'q": "Продавцов нет",
      "Biriktirilmagan": "Не привязан",

      // Soliq
      "Soliq Hisoblash": "Расчёт налога", "Soliq Stavkasi": "Ставка налога",
      "Soliq va hisobot": "Налог и отчёт", "Formula:": "Формула:",

      // Jo'natma
      "Jo'natma yaratish": "Создать отправку", "Jo'natma yo'q": "Отправок нет",
      "Jo'natmalar": "Отправки", "Jo'natmalar Ro'yxati": "Список отправок",
      "Jami Jo'natmalar": "Всего отправок", "Jo'natmalar soni": "Кол-во отправок",
      "Jo'natiladigan soni": "Кол-во к отправке", "Yetkazuvchilar Ro'yxati": "Список поставщиков",
      "Yetkazuvchi yo'q": "Поставщиков нет", "Yetkazuvchi (ixtiyoriy)": "Поставщик (необязательно)",
      "Zavodga Buyurtma": "Заказ заводу", "Zavodga buyurtma": "Заказ заводу",
      "Zavod Tanlang": "Выберите завод", "Mahsulot yetkazish": "Доставка товара",
      "Marshrut": "Маршрут", "Masofa va yo'l uchun": "За расстояние и дорогу",
      "Xarita": "Карта", "Google Maps": "Google Maps", "Yandex Xarita": "Яндекс Карты",
      "Xarita ilovasini tanlang": "Выберите приложение карт",
      "Marshrutni qayerda ochamiz?": "Где открыть маршрут?",

      // Chat
      "Chatlar yo'q": "Чатов нет", "Zavod bilan chat": "Чат с заводом",
      "Yetkazuvchi bilan chat": "Чат с поставщиком", "Yetkazib berish va chat": "Доставка и чат",
      "Hech kim topilmadi": "Никого не найдено",
      "Boshqa foydalanuvchi bilan chat boshlash uchun ularning ID sini kiriting":
        "Введите ID пользователя, чтобы начать чат",

      // Reyting / sharh
      "Reyting": "Рейтинг", "Sharh qoldirmoqchimisiz?": "Хотите оставить отзыв?",
      "Hozircha sharhlar yo'q": "Пока нет отзывов", "Tasdiqlangan xaridor": "Подтверждённый покупатель",
      "Baho berish uchun avval xarid qiling": "Сначала совершите покупку, чтобы оценить",
      "Baho va sharh qoldirish uchun tizimga kiring": "Войдите, чтобы оставить оценку и отзыв",
      "Buyurtma berish uchun tizimga kiring": "Войдите, чтобы оформить заказ",

      // Umumiy so'zlar / holatlar
      "Ma'lumot": "Информация", "Ma'lumotlar": "Данные", "Mavzu": "Тема",
      "Mavzuni almashtirish": "Сменить тему", "O'chiq": "Выкл", "Yoqilgan": "Вкл",
      "Barcha Qarzlar": "Все долги", "Qarzlar": "Долги", "Bugun — soat bo'yicha:": "Сегодня — по часам:",
      "Nima qilamiz": "Что делаем", "Sizdan": "От вас",

      // Bo'sh / xato holatlar
      "Savat bo'sh": "Корзина пуста", "Bu kategoriyada hozircha mahsulot yo'q": "В этой категории пока нет товаров",
      "Boshqa so'z bilan qidiring": "Попробуйте другой запрос",
      "Sahifa topilmadi": "Страница не найдена", "Xatolik yuz berdi": "Произошла ошибка",
      "Bosh sahifaga qaytish": "На главную",
      "Uzr, sizda bu bo'limga kirish huquqi yo'q.": "Извините, у вас нет доступа к этому разделу.",
      "Uzr, hozircha bu qism mavjud emas yoki nimadir xato yuz berdi.":
        "Извините, этот раздел недоступен или произошла ошибка.",

      // Platforma tavsifi (footer / about)
      "Biznes boshqaruv tizimi": "Система управления бизнесом",
      "Asoschi": "Основатель", "GPS yoqish": "Включить GPS", "GPS yoqing": "Включите GPS",
      "GPS orqali eng yaqin dokondan toping": "Найдите ближайший магазин через GPS",
    },

    en: {
      "Asosiy": "Main", "Boshqaruv": "Management", "Moliya": "Finance",
      "Hisob": "Account", "Boshqa": "Other", "Boshqalar": "Others",
      "Do'kon": "Store", "Dokon": "Store", "Dashboard": "Dashboard",
      "Bosh sahifa": "Home", "Xodimlar": "Staff", "Zavodga buyurtma": "Order to factory", "Reyting": "Rating",
      "Inventarizatsiya": "Inventory count", "Qaytarish": "Returns", "Jo'natma qabul": "Receive shipment",
      "Kassa": "Cashbox", "Mahsulotlar": "Products", "Mahsulot": "Product",
      "Qarz Daftar": "Debt ledger", "Qarz daftari": "Debt ledger",
      "Soliq": "Tax", "Hisobotlar": "Reports", "Hisobot": "Report",
      "Sotuvchilar": "Sellers", "Sotuvchi": "Seller",
      "Mijoz buyurtmalari": "Customer orders", "Zavod buyurtmalari": "Factory orders",
      "Chat": "Chat", "Chatlar": "Chats", "Skanner": "Scanner", "Skaner": "Scanner",
      "Yetkazuvchilar": "Suppliers", "Yetkazuvchi": "Supplier",
      "Jo'natish": "Dispatch", "Buyurtmalar": "Orders",
      "Zavodga so'rov": "Request to factory", "Mahsulot Qidirish": "Product search",
      "Mahsulot qidirish": "Product search", "🔍 Mahsulot Qidirish": "🔍 Product search",
      "Savat": "Cart", "Buyurtmalarim": "My orders",
      "Bildirishnomalar": "Notifications", "Profil": "Profile",
      "Chiqish": "Logout", "Kirish": "Login", "Login": "Login",
      "Ro'yxatdan o'tish": "Sign up", "Biz haqimizda": "About us",
      "Biz haqimizda &rarr;": "About us →", "Biz haqimizda →": "About us →", "Mehmon": "Guest",
      "Tizimga kirmagan": "Not logged in",

      "Dokon Egasi": "Store owner", "Do'kon egasining": "Store owner's",
      "Yetkazib Beruvchi": "Supplier", "Zavod": "Factory", "Zavodlar": "Factories",
      "Mijoz": "Customer", "Kompaniya": "Company",

      "Qo'shish": "Add", "O'chirish": "Delete", "Bekor": "Cancel",
      "Bekor qilish": "Cancel", "Saqlash": "Save", "Yangilash": "Refresh",
      "Tozalash": "Clear", "Ko'rish": "View", "Yopish": "Close",
      "Orqaga": "Back", "Yashirish": "Hide", "To'xtatish": "Stop",
      "Qabul": "Accept", "Qabul Qilish": "Accept", "Rad": "Reject",
      "Ruxsat": "Access", "Amal": "Action", "Harakatlar": "Actions",
      "Tezkor Harakatlar": "Quick actions", "Barchasini ko'rish": "View all",
      "Barchasi": "All", "Hammasi": "All", "🛒 Hammasi": "🛒 All",
      "Sotib olish": "Buy", "Savatga": "To cart", "Baholash": "Rate",
      "Yangi": "New", "Yangi Hisob": "New account", "Yangi Buyurtma": "New order",
      "Mahsulotlarni ko'rish": "View products", "Hoziroq buyurtma": "Order now",
      "Sotib olish narxi (UZS)": "Purchase price (UZS)",

      // Biz haqimizda (about) — loyiha nomi "Savdoyim" tarjima qilinmaydi
      "Kichik biznesni boshqarish uchun yagona raqamli ekotizim — savdo, ombor, kassa, buyurtma, soliq va yetkazib berish bitta platformada.": "A single digital ecosystem for managing a small business — sales, inventory, POS, orders, tax and delivery on one platform.",
      "Asoschi": "Founder",
      "Savdoyim platformasini boshidan oxirigacha ishlab chiqqan asoschi — arxitektura, backend va barcha modullar.": "The founder who built the Savdoyim platform end to end — architecture, backend and all modules.",
      "Ma'lumot": "Information",
      "Joylashuv": "Location",
      "Piskent tumani, Toshkent viloyati, O'zbekiston": "Piskent district, Tashkent region, Uzbekistan",
      "Bosqich": "Stage",
      "Nima qilamiz": "What we do",
      "Kassa (POS) va savdo": "POS & sales",
      "Ombor va barkod": "Inventory & barcodes",
      "Zavodga buyurtma": "Order to factory",
      "Soliq va hisobot": "Tax & reports",
      "Yetkazib berish va chat": "Delivery & chat",

      "Parol": "Password", "Parol *": "Password *", "Yangi parol": "New password",
      "Parolni unutdingizmi?": "Forgot password?", "Parolni Tiklash": "Reset password",
      "Foydalanuvchi nomi": "Username", "Username *": "Username *",
      "Ism": "Name", "Ism *": "Name *", "Ismingiz": "Your name",
      "Telefon": "Phone", "Telefon *": "Phone *", "Telefon raqam:": "Phone number:",
      "Email": "Email", "Email *": "Email *", "Email manzil": "Email address",
      "Email tasdiqlash kodi *": "Email verification code *",
      "Emailga tasdiqlash kodini yuborish": "Send verification code to Email",
      "Kod yuborish": "Send code", "Qayta kod yuborish": "Resend code",
      "Kod emailga yuborildi": "Code sent to Email", "Email bloklangan": "Email blocked",
      "Tasdiqlash kodi": "Verification code", "Tasdiqlash kodi:": "Verification code:",
      "Kodni kiriting": "Enter code", "Boshqa email bilan urinish": "Try another Email",
      "Rolingizni tanlang va boshlang": "Choose your role and start",
      "(kamida 6 ta belgi)": "(at least 6 characters)", "(majburiy)": "(required)",
      "Do'kon egasi username *": "Store owner username *",
      "Qaysi do'konda ishlaysiz?": "Which store do you work at?",
      "Do'kon ochish": "Open a store",
      "Yangi hisob ochish": "Create a new account", "yoki": "or",
      "— Tanlang —": "— Select —",
      "Kod yuborildi. Amal qilish muddati:": "Code sent. Valid for:",
      "Kod muddati tugadi. Qayta kod yuboring.": "Code expired. Send the code again.",

      "Dokon ma'lumotlari": "Store details", "Dokon nomi": "Store name",
      "Dokon manzili": "Store address", "Zavod ma'lumotlari": "Factory details",
      "Zavod nomi": "Factory name", "MCHJ nomi": "LLC name",
      "Soliq raqami": "Tax ID", "Soliq raqami (INN)": "Tax ID (INN)",
      "Transport ma'lumotlari": "Vehicle details", "Transport turi": "Vehicle type",
      "Mashina": "Vehicle", "Davlat raqami": "Plate number", "Davlat raqami *": "Plate number *",
      "Pasport seriyasi": "Passport series", "JSHSHR": "PINFL",
      "Hujjatlar (PDF/rasm)": "Documents (PDF/image)", "Joylashuv": "Location",

      "Kassa Balansi": "Cashbox balance", "Kassani Ochish": "Open cashbox",
      "Kassa &amp; savdo": "Cashbox & sales", "Kassa (POS) va savdo": "Cashbox (POS) & sales",
      "Naqd": "Cash", "💵 Naqd": "💵 Cash", "Karta": "Card", "💳 Karta": "💳 Card",
      "Qarz": "Debt", "📋 Qarz": "📋 Debt", "Karta raqami:": "Card number:",
      "Berilgan pul:": "Amount given:", "To'lash:": "To pay:",
      "Jami": "Total", "Jami:": "Total:", "Summa": "Amount", "Narx": "Price",
      "Soni": "Qty", "Chek": "Receipt", "Cheklar Soni": "Receipt count",
      "Cheklar yo'q": "No receipts", "Kirim": "Income", "Chiqim": "Expense",
      "Mijoz ismi": "Customer name", "Mijoz ismi:": "Customer name:",
      "Izoh": "Note", "Izoh (ixtiyoriy)": "Note (optional)",

      "Jami Savdo": "Total sales", "Kunlik Savdo": "Daily sales",
      "Haftalik Savdo": "Weekly sales", "Oylik Savdo": "Monthly sales",
      "Yillik Savdo": "Yearly sales", "Eng Ko'p Sotilgan": "Best sellers",
      "ta savdo": "sales", "📅 Kunlik": "📅 Daily", "📆 Haftalik": "📆 Weekly",
      "🗓 Oylik": "🗓 Monthly", "📊 Yillik": "📊 Yearly",
      "So'nggi Buyurtmalar": "Recent orders", "So'nggi Cheklar": "Recent receipts",
      "So'nggi Operatsiyalar": "Recent operations", "So'nggi Qarzlar": "Recent debts",
      "Savdo": "Sale", "Savdo yo'q": "No sales",

      "Ombor": "Warehouse", "Ombor va barkod": "Warehouse & barcode", "Ombordagi soni": "Stock quantity",
      "Dokonlarda": "In stores", "Dokonlarda Kam Qolgan": "Low in stores",
      "Kam": "Low", "Kam Qolgan": "Low stock", "Kam Qolgan Mahsulotlar": "Low stock products",
      "Kam qolganlar": "Low stock", "Qoldi": "Left", "Mavjud": "In stock",
      "Mavjud emas": "Out of stock", "Yetarli": "Sufficient", "Tugagan": "Out",
      "Tugayotgan": "Running out", "Minimum": "Minimum", "Min": "Min",
      "Minimum darajada": "At minimum", "Minimum soni (ogohlantirish)": "Min. quantity (alert)",
      "Mahsulot Qo'shish": "Add product", "Mahsulot nomi": "Product name",
      "Mahsulot nomi *": "Product name *", "Mahsulot turi": "Product type",
      "Mahsulot turi *": "Product type *", "Mahsulot tanlang": "Select a product",
      "Mahsulot yo'q": "No products", "Hozircha mahsulotlar yo'q": "No products yet",
      "Ishlab chiqaruvchi": "Manufacturer", "Tavsif": "Description",
      "Tavsiya etilgan mahsulotlar": "Recommended products",
      "Sotish narxi (UZS) *": "Selling price (UZS) *", "Rasm *": "Image *",
      "O'lchov birligi": "Unit of measure", "Barkod": "Barcode",
      "Barkod Skaneri": "Barcode scanner", "Barkod Skanerlash": "Barcode scanning",
      "Kamera Ochish": "Open camera", "Qo'lda Kiritish": "Enter manually",
      "Rasmga olish (kamera)": "Capture (camera)", "Suratga olish": "Take a photo",

      "Dona": "Pcs", "Kilogram": "Kilogram", "Litr": "Litre", "Metr": "Metre",
      "Quti": "Box", "Tur": "Type", "Jami tur": "Total types",

      "Ichimliklar": "Drinks", "Gazaklar": "Snacks", "Shirinliklar": "Sweets",
      "Sut mahsulotlari": "Dairy products", "Go'sht mahsulotlari": "Meat products",
      "Baliq mahsulotlari": "Fish products", "Non mahsulotlari": "Bakery products",
      "Meva va sabzavot": "Fruits & vegetables", "Un va yorma": "Flour & grains",
      "Un va yorma mahsulotlari": "Flour & grains", "Sabzavotlar": "Vegetables", "Mevalar": "Fruits",
      "Yog' mahsulotlari": "Oil products", "Konserva": "Canned goods",
      "Makaron": "Pasta", "Choy va qahva": "Tea & coffee", "Ziravorlar": "Spices",
      "Tuxum": "Eggs", "Muzlatilgan": "Frozen", "Gigiyena": "Hygiene",
      "Maishiy kimyo": "Household chemicals", "Bolalar mahsulotlari": "Baby products",
      "Hayvon ozuqasi": "Animal feed", "Hayvonlar uchun": "For animals",
      "Tamaki": "Tobacco",

      "Buyurtma berish": "Place order", "Buyurtma Tarkibi": "Order contents",
      "Buyurtma yo'q": "No orders", "Hali buyurtma bermagansiz": "You haven't ordered yet",
      "Holat": "Status", "Holat tarixi": "Status history", "Sana": "Date",
      "Sana va Vaqt": "Date & time", "Kutilmoqda": "Pending", "Kutilayotgan": "Pending",
      "Tasdiqlangan": "Confirmed", "Tayyorlanmoqda": "Preparing", "Yarim tayyor": "Half ready",
      "Yo'lda": "In transit", "Yetkazildi": "Delivered", "Yakunlandi": "Completed",
      "Bekor qilindi": "Cancelled", "Rad etildi": "Rejected", "Qabul qilindi": "Accepted",
      "To'langan": "Paid", "To'lanmagan": "Unpaid", "Bosqich": "Stage",

      "So'rov": "Request", "So'rovlar": "Requests", "Mening So'rovlarim": "My requests",
      "Yetkazuvchi So'rovlari": "Supplier requests", "So'rov rad etildi": "Request rejected",
      "So'rovingiz kutilmoqda": "Your request is pending", "Ruxsat yo'q": "No access",
      "Sotuvchilarni Boshqarish": "Manage sellers", "Sotuvchilar yo'q": "No sellers",
      "Biriktirilmagan": "Unassigned",

      "Soliq Hisoblash": "Tax calculation", "Soliq Stavkasi": "Tax rate",
      "Soliq va hisobot": "Tax & reporting", "Formula:": "Formula:",

      "Jo'natma yaratish": "Create dispatch", "Jo'natma yo'q": "No dispatches",
      "Jo'natmalar": "Dispatches", "Jo'natmalar Ro'yxati": "Dispatch list",
      "Jami Jo'natmalar": "Total dispatches", "Jo'natmalar soni": "Dispatch count",
      "Jo'natiladigan soni": "Quantity to dispatch", "Yetkazuvchilar Ro'yxati": "Supplier list",
      "Yetkazuvchi yo'q": "No suppliers", "Yetkazuvchi (ixtiyoriy)": "Supplier (optional)",
      "Zavodga Buyurtma": "Order to factory", "Zavodga buyurtma": "Order to factory",
      "Zavod Tanlang": "Select a factory", "Mahsulot yetkazish": "Product delivery",
      "Marshrut": "Route", "Masofa va yo'l uchun": "For distance and travel",
      "Xarita": "Map", "Yandex Xarita": "Yandex Maps",
      "Xarita ilovasini tanlang": "Choose a map app",
      "Marshrutni qayerda ochamiz?": "Where to open the route?",

      "Chatlar yo'q": "No chats", "Zavod bilan chat": "Chat with factory",
      "Yetkazuvchi bilan chat": "Chat with supplier", "Yetkazib berish va chat": "Delivery & chat",
      "Hech kim topilmadi": "No one found",
      "Boshqa foydalanuvchi bilan chat boshlash uchun ularning ID sini kiriting":
        "Enter a user's ID to start a chat",

      "Reyting": "Rating", "Sharh qoldirmoqchimisiz?": "Want to leave a review?",
      "Hozircha sharhlar yo'q": "No reviews yet", "Tasdiqlangan xaridor": "Verified buyer",
      "Baho berish uchun avval xarid qiling": "Make a purchase first to rate",
      "Baho va sharh qoldirish uchun tizimga kiring": "Log in to leave a rating and review",
      "Buyurtma berish uchun tizimga kiring": "Log in to place an order",

      "Ma'lumot": "Info", "Ma'lumotlar": "Details", "Mavzu": "Theme",
      "Mavzuni almashtirish": "Switch theme", "O'chiq": "Off", "Yoqilgan": "On",
      "Barcha Qarzlar": "All debts", "Qarzlar": "Debts", "Bugun — soat bo'yicha:": "Today — by hour:",
      "Nima qilamiz": "What we do", "Sizdan": "From you",

      "Savat bo'sh": "Cart is empty", "Bu kategoriyada hozircha mahsulot yo'q": "No products in this category yet",
      "Boshqa so'z bilan qidiring": "Try a different search",
      "Sahifa topilmadi": "Page not found", "Xatolik yuz berdi": "An error occurred",
      "Bosh sahifaga qaytish": "Back to home",
      "Uzr, sizda bu bo'limga kirish huquqi yo'q.": "Sorry, you don't have access to this section.",
      "Uzr, hozircha bu qism mavjud emas yoki nimadir xato yuz berdi.":
        "Sorry, this section is unavailable or an error occurred.",

      "Biznes boshqaruv tizimi": "Business management system",
      "Asoschi": "Founder", "GPS yoqish": "Enable GPS", "GPS yoqing": "Enable GPS",
      "GPS orqali eng yaqin dokondan toping": "Find the nearest store via GPS",
    }
  };

  /* ── Bayroqlar (SVG) — Windows'da emoji ishlamaydi, shuning uchun SVG ── */
  const FLAGS = {
    uz: '<svg viewBox="0 0 30 20" width="22" height="15" aria-hidden="true"><rect width="30" height="20" rx="2" fill="#fff"/><rect width="30" height="6.2" y="0" fill="#1eb0e6"/><rect width="30" height="6.2" y="13.8" fill="#12a04a"/><rect width="30" height="0.7" y="6.2" fill="#ce1126"/><rect width="30" height="0.7" y="13.1" fill="#ce1126"/><circle cx="6" cy="3.1" r="1.9" fill="#fff"/><circle cx="6.9" cy="3.1" r="1.9" fill="#1eb0e6"/></svg>',
    ru: '<svg viewBox="0 0 30 20" width="22" height="15" aria-hidden="true"><rect width="30" height="20" rx="2" fill="#fff"/><rect width="30" height="6.67" y="6.67" fill="#0039a6"/><rect width="30" height="6.66" y="13.34" fill="#d52b1e"/></svg>',
    en: '<svg viewBox="0 0 60 30" width="22" height="15" aria-hidden="true"><clipPath id="uk-r"><rect width="60" height="30" rx="3"/></clipPath><g clip-path="url(#uk-r)"><rect width="60" height="30" fill="#012169"/><path d="M0,0 60,30 M60,0 0,30" stroke="#fff" stroke-width="6"/><path d="M0,0 60,30 M60,0 0,30" clip-path="url(#uk-t)" stroke="#c8102e" stroke-width="4"/><clipPath id="uk-t"><path d="M30,15 60,0 60,30 30,15 60,30 0,30 30,15 0,30 0,0 30,15 0,0 60,0z"/></clipPath><path d="M30,0 v30 M0,15 h60" stroke="#fff" stroke-width="10"/><path d="M30,0 v30 M0,15 h60" stroke="#c8102e" stroke-width="6"/></g></svg>'
  };

  const LANGS = [
    { code: "uz", label: "O'zbek" },
    { code: "ru", label: "Русский" },
    { code: "en", label: "English" }
  ];

  const STORAGE_KEY = "savdoyim-lang";
  function getLang() { return localStorage.getItem(STORAGE_KEY) || "uz"; }
  function setLang(l) { localStorage.setItem(STORAGE_KEY, l); }

  /* ── Matn tugunlarini yig'ish va asl (uz) matnni saqlash ── */
  const SKIP_TAGS = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEXTAREA", "CODE", "PRE"]);
  let textNodes = [];   // { node, orig }
  let attrNodes = [];   // { el, attr, orig }

  function collectNodes() {
    textNodes = [];
    attrNodes = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        let p = node.parentElement;
        while (p) {
          if (SKIP_TAGS.has(p.tagName) || p.hasAttribute("data-i18n-skip")) return NodeFilter.FILTER_REJECT;
          p = p.parentElement;
        }
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    let n;
    while ((n = walker.nextNode())) textNodes.push({ node: n, orig: n.nodeValue });

    // placeholder + title atributlari
    document.querySelectorAll("[placeholder]").forEach(el => {
      if (el.closest("[data-i18n-skip]")) return;
      attrNodes.push({ el, attr: "placeholder", orig: el.getAttribute("placeholder") });
    });
    document.querySelectorAll("[title]").forEach(el => {
      if (el.closest("[data-i18n-skip]")) return;
      attrNodes.push({ el, attr: "title", orig: el.getAttribute("title") });
    });
    document.querySelectorAll("[aria-label]").forEach(el => {
      if (el.closest("[data-i18n-skip]")) return;
      attrNodes.push({ el, attr: "aria-label", orig: el.getAttribute("aria-label") });
    });
    // submit/button qiymatlari
    document.querySelectorAll("input[type=submit], input[type=button]").forEach(el => {
      if (el.closest("[data-i18n-skip]")) return;
      attrNodes.push({ el, attr: "value", orig: el.value });
    });
  }

  function lookup(table, core) {
    // 1) to'g'ridan-to'g'ri
    if (Object.prototype.hasOwnProperty.call(table, core)) return table[core];
    // 2) oldidagi emoji/belgi (harf bo'lmagan) prefiksni ajratib qolganini tarjima qilamiz
    //    masalan "🥤 Ichimliklar" -> prefiks "🥤 " + "Ichimliklar"
    const pm = core.match(/^([^\p{L}\p{N}]+)([\p{L}\p{N}][\s\S]*)$/u);
    if (pm) {
      const inner = lookup(table, pm[2].trim());
      if (inner != null) return pm[1] + inner;
    }
    // 3) oxiridagi "...", ":", "…" belgilarini ajratib qolganini tarjima qilamiz
    const sm = core.match(/^([\s\S]*?)([.…:]+)$/);
    if (sm && sm[1]) {
      const inner = lookup(table, sm[1]);
      if (inner != null) return inner + sm[2];
    }
    return null;
  }

  function translateString(str, lang) {
    if (lang === "uz") return str;
    const table = DICT[lang];
    if (!table) return str;
    // Bo'shliqlarni saqlagan holda faqat o'rtadagi matnni tarjima qilamiz
    const m = str.match(/^(\s*)([\s\S]*?)(\s*)$/);
    const lead = m[1], core = m[2], trail = m[3];
    const hit = lookup(table, core);
    return hit != null ? lead + hit + trail : str;
  }

  function apply(lang) {
    textNodes.forEach(t => {
      const out = translateString(t.orig, lang);
      if (t.node.nodeValue !== out) t.node.nodeValue = out;
    });
    attrNodes.forEach(a => {
      const out = translateString(a.orig, lang);
      if (a.el.getAttribute(a.attr) !== out) {
        if (a.attr === "value") a.el.value = out;
        else a.el.setAttribute(a.attr, out);
      }
    });
    document.documentElement.setAttribute("lang", lang);
    updateSwitcherUI(lang);
  }

  /* ── Til almashtirgich (bayroqli) UI ── */
  let switcherEl = null;

  function buildSwitcher() {
    const wrap = document.createElement("div");
    wrap.className = "lang-switch";
    wrap.setAttribute("data-i18n-skip", "");
    wrap.innerHTML = LANGS.map(l =>
      `<button type="button" class="lang-btn" data-lang="${l.code}" title="${l.label}" aria-label="${l.label}">
         <span class="lang-flag">${FLAGS[l.code]}</span>
         <span class="lang-code">${l.code.toUpperCase()}</span>
       </button>`
    ).join("");
    wrap.addEventListener("click", e => {
      const btn = e.target.closest(".lang-btn");
      if (!btn) return;
      const lang = btn.getAttribute("data-lang");
      setLang(lang);
      apply(lang);
    });
    return wrap;
  }

  function updateSwitcherUI(lang) {
    if (!switcherEl) return;
    switcherEl.querySelectorAll(".lang-btn").forEach(b => {
      b.classList.toggle("active", b.getAttribute("data-lang") === lang);
    });
  }

  function mountSwitcher() {
    switcherEl = buildSwitcher();
    const right = document.querySelector(".topbar-right");
    if (right) {
      right.insertBefore(switcherEl, right.firstChild);
    } else {
      // topbar yo'q sahifalarda (login, register, ...) — o'ng yuqoriga qo'yamiz
      switcherEl.classList.add("lang-switch-floating");
      document.body.appendChild(switcherEl);
    }
  }

  function init() {
    collectNodes();
    mountSwitcher();
    apply(getLang());
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Boshqa skriptlar dinamik matn qo'shsa qayta qo'llash uchun
  window.SavdoyimI18n = {
    refresh() { collectNodes(); apply(getLang()); },
    setLang(l) { setLang(l); apply(l); },
    t(str) { return translateString(str, getLang()); }
  };
})();
