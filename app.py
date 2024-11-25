from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import random
import hashlib

app = Flask(__name__)
app.secret_key = 'supersecretkey'

def create_db():
    conn = sqlite3.connect('banking_app.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                        account_number INTEGER PRIMARY KEY, 
                        first_name TEXT, 
                        last_name TEXT,
                        phone_number TEXT,
                        id_number TEXT,
                        username TEXT,
                        password TEXT,
                        balance REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_number INTEGER, 
                        transaction_type TEXT, 
                        amount REAL, 
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_account_number():
    return random.randint(10000, 99999)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash("Please fill both the username and password fields", "error")
            return redirect(url_for('login'))

        hashed_password = hash_password(password)

        conn = sqlite3.connect('banking_app.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accounts WHERE username=? AND password=?", (username, hashed_password))
        account = cursor.fetchone()
        conn.close()

        if account:
            session['account_number'] = account[0]
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone_number = request.form['phone_number']
        id_number = request.form['id_number']
        username = request.form['username']
        password = request.form['password']

        if not first_name or not last_name or not phone_number or not id_number or not username or not password:
            flash("All fields must be filled!", "error")
            return redirect(url_for('create_account'))

        account_number = generate_account_number()
        hashed_password = hash_password(password)

        conn = sqlite3.connect('banking_app.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO accounts (account_number, first_name, last_name, phone_number, 
                          id_number, username, password, balance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                       (account_number, first_name, last_name, phone_number, id_number, username, hashed_password, 0.0))
        conn.commit()
        conn.close()

        flash(f"Account created successfully! Your account number is {account_number}", "success")
        return redirect(url_for('login'))

    return render_template('create_account.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'account_number' not in session:
        return redirect(url_for('login'))

    account_number = session['account_number']

    conn = sqlite3.connect('banking_app.db')
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, last_name, balance FROM accounts WHERE account_number=?", (account_number,))
    account = cursor.fetchone()

    # Fetch transaction history
    cursor.execute("SELECT transaction_type, amount, timestamp FROM transactions WHERE account_number=? ORDER BY timestamp DESC", (account_number,))
    transactions = cursor.fetchall()
    conn.close()

    if request.method == 'POST':
        amount = float(request.form['amount'])
        if 'deposit' in request.form:
            if amount <= 0:
                flash("Deposit amount must be positive.", "error")
            else:
                conn = sqlite3.connect('banking_app.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE accounts SET balance = balance + ? WHERE account_number=?", (amount, account_number))
                cursor.execute("INSERT INTO transactions (account_number, transaction_type, amount) VALUES (?, ?, ?)", 
                               (account_number, 'Deposit', amount))
                conn.commit()
                conn.close()
                flash(f"R{amount} deposited successfully.", "success")
        elif 'withdraw' in request.form:
            if amount <= 0:
                flash("Withdrawal amount must be positive.", "error")
            else:
                conn = sqlite3.connect('banking_app.db')
                cursor = conn.cursor()
                cursor.execute("SELECT balance FROM accounts WHERE account_number=?", (account_number,))
                balance = cursor.fetchone()[0]
                if amount > balance:
                    flash("Insufficient funds.", "error")
                else:
                    cursor.execute("UPDATE accounts SET balance = balance - ? WHERE account_number=?", (amount, account_number))
                    cursor.execute("INSERT INTO transactions (account_number, transaction_type, amount) VALUES (?, ?, ?)", 
                                   (account_number, 'Withdraw', amount))
                    conn.commit()
                    conn.close()
                    flash(f"R{amount} withdrawn successfully.", "success")
        elif 'transfer' in request.form:
            # Transfer logic
            recipient_account_number = int(request.form['recipient_account_number'])
            if recipient_account_number == account_number:
                flash("Cannot transfer to the same account.", "error")
            elif amount <= 0:
                flash("Transfer amount must be positive.", "error")
            else:
                conn = sqlite3.connect('banking_app.db')
                cursor = conn.cursor()
                cursor.execute("SELECT balance FROM accounts WHERE account_number=?", (account_number,))
                balance = cursor.fetchone()[0]
                if amount > balance:
                    flash("Insufficient funds.", "error")
                else:
                    # Deduct from sender
                    cursor.execute("UPDATE accounts SET balance = balance - ? WHERE account_number=?", (amount, account_number))
                    # Add to recipient
                    cursor.execute("UPDATE accounts SET balance = balance + ? WHERE account_number=?", (amount, recipient_account_number))
                    # Insert transaction records for both sender and receiver
                    cursor.execute("INSERT INTO transactions (account_number, transaction_type, amount) VALUES (?, ?, ?)", 
                                   (account_number, 'Transfer', -amount))
                    cursor.execute("INSERT INTO transactions (account_number, transaction_type, amount) VALUES (?, ?, ?)", 
                                   (recipient_account_number, 'Transfer', amount))
                    conn.commit()
                    conn.close()
                    flash(f"R{amount} transferred successfully.", "success")
        return redirect(url_for('dashboard'))

    return render_template('dashboard.html', account=account, transactions=transactions)

if __name__ == '__main__':
    create_db()
    app.run(debug=True)
