from flask import Flask, render_template, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import stripe

app = Flask(__name__)
stripe.api_key = 'sk_test_51KrAd0ElpesYPEZku8wyaCgsfPaQTq8CsxaoI98GwuI29uYqI22MpFsfDyhNE0weWmjoAbqnPNJBSRMj4FlfDQbV00wJE3mdrE'
add_product_to_cart = None

"""
Configure Database
"""
app.config['SECRET_KEY'] = 'top-secret-key-1234'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


"""
User Tabel Configz
"""


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True)
    email = db.Column(db.String(50), unique=True, nullable=False)
    f_name = db.Column(db.String(50), unique=False, nullable=False)
    l_name = db.Column(db.String(50), unique=False, nullable=False)
    phone = db.Column(db.String(50), unique=False, nullable=False)
    address1 = db.Column(db.String(75), unique=False, nullable=False)
    address2 = db.Column(db.String(75), unique=False, nullable=False)
    city = db.Column(db.String(50), unique=False, nullable=False)
    state = db.Column(db.String(50), unique=False, nullable=False)
    zipcode = db.Column(db.String(25), unique=False, nullable=False)
    country = db.Column(db.String(75), unique=False, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    cart = db.relationship('Cart', lazy='joined', backref='user')


class Product(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    price = db.Column(db.Float, unique=False, nullable=False)
    details = db.Column(db.String(500), nullable=False)
    inventory = db.Column(db.Integer, unique=False, nullable=False)
    img_file = db.Column(db.String(1000), nullable=False)
    quant = db.Column(db.Integer, unique=False, nullable=True)
    cart = db.relationship('Cart', lazy='joined', backref='product')


class Cart(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


# db.create_all()


def create_product(title, price, details, inventory, img_file):
    '''Creates and commits a new product to the shop database'''
    new_product = Product(title=title, price=price, details=details, inventory=inventory, img_file=img_file)
    db.session.add(new_product)
    db.session.commit()


# create_product(
#     title='Simple Tee',
#     price=21.96,
#     details='This is the Simple Tee. Designed with minimalism in mind. See what everyone is talking about.',
#     inventory=31,
#     img_file='static/images/simple_tee.jpg'
# )
# create_product(
#     title='Hotel Tee',
#     price=33.96,
#     details='This is the Hotel Tee. Love your favorite home away from home. Designed with minimalism in mind. See what everyone is talking about.',
#     inventory=31,
#     img_file='static/images/hotel_tee.jpg'
# )

"""
Routes
"""


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == "POST":
        product_id = request.form.get('product_id')
        product_cart = request.form.get('product_cart')
        if product_id:
            product = Product.query.filter_by(id=product_id).first()
            return render_template('product.html', product=product)
        elif product_cart:
            global add_product_to_cart
            add_product_to_cart = Product.query.filter_by(id=product_cart).first()
            return redirect('cart')
    products = Product.query.all()
    return render_template('index.html', products=products)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        # Email doesn't exist or password incorrect.
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('cart'))

    return render_template("login.html", logged_in=current_user.is_authenticated)


@app.route("/create-account", methods=['GET', "POST"])
def create_account():
    if request.method == "POST":

        if User.query.filter_by(email=request.form.get('email')).first():
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            request.form.get('password'),
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=request.form.get('email'),
            f_name=request.form.get('f_name'),
            l_name=request.form.get('l_name'),
            phone=request.form.get('phone'),
            address1=request.form.get('address1'),
            address2=request.form.get('address2'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            zipcode=request.form.get('zipcode'),
            country=request.form.get('country'),
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("cart"))

    return render_template("create_account.html", logged_in=current_user.is_authenticated)


@app.route('/cart', methods=['POST', 'GET'])
@login_required
def cart():
    global add_product_to_cart
    if request.method == 'POST':
        delete_id = request.form.get('delete_id')
        item_to_delete = Cart.query.get(delete_id)
        db.session.query(Cart).filter(Cart.id == item_to_delete.id).delete()
        db.session.commit()

    user_cart = Cart.query.filter_by(user_id=current_user.id).all()
    cart_total = round(0, 2)

    if add_product_to_cart == None and user_cart == None:
        user_cart = None
        return render_template('cart.html', user_cart=user_cart, cart_total=cart_total)
    elif add_product_to_cart:
        add_to_cart = Cart(
            product_id=add_product_to_cart.id,
            user_id=current_user.id
        )

        db.session.add(add_to_cart)
        db.session.commit()
        user_cart = Cart.query.filter_by(user_id=current_user.id).all()
        for product in user_cart:
            cart_total += product.product.price
            cart_total = round(cart_total, 2)
        add_product_to_cart = None
        return render_template('cart.html', user_cart=user_cart, cart_total=cart_total)
    for product in user_cart:
        cart_total += product.product.price
        cart_total = round(cart_total, 2)
    return render_template('cart.html', user_cart=user_cart, cart_total=cart_total)


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    user_cart = Cart.query.filter_by(user_id=current_user.id).all()
    items = []
    for product in user_cart:
        new_item = {
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': product.product.title,
                },
                'unit_amount': int(product.product.price * 100),
            },
            'quantity': 1,
        }
        items.append(new_item)
    session = stripe.checkout.Session.create(
        line_items=items,
        mode='payment',
        success_url='http://127.0.0.1:5000/success',
        cancel_url='http://127.0.0.1:5000/cart',
    )

    return redirect(session.url, code=303)


@app.route('/success')
@login_required
def success():
    user_cart_items = db.session.query(Cart).filter(Cart.user_id == current_user.id).all()
    for item in user_cart_items:
        db.session.delete(item)
        db.session.commit()
    return render_template('success.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
