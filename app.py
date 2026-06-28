from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime


app = Flask(__name__)

app.secret_key = "securedesk123"
def init_db():

    conn = sqlite3.connect('database.db', timeout=10)

    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tickets(
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       title TEXT,
       description TEXT,
       category TEXT,
       priority TEXT,
       status TEXT,
       assigned_to TEXT,
       created_at TEXT           
    )
    ''')

    conn.commit()
    conn.close()

def detect_category(title, description):

    text = (title + " " + description).lower()

    network_keywords = [
        "wifi",
        "internet",
        "network",
        "router"
    ]

    hardware_keywords = [
        "laptop",
        "printer",
        "keyboard",
        "mouse",
        "monitor"
    ]

    software_keywords = [
        "software",
        "excel",
        "word",
        "application",
        "outlook"
    ]

    security_keywords = [
        "password",
        "virus",
        "hack",
        "security",
        "login"
    ]

    for word in network_keywords:
        if word in text:
            return "Network"

    for word in hardware_keywords:
        if word in text:
            return "Hardware"

    for word in software_keywords:
        if word in text:
            return "Software"

    for word in security_keywords:
        if word in text:
            return "Security"

    return "General"
@app.route('/')
def landing():
    return render_template('landing.html')


@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':
        print("FORM SUBMITTED")
 
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
            (name, email, password, role)
        )

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

             session['name'] = user[1]
             session['email'] = user[2]
             session['role'] = user[4]

        if user[4] == "Admin":
           return redirect('/admin-dashboard')
        else:
           return redirect('/dashboard')



    return render_template('login.html')

@app.route('/dashboard')
def dashboard():

    if 'name' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # User tickets
    cursor.execute("""
    SELECT *
    FROM tickets
    ORDER BY id DESC
    """)
    tickets = cursor.fetchall()

    # Latest assigned engineer
    cursor.execute("""
    SELECT assigned_to
    FROM tickets
    WHERE assigned_to != 'Not Assigned'
    ORDER BY id DESC
    LIMIT 1
    """)
    engineer = cursor.fetchone()

    # Recent Activity
    cursor.execute("""
    SELECT id,status
    FROM tickets
    ORDER BY id DESC
    LIMIT 5
    """)
    recent_activity = cursor.fetchall()

    # Pending Actions
    cursor.execute("""
    SELECT id,title
    FROM tickets
    WHERE status='Open'
    ORDER BY id DESC
    LIMIT 5
    """)
    pending_actions = cursor.fetchall()

    # KPI Cards
    cursor.execute("""
    SELECT COUNT(*)
    FROM tickets
    """)
    total_count = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM tickets
    WHERE status='Open'
    """)
    open_count = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM tickets
    WHERE status='In Progress'
    """)
    progress_count = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM tickets
    WHERE status='Resolved'
    """)
    resolved_count = cursor.fetchone()[0]

    conn.close()

    return render_template(
        'dashboard.html',
        tickets=tickets,
        total_count=total_count,
        open_count=open_count,
        progress_count=progress_count,
        resolved_count=resolved_count,
        engineer=engineer,
        recent_activity=recent_activity,
        pending_actions=pending_actions
    )
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

@app.route('/create-ticket', methods=['GET', 'POST'])
def create_ticket():

    if request.method == 'POST':

        title = request.form['title']
        description = request.form['description']
        priority = request.form['priority']
        
        created_at = datetime.now().strftime("%Y-%m-%d")

        category = detect_category(
            title,
            description
        )

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        print("Detected Category:", category)
 
        cursor.execute(
        '''
        INSERT INTO tickets
        (title, description, category, priority, status, assigned_to,created_at)
        VALUES (?, ?, ?, ?, ?, ?,?)
        ''',
        (
        title,
        description,
        category,
        priority,
        "Open",
        "Not Assigned",
        datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        )

        conn.commit()
        conn.close()

        return redirect('/my-tickets')

    return render_template('create_ticket.html')

@app.route('/my-tickets')
def my_tickets():

    conn = sqlite3.connect('database.db')

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tickets")

    tickets = cursor.fetchall()

    conn.close()

    return render_template(
        'my_tickets.html',
        tickets=tickets
    )

@app.route('/admin-dashboard')
def admin_dashboard():

    if 'role' not in session or session['role'] != "Admin":
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # ===========================
    # Team Availability
    # ===========================

    cursor.execute("""

    SELECT

    engineers.name,

    COUNT(

    CASE

    WHEN tickets.status='Open'
    OR tickets.status='In Progress'

    THEN 1

    END

    )

    FROM engineers

    LEFT JOIN tickets

    ON engineers.name=tickets.assigned_to

    GROUP BY engineers.name

    """)

    team_status = cursor.fetchall()

    # ===========================
    # Ticket Status
    # ===========================

    cursor.execute("""

    SELECT status,COUNT(*)

    FROM tickets

    GROUP BY status

    """)

    status_data = dict(cursor.fetchall())

    open_count = status_data.get("Open", 0)
    progress_count = status_data.get("In Progress", 0)
    resolved_count = status_data.get("Resolved", 0)

    # ===========================
    # Category Count
    # ===========================

    cursor.execute("""

    SELECT category,COUNT(*)

    FROM tickets

    GROUP BY category

    """)

    category_data = dict(cursor.fetchall())

    hardware_count = category_data.get("Hardware", 0)
    software_count = category_data.get("Software", 0)
    network_count = category_data.get("Network", 0)
    other_count = category_data.get("Other", 0)

    # ===========================
    # Overall Counts
    # ===========================

    cursor.execute("SELECT COUNT(*) FROM tickets")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='Resolved'")
    resolved = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE assigned_to='Not Assigned'")
    unassigned = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM engineers")
    total_engineers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets")
    total_tickets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='Open'")
    active_incidents = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status='Resolved'")
    resolved_today = cursor.fetchone()[0]

    # ===========================
    # Recent Tickets
    # ===========================

    cursor.execute("""

    SELECT *

    FROM tickets

    ORDER BY id DESC

    LIMIT 10

    """)

    recent_tickets = cursor.fetchall()

    # ===========================
    # Activity Feed
    # ===========================

    cursor.execute("""

    SELECT id,title,status,assigned_to

    FROM tickets

    ORDER BY id DESC

    LIMIT 5

    """)

    activity_feed = cursor.fetchall()

    # ===========================
    # Engineer Workload
    # ===========================

    cursor.execute("""

    SELECT assigned_to,

    COUNT(*)

    FROM tickets

    WHERE assigned_to!='Not Assigned'

    GROUP BY assigned_to

    """)

    engineer_workload = cursor.fetchall()

    # Employee List

    cursor.execute("""
    SELECT id,name,email,password
    FROM users
    WHERE role='Employee'
    ORDER BY id
    """)

    employees = cursor.fetchall()

    # Technician List

    cursor.execute("""
    SELECT id,name,email,password
    FROM engineers
    ORDER BY id
    """)

    technicians = cursor.fetchall()

    # ===========================
    # SLA Monitor
    # ===========================

    cursor.execute("""

    SELECT id,priority,status,created_at

    FROM tickets

    WHERE status!='Resolved'

    ORDER BY id DESC

    LIMIT 5

    """)

    sla_tickets = cursor.fetchall()

    conn.close()

    return render_template(

        "admin_dashboard.html",

        total=total,
        open_count=open_count,
        progress_count=progress_count,
        resolved=resolved,
        resolved_count=resolved_count,
        unassigned=unassigned,

        recent_tickets=recent_tickets,
        engineer_workload=engineer_workload,
        activity_feed=activity_feed,
        sla_tickets=sla_tickets,

        hardware_count=hardware_count,
        software_count=software_count,
        network_count=network_count,
        other_count=other_count,

        total_engineers=total_engineers,
        total_tickets=total_tickets,
        active_incidents=active_incidents,
        resolved_today=resolved_today,
        

        team_status=team_status,
        employees=employees,
        technicians=technicians

    )

@app.route('/manage-tickets')
def manage_tickets():

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("""
    SELECT *
    FROM engineers
    """)

    engineers = c.fetchall()

    c.execute("SELECT * FROM tickets")
    tickets = c.fetchall()

    c.execute("SELECT * FROM engineers")
    engineers = c.fetchall()

    conn.close()

    return render_template(
        'manage_tickets.html',
        tickets=tickets,
        engineers=engineers
    )

@app.route('/resolve/<int:id>')
def resolve_ticket(id):

    conn = sqlite3.connect('database.db')

    cursor = conn.cursor()

    cursor.execute(
        '''
        UPDATE tickets
        SET status=?
        WHERE id=?
        ''',
        ('Resolved', id)
    )

    conn.commit()

    conn.close()

    return redirect('/manage-tickets')

@app.route('/progress/<int:id>')
def progress_ticket(id):

    conn = sqlite3.connect('database.db')

    cursor = conn.cursor()

    cursor.execute(
    '''
    UPDATE tickets
    SET status=?
    WHERE id=?
    ''',
    (
    "In Progress",
    id
    )
    )

    conn.commit()
    conn.close()

    return redirect('/manage-tickets')

@app.route('/assign_engineer/<int:ticket_id>', methods=['POST'])
def assign_engineer(ticket_id):

    engineer = request.form['engineer']

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("""
    UPDATE tickets
    SET assigned_to=?
    WHERE id=?
    """,(engineer,ticket_id))

    conn.commit()
    conn.close()

    return redirect('/manage-tickets')

@app.route('/reports')
def reports():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tickets")
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM tickets WHERE status='Open'"
    )
    open_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM tickets WHERE status='Resolved'"
    )
    resolved = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM tickets WHERE priority='High'"
    )
    high_priority = cursor.fetchone()[0]

    conn.close()

    return render_template(
        'reports.html',
        total=total,
        open_count=open_count,
        resolved=resolved,
        high_priority=high_priority
    )

@app.route('/engineer-login', methods=['GET','POST'])
def engineer_login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute("""
            SELECT * FROM engineers
            WHERE email=? AND password=?
        """,(email,password))

        engineer = c.fetchone()

        conn.close()

        if engineer:

            session['engineer_id'] = engineer[0]
            session['engineer_name'] = engineer[1]

            return redirect('/engineer-dashboard')

    return render_template('engineer_login.html')

@app.route('/engineer-dashboard')
def engineer_dashboard():

    # Login check
    if 'engineer_name' not in session:
        return redirect('/engineer-login')

    # Logged technician name
    engineer_name = session['engineer_name']

    print("Logged Technician :", engineer_name)

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # My Assigned Tickets
    c.execute("""
        SELECT *
        FROM tickets
        WHERE assigned_to=?
        ORDER BY id DESC
    """, (engineer_name,))

    tickets = c.fetchall()

    print("Tickets :", tickets)

    # Assigned Count
    c.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE assigned_to=?
    """, (engineer_name,))

    assigned_count = c.fetchone()[0]

    # Open Count
    c.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE assigned_to=?
        AND status='Open'
    """, (engineer_name,))

    open_count = c.fetchone()[0]

    # In Progress Count
    c.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE assigned_to=?
        AND status='In Progress'
    """, (engineer_name,))

    working_count = c.fetchone()[0]

    # Resolved Count
    c.execute("""
        SELECT COUNT(*)
        FROM tickets
        WHERE assigned_to=?
        AND status='Resolved'
    """, (engineer_name,))

    resolved_count = c.fetchone()[0]

    # Recent Activity
    c.execute("""
        SELECT id,status
        FROM tickets
        WHERE assigned_to=?
        ORDER BY id DESC
        LIMIT 5
    """, (engineer_name,))

    recent_activity = c.fetchall()

    conn.close()

    return render_template(
        "engineer_dashboard.html",
        tickets=tickets,
        assigned_count=assigned_count,
        open_count=open_count,
        working_count=working_count,
        resolved_count=resolved_count,
        recent_activity=recent_activity
    )

@app.route('/update-ticket-status', methods=['POST'])
def update_ticket_status():

    ticket_id = request.form['ticket_id']
    status = request.form['status']

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("""
    UPDATE tickets
    SET status=?
    WHERE id=?
    """, (status, ticket_id))

    conn.commit()
    conn.close()

    return redirect('/engineer-dashboard')

@app.route('/engineer-register',methods=['GET','POST'])
def engineer_register():

    if request.method=="POST":

        name=request.form["name"]
        email=request.form["email"]
        password=request.form["password"]

        conn=sqlite3.connect("database.db")
        cursor=conn.cursor()

        cursor.execute("""

        INSERT INTO engineers

        (name,email,password)

        VALUES(?,?,?)

        """,(name,email,password))

        conn.commit()
        conn.close()

        return redirect("/engineer-login")

    return render_template("engineer_register.html")
@app.route('/create-engineer', methods=['GET', 'POST'])
def create_engineer():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('securedesk.db')
        c = conn.cursor()

        c.execute("""
        INSERT INTO engineers(name,email,password)
        VALUES(?,?,?)
        """,(name,email,password))

        conn.commit()
        conn.close()

        return redirect('/create-engineer')


    conn = sqlite3.connect('securedesk.db')
    c = conn.cursor()

    c.execute("SELECT * FROM engineers")
    technicians = c.fetchall()

    conn.close()

    return render_template(
        'create_engineer.html',
        technicians=technicians
    )
@app.route('/delete-technician/<int:id>')
def delete_technician(id):

    conn = sqlite3.connect('securedesk.db')
    c = conn.cursor()

    c.execute(
        "DELETE FROM engineers WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect('/create-engineer')
@app.route('/edit-technician/<int:id>',
methods=['GET','POST'])

def edit_technician(id):

    conn = sqlite3.connect('securedesk.db')
    c = conn.cursor()

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        c.execute("""
        UPDATE engineers
        SET name=?,
            email=?,
            password=?
        WHERE id=?
        """,(name,email,password,id))

        conn.commit()
        conn.close()

        return redirect('/create-engineer')


    c.execute(
        "SELECT * FROM engineers WHERE id=?",
        (id,)
    )

    technician = c.fetchone()

    conn.close()

    return render_template(
        'edit_technician.html',
        technician=technician
    )
@app.route('/edit-ticket/<int:id>')
def edit_ticket(id):

    return redirect('/engineer-dashboard')
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
