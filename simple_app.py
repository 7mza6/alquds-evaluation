"""
Al-Quds University - Course Evaluation Web App (Single File)
Updated version:
- Good / Neutral / Bad rating per course
- Optional comment per course
- Review/preview confirmation before submitting
- Per-course success/failure details
- Retry attempts for temporary portal failures
- Semester selector instead of one hard-coded semester only
- Safer SECRET_KEY handling through environment variable
- Server-side portal session storage instead of putting portal cookies in Flask's client session

Run:
    pip install flask requests
    export FLASK_SECRET_KEY="change-this-to-a-long-random-secret"
    python alquds_course_evaluation_updated.py
"""

from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import os
import re
import time
import uuid
from datetime import timedelta
from functools import wraps
from urllib.parse import urlencode

import requests

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-this-secret-key")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)

# In-memory server-side store for portal sessions.
# This is safer than storing portal cookies inside Flask's browser session cookie.
# Note: for production, replace this with Redis or another shared server-side session store.
PORTAL_SESSIONS = {}

# ==================== CONFIGURATION ====================
BASE = "https://student.alquds.edu"
LOGIN_URL = f"{BASE}/en/login"
EVAL_PAGE_URL = f"{BASE}/en/acadaffair/survey_eval/evaluation/"
LOAD_COURSES_URL = f"{BASE}/en/acadaffair/survey_eval/evaluation/__LOADCOURSES/"
SAVE_EVALUATION_URL = f"{BASE}/en/acadaffair/survey_eval/evaluation/__SAVEEVALUATION"

DEFAULT_SEMESTER_CODE = "2252-1-0"
REQUEST_TIMEOUT = 15
SUBMIT_TIMEOUT = 30
MAX_SUBMIT_RETRIES = 2
DELAY_BETWEEN_EVALUATIONS_SECONDS = 1.5

SEMESTER_OPTIONS = [
    ("2252-1-0", "Current / Default"),
    ("2251-1-0", "Previous semester"),
    ("2242-1-0", "Older semester"),
]
VALID_SEMESTER_CODES = {code for code, _label in SEMESTER_OPTIONS}

# ==================== HTML TEMPLATES ====================
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
        .login-card { width: 100%; max-width: 430px; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2); }
        .login-card h1 { text-align: center; margin-bottom: 30px; color: #333; font-weight: bold; }
        .form-control { border-radius: 8px; border: 1px solid #ddd; padding: 12px 15px; margin-bottom: 15px; }
        .form-control:focus { border-color: #667eea; box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25); }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; }
        .btn-primary:hover { background: linear-gradient(135deg, #5568d3 0%, #653a91 100%); }
        .small-note { color: #666; font-size: 0.9rem; }
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
            <p class="small-note mt-3 mb-0">
                Tip: set <code>FLASK_SECRET_KEY</code> before running this app for better session security.
            </p>
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
        .spinner { display: none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 9999; background: rgba(255, 255, 255, 0.95); padding: 30px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3); }
        .spinner.show { display: block; }
        .comment-input { min-width: 240px; }
        .rating-select { min-width: 115px; }
        .result-list { max-height: 300px; overflow-y: auto; }
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
        <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
            <h2 class="text-white mb-0">📚 Your Courses</h2>
            <form method="GET" action="{{ url_for('dashboard') }}" class="d-flex gap-2">
                <select name="semester" class="form-select">
                    {% for code, label in semester_options %}
                    <option value="{{ code }}" {% if code == semester_code %}selected{% endif %}>{{ label }} - {{ code }}</option>
                    {% endfor %}
                </select>
                <button class="btn btn-light" type="submit">Load</button>
            </form>
        </div>

        {% if error %}
        <div class="alert alert-danger">⚠️ {{ error }}</div>
        {% endif %}

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

        <div class="card mb-4">
            <div class="card-body">
                {% if courses %}
                    <div class="table-responsive">
                        <table class="table table-hover align-middle">
                            <thead class="table-light">
                                <tr>
                                    <th style="width: 50px;"><input type="checkbox" id="select-all" class="form-check-input"></th>
                                    <th>Course Code</th>
                                    <th>Course Name</th>
                                    <th>Instructor</th>
                                    <th>Class</th>
                                    <th>Status</th>
                                    <th>Rating</th>
                                    <th>Optional Comment</th>
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
                                    <td>
                                        {% if course.status == 'not evaluated' and course.eval_code %}
                                        <select class="form-select form-select-sm rating-select" data-course="{{ course.course_code }}">
                                            <option value="good">Good</option>
                                            <option value="neutral">Neutral</option>
                                            <option value="bad">Bad</option>
                                        </select>
                                        {% else %}
                                        <span class="text-muted">—</span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        {% if course.status == 'not evaluated' and course.eval_code %}
                                        <input type="text" class="form-control form-control-sm comment-input" data-course="{{ course.course_code }}" maxlength="500" placeholder="Optional comment">
                                        {% else %}
                                        <span class="text-muted">—</span>
                                        {% endif %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                {% else %}
                <div class="alert alert-info">No courses found. Please try a different semester or try again later.</div>
                {% endif %}
            </div>
        </div>

        <div class="card mb-5">
            <div class="card-body d-flex gap-2 flex-wrap align-items-center">
                <button class="btn btn-primary" id="evaluate-btn">🚀 Review & Evaluate Selected</button>
                <button class="btn btn-secondary" id="select-all-btn">☑️ Select All Pending</button>
                <button class="btn btn-outline-secondary" id="clear-selection-btn">Clear</button>
                <span class="ms-auto text-muted"><span id="selected-count">0</span> selected</span>
            </div>
        </div>
    </div>

    <div class="spinner" id="spinner">
        <div class="text-center">
            <div class="spinner-border text-primary mb-3" role="status"></div>
            <p class="text-dark mb-0">Processing evaluations...</p>
        </div>
    </div>

    <div class="modal fade" id="reviewModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Review Before Submitting</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p class="mb-2">Please review your selected courses, ratings, and comments.</p>
                    <div id="review-content" class="result-list"></div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="confirm-submit-btn">Submit Evaluations</button>
                </div>
            </div>
        </div>
    </div>

    <div class="modal fade" id="resultsModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Evaluation Results</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div id="results-content" class="result-list"></div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-primary" onclick="location.reload()">Refresh Courses</button>
                </div>
            </div>
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
    const reviewContent = document.getElementById('review-content');
    const resultsContent = document.getElementById('results-content');
    const confirmSubmitBtn = document.getElementById('confirm-submit-btn');
    const reviewModal = new bootstrap.Modal(document.getElementById('reviewModal'));
    const resultsModal = new bootstrap.Modal(document.getElementById('resultsModal'));
    let pendingSubmission = [];

    function updateSelectedCount() {
        const selected = document.querySelectorAll('.course-checkbox:checked').length;
        selectedCountSpan.textContent = selected;
    }

    function getCourseNameFromRow(checkbox) {
        const row = checkbox.closest('tr');
        return row ? row.children[2].innerText.trim() : checkbox.value;
    }

    function getSelectedCourses() {
        return Array.from(document.querySelectorAll('.course-checkbox:checked')).map(cb => {
            const ratingSelect = document.querySelector(`.rating-select[data-course="${cb.value}"]`);
            const commentInput = document.querySelector(`.comment-input[data-course="${cb.value}"]`);
            return {
                course_code: cb.value,
                course_name: getCourseNameFromRow(cb),
                rating: ratingSelect ? ratingSelect.value : 'neutral',
                comment: commentInput ? commentInput.value.trim() : ''
            };
        });
    }

    function renderReview(items) {
        const rows = items.map(item => `
            <tr>
                <td><code>${escapeHtml(item.course_code)}</code></td>
                <td>${escapeHtml(item.course_name)}</td>
                <td><strong>${escapeHtml(item.rating)}</strong></td>
                <td>${escapeHtml(item.comment || '—')}</td>
            </tr>
        `).join('');

        reviewContent.innerHTML = `
            <table class="table table-sm table-bordered">
                <thead class="table-light">
                    <tr><th>Code</th><th>Course</th><th>Rating</th><th>Comment</th></tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }

    function renderResults(result) {
        const successRows = (result.results?.success || []).map(item => `
            <li class="list-group-item list-group-item-success">✓ ${escapeHtml(item.course_name)} — ${escapeHtml(item.rating)}</li>
        `).join('');
        const failedRows = (result.results?.failed || []).map(item => `
            <li class="list-group-item list-group-item-danger">✗ ${escapeHtml(item.course_name)} — ${escapeHtml(item.error || 'Failed')}</li>
        `).join('');

        resultsContent.innerHTML = `
            <div class="alert alert-info">
                ${result.total_success} succeeded, ${result.total_failed} failed.
            </div>
            <h6>Successful</h6>
            <ul class="list-group mb-3">${successRows || '<li class="list-group-item text-muted">None</li>'}</ul>
            <h6>Failed</h6>
            <ul class="list-group">${failedRows || '<li class="list-group-item text-muted">None</li>'}</ul>
        `;
    }

    function escapeHtml(value) {
        return String(value)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
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

    evaluateBtn.addEventListener('click', function() {
        pendingSubmission = getSelectedCourses();

        if (pendingSubmission.length === 0) {
            alert('Please select at least one course');
            return;
        }

        renderReview(pendingSubmission);
        reviewModal.show();
    });

    confirmSubmitBtn.addEventListener('click', async function() {
        if (pendingSubmission.length === 0) return;

        reviewModal.hide();
        spinner.classList.add('show');
        confirmSubmitBtn.disabled = true;

        try {
            const response = await fetch('{{ url_for("api_evaluate") }}', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ courses: pendingSubmission, semester: '{{ semester_code }}' })
            });

            const result = await response.json();
            spinner.classList.remove('show');
            confirmSubmitBtn.disabled = false;

            if (result.success) {
                renderResults(result);
                resultsModal.show();
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            spinner.classList.remove('show');
            confirmSubmitBtn.disabled = false;
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
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in") or not session.get("portal_session_id"):
            return redirect(url_for("login"))
        if session.get("portal_session_id") not in PORTAL_SESSIONS:
            session.clear()
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def portal_headers(extra=None):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    if extra:
        headers.update(extra)
    return headers


def get_portal_session():
    portal_session_id = session.get("portal_session_id")
    return PORTAL_SESSIONS.get(portal_session_id)


def login_to_portal(username, password):
    http_session = requests.Session()
    headers = portal_headers({
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": BASE,
        "Referer": LOGIN_URL,
    })
    data = {"username": username, "password": password, "login": "Login"}

    try:
        response = http_session.post(LOGIN_URL, headers=headers, data=data, timeout=REQUEST_TIMEOUT)
        success = response.status_code == 200 and "logout" in response.text.lower()
        return (http_session, None) if success else (None, "Invalid credentials")
    except requests.RequestException as exc:
        return (None, f"Login request failed: {exc}")


def access_evaluation_page(http_session):
    try:
        response = http_session.get(EVAL_PAGE_URL, headers=portal_headers(), timeout=REQUEST_TIMEOUT)
        return response.status_code == 200
    except requests.RequestException:
        return False


def parse_courses_from_xml(xml_text):
    courses = []
    row_pattern = r"<row[^>]*>(.*?)</row>"
    cell_pattern = r"<cell[^>]*><!\[CDATA\[(.*?)\]\]></cell>"

    rows = re.findall(row_pattern, xml_text, re.DOTALL)

    for row_content in rows:
        cells = re.findall(cell_pattern, row_content)

        if len(cells) >= 9:
            status_cell = cells[7]
            status = "evaluated"
            eval_code = None

            if "not evaluated" in status_cell.lower():
                status = "not evaluated"
                eval_match = re.search(r'load_eval_form\("([^"]+)"', status_cell)
                if eval_match:
                    eval_code = eval_match.group(1)

            courses.append({
                "semester": cells[0],
                "course_code": cells[1],
                "section": cells[2],
                "course_name": cells[3],
                "instructor": cells[4],
                "units": cells[5],
                "type": cells[6],
                "status": status,
                "eval_code": eval_code,
            })

    return courses


def load_courses_from_portal(http_session, semester_code=DEFAULT_SEMESTER_CODE):
    headers = portal_headers({
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": EVAL_PAGE_URL,
    })
    data = {"param": semester_code}

    try:
        response = http_session.post(LOAD_COURSES_URL, headers=headers, data=data, timeout=REQUEST_TIMEOUT)
        response_text = response.text.strip()
        if response.status_code == 200 and (response_text.startswith("<?xml") or response_text.startswith("<rows")):
            return parse_courses_from_xml(response.text)
    except requests.RequestException:
        pass

    return []


def clamp_comment(comment):
    return (comment or "").strip()[:500]


def normalize_rating(rating):
    rating = (rating or "neutral").lower().strip()
    return rating if rating in {"good", "neutral", "bad"} else "neutral"


def normalize_semester_code(semester_code):
    return semester_code if semester_code in VALID_SEMESTER_CODES else DEFAULT_SEMESTER_CODE


def score_for_rating(rating):
    rating = normalize_rating(rating)
    if rating == "good":
        return "5-'1"
    if rating == "bad":
        return "1-'1"
    return "3-'1"


def special_score_for_rating(rating):
    rating = normalize_rating(rating)
    if rating == "good":
        return "5-6"
    if rating == "bad":
        return "1-6"
    return "3-6"


def build_payload(eval_code, course_units=None, rating="neutral", comment=""):
    payload = {}

    if "::" in eval_code:
        parts = eval_code.split("::")
        units = course_units if course_units else 3
        eval_course_formatted = f"{parts[0]}-1-{parts[1]}-{parts[2]}-{units}-0"
    else:
        eval_course_formatted = eval_code

    payload["eval_course"] = eval_course_formatted

    score = score_for_rating(rating)

    # Section 1 questions
    for q in range(1, 6):
        payload[f"1-{q}-2"] = score

    # Section 2 question 1 appears to use a different answer format.
    payload["2-1-4"] = special_score_for_rating(rating)

    # Section 2 remaining questions
    for q in range(2, 20):
        payload[f"2-{q}-2"] = score

    # Written comment field
    payload["3-1-3-8"] = clamp_comment(comment)

    return payload


def submit_evaluation_once(http_session, eval_code, course_units=None, rating="neutral", comment=""):
    headers = portal_headers({
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": EVAL_PAGE_URL,
    })
    payload = build_payload(eval_code, course_units, rating, comment)

    response = http_session.post(
        SAVE_EVALUATION_URL,
        headers=headers,
        data=urlencode(payload),
        timeout=SUBMIT_TIMEOUT,
    )
    if response.status_code != 200:
        return False, f"Portal returned status {response.status_code}"

    # The original version only checked status_code == 200. Keep that behavior,
    # but reject obvious HTML login redirects/errors when possible.
    body = response.text.lower()
    if "login" in body and "password" in body:
        return False, "Portal session expired"

    return True, "Submitted"


def submit_evaluation(http_session, eval_code, course_units=None, rating="neutral", comment=""):
    last_error = "Unknown error"

    for attempt in range(1, MAX_SUBMIT_RETRIES + 1):
        try:
            ok, message = submit_evaluation_once(http_session, eval_code, course_units, rating, comment)
            if ok:
                return True, message
            last_error = message
        except requests.RequestException as exc:
            last_error = str(exc)

        if attempt < MAX_SUBMIT_RETRIES:
            time.sleep(1)

    return False, last_error


def safe_int(value, default=3):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

# ==================== ROUTES ====================
@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            return render_template_string(LOGIN_TEMPLATE, error="Please enter credentials")

        http_session, error = login_to_portal(username, password)
        if error:
            return render_template_string(LOGIN_TEMPLATE, error=error)

        if not access_evaluation_page(http_session):
            return render_template_string(LOGIN_TEMPLATE, error="Could not access evaluation page")

        portal_session_id = str(uuid.uuid4())
        PORTAL_SESSIONS[portal_session_id] = http_session

        session.clear()
        session["logged_in"] = True
        session["username"] = username
        session["portal_session_id"] = portal_session_id
        session.permanent = True

        return redirect(url_for("dashboard"))

    return render_template_string(LOGIN_TEMPLATE)


@app.route("/dashboard")
@login_required
def dashboard():
    semester_code = normalize_semester_code(request.args.get("semester", DEFAULT_SEMESTER_CODE))

    http_session = get_portal_session()
    courses = load_courses_from_portal(http_session, semester_code)

    stats = {"total": 0, "evaluated": 0, "pending": 0}
    error = None

    if courses:
        pending = [c for c in courses if c["status"] == "not evaluated" and c["eval_code"]]
        evaluated = [c for c in courses if c["status"] == "evaluated"]
        stats = {"total": len(courses), "evaluated": len(evaluated), "pending": len(pending)}
    else:
        error = "Could not load courses for this semester"

    return render_template_string(
        DASHBOARD_TEMPLATE,
        error=error,
        courses=courses,
        stats=stats,
        semester_code=semester_code,
        semester_options=SEMESTER_OPTIONS,
    )


@app.route("/api/evaluate", methods=["POST"])
@login_required
def api_evaluate():
    data = request.get_json(silent=True) or {}
    selected_courses = data.get("courses", [])
    semester_code = normalize_semester_code(data.get("semester", DEFAULT_SEMESTER_CODE))

    if not isinstance(selected_courses, list) or not selected_courses:
        return jsonify({"success": False, "error": "No courses selected"})

    http_session = get_portal_session()
    all_courses = load_courses_from_portal(http_session, semester_code)
    course_map = {course["course_code"]: course for course in all_courses}

    results = {"success": [], "failed": []}

    for item in selected_courses:
        if not isinstance(item, dict):
            results["failed"].append({"course_name": "Unknown", "error": "Invalid course selection"})
            continue

        course_code = item.get("course_code")
        rating = normalize_rating(item.get("rating"))
        comment = clamp_comment(item.get("comment"))

        course = course_map.get(course_code)
        if not course:
            results["failed"].append({
                "course_code": course_code or "Unknown",
                "course_name": item.get("course_name", "Unknown"),
                "rating": rating,
                "error": "Course was not found in the loaded semester",
            })
            continue

        if course["status"] == "evaluated":
            results["failed"].append({
                "course_code": course_code,
                "course_name": course["course_name"],
                "rating": rating,
                "error": "Course is already evaluated",
            })
            continue

        if not course.get("eval_code"):
            results["failed"].append({
                "course_code": course_code,
                "course_name": course["course_name"],
                "rating": rating,
                "error": "Missing evaluation code",
            })
            continue

        units = safe_int(course.get("units"), 3)
        ok, message = submit_evaluation(http_session, course["eval_code"], units, rating, comment)

        if ok:
            results["success"].append({
                "course_code": course_code,
                "course_name": course["course_name"],
                "rating": rating,
                "comment": comment,
            })
        else:
            results["failed"].append({
                "course_code": course_code,
                "course_name": course["course_name"],
                "rating": rating,
                "comment": comment,
                "error": message,
            })

        time.sleep(DELAY_BETWEEN_EVALUATIONS_SECONDS)

    return jsonify({
        "success": True,
        "results": results,
        "total_success": len(results["success"]),
        "total_failed": len(results["failed"]),
    })


@app.route("/logout")
def logout():
    portal_session_id = session.get("portal_session_id")
    if portal_session_id:
        PORTAL_SESSIONS.pop(portal_session_id, None)
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\n" + "=" * 58)
    print("Al-Quds Course Evaluation - Updated Web App")
    print("=" * 58)
    print(f"\nStarting server on port {port}...")
    print(f"Open your browser: http://localhost:{port}\n")
    app.run(debug=False, host="0.0.0.0", port=port)
