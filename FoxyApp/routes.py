from flask import render_template, redirect, request, url_for, flash, send_file, jsonify, Response
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from FoxyApp import app, bcrypt, db, mail, admins
from FoxyApp.forms import RegistrationForm, LoginForm, AccountForm, EditAccountForm, NewProductForm, RequestResetForm, \
    ResetPasswordForm, PostForm, NewPictureForm, ToggleForm, LocationForm
from FoxyApp.models import User, Product, Post, Picture, Toggle, Location, Order, OrderItem
from FoxyApp.foxfirepdf import createInvoice, driver_sheet
from FoxyApp.foxfiretok import get_account_token, approve_account_token
from FoxyApp.label import label
from FoxyApp.foxfireutility import friday as get_this_friday
import secrets
import os
import logging
from PIL import Image, ImageOps
from datetime import datetime, timedelta, time
from sqlalchemy import func
import csv
from io import StringIO


#   Migrate orders to DB
#   1. Orders page: need to have a order name, user, cost, items, box size, address, date, prepaid, comments.
#   2. Orders page: Dropdown with orders by week-of, weeks orders are returned by name as a clickable link.
#   3. Orders page: For given week, number of orders, total income, number of boxes, number of each item, number of home deliveries.
#   4. Orders page: Table with all order fields, allows side-scrolling, all items in order in same cell with newline (ordered by weight), make printable.

#  todo add balance to users (double orders, confirm order, shopping cart).
#   1. auto deduct.
#   2. show customer their balance as they shop + debit if balance exceeded.
#   3. show admins outstanding prepaid total.
########################################################################################################################

#  todo make items available for admins, whether customers can place orders or not. This cannot affect the google sheet.
#  todo make number of items on the label more visible
# add item volume to items, calculate volume of box needed

@app.route('/health')
def health_check():
    return "OK", 200


@app.route("/admin", methods=["POST", "GET"])
@login_required
def admin():
    if current_user.email in admins:
        return redirect(url_for("admin_orders"))
    else:
        flash("You are not authorized.", "danger")
        return redirect(url_for("home"))


@app.route('/admin/orders', methods=['GET'])
@login_required
def admin_orders():
    if current_user.email not in admins:
        return redirect(url_for('home'))

    selected_week = request.args.get('week', default=None)
    # Find most recent Friday (weekday 4 = Friday)
    this_friday_str = get_this_friday()
    current_friday = datetime.strptime(this_friday_str, "%d-%b-%Y")

    weeks = []
    for i in range(12):
        friday_date = current_friday - timedelta(weeks=i)
        label = friday_date.strftime('%d %b %Y')
        weeks.append({
            'start': friday_date.strftime('%Y-%m-%d'),
            'label': f"Week ending {label}"
        })

    # Query orders
    query = db.session.query(Order, User).join(User, Order.user_id == User.id)

    if selected_week:
        # Parse selected Friday
        selected_friday = datetime.strptime(selected_week, '%Y-%m-%d')
        week_start = datetime.combine(selected_friday - timedelta(days=6), time.min)  # Saturday before
        week_end = datetime.combine(selected_friday, time.max)  # Inclusive of Friday
        query = query.filter(Order.order_date.between(week_start, week_end))

    orders = query.order_by(Order.order_date.desc()).all()

    # Cache locations for pickup checks
    valid_locations = [loc.short_name for loc in Location.query.all()]

    # Aggregate data
    order_data = []
    total_income = 0
    total_large_boxes = 0
    total_small_boxes = 0
    item_counts = {}
    home_deliveries = 0

    for order, user in orders:
        items = db.session.query(OrderItem, Product)\
            .join(Product, OrderItem.product_id == Product.id)\
            .filter(OrderItem.order_id == order.id)\
            .order_by(Product.veg_weight.desc())\
            .all()

        items_str = "\n".join([
            f"{item.OrderItem.quantity} x {item.Product.veg_name}"
            for item in items
        ])

        box_size = sum(item.OrderItem.quantity * item.Product.veg_vol for item in items)
        large_boxes = int(box_size)
        decimal_part = box_size - large_boxes
        small_boxes = 1 if 0 < decimal_part < 0.5 else 0
        if decimal_part >= 0.5:
            large_boxes += 1

        total_large_boxes += large_boxes
        total_small_boxes += small_boxes
        total_income += order.total_cost

        for item in items:
            item_name = item.Product.veg_name
            item_counts[item_name] = item_counts.get(item_name, 0) + item.OrderItem.quantity

        if order.pickup_location not in valid_locations:
            home_deliveries += 1

        order_data.append({
            'order_id': order.id,
            'user_name': user.name,
            'user_id': user.id,
            'cost': round(order.total_cost, 2),
            'items': items_str,
            'large_boxes': large_boxes,
            'small_boxes': small_boxes,
            'address': order.pickup_location,
            'date': order.order_date.strftime('%Y-%m-%d %H:%M'),
            'prepaid': user.prepaid == '1',
            'comments': order.comment or '',
            'invoice' : order.invoice
        })

    stats = {
        'num_orders': len(order_data),
        'total_income': round(total_income, 2),
        'total_large_boxes': total_large_boxes,
        'total_small_boxes': total_small_boxes,
        'item_counts': item_counts,
        'home_deliveries': home_deliveries
    }

    return render_template(
        'customer_orders.html',
        orders=order_data,
        weeks=weeks,
        selected_week=selected_week,
        stats=stats,
    )


@app.route('/admin/income-by-week')
@login_required
def income_by_week():
    if current_user.email not in admins:
        return redirect(url_for('home'))

    today = datetime.utcnow()
    current_monday = today - timedelta(days=today.weekday())
    data = []

    for i in range(12):
        week_start = current_monday - timedelta(weeks=i)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        total = db.session.query(func.sum(Order.total_cost)).filter(
            Order.order_date.between(week_start, week_end)
        ).scalar() or 0

        label = f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b')}"
        data.append((label, round(total, 2)))

    # Reverse to show oldest first
    data.reverse()

    return jsonify({
        'labels': [label for label, _ in data],
        'values': [value for _, value in data]
    })


@app.route("/static/labels/<label>/delete", methods=["POST", "GET"])
@login_required
def labels(label):
    if current_user.email in admins:
        rem = os.path.join(app.root_path, "static/labels", label)
        return redirect(url_for('admin')), os.remove(rem)
    else:
        flash("You are not authorized.", "danger")

@app.route("/driver_form_week", methods=["GET"])
@login_required
def driver_form_week():
    if current_user.email not in admins:
        flash("You are not authorized.", "danger")
        return redirect(url_for("home"))

    # Get the selected week from the query parameter
    selected_week = request.args.get('week', default=None)
    if not selected_week:
        flash("Please select a week to generate the driver sheet.", "warning")
        return redirect(url_for("admin_orders"))

    # selected_week is the Friday of the week
    week_end = datetime.strptime(selected_week, '%Y-%m-%d')
    week_start = datetime.combine(week_end - timedelta(days=6), time.min)
    orders_query = db.session.query(Order, User).join(User, Order.user_id == User.id).filter(
        Order.order_date.between(week_start, week_end)
    ).all()

    if not orders_query:
        flash("No orders found for the selected week.", "warning")
        return redirect(url_for("admin_orders"))

    # Format the orders into the structure expected by driver_sheet
    orders = [["Name", "Location", "Total", "Comments"]]  # Header row
    for order, user in orders_query:
        order_row = [
            user.name,
            order.pickup_location,
            f"${order.total_cost:.2f}",
            order.comment or ""
        ]
        orders.append(order_row)

    # Generate the PDF using driver_sheet
    filename = driver_sheet(orders, week=selected_week)
    return redirect(url_for('static', filename=filename))

@app.route("/orderform/<pdf>", methods=["POST", "GET"])
@login_required
def orderform(pdf):
    if current_user.email in admins:
        path = f"orderforms/{pdf}"
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
                veggie = Product(veg_image=picture,
                                 veg_name=form.veg_name.data,
                                 veg_price=form.veg_price.data,
                                 veg_url=form.veg_url.data,
                                 veg_weight=form.veg_weight.data,
                                 veg_vol=form.veg_vol.data,
                                 veg_sale=form.veg_sale.data)
            else:
                veggie = Product(veg_image=form.veg_image.data,
                                 veg_name=form.veg_name.data,
                                 veg_price=form.veg_price.data,
                                 veg_url=form.veg_url.data,
                                 veg_weight=form.veg_weight.data,
                                 veg_vol=form.veg_vol.data,
                                 veg_sale=form.veg_sale.data)
            db.session.add(veggie)
            db.session.commit()

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
            prods.archive=form.veg_dlt.data
            prods.veg_name = form.veg_name.data
            prods.veg_price = form.veg_price.data
            prods.veg_url = form.veg_url.data
            prods.veg_weight = form.veg_weight.data
            prods.veg_vol = form.veg_vol.data
            prods.veg_sale = form.veg_sale.data
            if form.veg_image.data and not None:
                picture = sav_thumbnail(form.veg_image.data)
                prods.veg_image = picture

            prods = Product.query.get_or_404(veg_id)
            db.session.commit()
            flash("The Item has been updated!", "success")
            return render_template("edit_product.html", form=form, item_matrix=prods)
        elif request.method == "GET":
            form.veg_name.data = prods.veg_name
            form.veg_price.data = prods.veg_price
            form.veg_url.data = prods.veg_url
            form.veg_weight.data = prods.veg_weight
            form.veg_vol.data = prods.veg_vol
            form.veg_image.data = prods.veg_image
            form.veg_dlt.data = prods.archive
            form.veg_sale.data = prods.veg_sale
        return render_template("edit_product.html", form=form, item_matrix=prods)


@app.route("/manage_products.html", methods=["POST", "GET"])
@login_required
def manage_products():
    if current_user.email in admins:
        form = ToggleForm()
        toggle = Toggle.query.filter_by(id=1).first()
        prods = Product.query.filter_by(archive=False).order_by(Product.veg_name)
        if form.validate_on_submit():
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
            return redirect(url_for("account_info"))

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
            return redirect(url_for("account_info", _anchor=f"user-{user.id}"))

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



LOG_FILE=os.path.join(app.root_path, "customer_order_log.txt")
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()  # Log to console as well
    ])
logger = logging.getLogger(__name__)


@app.route("/ordering/<int:user_id>", methods=["POST", "GET"])
@login_required
def ordering(user_id):
    logger.warning(f"{app.root_path}: Accessing ordering page for user_id: {user_id}, current_user: {current_user.id}")
    if current_user.email in admins:  # Allow admins to place OOB orders
        logger.warning(f"{app.root_path}: Admin user is placing an order.")
    elif current_user.id == user_id:  # Allow users to place order for themselves
        logger.warning(f"{app.root_path}: User is placing an order for themselves.")
    else:
        logger.warning(f"{app.root_path}: Unauthorized order attempt by user {current_user.id} for user_id: {user_id}")
        flash("Do not do that!", "danger")
        return render_template('home.html')

    prods = Product.query.order_by(Product.veg_name).filter(Product.veg_sale==True, Product.archive==False).all()
    prods2 = Product.query.order_by(Product.veg_weight).filter(Product.veg_sale==True, Product.archive==False).all()
    location = Location.query.filter_by(active=True).all()
    user = User.query.filter_by(id=user_id).first()

    if user.prepaid == "1":
        user.name = user.name + "(P)"
    toggle = Toggle.query.filter_by(id=1).first()

    try:
        if request.method == "POST":
            logger.warning(f"{app.root_path}: Processing order for user: {user.name}")
            purch = request.form
            dt = datetime.now().strftime('-%y%m%d%H%M%S%f')
            cost = 0.0
            volume = 0.0
            # Sanitize the comment: replace problematic characters and escape others
            raw_comment = purch.get("order_comment", "")
            # Replace problematic characters or escape them
            comment = (
                raw_comment
                .replace(",", ";")  # Replace commas with semicolons
                .replace("\n", " ")  # Replace newlines with spaces
                .replace("\r", " ")  # Replace carriage returns with spaces
                .replace('"', '\\"')  # Escape double quotes
                .replace("'", "\\'")  # Escape single quotes
                .strip()  # Remove leading/trailing whitespace
            )
            pickup = None
            pickup_address = None

            # Determine pickup location and adjust cost
            if purch["fulfill_location"] == user.address:
                pickup = user.address
                pickup_address = user.address
                cost += 7.0
            else:
                loc = Location.query.filter_by(id=int(purch["fulfill_location"])).first()
                pickup = loc.short_name
                pickup_address = loc.long_name
            logger.warning(f"{app.root_path}: Pickup location determined: {pickup_address}")

            # Create the order
            order = Order(
                user_id=user_id,
                pickup_location=pickup,
                total_cost=0.0,  # Will update later
                comment=comment,
                volume=volume,
                invoice = f"{user.id}{dt}"
            )
            db.session.add(order)
            db.session.flush()  # Get order.id without committing yet

            # Process ordered items
            items = []
            items_all = []
            for product in prods:
                if product.veg_name in purch and purch[product.veg_name] and purch[product.veg_name].isdigit():
                    qty = int(purch[product.veg_name])
                    if qty > 0:
                        price = float(product.veg_price)
                        item_cost = qty * price
                        item_volume = qty * float(product.veg_vol)
                        cost += item_cost
                        volume += item_volume

                        # Create OrderItem
                        order_item = OrderItem(
                            order_id=order.id,
                            product_id=product.id,
                            quantity=qty,
                            price_at_time=price
                        )
                        db.session.add(order_item)
                        items.append(f"{qty} {product.veg_name}")
                        items_all.append(str(qty))
                    else:
                        items_all.append("0")
                else:
                    items_all.append("0")

            #  record volume
            volume = f"{round(volume * 10) / 10}"
            order.volume = volume
            # Adjust cost for farm pickup
            if pickup in ["FARM", "farm"]:
                cost *= 0.80
            cost = round(cost * 2) / 2
            order.total_cost = cost
            db.session.commit()  # Commit the order and items

            total = f"{cost:.2f}"
            logger.warning(f"{app.root_path}: Order total calculated: {total}")

            # Generate receipt and PDF
            receipt = "\n".join(items)
            try:
                logger.warning(f"{app.root_path}: Creating invoice for user.")
                createInvoice(user, receipt, pickup_address, total, dt, comment)
                logger.warning(f"{app.root_path}: Invoice created successfully.")
            except Exception as e:
                logger.error(f"{app.root_path}: Failed to create invoice: {e}", exc_info=True)

            try:
                logger.warning(f"{app.root_path}: Sending receipt email to user.")
                send_receipt_email(user, receipt, pickup_address, total, dt, comment)
                logger.warning(f"{app.root_path}: Email sent successfully.")
            except Exception as e:
                logger.error(f"{app.root_path}: Failed to send email: {e}", exc_info=True)

            # Generate sorted receipt for label
            items_list = [(item.product.veg_name, item.quantity) for item in order.items]
            items_sorted = sorted(items_list, key=lambda x: next(
                (p.veg_weight for p in prods2 if p.veg_name == x[0]), 0))
            sorted_receipt = "\n".join([f"{qty} {name}" for name, qty in items_sorted])

            try:
                logger.warning(f"{app.root_path}: Generating label for user.")
                label(user, sorted_receipt, pickup, total, dt, comment, volume)
                logger.warning(f"{app.root_path}: Label generated successfully.")
            except Exception as e:
                logger.error(f"{app.root_path}: Failed to generate label: {e}", exc_info=True)

            ## Optionally keep Google Sheets sync (remove if not needed)
            #order_row = [user.name, pickup, total, comment] + items_all
            #order_row2 = [user.name, pickup, total, comment] + items
            #try:
            #    wks_label.append_row(order_row2)
            #    wks_order.append_row(order_row)
            #except Exception as e:
            #    logger.error(f"{app.root_path}: Failed to send order to Google Sheet: {e}", exc_info=True)

            # Flash success message
            if current_user.email in admins:
                flash(f"{user.name}'s total will be ${total}", "info")
                return redirect(url_for('account_info'))
            else:
                flash(f"Thanks for shopping with us. Your total will be ${total}.", "info")
                return redirect(url_for("home"))

        elif toggle.set_toggle == 1:
            return render_template("ordering.html", item_matrix=prods, location=location, admins=admins, user=user)
        else:
            return render_template("ordering.html", item_matrix=[], location=location, admins=admins, user=user)

    except Exception as e:
        db.session.rollback()
        logger.error(f"{app.root_path}: Error processing order: {e}", exc_info=True)
        flash("An error occurred while processing your order.", "danger")
        return redirect(url_for("home"))


@app.route("/location", methods=['GET', 'POST'])
@login_required
def location():
    if current_user.email in admins:
        form = LocationForm()
        location = Location.query.all()
        if form.validate_on_submit():
            loc = Location(short_name=form.short_name.data, long_name=form.long_name.data, description=form.description.data, active=form.active.data)
            db.session.add(loc)
            db.session.commit()
            flash('Your location has been created!', 'success')
            return redirect(url_for("location"))
        return render_template('location.html', title='Locations', form=form, legend='Locations', location=location)


@app.route("/edit_location/<int:id>", methods=['GET', 'POST'])
@login_required
def edit_location(id):
    if current_user.email in admins:
        form = LocationForm()
        location = Location.query.filter_by(id=id).first()
        if form.validate_on_submit():
            location.short_name = form.short_name.data
            location.long_name = form.long_name.data
            location.description = form.description.data
            location.active = form.active.data
            db.session.commit()
            flash('Your location has been updated!', 'success')
            return redirect(url_for("location"))
        elif request.method == 'GET':
            form.short_name.data = location.short_name
            form.long_name.data = location.long_name
            form.description.data = location.description
            form.active.data = location.active
        return render_template('edit_location.html', title='Edit Location',form=form, legend='Edit Location', location=location)



@app.route("/location/<int:id>/delete", methods=['GET', 'POST'])
@login_required
def delete_location(id):
    if current_user.email in admins:
        location = Location.query.filter_by(id=id).first()
        db.session.delete(location)
        db.session.commit()
        return redirect(url_for("location"))


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
    prods = Product.query.filter_by(archive=False).order_by(Product.veg_name).all()
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
        flash(f"A new account has been created for {new_user['name']}!", "success")
    return redirect(url_for("login"))


@app.route('/admin/orders/export')
@login_required
def export_orders():
    if current_user.email not in admins:
        return redirect(url_for('home'))

    selected_week = request.args.get('week', default=None)

    query = db.session.query(Order, User).join(User, Order.user_id == User.id)
    if selected_week:
        week_start = datetime.strptime(selected_week, '%Y-%m-%d')
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        query = query.filter(Order.order_date.between(week_start, week_end))

    orders = query.order_by(Order.order_date.desc()).all()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow([
        'Order ID', 'User Name', 'Cost', 'Items',
        'Large Boxes', 'Small Boxes', 'Address',
        'Date', 'Prepaid', 'Comments'
    ])

    for order, user in orders:
        items = db.session.query(OrderItem, Product)\
            .join(Product, OrderItem.product_id == Product.id)\
            .filter(OrderItem.order_id == order.id)\
            .all()

        items_str = ", ".join([
            f"{item.OrderItem.quantity} x {item.Product.veg_name}"
            for item in items
        ])

        box_size = sum(item.OrderItem.quantity * item.Product.veg_vol for item in items)
        large_boxes = int(box_size)
        small_boxes = 1 if 0 < (box_size - large_boxes) < 0.5 else 0
        if (box_size - large_boxes) >= 0.5:
            large_boxes += 1
            small_boxes = 0

        cw.writerow([
            order.id,
            user.name,
            round(order.total_cost, 2),
            items_str,
            large_boxes,
            small_boxes,
            order.pickup_location,
            order.order_date.strftime('%Y-%m-%d %H:%M'),
            'Yes' if user.prepaid == '1' else 'No',
            order.comment or ''
        ])

    output = si.getvalue()
    # Create filename based on week
    if selected_week:
        filename = f"orders_{selected_week}.csv"
    else:
        filename = f"orders_all_{datetime.utcnow().strftime('%Y-%m-%d')}.csv"

    return Response(
        output,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

