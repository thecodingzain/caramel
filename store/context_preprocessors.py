from .models import Category, Cart, WishList


def store_menu(request):
    categories = Category.objects.filter(is_active=True)
    context = {
        'categories_menu': categories,
    }
    return context

def cart_menu(request):
    if request.user.is_authenticated:
        cart_items= Cart.objects.filter(user=request.user)
        context = {
            'cart_items': cart_items,
        }
    else:
        context = {}
    return context


def wish_list_count(request):
    if request.user.is_authenticated:
        count = WishList.objects.filter(user=request.user).count()
    else:
        count = 0
    return {'wish_list_count': count}
