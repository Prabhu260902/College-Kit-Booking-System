# Low-Level Design (LLD) - College Event Kit Booking Systems

### 1. Purpose
Build a local application where users book an equipment kit and an admin manages approval, handover, return, and equipment issues.
- **Authentication:** JWT
- **No signup or deployment** (Local usage only)

### 2. Roles and Responsibilities
| Role | Actions |
|---|---|
| **Admin** | View all bookings, approve or reject bookings, hand over kits, receive kits, record issues, update kit condition |
| **User** | View available slots, create bookings, view own bookings and status |

Passwords are stored as SHA-256 hashes. The authenticated user and role are determined via JWT on the backend.

### 3. Data Models

#### 3.1 Kit (Collection: `kits`)
```json
{
    "id": "1",
    "name": "media_kit",
    "camera": true,
    "mic": true,
    "tripod": true,
    "current_booking_id": null,
    "ready_after": null
}
```
*A kit is ready for handover when all items are working, nobody holds it, and the inspection gap has finished.*

#### 3.2 Booking (Collection: `bookings`)
```json
{
    "id": "1",
    "kit_id": "1",
    "name": "User1",
    "start_time": "timestamp",
    "end_time": "timestamp",
    "status": 0,
    "handover_state": "NOT_HANDED_OVER",
    "comment": ""
}
```
**Booking statuses:**
- `0`: Pending
- `1`: Approved
- `2`: Rejected
- `3`: Kit unavailable

**Handover states:** `NOT_HANDED_OVER`, `HANDED_OVER`, `RECEIVED`.
*(Booking status and handover state serve different purposes. An approved booking can still be waiting for handover or already returned.)*

#### 3.3 Return Record (Collection: `handover`)
```json
{
    "id": "1",
    "booking_id": "1",
    "received_at": "timestamp",
    "all_returned": false,
    "items": ["tripod"],
    "compensation": false,
    "comment": "Tripod missing at return."
}
```
*There is one return record per booking. Receiving compensation money does not make equipment working. Only recovery, repair, or a working replacement changes its kit field to true.*

### 4. Relationships
- One kit can have many bookings.
- Each booking belongs to one user and one kit.
- Each booking has zero or one return record.
- A kit can be held by only one booking at a time.

### 5. Components and Methods
- **AuthService**: `login`, `validate_token`
- **BookingService**: `get_available_slots`, `create_booking`, `approve_booking`, `reject_booking`
- **KitService**: `handover_kit`, `receive_kit`, `update_condition`
- **BookingMaintenance**: `reject_expired_pending`, `mark_unavailable_bookings`

Django views validate requests and call these services. Services enforce business rules and access MongoDB. Templates display the results.

### 6. Business Rules
**Booking**
1. The booking must start in the future.
2. Start and end must fall within the next 72 hours.
3. Duration must be at least 2 hours.
4. Keep a 15-minute gap between reservations.
5. Pending, approved, and kit-unavailable bookings hold their slots.
6. Rejected bookings release their slots.
7. Block new bookings if any kit item is false.
8. Two simultaneous requests must not create overlapping reservations.

**Approval and Rejection**
- Only admin can approve or reject.
- Approval requires working equipment and a booking that has not started.
- Rejection requires a comment.
- A handed-over or received booking cannot be rejected.

**Handover**
Allow handover only when:
- Booking is approved and NOT_HANDED_OVER.
- Current time is within the booking period.
- Every kit item is working and `current_booking_id` is empty.
- Current time has reached `ready_after`, when set.

**Receiving the Kit**
Only receive a booking whose state is HANDED_OVER.
On success:
- `booking.handover_state = RECEIVED`
- `kit.current_booking_id = null`
- `kit.ready_after = received_at + 15 minutes`
- Create the return record. Set reported missing or damaged kit fields to false.

**Equipment Issues and Recovery (UPDATED IN IMPLEMENTATION)**
Immediately mark affected bookings as `3` (Unavailable) where `kit_id` matches, `status` is `0` or `1`, `handover_state` is `NOT_HANDED_OVER`, and `end_time > now`.
Show: *"Sorry for the inconvenience. Equipment from the previous booking is missing or damaged. Please wait for an admin update."*

After repair, recovery, or replacement:
- Admin updates the item fields to true.
- *Implementation Change*: **Future bookings marked as 'Kit unavailable' will automatically be restored back to 'Pending' status and the inconvenience comment will be cleared.**
- Set `ready_after` to at least resolution time plus 15 minutes.

### 7. APIs and Permissions
- `POST /api/login/` (Public)
- `GET /api/kits/slots/` (User)
- `POST /api/bookings/` (User)
- `GET /api/bookings/mine/` (User)
- `GET /api/admin/bookings/` (Admin)
- `POST /api/admin/bookings/<id>/approve/` (Admin)
- `POST /api/admin/bookings/<id>/reject/` (Admin)
- `POST /api/admin/bookings/<id>/handover/` (Admin)
- `POST /api/admin/bookings/<id>/receive/` (Admin)
- `POST /api/admin/kits/<id>/condition/` (Admin)

### 8. Frontend Pages
- **Login**: Username and password fields. Redirect to appropriate dashboard. Includes Light/Dark mode toggle.
- **User Dashboard**: Select kit, choose times, submit booking. View reservations and status. Modern Neo-glass aesthetic.
- **Admin Dashboard**: View all reservations. Approve/Reject/Handover/Receive actions. Return checklist. Diagnostics panel.

### 9. Cron Job
Run `maintain_bookings` every minute to:
1. Reject pending bookings whose start time has arrived (automatically adds a rejection comment).
2. Mark eligible pending or approved bookings as kit unavailable when their kit has an equipment issue.

### 10. Example Flow
1. User1 books the kit from 10:00 AM to 12:00 PM.
2. Admin approves and hands it over at 10:00 AM.
3. User2 has an approved booking from 12:15 PM to 2:15 PM.
4. At 12:00 PM, admin receives User1’s kit with a missing tripod.
5. The application sets `tripod = false` and User2’s booking status to 3.
6. Admin recovers the tripod at 12:05 PM.
7. Admin updates the Kit condition to check the Tripod box. User2's booking automatically restores to Pending (Implementation Update).
8. Admin reapproves User2’s booking.
9. Handover can happen at 12:20 PM after all checks pass.
