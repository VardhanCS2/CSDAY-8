from app.tasks.background_tasks import send_notification


result = send_notification.delay(
    "user@example.com"
)


print("Task ID:", result.id)