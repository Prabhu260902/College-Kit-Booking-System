from django.core.management.base import BaseCommand
from core.services import BookingMaintenance

class Command(BaseCommand):
    help = 'Run maintenance on bookings (reject expired, mark kit unavailable)'

    def handle(self, *args, **options):
        # 1. Reject pending bookings whose start time has arrived.
        BookingMaintenance.reject_expired_pending()
        self.stdout.write("Rejected expired pending bookings.")

        # 2. Mark eligible pending or approved bookings as kit unavailable when their kit has an equipment issue.
        # This requires checking all kits for issues.
        from core.db import db
        kits_with_issues = db.kits.find({
            "$or": [
                {"camera": False},
                {"mic": False},
                {"tripod": False}
            ]
        })
        for kit in kits_with_issues:
            BookingMaintenance.mark_unavailable_bookings(kit["id"])
        
        self.stdout.write("Marked bookings as kit unavailable for problematic kits.")
