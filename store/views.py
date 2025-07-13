import django
import requests
from django.contrib.auth.models import User
from store.models import Address, Cart, Category, Order, Product, OrderItem, WishList, Review
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import RegistrationForm, AddressForm
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.views import View
from decimal import Decimal
from .models import ContactMessage
from math import radians, cos, sin, asin, sqrt
from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator # for Class Based Views


# Create your views here.


def geocode_address(address):
    """
    Takes a full address string and returns (latitude, longitude) using the OpenCage API.
    Returns (None, None) if geocoding fails.
    """
    api_key = 'b9767c785f6f484d89cf8b3d61c82e99'  # Replace with your actual API key
    url = 'https://api.opencagedata.com/geocode/v1/json'

    params = {
        'q': address,
        'key': api_key,
        'language': 'en',
        'pretty': 1
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data['results']:
            lat = data['results'][0]['geometry']['lat']
            lon = data['results'][0]['geometry']['lng']
            return lat, lon
    except Exception as e:
        print(f"Geocoding failed: {e}")

    return None, None


def home(request):

    # Initialize wish_list_product_ids before using it in the context
    wish_list_product_ids = set()
    if request.user.is_authenticated:
        wish_list_product_ids = set(
            WishList.objects.filter(user=request.user).values_list('product_id', flat=True)
        )
    # Fetch the categories and products
    categories = Category.objects.filter(is_active=True, is_featured=True)[:3]
    products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    context = {
        'categories': categories,
        'products': products,
         'wish_list_product_ids': wish_list_product_ids,
    }

    
    return render(request, 'store/index.html', context)

def detail(request, slug):
    wish_list_product_ids = set()
    if request.user.is_authenticated:
        wish_list_product_ids = set(
            WishList.objects.filter(user=request.user).values_list('product_id', flat=True)
        )

    product = get_object_or_404(Product, slug=slug)
    related_products = Product.objects.exclude(id=product.id).filter(is_active=True, category=product.category)

   # Handle review submission
    if request.method == 'POST' and request.user.is_authenticated:
    # Check if the user already reviewed this product
        if Review.objects.filter(user=request.user, product=product).exists():
            messages.error(request, "You have already submitted a review for this product.")
        else:
            content = request.POST.get('content')
            rating = float(request.POST.get('rating', 0))
            Review.objects.create(user=request.user, product=product, content=content, rating=rating)
            messages.success(request, "Your review has been submitted.")

    # Fetch product reviews
    reviews = Review.objects.filter(product=product).order_by('-date_posted')
    has_reviewed = False
    if request.user.is_authenticated:
        has_reviewed = Review.objects.filter(user=request.user, product=product).exists()

    context = {
        'product': product,
        'related_products': related_products,
        'wish_list_product_ids': wish_list_product_ids,
        'reviews': reviews,
        'has_reviewed': has_reviewed,
    }

    return render(request, 'store/detail.html', context)

def get_shipping_cost(request):
    if request.method == "POST":
        city = request.POST.get("city", "").strip()
        user = request.user

        # Default fallback if user doesn't exist
        if not city:
            return JsonResponse({"error": "City required"}, status=400)

        # You can enhance this with geocoding API to get coordinates from the city
        # For simplicity, use a mock city-to-distance mapping:
        city_distances = {
            "Nairobi": 3,
            "Kiambu": 8,
            "Thika": 14,
            "Mombasa": 500,
        }

        distance_km = city_distances.get(city, 500)  # fallback to 500km

        if distance_km <= 5:
            shipping = 100
        elif distance_km <= 15:
            shipping = 200
        else:
            shipping = 3000

        return JsonResponse({"shipping": shipping})

    return JsonResponse({"error": "Invalid request"}, status=400)



def haversine(lat1, lon1, lat2, lon2):
    # Radius of Earth in kilometers
    R = 6371.0

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    return R * c  # returns distance in km




def all_categories(request):
    categories = Category.objects.filter(is_active=True)
    return render(request, 'store/categories.html', {'categories':categories})


def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(is_active=True, category=category)
    categories = Category.objects.filter(is_active=True)
    context = {
        'category': category,
        'products': products,
        'categories': categories,
    }
    return render(request, 'store/category_products.html', context)


# Authentication Starts Here

class RegistrationView(View):
    def get(self, request):
        form = RegistrationForm()
        return render(request, 'account/register.html', {'form': form})
    
    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            messages.success(request, "Congratulations! Registration Successful!")
            form.save()
            return redirect('store:login') # Redirect to login page after successful registration
        return render(request, 'account/register.html', {'form': form})
        

@login_required
def profile(request):
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user)
    return render(request, 'account/profile.html', {'addresses':addresses, 'orders':orders})


@method_decorator(login_required, name='dispatch')
class AddressView(View):
    def get(self, request):
        address = Address.objects.filter(user=request.user).first()
        form = AddressForm(instance=address)
        return render(request, 'account/edit_address.html', {'form': form})

    def post(self, request):
        address = Address.objects.filter(user=request.user).first()
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, "Address updated successfully.")
            return redirect('store:profile')
        return render(request, 'account/edit_address.html', {'form': form})



@login_required
def remove_address(request, id):
    a = get_object_or_404(Address, user=request.user, id=id)
    a.delete()
    messages.success(request, "Address removed.")
    return redirect('store:profile')

@login_required
def add_to_cart(request):
    if request.method == 'POST':
        user = request.user
        product_id = request.POST.get('prod_id')  # <-- changed from GET to POST
        product = get_object_or_404(Product, id=product_id)

        item_already_in_cart = Cart.objects.filter(product=product, user=user).first()
        if item_already_in_cart:
            item_already_in_cart.quantity += 1
            item_already_in_cart.save()
        else:
            Cart.objects.create(user=user, product=product)

        return redirect('store:cart')
    else:
        return HttpResponseBadRequest("Invalid request method.")





@login_required
def cart(request):
    user = request.user
    cart_products = Cart.objects.filter(user=user)

    amount = Decimal(0)
    for item in cart_products:
        amount += item.quantity * item.product.price

    # Store's fixed coordinates (e.g., Nairobi CBD)
    store_lat = 1.2921
    store_lon = 36.8219

    address = Address.objects.filter(user=user).first()
    if address and address.latitude and address.longitude:
        distance_km = haversine(store_lat, store_lon, address.latitude, address.longitude)
    else:
        distance_km = 0

    # Simple shipping logic
    if distance_km <= 5:
        shipping_amount = Decimal(100)
    elif distance_km <= 15:
        shipping_amount = Decimal(200)
    else:
        shipping_amount = Decimal(3000)

    total_price = amount + shipping_amount

    context = {
        'cart_products': cart_products,
        'amount': amount,
        'shipping_amount': shipping_amount,
        'total_price': total_price,
        'addresses': Address.objects.filter(user=user),
    }
    return render(request, 'store/cart.html', context)



@login_required
def remove_cart(request, cart_id):
    if request.method == 'GET':
        c = get_object_or_404(Cart, id=cart_id)
        c.delete()
        messages.success(request, "Product removed from Cart.")
    return redirect('store:cart')


@login_required
def plus_cart(request, cart_id):
    if request.method == 'GET':
        cp = get_object_or_404(Cart, id=cart_id)
        cp.quantity += 1
        cp.save()
    return redirect('store:cart')


@login_required
def minus_cart(request, cart_id):
    if request.method == 'GET':
        cp = get_object_or_404(Cart, id=cart_id)
        # Remove the Product if the quantity is already 1
        if cp.quantity == 1:
            cp.delete()
        else:
            cp.quantity -= 1
            cp.save()
    return redirect('store:cart')



def go_to_checkout(request):
    user = request.user
    if Address.objects.filter(user=user).exists():
        return redirect('store:checkout')
    else:
        return redirect('store:checkout')  # Or to a different first-time form


@login_required
@transaction.atomic
def checkout(request):
    user = request.user
    cart_items = Cart.objects.filter(user=user)

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('store:cart')

    cart_total = sum(item.product.price * item.quantity for item in cart_items)

    store_lat = 1.2921
    store_lon = 36.8219

    # Try to get saved address
    try:
        address = Address.objects.get(user=user)
    except Address.DoesNotExist:
        address = None

    # Calculate shipping based on distance
    shipping_amount = Decimal(3000)  # default
    if address and address.latitude is not None and address.longitude is not None:
        distance_km = haversine(store_lat, store_lon, address.latitude, address.longitude)
        if distance_km <= 5:
            shipping_amount = Decimal(100)
        elif distance_km <= 15:
            shipping_amount = Decimal(200)

    total_price = cart_total + shipping_amount

    # 🟩 GET with existing address: place order directly
    if request.method == 'GET' and address:
        order = Order.objects.create(
            user=user,
            first_name=address.first_name,
            last_name=address.last_name,
            email=address.email,
            phone=address.phone,
            address=address.address1,
            addressalt=address.address2,
            company=address.company,
            city=address.city,
            state=address.state,
            total_price=total_price
        )

        for item in cart_items:
            if item.product.stock < item.quantity:
                messages.error(request, f"Not enough stock for {item.product.title}.")
                return redirect('store:cart')

            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

            item.product.stock -= item.quantity
            item.product.save()

        cart_items.delete()
        messages.success(request, "Order placed successfully using your saved address!")
        return redirect('store:orders')

    # 🟨 POST: Save address, then place order
    if request.method == 'POST':
        required_fields = ['first_name', 'last_name', 'email', 'phone', 'address1', 'city', 'state']
        for field in required_fields:
            if not request.POST.get(field):
                messages.error(request, f"{field.replace('_', ' ').capitalize()} is required.")
                return redirect('store:checkout')

        full_address = f"{request.POST.get('address1')}, {request.POST.get('city')}, {request.POST.get('state')}"
        lat, lon = geocode_address(full_address)

        address = Address.objects.create(
            user=user,
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            address1=request.POST.get('address1'),
            address2=request.POST.get('address2', ''),
            city=request.POST.get('city'),
            state=request.POST.get('state'),
            company=request.POST.get('company', ''),
            latitude=lat,
            longitude=lon
        )

        order = Order.objects.create(
            user=user,
            first_name=address.first_name,
            last_name=address.last_name,
            email=address.email,
            phone=address.phone,
            address=address.address1,
            addressalt=address.address2,
            company=address.company,
            city=address.city,
            state=address.state,
            total_price=total_price
        )

        for item in cart_items:
            if item.product.stock < item.quantity:
                messages.error(request, f"Not enough stock for {item.product.title}.")
                return redirect('store:cart')

            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

            item.product.stock -= item.quantity
            item.product.save()

        cart_items.delete()
        messages.success(request, "Order placed successfully!")
        return redirect('store:orders')

    # 🟦 Render checkout page
    return render(request, 'store/checkout.html', {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'shipping_amount': shipping_amount,
        'total_price': total_price,
        'address': address,
    })



def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject', '')
        message = request.POST.get('message')

        # Save to database
        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        # Prepare email body
        full_message = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"

        try:
            send_mail(
                subject=f"Contact Form: {subject or 'No Subject'}",
                message=full_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['reginaldateya@gmail.com'],
            )
        except Exception as e:
            print("Email sending failed:", e)

        # ✅ Only run after successful POST
        messages.success(request, "Your message has been sent.")

        # ✅ Prevent resubmission on refresh
        return redirect('store:contact')  # Make sure your URL name is 'contact'

    return render(request, 'contact.html')

def blog_page(request):
    return render(request, 'store/blog.html')





@login_required
def orders(request):
    all_orders = Order.objects.filter(user=request.user).order_by('-ordered_date')
    return render(request, 'store/orders.html', {'orders': all_orders})

@login_required
def add_to_wishlist(request, product_id):
    if request.user.is_authenticated:
        product = get_object_or_404(Product, id=product_id)
        if not WishList.objects.filter(user=request.user, product=product).exists():
            WishList.objects.create(user=request.user, product=product)

        # Return the new wish list count as JSON for AJAX
        new_count = WishList.objects.filter(user=request.user).count()
        return JsonResponse({'new_wish_list_count': new_count})
    else:
        return redirect('store:login')  # If not logged in, redirect to login
    

def toggle_wish_list(request, product_id):
    if request.user.is_authenticated:
        product = get_object_or_404(Product, id=product_id)
        # Check if the product is already in the wish list
        wish_list_item = WishList.objects.filter(user=request.user, product=product).first()
        
        if wish_list_item:
            # If the product is already in the wish list, remove it
            wish_list_item.delete()
            action = 'removed'
        else:
            # If the product is not in the wish list, add it
            WishList.objects.create(user=request.user, product=product)
            action = 'added'
        
        # Return a JSON response to update the front-end
        return JsonResponse({'action': action})
    else:
        return JsonResponse({'error': 'User not authenticated'}, status=400)

    
def some_view(request):
    # Fetch the user's wish list count (if authenticated)
    wish_list_count = 0
    if request.user.is_authenticated:
        wish_list_count = WishList.objects.filter(user=request.user).count()

    return render(request, 'store/wishlist.html', {
        'wish_list_count': wish_list_count,
    })  
class WishListView(LoginRequiredMixin, View):
    def get(self, request):
        wishlist_items = WishList.objects.filter(user=request.user).select_related('product')
        return render(request, 'store/wishlist.html', {'wishlist_items': wishlist_items}) 
    





def shop(request):
    return render(request, 'store/shop.html')





def test(request):
    return render(request, 'store/test.html')
