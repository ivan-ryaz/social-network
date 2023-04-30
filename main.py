from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user, login_required, LoginManager, UserMixin, login_user, logout_user
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager
from operator import itemgetter

app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'secret_key'

# Инициализация базы данных
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Определение модели User
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='author', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)


    def get_id(self):
        return str(self.id)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=True)

    def repr(self):
        return f"Role('{self.name}')"


class UserRoles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)

    def repr(self):
        return f"UserRoles('{self.user_id}', '{self.role_id}')"


# Определение модели Post
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def repr(self):
        return f"Post('{self.title}', '{self.date_posted}')"


# Определение модели Message
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Message {}>'.format(self.body)


# Создание таблиц базы данных
with app.app_context():
    db.create_all()


@login_required
def check_auth():
    return 'YES'


# Роутинг и контроллеры
@app.route('/')
def home():
    if check_auth() == 'YES':
        return render_template('main_chat.html')
    posts = Post.query.order_by(Post.date_posted.desc()).all()

    return render_template('home.html', posts=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created successfully', 'success')

        return redirect(url_for('login'))
    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if not user or not user.password == password:
            flash('Invalid email or password, please try again', 'danger')
            return redirect(url_for('login'))
        login_user(user)
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('home'))
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))




@login_required
@app.route('/messages')
def messages():
    chats = Message.query.filter((Message.sender_id == current_user.id) |
                                 (Message.recipient_id == current_user.id)
                                 ).group_by(
        Message.sender_id,
        Message.recipient_id,
        Message.body,
        Message.timestamp
    ).all()
    return render_template('messages.html',
                           chats=sorted(chats,
                                        key=lambda x: x.timestamp,
                                        reverse=True
                                        ),
                           User=User)


@login_required
@app.route('/new_message', methods=['GET', 'POST'])
def new_message():
    if request.method == 'POST':
        recipient_username = request.form['recipient']
        body = request.form['body']

        # Проверяем, существует ли пользователь-получатель
        recipient = User.query.filter_by(email=recipient_username).first()
        if not recipient:
            flash('User not found', 'danger')
            return redirect(url_for('messages'))

        # Создаем новое сообщение
        message = Message(sender_id=current_user.id,
                          recipient_id=recipient.id,
                          body=body)
        db.session.add(message)
        db.session.commit()

        flash('Message sent successfully', 'success')
        return redirect(url_for('messages'))

    # Если метод GET, просто отрисовываем шаблон
    return render_template('new_message.html')


if __name__ == '__main__':
    app.run()