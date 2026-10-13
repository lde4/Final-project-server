# ====================================================================
# חלק א': ייבוא הספריות המיושר והתקני לשרת פלאסק, סוקטים ו-MySQL
# ====================================================================
import socket          # מפעיל את שרת הסוקטים הטהור ברקע (TCP Socket Server) להאזנה בפורט 12345
import json            # מאפשר להמיר ולפענח חבילות מידע בין טקסט (JSON) לאובייקטים של פייתון
import threading       # מאפשר להריץ את שרת הסוקטים בחוט (Thread) נפרד במקביל לפלאסק כדי שהשרת לא ייחסם
import random          # מיועד להגרלה האקראית של 2 שאלות אבטחה מתוך מאגר 6 השאלות שהמשתמש מילא
import pymysql         # מקשר ומחבר פיזית את קוד הפייתון לבסיס הנתונים MySQL (עבור הסיסמה 1234 והמשתמש root)
from flask import Flask, render_template, jsonify, request  # רכיבי הליבה של פלאסק ליצירת השרת, שליפת נתונים והחזרת תשובות JSON לאתר
from flask_cors import CORS  # ספריית הגנה חובה המונעת מהדפדפן לחסום את קריאות ה-fetch של האתר מול שרת הפלאסק
from datetime import datetime  # משמשת לשליפת השעה והתאריך המדויקים ברגע הלוגאין לצורך עדכון עמודת החיבור האחרון ב-MySQL

app = Flask(__name__)  # יצירת אפליקציית פלאסק
CORS(app)  # הפעלת הגדרות ה-CORS

# ====================================================================
# פונקציה ליצירת חיבור פיזי ותקני למסד הנתונים MySQL בכל פעולה
# ====================================================================
def get_db_connection():
    return pymysql.connect(
        host='127.0.0.1',
        user='root',
        password='1234',
        database='lmap_db',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# ====================================================================
# חלק ב': שרת סוקטים רגיל (TCP Socket Server) של פייתון המקושר ל-MySQL
# ====================================================================
def run_python_socket_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('127.0.0.1', 12345))
    server_socket.listen(5)
    print("שרת הסוקטים הרגיל של פייתון רץ ומקשיב בכתובת 127.0.0.1:12345...")

    while True:
        client_conn, client_addr = server_socket.accept()
        client_thread = threading.Thread(target=handle_socket_client, args=(client_conn,))
        client_thread.start()

def handle_socket_client(conn):
    try:
        raw_data = conn.recv(4096)
        if not raw_data: return
        request_json = json.loads(raw_data.decode('utf-8'))
        action = request_json.get('action')
        user_data = request_json.get('data')
        response = {'success': False, 'message': 'Unknown action'}

        if action == 'register':
            username = user_data.get('username')
            db = get_db_connection()
            with db.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cursor.fetchone():
                    response = {'success': False, 'message': 'User already exists'}
                else:
                    sql = """INSERT INTO users (username, email, password, ans1, ans2, ans3, ans4, ans5, ans6, is_admin) 
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                    cursor.execute(sql, (
                        username, user_data.get('email'), user_data.get('password'),
                        user_data.get('ans1'), user_data.get('ans2'), user_data.get('ans3'),
                        user_data.get('ans4'), user_data.get('ans5'), user_data.get('ans6'),
                        True if username.lower() == 'admin' else False
                    ))
                    db.commit()
                    response = {'success': True}
            db.close()

        conn.sendall(json.dumps(response).encode('utf-8'))
    except Exception as e:
        print(f"שגיאה בטיפול בסוקט: {e}")
    finally:
        conn.close()

# ====================================================================
# חלק ג': נתיבי ה-API עבור דפי ה-HTML (מחוברים כולם ל-MySQL)
# ====================================================================

@app.route('/api/register', methods=['POST'])
def web_register():
    data = request.get_json()
    username = data.get('username')

    try:
        db = get_db_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'שם המשתמש כבר תפוס במערכת!'})

            sql = """INSERT INTO users (username, email, password, ans1, ans2, ans3, ans4, ans5, ans6, is_admin) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (
                username, data.get('email'), data.get('password'),
                data.get('ans1'), data.get('ans2'), data.get('ans3'),
                data.get('ans4'), data.get('ans5'), data.get('ans6'),
                True if username.lower() == 'admin' else False
            ))
            db.commit()
        db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'})


@app.route('/api/login', methods=['POST'])
def web_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    try:
        db = get_db_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            found_user = cursor.fetchone()

            if not found_user:
                return jsonify({'success': False, 'message': 'שם המשתמש אינו קיים במערכת!'})
            if found_user['password'] != password:
                return jsonify({'success': False, 'message': 'הסיסמה שהוקלדה שגויה!'})

            now_str = datetime.now().strftime("%d/%m/%Y , %H:%M")
            cursor.execute("UPDATE users SET last_login = %s WHERE username = %s", (now_str, username))
            db.commit()
        db.close()
        return jsonify({'success': True, 'username': username})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'})


@app.route('/api/forgot-password', methods=['POST'])
def web_forgot_password():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')

    try:
        db = get_db_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            found_user = cursor.fetchone()

            if not found_user:
                return jsonify({'success': False, 'message': 'שם המשתמש אינו קיים במערכת!'})
            if found_user['email'].lower() != email.lower():
                return jsonify({'success': False, 'message': 'כתובת האימייל אינה תואמת למשתמש זה!'})

        db.close()

        # מאגר 6 השאלות הרשמיות של התוכנה
        all_questions = [
            {'id': 'q1', 'text': "What was the name of your first pet?"},
            {'id': 'q2', 'text': "In what city were you born?"},
            {'id': 'q3', 'text': "What was the name of your primary school?"},
            {'id': 'q4', 'text': "What is your favorite food?"},
            {'id': 'q5', 'text': "What is the name of your paternal grandfather?"},
            {'id': 'q6', 'text': "What is your mother's maiden name?"}
        ]

        # 🎲 הגרלה אקראית לחלוטין של 2 שאלות מתוך מאגר ה-6 ללא חזרות
        lucky_questions = random.sample(all_questions, 2)

        # 🔧 התיקון המושלם: הפרדה מדויקת בין השאלה הראשונה [0] לשאלה השנייה [1]
        return jsonify({
            'success': True,
            'questionA_id': lucky_questions[0]['id'],
            'questionA_text': lucky_questions[0]['text'],
            'questionB_id': lucky_questions[1]['id'],
            'questionB_text': lucky_questions[1]['text']
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'})


@app.route('/api/verify-security-answers', methods=['POST'])
def verify_security_answers():
    data = request.get_json()
    username = data.get('username')
    qA_id = data.get('qA_id')
    qA_ans = data.get('qA_ans')
    qB_id = data.get('qB_id')
    qB_ans = data.get('qB_ans')

    try:
        db = get_db_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            found_user = cursor.fetchone()

            if not found_user:
                return jsonify({'success': False, 'message': 'משתמש זה לא נמצא!'})

            id_to_field = {'q1': 'ans1', 'q2': 'ans2', 'q3': 'ans3', 'q4': 'ans4', 'q5': 'ans5', 'q6': 'ans6'}
            correct_ans_A = found_user.get(id_to_field.get(qA_id))
            correct_ans_B = found_user.get(id_to_field.get(qB_id))

            if qA_ans == correct_ans_A and qB_ans == correct_ans_B:
                return jsonify({'success': True})

            return jsonify({'success': False, 'message': 'אחת או יותר מהתשובות לשאלות האבטחה שגויה!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'})
    finally:
        db.close()


@app.route('/api/update-password', methods=['POST'])
def web_update_password():
    data = request.get_json()
    username = data.get('username')
    new_password = data.get('newPassword')

    try:
        db = get_db_connection()
        with db.cursor() as cursor:
            cursor.execute("UPDATE users SET password = %s WHERE username = %s", (new_password, username))
            db.commit()
        db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'})


@app.route('/api/users', methods=['GET'])
def get_users_api():
    try:
        db = get_db_connection()
        with db.cursor() as cursor:
            cursor.execute("SELECT username, email, is_admin as isAdmin, last_login as lastLogin FROM users")
            users = cursor.fetchall()
        db.close()
        return jsonify(users)
    except Exception as e:
        return jsonify([])


@app.route('/api/delete/<username>', methods=['POST'])
def delete_user_api(username):
    try:
        db = get_db_connection()
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE username = %s", (username,))
            db.commit()
        db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'})


# הפעלת שרת הסוקטים וה-Flask במקביל
if __name__ == '__main__':
    socket_thread = threading.Thread(target=run_python_socket_server)
    socket_thread.daemon = True
    socket_thread.start()

    app.run(port=5000, debug=True, use_reloader=False)
