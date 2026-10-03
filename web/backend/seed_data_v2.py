#!/usr/bin/env python3
"""
Seed data script for APEX-OS Business Platform API endpoints.
Populates all endpoints with realistic test data, skipping those already populated.
"""

import json
import random
import string
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library required. Install with: pip install requests")
    sys.exit(1)

# ── Configuration ──────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 1

# ── Realistic Data Pools ───────────────────────────────────────────────────────
FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "David", "Elizabeth", "William", "Barbara", "Richard", "Susan",
    "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen", "Christopher",
    "Lisa", "Daniel", "Nancy", "Matthew", "Betty", "Anthony", "Margaret",
    "Mark", "Sandra", "Donald", "Ashley", "Steven", "Kimberly", "Paul",
    "Emily", "Andrew", "Donna", "Joshua", "Michelle", "Kenneth", "Carol",
    "Kevin", "Amanda", "Brian", "Dorothy", "George", "Melissa", "Timothy",
    "Deborah", "Ronald", "Stephanie", "Edward", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary",
    "Amy", "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Anna",
    "Stephen", "Brenda", "Larry", "Pamela", "Justin", "Emma", "Scott",
    "Nicole", "Brandon", "Helen", "Benjamin", "Samantha", "Samuel", "Katherine",
    "Gregory", "Christine", "Alexander", "Debra", "Patrick", "Rachel",
    "Frank", "Carolyn", "Raymond", "Janet", "Jack", "Catherine", "Dennis",
    "Maria", "Jerry", "Heather", "Tyler", "Diane", "Aaron", "Ruth",
    "Jose", "Julie", "Adam", "Olivia", "Nathan", "Joyce", "Henry",
    "Virginia", "Douglas", "Victoria", "Zachary", "Kelly", "Peter", "Lauren",
    "Kyle", "Christina", "Noah", "Joan", "Ethan", "Evelyn", "Jeremy",
    "Judith", "Walter", "Andrea", "Christian", "Hannah", "Keith", "Megan",
    "Roger", "Cheryl", "Terry", "Jacqueline", "Austin", "Martha", "Sean",
    "Madison", "Gerald", "Teresa", "Carl", "Gloria", "Harold", "Sara",
    "Dylan", "Janice", "Arthur", "Ann", "Lawrence", "Abigail", "Jordan",
    "Kathryn", "Jesse", "Sophia", "Bryan", "Frances", "Billy", "Jean",
    "Bruce", "Alice", "Gabriel", "Judy", "Joe", "Isabella", "Logan",
    "Julia", "Alan", "Grace", "Juan", "Amber", "Wayne", "Denise",
    "Ralph", "Danielle", "Roy", "Marilyn", "Eugene", "Beverly", "Randy",
    "Charlotte", "Vincent", "Natalie", "Louis", "Theresa", "Russell",
    "Diana", "Philip", "Brittany", "Bobby", "Kayla", "Johnny", "Alexis",
    "Bradley", "Lori",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz",
    "Parker", "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris",
    "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan",
    "Cooper", "Peterson", "Bailey", "Reed", "Kelly", "Howard", "Ramos",
    "Kim", "Cox", "Ward", "Richardson", "Watson", "Brooks", "Chavez",
    "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes",
    "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long",
    "Ross", "Foster", "Jimenez", "Powell", "Jenkins", "Perry", "Russell",
    "Sullivan", "Bell", "Coleman", "Butler", "Henderson", "Barnes",
    "Gonzales", "Fisher", "Vasquez", "Simmons", "Romero", "Jordan",
    "Patterson", "Alexander", "Hamilton", "Graham", "Reynolds", "Griffin",
    "Wallace", "Moreno", "West", "Cole", "Hayes", "Bryant", "Herrera",
    "Gibson", "Ellis", "Tran", "Medina", "Aguilar", "Stevens", "Murray",
    "Ford", "Castro", "Marshall", "Owens", "Harrison", "Fernandez",
    "Mcdonald", "Woods", "Washington", "Kennedy", "Wells", "Vargas",
    "Henry", "Chen", "Freeman", "Webb", "Tucker", "Guzman", "Burns",
    "Crawford", "Olson", "Simpson", "Porter", "Hunter", "Gordon",
    "Mendez", "Shaw", "Snyder", "Mason", "Dixon", "Munoz", "Hunt",
    "Hicks", "Holmes", "Palmer", "Wagner", "Black", "Robertson", "Boyd",
    "Rose", "Stone", "Salazar", "Warren", "Fox", "Mills", "Meyer",
    "Rice", "Schmidt", "Garza", "Daniels", "Ferguson", "Nichols",
    "Stephens", "Soto", "Weaver", "Ryan", "Gardner", "Payne", "Grant",
    "Dunn", "Kelley", "Spencer", "Hawkins", "Arnold", "Pierce", "Vazquez",
    "Hansen", "Peters", "Santos", "Hart", "Bradley", "Knight", "Elliott",
    "Cunningham", "Duncan", "Armstrong", "Hudson", "Carroll", "Lane",
    "Riley", "Andrews", "Alvarado", "Ray", "Delgado", "Berry", "Perkins",
    "Hoffman", "Johnston", "Matthews", "Pena", "Richards", "Contreras",
    "Willis", "Carpenter", "Lawrence", "Sandoval", "Guerrero", "George",
    "Chapman", "Rios", "Estrada", "Ortega", "Watkins", "Greene", "Nunez",
    "Wheeler", "Valdez", "Harper", "Burke", "Larson", "Santiago", "Maldonado",
    "Morrison", "Franklin", "Carlson", "Dominguez", "Carpenter", "Salinas",
]

DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "company.com", "business.org",
    "enterprise.io", "corp.net", "mail.com", "protonmail.com", "fastmail.com",
]

COMPANY_NAMES = [
    "Acme Corp", "Globex Inc", "Initech", "Umbrella Corp", "Stark Industries",
    "Wayne Enterprises", "Cyberdyne Systems", "Soylent Corp", "Hooli",
    "Pied Piper", "Massive Dynamic", "Aperture Science", "Tyrell Corp",
    "Weyland-Yutani", "Oscorp", "LexCorp", "Daily Planet", "Gekko & Co",
    "Bluth Company", "Dunder Mifflin", "Sterling Cooper", "Vandelay Industries",
    "Prestige Worldwide", "Bubba Gump", "Monarch", "Apex Solutions",
    "Nexus Technologies", "Vertex Industries", "Zenith Corp", "Pinnacle Group",
    "Summit Enterprises", "Atlas Logistics", "Beacon Manufacturing",
    "Catalyst Consulting", "Delta Systems", "Eclipse Software", "Fusion Energy",
    "Genesis Biotech", "Horizon Media", "Infinity Labs", "Jupiter Mining",
    "Keystone Construction", "Liberty Financial", "Meridian Health",
    "Nova Pharmaceuticals", "Omega Defense", "Quantum Dynamics",
    "Redwood Ventures", "Silverline Capital", "Titan Aerospace",
    "Ursa Major", "Vanguard Solutions", "Westbrook Partners", "Xenon Labs",
    "Yellowstone Resources", "Zephyr Technologies", "Blue Ridge",
    "Crimson Peak", "Diamondback", "Emerald City", "Falcon Crest",
    "Golden Gate", "Iron Mountain", "Jasper Ridge", "Kodiak Island",
    "Lone Star", "Midnight Sun", "North Star", "Pacific Rim",
    "Rising Sun", "Southern Cross", "Thunder Valley", "Union Pacific",
    "White Sands", "Black Forest", "Red River", "Blue Mountain",
]

LEAD_STATUSES = ["new", "contacted", "qualified", "proposal", "won", "lost", "nurturing"]
LEAD_SOURCES = ["website", "referral", "cold_call", "social_media", "trade_show", "email_campaign", "partner", "advertisement"]
INDUSTRIES = ["Technology", "Healthcare", "Finance", "Manufacturing", "Retail", "Education", "Real Estate", "Legal", "Marketing", "Consulting"]
ROLES = ["admin", "manager", "sales_rep", "support_agent", "viewer", "analyst"]
STATUSES = ["active", "inactive", "pending", "archived"]
PRIORITIES = ["low", "medium", "high", "urgent"]
TICKET_STATUSES = ["open", "in_progress", "waiting", "resolved", "closed"]
PROJECT_STATUSES = ["planning", "in_progress", "on_hold", "completed", "cancelled"]
TASK_STATUSES = ["todo", "in_progress", "review", "done", "blocked"]
INVOICE_STATUSES = ["draft", "sent", "paid", "overdue", "cancelled"]
PRODUCT_CATEGORIES = ["Software", "Hardware", "Services", "Subscription", "License", "Support", "Training", "Consulting"]

# ── Helpers ────────────────────────────────────────────────────────────────────

def random_email(first: str, last: str) -> str:
    """Generate a realistic email address."""
    patterns = [
        f"{first.lower()}.{last.lower()}",
        f"{first.lower()[0]}{last.lower()}",
        f"{first.lower()}{last.lower()[0]}",
        f"{first.lower()}_{last.lower()}",
        f"{first.lower()}{random.randint(1, 99)}",
    ]
    return f"{random.choice(patterns)}@{random.choice(DOMAINS)}"

def random_phone() -> str:
    """Generate a realistic US phone number."""
    return f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"

def random_date(start_year: int = 2023, end_year: int = 2026) -> str:
    """Generate a random ISO date string."""
    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"

def random_datetime(start_year: int = 2023, end_year: int = 2026) -> str:
    """Generate a random ISO datetime string."""
    date = random_date(start_year, end_year)
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return f"{date}T{hour:02d}:{minute:02d}:{second:02d}Z"

def random_string(length: int = 10) -> str:
    """Generate a random alphanumeric string."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

def random_name() -> str:
    """Generate a random full name."""
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def random_company() -> str:
    """Generate a random company name."""
    return random.choice(COMPANY_NAMES)

def make_request(method: str, url: str, **kwargs) -> Tuple[Optional[requests.Response], Optional[Exception]]:
    """Make an HTTP request with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.request(method, url, timeout=TIMEOUT, **kwargs)
            return resp, None
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                return None, e
    return None, None

def extract_items(response_data: Any) -> List[Dict]:
    """Extract items from various response formats."""
    if isinstance(response_data, list):
        return response_data
    if isinstance(response_data, dict):
        for key in ("items", "data", "results", "records", "objects", "entries"):
            if key in response_data and isinstance(response_data[key], list):
                return response_data[key]
        if "id" in response_data:
            return [response_data]
    return []

def has_existing_data(response_data: Any) -> bool:
    """Check if the response contains existing data."""
    items = extract_items(response_data)
    return len(items) > 0

# ── Endpoint Definitions ───────────────────────────────────────────────────────

ENDPOINTS = {
    "users": {
        "path": "/users",
        "method": "POST",
        "generator": lambda i: {
            "name": random_name(),
            "email": random_email(random.choice(FIRST_NAMES), random.choice(LAST_NAMES)),
            "role": random.choice(ROLES),
            "is_active": random.choice([True, True, True, False]),
            "phone": random_phone(),
            "department": random.choice(["Sales", "Marketing", "Engineering", "Support", "Finance", "HR", "Operations"]),
            "avatar_url": f"https://api.dicebear.com/7.x/avataaars/svg?seed={random_string(8)}",
            "created_at": random_datetime(),
            "last_login": random_datetime(2025, 2026),
        },
    },
    "leads": {
        "path": "/leads",
        "method": "POST",
        "generator": lambda i: {
            "name": random_name(),
            "email": random_email(random.choice(FIRST_NAMES), random.choice(LAST_NAMES)),
            "status": random.choice(LEAD_STATUSES),
            "source": random.choice(LEAD_SOURCES),
            "company": random_company(),
            "phone": random_phone(),
            "value": round(random.uniform(1000, 100000), 2),
            "notes": f"Interested in {random.choice(['enterprise', 'small business', 'startup'])} solutions. Follow up required.",
            "assigned_to": random.randint(1, 20),
            "created_at": random_datetime(),
            "last_contact": random_datetime(2025, 2026),
        },
    },
    "contacts": {
        "path": "/contacts",
        "method": "POST",
        "generator": lambda i: {
            "first_name": random.choice(FIRST_NAMES),
            "last_name": random.choice(LAST_NAMES),
            "email": random_email(random.choice(FIRST_NAMES), random.choice(LAST_NAMES)),
            "phone": random_phone(),
            "company": random_company(),
            "job_title": random.choice(["CEO", "CTO", "VP Sales", "Director", "Manager", "Engineer", "Analyst", "Consultant"]),
            "address": f"{random.randint(100, 9999)} {random.choice(['Main St', 'Oak Ave', 'Park Blvd', 'Cedar Ln', 'Maple Dr'])}",
            "city": random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Seattle", "Denver", "Boston"]),
            "state": random.choice(["CA", "NY", "TX", "FL", "WA", "CO", "MA", "IL"]),
            "zip_code": f"{random.randint(10000, 99999)}",
            "country": "US",
            "created_at": random_datetime(),
        },
    },
    "accounts": {
        "path": "/accounts",
        "method": "POST",
        "generator": lambda i: {
            "name": random_company(),
            "industry": random.choice(INDUSTRIES),
            "website": f"https://www.{random_string(8).lower()}.com",
            "phone": random_phone(),
            "email": random_email(random.choice(FIRST_NAMES), random.choice(LAST_NAMES)),
            "address": f"{random.randint(100, 9999)} {random.choice(['Business Park', 'Commerce Dr', 'Industrial Way', 'Corporate Blvd'])}",
            "city": random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Seattle"]),
            "state": random.choice(["CA", "NY", "TX", "FL", "WA", "CO"]),
            "zip_code": f"{random.randint(10000, 99999)}",
            "country": "US",
            "annual_revenue": round(random.uniform(50000, 50000000), 2),
            "employee_count": random.randint(5, 5000),
            "status": random.choice(STATUSES),
            "created_at": random_datetime(),
        },
    },
    "opportunities": {
        "path": "/opportunities",
        "method": "POST",
        "generator": lambda i: {
            "name": f"{random_company()} - {random.choice(['Expansion', 'Renewal', 'New Deal', 'Upgrade', 'Pilot'])}",
            "account_id": random.randint(1, 50),
            "value": round(random.uniform(5000, 500000), 2),
            "stage": random.choice(["prospecting", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"]),
            "probability": random.randint(5, 95),
            "close_date": random_date(2026, 2027),
            "source": random.choice(LEAD_SOURCES),
            "description": f"Opportunity for {random.choice(['enterprise license', 'annual subscription', 'custom implementation', 'training package'])}.",
            "assigned_to": random.randint(1, 20),
            "created_at": random_datetime(),
        },
    },
    "activities": {
        "path": "/activities",
        "method": "POST",
        "generator": lambda i: {
            "type": random.choice(["call", "email", "meeting", "note", "task"]),
            "subject": f"{random.choice(['Follow up', 'Check in', 'Demo', 'Proposal review', 'Contract discussion'])} with {random_name()}",
            "description": f"Discussed {random.choice(['pricing', 'timeline', 'requirements', 'budget', 'implementation plan'])}.",
            "due_date": random_date(2026, 2027),
            "completed": random.choice([True, False]),
            "assigned_to": random.randint(1, 20),
            "related_to": random.choice(["lead", "contact", "account", "opportunity"]),
            "related_id": random.randint(1, 100),
            "created_at": random_datetime(),
        },
    },
    "tickets": {
        "path": "/tickets",
        "method": "POST",
        "generator": lambda i: {
            "subject": f"{random.choice(['Login issue', 'Feature request', 'Bug report', 'Billing question', 'Integration help', 'Performance concern'])}",
            "description": f"Customer reported: {random.choice(['unable to access dashboard', 'data not syncing', 'email notifications not working', 'API rate limit exceeded', 'UI rendering issue'])}.",
            "status": random.choice(TICKET_STATUSES),
            "priority": random.choice(PRIORITIES),
            "category": random.choice(["bug", "feature_request", "question", "billing", "technical", "account"]),
            "requester_email": random_email(random.choice(FIRST_NAMES), random.choice(LAST_NAMES)),
            "assigned_to": random.randint(1, 20),
            "created_at": random_datetime(),
            "updated_at": random_datetime(2025, 2026),
        },
    },
    "projects": {
        "path": "/projects",
        "method": "POST",
        "generator": lambda i: {
            "name": f"{random.choice(['Website Redesign', 'Mobile App', 'API Migration', 'Data Pipeline', 'Security Audit', 'Cloud Migration', 'ERP Implementation', 'CRM Upgrade'])} - {random_company()}",
            "description": f"Project to {random.choice(['improve efficiency', 'reduce costs', 'enhance user experience', 'modernize infrastructure', 'expand capabilities'])}.",
            "status": random.choice(PROJECT_STATUSES),
            "priority": random.choice(PRIORITIES),
            "start_date": random_date(2025, 2026),
            "end_date": random_date(2026, 2027),
            "budget": round(random.randint(10000, 500000), 2),
            "manager_id": random.randint(1, 20),
            "client": random_company(),
            "created_at": random_datetime(),
        },
    },
    "tasks": {
        "path": "/tasks",
        "method": "POST",
        "generator": lambda i: {
            "title": f"{random.choice(['Review', 'Implement', 'Test', 'Document', 'Deploy', 'Design', 'Analyze', 'Optimize'])} {random.choice(['user module', 'payment flow', 'reporting', 'API endpoints', 'database schema', 'UI components', 'security layer', 'integration'])}",
            "description": f"Task for {random.choice(['sprint planning', 'release preparation', 'bug fix', 'feature development', 'performance improvement'])}.",
            "status": random.choice(TASK_STATUSES),
            "priority": random.choice(PRIORITIES),
            "due_date": random_date(2026, 2027),
            "assigned_to": random.randint(1, 20),
            "project_id": random.randint(1, 30),
            "estimated_hours": round(random.uniform(1, 40), 1),
            "created_at": random_datetime(),
        },
    },
    "invoices": {
        "path": "/invoices",
        "method": "POST",
        "generator": lambda i: {
            "invoice_number": f"INV-{random.randint(10000, 99999)}",
            "client_name": random_company(),
            "client_email": random_email(random.choice(FIRST_NAMES), random.choice(LAST_NAMES)),
            "amount": round(random.randint(500, 50000), 2),
            "tax_amount": round(random.uniform(50, 5000), 2),
            "total": round(random.randint(550, 55000), 2),
            "status": random.choice(INVOICE_STATUSES),
            "issue_date": random_date(2025, 2026),
            "due_date": random_date(2026, 2027),
            "paid_date": random_date(2026, 2027) if random.choice([True, False]) else None,
            "description": f"Invoice for {random.choice(['monthly subscription', 'professional services', 'license renewal', 'support contract', 'training services'])}.",
            "created_at": random_datetime(),
        },
    },
    "products": {
        "path": "/products",
        "method": "POST",
        "generator": lambda i: {
            "name": f"{random.choice(['Pro', 'Enterprise', 'Starter', 'Ultimate', 'Team', 'Business'])} {random.choice(['Plan', 'License', 'Package', 'Suite', 'Module', 'Add-on'])}",
            "description": f"{random.choice(['Full-featured', 'Scalable', 'Secure', 'Cloud-based', 'AI-powered'])} solution for {random.choice(['small teams', 'enterprises', 'startups', 'agencies', 'developers'])}.",
            "category": random.choice(PRODUCT_CATEGORIES),
            "price": round(random.uniform(9.99, 999.99), 2),
            "cost": round(random.uniform(5, 500), 2),
            "sku": f"PRD-{random_string(6).upper()}",
            "is_active": random.choice([True, True, True, False]),
            "stock_quantity": random.randint(0, 1000),
            "created_at": random_datetime(),
        },
    },
    "events": {
        "path": "/events",
        "method": "POST",
        "generator": lambda i: {
            "title": f"{random.choice(['Team Standup', 'Client Meeting', 'Product Review', 'Sprint Planning', 'Quarter Review', 'Training Session', 'Workshop', 'Webinar'])}",
            "description": f"Event for {random.choice(['project kickoff', 'status update', 'stakeholder alignment', 'knowledge sharing', 'process improvement'])}.",
            "start_time": random_datetime(2026, 2027),
            "end_time": random_datetime(2026, 2027),
            "location": random.choice(["Conference Room A", "Zoom", "Office", "Client Site", "Offsite"]),
            "attendees": [random_email(random.choice(FIRST_NAMES), random.choice(LAST_NAMES)) for _ in range(random.randint(2, 8))],
            "organizer": random_name(),
            "created_at": random_datetime(),
        },
    },
    "notes": {
        "path": "/notes",
        "method": "POST",
        "generator": lambda i: {
            "content": f"{random.choice(['Discussed requirements', 'Follow-up needed', 'Positive feedback', 'Concerns raised', 'Next steps agreed', 'Action items identified'])} regarding {random.choice(['project timeline', 'budget', 'technical approach', 'resource allocation', 'risk mitigation'])}.",
            "related_to": random.choice(["lead", "contact", "account", "opportunity", "ticket"]),
            "related_id": random.randint(1, 100),
            "author_id": random.randint(1, 20),
            "is_pinned": random.choice([True, False]),
            "created_at": random_datetime(),
        },
    },
    "notifications": {
        "path": "/notifications",
        "method": "POST",
        "generator": lambda i: {
            "title": random.choice(["New lead assigned", "Ticket updated", "Invoice due soon", "Task completed", "Meeting reminder", "Project milestone reached"]),
            "message": f"{random.choice(['Please review', 'Action required', 'Status update', 'Important alert', 'FYI'])}: {random.choice(['deadline approaching', 'new comment added', 'priority changed', 'assignment updated'])}.",
            "type": random.choice(["info", "warning", "success", "error"]),
            "is_read": random.choice([True, False]),
            "user_id": random.randint(1, 20),
            "link": f"/{random.choice(['leads', 'tickets', 'tasks', 'projects', 'invoices'])}/{random.randint(1, 100)}",
            "created_at": random_datetime(2025, 2026),
        },
    },
    "reports": {
        "path": "/reports",
        "method": "POST",
        "generator": lambda i: {
            "name": f"{random.choice(['Sales', 'Marketing', 'Support', 'Financial', 'Operational', 'Technical'])} {random.choice(['Summary', 'Analysis', 'Forecast', 'Performance', 'Trend', 'Dashboard'])}",
            "description": f"Report covering {random.choice(['Q1 2026', 'Q2 2026', 'last 30 days', 'last quarter', 'year to date', 'custom period'])}.",
            "type": random.choice(["sales", "marketing", "support", "financial", "operational", "custom"]),
            "filters": {"date_range": "last_30_days", "group_by": random.choice(["day", "week", "month"])},
            "created_by": random.randint(1, 20),
            "is_scheduled": random.choice([True, False]),
            "schedule": random.choice(["daily", "weekly", "monthly"]),
            "created_at": random_datetime(),
        },
    },
    "workflows": {
        "path": "/workflows",
        "method": "POST",
        "generator": lambda i: {
            "name": f"{random.choice(['Lead Nurture', 'Onboarding', 'Escalation', 'Approval', 'Renewal', 'Follow-up'])} Workflow",
            "description": f"Automated workflow for {random.choice(['new leads', 'customer onboarding', 'support escalation', 'contract approval', 'subscription renewal', 'post-sale follow-up'])}.",
            "trigger": random.choice(["record_created", "status_changed", "date_reached", "manual", "scheduled"]),
            "actions": [
                {"type": "send_email", "template": random.choice(["welcome", "follow_up", "reminder", "notification"])},
                {"type": "create_task", "assignee": random.randint(1, 20)},
            ],
            "is_active": random.choice([True, True, False]),
            "created_at": random_datetime(),
        },
    },
    "settings": {
        "path": "/settings",
        "method": "POST",
        "generator": lambda i: {
            "key": random.choice(["company_name", "timezone", "date_format", "currency", "language", "theme", "email_notifications", "auto_assign"]),
            "value": random.choice(["APEX-OS", "America/New_York", "MM/DD/YYYY", "USD", "en", "dark", "true", "false"]),
            "category": random.choice(["general", "localization", "notifications", "security", "integrations"]),
            "description": f"Setting for {random.choice(['company branding', 'user preferences', 'system behavior', 'security policy', 'third-party integration'])}.",
            "updated_at": random_datetime(2025, 2026),
        },
    },
    "audit_logs": {
        "path": "/audit_logs",
        "method": "POST",
        "generator": lambda i: {
            "action": random.choice(["create", "update", "delete", "login", "logout", "export", "import"]),
            "entity_type": random.choice(["user", "lead", "contact", "account", "opportunity", "ticket", "project", "task"]),
            "entity_id": random.randint(1, 100),
            "user_id": random.randint(1, 20),
            "details": f"{random.choice(['Record created', 'Field modified', 'Record removed', 'User authenticated', 'Data exported'])}",
            "ip_address": f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "created_at": random_datetime(2025, 2026),
        },
    },
    "integrations": {
        "path": "/integrations",
        "method": "POST",
        "generator": lambda i: {
            "name": random.choice(["Slack", "Salesforce", "HubSpot", "Zapier", "Stripe", "Twilio", "SendGrid", "Jira"]),
            "type": random.choice(["crm", "communication", "payment", "email", "project_management", "automation"]),
            "status": random.choice(["active", "inactive", "error", "pending"]),
            "config": {"api_key": random_string(32), "webhook_url": f"https://hooks.{random_string(8)}.com/events"},
            "last_sync": random_datetime(2025, 2026),
            "created_at": random_datetime(),
        },
    },
    "documents": {
        "path": "/documents",
        "method": "POST",
        "generator": lambda i: {
            "name": f"{random.choice(['Contract', 'Proposal', 'Report', 'Invoice', 'Agreement', 'Specification', 'Manual', 'Guide'])} - {random_company()}",
            "type": random.choice(["pdf", "docx", "xlsx", "pptx", "txt", "md"]),
            "size": random.randint(10000, 10000000),
            "url": f"https://storage.example.com/docs/{random_string(16)}",
            "category": random.choice(["legal", "sales", "marketing", "technical", "financial", "hr"]),
            "tags": [random.choice(["important", "draft", "final", "archived", "review", "approved"]) for _ in range(random.randint(1, 3))],
            "uploaded_by": random.randint(1, 20),
            "created_at": random_datetime(),
        },
    },
    "campaigns": {
        "path": "/campaigns",
        "method": "POST",
        "generator": lambda i: {
            "name": f"{random.choice(['Q1 Launch', 'Summer Sale', 'Product Update', 'Webinar Series', 'Newsletter', 'Referral Program'])} 2026",
            "type": random.choice(["email", "social", "ppc", "content", "event", "webinar"]),
            "status": random.choice(["draft", "active", "paused", "completed", "cancelled"]),
            "start_date": random_date(2026, 2027),
            "end_date": random_date(2026, 2027),
            "budget": round(random.randint(1000, 100000), 2),
            "spent": round(random.randint(0, 50000), 2),
            "impressions": random.randint(1000, 1000000),
            "clicks": random.randint(100, 50000),
            "conversions": random.randint(10, 5000),
            "created_at": random_datetime(),
        },
    },
    "deals": {
        "path": "/deals",
        "method": "POST",
        "generator": lambda i: {
            "name": f"{random_company()} - {random.choice(['Annual Contract', 'Multi-year Deal', 'Expansion', 'Renewal', 'New Business'])}",
            "value": round(random.randint(10000, 1000000), 2),
            "stage": random.choice(["prospecting", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"]),
            "probability": random.randint(5, 95),
            "close_date": random_date(2026, 2027),
            "account_id": random.randint(1, 50),
            "contact_id": random.randint(1, 100),
            "assigned_to": random.randint(1, 20),
            "source": random.choice(LEAD_SOURCES),
            "created_at": random_datetime(),
        },
    },
}

# ── Seeding Logic ──────────────────────────────────────────────────────────────

def check_endpoint_exists(endpoint_path: str) -> Tuple[bool, Any]:
    """Check if endpoint exists and return its data."""
    url = f"{BASE_URL}{endpoint_path}"
    resp, err = make_request("GET", url)
    if err:
        return False, None
    if resp is None:
        return False, None
    if resp.status_code == 200:
        try:
            return True, resp.json()
        except (json.JSONDecodeError, ValueError):
            return True, None
    return False, None

def seed_endpoint(name: str, config: Dict, count: int = 10) -> Dict[str, Any]:
    """Seed a single endpoint with test data."""
    result = {
        "endpoint": name,
        "path": config["path"],
        "seeded": 0,
        "skipped": False,
        "errors": [],
    }

    # Check if endpoint exists
    exists, data = check_endpoint_exists(config["path"])
    if not exists:
        result["errors"].append(f"Endpoint not accessible (GET {config['path']} failed)")
        return result

    # Check if already has data
    if data is not None and has_existing_data(data):
        result["skipped"] = True
        return result

    # Seed items
    url = f"{BASE_URL}{config['path']}"
    for i in range(count):
        payload = config["generator"](i)
        resp, err = make_request(config["method"], url, json=payload)
        if err:
            result["errors"].append(f"Item {i+1}: {str(err)}")
            continue
        if resp is None:
            result["errors"].append(f"Item {i+1}: No response")
            continue
        if resp.status_code in (200, 201, 202):
            result["seeded"] += 1
        else:
            result["errors"].append(f"Item {i+1}: HTTP {resp.status_code} - {resp.text[:200]}")

    return result

def print_summary(results: List[Dict[str, Any]]) -> None:
    """Print a formatted summary of seeding results."""
    print("\n" + "=" * 70)
    print("SEED DATA SUMMARY")
    print("=" * 70)

    total_seeded = 0
    total_skipped = 0
    total_errors = 0

    for r in results:
        status_icon = "✓" if r["seeded"] > 0 else "⊘" if r["skipped"] else "✗"
        status_text = f"Seeded {r['seeded']}" if r["seeded"] > 0 else "Skipped (has data)" if r["skipped"] else "Failed"
        print(f"  {status_icon} {r['endpoint']:20s} {r['path']:25s} {status_text}")

        if r["errors"]:
            for err in r["errors"][:3]:
                print(f"      ERROR: {err}")
            if len(r["errors"]) > 3:
                print(f"      ... and {len(r['errors']) - 3} more errors")

        total_seeded += r["seeded"]
        total_skipped += 1 if r["skipped"] else 0
        total_errors += len(r["errors"])

    print("-" * 70)
    print(f"  Total seeded:  {total_seeded}")
    print(f"  Total skipped: {total_skipped}")
    print(f"  Total errors:  {total_errors}")
    print("=" * 70 + "\n")

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    """Main entry point for the seed script."""
    print(f"APEX-OS Business Platform - Seed Data Script v2")
    print(f"Target: {BASE_URL}")
    print(f"Endpoints: {len(ENDPOINTS)}")
    print(f"Items per endpoint: 10+")
    print()

    results = []
    for name, config in ENDPOINTS.items():
        print(f"  Processing {name}...", end=" ", flush=True)
        result = seed_endpoint(name, config, count=12)
        results.append(result)
        if result["seeded"] > 0:
            print(f"seeded {result['seeded']} items")
        elif result["skipped"]:
            print("skipped (already has data)")
        else:
            print(f"failed ({len(result['errors'])} errors)")

    print_summary(results)

    # Exit with error code if all failed
    if all(r["seeded"] == 0 and not r["skipped"] for r in results):
        print("ERROR: No data was seeded. Check API connectivity.")
        sys.exit(1)

if __name__ == "__main__":
    main()
