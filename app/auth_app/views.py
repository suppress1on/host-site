# host-site/app/auth_app/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from .forms import CustomUserCreationForm, CustomAuthenticationForm, TwoFACodeForm
from .models import CustomUser

# --- Вспомогательная функция для отправки 2FA кода ---
def send_two_fa_code_email(request, user):
    code = user.generate_two_fa_code()
    send_mail(
        'Ваш код подтверждения для Host Site',
        f'Ваш 6-значный код подтверждения: {code}\n'
        'Этот код действителен в течение 5 минут. Не сообщайте его никому.',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    messages.info(request, f'Код подтверждения отправлен на {user.email}. Проверьте почту.')


# --- REGISTRATION VIEW ---
def register_view(request):
    if request.user.is_authenticated:
        return redirect('main_app:home')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_email_verified = False # При регистрации email не подтвержден
            user.save()

            # Отправляем 2FA код сразу после регистрации
            send_two_fa_code_email(request, user)

            messages.success(request, 'Аккаунт успешно создан! Для завершения регистрации, пожалуйста, введите код из письма.')
            # Перенаправляем на страницу ввода 2FA кода, передавая ID пользователя
            return redirect('auth:two_fa_verification_with_id', user_id=user.pk)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Ошибка в поле '{field}': {error}")
    else:
        form = CustomUserCreationForm()
    return render(request, 'auth_app/register.html', {'form': form})


# --- LOGIN VIEW ---
def login_view(request):
    if request.user.is_authenticated:
        return redirect('main_app:home')

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Аутентификация по логину/паролю прошла. Теперь запрашиваем 2FA.
                send_two_fa_code_email(request, user)
                messages.info(request, 'На вашу почту отправлен код для входа. Пожалуйста, введите его.')
                # Сохраняем user.pk в сессии, чтобы знать, кого верифицировать
                request.session['unverified_user_id'] = user.pk
                return redirect('auth:two_fa_verification_with_id', user_id=user.pk)
            else:
                messages.error(request, "Неверное имя пользователя или пароль.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Ошибка в поле '{field}': {error}")
    else:
        form = CustomAuthenticationForm()
    return render(request, 'auth_app/login.html', {'form': form})


# --- 2FA VERIFICATION VIEW (Единая для регистрации и входа) ---
def two_fa_verification_view(request, user_id):
    # Если пользователь уже полностью аутентифицирован в сессии, он не должен быть на этой странице
    if request.user.is_authenticated:
        messages.info(request, 'Вы уже вошли в систему.')
        return redirect('main_app:home')

    try:
        user = CustomUser.objects.get(pk=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Пользователь не найден.')
        return redirect('auth:register')

    # --- ОТЛАДОЧНЫЕ ВЫВОДЫ ---
    print(f"\n--- DEBUG 2FA VERIFICATION for user_id: {user_id} ---")
    print(f"User email: {user.email}")
    print(f"user.is_email_verified: {user.is_email_verified}")
    print(f"request.session.get('unverified_user_id'): {request.session.get('unverified_user_id')}")
    print(f"Current session keys: {list(request.session.keys())}")

    is_allowed_via_registration = not user.is_email_verified and request.session.get('unverified_user_id') is None
    is_allowed_via_login = request.session.get('unverified_user_id') == user.pk

    print(f"is_allowed_via_registration: {is_allowed_via_registration}")
    print(f"is_allowed_via_login: {is_allowed_via_login}")

    if not (is_allowed_via_registration or is_allowed_via_login):
        messages.error(request, 'Для доступа к этой странице необходимо пройти регистрацию или вход.')
        print("DEBUG 2FA: Redirecting to login because not allowed.")
        return redirect('auth:login')


    if request.method == 'POST':
        form = TwoFACodeForm(request.POST)
        if form.is_valid():
            entered_code = form.cleaned_data['code']

            if (user.two_fa_code == entered_code and
                    user.two_fa_code_expires and
                    user.two_fa_code_expires > timezone.now()):

                user.two_fa_code = None
                user.two_fa_code_expires = None
                user.is_email_verified = True
                user.save()

                login(request, user)
                messages.success(request, 'Код успешно подтвержден! Вы вошли в аккаунт.')
                if 'unverified_user_id' in request.session:
                    del request.session['unverified_user_id']
                return redirect('main_app:home')
            else:
                messages.error(request, 'Неверный или просроченный код подтверждения.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Ошибка в поле '{field}': {error}")
    else: # GET request
        form = TwoFACodeForm()

    return render(request, 'auth_app/two_fa_verification.html', {'form': form, 'user': user})


# --- PROFILE VIEW ---
@login_required
def profile_view(request):
    if not request.user.is_email_verified:
        messages.warning(request, 'Ваш адрес электронной почты не подтвержден. Пожалуйста, подтвердите его.')
        send_two_fa_code_email(request, request.user)
        return redirect('auth:two_fa_verification_with_id', user_id=request.user.pk)

    return render(request, 'auth_app/profile.html', {'user': request.user})


# --- LOGOUT VIEW ---
def logout_view(request):
    logout(request)
    if 'unverified_user_id' in request.session:
        del request.session['unverified_user_id']
    messages.info(request, "Вы успешно вышли из аккаунта.")
    return redirect('auth:login')
