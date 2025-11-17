from django.contrib import admin
from .models import Client, ClientNGCompany


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'industry', 'prefecture', 'employee_count', 'revenue', 'is_active', 'created_at')
    list_filter = ('industry', 'prefecture', 'is_active', 'created_at')
    search_fields = ('name', 'contact_person', 'contact_email', 'notes')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'company_type', 'industry')
        }),
        ('担当者情報', {
            'fields': ('contact_person', 'contact_person_position', 'contact_email', 'contact_phone')
        }),
        ('企業情報', {
            'fields': ('facebook_url', 'employee_count', 'revenue', 'prefecture')
        }),
        ('連絡先情報', {
            'fields': ('address', 'website', 'notes')
        }),
        ('システム管理', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ClientNGCompany)
class ClientNGCompanyAdmin(admin.ModelAdmin):
    list_display = ('client', 'company_name', 'matched', 'is_active', 'created_at')
    list_filter = ('matched', 'is_active', 'created_at')
    search_fields = ('client__name', 'company_name', 'reason')
    ordering = ('-created_at',)
