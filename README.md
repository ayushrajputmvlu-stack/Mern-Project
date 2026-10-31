# Digital Record System for Community Health Workers

A local learning/demo project built with Flask, HTML/CSS/JavaScript, and MySQL.

## Features
- Login with hashed passwords and session-based access
- Dashboard counts and recently registered people
- Add, search, view, and edit person records
- Blood group, allergies, health issues, contact information
- Follow-up scheduling and status updates
- Parameterized SQL queries, basic CSRF token checks, and server-side validation

## Before you start
Use fictional data for a college demo. This project is not certified for real patient data or production use. For real deployment, get a security/privacy review, use HTTPS, backups, least-privilege accounts, stronger monitoring, and applicable legal approvals.

## 1. Install software
Install Python 3.11+ and MySQL Server. VS Code is your editor. MySQL Workbench is optional but useful.

## 2. Create the database
Open MySQL Workbench or the MySQL command-line client and run the entire `database.sql` script.

Create a dedicated database user (adjust port if your server uses 3306 instead of 3307):

```sql
CREATE USER 'health_app'@'localhost' IDENTIFIED BY 'choose_a_strong_database_password';
GRANT SELECT, INSERT, UPDATE ON community_health_db.* TO 'health_app'@'localhost';
GRANT SELECT, INSERT, UPDATE ON community_health_db.followups TO 'health_app'@'localhost';
FLUSH PRIVILEGES;
```

Note: The first grant already applies to all tables in the database; the second grant is unnecessary but harmless on MySQL versions that allow it. If you use `127.0.0.1`, adjust the host account if needed. For this demo, use `localhost` in DB_HOST.

## 3. Configure environment
In the project folder, copy `.env.example` to a new file named `.env`. Set DB_PASSWORD to the password for the `health_app` database user. Set DB_PORT to your configured MySQL port (the earlier setup used 3307; if you kept 3306, change it to 3306).

Generate a long random Flask secret and replace SECRET_KEY. Do not share `.env` or commit it to GitHub.

## 4. Install Python packages
Open a terminal in this folder:

```powershell
py -m venv venv
venv\Scripts\activate
py -m pip install -r requirements.txt
```

If `py` is unavailable, try `python` instead.

## 5. Create the first administrator
Run:

```powershell
py create_admin.py
```

Enter a name, email, and a strong password when prompted. Password characters are not shown. Keep the login details private. The script creates a hashed password; it does not store the password in plain text.

## 6. Start the website

```powershell
py app.py
```

Open `http://127.0.0.1:5000` in your browser and sign in with the administrator account you created.

## Troubleshooting
- **Can't connect to MySQL:** Confirm MySQL service is running and DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and DB_NAME in `.env` are correct.
- **Access denied:** Confirm the `health_app` user and grants exist, and that the password matches `.env`.
- **Unknown database:** Run `database.sql` in MySQL.
- **Port 3306 warning:** Use the port shown in MySQL Configurator; this project defaults to 3307 because that was selected during the guided setup.
- **`py` not recognized:** Try `python` or reinstall Python with PATH enabled.

## Important limitations
This is a college-project starter, not a production-ready health records platform. Before storing real health data, implement a formal security review, HTTPS deployment, robust audit logs, backup/restore testing, account lockout/rate limiting, stricter role permissions, and applicable privacy/consent processes. Avoid entering unnecessary sensitive information.
