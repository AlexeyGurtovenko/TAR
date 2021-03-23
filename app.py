from flask import Flask, redirect, url_for, render_template, request, session, flash
import os
from datetime import timezone, timedelta
from tardriver import TarDriver
import logging
import threading


TOKEN = #TRELLO USER TOKEN
API_KEY = #TRELLO USER API KEY


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.permanent_session_lifetime = timedelta(minutes=1)
remove_pattern = str.maketrans(' +.!@#$%^&*()_{[]}|,<>;:"/', '--------------------------')


@app.route("/", methods=["POST", "GET"])
@app.route("/projects", methods=["POST", "GET"])
def projects():
    if request.method == "POST":
        new_project_name = request.form["project_name"]
        new_project_desc = request.form["project_description"]
        tar.create_new_project(project_template = tar.basic_template, project_name = new_project_name, project_description = new_project_desc)
    
    return render_template("projects.html", tar_driver = tar, remove=remove_pattern)


@app.route("/team")
def team():
    return render_template("team.html", tar_driver = tar, remove=remove_pattern)


@app.route("/settings", methods=["POST", "GET"])
def settings():
    if request.method == "POST":
        work_hours = request.form.getlist('work-hours')
        lunch_hours = request.form.getlist('lunch-hours')
        workdays = request.form.getlist('work-days') 
        database_update = request.form.getlist('database-update-period') 
        
        if len(work_hours) > 0:
            tar.set_workhours(workhours = work_hours)

        if len(lunch_hours) > 0:
            tar.set_lunch_hours(lunch_hours = lunch_hours)

        if len(workdays) > 0:
            tar.set_workdays(workdays = workdays[0])
        
        if len(database_update) > 0:
            tar.set_database_update_period(database_update[0])            

    return render_template("settings.html", tar_driver = tar)


@app.route("/reports", methods=["POST", "GET"])
def reports():
    if request.method == "POST":
        boards = request.form.getlist('boards')
        lists = request.form.getlist('lists')
        members = request.form.getlist('members')
        tar.filter_dates.clear()
        tar.filter_dates.append(request.form.getlist('report-dates')[0].translate(str.maketrans('T',' ')))
        tar.filter_dates.append(request.form.getlist('report-dates')[1].translate(str.maketrans('T',' ')))
        print(tar.filter_dates)

        if len(boards) > 0 and len(lists) > 0 and len(members) > 0:
            tar.get_project_report(board_id = boards[0], lists = lists, members = members)
            return render_template("report.html", tar_driver = tar)
        
    return render_template("reports.html", tar_driver = tar, remove=remove_pattern)




if __name__ == "__main__":
    tar = TarDriver(trello_apiKey = API_KEY, trello_token = TOKEN, local_timezone = 'Asia/Tomsk')

    #thread_updating_database = threading.Thread(target = tar.update_database, args=[False, ])
    #thread_running_flask = threading.Thread(target = app.run)

    #thread_updating_database.start()
    #thread_running_flask.start()

    tar.fill_database()

    app.run()





"""
@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        session.permanent = True
        uName = request.form["nm"]
        session["user"] = uName
        return redirect(url_for("user"))
    else:
        if "user" in session:
           return redirect(url_for("user")) 
        return render_template("login.html")


@app.route("/calendar")
def calendar():
    return render_template("calendar.html")

@app.route("/user")
def user():
    if "user" in session:
        user = session["user"]
        return render_template("user.html")
    else:
        return render_template("login.html") 


@app.route("/logout")
def logout():
    session.pop("user", None)
    return render_template("login.html") 
"""