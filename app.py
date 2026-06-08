import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from google import genai
from google.genai import types
from db import get_db_connection
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "ThatoSecret1024SystemMasterKey")

# Configure the free Gemini API
client = genai.Client(api_key="AQ.Ab8RN6K6XQB-52ScmZd9aKWmGuITH955LlxSMYsNK_sw-TzxUw")

# 📂 Configure Secure File Upload Target Destination Mapping
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'xlsx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure target directories exist inside project directory layout
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    if "employee_id" in session: 
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"].strip()
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            # Explicitly select columns to verify mapping alignment
            cursor.execute("""
                SELECT EmployeeID, FirstName, Department, UserRole 
                FROM Dim_Employees 
                WHERE Email = ?
            """, (email,))
            user = cursor.fetchone()
            conn.close()
            
            if user and password == "mockhash":
                session.clear()
                
                # 🛡️ Safe Extraction explicitly utilizing exact SQL positional indices
                db_emp_id = user[0]
                db_first_name = user[1]
                db_dept = user[2]
                db_role = user[3]
                
                # Print to terminal console so you can see exactly what track is logging in
                print(f"DEBUG LOGIN -> Name: {db_first_name}, Role: {db_role}, Track Mapped: {db_dept}")
                
                session.update({
                    "employee_id": db_emp_id,
                    "first_name": db_first_name,
                    "department": db_dept,  # Sets 'Systems Development', 'Cloud Engineering', etc.
                    "role": db_role
                })
                return redirect(url_for("dashboard"))
            
        flash("Authentication failed. Invalid email signature or access credentials.")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "role" not in session:
        return redirect(url_for("login"))
        
    role = session["role"]
    emp_id = session.get("employee_id")
    emp_dept = session.get("department") # Get the logged-in user's track (e.g., 'Systems Development')
    current_now = datetime.now()
    
    conn = get_db_connection()
    unified_curriculum = []
    all_modules = []
    
    if conn:
        cursor = conn.cursor()
        
        # 1. Fetch modules based on user roles and curriculum track matches
        if role == 'Learner' and emp_dept:
            # Learners ONLY see modules matching their assigned department track
            cursor.execute("""
                SELECT ModuleID, ModuleName, Category, TimeLimitMinutes, DifficultyLevel, 
                       AssessmentType, IsTimed, WindowStartDate, WindowEndDate 
                FROM Dim_Modules
                WHERE Category = ?
            """, (emp_dept,))
        else:
            # Admins and Facilitators see ALL modules across all portfolios
            cursor.execute("""
                SELECT ModuleID, ModuleName, Category, TimeLimitMinutes, DifficultyLevel, 
                       AssessmentType, IsTimed, WindowStartDate, WindowEndDate 
                FROM Dim_Modules
            """)
        modules_raw = cursor.fetchall()
        
        # Build all_modules tracker list for admin panels dropdown
        all_modules = [{"ID": r[0], "Name": r[1]} for r in modules_raw]
        
        for mod in modules_raw:
            mod_id = mod[0]
            
            # Fetch content folders matching the active module layout
            cursor.execute("SELECT Title, URL, Type, MaterialSubtype FROM Dim_Materials WHERE ModuleID = ?", (mod_id,))
            materials_raw = cursor.fetchall()
            documents = [dict(Title=r[0], URL=r[1], Type=r[2]) for r in materials_raw if r[3] != 'Video']
            videos = [dict(Title=r[0], URL=r[1], Type=r[2]) for r in materials_raw if r[3] == 'Video']
            
            cursor.execute("SELECT QuestionID FROM Dim_Questions WHERE ModuleID = ?", (mod_id,))
            questions_count = len(cursor.fetchall())
            
            # Evaluate window scheduling states safely
            start_date = mod[7]
            end_date = mod[8]
            
            is_locked_by_date = False
            lock_reason = ""
            
            if start_date and current_now < start_date:
                is_locked_by_date = True
                lock_reason = f"Opens on {start_date.strftime('%d %b, %H:%M')}"
            elif end_date and current_now > end_date:
                is_locked_by_date = True
                lock_reason = "Expired / Evaluation Window Closed"

            unified_curriculum.append({
                "module": {
                    "ModuleID": mod_id, 
                    "ModuleName": mod[1], 
                    "Category": mod[2], 
                    "TimeLimitMinutes": mod[3], 
                    "DifficultyLevel": mod[4], 
                    "AssessmentType": mod[5],
                    "IsTimed": mod[6],
                    "StartStr": start_date.strftime('%Y-%m-%d %H:%M') if start_date else "Always Open",
                    "EndStr": end_date.strftime('%Y-%m-%d %H:%M') if end_date else "No Deadline"
                },
                "documents": documents,
                "videos": videos,
                "questions_count": questions_count,
                "is_locked_by_date": is_locked_by_date,
                "lock_reason": lock_reason
            })
            
        conn.close()

    employee = {
        "FirstName": session.get("first_name", "User"), 
        "Role": role,
        "Department": emp_dept
    }
    
    # 🌟 CRITICAL FIX: Pass 'unified_curriculum' into the template using the name 'unified_curriculum'
    return render_template(
        "dashboard.html", 
        employee=employee, 
        unified_curriculum=unified_curriculum, 
        all_modules=all_modules, 
        attempts=[], 
        live_classes=[]
    )


@app.route("/module/<int:module_id>")
def view_module_hub(module_id):
    if "role" not in session:
        return redirect(url_for("login"))
        
    role = session["role"]
    emp_id = session.get("employee_id")
    current_now = datetime.now()
    
    conn = get_db_connection()
    if not conn:
        return "Database Connection Failure", 500
        
    cursor = conn.cursor()
    
    # 1. Fetch specific module properties
    cursor.execute("""
        SELECT ModuleID, ModuleName, Category, TimeLimitMinutes, DifficultyLevel, 
               AssessmentType, IsTimed, WindowStartDate, WindowEndDate 
        FROM Dim_Modules WHERE ModuleID = ?
    """, (module_id,))
    mod = cursor.fetchone()
    
    if not mod:
        conn.close()
        return "Module Not Found", 404
        
    # 2. Fetch specific study materials
    cursor.execute("SELECT Title, URL, Type, MaterialSubtype, MaterialID FROM Dim_Materials WHERE ModuleID = ?", (module_id,))
    materials_raw = cursor.fetchall()
    documents = [dict(Title=r[0], URL=r[1], Type=r[2], ID=r[4]) for r in materials_raw if r[3] != 'Video']
    videos = [dict(Title=r[0], URL=r[1], Type=r[2], ID=r[4]) for r in materials_raw if r[3] == 'Video']
    
    # 3. Fetch specific saved historical playbacks
    cursor.execute("SELECT Title, RecordingURL, DateUploaded FROM Dim_MeetingRecordings WHERE ModuleID = ? ORDER BY DateUploaded DESC", (module_id,))
    recordings_raw = cursor.fetchall()
    recordings = [dict(Title=r[0], URL=r[1], Date=r[2].strftime('%d %b %Y') if r[2] else "") for r in recordings_raw]
    
    # 4. Check assessment status
    cursor.execute("SELECT QuestionID FROM Dim_Questions WHERE ModuleID = ?", (module_id,))
    questions_count = len(cursor.fetchall())
    
    # Date evaluations
    start_date, end_date = mod[7], mod[8]
    is_locked_by_date = False
    lock_reason = ""
    if start_date and current_now < start_date:
        is_locked_by_date = True
        lock_reason = f"Opens on {start_date.strftime('%d %b, %H:%M')}"
    elif end_date and current_now > end_date:
        is_locked_by_date = True
        lock_reason = "Expired Window"

    module_data = {
        "ModuleID": mod[0], "ModuleName": mod[1], "Category": mod[2],
        "TimeLimitMinutes": mod[3], "DifficultyLevel": mod[4], "AssessmentType": mod[5],
        "IsTimed": mod[6], "StartStr": start_date.strftime('%Y-%m-%d %H:%M') if start_date else "Always Open",
        "EndStr": end_date.strftime('%Y-%m-%d %H:%M') if end_date else "No Deadline"
    }
    
    conn.close()
    employee = {"FirstName": session.get("first_name", "User"), "Role": role}
    
    return render_template(
        "module_hub.html", 
        employee=employee, module=module_data, documents=documents, 
        videos=videos, recordings=recordings, questions_count=questions_count,
        is_locked_by_date=is_locked_by_date, lock_reason=lock_reason
    )

@app.route("/admin/configure_timing", methods=["POST"])
def configure_timing():
    if "role" not in session or session["role"] not in ["Admin", "Facilitator"]:
        abort(403)
        
    module_id = int(request.form["module_id"])
    is_timed = 1 if request.form.get("is_timed") == "on" else 0
    time_limit = request.form.get("time_limit")
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    
    # Clean blank HTML inputs to None/NULL
    time_limit = int(time_limit) if (is_timed and time_limit) else 0
    start_date = start_date if start_date else None
    end_date = end_date if end_date else None
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Dim_Modules 
            SET IsTimed = ?, TimeLimitMinutes = ?, WindowStartDate = ?, WindowEndDate = ?
            WHERE ModuleID = ?
        """, (is_timed, time_limit, start_date, end_date, module_id))
        conn.commit()
        conn.close()
        flash("⏰ Assessment availability settings updated successfully.")
        
    return redirect(url_for("dashboard"))

@app.route("/admin/generator", methods=["GET", "POST"])
def assessment_generator():
    if "role" not in session or session["role"] not in ["Admin", "Facilitator"]:
        abort(403)
        
    conn = get_db_connection()
    modules = []
    if conn:
        cursor = conn.cursor()
        if session["role"] == "Admin":
            cursor.execute("SELECT ModuleID, ModuleName FROM Dim_Modules")
        else:
            cursor.execute("""
                SELECT M.ModuleID, M.ModuleName FROM Dim_Modules M
                INNER JOIN Bridge_User_Modules B ON M.ModuleID = B.ModuleID
                WHERE B.EmployeeID = ?
            """, (session["employee_id"],))
        modules = [{"ID": r[0], "Name": r[1]} for r in cursor.fetchall()]
        conn.close()

    if request.method == "POST":
        module_id = request.form["module_id"]
        assessment_type = request.form["assessment_type"]
        raw_text = request.form["raw_text"]
        
        prompt = f"""
        You are an expert curriculum assistant. Analyze the following raw text document containing questions and answers.
        Extract them into a strictly structured JSON array format.
        
        Rules:
        1. Identify if a question is Multiple-Choice (MCQ) or Written/Paragraph.
        2. For MCQ questions, populate fields "opt_a", "opt_b", "opt_c", "opt_d", and "correct_option" (must be 'A', 'B', 'C', or 'D').
        3. For Written questions, leave options and correct_option as null, and set type to "Written".
        
        Expected JSON format output:
        [
          {{
            "type": "MCQ",
            "text": "What does SQL stand for?",
            "opt_a": "Structured Question Language",
            "opt_b": "Structured Query Language",
            "opt_c": "Simple Query Log",
            "opt_d": "None of the above",
            "correct_option": "B"
          }},
          {{
            "type": "Written",
            "text": "Explain the concept of database normalization in your own words.",
            "opt_a": null, "opt_b": null, "opt_c": null, "opt_d": null, "correct_option": null
          }}
        ]

        Raw Text Document:
        {raw_text}
        """
        
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            
            # Extract the raw JSON string text out of the response object
            extracted_questions = json.loads(response.text)
            
            return render_template(
                "review_assessment.html", 
                questions=extracted_questions, 
                module_id=module_id, 
                assessment_type=assessment_type
            )
        except Exception as e:
            flash(f"AI Generation Interface Error: {str(e)}")
            return redirect(url_for("assessment_generator"))
            
    return render_template("generator.html", modules=modules)


@app.route("/admin/save_generated_assessment", methods=["POST"])
def save_generated_assessment():
    if "role" not in session or session["role"] not in ["Admin", "Facilitator"]:
        abort(403)
        
    module_id = int(request.form["module_id"])
    assessment_type = request.form["assessment_type"]
    
    q_types = request.form.getlist("type")
    q_texts = request.form.getlist("text")
    opts_a = request.form.getlist("opt_a")
    opts_b = request.form.getlist("opt_b")
    opts_c = request.form.getlist("opt_c")
    opts_d = request.form.getlist("opt_d")
    correct_opts = request.form.getlist("correct_option")
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        
        # Normalize the structural target type footprint inside the module matrix
        cursor.execute("UPDATE Dim_Modules SET AssessmentType = ? WHERE ModuleID = ?", (assessment_type, module_id))
        
        for i in range(len(q_texts)):
            if q_types[i] == "MCQ":
                cursor.execute("""
                    INSERT INTO Dim_Questions (ModuleID, QuestionText, OptionA, OptionB, OptionC, OptionD, CorrectOption, QuestionType)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'MCQ')""",
                    (module_id, q_texts[i], opts_a[i], opts_b[i], opts_c[i], opts_d[i], correct_opts[i]))
            else:
                # FIX: Explicitly supply all 8 columns with standard NULL values to preserve parameter index alignment
                cursor.execute("""
                    INSERT INTO Dim_Questions (ModuleID, QuestionText, OptionA, OptionB, OptionC, OptionD, CorrectOption, QuestionType)
                    VALUES (?, ?, NULL, NULL, NULL, NULL, NULL, 'Written')""",
                    (module_id, q_texts[i]))
                    
        conn.commit()
        conn.close()
        flash(f"🎉 Success! Finalized {assessment_type} questions safely saved to the database.")
        
    return redirect(url_for("dashboard"))

# ========================================================
# 🤖 ADVANCED CONTROL CENTER FOR MANAGEMENT PROFILES
# ========================================================

@app.route("/admin/add_class_meeting", methods=["POST"])
def add_class_meeting():
    if "role" not in session or session["role"] not in ["Admin", "Facilitator"]:
        abort(403)
    
    module_id = int(request.form["module_id"])
    topic = request.form["topic"]
    meeting_url = request.form["meeting_url"]
    scheduled_time = request.form["scheduled_time"]
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Dim_Classes (ModuleID, Topic, MeetingURL, ScheduledDateTime, CreatedBy)
            VALUES (?, ?, ?, ?, ?)""", (module_id, topic, meeting_url, scheduled_time, session.get("employee_id", 0)))
        conn.commit()
        conn.close()
        flash("📅 New virtual room link deployed successfully to the Student workspace.")
    return redirect(url_for("dashboard"))

@app.route("/admin/add_segmented_material", methods=["POST"])
def add_segmented_material():
    if "role" not in session or session["role"] not in ["Admin", "Facilitator"]:
        abort(403)
        
    module_id = request.form["module_id"]
    title = request.form["title"].strip()
    subtype = request.form["subtype"] # 'Document' or 'Video'
    
    resource_url = ""
    
    # 📥 Check if a file stream attachment payload exists in the request pipeline
    if 'file_upload' in request.files and request.files['file_upload'].filename != '':
        file = request.files['file_upload']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Prepend timestamp to prevent file collision overwriting
            unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Map structural routing path back to application client assets engine
            resource_url = f"/static/uploads/{unique_filename}"
        else:
            flash("❌ Rejected: Invalid file extension format.")
            return redirect(url_for("dashboard"))
    else:
        # Fallback to standard external raw URL input field if no file stream was uploaded
        resource_url = request.form.get("url", "").strip()

    if not resource_url:
        flash("❌ Error: You must supply either an active Stream Link URL or upload a file.")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        material_type = 'External Stream Link' if subtype == 'Video' else 'Core Documentation'
        cursor.execute("""
            INSERT INTO Dim_Materials (ModuleID, Title, URL, Type, MaterialSubtype)
            VALUES (?, ?, ?, ?, ?)""", (module_id, title, resource_url, material_type, subtype))
        conn.commit()
        conn.close()
        flash(f"🎉 Asset attached directly into the targeted Study Folder profiles.")
        
    return redirect(url_for("dashboard"))

# Sandbox Test Suite Engine to preview questions safely
@app.route("/admin/sandbox/test/<int:module_id>")
def sandbox_test(module_id):
    if "role" not in session or session["role"] not in ["Admin", "Facilitator"]:
        abort(403)
        
    conn = get_db_connection()
    questions = []
    module_name = "Sandbox Pool"
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ModuleName FROM Dim_Modules WHERE ModuleID = ?", (module_id,))
        res = cursor.fetchone()
        if res: module_name = res[0]
        
        cursor.execute("SELECT QuestionText, OptionA, OptionB, OptionC, OptionD, CorrectOption, QuestionType FROM Dim_Questions WHERE ModuleID = ?", (module_id,))
        questions = [{"Text": r[0], "A": r[1], "B": r[2], "C": r[3], "D": r[4], "Key": r[5], "Type": r[6]} for r in cursor.fetchall()]
        conn.close()
        
    return render_template("sandbox_preview.html", questions=questions, name=module_name)

# ========================================================
# 🔒 CONTENT INJECTION GATEKEEPERS (ADMIN & FACILITATOR)
# ========================================================

@app.route("/admin/add_material", methods=["POST"])
def add_material():
    # Only Admin and Facilitator roles can append custom materials to the track views
    if "role" not in session or session["role"] not in ["Admin", "Facilitator"]:
        abort(403)
        
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Dim_StudyMaterials (ModuleID, MaterialTitle, MaterialType, ResourceURL) VALUES (?, ?, ?, ?)",
                       (int(request.form["module_id"]), request.form["title"], request.form["type"], request.form["url"]))
        conn.commit()
        conn.close()
        flash("🚀 Learning content resource successfully synchronized!")
    return redirect(url_for("dashboard"))


@app.route("/admin/add_question", methods=["POST"])
def admin_add_question():
    if "role" not in session or session["role"] not in ["Admin", "Facilitator"]:
        abort(403)
        
    q_type = request.form.get("question_type", "MCQ")
    m_id = int(request.form["module_id"])
    q_text = request.form["question_text"]
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        if q_type == "MCQ":
            cursor.execute("""
                INSERT INTO Dim_Questions (ModuleID, QuestionText, OptionA, OptionB, OptionC, OptionD, CorrectOption, QuestionType) 
                VALUES (?, ?, ?, ?, ?, ?, ?, 'MCQ')""",
                (m_id, q_text, request.form["opt_a"], request.form["opt_b"], request.form["opt_c"], request.form["opt_d"], request.form["correct_option"]))
        else:
            # Written questions do not parse selection items or correct answers to the database row
            cursor.execute("""
                INSERT INTO Dim_Questions (ModuleID, QuestionText, OptionA, OptionB, OptionC, OptionD, CorrectOption, QuestionType) 
                VALUES (?, ?, NULL, NULL, NULL, NULL, NULL, 'Written')""",
                (m_id, q_text))
        conn.commit()
        conn.close()
        flash("✅ Section block successfully updated into the curriculum track matrix!")
    return redirect(url_for("dashboard"))




# ========================================================
# 📝 ASSESSMENT REPO & METADATA CONTROLLERS
# ========================================================

@app.route("/admin/update_assessment_settings", methods=["POST"])
def update_assessment_settings():
    if "role" not in session or session["role"] not in ["Admin", "Facilitator"]:
        abort(403)
        
    module_id = request.form["module_id"]
    assessment_type = request.form["assessment_type"]  # Quiz, Test, Exam
    time_limit = request.form["time_limit"]            # In minutes
    start_date = request.form["start_date"]            # YYYY-MM-DD
    end_date = request.form["end_date"]                # YYYY-MM-DD
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        # Update metadata constraints on the primary dimension model
        cursor.execute("""
            UPDATE Dim_Modules 
            SET AssessmentType = ?, TimeLimit = ?, StartStr = ?, EndStr = ?
            WHERE ModuleID = ?
        """, (assessment_type, time_limit, start_date, end_date, module_id))
        conn.commit()
        conn.close()
        flash("⚙️ Assessment window and configurations updated successfully.")
    return redirect(url_for("dashboard"))


@app.route("/admin/edit_questions_workspace/<int:module_id>")
def edit_questions_workspace(module_id):
    if "role" not in session or session["role"] not in ["Admin", "Facilitator"]:
        abort(403)
        
    conn = get_db_connection()
    questions = []
    module_info = None
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ModuleID, ModuleName, AssessmentType FROM Dim_Modules WHERE ModuleID = ?", (module_id,))
        module_info = cursor.fetchone()
        
        cursor.execute("""
            SELECT QuestionID, QuestionType, QuestionText, OptionA, OptionB, OptionC, OptionD, CorrectOption 
            FROM Dim_Questions WHERE ModuleID = ?
        """, (module_id,))
        rows = cursor.fetchall()
        conn.close()
        
        # Format map objects to feed clean structures straight to your verified review view block
        for row in rows:
            questions.append({
                'id': row[0], 'type': row[1], 'text': row[2],
                'opt_a': row[3], 'opt_b': row[4], 'opt_c': row[5], 'opt_d': row[6],
                'correct_option': row[7]
            })
            
    return render_template("review_assessment.html", module_id=module_id, assessment_type=module_info[2], questions=questions)

# ========================================================
# SECURITY-MAPPED EVALUATION ENGINE CALLS (LEARNER ONLY)
# ========================================================

@app.route("/quiz/<int:module_id>")
def quiz(module_id):
    if "employee_id" not in session: 
        return redirect(url_for("login"))
    
    # Block Facilitators and Admins from writing student tests
    if session["role"] != "Learner":
        flash("Administrative accounts are restricted from launching active execution assessments.")
        return redirect(url_for("dashboard"))
    
    conn = get_db_connection()
    module_data, questions_list = None, []
    
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ModuleID, ModuleName, TimeLimitMinutes FROM Dim_Modules WHERE ModuleID = ?", (module_id,))
        m = cursor.fetchone()
        if m: module_data = {"ModuleID": m[0], "ModuleName": m[1], "TimeLimitMinutes": m[2]}
        
        cursor.execute("SELECT QuestionID, QuestionText, OptionA, OptionB, OptionC, OptionD FROM Dim_Questions WHERE ModuleID = ?", (module_id,))
        questions_list = [{"QuestionID": r[0], "QuestionText": r[1], "OptionA": r[2], "OptionB": r[3], "OptionC": r[4], "OptionD": r[5]} for r in cursor.fetchall()]
        conn.close()
        
    return render_template("quiz_form.html", module=module_data, questions=questions_list)

@app.route("/submit_quiz", methods=["POST"])
def submit_quiz():
    if "employee_id" not in session or session["role"] != "Learner": 
        abort(403)
    
    module_id = int(request.form["module_id"])
    conn = get_db_connection()
    
    if conn:
        cursor = conn.cursor()
        
        # Pull only MCQ question keys from the database to compute the grade safely
        cursor.execute("SELECT QuestionID, CorrectOption FROM Dim_Questions WHERE ModuleID = ? AND QuestionType = 'MCQ'", (module_id,))
        mcq_keys = {r[0]: r[1] for r in cursor.fetchall()}
        
        # Calculate scores strictly for the MCQ items (Written answers are recorded successfully via request payload keys)
        correct = sum(1 for q_id, opt in mcq_keys.items() if request.form.get(f"question_{q_id}") == opt)
        score = (correct / len(mcq_keys)) * 100 if mcq_keys else 100.0 # Default full completion pass mark if written only
        
        # Log the attempt outcome row cleanly
        cursor.execute("""
            INSERT INTO Fact_Quiz_Attempts (EmployeeID, ModuleID, Score, DurationSeconds, AssessmentTypeRecorded) 
            VALUES (?, ?, ?, ?, (SELECT TOP 1 AssessmentType FROM Dim_Modules WHERE ModuleID = ?))
        """, (session["employee_id"], module_id, score, 180, module_id))
        
        conn.commit()
        conn.close()
        flash(f"🎉 Paper compilation finalized! Automatically processed section elements score marked: {score:.1f}%")
    return redirect(url_for("dashboard"))

@app.route("/admin/add_learner", methods=["POST"])
def add_learner():
    # 1. Security Check: Only let Admins or Facilitators execute this block
    if "role" not in session or session["role"] not in ["Admin", "Facilitator"]:
        abort(403)
        
    full_name = request.form.get("first_name", "").strip()
    email = request.form.get("email", "").strip()
    department = request.form.get("department") # This matches the module 'Category'
    
    # 2. Prevent empty submissions
    if not full_name or not email:
        flash("❌ Error: Full Name and Email are required fields.")
        return redirect(url_for("dashboard"))
        
    # 3. Handle the Split for FirstName and LastName safely to satisfy database NOT NULL rules
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else "." # Fallback if no last name was entered
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # 4. Added 'PasswordHash' column and passed 'mockhash' to satisfy the constraint
            cursor.execute("""
                INSERT INTO Dim_Employees (FirstName, LastName, Email, Department, UserRole, RoleLevel, PasswordHash)
                VALUES (?, ?, ?, ?, 'Learner', 'Learner', 'mockhash')
            """, (first_name, last_name, email, department))
            conn.commit()
            
            flash(f"🎉 Learner '{full_name}' successfully enrolled into the '{department}' track!")
        except Exception as e:
            flash(f"❌ Database Rejection: {str(e)}")
        finally:
            conn.close()
            
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ========================================================
# 🛠️ CONTENT MATERIAL (CRUD UTILITIES)
# ========================================================

@app.route("/admin/delete_curriculum_material/<int:material_id>", methods=["POST"])
def delete_curriculum_material(material_id):
    if "role" not in session or session["role"] not in ["Admin", "Facilitator"]:
        abort(403)
        
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Dim_Materials WHERE MaterialID = ?", (material_id,))
        conn.commit()
        conn.close()
        flash("🗑️ Study resource record deleted successfully from the curriculum matrix.")
    return redirect(url_for("dashboard"))

@app.route("/admin/reset_assessment/<int:module_id>", methods=["POST"])
def reset_assessment(module_id):
    if "role" not in session or session["role"] not in ["Admin", "Facilitator"]:
        abort(403)
        
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        # Wipes out existing questions linked to this module to clear space for updates
        cursor.execute("DELETE FROM Dim_Questions WHERE ModuleID = ?", (module_id,))
        cursor.execute("UPDATE Dim_Modules SET AssessmentType = 'Quiz' WHERE ModuleID = ?", (module_id,))
        conn.commit()
        conn.close()
        flash("🧹 Evaluation repository wiped clean. You can now rebuild or update questions safely.")
    return redirect(url_for("dashboard"))


# ========================================================
# 📼 CLOUD MEETING RECORDINGS VAULT ROUTING
# ========================================================

@app.route("/admin/add_recording", methods=["POST"])
def add_recording():
    if "role" not in session or session["role"] not in ["Admin", "Facilitator"]:
        abort(403)
        
    module_id = int(request.form["module_id"])
    title = request.form["title"]
    recording_url = request.form["recording_url"]
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Dim_MeetingRecordings (ModuleID, Title, RecordingURL)
            VALUES (?, ?, ?)
        """, (module_id, title, recording_url))
        conn.commit()
        conn.close()
        flash("📼 Class recording link cataloged and deployed to the archive registry vault.")
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)