from django.contrib import admin
from .models import Company, Executive


class ExecutiveInline(admin.TabularInline):
    model = Executive
    extra = 1
    fields = ('name', 'position', 'facebook_url', 'direct_email')


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', 'prefecture', 'employee_count', 'revenue', 'is_global_ng', 'created_at')
    list_filter = ('industry', 'prefecture', 'tob_toc_type', 'is_global_ng', 'created_at')
    search_fields = ('name', 'contact_person_name', 'business_description')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'corporate_number', 'industry', 'business_description')
        }),
        ('担当者情報', {
            'fields': ('contact_person_name', 'contact_person_position', 'facebook_url')
        }),
        ('事業情報', {
            'fields': ('tob_toc_type',)
        }),
        ('所在地', {
            'fields': ('prefecture', 'city')
        }),
        ('規模情報', {
            'fields': ('employee_count', 'revenue', 'capital', 'established_year')
        }),
        ('連絡先', {
            'fields': ('website_url', 'contact_email', 'phone')
        }),
        ('システム管理', {
            'fields': ('notes', 'is_global_ng')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ExecutiveInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related().prefetch_related('executives')


@admin.register(Executive)
class ExecutiveAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'position', 'facebook_url', 'direct_email', 'created_at')
    list_filter = ('position', 'created_at')
    search_fields = ('name', 'company__name', 'direct_email')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('基本情報', {
            'fields': ('company', 'name', 'position')
        }),
        ('連絡先', {
            'fields': ('facebook_url', 'other_sns_url', 'direct_email')
        }),
        ('備考', {
            'fields': ('notes',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
