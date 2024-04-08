from flask import Flask,redirect,url_for,render_template,request,flash,abort,session,send_file
from flask_session import Session
from key import secret_key,salt1,salt2
from itsdangerous import URLSafeTimedSerializer
from stoken import token
import os
import mysql.connector
from cmail import sendmail
from io import BytesIO
from otp import genotp
app = Flask(__name__)
app.secret_key =secret_key
app.config['SESSION_TYPE']='filesystem'   

Session(app)
mydb=mysql.connector.connect(host="localhost",user="root",password="mysql",db='gall2')
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        name=request.form['name']
        email=request.form['email']
        password=request.form['password']
        gender=request.form['gender']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from register where name=%s',[name])
        count=cursor.fetchone()[0]
        cursor.execute('select count(*) from register where email=%s',[email])
        count1=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            flash('username already in use')
            return render_template('register.html')
        elif count1==1:
            flash('Email already in use')
            return render_template('register.html')
        data={'name':name,'email':email,'password':password,'gender':gender}
        subject='Email Confirmation'
        body=f"Thanks for signing up\n\nfollow this link for further steps-{url_for('confirm',token=token(data,salt1),_external=True)}"
        sendmail(to=email,subject=subject,body=body)
        flash('Confirmation link sent to mail')
        return redirect(url_for('login'))
    return render_template('register.html')
@app.route('/otp/<otp>/<name>/<email>/<password>/<gender>',methods=['GET','POST'])
def otp(otp,name,password,email,gender):
    if request.method=='POST':
        uotp=request.form['otp']
        if otp==uotp:
            cursor=mydb.cursor(buffered=True)
            lst=[name,email,password,gender]
            query='insert into register values(%s,%s,%s,%s)'
            cursor.execute(query,lst)
            mydb.commit()
            cursor.close()
            flash('Details Registered')
            return redirect(url_for('login'))
        else:
            flash('Wrong OTP')
            return render_template('otp.html',otp=otp,name=name,email=email,password=password,gender=gender)       
@app.route('/home')
def home():
    return render_template('dashboard.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))
    if request.method=='POST':
        name=request.form['name']
        password=request.form['password']
        print('hi')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('SELECT count(*) from register where name=%s and password=%s',[name,password])
        count=cursor.fetchone()[0]
        print(count)
        if count==1:
            session['user']=name
            if not session.get(name):
                session[name]={}
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt1,max_age=180)
    except Exception as e:
        abort (404,'Link Expired register again')
    else:
        cursor=mydb.cursor(buffered=True)
        email=data['email']
        cursor.execute('select count(*) from register where email=%s',[email])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.close()
            flash('You are already registerterd!')
            return redirect(url_for('login'))
        else:
            cursor.execute('insert into register values(%s,%s,%s,%s)',[data['name'],data['email'],data['password'],data['gender']])
            mydb.commit()
            cursor.close()
            flash('Details registered!')
            return redirect(url_for('login'))


@app.route('/aforget',methods=['GET','POST'])
def aforgot():
    if request.method=='POST':
        id1=request.form['name']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*),email from register where email=%s',[id1])
        count,email=cursor.fetchone()
        cursor.close()
        if count==1:
            cursor=mydb.cursor(buffered=True)
            subject='Forget Password'
            confirm_link=url_for('areset',token=token(id1,salt=salt2),_external=True)
            body=f"Use this link to reset your password-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Reset link sent check your email')
            return redirect(url_for('login'))
        else:
            flash('Invalid email id')
            return render_template('forgot.html')
    return render_template('forgot.html')


@app.route('/areset/<token>',methods=['GET','POST'])
def areset(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        id1=serializer.loads(token,salt=salt2,max_age=180)
    except:
        abort(404,'Link Expired')
    else:
        if request.method=='POST':
            newpassword=request.form['npassword']
            confirmpassword=request.form['cpassword']
            if newpassword==confirmpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update  register set password=%s where name=%s',[newpassword,id1])
                mydb.commit()
                flash('Reset Successful')
                return redirect(url_for('login'))
            else:
                flash('Passwords mismatched')
                return render_template('newpassword.html')
        return render_template('newpassword.html')
@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('index'))
    else:
        flash("already logged out")
        return redirect(url_for('login'))
@app.route('/additems',methods=['GET','POST'])
def additems():
    if request.method=="POST":
        image=request.files['image']
        description=request.form['desc']
        id1=genotp()
        cursor=mydb.cursor(buffered=True)
        filename=id1+'.jpg'
        cursor.execute('insert into additems(itemid,name,description) values(%s,%s,%s)',[id1,session.get('user'),description])
        mydb.commit()
        cursor.close()
        print(filename)
        path=os.path.dirname(os.path.abspath(__file__))
        static_path=os.path.join(path,'static')
        image.save(os.path.join(static_path,filename))
        
        print('success')
        return redirect(url_for('available'))
    return render_template('additems.html')

@app.route('/available')
def available():
    if session.get('user'):       
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select * from additems where name=%s',[session.get('user')])
        items=cursor.fetchall()
        print(items)
        cursor.close()
        return render_template('gallary.html',items=items)
    else:
        return redirect(url_for('login'))
@app.route('/deleteitem/<itemid>')
def deleteitem(itemid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('delete from additems where itemid=%s',[itemid])
    mydb.commit()
    cursor.close()
    path=os.path.dirname(os.path.abspath(__file__))
    static_path=os.path.join(path,'static')    
    filename=f"{itemid}.jpg"
    os.remove(os.path.join(static_path,filename))
    flash('item deleted successfully')
    return redirect(url_for('available'))
@app.route('/additems',methods=['GET','POST'])
def dashboard():
    return render_template('dashboard.html')
@app.route('/album')
def album():
    if session.get('user'):
        return render_template('album.html')
@app.route('/createalbum',methods=['GET','POST'])
def createalbum():
    if session.get('user'):  
        if request.method=='POST':
            name=request.form['name']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into album_names(album_name,added_by) values(%s,%s)',[name,session.get('user')])
            mydb.commit()
            cursor.close()
            return redirect(url_for('cb'))
    return render_template('createalbum.html')
@app.route('/cb')
def cb():
    if session.get('user'):       
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select * from album_names where added_by=%s',[session.get('user')])
        items=cursor.fetchall()
        print(items)
        cursor.close()
        return redirect(url_for('view1'))
    return render_template('createalbum.html',items=items)
    # else:
    #     return redirect(url_for('login'))
@app.route('/move/<itemid>',methods=['GET','POST'])
def move(itemid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select * from album_names where added_by=%s',[session.get('user')])
        items=cursor.fetchall()
        print(items)
        mydb.commit()
        cursor.close()
        return render_template('move.html',items=items,itemid=itemid) 
    else:
        return redirect(url_for('login'))
@app.route('/move1/<itemid>',methods=['GET','POST'])
def move1(itemid):
    if session.get('user'):
        if request.method=='POST':       
            cursor=mydb.cursor(buffered=True)
            '''cursor.execute('select * from album_names where added_by=%s',[session.get('user')])
            items1=cursor.fetchone()[0]
            print(items1)'''
            name=request.form['option']
            cursor.execute('insert into album(albumname,itemid,added_by) values(%s,%s,%s)',[name,itemid,session.get('user')])
            mydb.commit()
            cursor.close()
            return redirect(url_for('view1'))
    else:
        return redirect(url_for('login')) 

@app.route('/view/<album_name>')
def view(album_name):
    if session.get('user'): 
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select * from album where albumname=%s',[album_name])
        items1=cursor.fetchall()
        print(items1)
        cursor.close()
        return render_template('view.html',items1=items1)
    else:
        return redirect(url_for('login'))
@app.route('/view1')
def view1():
    if session.get('user'): 
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select * from album_names where added_by=%s',[session.get('user')])
        items1=cursor.fetchall()
        print(items1)
        cursor.close()
    return render_template('allalbums.html',items1=items1)
# @app.route('/available1')
# def available1():
#     if session.get('user'):       
#         cursor=mydb.cursor(buffered=True)
#         cursor.execute('select description from additems where name=%s',[session.get('user')])
#         itemss=cursor.fetchall()
#         print(itemss)
#         cursor.close()
#         return render_template('view.html',itemss=itemss)
#     else:
#         return redirect(url_for('login'))

app.run(debug=True, use_reloader=True)