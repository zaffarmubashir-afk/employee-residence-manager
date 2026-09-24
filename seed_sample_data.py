"""
Optional: populates the database with a few sample companies/employees so
you can see the Dashboard colours and Reports working immediately.
Run once with:   python seed_sample_data.py
(Safe to skip - the app works fine with an empty database too.)
"""
import sys, os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import database as db


def d(days_from_today):
    return (date.today() + timedelta(days=days_from_today)).isoformat()


def run():
    db.init_db()
    if db.list_companies():
        print(f"Database already has data - skipping seed.\n"
              f"(Delete the file at {db.DB_PATH} to reset.)")
        return

    c1 = db.add_company({
        "company_name": "Falcon Trading LLC",
        "legal_type": "Mainland",
        "trade_license_no": "CN-1102345",
        "trade_license_expiry": d(45),
        "establishment_card_no": "EC-778812",
        "establishment_card_expiry": d(10),
        "mohre_establishment_no": "MOH-556291",
        "immigration_file_no": "700/12345/2026/1",
        "chamber_of_commerce_no": "DCCI-88221",
        "chamber_of_commerce_expiry": d(200),
        "tenancy_ejari_no": "EJ-9981233",
        "tenancy_ejari_expiry": d(-5),
        "status": "Active",
        "address": "Office 1204, Business Bay, Dubai",
        "phone": "+971 4 123 4567",
        "email": "info@falcontrading.ae",
    })

    c2 = db.add_company({
        "company_name": "Bright Horizon Tech FZ-LLC",
        "legal_type": "Free Zone",
        "free_zone_name": "Dubai Internet City",
        "trade_license_no": "DIC-0092211",
        "trade_license_expiry": d(300),
        "establishment_card_no": "EC-441987",
        "establishment_card_expiry": d(90),
        "status": "Active",
        "address": "DIC Building 3, Dubai",
        "phone": "+971 4 987 6543",
        "email": "hr@brighthorizon.ae",
    })

    e1 = db.add_employee({
        "company_id": c1, "employee_code": "EMP-001", "full_name": "John Michael Cruz",
        "nationality": "Filipino", "gender": "Male", "job_title": "Senior Accountant",
        "date_of_joining": "2022-03-01", "passport_no": "P1234567", "passport_expiry": d(500),
        "entry_permit_no": "EP-9012", "entry_permit_expiry": d(400),
        "residence_visa_no": "RV-778901", "residence_visa_expiry": d(20),
        "emirates_id_no": "784-1990-1234567-1", "emirates_id_expiry": d(8),
        "labour_card_no": "LC-2201", "labour_card_expiry": d(60),
        "employment_contract_no": "MOHRE-EC-5521", "employment_contract_expiry": d(60),
        "medical_test_date": "2022-02-15", "medical_test_expiry": d(20),
        "insurance_policy_no": "INS-8834", "insurance_expiry": d(25),
        "basic_salary": "8000", "status": "Active", "visa_sponsor": "Falcon Trading LLC",
    })

    db.add_employee({
        "company_id": c1, "employee_code": "EMP-002", "full_name": "Aisha Al Marri",
        "nationality": "Emirati", "gender": "Female", "job_title": "HR Manager",
        "date_of_joining": "2021-06-15", "passport_no": "AE998877", "passport_expiry": d(1200),
        "status": "Active", "basic_salary": "12000",
    })

    db.add_employee({
        "company_id": c2, "employee_code": "EMP-101", "full_name": "Rohit Sharma",
        "nationality": "Indian", "gender": "Male", "job_title": "Software Engineer",
        "date_of_joining": "2023-01-10", "passport_no": "N5566778", "passport_expiry": d(900),
        "residence_visa_no": "RV-556231", "residence_visa_expiry": d(120),
        "emirates_id_no": "784-1992-7788990-2", "emirates_id_expiry": d(120),
        "labour_card_no": "LC-9981", "labour_card_expiry": d(-15),
        "status": "Active", "basic_salary": "15000", "visa_sponsor": "Bright Horizon Tech FZ-LLC",
    })

    db.add_custom_document({
        "owner_type": "company", "owner_id": c1, "document_name": "VAT Registration Certificate",
        "document_no": "TRN-100234567800003", "issue_date": "2023-01-01", "expiry_date": "",
        "status": "Active", "notes": "No expiry - permanent registration",
    })
    db.add_custom_document({
        "owner_type": "employee", "owner_id": e1, "document_name": "Bank Guarantee Letter",
        "document_no": "BG-4432", "issue_date": d(-300), "expiry_date": d(35),
        "status": "Active",
    })

    print("Sample data created: 2 companies, 3 employees, 2 extra documents.")
    print("Launch the app with:  python main.py")


if __name__ == "__main__":
    run()
