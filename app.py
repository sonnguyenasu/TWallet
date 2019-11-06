import mysql.connector as mc
from flask import Flask, render_template, redirect, jsonify, request, session
from helper import apology,login_required,lookup
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
app = Flask(__name__)
mydb = mc.connect(
  host = "localhost",
  user = "root",
  password = "password",
  database = "mydatabase"
)
# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

cursor = mydb.cursor()

@app.route("/")
@login_required
def index():
  id = session["user_id"]
  cursor.execute("SELECT * FROM users WHERE id = {}".format(id))
  rows = cursor.fetchall()
  return render_template("account.html",rows=rows)

@app.route("/login",methods=["GET","POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        cursor.execute("SELECT * FROM users WHERE user = %s",
                          (request.form.get("username"),))
        rows = cursor.fetchall()
        
        mydb.commit()
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            return apology("invalid username and/or password", 403)
        
        # Remember which user has logged in
        session["user_id"] = rows[0][0]
        
        # Redirect user to home page
        
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")



@app.route("/register",methods=["GET","POST"])
def register():
  if request.method == "GET":
    return render_template("register.html")
  else:
    user = request.form.get("username")
    pwd = request.form.get("password")
    cf = request.form.get("confirmation")
    if pwd != cf:
      return apology("Please confirmed password correctly")
    try:  
      cursor.execute("INSERT INTO users(user,hash) VALUES(%s,%s)",(user,generate_password_hash(pwd)))
      mydb.commit()
      return redirect("/login")
    except:
      return apology("Sorry, the username is already taken")

@app.route("/account")
@login_required
def account():
  cursor.execute("SELECT * FROM users WHERE id={}".format(session['user_id']))
  rows = cursor.fetchall()
  return render_template("account.html",rows=rows)

@app.route("/pwd",methods=["GET","POST"])
@login_required
def change():
  if request.method == "GET":
    return render_template("change.html")
  else:
    old = request.form.get("oldpwd")
    new = request.form.get("password")
    confirm = request.form.get("confirmation")
    cursor.execute("SELECT hash FROM users WHERE id={}".format(session["user_id"]))
    pwd = cursor.fetchall()
    trueOld=pwd[0][0]
    if not check_password_hash(trueOld,old):
      return render_template("change.html",cash=trueOld,cash1=old)
    elif new != confirm:
      return apology("The new password does not match")
    else:
      cursor.execute("UPDATE users SET hash=%s WHERE id=%s",(generate_password_hash(new),session['user_id']))
      mydb.commit()
      return redirect("/")

@app.route("/search",methods=["GET","POST"])
@login_required
def search():
  if request.method == "GET":
    return render_template("search.html")
  else:
    if not request.form.get("type") or not request.form.get("query"):
      return apology("MISSING A FIELD")
    q = request.form.get("query")
    if request.form.get("type") == "time":
      type = f"time LIKE '%{q}%'"
    elif request.form.get("type") == "category":
      type = f"cat LIKE '%{q}%'"
    cursor.execute(f"SELECT user,cat,amount,price,time FROM writehist JOIN users ON writehist.user_id=users.id WHERE users.id={session['user_id']} HAVING {type}")
    rows = cursor.fetchall()
    sum=0
    for row in rows:
      sum += row[2]*row[3]
    return render_template("read.html",rows=rows,sum=sum)

@app.route("/read")
@login_required
def read():
  cursor.execute(f"SELECT user,cat,amount,price,time FROM writehist JOIN users ON writehist.user_id=users.id WHERE users.id={session['user_id']} ORDER BY time")
  content=cursor.fetchall()
  sum=0
  for row in content:
    sum += row[2]*row[3]
  return render_template("read.html",rows=content,sum=sum)

@app.route("/write", methods=["GET","POST"])
@login_required
def write():
  if request.method == "GET":
    return render_template("write.html")
  else:
    cat = request.form.get("category")
    amount = request.form.get("amount")
    price = request.form.get("price")
    cursor.execute(f"INSERT INTO writehist(user_id,cat,amount,price) VALUES('{session['user_id']}','{cat}','{amount}','{price}')")
    mydb.commit()
    return redirect("/")

@app.route("/comprehend",methods=["GET","POST"])
@login_required
def comprehend():
  if request.method == "GET":
    return render_template("comprehend.html")
  else:
    now = datetime.now()
    lower = now - timedelta(days = 7)
    if request.form.get("type") == "time":
      session['status']=1
      cursor.execute(f"SELECT time,SUM(price*amount) FROM writehist WHERE user_id={session['user_id']} GROUP BY DATE(time) HAVING time > '{lower}'")
      data = cursor.fetchall()
      xs = (row[0].strftime("%d/%m/%Y") for row in data)
      x = np.arange(len(data))
      y = [row[1] for row in data]
      plt.plot(x,y)
      plt.xticks(x, xs)
      sum=0
      for row in data:
        sum += row[1]
    else:
      session['status']=0
      cursor.execute(f"SELECT cat,SUM(price*amount) FROM writehist WHERE user_id={session['user_id']} GROUP BY cat")
      data = cursor.fetchall()
      sum=0
      for row in data:
        sum += row[1]
      xs = (row[0] for row in data)
      x = np.arange(len(data))
      y = [row[1] for row in data]
      plt.barh(x,y)
      plt.yticks(x, xs)
    plt.savefig("static/test.png")
    plt.close()
    return render_template("comprehended.html",data = data,rows= data,sum=sum)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
