from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
import random
from random import randint
import time
from datetime import datetime
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///decasaved.db")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":
        first_name = request.form.get("firstname")
        last_name = request.form.get("lastname")
        email = request.form.get("email")
        bank = request.form.get("bank")
        account_no = request.form.get("account")
        phone = request.form.get("phone")
        password = request.form.get("password")
        confirm = request.form.get("confirmpassword")
        if not first_name and not last_name and not email and not bank and not account_no and not phone and not password and not confirm:
            return apology("Field(s) cannot be left blank", 400)
        if(confirm != password):
            return apology("password mismatch", 400)

        hash = generate_password_hash(password, method= 'pbkdf2:sha256', salt_length = 8)
        deca_acct = randint(1000000000, 9999999999)
        balance = 0.00
        db.execute("INSERT INTO users (firstname, lastname, email, bank, account_no, phone_number, hash, deca_accountno, balance) VALUES (:first_name, :last_name, :email, :bank, :account_no, :phone, :hash, :deca_acct, :balance)", first_name=first_name, last_name=last_name, email=email, bank=bank, account_no=account_no, phone=phone, hash=hash, deca_acct =deca_acct, balance=balance)
        session_id= db.execute("SELECT id FROM users WHERE email=:email", email=email)
        session["user_id"] = session_id[0]["id"]
        return redirect("/login")
        

@app.route("/check", methods=["GET"])
def check():
    email = request.args.get("email")
    """Return true if email available, else false, in JSON format"""
    row = db.execute("SELECT * FROM users WHERE email=:email", email=email)
    if (len(row) < 1 and len(email) >= 1):
        return jsonify(True)
    else:
        return jsonify(False)

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    email= request.form.get("email")
    password= request.form.get("password")
    if request.method == "POST":
        if not email:
            return apology("email must be provided", 400)
        elif not password:
            return apology("must provide password", 400)
        rows= db.execute("SELECT * FROM users WHERE email=:email", email=email)
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("this user does not exist", 400)
        session["user_id"] = rows[0]["id"]
        
        # Grab user details
        userDetails = db.execute("SELECT * FROM users WHERE id= :id", id=session["user_id"])
        return render_template("user-dashboard.html", userDetails=userDetails)
    else:
        return render_template("login.html")

@app.route("/save", methods=["GET", "POST"])
@login_required
def save():
    if request.method == "GET":
        return render_template("save.html")
    elif request.method == "POST":
        now= datetime.now()
        result= request.get_json()
        samount=result["deposit_amount"]
        ref=result["reference"]
        wamount = ""
        print(samount)
        save_balance = db.execute("SELECT balance FROM users WHERE id=:id", id=session["user_id"])    
        new_balance = float(samount) + save_balance[0]['balance']
        print(new_balance)
        db.execute("UPDATE users SET balance=:new_balance WHERE id=:id", new_balance=new_balance, id=session["user_id"])
        db.execute("INSERT INTO tranzact(users_id, deposit, withdrawal, current_balance, 'time') VALUES(:users_id, :deposit, :withdrawal, :current_balance, :time)", users_id=session["user_id"], deposit=samount, withdrawal=wamount, current_balance=new_balance, time=now)
        
        # Grab user details
        userDetails = db.execute("SELECT * FROM users WHERE id= :id", id=session["user_id"])
        return redirect("/user-dashboard", userDetails=userDetails)

@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    if request.method == "GET":
        users = db.execute("SELECT firstname, bank, account_no FROM users where id=:id", id=session["user_id"])
        return render_template("withdraw.html", users=users)
    elif request.method == "POST":
        wamount = int(request.form.get("wamount"))
        now= datetime.now()
        try:
            int(request.form.get("wamount"))
        except:
            return apology("Withdrawals must be a positive value", 400)
        wamount = int(request.form.get("wamount"))
        samount = ""
        if wamount <= 0:
            return apology("Please Enter a positive value")
        balance = db.execute("SELECT balance FROM users WHERE id=:id", id=session["user_id"])
        if wamount > balance[0]["balance"]:
            return apology("Insufficient funds")
        new_balance = balance[0]["balance"] - wamount
        db.execute("UPDATE users SET balance=:new_balance WHERE id=:id", new_balance=new_balance, id=session["user_id"])
        db.execute("INSERT INTO tranzact(users_id, deposit, withdrawal, current_balance, 'time') VALUES(:users_id, :deposit, :withdrawal, :current_balance, :time)", users_id=session["user_id"], deposit=samount, withdrawal=wamount, current_balance=new_balance, time=now)
        
        # Grab user details
        userDetails = db.execute("SELECT * FROM users WHERE id= :id", id=session["user_id"])
        return render_template("user-dashboard.html", userDetails=userDetails)

@app.route("/transactions")
@login_required
def transactions():
    trans_history = db.execute("SELECT * FROM tranzact WHERE users_id = :users_id", users_id=session["user_id"])
    return render_template("transactions.html", transactions=trans_history)

@app.route("/faq", methods=["GET", "POST"])
def faq():
    if request.method == "GET":
        return render_template("faq.html")

@app.route("/user-dashboard", methods=["GET", "POST"])
@login_required
def user_dashboard():
    if request.method == "GET":
        
        # Grab user details
        # userDetails = db.execute("SELECT * FROM users WHERE id= :id", id=session["user_id"])
        return render_template("user-dashboard.html")
      
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot-password.html")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/")
