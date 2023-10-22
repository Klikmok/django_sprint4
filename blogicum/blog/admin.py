from django.contrib import admin

from .models import Category, Location, Post


class PostAdmin(admin.ModelAdmin):
    empty_value_display = 'Не задано'


admin.site.empty_value_display = 'Не задано'
admin.site.register(Category)
admin.site.register(Location)
admin.site.register(Post, PostAdmin)
