from django.contrib import admin
from .models import (
    Company,
    Executive,
    CompanyUpdateCandidate,
    CompanyReviewBatch,
    CompanyReviewItem,
    CompanyUpdateHistory,
)


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


@admin.register(CompanyUpdateCandidate)
class CompanyUpdateCandidateAdmin(admin.ModelAdmin):
    list_display = (
        'company',
        'field',
        'candidate_value',
        'rejection_reason_display',
        'source_type',
        'confidence',
        'status',
        'collected_at',
    )
    list_filter = ('status', 'source_type', 'confidence', 'collected_at')
    search_fields = ('company__name', 'field', 'candidate_value')
    ordering = ('-created_at',)

    @admin.display(description='否認理由')
    def rejection_reason_display(self, obj):
        if not obj.rejection_reason_code:
            return ''
        label = obj.get_rejection_reason_code_display()
        detail = (obj.rejection_reason_detail or '').strip()
        return f'{label} / {detail}' if detail else label


@admin.register(CompanyReviewBatch)
class CompanyReviewBatchAdmin(admin.ModelAdmin):
    list_display = ('company', 'status', 'assigned_to', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('company__name',)
    ordering = ('-created_at',)


@admin.register(CompanyReviewItem)
class CompanyReviewItemAdmin(admin.ModelAdmin):
    list_display = ('batch', 'field', 'decision', 'confidence', 'decided_by', 'decided_at')
    list_filter = ('decision', 'confidence')
    search_fields = ('batch__company__name', 'field', 'candidate_value')
    ordering = ('-created_at',)


@admin.register(CompanyUpdateHistory)
class CompanyUpdateHistoryAdmin(admin.ModelAdmin):
    list_display = ('company', 'field', 'source_type', 'approved_by', 'approved_at', 'created_at')
    list_filter = ('field', 'source_type', 'approved_at')
    search_fields = ('company__name', 'field', 'new_value')
    ordering = ('-created_at',)
