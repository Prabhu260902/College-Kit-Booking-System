import json
from functools import wraps
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from .services import AuthService, BookingService, KitService

def require_auth(roles=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JsonResponse({"error": "Unauthorized"}, status=401)
            token = auth_header.split(" ")[1]
            user = AuthService.validate_token(token)
            if not user:
                return JsonResponse({"error": "Invalid or expired token"}, status=401)
            if roles and user["role"] not in roles:
                return JsonResponse({"error": "Forbidden"}, status=403)
            request.user_info = user
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def index_view(request):
    return render(request, "index.html")

@csrf_exempt
def login_api(request):
    if request.method == "POST":
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")
        print(username, password)
        token = AuthService.login(username, password)
        if token:
            user = AuthService.validate_token(token)
            return JsonResponse({"token": token, "role": user["role"]})
        return JsonResponse({"error": "Invalid credentials"}, status=401)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@require_auth(roles=["USER", "ADMIN"])
def get_slots_api(request):
    if request.method == "GET":
        kit_id = request.GET.get("kit_id", "1")
        slots = BookingService.get_available_slots(kit_id)
        # return simplified view
        for s in slots:
            s.pop("_id", None)
        return JsonResponse({"bookings": slots})
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@require_auth(roles=["USER"])
def create_booking_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            b = BookingService.create_booking(
                user=request.user_info,
                kit_id=data.get("kit_id", "1"),
                start_timestamp=data["start_time"],
                end_timestamp=data["end_time"]
            )
            b.pop("_id", None)
            return JsonResponse(b)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@require_auth(roles=["USER"])
def my_bookings_api(request):
    if request.method == "GET":
        from .db import db
        bookings = list(db.bookings.find({"name": request.user_info["username"]}))
        for b in bookings:
            b.pop("_id", None)
        return JsonResponse({"bookings": bookings})
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@require_auth(roles=["ADMIN"])
def admin_bookings_api(request):
    if request.method == "GET":
        from .db import db
        bookings = list(db.bookings.find())
        for b in bookings:
            b.pop("_id", None)
        return JsonResponse({"bookings": bookings})
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@require_auth(roles=["ADMIN"])
def admin_approve_api(request, id):
    if request.method == "POST":
        try:
            BookingService.approve_booking(id)
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@require_auth(roles=["ADMIN"])
def admin_reject_api(request, id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            BookingService.reject_booking(id, data.get("comment", ""))
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@require_auth(roles=["ADMIN"])
def admin_handover_api(request, id):
    if request.method == "POST":
        try:
            KitService.handover_kit(id)
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@require_auth(roles=["ADMIN"])
def admin_receive_api(request, id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            KitService.receive_kit(id, data.get("items", []), data.get("comment", ""))
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@require_auth(roles=["ADMIN"])
def admin_condition_api(request, id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            KitService.update_condition(id, data)
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)
