from app.celery_worker import celery_app


@celery_app.task
def send_notification(email: str):

    print(
        f"Sending notification to {email}"
    )

    return "Notification sent successfully"