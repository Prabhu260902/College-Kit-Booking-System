Frontend:
	- We need 2 roles: Admin / User
Admin Actions:
	- Show all bookings
	- Approve or reject pending bookings with a comment
	- After approval, show an option to hand over the kit
	- Before handover, check:
		- Booking is approved
		- Current time is within the booking period
		- All kit items are working
		- Kit is not currently with another user
		- The 15-minute inspection gap is completed
	- After handover, change handover_state to HANDED_OVER
	- After handover, show an option to receive the kit
	- While receiving, record missing or damaged items
	- Change handover_state to RECEIVED
	- If anything is missing or damaged:
		- Update the corresponding kit item to false
		- Immediately update affected upcoming bookings to status 3
		- Show a warning to affected users
	- Provide an option to update kit condition after recovery, repair, or replacement
	- Once the kit is working, admin can approve or reject affected bookings manually
User Actions:
	- Show available time ranges for the next 3 days
	- Next 3 days means the next 72 hours from the current time
	- Allow booking within an available time range
	- Both start_time and end_time must be within the next 72 hours
	- Minimum booking duration is 2 hours — hard rule
	- Keep a 15-minute gap between bookings
	- Show only the logged-in user’s bookings
	- After booking, show four statuses:
		- Pending
		- Approved
		- Rejected
		- Kit unavailable
	- For Kit unavailable, show:
		- “Sorry for the inconvenience. Equipment from the previous booking is missing or damaged. Your booking cannot proceed until the admin resolves the issue.”
Booking Rules:
	- Pending and approved bookings reserve their time slots
	- Rejected bookings release their time slots
	- Kit unavailable bookings retain their slots until the admin approves or rejects them
	- Do not allow overlapping bookings for the same kit
	- If two users request the same slot together, only one booking should succeed
	- Do not allow new bookings if any kit item is false
	- Do not allow approval after the booking start time has passed
	- After receiving the kit, allow the next handover only after 15 minutes from the actual received time
Technology:
	- Use Django for backend and frontend
	- Use Django templates, HTML, CSS, and basic JavaScript
	- Use MongoDB for the database
	- Use JWT authentication
	- No deployment needed; run locally
Authentication:
	- Admin:
		- user_name: Admin
		- password: 1234
		- role: ADMIN
	- User1:
		- user_name: User1
		- password: 1234
		- role: USER
	- User2:
		- user_name: User2
		- password: 1234
		- role: USER
	- No signup for now
	- Keep these as predefined demo accounts
	- Store passwords as hashes
	- Validate JWT signature and expiry on protected requests
	- Get the username and role from the authenticated account
	- Users cannot access admin APIs
	- Users cannot view another user’s booking details
	- Users cannot submit or update booking status, handover state, or kit condition
Models:
- Model Name: kits
- In future, add new kits to this collection
- Model structure:

{
    "id": "1",
    "name": "media_kit",
    "camera": true,
    "mic": true,
    "tripod": true,
    "current_booking_id": null,
    "ready_after": null
}

- true indicates the item is present and working
- false indicates the item is missing or damaged
- Check these fields during new booking, approval, and handover
- current_booking_id stores the booking currently holding the kit
- Set current_booking_id during handover
- Clear current_booking_id when receiving the kit
- ready_after stores the earliest time the kit can be handed over
- Set ready_after to received time + 15 minutes
- After repair, recovery, or replacement, update ready_after to at least that time + 15 minutes

- Model Name: Bookings
- Store all bookings in this collection
- Model structure:

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

- kit_id identifies the booked kit
- name comes from the authenticated user
- status:
	- 0 means pending
	- 1 means approved
	- 2 means rejected
	- 3 means kit unavailable
- handover_state:
	- NOT_HANDED_OVER
	- HANDED_OVER
	- RECEIVED
- Booking status and handover state are separate
- When something happens to a kit, update affected bookings where:
	- kit_id matches the affected kit
	- status is 0 or 1
	- handover_state is NOT_HANDED_OVER
	- end_time is greater than the current time
- Set status to 3 and add a proper comment
- Do not change already handed-over or received bookings

Cron:
	- Write one cron that runs every minute
	- First:
		- Find pending bookings where start_time is less than or equal to the current time
		- Change status from 0 to 2
		- Add comment:
			- “Rejected automatically because approval was not completed before the start time.”
	- Then:
		- Check kits for missing or damaged items
		- Update affected bookings with status 0 or 1 to status 3
		- Consider only bookings with end_time greater than the current time
		- Consider only bookings not yet handed over
		- Add a comment identifying the unavailable items
	- Update bookings immediately when admin records an issue; cron acts as a backup
	- Running the cron again should not duplicate records or change completed bookings
- Model Name: handover
- Store kit return details in this collection
- Keep one return record per booking
- Model structure:

{
    "id": "1",
    "booking_id": "1",
    "received_at": "timestamp",
    "all_returned": true,
    "items": [],
    "compensation": false,
    "comment": ""
}

- all_returned means all items returned in working condition
- items is empty when all_returned is true
- Otherwise, store missing or damaged item keys:
	- camera
	- mic
	- tripod
- Example:

{
    "id": "1",
    "booking_id": "1",
    "received_at": "timestamp",
    "all_returned": false,
    "items": ["tripod"],
    "compensation": false,
    "comment": "Tripod was missing when the kit was received."
}

- compensation becomes true when the responsible user provides money or a working replacement for the affected items
- Receiving money does not make the kit usable
- Set the kit item to true only after recovery, repair, or a working replacement
- Keep the original return record unchanged; record the resolution in its comment
- Repeating a receive action must not create another return record or change a newer booking’s kit state

Time Handling:
	- Store timestamps in UTC
	- Show dates and times in IST
	- Validate booking times and all business rules on the backend