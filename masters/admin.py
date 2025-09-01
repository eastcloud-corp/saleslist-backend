from django.contrib import admin
from .models import Industry, Status, Prefecture


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    ordering = ('display_order', 'name')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'display_order', 'is_active')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'display_order', 'color_code', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('category', 'display_order', 'name')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'category', 'description')
        }),
        ('表示設定', {
            'fields': ('display_order', 'color_code', 'is_active')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Prefecture)
class PrefectureAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'display_order', 'is_active', 'created_at')
    list_filter = ('region', 'is_active')
    search_fields = ('name',)
    ordering = ('display_order', 'name')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'region', 'display_order', 'is_active')
        }),
    )
    
    readonly_fields = ('created_at',)
