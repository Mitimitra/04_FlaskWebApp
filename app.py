from flask import Flask, render_template, request, redirect, session, jsonify
from datetime import date
import psycopg2

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def get_db_connection():
    return psycopg2.connect(
        database="MCPL01",
        host="dpg-d1h20lvgi27c73c75i9g-a.oregon-postgres.render.com",
        port="5432",
        user="mahesh",
        password="Jk3YQreoLTe05itpp3mz0vI4ssBCzB4x"
    )

@app.route("/")
def dashboard():
    if "emp_name" in session:
        return render_template("dashboard.html")
    else:
        return render_template("login.html", message="Your session has been timed out. Please Log in again.")
    

@app.route("/get_project_history_by_code")
def get_project_history_by_code():
    project_code = request.args.get("code")
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT pm."ProjectCode", pm."ProjectName", um."EmpName", ph."DateOfEntry",
               ph."EventDate", ph."Event", ph."Remarks"
        FROM "ProjectHistory" ph
        JOIN "ProjectMaster" pm ON ph."ProjectID" = pm."ProjectID"
        JOIN "UserMaster" um ON ph."UserID" = um."UserID"
        WHERE pm."ProjectCode" = %s
        ORDER BY ph."EventDate" DESC
    ''', (project_code,))

    records = []
    for idx, row in enumerate(cursor.fetchall()):
        records.append({
            "SrNo": idx + 1,
            "ProjectCode": row[0],
            "ProjectName": row[1],
            "EmpName": row[2],
            "DateOfEntry": row[3].strftime('%Y-%m-%d') if row[3] else '',
            "EventDate": row[4].strftime('%d %b %Y') if row[4] else '',
            "Event": row[5],
            "Remarks": row[6]
        })

    return jsonify(records)

    

@app.route("/project_hist", methods=["GET", "POST"])
def project_history():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT "ProjectCode", "ProjectName" FROM "ProjectMaster" ORDER BY "ProjectCode"')
    projects = [{"code": row[0], "name": row[1]} for row in cursor.fetchall()]
    today = date.today().strftime('%Y-%m-%d')

    if request.method == "POST":
        project_code = request.form['project_code']
        emp_name = session['emp_name']
        entry_date = request.form['entry_date']
        event_date = request.form['event_date']
        event_desc = request.form['event_desc']
        remarks = request.form['remarks']

        cursor.execute('SELECT "ProjectID" FROM "ProjectMaster" WHERE "ProjectCode" = %s', (project_code,))
        project_row = cursor.fetchone()
        project_id = project_row[0] if project_row else None

        cursor.execute('SELECT "UserID" FROM "UserMaster" WHERE "EmpName" = %s', (emp_name,))
        user_row = cursor.fetchone()
        user_id = user_row[0] if user_row else None
        

        if project_id and user_id:
            cursor.execute('''
                INSERT INTO "ProjectHistory"("ProjectID","UserID","DateOfEntry","EventDate","Event","Remarks")
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (project_id, user_id, entry_date, event_date, event_desc, remarks))
            conn.commit()
            message = "Record Saved Successfully"
        else:
            message = "Invalid Project or User"

        return render_template("project_history.html", 
                               message=message, 
                               projects=projects, 
                               today=today)

    return render_template("project_history.html", projects=projects, today=today)



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        print("In Login")
        org_code = request.form.get('org_code', '').strip().upper()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get OrganisationID from OrgCode
        cursor.execute('SELECT "OrganisationID" FROM "OrganisationMaster" WHERE "OrgCode" = %s', (org_code,))
        org = cursor.fetchone()

        if not org:
            conn.close()
            return render_template('login.html', error="Invalid Organization Code")

        org_id = org[0]

        # Validate user
        cursor.execute('''
            SELECT "EmpName", "UserName"
            FROM "UserMaster"
            WHERE "UserName" = %s AND "UserPWD" = %s AND "OrganisationID" = %s
        ''', (username, password, org_id))

        user = cursor.fetchone()
        conn.close()

        if user:
            session['username'] = user[1]
            session['emp_name'] = user[0]
            session['organisation_id'] = org_id
            return render_template('dashboard.html', message="User found")
        else:
            return render_template('login.html', error="Invalid Username or Password")

    return render_template("login.html")


@app.route("/validate_org")
def validate_org():
    org_code = request.args.get('org_code', '').strip().upper()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM "OrganisationMaster" WHERE "OrgCode" = %s', (org_code.upper(),))
    result = cursor.fetchone()
    print(result)
    conn.close()
    return jsonify({'valid': bool(result)})




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)