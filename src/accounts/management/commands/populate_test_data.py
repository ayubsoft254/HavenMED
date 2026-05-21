"""
Management command: populate_test_data
========================================
Populates the database with realistic Kenyan healthcare test data.

Usage:
    python manage.py populate_test_data            # Full seed (keeps existing data)
    python manage.py populate_test_data --flush    # Wipe then re-seed
    python manage.py populate_test_data --summary  # Print credentials only (no DB writes)

What gets created
-----------------
  1 Superadmin
  5 Patients              (auto-approved)
  6 Healthcare Professionals (approved)
  2 Clinic institutions   (approved)
  1 Hospital institution  (approved)
  8 Service Types         (general medical services)
  Availability slots      (Mon-Sat for every professional)
  15+ Appointments        (varied statuses, types, priorities)
  Payments                (for paid/completed appointments)
  Consultation Notes      (for completed appointments)

All passwords are:  TestPass123!
"""

import random
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


# ── helpers ──────────────────────────────────────────────────────────────────

PASSWORD = "TestPass123!"

PATIENTS = [
    dict(first_name="Amina",   last_name="Hassan",   email="amina.hassan@test.havenmed.co.ke",   phone="+254711000001", county="nairobi",  subcounty="westlands",      dob=date(1990, 3, 15), gender="F", history="Hypertension, controlled", allergies="Penicillin"),
    dict(first_name="Brian",   last_name="Omondi",   email="brian.omondi@test.havenmed.co.ke",   phone="+254711000002", county="kiambu",   subcounty="thika_town",     dob=date(1985, 7, 22), gender="M", history="Type 2 Diabetes", allergies="None"),
    dict(first_name="Cynthia", last_name="Wanjiku",  email="cynthia.wanjiku@test.havenmed.co.ke",phone="+254711000003", county="nakuru",   subcounty="nakuru_town_east",dob=date(2000, 1, 5),  gender="F", history="Asthma",    allergies="Sulfa drugs"),
    dict(first_name="David",   last_name="Kipchoge", email="david.kipchoge@test.havenmed.co.ke", phone="+254711000004", county="nairobi",  subcounty="kasarani",       dob=date(1978, 11, 30),gender="M", history="None",       allergies="None"),
    dict(first_name="Esther",  last_name="Mwangi",   email="esther.mwangi@test.havenmed.co.ke",  phone="+254711000005", county="mombasa",  subcounty="nyali",          dob=date(1995, 6, 18), gender="F", history="Migraines",  allergies="Ibuprofen"),
]

PROFESSIONALS = [
    dict(first_name="Dr. James",   last_name="Kariuki",  email="james.kariuki@test.havenmed.co.ke",  phone="+254722000001", county="nairobi",  subcounty="westlands",   spec="general_practice",  years=12, license="KMPDU-2024-001", fee=1500, bio="Experienced GP with a focus on preventive care and chronic disease management."),
    dict(first_name="Dr. Fatuma",  last_name="Ali",      email="fatuma.ali@test.havenmed.co.ke",     phone="+254722000002", county="mombasa",  subcounty="mvita",       spec="pediatrics",        years=8,  license="KMPDU-2024-002", fee=2000, bio="Dedicated pediatrician specializing in child development and immunization."),
    dict(first_name="Dr. Kevin",   last_name="Mutua",    email="kevin.mutua@test.havenmed.co.ke",    phone="+254722000003", county="kiambu",   subcounty="kikuyu",      spec="cardiology",        years=15, license="KMPDU-2024-003", fee=3500, bio="Consultant cardiologist with expertise in non-invasive cardiac procedures."),
    dict(first_name="Dr. Grace",   last_name="Ochieng",  email="grace.ochieng@test.havenmed.co.ke",  phone="+254722000004", county="nakuru",   subcounty="nakuru_town_west", spec="gynecology", years=10, license="KMPDU-2024-004", fee=2500, bio="Specialist in maternal health, family planning, and women's wellness."),
    dict(first_name="Dr. Samuel",  last_name="Njoroge",  email="samuel.njoroge@test.havenmed.co.ke", phone="+254722000005", county="nairobi",  subcounty="kasarani",    spec="orthopedics",       years=9,  license="KMPDU-2024-005", fee=3000, bio="Orthopedic surgeon specializing in sports injuries and joint replacement."),
    dict(first_name="Dr. Lilian",  last_name="Chebet",   email="lilian.chebet@test.havenmed.co.ke",  phone="+254722000006", county="nairobi",  subcounty="roysambu",    spec="dermatology",       years=6,  license="KMPDU-2024-006", fee=2200, bio="Dermatologist with a special interest in skin cancer screening and cosmetic dermatology."),
]

CLINICS = [
    dict(first_name="",        last_name="",           email="afya.clinic@test.havenmed.co.ke",    phone="+254733000001", county="nairobi",  subcounty="westlands",    inst_name="Afya Bora Clinic",      reg="KMPDB-CLINIC-001", address="Westlands, Nairobi, off Waiyaki Way", services="General OPD, Pharmacy, Lab, Radiology", beds=None, staff=25),
    dict(first_name="",        last_name="",           email="health.point@test.havenmed.co.ke",   phone="+254733000002", county="kiambu",   subcounty="thika_town",   inst_name="HealthPoint Medical Centre", reg="KMPDB-CLINIC-002", address="Thika Town, Kiambu County, Tom Mboya St", services="General Practice, MCH, Dental, Physiotherapy", beds=None, staff=18),
]

HOSPITALS = [
    dict(first_name="",        last_name="",           email="nairobi.health@test.havenmed.co.ke", phone="+254733000003", county="nairobi",  subcounty="starehe",      inst_name="Nairobi Heights Hospital", reg="KMPDB-HOSP-001",  address="Starehe, Nairobi CBD, Hospital Rd", services="Emergency, Surgery, ICU, Maternity, Radiology, Lab, Pharmacy, Specialist Clinics", beds=150, staff=200),
]

SERVICE_TYPES = [
    dict(name="General Consultation",   desc="Standard outpatient consultation with a GP.",           price=1200, mins=30, home_fee=500, urgent_fee=300),
    dict(name="Specialist Consultation",desc="Consultation with a medical specialist.",                price=2500, mins=45, home_fee=700, urgent_fee=500),
    dict(name="Pediatric Consultation", desc="Child health consultation up to 18 years.",             price=1500, mins=30, home_fee=500, urgent_fee=300),
    dict(name="Cardiology Review",      desc="Cardiac assessment and ECG interpretation.",            price=3500, mins=60, home_fee=0,   urgent_fee=800, home=False),
    dict(name="Gynecology & Obstetrics",desc="Women's health, antenatal care, family planning.",      price=2200, mins=45, home_fee=600, urgent_fee=400),
    dict(name="Dermatology Consultation",desc="Skin, hair, and nail condition assessment.",           price=2000, mins=30, home_fee=500, urgent_fee=300),
    dict(name="Home Visit — General",   desc="Doctor visits patient at home for general care.",       price=2500, mins=60, home_fee=0,   urgent_fee=500, virtual=False, inperson=False, home_only=True),
    dict(name="Virtual Consultation",   desc="Secure online video consultation with a doctor.",       price=900,  mins=20, home_fee=0,   urgent_fee=200, home=False, inperson=False),
]

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

APPOINTMENT_SCENARIOS = [
    # (patient_idx, doctor_idx, service_idx, type,        status,      priority,   days_offset, paid)
    (0, 0, 0, "virtual",    "completed", "normal",    -14, True),
    (1, 2, 3, "in_person",  "completed", "normal",    -10, True),
    (2, 1, 2, "virtual",    "completed", "normal",    -7,  True),
    (3, 4, 1, "in_person",  "completed", "normal",    -5,  True),
    (4, 5, 5, "virtual",    "completed", "normal",    -3,  True),
    (0, 3, 4, "home_visit", "confirmed", "normal",    2,   True),
    (1, 0, 7, "virtual",    "confirmed", "normal",    3,   False),
    (2, 5, 5, "virtual",    "confirmed", "urgent",    4,   False),
    (3, 1, 2, "in_person",  "pending",   "normal",    5,   False),
    (4, 2, 3, "in_person",  "pending",   "normal",    6,   False),
    (0, 4, 1, "virtual",    "pending",   "urgent",    7,   False),
    (1, 3, 4, "home_visit", "pending",   "normal",    8,   False),
    (2, 0, 0, "virtual",    "cancelled", "normal",    -2,  False),
    (3, 5, 5, "in_person",  "no_show",   "normal",    -1,  False),
    (4, 2, 3, "in_person",  "paid",      "emergency", 1,   True),
]


class Command(BaseCommand):
    help = "Seed the database with realistic test data for all user types and features."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete ALL existing user/service data before seeding.",
        )
        parser.add_argument(
            "--summary",
            action="store_true",
            help="Print login credentials table without writing to DB.",
        )

    # ── entry point ───────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        if options["summary"]:
            self._print_summary()
            return

        if options["flush"]:
            self._flush()

        self.stdout.write(self.style.MIGRATE_HEADING("\n[+] HavenMED -- Seeding Test Data\n" + "-" * 50))

        with transaction.atomic():
            admin   = self._create_superadmin()
            patients = self._create_patients()
            doctors  = self._create_professionals()
            insts    = self._create_institutions()
            services = self._create_service_types()
            self._create_availability_slots(doctors)
            self._create_appointments(patients, doctors, services)

        self.stdout.write("")
        self._print_summary()
        self.stdout.write(self.style.SUCCESS("\n[DONE] Database seeded successfully.\n"))

    # ── flush ─────────────────────────────────────────────────────────────────

    def _flush(self):
        from services.models import (Appointment, AvailabilitySlot,
                                     ConsultationNotes, Payment, ServiceType)
        from accounts.models import (User, PatientProfile,
                                     HealthcareProfessionalProfile, InstitutionProfile)

        self.stdout.write(self.style.WARNING("[!] Flushing existing data ..."))
        ConsultationNotes.objects.all().delete()
        Payment.objects.all().delete()
        Appointment.objects.all().delete()
        AvailabilitySlot.objects.all().delete()
        ServiceType.objects.all().delete()
        # Delete non-superuser test accounts
        User.objects.filter(email__endswith="@test.havenmed.co.ke").delete()
        self.stdout.write(self.style.WARNING("    Done.\n"))

    # ── superadmin ────────────────────────────────────────────────────────────

    def _create_superadmin(self):
        from accounts.models import User

        email = "admin@havenmed.co.ke"
        if User.objects.filter(email=email).exists():
            self.stdout.write(f"    --  Superadmin already exists: {email}")
            return User.objects.get(email=email)

        admin = User.objects.create_superuser(
            username="admin",
            email=email,
            password=PASSWORD,
            first_name="HavenMED",
            last_name="Admin",
        )
        # Superadmin has no user_type; mark approved so nothing breaks
        admin.is_approved = True
        admin.save(update_fields=["is_approved"])
        self.stdout.write(self.style.SUCCESS(f"    OK  Superadmin created: {email}"))
        return admin

    # ── patients ─────────────────────────────────────────────────────────────

    def _create_patients(self):
        from accounts.models import User, PatientProfile

        created = []
        for p in PATIENTS:
            if User.objects.filter(email=p["email"]).exists():
                u = User.objects.get(email=p["email"])
                self.stdout.write(f"    --  Patient exists: {p['email']}")
            else:
                u = User.objects.create_user(
                    username=p["email"].split("@")[0],
                    email=p["email"],
                    password=PASSWORD,
                    first_name=p["first_name"],
                    last_name=p["last_name"],
                    phone_number=p["phone"],
                    user_type="patient",
                    county=p["county"],
                    subcounty=p["subcounty"],
                    is_approved=True,   # patients auto-approved
                    is_active=True,
                )
                self.stdout.write(self.style.SUCCESS(f"    OK  Patient: {u.get_full_name()} <{u.email}>"))

            # Ensure / update PatientProfile
            profile, _ = PatientProfile.objects.get_or_create(user=u)
            profile.date_of_birth = p["dob"]
            profile.gender = p["gender"]
            profile.medical_history = p["history"]
            profile.allergies = p["allergies"]
            profile.emergency_contact_name = "Emergency Contact"
            profile.emergency_contact_phone = "+254700000000"
            profile.save()

            created.append(profile)
        return created

    # ── healthcare professionals ──────────────────────────────────────────────

    def _create_professionals(self):
        from accounts.models import User, HealthcareProfessionalProfile
        import tempfile, os
        from django.core.files.base import ContentFile

        # Minimal 1×1 white PNG to satisfy ImageField (avoids needing real files)
        DUMMY_PNG = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00"
            b"\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
            b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00"
            b"\x00IEND\xaeB`\x82"
        )

        created = []
        for p in PROFESSIONALS:
            if User.objects.filter(email=p["email"]).exists():
                u = User.objects.get(email=p["email"])
                self.stdout.write(f"    --  Professional exists: {p['email']}")
            else:
                # Disconnect signal so it doesn't try to create an incomplete profile
                from django.db.models.signals import post_save
                from accounts.models import create_user_profile, save_user_profile
                post_save.disconnect(create_user_profile, sender=User)
                post_save.disconnect(save_user_profile, sender=User)
                try:
                    u = User.objects.create_user(
                        username=p["email"].split("@")[0],
                        email=p["email"],
                        password=PASSWORD,
                        first_name=p["first_name"],
                        last_name=p["last_name"],
                        phone_number=p["phone"],
                        user_type="healthcare_professional",
                        county=p["county"],
                        subcounty=p["subcounty"],
                        is_approved=True,
                        is_active=True,
                    )
                finally:
                    post_save.connect(create_user_profile, sender=User)
                    post_save.connect(save_user_profile, sender=User)
                self.stdout.write(self.style.SUCCESS(f"    OK  Professional: {u.get_full_name()} <{u.email}>"))


            # Ensure / update HealthcareProfessionalProfile
            profile, created_now = HealthcareProfessionalProfile.objects.get_or_create(
                user=u,
                defaults={"specialization": p["spec"], "years_of_experience": p["years"],
                          "kmpdu_license_number": p["license"]}
            )
            if not created_now:
                profile.specialization = p["spec"]
                profile.years_of_experience = p["years"]
                profile.kmpdu_license_number = p["license"]

            profile.bio = p["bio"]
            profile.consultation_fee = Decimal(str(p["fee"]))
            profile.available_for_home_visits = True
            profile.available_for_virtual_consultations = True
            profile.is_available = True
            profile.average_rating = Decimal(str(round(random.uniform(3.8, 5.0), 2)))
            profile.total_reviews = random.randint(10, 120)

            # Attach dummy documents only if fields are empty
            if not profile.national_id:
                profile.national_id.save(f"dummy_id_{u.id}.png", ContentFile(DUMMY_PNG), save=False)
            if not profile.kmpdu_license:
                profile.kmpdu_license.save(f"dummy_lic_{u.id}.png", ContentFile(DUMMY_PNG), save=False)

            profile.save()
            created.append(profile)
        return created

    # ── institutions ─────────────────────────────────────────────────────────

    def _create_institutions(self):
        from accounts.models import User, InstitutionProfile
        from django.core.files.base import ContentFile

        DUMMY_PNG = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00"
            b"\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
            b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00"
            b"\x00IEND\xaeB`\x82"
        )

        all_inst = CLINICS + HOSPITALS
        inst_types = ["clinic"] * len(CLINICS) + ["hospital"] * len(HOSPITALS)
        created = []

        for p, itype in zip(all_inst, inst_types):
            if User.objects.filter(email=p["email"]).exists():
                u = User.objects.get(email=p["email"])
                self.stdout.write(f"    --  Institution exists: {p['email']}")
            else:
                from django.db.models.signals import post_save
                from accounts.models import create_user_profile, save_user_profile
                post_save.disconnect(create_user_profile, sender=User)
                post_save.disconnect(save_user_profile, sender=User)
                try:
                    u = User.objects.create_user(
                        username=p["email"].split("@")[0],
                        email=p["email"],
                        password=PASSWORD,
                        first_name=p["inst_name"],
                        last_name="",
                        phone_number=p["phone"],
                        user_type=itype,
                        county=p["county"],
                        subcounty=p["subcounty"],
                        is_approved=True,
                        is_active=True,
                    )
                finally:
                    post_save.connect(create_user_profile, sender=User)
                    post_save.connect(save_user_profile, sender=User)
                self.stdout.write(self.style.SUCCESS(f"    OK  Institution ({itype}): {p['inst_name']} <{u.email}>"))


            profile, created_now = InstitutionProfile.objects.get_or_create(
                user=u,
                defaults={
                    "institution_type": itype,
                    "institution_name": p["inst_name"],
                    "registration_number": p["reg"],
                    "physical_address": p["address"],
                    "services_offered": p["services"],
                }
            )
            if not created_now:
                profile.institution_name = p["inst_name"]
                profile.registration_number = p["reg"]
                profile.physical_address = p["address"]
                profile.services_offered = p["services"]

            profile.emergency_services = (itype == "hospital")
            profile.average_rating = Decimal(str(round(random.uniform(3.5, 4.9), 2)))
            profile.total_reviews = random.randint(20, 300)
            if p.get("beds"):
                profile.bed_capacity = p["beds"]
            if p.get("staff"):
                profile.staff_count = p["staff"]
            profile.operating_hours = "Mon–Fri: 8 AM – 8 PM  |  Sat: 8 AM – 4 PM  |  Sun: Emergency Only"

            if not profile.medical_license:
                profile.medical_license.save(f"dummy_inst_lic_{u.id}.png", ContentFile(DUMMY_PNG), save=False)

            profile.save()
            created.append(profile)
        return created

    # ── service types ─────────────────────────────────────────────────────────

    def _create_service_types(self):
        from services.models import ServiceType

        created = []
        for s in SERVICE_TYPES:
            obj, new = ServiceType.objects.get_or_create(
                name=s["name"],
                defaults={
                    "description": s["desc"],
                    "base_price": Decimal(str(s["price"])),
                    "duration_minutes": s["mins"],
                    "home_visit_extra_fee": Decimal(str(s.get("home_fee", 0))),
                    "urgent_fee": Decimal(str(s.get("urgent_fee", 0))),
                    "virtual_available": not s.get("home_only", False),
                    "home_visit_available": s.get("home", True),
                    "in_person_available": not s.get("home_only", False) and s.get("inperson", True),
                    "is_active": True,
                }
            )
            if new:
                self.stdout.write(self.style.SUCCESS(f"    OK  ServiceType: {obj.name}  (KES {obj.base_price})"))
            else:
                self.stdout.write(f"    --  ServiceType exists: {obj.name}")
            created.append(obj)
        return created

    # ── availability slots ────────────────────────────────────────────────────

    def _create_availability_slots(self, doctors):
        from services.models import AvailabilitySlot

        slot_count = 0
        for doctor in doctors:
            for day in DAYS:
                # Morning slot
                obj, new = AvailabilitySlot.objects.get_or_create(
                    healthcare_professional=doctor,
                    day_of_week=day,
                    start_time=time(8, 0),
                    defaults={
                        "end_time": time(12, 0),
                        "slot_duration": 30,
                        "is_active": True,
                        "virtual_consultations_available": True,
                        "home_visits_available": (day in ["saturday"]),
                        "in_person_available": True,
                    }
                )
                if new:
                    slot_count += 1

                # Afternoon slot (Mon–Fri only)
                if day != "saturday":
                    obj2, new2 = AvailabilitySlot.objects.get_or_create(
                        healthcare_professional=doctor,
                        day_of_week=day,
                        start_time=time(14, 0),
                        defaults={
                            "end_time": time(17, 0),
                            "slot_duration": 30,
                            "is_active": True,
                            "virtual_consultations_available": True,
                            "home_visits_available": True,
                            "in_person_available": True,
                        }
                    )
                    if new2:
                        slot_count += 1

        self.stdout.write(self.style.SUCCESS(f"    OK  Availability slots created: {slot_count}"))

    # ── appointments ─────────────────────────────────────────────────────────

    def _create_appointments(self, patients, doctors, services):
        from services.models import Appointment, Payment, ConsultationNotes

        today = date.today()
        created_count = 0
        skipped_count = 0

        for (pi, di, si, atype, status, priority, offset, paid) in APPOINTMENT_SCENARIOS:
            patient = patients[pi]
            doctor  = doctors[di]
            service = services[si]
            appt_date = today + timedelta(days=offset)
            appt_time = time(random.choice([9, 10, 11, 14, 15, 16]), random.choice([0, 30]))

            # Avoid duplicates
            exists = Appointment.objects.filter(
                patient=patient,
                healthcare_professional=doctor,
                appointment_date=appt_date,
                appointment_time=appt_time,
            ).exists()
            if exists:
                skipped_count += 1
                continue

            fee = doctor.consultation_fee or service.base_price
            extra = service.home_visit_extra_fee if atype == "home_visit" else Decimal("0")
            if priority == "urgent":
                extra += service.urgent_fee
            if priority == "emergency":
                extra += service.urgent_fee * 2

            appt = Appointment(
                patient=patient,
                healthcare_professional=doctor,
                service_type=service,
                appointment_type=atype,
                appointment_date=appt_date,
                appointment_time=appt_time,
                duration_minutes=service.duration_minutes,
                priority=priority,
                status=status,
                consultation_fee=fee,
                additional_fees=extra,
                total_amount=fee + extra,
                chief_complaint=self._random_complaint(),
                symptoms=self._random_symptoms(),
                patient_phone=patient.user.phone_number or "+254700000000",
                patient_email=patient.user.email,
                visit_address="123 Test Street, Nairobi" if atype == "home_visit" else "",
                is_paid=paid,
            )

            # Status-linked timestamps
            if status in ("confirmed", "paid", "in_progress", "completed"):
                appt.confirmed_at = timezone.now() - timedelta(days=abs(offset) + 1)
            if status == "completed":
                appt.started_at   = timezone.now() - timedelta(days=abs(offset), hours=2)
                appt.completed_at = timezone.now() - timedelta(days=abs(offset), hours=1)
                appt.diagnosis    = "Patient assessed and treated as per clinical guidelines."
                appt.treatment_plan = "Continue prescribed medication. Follow up in 4 weeks."
                appt.prescription = "Amoxicillin 500 mg TDS × 7 days"
                appt.doctor_notes = "Patient responded well. Advised lifestyle modifications."
                appt.patient_rating = random.randint(4, 5)
                appt.patient_review = random.choice([
                    "Excellent service! Doctor was very thorough.",
                    "Very professional and caring. Highly recommended.",
                    "Quick diagnosis and clear treatment plan. Thank you!",
                    "Felt very comfortable. Will definitely book again.",
                ])

            if paid:
                appt.paid_at = timezone.now() - timedelta(days=abs(offset))
                appt.payment_method = random.choice(["mpesa", "card"])
                appt.payment_reference = f"TXN{random.randint(100000, 999999)}"

            appt.save()
            created_count += 1

            # Payment record for paid appointments
            if paid:
                Payment.objects.get_or_create(
                    appointment=appt,
                    defaults={
                        "amount": appt.total_amount,
                        "payment_method": appt.payment_method,
                        "status": "completed",
                        "external_reference": appt.payment_reference,
                        "mpesa_receipt_number": f"QHX{random.randint(1000000, 9999999)}" if appt.payment_method == "mpesa" else "",
                        "transaction_id": f"TXN-{random.randint(10000, 99999)}",
                        "phone_number": appt.patient_phone,
                        "completed_at": appt.paid_at,
                    }
                )

            # Consultation notes for completed appointments
            if status == "completed":
                ConsultationNotes.objects.get_or_create(
                    appointment=appt,
                    defaults={
                        "blood_pressure_systolic":  random.randint(110, 135),
                        "blood_pressure_diastolic": random.randint(70, 90),
                        "heart_rate":               random.randint(62, 88),
                        "temperature":              Decimal(str(round(random.uniform(36.4, 37.2), 1))),
                        "weight":                   Decimal(str(round(random.uniform(55.0, 95.0), 1))),
                        "height":                   Decimal(str(round(random.uniform(155.0, 185.0), 1))),
                        "chief_complaint_details":  "Patient presented with " + self._random_complaint().lower(),
                        "assessment_and_plan":      "Assessed and managed appropriately. Patient educated on self-care.",
                        "medications_prescribed":   "As per prescription issued.",
                        "follow_up_instructions":   "Return in 4 weeks or earlier if symptoms worsen.",
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"    OK  Appointments created: {created_count}  (skipped: {skipped_count})"))

    # ── helpers ───────────────────────────────────────────────────────────────

    def _random_complaint(self):
        return random.choice([
            "Persistent cough and sore throat for 5 days",
            "Chest pain and shortness of breath",
            "Severe headache and dizziness",
            "Lower back pain affecting mobility",
            "Skin rash and itching on arms",
            "Abdominal pain and nausea",
            "Joint pain and swelling in knees",
            "Fatigue and loss of appetite",
            "High fever and chills",
            "Regular diabetes and blood pressure review",
        ])

    def _random_symptoms(self):
        return random.choice([
            "Fever 38.5°C, dry cough, fatigue",
            "Sharp chest pain on exertion, mild SOB",
            "Throbbing headache, photophobia, nausea",
            "Lower back stiffness, worse in mornings",
            "Erythematous rash, pruritus, no fever",
            "Epigastric pain, bloating, vomiting ×2",
            "Bilateral knee swelling, reduced ROM",
            "Generalized weakness, anorexia, weight loss",
            "T 39.1°C, rigors, myalgia",
            "Asymptomatic — routine follow-up visit",
        ])

    # ── summary table ─────────────────────────────────────────────────────────

    def _print_summary(self):
        W = 80
        self.stdout.write("\n" + "=" * W)
        self.stdout.write("  [KEY] TEST CREDENTIALS  --  Password for ALL accounts: " + self.style.WARNING(PASSWORD))
        self.stdout.write("=" * W)

        sections = [
            ("SUPERADMIN", [("HavenMED Admin",         "admin@havenmed.co.ke",                    "Django Admin + all access")]),
            ("PATIENTS (auto-approved)", [
                (f"{p['first_name']} {p['last_name']}", p["email"], f"{p['county'].title()} | DOB {p['dob']}")
                for p in PATIENTS
            ]),
            ("HEALTHCARE PROFESSIONALS (approved)", [
                (p["first_name"] + " " + p["last_name"], p["email"],
                 f"{p['spec'].replace('_',' ').title()} | {p['years']} yrs | KES {p['fee']}/consult")
                for p in PROFESSIONALS
            ]),
            ("CLINICS (approved)", [
                (p["inst_name"], p["email"], p["county"].title()) for p in CLINICS
            ]),
            ("HOSPITALS (approved)", [
                (p["inst_name"], p["email"], p["county"].title()) for p in HOSPITALS
            ]),
        ]

        for title, rows in sections:
            self.stdout.write(f"  -- {title} " + "-" * max(0, W - len(title) - 6))
            for name, email, note in rows:
                self.stdout.write(f"  (*) {name:<35} {email:<45}")
                self.stdout.write(f"      -> {note}")

        self.stdout.write("\n" + "=" * W)
        self.stdout.write("  [WEB]   Login URL:   http://127.0.0.1:8000/accounts/login/")
        self.stdout.write("  [ADMIN] Admin URL:   http://127.0.0.1:8000/admin/")
        self.stdout.write("=" * W + "\n")
