from gemini import get_ai_response
from flask import Flask, render_template, request,redirect,session,jsonify
from db import get_connection
app = Flask(__name__)
app.secret_key = ""
@app.route("/")
def home():
    return render_template("login.html")
@app.route("/register")
def register_page():
    return render_template("register.html")
@app.route("/login", methods=["POST"])
def login():
    
    email = request.form["email"]
    password = request.form["password"]
    connection=get_connection()
    cursor = connection.cursor()
    sql = """select * from users where email=:1 and password=:2"""
    cursor.execute(sql, (email, password))
    user = cursor.fetchone()
    cursor.close()
    connection.close()
    if user:
        session["email"] = user[2]
        session["name"] = user[1]
        return redirect("/dashboard")
    else:
        return "Invalid email or password"
    

@app.route("/register", methods=["POST"])
def register():
    print(request.form)
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    print(name,email,password)
    connection=get_connection()
    cursor = connection.cursor()
    sql = """insert into users(name,email,password,created_date) values(:1,:2,:3,sysdate)"""
    print(name,email,password)
    cursor.execute(sql, (name, email, password))
    print("insert executed")
    connection.commit()
    print("commit executed")
    cursor.close()
    connection.close()
    session["email"] = email
    session["name"] = name

    return redirect("/dashboard")
@app.route("/dashboard")
def dashboard():

    if "email" not in session:

        return redirect("/")

    return render_template("dashboard.html",name=session["name"])
@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()
    print(data)
    message = data["message"]
    print(message)

    ai_response = get_ai_response(message)

    print(ai_response)
    return jsonify({
        "response": ai_response
    })
if __name__ == "__main__":
    app.run(debug=True)