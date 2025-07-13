from django.contrib import admin
from .models import Address, Category, Product, Cart, Order, OrderItem, ContactMessage
from django.contrib.admin.sites import AlreadyRegistered # Add this import at the top of the file


# Register your models here.
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'email', 'phone', 'city', 'state')
    search_fields = ('user__username', 'first_name', 'last_name', 'email', 'phone', 'city', 'state')
    list_filter = ('city', 'state')
    list_per_page = 10
    

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'submitted_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('submitted_at',)    


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'category_image', 'is_active', 'is_featured', 'updated_at')
    list_editable = ('slug', 'is_active', 'is_featured')
    list_filter = ('is_active', 'is_featured')
    list_per_page = 10
    search_fields = ('title', 'description')
    prepopulated_fields = {"slug": ("title", )}


class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'category', 'stock', 'product_image', 'is_active', 'is_featured', 'updated_at')
    list_editable = ('slug', 'category', 'is_active', 'is_featured', 'stock')
    list_filter = ('category', 'is_active', 'is_featured')
    list_per_page = 10
    search_fields = ('title', 'category', 'short_description')
    prepopulated_fields = {"slug": ("title", )}

class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity', 'created_at')
    list_editable = ('quantity',)
    list_filter = ('created_at',)
    list_per_page = 20
    search_fields = ('user', 'product')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'total_price', 'ordered_date']
    list_filter = ['status']
    list_editable = ['status']
    inlines = [OrderItemInline]



    




try:
    admin.site.register(Address, AddressAdmin)
    admin.site.register(Category, CategoryAdmin)
    admin.site.register(Product, ProductAdmin)
    admin.site.register(Cart, CartAdmin)
    admin.site.register(Order, OrderAdmin)
except AlreadyRegistered as e:
    print(f"[Admin Debug] Already registered: {e}")