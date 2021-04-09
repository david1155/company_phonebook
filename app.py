from flask import Flask, g, request, session, redirect, url_for, render_template, Response
from flask_simpleldap import LDAP
import sqlite3
import datetime
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from reportlab.platypus.tables import TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle

from config import *


def connect_db():
    return sqlite3.connect('employees.db')


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def vCard_gen(person):
    vcf = "BEGIN:VCARD"
    vcf += "\n"
    vcf += "VERSION:3.0"
    vcf += "\n"
    vcf += "N:" + person.get('lastname') + ";" + person.get('firstname')
    vcf += "\n"
    vcf += "FN:" + person.get('firstname') + " " + person.get('middlename') + " " + person.get('lastname')
    vcf += "\n"
    vcf += "EMAIL;TYPE=INTERNET:" + person.get('email')
    vcf += "\n"
    vcf += "ORG:"+org_vcard
    vcf += "\n"
    if person.get('cellphone') != "" and person.get('cellphone') is not None:
        vcf += "TEL;type=CELL;type=pref:" + person.get('cellphone')
        vcf += "\n"
    if person.get('intphone') != "" and person.get('intphone') is not None:
        vcf += "TEL;type=WORK:" + person.get('intphone')
        vcf += "\n"
    if person.get('position') != "" and person.get('position') is not None:
        vcf += "TITLE:" + person.get('position')
        vcf += "\n"
    if person.get('birthday') != "" and person.get('birthday') is not None:
        try:
            vcf += "BDAY;VALUE=DATE:" + datetime.datetime.strptime(person.get('birthday'), '%d.%m.%Y').strftime(
                '%Y-%m-%d')
            vcf += "\n"
        except:
            pass
    vcf += "END:VCARD"
    return (vcf)


app = Flask(__name__)

# app.config['LDAP_SCHEMA'] = 'ldaps'
# app.config['LDAP_BASE_DN'] = ldap_base
# app.config['LDAP_HOST'] = ldap_host
# app.config['LDAP_PORT'] = 636
# app.config['LDAP_USE_SSL'] = True
# app.config['LDAP_USERNAME'] = ldap_user
# app.config['LDAP_PASSWORD'] = ldap_password
# app.config['LDAP_USER_OBJECT_FILTER'] = '(sAMAccountName=%s)'

app.config['SECRET_KEY'] = secret_key
# ldap = LDAP(app)


@app.before_request
def before_request():
    g.user = None
    # if 'user_id' in session:
    #     # This is where you'd query your database to get the user info.
    #     g.user = {}
        # Create a global with the LDAP groups the user is a member of.
        # g.ldap_groups = ldap.get_user_groups(user=session['user_id'])
    g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
    g.db.close()


@app.route('/')
# @ldap.login_required
def index():
    # username = remove_prefix(session['user_id'], conf_domain+'\\')
    # if str(username).lower() in admin_users:
    #     admin = True
    # else:
    #     admin = False

    cur = g.db.execute(
        'SELECT id, position, lastname, firstname, middlename, intphone, cellphone, email, birthday, login FROM persons WHERE active ORDER BY lastname')

    people = []
    login_id = False
    for row in cur.fetchall():
        people.append({
            'id': row[0],
            'position': row[1],
            'lastname': row[2],
            'firstname': row[3],
            'middlename': row[4],
            'intphone': row[5],
            'cellphone': row[6],
            'email': row[7],
            'birthday': row[8],
        })

        # if str(username).casefold() == str(row[9]).casefold():
        #     login_id = row[0]

    return render_template('phonebook.html', people=people, login_id=login_id, admin=admin)


@app.route('/new', endpoint='edit', methods=['GET', 'POST'])
@app.route('/edit/<id>', methods=['GET', 'POST'])
# @ldap.login_required
def edit(id=None):
    # username = remove_prefix(session['user_id'], conf_domain+'\\')
    # if str(username).lower() in admin_users:
    #     admin = True
    # else:
    #     admin = False
    person = False
    if request.form:
        valid = True
        if valid:
            if not id:
                g.db.execute("""insert into persons(firstname, middlename, lastname, intphone, cellphone, email, position, birthday, login)
                        values(?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
                    request.form['firstname'],
                    request.form['middlename'],
                    request.form['lastname'],
                    request.form['intphone'],
                    request.form['cellphone'],
                    request.form['email'],
                    request.form['position'],
                    request.form['birthday'],
                    request.form['login'],
                ])
            elif "birthday" in request.form and "cellphone" in request.form and "email" not in request.form:
                g.db.execute("""update persons set cellphone=?, birthday=? where id=?""", [
                    request.form['cellphone'],
                    request.form['birthday'],
                    id,
                ])
                g.db.commit()
                return redirect(url_for('index'))
            else:
                g.db.execute("""update persons set firstname=?, middlename=?, lastname=?,
                        intphone=?, cellphone=?, email=?, position=?, birthday=?, login=? where id=?""", [
                    request.form['firstname'],
                    request.form['middlename'],
                    request.form['lastname'],
                    request.form['intphone'],
                    request.form['cellphone'],
                    request.form['email'],
                    request.form['position'],
                    request.form['birthday'],
                    request.form['login'],
                    id,
                ])
            g.db.commit()
            return redirect(url_for('index'))
        else:
            person = request.form
    else:
        if id:
            row = g.db.execute(
                """select firstname, middlename, lastname, intphone, cellphone, email, position, birthday, login from persons where id=?""",
                [id]).fetchone()
            person = {'firstname': row[0],
                      'middlename': row[1],
                      'lastname': row[2],
                      'intphone': row[3],
                      'cellphone': row[4],
                      'email': row[5],
                      'position': row[6],
                      'birthday': row[7],
                      'login': row[8],
                      }

    return render_template('edit.html', person=person, admin=admin, username=username)


@app.route('/delete/<id>')
# @ldap.login_required
def delete(id):
    username = remove_prefix(session['user_id'], 'MAIN\\')
    if username in admin_users:
        admin = True
    else:
        admin = False
    g.db.execute('delete from persons where id=?', [id])
    g.db.commit()
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('index'))
    if request.method == 'POST':
        user = remove_prefix(request.form['user'], conf_domain + '\\')
        passwd = request.form['passwd']
        test = ldap.bind_user(user, passwd)
        if test is None or passwd == '':
            return render_template('login.html', failed=True)
        else:
            session['user_id'] = remove_prefix(request.form['user'], conf_domain + '\\')
            return redirect('/')
    return render_template('login.html', failed=False)


@app.route('/vCard/<id>.vcf')
# @ldap.login_required
def vCard(id):
    row = g.db.execute(
        """select firstname, middlename, lastname, intphone, cellphone, email, position, birthday from persons where id=?""",
        [id]).fetchone()
    person = {'firstname': row[0],
              'middlename': row[1],
              'lastname': row[2],
              'intphone': row[3],
              'cellphone': row[4],
              'email': row[5],
              'position': row[6],
              'birthday': row[7],
              }

    return Response(vCard_gen(person), mimetype='text/x-vcard')


@app.route('/vCard/all.vcf')
# @ldap.login_required
def vCard_all():
    cur = g.db.execute(
        'SELECT id, position, lastname, firstname, middlename, intphone, cellphone, email, birthday, login FROM persons WHERE active ORDER BY lastname')
    people = []
    for row in cur.fetchall():
        people.append({
            'id': row[0],
            'position': row[1],
            'lastname': row[2],
            'firstname': row[3],
            'middlename': row[4],
            'intphone': row[5],
            'cellphone': row[6],
            'email': row[7],
            'birthday': row[8],
        })

    vcard_phonebook = ""

    for person in people:
        vcard_phonebook += vCard_gen(person)

    return Response(vcard_phonebook, mimetype='text/x-vcard')


@app.route('/phonebook.pdf')
# @ldap.login_required
def pdf_phonebook():
    def make_doc():
        pdfmetrics.registerFont(TTFont('HelvRu', 'helv_ru.ttf'))
        pdf = io.BytesIO()

        doc = SimpleDocTemplate(pdf, leftMargin=30, rightMargin=30, topMargin=20, bottomMargin=0,
                                pagesize=landscape(A4))

        story = []

        data = [
            ['Title', 'Last Name', 'First Name', 'Middle Name', 'Extension', 'Mobile phone', 'E-Mail', 'Birthday']]

        cur = g.db.execute(
            'SELECT position, lastname, firstname, middlename, intphone, cellphone, email, birthday FROM persons WHERE active ORDER BY lastname')

        for row in cur.fetchall():
            data.append([
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                row[5],
                row[6],
                row[7],
            ])

        t = Table(data)
        data_len = len(data)
        for each in range(data_len):
            if each == 0:
                bg_color = colors.lightblue
            elif each % 2 == 0:
                bg_color = colors.whitesmoke
            else:
                bg_color = colors.lightgrey

            t.setStyle(TableStyle([('BACKGROUND', (0, each), (-1, each), bg_color)]))

        t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                               ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                               ('FONT', (0, 0), (-1, 100), font, 9)]))
        text_content = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        styles = getSampleStyleSheet()
        # styleN = styles['Normal']
        styleN = ParagraphStyle(
            name='Normal',
            fontName=font,
            fontSize=5,
        )
        styleH = ParagraphStyle(
            name='Normal',
            fontName=font,
            fontSize=16,
            alignment=1,
            leading=20,
        )
        styleH1 = ParagraphStyle(
            name='Normal',
            fontName=font,
            fontSize=10,
            alignment=1,
            leading=15,
        )

        p = Paragraph(text_content, styleN)
        h = Paragraph(header_content, styleH)
        h1 = Paragraph(header_content1, styleH1)

        story.append(h)
        story.append(h1)
        story.append(t)
        story.append(p)

        doc.build(story)
        pdf.seek(0)

        return pdf

    return Response(make_doc(), mimetype='application/pdf')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run()
