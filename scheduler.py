from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

# =========================================================
# EMAIL RETRY JOB (WITH ANALYTICS + DEAD LETTER SUPPORT)
# =========================================================
def retry_failed_emails_job(app, db, EmailQueue, Message, mail, load_admin_mail):

    with app.app_context():

        failed_items = EmailQueue.query.filter(
            EmailQueue.status == "failed",
            EmailQueue.attempts < 5
        ).all()

        print(
            f"[EMAIL RETRY RUN] {datetime.utcnow()} | COUNT: {len(failed_items)}"
        )

        for item in failed_items:

            print(
                f"Retrying email ID {item.id} | attempt {item.attempts}"
            )

            try:
                msg = Message(
                    subject=item.subject,
                    recipients=[item.recipient],
                    body=item.body
                )

                load_admin_mail()
                mail.send(msg)

                item.status = "sent"
                item.sent_at = datetime.utcnow()
                item.error = None

            except Exception as e:

                item.attempts += 1
                item.error = str(e)

                # =====================================
                # DEAD LETTER HANDLING (IMPORTANT)
                # =====================================
                if item.attempts >= 5:
                    item.status = "dead"

            # NOTE: commit moved OUTSIDE loop (FIXED)

        db.session.commit()


# =========================================================
# MAIN SCHEDULER STARTER
# =========================================================
def start_scheduler(app, db, User, TheorySubmission, Result, Subject,
                    SubjectGroup, EmailQueue, Message, mail, load_admin_mail,
                    RECYCLE_RETENTION_DAYS ):
    

    # =====================================================
    # CLEANUP JOB
    # =====================================================
    def auto_cleanup_deleted_records():

        with app.app_context():
            try:

                cutoff = datetime.utcnow() - timedelta(days=RECYCLE_RETENTION_DAYS)
                cutoff = datetime.utcnow() - timedelta(days=RECYCLE_RETENTION_DAYS)

                print("Cleanup run:", datetime.utcnow())

                deleted_t = TheorySubmission.query.filter(
                    TheorySubmission.deleted == True,
                    TheorySubmission.deleted_at <= cutoff
                ).delete(synchronize_session=False)

                deleted_r = Result.query.filter(
                    Result.deleted == True,
                    Result.deleted_at <= cutoff
                ).delete(synchronize_session=False)

                deleted_s = Subject.query.filter(
                    Subject.deleted == True,
                    Subject.deleted_at <= cutoff
                ).delete(synchronize_session=False)

                deleted_g = SubjectGroup.query.filter(
                    SubjectGroup.deleted == True,
                    SubjectGroup.deleted_at <= cutoff
                ).delete(
                    synchronize_session=False
                )

                deleted_u = User.query.filter(
                    User.deleted == True,
                    User.deleted_at <= cutoff
                ).delete(
                    synchronize_session=False
                )            

                db.session.commit()

                print(
                    f"""
                Cleanup completed

                Theory deleted : {deleted_t}
                Results deleted: {deleted_r}
                Subjects deleted: {deleted_s}
                Groups deleted : {deleted_g}
                Users deleted  : {deleted_u}
                """
                )
            except Exception as e:

                db.session.rollback()

                print("Cleanup failed:", e)

    # =====================================================
    # AUTO DISABLE EXPIRED RETAKE PERMISSIONS
    # =====================================================
    def auto_disable_expired_retakes():

        with app.app_context():

            try:

                cutoff = datetime.utcnow() - timedelta(hours=24)

                # Disable expired Result retakes
                expired_results = (
                    Result.query
                    .filter(
                        Result.can_retake == True,
                        Result.retake_granted_at != None,
                        Result.retake_granted_at <= cutoff
                    )
                    .all()
                )

                for r in expired_results:
                    r.can_retake = False
                    print(
                        f"Disabled retake for Result ID {r.id} "
                        f"(User {r.user_id}, Subject {r.subject_id})"
                    )                    

                # Disable expired Theory retakes
                expired_theory = (
                    TheorySubmission.query
                    .filter(
                        TheorySubmission.can_retake == True,
                        TheorySubmission.retake_granted_at != None,
                        TheorySubmission.retake_granted_at <= cutoff
                    )
                    .all()
                )

                for t in expired_theory:
                    t.can_retake = False
                    print(
                        f"Disabled retake for TheorySubmission ID {t.id} "
                        f"(User {t.user_id}, Subject {t.subject_id})"
                    )                    

                db.session.commit()

            except Exception as e:

                db.session.rollback()

                print("Auto disable retakes failed:", e)                

    # =====================================================
    # FIRST CLEANUP RUN
    # =====================================================
    scheduler.add_job(
        auto_cleanup_deleted_records,
        trigger='date',
        run_date=datetime.utcnow() + timedelta(minutes=10),
        id='cleanup_first_run',
        replace_existing=True
    )

    # =====================================================
    # RECURRING CLEANUP
    # =====================================================
    scheduler.add_job(
        auto_cleanup_deleted_records,
        trigger='interval',
        hours=12,
        id='cleanup_recurring',
        replace_existing=True
    )

    # =====================================================
    # EMAIL RETRY SYSTEM (EVERY 5 MINUTES)
    # =====================================================
    scheduler.add_job(
        retry_failed_emails_job,
        trigger='interval',
        minutes=5,
        id='email_retry_job',
        replace_existing=True,
        args=[app, db, EmailQueue, Message, mail, load_admin_mail]
    )

    print("✅ Scheduler started")
    print("✅ Cleanup job registered")
    print("✅ Email retry job registered")

    # =====================================================
    # AUTO DISABLE RETAKE PERMISSIONS
    # =====================================================
    scheduler.add_job(
        auto_disable_expired_retakes,
        trigger="interval",
        minutes=10,
        id="auto_disable_retakes",
        replace_existing=True
    )

    print("✅ Retake expiry job registered")
    

##    scheduler.start()
    if not scheduler.running:
        scheduler.start()    
