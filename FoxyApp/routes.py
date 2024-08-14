from flask import render_template, redirect, request, url_for, flash, send_file
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from FoxyApp import app, bcrypt, db, mail, admins, api_key
from FoxyApp.forms import RegistrationForm, LoginForm, AccountForm, EditAccountForm, NewProductForm, RequestResetForm, ResetPasswordForm, PostForm, NewPictureForm, ToggleForm, CycleForm
from FoxyApp.models import User, Product, Post, Picture, Toggle
from FoxyApp.foxfiresheet import wks_order, wks_customer_details, wks_label, cycle, refresh_worksheet
from FoxyApp.foxfirepdf import createInvoice, driver_sheet
from FoxyApp.foxfiretok import get_account_token, approve_account_token
from FoxyApp.label import label
import secrets
import os
from PIL import Image, ImageOps
from datetime import datetime

@app.route("/admin", methods=["POST", "GET"])
@login_required
def admin():
    if current_user.email in admins:
        form = CycleForm()
        if request.method == "POST" and form.set_toggle.data == True:
            query = Product.query.order_by(Product.veg_name).filter_by(veg_sale=True)
            lis = list(query)
            prods = ["Name", "Location", "Total", "Comments"]
            for item in lis:
                prods.append(item.veg_name)
            cycle(prods)
            folder_path = 'FoxyApp/static/labels'
            entries = os.listdir(folder_path)
            files = [entry for entry in entries if os.path.isfile(os.path.join(folder_path, entry))]
            for f in files:
                label = os.path.join(app.root_path, "static/labels", f)
                os.remove(label)
            return render_template("admin.html", form=form)
        else:
            folder_path = 'FoxyApp/static/labels'
            entries = os.listdir(folder_path)
            files = [entry for entry in entries if os.path.isfile(os.path.join(folder_path, entry))]
            sorted_files = sorted(files, key=lambda x: os.path.getctime(os.path.join(folder_path, x)))
            return render_template("admin.html", form=form, labels=sorted_files)
    else:
        flash("You are not authorized.", "danger")


@app.route("/static/labels/<label>/delete", methods=["POST", "GET"])
@login_required
def labels(label):
    if current_user.email in admins:
        rem = os.path.join(app.root_path, "static/labels", label)
        return redirect(url_for('admin')), os.remove(rem)
    else:
        flash("You are not authorized.", "danger")

@app.route("/driver_form", methods=["POST", "GET"])
@login_required
def driver_form():
    if current_user.email in admins:
        orders = refresh_worksheet()
        driver_sheet(orders)
        path = "orders.pdf"
        return redirect(url_for('static', filename=path))

    else:
        flash("You are not authorized.", "danger")

@app.route("/orderform/<pdf>", methods=["POST", "GET"])
@login_required
def orderform(pdf):
    if current_user.email in admins:
        path = f"/var/www/foxfirefarmky.com/orderforms/{pdf}"
        return send_file(path, as_attachment=True)
    else:
        flash("You are not authorized.", "danger")


@app.route("/new_product.html", methods=["POST", "GET"])
@login_required
def new_product():
    if current_user.email in admins:
        prods = Product.query.all()
        form = NewProductForm()
        if form.validate_on_submit():
            if form.veg_image.data:
                picture = sav_thumbnail(form.veg_image.data)
                veggie = Product(veg_image=picture, veg_name=form.veg_name.data, veg_price=form.veg_price.data,
                                 veg_url=form.veg_url.data, veg_sale=form.veg_sale.data)
            else:
                veggie = Product(veg_image=form.veg_image.data, veg_name=form.veg_name.data,
                                 veg_price=form.veg_price.data, veg_url=form.veg_url.data, veg_sale=form.veg_sale.data)
            db.session.add(veggie)
            db.session.commit()

            # If product was listed for sale, update order form with new products so columns are not messed up
            if form.veg_sale.data == True:
                query = Product.query.order_by(Product.veg_name).filter_by(veg_sale=True)
                lis = list(query)
                prods = ["Name", "Location", "Total", "Comments"]
                for item in lis:
                    prods.append(item.veg_name)
                wks_order.append_row(prods)

            flash("Your new product has been added", "success")
            return redirect(url_for("new_product"))
        return render_template(url_for("new_product"), form=form, item_matrix=prods)
    flash("You are not authorized.", "danger")
    return render_template(url_for("home"))


@app.route("/new_picture.html", methods=["POST", "GET"])
@login_required
def new_picture():
    if current_user.email in admins:
        form = NewPictureForm()
        pics = Picture.query.all()
        if form.validate_on_submit():
            thumbnail = sav_pic_thumbnail(form.image.data)
            image = sav_picture(form.image.data)
            pic = Picture(image=image, thumbnail=thumbnail, name=form.name.data)
            db.session.add(pic)
            db.session.commit()
            flash("Your new image is uploaded", "success")
            return redirect(url_for("new_picture"))
        return render_template(url_for("new_picture"), form=form, pics=pics)
    flash("You are not authorized.", "danger")
    return render_template(url_for("home"))


@app.route("/picture/<name>/delete", methods=["POST", "GET"])
@login_required
def del_picture(name):
    if current_user.email in admins:
        pic = Picture.query.get_or_404(name)
        deleter(pic.image, pic.thumbnail)
        db.session.delete(pic)
        db.session.commit()
        flash("Your image was deleted", "success")
        return redirect(url_for("new_picture"))


@app.route("/product/<veg_id>", methods=["POST", "GET"])
@login_required
def edit_products(veg_id):
    if current_user.email in admins:
        prods = Product.query.get_or_404(veg_id)
        form = NewProductForm()
        if form.validate_on_submit():
            if form.veg_dlt.data == True:
                delete_veg(veg_id)
                return redirect(url_for('manage_products', post_id=prods.id))
            flash("The Item has been updated!", "success")
            prods.veg_name = form.veg_name.data
            prods.veg_price = form.veg_price.data
            prods.veg_url = form.veg_url.data
            if form.veg_image.data and not None:
                picture = sav_thumbnail(form.veg_image.data)
                prods.veg_image = picture

            # Translate text boolean to digit
            if form.veg_sale.data == True:
                form.veg_sale.data = 1
            else:
                form.veg_sale.data = 0

            #Check to see if the For Sale status has been changed. We need to know this to see if we need to update the orders sheet.
            if int(prods.veg_sale) != int(form.veg_sale.data):
                prods.veg_sale = form.veg_sale.data
                # update order form with new products so columns are not messed up
                query = Product.query.order_by(Product.veg_name).filter_by(veg_sale=True)
                lis = list(query)
                prods = ["Name", "Location", "Total", "Comments"]
                for item in lis:
                    prods.append(item.veg_name)
                wks_order.append_row(prods)
            prods = Product.query.get_or_404(veg_id)
            db.session.commit()
            return render_template("edit_product.html", form=form, item_matrix=prods)
        elif request.method == "GET":
            form.veg_name.data = prods.veg_name
            form.veg_price.data = prods.veg_price
            form.veg_url.data = prods.veg_url
            form.veg_image.data = prods.veg_image
            #  form.veg_sale.data = prods.veg_sale   this resulted in the checkbox being checked no matter the value.
            #  Resorted to IF statement in the template with checked=True/False for each condition.
        return render_template("edit_product.html", form=form, item_matrix=prods)


@app.route("/manage_products.html", methods=["POST", "GET"])
@login_required
def manage_products():
    if current_user.email in admins:
        form = ToggleForm()
        toggle = Toggle.query.filter_by(id=1).first()
        prods = Product.query.order_by(Product.veg_name).all()
        if form.validate_on_submit():
            #t = Toggle(name="Ordering", set_toggle=1, id=1)
            #db.session.add(t)
            #db.session.commit()
            if form.set_toggle.data == True:
                toggle.set_toggle = 1
                db.session.commit()
                return render_template(url_for("manage_products"), item_matrix=prods, form=form, toggle = toggle)
            elif form.set_toggle.data == False:
                toggle.set_toggle = 0
                db.session.commit()
                return render_template(url_for("manage_products"), item_matrix=prods, form=form, toggle = toggle)
        return render_template(url_for("manage_products"), item_matrix=prods, form=form, toggle = toggle)


@app.route("/customer_orders.html")
@login_required
def customer_orders():
    if current_user.email in admins:
        return render_template(url_for("customer_orders"))


@app.route("/account_info.html")
@login_required
def account_info():
    if current_user.email in admins:
        all_users = User.query.order_by(User.name).all()
        return render_template(url_for("account_info"), all_users=all_users)


@app.route('/register.html', methods=["POST", "GET"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        h_password = secrets.token_hex(12)
        hashed_password = bcrypt.generate_password_hash(h_password).decode('utf-8')
        account_token = get_account_token(form.name.data, hashed_password, form.address.data, form.city.data, form.state.data, form.zipcode.data, form.phone.data, form.email.data)
        new_account_email(form.name.data, form.address.data, form.city.data, form.state.data, form.zipcode.data, form.phone.data, form.email.data, form.route.data, account_token)

        #newUser = User(
        #    name=form.name.data,
        #    password=h_password,
        #    address=form.address.data,
        #    city=form.city.data,
        #    state=form.state.data,
        #    zipcode=form.zipcode.data,
        #    phone=form.phone.data,
        #    email=form.email.data
        #    )
        #db.session.add(newUser)
        #db.session.commit()
        #user = User.query.filter_by(email=form.email.data).first()
        #send_reset_email(user)
        #flash(f"An account request has been submitted for {form.name.data}. Once approved, a email will be sent to you to complete sign up", 'success')
        return redirect(url_for('registration_successful'))

    else:
        return render_template(url_for("register"), title="Register", form=form)


@app.route('/registration_successful.html', methods=["POST", "GET"])
def registration_successful():
    return render_template(url_for("registration_successful"))


@app.route('/create_dummy', methods=["POST", "GET"])
@login_required
def create_dummy():
    if current_user.email in admins:
        form = RegistrationForm()
        if form.validate_on_submit():
            h_password = secrets.token_hex(12)
            hashed_password = bcrypt.generate_password_hash(h_password).decode('utf-8')
            newUser = User(
                name=form.name.data,
                password=hashed_password,
                address=form.address.data,
                city=form.city.data,
                state=form.state.data,
                zipcode=form.zipcode.data,
                phone=form.phone.data,
                email=form.email.data,
                prepaid=form.prepaid.data
                )
            db.session.add(newUser)
            db.session.commit()
            flash(f"An account request has been created for {form.name.data}.", 'success')
            return render_template("create_dummy.html", title="Create Account", form=form)

        else:
            return render_template("create_dummy.html", title="Create Account", form=form)


@app.route('/account.html', methods=["POST", "GET"])
@login_required
def account():
    form = AccountForm()
    if form.validate_on_submit():
        flash("Your account has been updated.", 'success')
        current_user.name = form.name.data
        current_user.address = form.address.data
        current_user.city = form.city.data
        current_user.state = form.state.data
        current_user.zipcode = form.zipcode.data
        current_user.phone = form.phone.data
        current_user.email = form.email.data
        db.session.commit()
        return render_template(url_for('account'), title="Account", form=form)
    elif request.method == "GET":
        form.name.data = current_user.name
        form.address.data = current_user.address
        form.city.data = current_user.city
        form.state.data = current_user.state
        form.zipcode.data = current_user.zipcode
        form.phone.data = current_user.phone
        form.email.data = current_user.email
    return render_template(url_for("account"), title="Account", form=form)


@app.route('/edit_account/<int:user_id>', methods=["POST", "GET"])
@login_required
def edit_account(user_id):
    if current_user.email in admins:
        form = EditAccountForm()
        user = User.query.get_or_404(user_id)
        if form.validate_on_submit():
            if form.dlt.data:
                db.session.delete(user)
                db.session.commit()
                flash('The user has been deleted!', 'success')
                return redirect(url_for('admin'))

            # Translate text boolean to digit
            if form.prepaid.data == True:
                user.prepaid = '1'
            else:
                user.prepaid = '0'

            user.name = form.name.data
            user.address = form.address.data
            user.city = form.city.data
            user.state = form.state.data
            user.zipcode = form.zipcode.data
            user.phone = form.phone.data
            user.email = form.email.data
            db.session.commit()
            flash("Your account has been updated.", 'success')
            return redirect(url_for("admin"))

        elif request.method == "GET":
            form.name.data = user.name
            form.address.data = user.address
            form.city.data = user.city
            form.state.data = user.state
            form.zipcode.data = user.zipcode
            form.phone.data = user.phone
            form.email.data = user.email
        return render_template('edit_account.html', title="Account", form=form, user=user)


def send_receipt_email(user, order, pickup, total, dt, comment):
    msg = Message(f'Foxfire Farm Order Invoice {user.id}{dt}',
                  sender='noreply.pwresets.foxfire@gmail.com',
                  recipients=[user.email])
    msg.body = f'''Thank you for shopping with Foxfire Farm! 
Invoice number: {user.id}{dt}
The following items have been placed in your order: 

{order}

When ready, they can be picked up at:
{pickup}


Your total will be: ${total}
'''
#    msg2 = Message(f'Foxfire Farm New Order Invoice {user.id}{dt}',
#                    sender='noreply.pwresets.foxfire@gmail.com',
#                    recipients=["josh@dinky.pw"])
#    msg2.body = f'''The following items have been ordered by {user.name}:
#Invoice number: {user.id}{dt}
#
#{order}
#
#Delivery location:
#{pickup}
#Comments:
#{comment}
#
#
#Customer total is: {total}
#'''
    path = os.path.join(app.root_path, "orderforms", f"{user.id}{dt}.pdf")
    with app.open_resource(path) as fp:
        msg.attach(f"{user.id}{dt}.pdf", "text/pdf", fp.read())
    mail.send(msg)
#    with app.open_resource(app.root_path, "orderforms", f"{user.id}{dt}.pdf") as fp:
#        msg2.attach(f"{user.id}{dt}.pdf", "text/pdf", fp.read())
#    mail.send(msg2)


@app.route("/ordering/<int:user_id>", methods=["POST", "GET"])
@login_required
def ordering(user_id):
    if current_user.email in admins:  # allow admins to place OOB orders
        pass
    elif current_user.id == user_id:  # Allow users to place order for themselves
        pass
    else:
        flash("Do not do that!", "danger")
        return render_template('home.html')
    prods = Product.query.order_by(Product.veg_name).filter_by(veg_sale=True)
    prods2 = Product.query.order_by(Product.veg_name)
    user = User.query.filter_by(id=user_id).first()
    if user.prepaid == "1":
        user.name = user.name + "(P)"
    toggle = Toggle.query.filter_by(id=1).first()
    fulfilment_address = user.address
    if request.method == "POST":

        #declare variables
        purch = request.form
        dt = datetime.now().strftime('-%y%m%d%H%M%S%f')
        order = f"{user.name},"
        order2 = f"{user.name},"
        items_all = ""
        items = ""

        # mark orders made on behalf of customer with *
        if current_user.id != user_id:
            order = f"*{user.name},"
            order2 = f"*{user.name},"
        cost = 0
        comment = purch["order_comment"]
        comment = comment.replace(",", ";") #make sure customers comments with commas are replaced with semicolons
        locations = {"home": f"{fulfilment_address}",
                     "farm": f"Farm",                          #: 2107 South Fork Ridge Rd; Liberty KY 42539",
                     "boyle": f"Boyle",           #: 105 East Walnut; Danville KY 40422",
                     "danville2": f"NC",         #: 802 South 4th Street; Danville KY 40422",
                     "somerset": f"Nature's Best",             #: 1340 S Highway 27 Ste B; Somerset 42501",
                     "somerset2": f"Selenas"}                  #: 217 HWY 1248; Somerset KY"}
        address   = {"home": f"{fulfilment_address}",
                     "farm": f"Farm: 2107 South Fork Ridge Rd; Liberty KY 42539",
                     "boyle": f"Boyle County Farmers Market",
                     "danville2": f"Nutrition Center: 802 South 4th Street; Danville KY 40422",
                     "somerset": f"Nature's Best: 1340 S Highway 27 Ste B; Somerset 42501",
                     "somerset2": f"Selenas: 217 HWY 1248; Somerset KY"}
        pickup = locations[purch['fulfill_location']]
        pickup_address = address[purch['fulfill_location']]
        #  purch looks like ImmutableMultiDict([('TurnipsHappy', '20'), ('cabbage', '5'), ('fulfill_location', 'farm'), ('order_comment', 'Testing faster submit on orders')])

        # Check items in order and append as needed, calculate cost for each item, and create two strings./
        # Items_All is for the spreadsheet so the columns stay ordered, Item is for the email so customers dont/
        # get a ton of items like "Lettuce: 0" in the email.

        # todo Why cant I just use 'prods'? when would a product that is not for sale be found in an order?
        # todo we might need to go back to prods2. I want to see if this breaks anything. if we do that,
        #    we need to remove the filters in the add, delete, and edit products routes

        for key in prods:
            for i in purch:# add ordered items to list
                if key.veg_name == i and not purch[i] == '' and not i == 'fulfill_location':  # find number of items 'purch[i]' and multiply by price 'key[0]'
                    if purch[i].isdigit():
                        cst = float(purch[i]) * float(key.veg_price)
                        cost += cst
                        items_all += f"{purch[i]}," #add only the number of items, this will be sent to the google sheet
                        items += f"{purch[i]} {i}," #Add the number of items and the name of the item for the customer receipt, and email.
                    else:
                        flash("Only numbers may be used in the order form.", "danger")
                        return redirect(url_for('ordering', item_matrix=prods, user_id=user_id))
                    break  # do not keep comparing after a match is found
            if key.veg_name != i and not i == 'fulfill_location':  # Set existing but unordered items in purchase to zero to maintain columns
                items_all += "0" + ","

        # Charge 20% less for items picked up at the farm, or add a $7 fee for delivery
        if purch["fulfill_location"] == "farm":
            cost = cost * 0.80
            cost = round(cost * 2) / 2
        elif purch["fulfill_location"] == "home":
            # calc_address = user.address + " " + user.city + " " + user.state + " " + user.zipcode
            delivery_charge = 7 #int(get_milage(calc_address, api_key)) * 2
            # if delivery_charge < 5:
            #    delivery_charge = 5
            cost = cost + delivery_charge

        # round float to currency format.
        total = str(f"{cost:.2f}")

        # create a PDF invoice, and send an email to the customer.
        receipt = items.replace(",", "\n")
        createInvoice(user, receipt, pickup_address, total, dt, comment)
        send_receipt_email(user, receipt, pickup_address, total, dt, comment)
        label(user, receipt, pickup, total, dt, comment)

        #build the order
        order += pickup + "," + total + "," + f"{comment}" + "," + f"{items_all}"
        order = order.split(",")

        #order minus empty columns for easy printing.
        order2 += pickup + "," + total + "," + f"{comment}" + "," + f"{items}"
        order2 = order2.split(",")
        # "orders" looks like ['Leaks: 25', 'Pickles: 100', 'Customer total is 248.75']
        # Make API call to the google sheet to post the new order.
        wks_label.append_row(order2)
        wks_order.append_row(order)

        # Flash cost totals
        if current_user.email in admins:
            flash(
                f"{user.name}'s total will be ${total}",
                "info")
            return redirect(url_for('account_info'))
        else:
            flash(
                f"Thanks for shopping with us. You will receive an email with your invoice shortly. Your total will be ${total}. We will see you soon!",
                "info")
            return redirect(url_for("home"))

    elif toggle.set_toggle == 1:
        return render_template("ordering.html", item_matrix=prods, admins=admins, user=user)
    else:
        return render_template("ordering.html", item_matrix=[], admins=admins, user=user)


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    if current_user.email in admins:
        form = PostForm()
        posts = Post.query.all()
        if form.validate_on_submit():
            post = Post(title=form.title.data, content=form.content.data, visible=form.visible.data)
            db.session.add(post)
            db.session.commit()
            flash('Your post has been created!', 'success')
            return redirect(url_for('new_post'))
        return render_template('create_post.html', title='New Post',form=form, legend='New Post', posts=posts)


@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    if current_user.email in admins:
        post = Post.query.get_or_404(post_id)
        form = PostForm()
        if form.validate_on_submit():
            if form.dlt.data == True:
                delete_post(post_id)
                return redirect(url_for('new_post', post_id=post.id))
            post.title = form.title.data
            post.content = form.content.data
            post.visible = form.visible.data
            db.session.commit()
            flash('Your post has been updated!', 'success')
            return redirect(url_for('new_post', post_id=post.id))
        elif request.method == 'GET':
            form.title.data = post.title
            form.content.data = post.content
        return render_template('edit_post.html', title='Update Post', form=form, legend='Update Post', post=post)


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    if current_user.email in admins:
        post = Post.query.get_or_404(post_id)
        db.session.delete(post)
        db.session.commit()
        flash('Your post has been deleted!', 'success')
        return redirect(url_for('admin'))

@app.route("/product/<int:veg_id>/delete", methods=['POST'])
@login_required
def delete_veg(veg_id):
    if current_user.email in admins:
        veg = Product.query.get_or_404(veg_id)
        upload_deleter(veg.veg_image)
        db.session.delete(veg)
        db.session.commit()

        # If product was listed for sale, update order form with new products so columns are not messed up
        if veg.veg_sale == "1":
            query = Product.query.order_by(Product.veg_name).filter_by(veg_sale=True)
            lis = list(query)
            prods = ["Name", "Location", "Total", "Comments"]
            for item in lis:
                prods.append(item.veg_name)
            wks_order.append_row(prods)

        flash('Your product has been deleted!', 'success')
        return redirect(url_for('admin'))

def sav_thumbnail(pic_in):
    random_hex = secrets.token_hex(4)
    _, f_ext = os.path.splitext(pic_in.filename)
    pic_name = random_hex + f_ext
    pic_path = os.path.join(app.root_path, "static/uploads", pic_name)
    pic_out = (200, 200)
    pic = Image.open(pic_in)
    pic = ImageOps.exif_transpose(pic)
    pic.thumbnail(pic_out)
    pic.save(pic_path)
    return pic_name

def sav_pic_thumbnail(pic_in):
    random_hex = secrets.token_hex(4)
    _, f_ext = os.path.splitext(pic_in.filename)
    pic_name = random_hex + f_ext
    pic_path = os.path.join(app.root_path, "static/photos", pic_name)
    pic_out = (200, 200)
    pic = Image.open(pic_in)
    pic.thumbnail(pic_out)
    pic.save(pic_path)
    return pic_name

def sav_picture(pic_in):
    random_hex = secrets.token_hex(4)
    _, f_ext = os.path.splitext(pic_in.filename)
    pic_name = random_hex + f_ext
    pic_path = os.path.join(app.root_path, "static/photos", pic_name)
    pic = Image.open(pic_in)
    pic.save(pic_path)
    return pic_name


def upload_deleter(veg_image):
    try:
        rem = os.path.join(app.root_path, "static/uploads", veg_image)
        os.remove(rem)
    except:
        pass

def deleter(picture, thumbnail):
    rem = os.path.join(app.root_path, "static/photos", thumbnail)
    os.remove(rem)
    rem = os.path.join(app.root_path, "static/photos", picture)
    os.remove(rem)


@app.route('/login.html', methods=["POST", "GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            if current_user.email in admins:
                return redirect(url_for("admin"))
            return redirect(url_for("home"))
        else:
            flash(f"Your email or password are incorrect", 'danger')
            return render_template(url_for("login"), title="Login", form=form)
    else:
        return render_template(url_for("login"), title="Login", form=form)


@app.route('/logout', methods=["POST", "GET"])
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/products.html")
def products():
    prods = Product.query.order_by(Product.veg_name).all()
    return render_template(url_for("products"), item_matrix=prods)


@app.route("/thanks.html")
def thanks():
    return render_template(url_for("thanks"))


@app.route("/about.html")
def about():
    return render_template("about.html")


@app.route("/partners.html")
def partners():
    return render_template("partners.html")


@app.route("/organic.html")
def organic():
    return render_template("organic.html")


@app.route("/photo.html")
def photo():
    pics = Picture.query.all()
    return render_template("photo.html", pics=pics)


@app.route("/contact.html")
def contact():
    return render_template("contact.html")


@app.route("/wheretofind.html")
def wheretofind():
    return render_template("wheretofind.html")


@app.route("/")
@app.route("/home.html")
def home():
    posts = Post.query.order_by(Post.id.desc()).filter_by(visible=True)
    return render_template("home.html", posts=posts)

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Account Password Update',
                  sender='noreply.pwresets.foxfire@gmail.com',
                  recipients=[user.email])
    msg.body = f'''To update your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)

def customer_account_email(user):
    token = user.get_reset_token()
    msg = Message('Your account was approved!',
                  sender='noreply.pwresets.foxfire@gmail.com',
                  recipients=[user.email])
    msg.body = f'''To claim your account, visit the following link and set your password:
    
{url_for('reset_token', token=token, _external=True)}

your username is: {user.email}

Once you have finished signup, and logged into your account, you can begin purchasing by going to the "Order" tab on the home page. 
'''
    mail.send(msg)

def new_account_email(name, address, city, state, zipcode, phone, email, route, account_token):

    msg = Message('New Account Request',
                  sender='noreply.pwresets.foxfire@gmail.com',
                  recipients=['josh@dinky.pw'])
    msg.body = f'''An account has been requested by:
{name}
{phone}
{address}
{city}, {state}, {zipcode}
{email}

They learned about us via : {route}




To approve this account request, visit the following link:
{url_for('new_account', token=account_token, _external=True)}
If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with password reset instructions.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        flash('You are still logged in. Please log out and try again if you are trying to reset your password.', 'success')
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


@app.route("/new_account/<token>", methods=['GET', 'POST'])
def new_account(token):
    new_user = approve_account_token(token)
    user = User(
        name=new_user['name'],
        password=new_user['password'],
        address=new_user['address'],
        city=new_user['city'],
        state=new_user['state'],
        zipcode=new_user['zipcode'],
        phone=new_user['phone'],
        email=new_user['email']
    )
    if User.query.filter_by(email=new_user['email']).first():
        flash(f"An account for {new_user['name']} already exists!", 'danger')
        return redirect(url_for("login"))
    else:
        db.session.add(user)
        db.session.commit()
        user = User.query.filter_by(email=new_user['email']).first()
        customer_account_email(user)
        new_customer = [ user.id, user.name, user.address, user.city,  user.state, user.zipcode, user.phone, user.email]
        wks_customer_details.append_row(new_customer)
        flash(f"A new account has been created for {new_user['name']}!", "success")
    return redirect(url_for("login"))