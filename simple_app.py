"""
Al-Quds University - Course Evaluation Web App (Single File)
Simple, easy to use - everything in one file!
"""

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import requests
import re
import time
from functools import wraps
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# ==================== CONFIGURATION ====================
BASE = "https://student.alquds.edu"
LOGIN_URL = f"{BASE}/en/login"
EVAL_PAGE_URL = f"{BASE}/en/acadaffair/survey_eval/evaluation/"
LOAD_COURSES_URL = f"{BASE}/en/acadaffair/survey_eval/evaluation/__LOADCOURSES/"
SAVE_EVALUATION_URL = f"{BASE}/en/acadaffair/survey_eval/evaluation/__SAVEEVALUATION"

# ==================== HTML TEMPLATES ====================
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Al-Quds Course Evaluation</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .navbar { background: #2c3e50 !important; }
        .card { border: none; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); border-radius: 12px; }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; }
        .btn-primary:hover { background: linear-gradient(135deg, #5568d3 0%, #653a91 100%); }
        .login-container { display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .login-card { width: 100%; max-width: 400px; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2); }
        .login-card h1 { text-align: center; margin-bottom: 30px; color: #333; font-weight: bold; }
        .form-control { border-radius: 8px; border: 1px solid #ddd; padding: 12px 15px; margin-bottom: 15px; }
        .form-control:focus { border-color: #667eea; box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25); }
        .stats-box { background: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
        .stats-number { font-size: 2.5rem; font-weight: bold; color: #667eea; }
        .badge-evaluated { background-color: #28a745; }
        .badge-pending { background-color: #ffc107; color: #333; }
        .spinner { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 9999; background: rgba(255, 255, 255, 0.9); padding: 30px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3); }
        .spinner.show { display: block; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark">
        <div class="container-fluid">
            <span class="navbar-brand">🎓 Al-Quds Course Evaluation</span>
            {% if session.get('logged_in') %}
            <div>
                <span class="navbar-text text-light me-3">{{ session.get('username') }}</span>
                <a href="{{ url_for('logout') }}" class="btn btn-outline-light btn-sm">Logout</a>
            </div>
            {% endif %}
        </div>
    </nav>

    <div class="container mt-5">
        {% block content %}{% endblock %}
    </div>

    <div class="spinner" id="spinner">
        <div class="text-center">
            <div class="spinner-border text-primary mb-3" role="status"></div>
            <p class="text-dark">Processing evaluations...</p>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Al-Quds Course Evaluation</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .navbar { background: #2c3e50 !important; }
        .login-container { display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .login-card { width: 100%; max-width: 400px; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2); }
        .login-card h1 { text-align: center; margin-bottom: 30px; color: #333; font-weight: bold; }
        .form-control { border-radius: 8px; border: 1px solid #ddd; padding: 12px 15px; margin-bottom: 15px; }
        .form-control:focus { border-color: #667eea; box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25); }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; }
        .btn-primary:hover { background: linear-gradient(135deg, #5568d3 0%, #653a91 100%); }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark">
        <div class="container-fluid">
            <span class="navbar-brand">🎓 Al-Quds Course Evaluation</span>
        </div>
    </nav>

    <div class="login-container">
        <div class="login-card">
            <h1>🎓 Login</h1>
            {% if error %}
            <div class="alert alert-danger">⚠️ {{ error }}</div>
            {% endif %}
            <form method="POST">
                <input type="text" name="username" class="form-control" placeholder="Student ID" required autofocus>
                <input type="password" name="password" class="form-control" placeholder="Password" required>
                <button type="submit" class="btn btn-primary w-100 py-2">Login</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Al-Quds Course Evaluation - Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .navbar { background: #2c3e50 !important; }
        .card { border: none; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); border-radius: 12px; }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; }
        .btn-primary:hover { background: linear-gradient(135deg, #5568d3 0%, #653a91 100%); }
        .stats-box { background: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
        .stats-number { font-size: 2.5rem; font-weight: bold; color: #667eea; }
        .badge-evaluated { background-color: #28a745; }
        .badge-pending { background-color: #ffc107; color: #333; }
        .spinner { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 9999; background: rgba(255, 255, 255, 0.9); padding: 30px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3); }
        .spinner.show { display: block; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark">
        <div class="container-fluid">
            <span class="navbar-brand">🎓 Al-Quds Course Evaluation</span>
            <div>
                <span class="navbar-text text-light me-3">{{ session.get('username') }}</span>
                <a href="{{ url_for('logout') }}" class="btn btn-outline-light btn-sm">Logout</a>
            </div>
        </div>
    </nav>

    <div class="container mt-5">
        <h2 class="text-white mb-4">📚 Your Courses</h2>

        {% if error %}
        <div class="alert alert-danger">⚠️ {{ error }}</div>
        {% endif %}

        <!-- Statistics -->
        <div class="row mb-4">
            <div class="col-md-4">
                <div class="stats-box">
                    <div class="stats-number">{{ stats.total }}</div>
                    <div>Total Courses</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="stats-box">
                    <div class="stats-number" style="color: #28a745;">{{ stats.evaluated }}</div>
                    <div>Evaluated ✓</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="stats-box">
                    <div class="stats-number" style="color: #ffc107;">{{ stats.pending }}</div>
                    <div>Pending</div>
                </div>
            </div>
        </div>

        <!-- Courses Table -->
        <div class="card mb-4">
            <div class="card-body">
                {% if courses %}
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead class="table-light">
                                <tr>
                                    <th style="width: 50px;"><input type="checkbox" id="select-all" class="form-check-input"></th>
                                    <th>Course Code</th>
                                    <th>Course Name</th>
                                    <th>Instructor</th>
                                    <th>Class</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for course in courses %}
                                <tr>
                                    <td>
                                        {% if course.status == 'not evaluated' and course.eval_code %}
                                        <input type="checkbox" class="form-check-input course-checkbox" value="{{ course.course_code }}">
                                        {% else %}
                                        <input type="checkbox" disabled>
                                        {% endif %}
                                    </td>
                                    <td><code>{{ course.course_code }}</code></td>
                                    <td><strong>{{ course.course_name }}</strong></td>
                                    <td>{{ course.instructor }}</td>
                                    <td>{{ course.units }}</td>
                                    <td>
                                        {% if course.status == 'evaluated' %}
                                        <span class="badge badge-evaluated">✓ Evaluated</span>
                                        {% else %}
                                        <span class="badge badge-pending">⊙ Pending</span>
                                        {% endif %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                {% else %}
                <div class="alert alert-info">No courses found. Please try again later.</div>
                {% endif %}
            </div>
        </div>

        <!-- Action Buttons -->
        <div class="card">
            <div class="card-body d-flex gap-2">
                <button class="btn btn-primary" id="evaluate-btn">🚀 Evaluate Selected</button>
                <button class="btn btn-secondary" id="select-all-btn">☑️ Select All</button>
                <button class="btn btn-outline-secondary" id="clear-selection-btn">Clear</button>
                <span class="ms-auto text-muted pt-2"><span id="selected-count">0</span> selected</span>
            </div>
        </div>
    </div>

    <div class="spinner" id="spinner">
        <div class="text-center">
            <div class="spinner-border text-primary mb-3" role="status"></div>
            <p class="text-dark">Processing evaluations...</p>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
    const selectAllCheckbox = document.getElementById('select-all');
    const courseCheckboxes = document.querySelectorAll('.course-checkbox');
    const evaluateBtn = document.getElementById('evaluate-btn');
    const selectAllBtn = document.getElementById('select-all-btn');
    const clearSelectionBtn = document.getElementById('clear-selection-btn');
    const selectedCountSpan = document.getElementById('selected-count');
    const spinner = document.getElementById('spinner');

    function updateSelectedCount() {
        const selected = document.querySelectorAll('.course-checkbox:checked').length;
        selectedCountSpan.textContent = selected;
    }

    selectAllCheckbox.addEventListener('change', function() {
        courseCheckboxes.forEach(cb => cb.checked = this.checked);
        updateSelectedCount();
    });

    courseCheckboxes.forEach(cb => cb.addEventListener('change', updateSelectedCount));

    selectAllBtn.addEventListener('click', function() {
        courseCheckboxes.forEach(cb => cb.checked = true);
        selectAllCheckbox.checked = true;
        updateSelectedCount();
    });

    clearSelectionBtn.addEventListener('click', function() {
        courseCheckboxes.forEach(cb => cb.checked = false);
        selectAllCheckbox.checked = false;
        updateSelectedCount();
    });

    evaluateBtn.addEventListener('click', async function() {
        const selected = Array.from(document.querySelectorAll('.course-checkbox:checked')).map(cb => cb.value);
        
        if (selected.length === 0) {
            alert('Please select at least one course');
            return;
        }
        
        if (!confirm(`Evaluate ${selected.length} course(s)?`)) return;
        
        spinner.classList.add('show');
        
        try {
            const response = await fetch('{{ url_for("api_evaluate") }}', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ courses: selected })
            });
            
            const result = await response.json();
            spinner.classList.remove('show');
            
            if (result.success) {
                alert(`Success! ${result.total_success} evaluated, ${result.total_failed} failed.\\nPage will refresh...`);
                location.reload();
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            spinner.classList.remove('show');
            alert('Error: ' + error.message);
        }
    });

    updateSelectedCount();
    </script>
</body>
</html>
"""

# ==================== HELPER FUNCTIONS ====================
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def login_to_portal(username, password):
    http_session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": BASE,
        "Referer": LOGIN_URL,
    }
    data = {"username": username, "password": password, "login": "Login"}
    
    try:
        r = http_session.post(LOGIN_URL, headers=headers, data=data, timeout=10)
        success = r.status_code == 200 and "logout" in r.text.lower()
        return (http_session, None) if success else (None, "Invalid credentials")
    except Exception as e:
        return (None, str(e))

def access_evaluation_page(http_session):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = http_session.get(EVAL_PAGE_URL, headers=headers, timeout=10)
        return r.status_code == 200
    except:
        return False

def parse_courses_from_xml(xml_text):
    courses = []
    row_pattern = r'<row[^>]*>(.*?)</row>'
    cell_pattern = r'<cell[^>]*><!\[CDATA\[(.*?)\]\]></cell>'
    
    rows = re.findall(row_pattern, xml_text, re.DOTALL)
    
    for row_content in rows:
        cells = re.findall(cell_pattern, row_content)
        
        if len(cells) >= 9:
            status_cell = cells[7]
            status = "evaluated"
            eval_code = None
            
            if "not evaluated" in status_cell:
                status = "not evaluated"
                eval_match = re.search(r'load_eval_form\("([^"]+)"', status_cell)
                if eval_match:
                    eval_code = eval_match.group(1)
            
            course = {
                'semester': cells[0],
                'course_code': cells[1],
                'section': cells[2],
                'course_name': cells[3],
                'instructor': cells[4],
                'units': cells[5],
                'type': cells[6],
                'status': status,
                'eval_code': eval_code
            }
            courses.append(course)
    
    return courses

def load_courses_from_portal(http_session, semester_code="2252-1-0"):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": EVAL_PAGE_URL,
    }
    
    data = {"param": semester_code}
    
    try:
        r = http_session.post(LOAD_COURSES_URL, headers=headers, data=data, timeout=10)
        if r.status_code == 200 and (r.text.startswith("<?xml") or r.text.startswith("<rows")):
            return parse_courses_from_xml(r.text)
    except:
        pass
    
    return []

def build_payload(eval_code, course_units=None):
    payload = {}
    
    if "::" in eval_code:
        parts = eval_code.split("::")
        units = course_units if course_units else 3
        eval_course_formatted = f"{parts[0]}-1-{parts[1]}-{parts[2]}-{units}-0"
    else:
        eval_course_formatted = eval_code
    
    payload['eval_course'] = eval_course_formatted
    
    for q in range(1, 6):
        payload[f"1-{q}-2"] = "5-'1"
    
    payload["2-1-4"] = "5-6"
    for q in range(2, 20):
        payload[f"2-{q}-2"] = "5-'1"
    
    payload["3-1-3-8"] = ""
    
    return payload

def submit_evaluation(http_session, eval_code, course_units=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": EVAL_PAGE_URL,
    }
    
    payload = build_payload(eval_code, course_units)
    
    try:
        from urllib.parse import urlencode
        r = http_session.post(SAVE_EVALUATION_URL, headers=headers, data=urlencode(payload), timeout=30)
        return r.status_code == 200
    except:
        return False

# ==================== ROUTES ====================
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            return render_template_string(LOGIN_TEMPLATE, error='Please enter credentials')
        
        http_session, error = login_to_portal(username, password)
        
        if error:
            return render_template_string(LOGIN_TEMPLATE, error=error)
        
        if not access_evaluation_page(http_session):
            return render_template_string(LOGIN_TEMPLATE, error='Could not access evaluation page')
        
        session['logged_in'] = True
        session['username'] = username
        session['http_session'] = requests.utils.dict_from_cookiejar(http_session.cookies)
        session.permanent = True
        
        return redirect(url_for('dashboard'))
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/dashboard')
@login_required
def dashboard():
    http_session = requests.Session()
    for key, val in session.get('http_session', {}).items():
        http_session.cookies.set(key, val)
    
    courses = load_courses_from_portal(http_session)
    
    if not courses:
        return render_template_string(DASHBOARD_TEMPLATE, error='Could not load courses', courses=[], stats={})
    
    pending = [c for c in courses if c['status'] == 'not evaluated' and c['eval_code']]
    evaluated = [c for c in courses if c['status'] == 'evaluated']
    
    stats = {'total': len(courses), 'evaluated': len(evaluated), 'pending': len(pending)}
    
    return render_template_string(DASHBOARD_TEMPLATE, courses=courses, stats=stats)

@app.route('/api/evaluate', methods=['POST'])
@login_required
def api_evaluate():
    data = request.get_json()
    selected_courses = data.get('courses', [])
    
    if not selected_courses:
        return jsonify({'success': False, 'error': 'No courses selected'})
    
    http_session = requests.Session()
    for key, val in session.get('http_session', {}).items():
        http_session.cookies.set(key, val)
    
    results = {'success': [], 'failed': []}
    all_courses = load_courses_from_portal(http_session)
    course_map = {c['course_code']: c for c in all_courses}
    
    for course_code in selected_courses:
        if course_code in course_map:
            course = course_map[course_code]
            
            if course['eval_code']:
                units = int(course['units']) if course['units'] else 3
                
                if submit_evaluation(http_session, course['eval_code'], units):
                    results['success'].append(course['course_name'])
                else:
                    results['failed'].append(course['course_name'])
                
                time.sleep(1.5)
    
    return jsonify({
        'success': True,
        'results': results,
        'total_success': len(results['success']),
        'total_failed': len(results['failed'])
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "="*50)
    print("Al-Quds Course Evaluation - Web App")
    print("="*50)
    print(f"\nStarting server on port {port}...")
    print(f"Open your browser: http://localhost:{port}\n")
    app.run(debug=False, host='0.0.0.0', port=port)
