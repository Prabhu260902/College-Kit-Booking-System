import jwt
import hashlib
from datetime import datetime, timedelta
import uuid
from django.conf import settings
from .db import db

class AuthService:
    @staticmethod
    def login(username, password):
        user = db.users.find_one({"username": username})
        if not user:
            return None
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user["password_hash"] == password_hash:
            payload = {
                "username": username,
                "role": user["role"],
                "exp": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRY_HOURS)
            }
            token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
            return token
        return None

    @staticmethod
    def validate_token(token):
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

class BookingService:
    @staticmethod
    def get_available_slots(kit_id):
        # We find ranges of busy times. Everything else in the next 72 hours is available.
        # But actually, the prompt says "View available slots, create bookings" 
        # So we can just fetch existing approved or pending bookings in next 72h.
        now = datetime.utcnow()
        end_horizon = now + timedelta(hours=72)
        bookings = db.bookings.find({
            "kit_id": kit_id,
            "status": {"$in": [0, 1, 3]},
            "end_time": {"$gt": now.timestamp()},
            "start_time": {"$lt": end_horizon.timestamp()}
        })
        
        # A simpler approach: return the busy blocks, and frontend calculates available
        # or we calculate available here. Let's return the list of bookings (busy blocks)
        return list(bookings)

    @staticmethod
    def create_booking(user, kit_id, start_timestamp, end_timestamp):
        now = datetime.utcnow().timestamp()
        if start_timestamp <= now:
            raise ValueError("The booking must start in the future.")
        if end_timestamp <= start_timestamp:
            raise ValueError("End time must be after the start time.")
        if end_timestamp - start_timestamp < 7200:
            raise ValueError("Duration must be at least 2 hours.")
        if end_timestamp > now + 72 * 3600:
            raise ValueError("Start and end must fall within the next 72 hours.")
            
        kit = db.kits.find_one({"id": kit_id})
        if not kit:
            raise ValueError("Kit not found")
        if not (kit.get("camera") and kit.get("mic") and kit.get("tripod")):
            raise ValueError("Cannot book: some kit items are missing/damaged.")

        # Check overlapping
        start_with_gap = start_timestamp - 900
        end_with_gap = end_timestamp + 900
        
        overlap = db.bookings.find_one({
            "kit_id": kit_id,
            "status": {"$in": [0, 1, 3]},
            "$or": [
                {"start_time": {"$lt": end_with_gap}, "end_time": {"$gt": start_with_gap}}
            ]
        })
        if overlap:
            raise ValueError("Overlapping booking or insufficient 15-minute gap.")

        booking_id = str(uuid.uuid4())
        booking = {
            "id": booking_id,
            "kit_id": kit_id,
            "name": user["username"],
            "start_time": start_timestamp,
            "end_time": end_timestamp,
            "status": 0,
            "handover_state": "NOT_HANDED_OVER",
            "comment": ""
        }
        db.bookings.insert_one(booking)
        return booking

    @staticmethod
    def approve_booking(booking_id):
        booking = db.bookings.find_one({"id": booking_id})
        if not booking:
            raise ValueError("Booking not found")
        # if booking["start_time"] <= datetime.utcnow().timestamp():
        #     raise ValueError("Cannot approve booking that has already started.")
            
        kit = db.kits.find_one({"id": booking["kit_id"]})
        if not (kit.get("camera") and kit.get("mic") and kit.get("tripod")):
            raise ValueError("Cannot approve: equipment is not fully working.")

        db.bookings.update_one({"id": booking_id}, {"$set": {"status": 1}})

    @staticmethod
    def reject_booking(booking_id, comment):
        if not comment:
            raise ValueError("Rejection requires a comment.")
        booking = db.bookings.find_one({"id": booking_id})
        if not booking:
            raise ValueError("Booking not found")
        if booking["handover_state"] in ["HANDED_OVER", "RECEIVED"]:
            raise ValueError("Cannot reject handed-over or received booking.")
            
        db.bookings.update_one({"id": booking_id}, {"$set": {"status": 2, "comment": comment}})

class KitService:
    @staticmethod
    def handover_kit(booking_id):
        booking = db.bookings.find_one({"id": booking_id})
        if not booking:
            raise ValueError("Booking not found")
        if booking["status"] != 1:
            raise ValueError("Booking is not approved.")
        if booking["handover_state"] != "NOT_HANDED_OVER":
            raise ValueError("Handover state is not NOT_HANDED_OVER.")
            
        now = datetime.utcnow().timestamp()
        if not (booking["start_time"] <= now <= booking["end_time"]):
            raise ValueError("Current time is not within the booking period.")
            
        kit = db.kits.find_one({"id": booking["kit_id"]})
        if not (kit.get("camera") and kit.get("mic") and kit.get("tripod")):
            raise ValueError("Not all kit items are working.")
        if kit.get("current_booking_id"):
            raise ValueError("Kit is already held by another booking.")
        if kit.get("ready_after") and now < kit["ready_after"]:
            raise ValueError("Kit is not ready for handover yet.")

        db.bookings.update_one({"id": booking_id}, {"$set": {"handover_state": "HANDED_OVER"}})
        db.kits.update_one({"id": booking["kit_id"]}, {"$set": {"current_booking_id": booking_id}})

    @staticmethod
    def receive_kit(booking_id, items_missing_or_damaged, comment):
        booking = db.bookings.find_one({"id": booking_id})
        if not booking:
            raise ValueError("Booking not found")
        if booking["handover_state"] != "HANDED_OVER":
            raise ValueError("Booking is not in HANDED_OVER state.")
            
        kit = db.kits.find_one({"id": booking["kit_id"]})
        if kit.get("current_booking_id") != booking_id:
            raise ValueError("This booking does not currently hold the kit.")

        now = datetime.utcnow().timestamp()
        db.bookings.update_one({"id": booking_id}, {"$set": {"handover_state": "RECEIVED"}})
        db.kits.update_one({"id": booking["kit_id"]}, {
            "$set": {
                "current_booking_id": None,
                "ready_after": now + 900
            }
        })
        
        # update kit condition if items missing
        if items_missing_or_damaged:
            updates = {}
            for item in items_missing_or_damaged:
                if item in ["camera", "mic", "tripod"]:
                    updates[item] = False
            if updates:
                db.kits.update_one({"id": booking["kit_id"]}, {"$set": updates})

        # create return record
        record_id = str(uuid.uuid4())
        db.handover.insert_one({
            "id": record_id,
            "booking_id": booking_id,
            "received_at": now,
            "all_returned": len(items_missing_or_damaged) == 0,
            "items": items_missing_or_damaged,
            "compensation": False,
            "comment": comment
        })

        if items_missing_or_damaged:
            BookingMaintenance.mark_unavailable_bookings(booking["kit_id"])

    @staticmethod
    def update_condition(kit_id, item_states):
        db.kits.update_one({"id": kit_id}, {"$set": item_states})
        
        # Check if the kit is now fully operational
        kit = db.kits.find_one({"id": kit_id})
        if kit.get("camera") and kit.get("mic") and kit.get("tripod"):
            now = datetime.utcnow().timestamp()
            # Restore future unavailable bookings back to Pending
            db.bookings.update_many(
                {
                    "kit_id": kit_id,
                    "status": 3,
                    "end_time": {"$gt": now}
                },
                {"$set": {
                    "status": 0,
                    "comment": ""
                }}
            )

class BookingMaintenance:
    @staticmethod
    def reject_expired_pending():
        now = datetime.utcnow().timestamp()
        db.bookings.update_many(
            {"status": 0, "start_time": {"$lte": now}},
            {"$set": {
                "status": 2, 
                "comment": "Rejected automatically because approval was not completed before the start time."
            }}
        )

    @staticmethod
    def mark_unavailable_bookings(kit_id):
        now = datetime.utcnow().timestamp()
        # Immediately mark affected bookings as 3
        # kit_id matches, status 0 or 1, handover_state NOT_HANDED_OVER, end_time > now
        db.bookings.update_many(
            {
                "kit_id": kit_id,
                "status": {"$in": [0, 1]},
                "handover_state": "NOT_HANDED_OVER",
                "end_time": {"$gt": now}
            },
            {"$set": {
                "status": 3,
                "comment": "Sorry for the inconvenience. Equipment from the previous booking is missing or damaged. Please wait for an admin update."
            }}
        )
